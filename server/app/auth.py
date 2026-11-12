"""One switch for auth: MCP_AUTH = none | static | jwt.

- none:   no auth. Fine for stdio (the spec says stdio servers take credentials
          from the environment) and for local HTTP dev.
- static: one shared bearer token. Dev and internal use only.
- jwt:    verify bearer JWTs issued by your identity provider, via its JWKS
          endpoint (or a PEM public key). Works with Supabase, Auth0, Clerk,
          WorkOS, Cognito, Keycloak... anything that signs JWTs.

If MCP_AUTH_SERVERS is set, the JWT verifier is wrapped so the server
publishes OAuth 2.0 Protected Resource Metadata (RFC 9728), which the MCP
authorization spec requires for HTTP servers that use OAuth.
"""

from __future__ import annotations

from fastmcp.server.auth import AuthProvider, RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier, StaticTokenVerifier

from .settings import Settings

DEV_CLIENT_ID = "dev-token"


def build_auth(settings: Settings) -> AuthProvider | None:
    if settings.auth == "none":
        return None

    if settings.auth == "static":
        assert settings.dev_token  # validated in Settings
        return StaticTokenVerifier(
            tokens={
                settings.dev_token: {
                    "client_id": DEV_CLIENT_ID,
                    "scopes": [settings.write_scope, *settings.required_scopes],
                }
            },
            required_scopes=settings.required_scopes or None,
        )

    verifier = JWTVerifier(
        jwks_uri=settings.jwt_jwks_uri,
        public_key=settings.jwt_public_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        algorithm=settings.jwt_algorithm,
        required_scopes=settings.required_scopes or None,
        base_url=settings.base_url,
    )
    if settings.auth_servers:
        assert settings.base_url  # validated in Settings
        return RemoteAuthProvider(
            token_verifier=verifier,
            authorization_servers=settings.auth_servers,
            base_url=settings.base_url,
            scopes_supported=sorted({settings.write_scope, *settings.required_scopes}),
            resource_name=settings.name,
        )
    return verifier
