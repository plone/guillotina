import pytest

from guillotina.contrib.oauth.api import well_known
from guillotina.response import HTTPNotFound


class _FakeRequest:
    def __init__(self, protected_path=None):
        self.oauth_protected_resource_path = protected_path


@pytest.mark.asyncio
async def test_register_protected_resource_provider_appends_provider(monkeypatch):
    providers = []
    monkeypatch.setattr(well_known, "_PROTECTED_RESOURCE_PROVIDERS", providers)

    def provider(request, container, protected_path):
        return None

    well_known.register_protected_resource_provider(provider)
    assert providers == [provider]


@pytest.mark.asyncio
async def test_protected_resource_metadata_uses_first_matching_provider(monkeypatch):
    def provider_a(request, container, protected_path):
        return None

    def provider_b(request, container, protected_path):
        return {"resource": "b", "authorization_servers": ["issuer"]}

    def provider_c(request, container, protected_path):
        raise AssertionError("should not be called after a matching provider")

    monkeypatch.setattr(
        well_known,
        "_PROTECTED_RESOURCE_PROVIDERS",
        [provider_a, provider_b, provider_c],
    )
    request = _FakeRequest("/db/guillotina/@mcp/protocol")
    result = well_known._protected_resource_metadata(request, None)
    assert result == {"resource": "b", "authorization_servers": ["issuer"]}


@pytest.mark.asyncio
async def test_protected_resource_metadata_returns_404_when_no_provider_matches(monkeypatch):
    def provider(request, container, protected_path):
        return None

    monkeypatch.setattr(well_known, "_PROTECTED_RESOURCE_PROVIDERS", [provider])
    request = _FakeRequest("/db/guillotina/unknown-resource")
    with pytest.raises(HTTPNotFound):
        well_known._protected_resource_metadata(request, None)


@pytest.mark.asyncio
async def test_container_path_parts_allows_resource_suffix():
    db_id, container_id, protected_path = well_known._container_path_parts(
        "/db/guillotina/subfolder/@mcp/protocol", allow_resource_path=True
    )
    assert db_id == "db"
    assert container_id == "guillotina"
    assert protected_path == "/db/guillotina/subfolder/@mcp/protocol"


@pytest.mark.asyncio
async def test_container_path_parts_rejects_suffix_for_issuer_metadata():
    with pytest.raises(HTTPNotFound):
        well_known._container_path_parts("/db/guillotina/extra")
