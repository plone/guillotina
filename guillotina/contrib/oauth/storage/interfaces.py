from zope.interface import Interface


class IOAuthStore(Interface):
    """Persistent OAuth state for a single container.

    Implementations must scope all data by the database-qualified container key
    passed to ``__init__``.
    All methods are async. Record dict shapes returned by read methods:

    - **client**: ``client_id``, ``client_name``, ``redirect_uris``, ``grant_types``,
      ``response_types``, ``token_endpoint_auth_method``, ``scope``, ``created_at``,
      ``updated_at``
    - **code**: ``code_hash``, ``client_id``, ``user_id``, ``redirect_uri``, ``scope``,
      ``resource``, ``code_challenge``, ``code_challenge_method``, ``expires_at``,
      ``created_at``
    - **refresh**: ``token_hash``, ``client_id``, ``user_id``, ``scope``, ``resource``,
      ``expires_at``, ``rotated_from``, ``auth_code_hash``, ``created_at``, ``last_used_at``,
      optional ``revoked_at``, ``replaced_by``
    """

    def get_client(self, client_id):
        """Return a client record or ``None``."""

    def create_client(self, client):
        """Create a dynamically registered client."""

    def has_consent(self, consent_key):
        """Return whether the user already granted (and not-yet-expired) consent for this key."""

    def create_consent(self, consent_key, *, user_id, client_id, scope, resource):
        """Persist a consent decision, refreshing its expiry on re-grant."""

    def list_consents(self, user_id):
        """Return the user's active (unexpired) consent records (newest first)."""

    def delete_consent(self, consent_key, *, user_id=None):
        """Delete a consent (optionally scoped to ``user_id``). Return ``True`` if removed."""

    def revoke_user_client_refresh_tokens(self, *, user_id, client_id):
        """Revoke every refresh token a user holds for a client. Return ``True`` if any changed."""

    def create_code(self, *, raw_code, client_id, user_id, redirect_uri, scope, resource, code_challenge):
        """Store a new authorization code and return its record."""

    def get_active_code(self, code):
        """Return a valid, unexpired authorization code record or ``None``."""

    def consume_code(self, code):
        """Atomically return and delete an unexpired code, or ``None`` if unavailable."""

    def delete_code(self, code_hash_val):
        """Remove an authorization code after use or cleanup."""

    def revoke_refresh_tokens_by_auth_code(self, auth_code_hash):
        """Revoke refresh tokens issued from a code; return ``True`` if any were changed."""

    def create_refresh_token(
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
        """Store a refresh token and return the opaque token string."""

    def rotate_refresh_token(self, *, old_refresh_raw, new_refresh_raw, client_id, scope, resource):
        """Mark ``old_refresh_raw`` revoked and persist ``new_refresh_raw``. Return ``False`` if not rotatable."""

    def revoke_refresh_family_for_reuse(self, *, client_id, user_id, auth_code_hash):
        """Revoke all refresh tokens in the reuse-compromise rotation family."""

    def revoke_refresh_family(self, *, client_id, user_id, auth_code_hash):
        """Revoke all refresh tokens in one authorization grant family."""

    def get_valid_refresh(self, token):
        """Return a valid, unexpired refresh token record or ``None``."""

    def get_refresh_token(self, token):
        """Return a refresh token record regardless of expiry, or ``None``."""

    def revoke_refresh_token(self, token):
        """Revoke a refresh token without removing its replay-detection record."""

    def delete_container_data(self):
        """Remove all OAuth state for this container (addon uninstall)."""
