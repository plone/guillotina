OAUTH_DDL = [
    """
CREATE TABLE IF NOT EXISTS oauth_clients (
    container_db_key text NOT NULL,
    client_id text NOT NULL,
    client_name text NOT NULL,
    redirect_uris jsonb NOT NULL DEFAULT '[]',
    grant_types jsonb NOT NULL DEFAULT '[]',
    response_types jsonb NOT NULL DEFAULT '[]',
    scope text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (container_db_key, client_id)
)
""",
    """
CREATE TABLE IF NOT EXISTS oauth_authorization_codes (
    container_db_key text NOT NULL,
    code_hash text NOT NULL,
    client_id text NOT NULL,
    user_id text NOT NULL,
    redirect_uri text NOT NULL,
    scope jsonb NOT NULL DEFAULT '[]',
    resource jsonb NOT NULL DEFAULT '[]',
    code_challenge text,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (container_db_key, code_hash)
)
""",
    """
CREATE INDEX IF NOT EXISTS oauth_codes_expires_idx
    ON oauth_authorization_codes (expires_at)
""",
    """
CREATE TABLE IF NOT EXISTS oauth_refresh_tokens (
    container_db_key text NOT NULL,
    token_hash text NOT NULL,
    client_id text NOT NULL,
    user_id text NOT NULL,
    scope jsonb NOT NULL DEFAULT '[]',
    resource jsonb NOT NULL DEFAULT '[]',
    expires_at timestamptz NOT NULL,
    rotated_from text,
    auth_code_hash text,
    revoked_at timestamptz,
    replaced_by text,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_used_at timestamptz,
    PRIMARY KEY (container_db_key, token_hash)
)
""",
    """
CREATE INDEX IF NOT EXISTS oauth_refresh_expires_idx
    ON oauth_refresh_tokens (expires_at)
""",
    """
CREATE INDEX IF NOT EXISTS oauth_refresh_auth_code_idx
    ON oauth_refresh_tokens (container_db_key, auth_code_hash)
    WHERE auth_code_hash IS NOT NULL
""",
    """
ALTER TABLE oauth_refresh_tokens ADD COLUMN IF NOT EXISTS revoked_at timestamptz
""",
    """
ALTER TABLE oauth_refresh_tokens ADD COLUMN IF NOT EXISTS replaced_by text
""",
    """
CREATE TABLE IF NOT EXISTS oauth_consents (
    container_db_key text NOT NULL,
    consent_key text NOT NULL,
    user_id text NOT NULL,
    client_id text NOT NULL,
    scope jsonb NOT NULL DEFAULT '[]',
    resource jsonb NOT NULL DEFAULT '[]',
    granted_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz,
    PRIMARY KEY (container_db_key, consent_key)
)
""",
    """
ALTER TABLE oauth_consents ADD COLUMN IF NOT EXISTS expires_at timestamptz
""",
    """
CREATE INDEX IF NOT EXISTS oauth_consents_user_idx
    ON oauth_consents (container_db_key, user_id)
""",
    """
CREATE INDEX IF NOT EXISTS oauth_consents_expires_idx
    ON oauth_consents (expires_at)
    WHERE expires_at IS NOT NULL
""",
]
