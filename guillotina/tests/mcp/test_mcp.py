import asyncio
import base64
import json
import os

import pytest

from guillotina.auth.users import GuillotinaUser
from guillotina.component import query_utility
from guillotina.contrib.mcp import resources as mcp_resources
from guillotina.contrib.mcp import tools as mcp_tools
from guillotina.contrib.mcp.interfaces import IMCPToolRegistry
from guillotina.interfaces import Allow
from guillotina.interfaces.catalog import ICatalogUtility
from guillotina.response import HTTPUnauthorized
from guillotina.tests import utils
from guillotina.utils import get_security_policy, resolve_dotted_name


pytestmark = pytest.mark.asyncio

NOT_POSTGRES = os.environ.get("DATABASE", "DUMMY") in ("cockroachdb", "DUMMY")

MCP_SETTINGS = {
    "applications": ["guillotina", "guillotina.contrib.mcp"],
}

MCP_SETTINGS_REDIS = {
    "applications": [
        "guillotina",
        "guillotina.contrib.mcp",
        "guillotina.contrib.redis",
    ],
}

MCP_SETTINGS_DISABLED = {
    "applications": ["guillotina", "guillotina.contrib.mcp"],
    "mcp": {"enabled": False},
}

MCP_SETTINGS_DBUSERS = {
    "applications": ["guillotina", "guillotina.contrib.dbusers", "guillotina.contrib.mcp"],
    "auth_user_identifiers": ["guillotina.contrib.dbusers.users.DBUserIdentifier"],
}

MCP_SETTINGS_PG_CATALOG = {
    "applications": ["guillotina", "guillotina.contrib.mcp", "guillotina.contrib.catalog.pg"],
    "load_utilities": {
        "catalog": {
            "provides": "guillotina.interfaces.ICatalogUtility",
            "factory": "guillotina.contrib.catalog.pg.utility.PGSearchUtility",
        }
    },
}

PROTOCOL_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


class _MemoryCacheDriver:
    def __init__(self):
        self._data = {}

    async def get(self, key):
        return self._data.get(key)

    async def set(self, key, data, expire=None):
        self._data[key] = data


class _EmptyCatalog:
    async def search(self, context, query):
        return {"items": [], "items_total": 0}


class _RequestWithQuery:
    def __init__(self, request, query):
        self._request = request
        self.query = query

    def __getattr__(self, name):
        return getattr(self._request, name)


def _skip_if_protocol_unavailable(response, status):
    if status != 503:
        return
    reason = ""
    if isinstance(response, dict):
        reason = str(response.get("reason") or response.get("message") or "")
    known_causes = (
        "MCP SDK missing",
        'Install "guillotina[mcp]"',
        "MCP registry utility is not available",
    )
    if any(cause in reason for cause in known_causes):
        detail = f": {reason}" if reason else ""
        pytest.skip(f"MCP protocol unavailable in this environment{detail}")


async def _protocol(requester, method, params=None, id=1):
    payload = {"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}}
    response, status = await requester(
        "POST",
        "/db/guillotina/@mcp/protocol",
        data=json.dumps(payload),
        headers=PROTOCOL_HEADERS,
    )
    _skip_if_protocol_unavailable(response, status)
    return response, status


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_initialize(container_requester):
    async with container_requester as requester:
        response, status = await _protocol(
            requester,
            "initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        )
        assert status == 200
        assert response["jsonrpc"] == "2.0"
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert "tools" in response["result"]["capabilities"]
        assert "resources" in response["result"]["capabilities"]
        assert response["result"]["serverInfo"]["name"] == "guillotina-mcp"


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_tools_list(container_requester):
    async with container_requester as requester:
        response, status = await _protocol(requester, "tools/list")
        assert status == 200
        names = {t["name"] for t in response["result"]["tools"]}
        assert names == {"list_children", "resolve_path", "search"}


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_tools_call_resolve_path(container_requester):
    async with container_requester as requester:
        response, status = await _protocol(
            requester,
            "tools/call",
            params={"name": "resolve_path", "arguments": {"path": "/"}},
        )
        assert status == 200
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["path"] == "/"
        assert content["resource"]["@type"] == "Container"


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_tools_call_list_children(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina",
            data=json.dumps({"@type": "Item", "id": "item-proto"}),
        )
        assert status == 201

        response, status = await _protocol(
            requester,
            "tools/call",
            params={"name": "list_children", "arguments": {"path": "/", "limit": 20}},
        )
        assert status == 200
        content = json.loads(response["result"]["content"][0]["text"])
        ids = {item["id"] for item in content["items"]}
        assert "item-proto" in ids


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_tools_call_unknown_tool_returns_error(container_requester):
    async with container_requester as requester:
        response, status = await _protocol(
            requester,
            "tools/call",
            params={"name": "does-not-exist", "arguments": {}},
        )
        assert status == 200
        # Unknown tool: SDK returns a tool result with isError=True (not a JSON-RPC error)
        assert response["result"]["isError"] is True


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_resolve_path_tool_respects_access_content(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina",
            data=json.dumps({"@type": "Item", "id": "secret-item"}),
        )
        assert status == 201

        _, status = await requester(
            "POST",
            "/db/guillotina/secret-item/@sharing",
            data=json.dumps(
                {
                    "perminhe": [{"permission": "guillotina.AccessContent", "setting": "Deny"}],
                    "roleperm": [
                        {
                            "permission": "guillotina.AccessContent",
                            "role": "guillotina.Owner",
                            "setting": "Allow",
                        }
                    ],
                }
            ),
        )
        assert status == 200

        async with requester.transaction():
            container = await utils.get_container(requester=requester)
            secret = await container.async_get("secret-item")
            manager = GuillotinaUser("mcp-manager", roles={"guillotina.Manager": Allow})
            utils.login(user=manager)
            policy = get_security_policy(manager)
            assert policy.check_permission("guillotina.MCPExecute", container)
            assert not policy.check_permission("guillotina.AccessContent", secret)

            registry = query_utility(IMCPToolRegistry)
            with pytest.raises(HTTPUnauthorized):
                await registry.invoke(
                    "resolve_path",
                    container,
                    utils.get_mocked_request(db=requester.db),
                    {"path": "/secret-item"},
                )


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_resolve_path_tool_serialized_requires_view_content(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina",
            data=json.dumps({"@type": "Item", "id": "viewless-item"}),
        )
        assert status == 201

        async with requester.transaction():
            container = await utils.get_container(requester=requester)
            viewless = await container.async_get("viewless-item")
            executor = GuillotinaUser(
                "mcp-viewless",
                permissions={
                    "guillotina.MCPExecute": Allow,
                    "guillotina.AccessContent": Allow,
                },
            )
            utils.login(user=executor)
            policy = get_security_policy(executor)
            assert policy.check_permission("guillotina.MCPExecute", container)
            assert policy.check_permission("guillotina.AccessContent", viewless)
            assert not policy.check_permission("guillotina.ViewContent", viewless)

            registry = query_utility(IMCPToolRegistry)
            request = utils.get_mocked_request(db=requester.db)
            result = await registry.invoke(
                "resolve_path",
                container,
                request,
                {"path": "/viewless-item"},
            )
            assert result["resource"]["id"] == "viewless-item"
            assert "serialized" not in result

            with pytest.raises(HTTPUnauthorized):
                await registry.invoke(
                    "resolve_path",
                    container,
                    request,
                    {"path": "/viewless-item", "include_serialized": True},
                )


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_list_children_tool_filters_inaccessible_children(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina",
            data=json.dumps({"@type": "Folder", "id": "mcp-folder"}),
        )
        assert status == 201
        for item_id in ("visible-item", "secret-item"):
            _, status = await requester(
                "POST",
                "/db/guillotina/mcp-folder",
                data=json.dumps({"@type": "Item", "id": item_id}),
            )
            assert status == 201

        _, status = await requester(
            "POST",
            "/db/guillotina/mcp-folder/@sharing",
            data=json.dumps(
                {
                    "prinperm": [
                        {
                            "principal": "mcp-manager",
                            "permission": "guillotina.AccessContent",
                            "setting": "Allow",
                        }
                    ]
                }
            ),
        )
        assert status == 200
        _, status = await requester(
            "POST",
            "/db/guillotina/mcp-folder/secret-item/@sharing",
            data=json.dumps({"perminhe": [{"permission": "guillotina.AccessContent", "setting": "Deny"}]}),
        )
        assert status == 200

        async with requester.transaction():
            container = await utils.get_container(requester=requester)
            folder = await container.async_get("mcp-folder")
            secret = await folder.async_get("secret-item")
            manager = GuillotinaUser("mcp-manager", roles={"guillotina.Manager": Allow})
            utils.login(user=manager)
            policy = get_security_policy(manager)
            assert policy.check_permission("guillotina.MCPExecute", container)
            assert policy.check_permission("guillotina.AccessContent", folder)
            assert not policy.check_permission("guillotina.AccessContent", secret)

            registry = query_utility(IMCPToolRegistry)
            result = await registry.invoke(
                "list_children",
                container,
                utils.get_mocked_request(db=requester.db),
                {"path": "/mcp-folder"},
            )

        assert {item["id"] for item in result["items"]} == {"visible-item"}


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_tool_cache_isolated_by_effective_security(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina",
            data=json.dumps({"@type": "Item", "id": "cached-secret-item"}),
        )
        assert status == 201
        _, status = await requester(
            "POST",
            "/db/guillotina/cached-secret-item/@sharing",
            data=json.dumps(
                {
                    "perminhe": [{"permission": "guillotina.AccessContent", "setting": "Deny"}],
                    "roleperm": [
                        {
                            "permission": "guillotina.AccessContent",
                            "role": "guillotina.Owner",
                            "setting": "Allow",
                        }
                    ],
                }
            ),
        )
        assert status == 200

        async with requester.transaction():
            container = await utils.get_container(requester=requester)
            secret = await container.async_get("cached-secret-item")
            registry = query_utility(IMCPToolRegistry)
            cache_disabled = registry._cache_disabled
            driver_redis = registry._driver_redis
            registry._cache_disabled = False
            registry._driver_redis = _MemoryCacheDriver()
            request = utils.get_mocked_request(db=requester.db)

            try:
                utils.login()
                root_result = await registry.invoke(
                    "resolve_path",
                    container,
                    request,
                    {"path": "/cached-secret-item"},
                )
                assert root_result["resource"]["id"] == "cached-secret-item"

                manager = GuillotinaUser("mcp-manager", roles={"guillotina.Manager": Allow})
                utils.login(user=manager)
                policy = get_security_policy(manager)
                assert policy.check_permission("guillotina.MCPExecute", container)
                assert not policy.check_permission("guillotina.AccessContent", secret)

                with pytest.raises(HTTPUnauthorized):
                    await registry.invoke(
                        "resolve_path",
                        container,
                        request,
                        {"path": "/cached-secret-item"},
                    )
            finally:
                registry._cache_disabled = cache_disabled
                registry._driver_redis = driver_redis


@pytest.mark.app_settings(MCP_SETTINGS_PG_CATALOG)
@pytest.mark.skipif(NOT_POSTGRES, reason="Only PG")
async def test_search_tool_uses_catalog_security_filter(container_requester):
    async with container_requester as requester:
        for item_id in ("visible-item", "secret-item"):
            _, status = await requester(
                "POST",
                "/db/guillotina",
                data=json.dumps({"@type": "Item", "id": item_id}),
            )
            assert status == 201

        _, status = await requester(
            "POST",
            "/db/guillotina/visible-item/@sharing",
            data=json.dumps(
                {
                    "prinperm": [
                        {
                            "principal": "mcp-manager",
                            "permission": "guillotina.AccessContent",
                            "setting": "Allow",
                        }
                    ]
                }
            ),
        )
        assert status == 200
        _, status = await requester(
            "POST",
            "/db/guillotina/@sharing",
            data=json.dumps(
                {
                    "prinperm": [
                        {
                            "principal": "mcp-manager",
                            "permission": "guillotina.SearchContent",
                            "setting": "Allow",
                        }
                    ]
                }
            ),
        )
        assert status == 200
        _, status = await requester(
            "POST",
            "/db/guillotina/secret-item/@sharing",
            data=json.dumps({"perminhe": [{"permission": "guillotina.AccessContent", "setting": "Deny"}]}),
        )
        assert status == 200

        async with requester.transaction():
            container = await utils.get_container(requester=requester)
            visible = await container.async_get("visible-item")
            secret = await container.async_get("secret-item")
            manager = GuillotinaUser("mcp-manager", roles={"guillotina.Manager": Allow})
            utils.login(user=manager)
            policy = get_security_policy(manager)
            assert policy.check_permission("guillotina.MCPExecute", container)
            assert policy.check_permission("guillotina.SearchContent", container)
            assert policy.check_permission("guillotina.AccessContent", visible)
            assert not policy.check_permission("guillotina.AccessContent", secret)

            registry = query_utility(IMCPToolRegistry)
            result = await registry.invoke(
                "search",
                container,
                utils.get_mocked_request(db=requester.db),
                {"query": {"type_name": "Item", "_metadata": "id,type_name,title,path"}},
            )

        assert {item["id"] for item in result["result"]["items"]} == {"visible-item"}
        assert result["result"]["items_total"] == 1


@pytest.mark.app_settings(MCP_SETTINGS_PG_CATALOG)
@pytest.mark.skipif(NOT_POSTGRES, reason="Only PG")
async def test_list_children_tool_uses_catalog_security_filter(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina",
            data=json.dumps({"@type": "Folder", "id": "catalog-folder"}),
        )
        assert status == 201
        for item_id in ("visible-child", "secret-child"):
            _, status = await requester(
                "POST",
                "/db/guillotina/catalog-folder",
                data=json.dumps({"@type": "Item", "id": item_id}),
            )
            assert status == 201

        _, status = await requester(
            "POST",
            "/db/guillotina/catalog-folder/@sharing",
            data=json.dumps(
                {
                    "prinperm": [
                        {
                            "principal": "mcp-manager",
                            "permission": "guillotina.AccessContent",
                            "setting": "Allow",
                        },
                        {
                            "principal": "mcp-manager",
                            "permission": "guillotina.ViewContent",
                            "setting": "Allow",
                        },
                    ]
                }
            ),
        )
        assert status == 200
        _, status = await requester(
            "POST",
            "/db/guillotina/catalog-folder/secret-child/@sharing",
            data=json.dumps({"perminhe": [{"permission": "guillotina.AccessContent", "setting": "Deny"}]}),
        )
        assert status == 200
        await asyncio.sleep(0.5)

        async with requester.transaction():
            container = await utils.get_container(requester=requester)
            folder = await container.async_get("catalog-folder")
            secret = await folder.async_get("secret-child")
            manager = GuillotinaUser("mcp-manager", roles={"guillotina.Manager": Allow})
            utils.login(user=manager)
            policy = get_security_policy(manager)
            assert policy.check_permission("guillotina.MCPExecute", container)
            assert policy.check_permission("guillotina.AccessContent", folder)
            assert policy.check_permission("guillotina.ViewContent", folder)
            assert not policy.check_permission("guillotina.AccessContent", secret)

            registry = query_utility(IMCPToolRegistry)
            result = await registry.invoke(
                "list_children",
                container,
                utils.get_mocked_request(db=requester.db),
                {"path": "/catalog-folder", "include_serialized": True},
            )

        assert {item["id"] for item in result["items"]} == {"visible-child"}
        item = result["items"][0]
        assert item["serialized"]["@name"] == "visible-child"
        assert item["serialized"]["@type"] == "Item"


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_summary_resource_respects_access_content(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina",
            data=json.dumps({"@type": "Item", "id": "secret-summary-item"}),
        )
        assert status == 201
        _, status = await requester(
            "POST",
            "/db/guillotina/secret-summary-item/@sharing",
            data=json.dumps(
                {
                    "perminhe": [{"permission": "guillotina.AccessContent", "setting": "Deny"}],
                    "roleperm": [
                        {
                            "permission": "guillotina.AccessContent",
                            "role": "guillotina.Owner",
                            "setting": "Allow",
                        }
                    ],
                }
            ),
        )
        assert status == 200

        async with requester.transaction():
            container = await utils.get_container(requester=requester)
            secret = await container.async_get("secret-summary-item")
            manager = GuillotinaUser("mcp-manager", roles={"guillotina.Manager": Allow})
            utils.login(user=manager)
            policy = get_security_policy(manager)
            assert policy.check_permission("guillotina.MCPExecute", container)
            assert not policy.check_permission("guillotina.AccessContent", secret)

            registry = query_utility(IMCPToolRegistry)
            request = _RequestWithQuery(
                utils.get_mocked_request(db=requester.db), {"path": "/secret-summary-item"}
            )
            with pytest.raises(HTTPUnauthorized):
                await registry.read_resource("summary", container, request)


@pytest.mark.app_settings(MCP_SETTINGS_DBUSERS)
async def test_users_resource_requires_manage_users(dbusers_requester):
    async with dbusers_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/users",
            data=json.dumps(
                {
                    "@type": "User",
                    "id": "listed-user",
                    "username": "listed-user",
                    "email": "listed@example.com",
                    "password": "password",
                }
            ),
        )
        assert status == 201

        async with requester.transaction():
            container = await utils.get_container(requester=requester)
            executor = GuillotinaUser("mcp-executor", permissions={"guillotina.MCPExecute": Allow})
            utils.login(user=executor)
            policy = get_security_policy(executor)
            assert policy.check_permission("guillotina.MCPExecute", container)
            assert not policy.check_permission("guillotina.ManageUsers", container)

            registry = query_utility(IMCPToolRegistry)
            with pytest.raises(HTTPUnauthorized):
                await registry.read_resource("users", container, utils.get_mocked_request(db=requester.db))


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_config_resource_requires_read_configuration(container_requester):
    async with container_requester as requester:
        async with requester.transaction():
            container = await utils.get_container(requester=requester)
            executor = GuillotinaUser("mcp-executor", permissions={"guillotina.MCPExecute": Allow})
            utils.login(user=executor)
            policy = get_security_policy(executor)
            assert policy.check_permission("guillotina.MCPExecute", container)
            assert not policy.check_permission("guillotina.ReadConfiguration", container)

            registry = query_utility(IMCPToolRegistry)
            with pytest.raises(HTTPUnauthorized):
                await registry.read_resource("config", container, utils.get_mocked_request(db=requester.db))


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_search_tool_requires_search_content_permission(container_requester, monkeypatch):
    async with container_requester as requester:

        def query_catalog_utility(interface, default=None):
            if interface is ICatalogUtility:
                return _EmptyCatalog()
            return default

        monkeypatch.setattr(mcp_tools, "query_utility", query_catalog_utility)

        async with requester.transaction():
            container = await utils.get_container(requester=requester)
            executor = GuillotinaUser("mcp-executor", roles={"guillotina.Manager": Allow})
            utils.login(user=executor)
            policy = get_security_policy(executor)
            assert policy.check_permission("guillotina.MCPExecute", container)
            assert not policy.check_permission("guillotina.SearchContent", container)

            registry = query_utility(IMCPToolRegistry)
            with pytest.raises(HTTPUnauthorized):
                await registry.invoke(
                    "search",
                    container,
                    utils.get_mocked_request(db=requester.db),
                    {"query": {"type_name": "Item"}},
                )


@pytest.mark.app_settings(MCP_SETTINGS_DISABLED)
async def test_mcp_disabled_rejects_protocol_requests(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/@mcp/protocol",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1.0"},
                    },
                }
            ),
            headers=PROTOCOL_HEADERS,
        )
        assert status in (404, 503)
        if status == 503 and isinstance(response, dict):
            reason = str(response.get("reason") or response.get("message") or "")
            assert "disabled" in reason.lower()


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_tool_cache_isolated_by_container_context(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db",
            data=json.dumps(
                {
                    "@type": "Container",
                    "title": "Other Container",
                    "id": "mcp-other",
                    "description": "Other container",
                }
            ),
        )
        assert status == 200

        try:
            async with requester.transaction():
                registry = query_utility(IMCPToolRegistry)
                cache_disabled = registry._cache_disabled
                driver_redis = registry._driver_redis
                registry._cache_disabled = False
                registry._driver_redis = _MemoryCacheDriver()
                request = utils.get_mocked_request(db=requester.db)

                try:
                    utils.login()
                    first_container = await utils.get_container(
                        requester=requester, container_id="guillotina"
                    )
                    first_result = await registry.invoke(
                        "resolve_path", first_container, request, {"path": "/"}
                    )
                    assert first_result["resource"]["id"] == "guillotina"

                    second_container = await utils.get_container(
                        requester=requester, container_id="mcp-other"
                    )
                    second_result = await registry.invoke(
                        "resolve_path", second_container, request, {"path": "/"}
                    )
                    assert second_result["resource"]["id"] == "mcp-other"
                finally:
                    registry._cache_disabled = cache_disabled
                    registry._driver_redis = driver_redis
        finally:
            await requester("DELETE", "/db/mcp-other")


@pytest.mark.app_settings(MCP_SETTINGS_DBUSERS)
async def test_protocol_requires_access_content_on_invocation_context(dbusers_requester):
    async with dbusers_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/users",
            data=json.dumps(
                {
                    "@type": "User",
                    "id": "mcp-manager",
                    "username": "mcp-manager",
                    "email": "manager@example.com",
                    "password": "password",
                    "user_roles": ["guillotina.Manager"],
                }
            ),
        )
        assert status == 201
        _, status = await requester(
            "POST",
            "/db/guillotina",
            data=json.dumps({"@type": "Item", "id": "private-context"}),
        )
        assert status == 201
        _, status = await requester(
            "POST",
            "/db/guillotina/private-context/@sharing",
            data=json.dumps({"perminhe": [{"permission": "guillotina.AccessContent", "setting": "Deny"}]}),
        )
        assert status == 200

        response, status = await requester(
            "POST",
            "/db/guillotina/private-context/@mcp/protocol",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1.0"},
                    },
                }
            ),
            headers=PROTOCOL_HEADERS,
            token=base64.b64encode(b"mcp-manager:password").decode("ascii"),
            auth_type="Basic",
        )
        _skip_if_protocol_unavailable(response, status)
        assert status == 401


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_resources_list(container_requester):
    async with container_requester as requester:
        response, status = await _protocol(requester, "resources/list")
        assert status == 200
        names = {r["name"] for r in response["result"]["resources"]}
        for expected in ("info", "health", "config", "users", "catalog", "summary"):
            assert expected in names, f"Missing resource: {expected}"


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_resources_read_info(container_requester):
    async with container_requester as requester:
        response, status = await _protocol(
            requester,
            "resources/read",
            params={"uri": "guillotina://resources/info"},
        )
        assert status == 200
        content = json.loads(response["result"]["contents"][0]["text"])
        assert "version" in content
        assert "container_id" in content


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_resources_read_summary_with_path(container_requester):
    """resources/read for summary accepts ?path= URI query params (server.py uri matching fix)."""
    async with container_requester as requester:
        # Without path — should return container summary
        response, status = await _protocol(
            requester,
            "resources/read",
            params={"uri": "guillotina://resources/summary"},
        )
        assert status == 200
        content = json.loads(response["result"]["contents"][0]["text"])
        assert content["path"] == "/"
        assert content["@type"] == "Container"

        # With ?path=/ — same result, proves URI query params are forwarded
        response, status = await _protocol(
            requester,
            "resources/read",
            params={"uri": "guillotina://resources/summary?path=/"},
        )
        assert status == 200
        content = json.loads(response["result"]["contents"][0]["text"])
        assert content["path"] == "/"
        assert content["@type"] == "Container"


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_requires_accept_header(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/@mcp/protocol",
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}),
            headers={"Content-Type": "application/json"},
        )
        _skip_if_protocol_unavailable(response, status)
        assert status in (200, 406)
        if status == 200:
            assert response.get("jsonrpc") == "2.0"
            assert "result" in response


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_invalid_json_rpc_returns_400(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/@mcp/protocol",
            data=json.dumps({"not": "jsonrpc"}),
            headers=PROTOCOL_HEADERS,
        )
        _skip_if_protocol_unavailable(response, status)
        assert status == 400


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_unknown_action_returns_404(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/@mcp/not-a-real-action",
            data=json.dumps({}),
            headers=PROTOCOL_HEADERS,
        )
        assert status == 404


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_protocol_resource_registry_matches_defaults(container_requester):
    async with container_requester as requester:
        response, status = await _protocol(requester, "resources/list")
        assert status == 200
        registered_names = {r["name"] for r in response["result"]["resources"]}
        default_names = {res[0] for res in mcp_resources.default_resources()}
        assert registered_names == default_names


@pytest.mark.app_settings(MCP_SETTINGS)
async def test_invoke_resolve_path_tool(container_requester):
    """Kept as an alias — now uses the JSON-RPC protocol path."""
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina",
            data=json.dumps({"@type": "Item", "id": "foo_item"}),
        )
        assert status == 201

        response, status = await _protocol(
            requester,
            "tools/call",
            params={"name": "resolve_path", "arguments": {"path": "/"}},
        )
        assert status == 200
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["resource"]["@type"] == "Container"
        assert content["path"] == "/"

        response, status = await _protocol(
            requester,
            "tools/call",
            params={"name": "resolve_path", "arguments": {"path": "/foo_item"}},
        )
        assert status == 200
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["resource"]["@type"] == "Item"
        assert content["path"] == "/foo_item"


@pytest.mark.app_settings(MCP_SETTINGS_REDIS)
async def test_cache_redis_isolated_by_container_context(redis_container, container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db",
            data=json.dumps(
                {
                    "@type": "Container",
                    "title": "Other Container",
                    "id": "mcp-other",
                    "description": "Other container",
                }
            ),
        )
        assert status == 200

        driver = await resolve_dotted_name("guillotina.contrib.redis").get_driver()
        assert driver.initialized
        keys = await driver.keys_startswith("mcp_tool_cache:v1")
        await driver.delete_all(keys)

        try:
            async with requester.transaction():
                utils.login()
                registry = query_utility(IMCPToolRegistry)
                assert registry._cache_disabled is False

                first_container = await utils.get_container(requester=requester, container_id="guillotina")
                first_result = await registry.invoke(
                    "resolve_path",
                    first_container,
                    utils.get_mocked_request(db=requester.db),
                    {"path": "/"},
                )
                assert first_result["resource"]["id"] == "guillotina"

                second_container = await utils.get_container(requester=requester, container_id="mcp-other")
                second_result = await registry.invoke(
                    "resolve_path",
                    second_container,
                    utils.get_mocked_request(db=requester.db),
                    {"path": "/"},
                )
                assert second_result["resource"]["id"] == "mcp-other"
        finally:
            keys = await driver.keys_startswith("mcp_tool_cache:v1")
            await driver.delete_all(keys)
            await requester("DELETE", "/db/mcp-other")


@pytest.mark.app_settings(MCP_SETTINGS_REDIS)
async def test_cache_redis(redis_container, container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina",
            data=json.dumps({"@type": "Item", "id": "foo_item"}),
        )
        assert status == 201

        response, status = await _protocol(
            requester,
            "tools/call",
            params={"name": "resolve_path", "arguments": {"path": "/"}},
        )
        assert status == 200
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["resource"]["@type"] == "Container"
        assert content["path"] == "/"

        response, status = await _protocol(
            requester,
            "tools/call",
            params={"name": "resolve_path", "arguments": {"path": "/foo_item"}},
        )
        assert status == 200
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["resource"]["@type"] == "Item"
        assert content["path"] == "/foo_item"
        driver = await resolve_dotted_name("guillotina.contrib.redis").get_driver()
        assert driver.initialized
        keys = await driver.keys_startswith("mcp_tool_cache:v1")
        assert len(keys) == 2
        # Let's modify an object to invalidate the cache
        _, status = await requester(
            "PATCH",
            "/db/guillotina/foo_item",
            data=json.dumps({"title": "Foo title"}),
        )
        assert status == 204
        await asyncio.sleep(0.5)
        keys = await driver.keys_startswith("mcp_tool_cache:v1")
        assert len(keys) == 0
