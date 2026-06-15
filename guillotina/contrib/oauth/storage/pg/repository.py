import json
from datetime import datetime, timezone

from zope.interface import implementer

from guillotina import app_settings
from guillotina.contrib.oauth.storage.interfaces import IOAuthStore
from guillotina.contrib.oauth.utils.crypto import token_hash
from guillotina.exceptions import TransactionNotFound
from guillotina.transactions import get_transaction


def _format_iso_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _to_json_string(value):
    return json.dumps(value)


def _parse_json_string(value):
    if value is None:
        return []
    if isinstance(value, str):
        return json.loads(value)
    return list(value)


def _ensure_utc(value):
    if value is None:
        return None
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return _ensure_utc(value)
    if isinstance(value, str):
        return _ensure_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    return value


def _row_to_client(row):
    if row is None:
        return None
    return {
        "client_id": row["client_id"],
        "client_name": row["client_name"],
        "redirect_uris": _parse_json_string(row["redirect_uris"]),
        "grant_types": _parse_json_string(row["grant_types"]),
        "response_types": _parse_json_string(row["response_types"]),
        "token_endpoint_auth_method": "none",
        "scope": row["scope"] or "",
        "created_at": _format_iso_datetime(row["created_at"]),
        "updated_at": _format_iso_datetime(row["updated_at"]),
    }


def _row_to_code(row):
    if row is None:
        return None
    return {
        "code_hash": row["code_hash"],
        "client_id": row["client_id"],
        "user_id": row["user_id"],
        "redirect_uri": row["redirect_uri"],
        "scope": _parse_json_string(row["scope"]),
        "resource": _parse_json_string(row["resource"]),
        "code_challenge": row["code_challenge"],
        "code_challenge_method": "S256",
        "expires_at": _format_iso_datetime(row["expires_at"]),
        "created_at": _format_iso_datetime(row["created_at"]),
    }


def _row_to_refresh(row):
    if row is None:
        return None
    return {
        "token_hash": row["token_hash"],
        "client_id": row["client_id"],
        "user_id": row["user_id"],
        "scope": _parse_json_string(row["scope"]),
        "resource": _parse_json_string(row["resource"]),
        "expires_at": _format_iso_datetime(row["expires_at"]),
        "rotated_from": row["rotated_from"],
        "auth_code_hash": row["auth_code_hash"],
        "created_at": _format_iso_datetime(row["created_at"]),
        "last_used_at": _format_iso_datetime(row["last_used_at"]),
        "revoked_at": _format_iso_datetime(row["revoked_at"]),
        "replaced_by": row["replaced_by"],
    }


def _row_to_consent(row):
    if row is None:
        return None
    return {
        "consent_key": row["consent_key"],
        "user_id": row["user_id"],
        "client_id": row["client_id"],
        "scope": _parse_json_string(row["scope"]),
        "resource": _parse_json_string(row["resource"]),
        "granted_at": _format_iso_datetime(row["granted_at"]),
        "expires_at": _format_iso_datetime(row["expires_at"]),
    }


@implementer(IOAuthStore)
class PostgresOAuthStore:
    def __init__(self, container_db_key: str):
        self.container_db_key = container_db_key

    async def _connection(self):
        txn = get_transaction()
        if txn is None:
            raise TransactionNotFound()
        conn = await txn.get_connection()
        return txn, conn

    async def get_client(self, client_id):
        txn, conn = await self._connection()
        async with txn.lock:
            row = await conn.fetchrow(
                """
                SELECT client_id, client_name, redirect_uris, grant_types, response_types,
                       scope, created_at, updated_at
                FROM oauth_clients
                WHERE container_db_key = $1 AND client_id = $2
                """,
                self.container_db_key,
                client_id,
            )
        return _row_to_client(row)

    async def create_client(self, client):
        txn, conn = await self._connection()
        async with txn.lock:
            await conn.execute(
                """
                INSERT INTO oauth_clients (
                    container_db_key, client_id, client_name, redirect_uris, grant_types,
                    response_types, scope, created_at, updated_at
                ) VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, $7, $8, $9)
                """,
                self.container_db_key,
                client["client_id"],
                client["client_name"],
                _to_json_string(client["redirect_uris"]),
                _to_json_string(client["grant_types"]),
                _to_json_string(client["response_types"]),
                client["scope"],
                _parse_dt(client["created_at"]),
                _parse_dt(client["updated_at"]),
            )

    async def has_consent(self, consent_key):
        txn, conn = await self._connection()
        async with txn.lock:
            row = await conn.fetchrow(
                """
                SELECT 1 FROM oauth_consents
                WHERE container_db_key = $1 AND consent_key = $2
                  AND (expires_at IS NULL OR expires_at > now())
                """,
                self.container_db_key,
                consent_key,
            )
        return row is not None

    async def create_consent(self, consent_key, *, user_id, client_id, scope, resource):
        ttl = app_settings.get("oauth", {}).get("consent_ttl", 2592000)
        # ttl == 0 means the consent never expires; any other value (including a
        # negative one, used by tests to force expiry) yields an explicit timestamp.
        txn, conn = await self._connection()
        async with txn.lock:
            await conn.execute(
                """
                INSERT INTO oauth_consents (
                    container_db_key, consent_key, user_id, client_id, scope, resource,
                    granted_at, expires_at
                ) VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, now(),
                    CASE WHEN $7::int = 0 THEN NULL
                         ELSE now() + $7::int * interval '1 second'
                    END)
                ON CONFLICT (container_db_key, consent_key) DO UPDATE
                SET scope = EXCLUDED.scope,
                    resource = EXCLUDED.resource,
                    granted_at = EXCLUDED.granted_at,
                    expires_at = EXCLUDED.expires_at
                """,
                self.container_db_key,
                consent_key,
                user_id,
                client_id,
                _to_json_string(list(scope)),
                _to_json_string(list(resource)),
                int(ttl),
            )

    async def list_consents(self, user_id):
        txn, conn = await self._connection()
        async with txn.lock:
            rows = await conn.fetch(
                """
                SELECT consent_key, user_id, client_id, scope, resource, granted_at, expires_at
                FROM oauth_consents
                WHERE container_db_key = $1 AND user_id = $2
                  AND (expires_at IS NULL OR expires_at > now())
                ORDER BY granted_at DESC
                """,
                self.container_db_key,
                user_id,
            )
        return [_row_to_consent(row) for row in rows]

    async def delete_consent(self, consent_key, *, user_id=None):
        txn, conn = await self._connection()
        async with txn.lock:
            if user_id is None:
                result = await conn.execute(
                    """
                    DELETE FROM oauth_consents
                    WHERE container_db_key = $1 AND consent_key = $2
                    """,
                    self.container_db_key,
                    consent_key,
                )
            else:
                result = await conn.execute(
                    """
                    DELETE FROM oauth_consents
                    WHERE container_db_key = $1 AND consent_key = $2 AND user_id = $3
                    """,
                    self.container_db_key,
                    consent_key,
                    user_id,
                )
        return int(result.split()[-1]) > 0

    async def revoke_user_client_refresh_tokens(self, *, user_id, client_id):
        txn, conn = await self._connection()
        async with txn.lock:
            result = await conn.execute(
                """
                UPDATE oauth_refresh_tokens
                SET revoked_at = COALESCE(revoked_at, now())
                WHERE container_db_key = $1
                  AND user_id = $2
                  AND client_id = $3
                  AND revoked_at IS NULL
                """,
                self.container_db_key,
                user_id,
                client_id,
            )
        return int(result.split()[-1]) > 0

    async def create_code(
        self,
        *,
        raw_code,
        client_id,
        user_id,
        redirect_uri,
        scope,
        resource,
        code_challenge,
    ):
        ttl = app_settings["oauth"].get("authorization_code_ttl", 600)
        code_hash_val = token_hash(raw_code)
        txn, conn = await self._connection()
        async with txn.lock:
            await conn.execute(
                """
                INSERT INTO oauth_authorization_codes (
                    container_db_key, code_hash, client_id, user_id, redirect_uri,
                    scope, resource, code_challenge, expires_at, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8,
                    now() + $9::int * interval '1 second', now())
                """,
                self.container_db_key,
                code_hash_val,
                client_id,
                user_id,
                redirect_uri,
                _to_json_string(list(scope)),
                _to_json_string(list(resource)),
                code_challenge,
                int(ttl),
            )
        return _row_to_code(
            {
                "code_hash": code_hash_val,
                "client_id": client_id,
                "user_id": user_id,
                "redirect_uri": redirect_uri,
                "scope": list(scope),
                "resource": list(resource),
                "code_challenge": code_challenge,
                "expires_at": None,
                "created_at": None,
            }
        )

    async def get_active_code(self, code):
        txn, conn = await self._connection()
        async with txn.lock:
            row = await conn.fetchrow(
                """
                SELECT code_hash, client_id, user_id, redirect_uri, scope, resource,
                       code_challenge, expires_at, created_at
                FROM oauth_authorization_codes
                WHERE container_db_key = $1
                  AND code_hash = $2
                  AND expires_at > now()
                """,
                self.container_db_key,
                token_hash(code),
            )
        return _row_to_code(row)

    async def consume_code(self, code):
        txn, conn = await self._connection()
        async with txn.lock:
            row = await conn.fetchrow(
                """
                DELETE FROM oauth_authorization_codes
                WHERE container_db_key = $1
                  AND code_hash = $2
                  AND expires_at > now()
                RETURNING code_hash, client_id, user_id, redirect_uri,
                          scope, resource, code_challenge, expires_at, created_at
                """,
                self.container_db_key,
                token_hash(code),
            )
        return _row_to_code(row)

    async def delete_code(self, code_hash_val):
        txn, conn = await self._connection()
        async with txn.lock:
            await conn.execute(
                """
                DELETE FROM oauth_authorization_codes
                WHERE container_db_key = $1 AND code_hash = $2
                """,
                self.container_db_key,
                code_hash_val,
            )

    async def revoke_refresh_tokens_by_auth_code(self, auth_code_hash):
        txn, conn = await self._connection()
        async with txn.lock:
            result = await conn.execute(
                """
                UPDATE oauth_refresh_tokens
                SET revoked_at = COALESCE(revoked_at, now())
                WHERE container_db_key = $1
                  AND auth_code_hash = $2
                  AND revoked_at IS NULL
                """,
                self.container_db_key,
                auth_code_hash,
            )
        return int(result.split()[-1]) > 0

    async def revoke_refresh_family(self, *, client_id, user_id, auth_code_hash):
        txn, conn = await self._connection()
        async with txn.lock:
            result = await conn.execute(
                """
                UPDATE oauth_refresh_tokens
                SET revoked_at = COALESCE(revoked_at, now())
                WHERE container_db_key = $1
                  AND client_id = $2
                  AND user_id = $3
                  AND (
                    ($4::text IS NULL AND auth_code_hash IS NULL)
                    OR auth_code_hash = $4
                  )
                  AND revoked_at IS NULL
                """,
                self.container_db_key,
                client_id,
                user_id,
                auth_code_hash,
            )
        return int(result.split()[-1]) > 0

    async def create_refresh_token(
        self,
        *,
        raw_token,
        client_id,
        user_id,
        scope,
        resource,
        auth_code_hash=None,
        rotated_from=None,
    ):
        ttl = app_settings["oauth"].get("refresh_token_ttl", 2592000)
        hash_val = token_hash(raw_token)
        txn, conn = await self._connection()
        async with txn.lock:
            await conn.execute(
                """
                INSERT INTO oauth_refresh_tokens (
                    container_db_key, token_hash, client_id, user_id, scope, resource,
                    expires_at, rotated_from, auth_code_hash, created_at, last_used_at
                ) VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb,
                    now() + $7::int * interval '1 second', $8, $9, now(), now())
                """,
                self.container_db_key,
                hash_val,
                client_id,
                user_id,
                _to_json_string(list(scope)),
                _to_json_string(list(resource)),
                int(ttl),
                rotated_from,
                auth_code_hash,
            )
        return raw_token

    async def rotate_refresh_token(self, *, old_refresh_raw, new_refresh_raw, client_id, scope, resource):
        oh = token_hash(old_refresh_raw)
        nh = token_hash(new_refresh_raw)
        ttl = app_settings["oauth"].get("refresh_token_ttl", 2592000)
        txn, conn = await self._connection()
        async with txn.lock:
            upd = await conn.fetchrow(
                """
                UPDATE oauth_refresh_tokens
                SET revoked_at = now(), replaced_by = $4
                WHERE container_db_key = $1
                  AND token_hash = $2
                  AND client_id = $3
                  AND revoked_at IS NULL
                  AND expires_at > now()
                RETURNING user_id, auth_code_hash
                """,
                self.container_db_key,
                oh,
                client_id,
                nh,
            )
            if upd is None:
                return False
            await conn.execute(
                """
                INSERT INTO oauth_refresh_tokens (
                    container_db_key, token_hash, client_id, user_id, scope, resource,
                    expires_at, rotated_from, auth_code_hash, created_at, last_used_at
                ) VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb,
                    now() + $7::int * interval '1 second', $8, $9, now(), now())
                """,
                self.container_db_key,
                nh,
                client_id,
                upd["user_id"],
                _to_json_string(list(scope)),
                _to_json_string(list(resource)),
                int(ttl),
                oh,
                upd["auth_code_hash"],
            )
        return True

    async def get_valid_refresh(self, token):
        txn, conn = await self._connection()
        async with txn.lock:
            row = await conn.fetchrow(
                """
                SELECT token_hash, client_id, user_id, scope, resource, expires_at,
                       rotated_from, auth_code_hash, created_at, last_used_at,
                       revoked_at, replaced_by
                FROM oauth_refresh_tokens
                WHERE container_db_key = $1
                  AND token_hash = $2
                  AND expires_at > now()
                  AND revoked_at IS NULL
                """,
                self.container_db_key,
                token_hash(token),
            )
        return _row_to_refresh(row)

    async def get_refresh_token(self, token):
        txn, conn = await self._connection()
        async with txn.lock:
            row = await conn.fetchrow(
                """
                SELECT token_hash, client_id, user_id, scope, resource, expires_at,
                       rotated_from, auth_code_hash, created_at, last_used_at,
                       revoked_at, replaced_by
                FROM oauth_refresh_tokens
                WHERE container_db_key = $1 AND token_hash = $2
                """,
                self.container_db_key,
                token_hash(token),
            )
        return _row_to_refresh(row)

    async def revoke_refresh_token(self, token):
        txn, conn = await self._connection()
        async with txn.lock:
            await conn.execute(
                """
                UPDATE oauth_refresh_tokens
                SET revoked_at = COALESCE(revoked_at, now())
                WHERE container_db_key = $1 AND token_hash = $2
                """,
                self.container_db_key,
                token_hash(token),
            )

    async def delete_container_data(self):
        txn, conn = await self._connection()
        async with txn.lock:
            await conn.execute(
                "DELETE FROM oauth_consents WHERE container_db_key = $1", self.container_db_key
            )
            await conn.execute(
                "DELETE FROM oauth_refresh_tokens WHERE container_db_key = $1", self.container_db_key
            )
            await conn.execute(
                "DELETE FROM oauth_authorization_codes WHERE container_db_key = $1", self.container_db_key
            )
            await conn.execute("DELETE FROM oauth_clients WHERE container_db_key = $1", self.container_db_key)


async def cleanup_expired(conn, batch_size=5000):
    await conn.execute("BEGIN")
    await conn.execute(
        """
        DELETE FROM oauth_authorization_codes
        WHERE (container_db_key, code_hash) IN (
            SELECT container_db_key, code_hash
            FROM oauth_authorization_codes
            WHERE expires_at < now()
            LIMIT $1
        )
        """,
        batch_size,
    )
    await conn.execute(
        """
        DELETE FROM oauth_refresh_tokens
        WHERE (container_db_key, token_hash) IN (
            SELECT container_db_key, token_hash
            FROM oauth_refresh_tokens
            WHERE expires_at < now()
            LIMIT $1
        )
        """,
        batch_size,
    )
    await conn.execute(
        """
        DELETE FROM oauth_consents
        WHERE (container_db_key, consent_key) IN (
            SELECT container_db_key, consent_key
            FROM oauth_consents
            WHERE expires_at IS NOT NULL AND expires_at < now()
            LIMIT $1
        )
        """,
        batch_size,
    )
    await conn.execute("COMMIT")
