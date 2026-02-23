# Authentication Providers Reference

Complete reference for all 15 supported authentication providers with configuration examples.

## Quick Reference Table

| Provider      | Type   | Auth Flow    | Key Credentials                     |
|---------------|--------|--------------|-------------------------------------|
| Auth0         | OIDC   | OAuth 2.0    | client_id, client_secret            |
| AWS Cognito   | OIDC   | OAuth 2.0    | access_key_id, secret_access_key    |
| Azure         | OAuth  | OAuth 2.0    | client_id, client_secret, tenant_id |
| Debug         | Custom | Direct       | user_id, username                   |
| Descope       | OIDC   | OAuth 2.0    | project_id, public_key              |
| Discord       | OAuth  | OAuth 2.0    | client_id, client_secret            |
| GitHub        | OAuth  | OAuth 2.0    | client_id, client_secret            |
| Google        | OAuth  | OAuth 2.0    | client_id, client_secret            |
| In-Memory     | Custom | Direct       | users (dict)                        |
| Introspection | Token  | RFC 7662     | client_id, client_secret            |
| JWT           | Token  | Verification | secret_key, algorithm               |
| OCI           | OAuth  | Mutual TLS   | user_ocid, tenancy_ocid             |
| Scalekit      | OIDC   | OAuth 2.0    | client_id, client_secret            |
| Supabase      | OIDC   | OAuth 2.0    | project_url, api_key                |
| WorkOS        | OIDC   | OAuth 2.0    | api_key, client_id                  |

---

## 1. Auth0

### Description

Auth0 is a cloud-based identity platform providing OAuth 2.0 and OpenID Connect.

### Configuration Fields

```yaml
auth:
  auth0:
    domain: "https://your-tenant.auth0.com"
    client_id: "$AUTH0_CLIENT_ID"
    client_secret: "$AUTH0_CLIENT_SECRET"
    audience: "your-api-identifier"
    scopes:
      - openid
      - profile
      - email
    grant_type: "client_credentials"
```

### Environment Variables

```bash
export AUTH0_DOMAIN="https://your-tenant.auth0.com"
export AUTH0_CLIENT_ID="your-client-id"
export AUTH0_CLIENT_SECRET="your-client-secret"
```

### Setup Instructions

1. Go to Auth0 Dashboard → Applications
2. Create a new Regular Web Application
3. Note the Domain, Client ID, and Client Secret
4. Configure Application URIs with your redirect URL
5. Create an API and note the audience

### Notes

- Use `grant_type: "client_credentials"` for machine-to-machine authentication
- Scopes determine what information is requested from user
- Audience identifies the target API

---

## 2. AWS Cognito

### Description

Amazon Web Services (AWS) Cognito provides cloud-based user authentication and authorization.

### Configuration Fields

```yaml
auth:
  aws:
    access_key_id: "$AWS_ACCESS_KEY_ID"
    secret_access_key: "$AWS_SECRET_ACCESS_KEY"
    region: "$AWS_REGION"
    session_token: null
    role_arn: null
```

### Environment Variables

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"
```

### Setup Instructions

1. Create AWS IAM User with appropriate permissions
2. Generate Access Key and Secret Access Key
3. Note your AWS Region (us-east-1, eu-west-1, etc.)
4. (Optional) Create IAM Role and note ARN for cross-account access
5. (Optional) Generate Session Token for temporary credentials

### Notes

- Region must be a valid AWS region where Cognito is available
- session_token and role_arn are optional for standard setup
- session_token is used for temporary security credentials

---

## 3. Azure (Microsoft Entra)

### Description

Microsoft Azure / Microsoft Entra ID provides enterprise cloud-based authentication.

### Configuration Fields

```yaml
auth:
  azure:
    client_id: "$AZURE_CLIENT_ID"
    client_secret: "$AZURE_CLIENT_SECRET"
    tenant_id: "$AZURE_TENANT_ID"
    token_url: null
    issuer: null
    scopes:
      - "api://your-app-id/read"
```

### Environment Variables

```bash
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
```

### Setup Instructions

1. Go to Azure Portal → App registrations
2. Create a new app registration
3. Note Application (client) ID
4. Go to Certificates & Secrets → create Client Secret
5. Go to API permissions → Expose an API
6. Create custom scopes (e.g., "read", "write")
7. Note your Directory (tenant) ID

### Notes

- token_url defaults to Azure standard endpoint if not specified
- issuer defaults to tenant authority if not specified
- Scopes should be in format: "api://client-id/scope-name"
- Supports both single-tenant and multi-tenant configurations

---

## 4. Debug

### Description

Simple debug authentication for testing and development purposes.

### Configuration Fields

```yaml
auth:
  debug:
    user_id: "debug-user"
    username: "debug"
```

### Environment Variables

(No environment variables used - hardcoded for testing)

### Setup Instructions

1. No external setup required
2. Used for local testing and development
3. Accepts any token

### Notes

- **⚠️ SECURITY WARNING:** Never use in production
- Useful for testing authentication flow without external provider
- Bypasses all security checks

---

## 5. Descope

### Description

Descope provides authentication and authorization with support for Dynamic Client Registration.

### Configuration Fields

```yaml
auth:
  descope:
    project_id: "$DESCOPE_PROJECT_ID"
    public_key: "$DESCOPE_PUBLIC_KEY"
    scopes:
      - openid
      - profile
```

### Environment Variables

```bash
export DESCOPE_PROJECT_ID="your-project-id"
export DESCOPE_PUBLIC_KEY="your-public-key"
```

### Setup Instructions

1. Go to Descope Console
2. Create a new MCP Server project
3. Enable Dynamic Client Registration (DCR)
4. Note your Project ID
5. Download or copy your Public Key
6. Configure your Well-Known URL

### Notes

- Project ID format: "P..." (letters and numbers)
- Public key is used for JWT verification
- Supports DCR for dynamic client registration

---

## 6. Discord

### Description

Discord provides OAuth 2.0 authentication for Discord users.

### Configuration Fields

```yaml
auth:
  discord:
    client_id: "$DISCORD_CLIENT_ID"
    client_secret: "$DISCORD_CLIENT_SECRET"
    bot_token: "$DISCORD_BOT_TOKEN"
    scopes:
      - identify
      - email
    redirect_uri: "http://localhost:8000/auth/callback"
```

### Environment Variables

```bash
export DISCORD_CLIENT_ID="your-app-id"
export DISCORD_CLIENT_SECRET="your-client-secret"
export DISCORD_BOT_TOKEN="your-bot-token"
```

### Setup Instructions

1. Go to Discord Developer Portal → Applications
2. Create a new application
3. Go to OAuth2 → General
4. Note Client ID and Client Secret
5. Add redirect URI: `http://your-domain/auth/callback`
6. (Optional) Go to Bot → create bot token for bot_token

### Scopes

- `identify` - User ID and username
- `email` - User email address
- `guilds` - Access to user's guild list

### Notes

- bot_token is optional, used if you need Discord API access
- Redirect URI must match exactly in Discord application settings
- Default scopes usually sufficient for authentication only

---

## 7. GitHub

### Description

GitHub provides OAuth 2.0 authentication for GitHub users.

### Configuration Fields

```yaml
auth:
  github:
    client_id: "$GITHUB_CLIENT_ID"
    client_secret: "$GITHUB_CLIENT_SECRET"
    scopes:
      - "user:email"
    redirect_uri: "http://localhost:8000/auth/callback"
```

### Environment Variables

```bash
export GITHUB_CLIENT_ID="your-app-id"
export GITHUB_CLIENT_SECRET="your-client-secret"
```

### Setup Instructions

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create a new OAuth App
3. Note Client ID and Client Secret
4. Set Authorization callback URL: `http://your-domain/auth/callback`
5. Note your App ID

### Scopes

- `user:email` - Access to user email
- `read:user` - Access to user profile
- `repo` - Repository access (if needed)

### Notes

- `user:email` scope is recommended for getting user email
- Redirect URI must match exactly in GitHub OAuth App settings
- GitHub uses opaque tokens (not JWT)

---

## 8. Google

### Description

Google provides OAuth 2.0 and OpenID Connect for Google accounts.

### Configuration Fields

```yaml
auth:
  google:
    client_id: "$GOOGLE_CLIENT_ID"
    client_secret: "$GOOGLE_CLIENT_SECRET"
    project_id: "$GOOGLE_PROJECT_ID"
    scopes:
      - openid
      - email
      - profile
    redirect_uri: "http://localhost:8000/auth/callback"
```

### Environment Variables

```bash
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_PROJECT_ID="your-project-id"
```

### Setup Instructions

1. Go to Google Cloud Console → APIs & Services
2. Create a new project
3. Enable Google+ API
4. Create OAuth 2.0 credentials (Web application)
5. Add authorized redirect URI
6. Note Client ID, Client Secret, and Project ID

### Scopes

- `openid` - OpenID Connect scope
- `email` - User email
- `profile` - User profile information

### Notes

- Client ID ends with `.apps.googleusercontent.com`
- Project ID is the GCP project identifier
- redirect_uri should be registered in Google Cloud Console

---

## 9. In-Memory

### Description

Simple in-memory user store for testing and development.

### Configuration Fields

```yaml
auth:
  in_memory:
    users:
      user1: "password1"
      user2: "password2"
```

### Environment Variables

(No environment variables - credentials in config)

### Setup Instructions

1. Define users and passwords in config.yaml
2. No external service required
3. Completely local, no network calls

### Notes

- **⚠️ SECURITY WARNING:** Never use in production
- Passwords stored in plaintext in config file
- Useful for development and testing only
- All authentication happens locally

---

## 10. Introspection (OAuth 2.0 Token Introspection)

### Description

RFC 7662 Token Introspection for validating opaque OAuth tokens.

### Configuration Fields

```yaml
auth:
  introspection:
    introspection_url: "$TOKEN_INTROSPECTION_URL"
    client_id: "$TOKEN_INTROSPECTION_CLIENT_ID"
    client_secret: "$TOKEN_INTROSPECTION_CLIENT_SECRET"
```

### Environment Variables

```bash
export TOKEN_INTROSPECTION_URL="https://auth-server.com/oauth/introspect"
export TOKEN_INTROSPECTION_CLIENT_ID="your-client-id"
export TOKEN_INTROSPECTION_CLIENT_SECRET="your-client-secret"
```

### Setup Instructions

1. Identify your OAuth provider that supports RFC 7662
2. Register your application with the provider
3. Note the token introspection endpoint URL
4. Get your client credentials

### Supported Providers

- Auth0
- Okta
- Keycloak
- Any RFC 7662 compliant OAuth server

### Notes

- Used for validating opaque (non-JWT) tokens
- Requires network call for each token validation
- Client credentials authenticate to introspection endpoint

---

## 11. JWT

### Description

Direct JWT verification using shared secret or public key.

### Configuration Fields

```yaml
auth:
  jwt:
    secret_key: "$JWT_SECRET_KEY"
    algorithm: "HS256"
    issuer: null
    audience: null
```

### Environment Variables

```bash
export JWT_SECRET_KEY="your-secret-key-or-base64-encoded-key"
```

### Setup Instructions

1. Generate or obtain your JWT secret key
2. Note the algorithm used (HS256, RS256, etc.)
3. (Optional) Note issuer claim if validating
4. (Optional) Note audience claim if validating

### Algorithms

- `HS256` - HMAC with SHA-256 (symmetric, uses secret_key)
- `RS256` - RSA with SHA-256 (asymmetric, uses public key)
- Others: HS384, HS512, RS384, RS512, ES256, etc.

### Notes

- `issuer` and `audience` are optional validation claims
- For RS256, secret_key should be the public key
- Token must be a valid JWT with correct signature

---

## 12. OCI (Oracle Cloud Identity)

### Description

Oracle Cloud Infrastructure (OCI) authentication using API signing.

### Configuration Fields

```yaml
auth:
  oci:
    user_ocid: "$OCI_USER_OCID"
    tenancy_ocid: "$OCI_TENANCY_OCID"
    api_key: "$OCI_API_KEY"
    fingerprint: "$OCI_FINGERPRINT"
    region: "us-phoenix-1"
```

### Environment Variables

```bash
export OCI_USER_OCID="ocid1.user.oc1..."
export OCI_TENANCY_OCID="ocid1.tenancy.oc1..."
export OCI_API_KEY="-----BEGIN RSA PRIVATE KEY-----..."
export OCI_FINGERPRINT="xx:xx:xx:xx:xx:xx:xx:xx"
```

### Setup Instructions

1. Go to OCI Console → Users
2. Create or select a user
3. Go to API keys → Add API Key
4. Download private key and note fingerprint
5. Note your User OCID and Tenancy OCID
6. Note your OCI region (us-phoenix-1, us-ashburn-1, etc.)

### OCID Format

- User OCID: `ocid1.user.oc1...`
- Tenancy OCID: `ocid1.tenancy.oc1...`

### Regions

- us-phoenix-1 (Phoenix)
- us-ashburn-1 (Ashburn)
- eu-amsterdam-1 (Amsterdam)
- ap-tokyo-1 (Tokyo)
- And many more...

### Notes

- API key is an RSA private key (PEM format)
- Fingerprint is SHA256 hash of public key
- Uses mutual TLS certificate authentication

---

## 13. Scalekit

### Description

Scalekit provides enterprise SSO and SAML/OIDC authentication.

### Configuration Fields

```yaml
auth:
  scalekit:
    client_id: "$SCALEKIT_CLIENT_ID"
    client_secret: "$SCALEKIT_CLIENT_SECRET"
    environment_url: "$SCALEKIT_ENVIRONMENT_URL"
    scopes:
      - openid
      - profile
      - email
```

### Environment Variables

```bash
export SCALEKIT_CLIENT_ID="your-client-id"
export SCALEKIT_CLIENT_SECRET="your-client-secret"
export SCALEKIT_ENVIRONMENT_URL="https://api.scalekit.com"
```

### Setup Instructions

1. Go to Scalekit Dashboard
2. Create a new application
3. Note Client ID and Client Secret
4. Note your environment URL
5. Configure redirect URIs

### Scopes

- `openid` - OpenID Connect
- `profile` - User profile
- `email` - User email

### Notes

- Enterprise-focused SSO solution
- Supports SAML, OIDC, OAuth 2.0
- Multi-tenant friendly

---

## 14. Supabase

### Description

Supabase provides open-source PostgreSQL-based backend with built-in authentication.

### Configuration Fields

```yaml
auth:
  supabase:
    project_url: "$SUPABASE_PROJECT_URL"
    api_key: "$SUPABASE_API_KEY"
    scopes:
      - openid
      - profile
      - email
```

### Environment Variables

```bash
export SUPABASE_PROJECT_URL="https://your-project.supabase.co"
export SUPABASE_API_KEY="your-anon-or-service-key"
```

### Setup Instructions

1. Create a Supabase project at supabase.com
2. Go to Project Settings → API
3. Note Project URL
4. Note Anon Key (public, for frontend) or Service Key (for backend)
5. Enable providers you want (Google, GitHub, etc.)

### Key Types

- Anon Key - Public, for client-side auth
- Service Key - Private, for server-side operations

### Notes

- Includes PostgreSQL database
- Built-in user management
- Supports email, phone, OAuth providers
- Real-time capabilities

---

## 15. WorkOS

### Description

WorkOS provides enterprise SSO (Single Sign-On) with support for SAML, OAuth, and OIDC.

### Configuration Fields

```yaml
auth:
  workos:
    api_key: "$WORKOS_API_KEY"
    client_id: "$WORKOS_CLIENT_ID"
    organization_id: "$WORKOS_ORGANIZATION_ID"
    scopes:
      - openid
      - profile
      - email
```

### Environment Variables

```bash
export WORKOS_API_KEY="sk_test_xxxxx"
export WORKOS_CLIENT_ID="your-client-id"
export WORKOS_ORGANIZATION_ID="org_xxxxx"
```

### Setup Instructions

1. Go to WorkOS Dashboard
2. Create a new application
3. Note API Key (starts with sk_test_ or sk_live_)
4. Note Client ID
5. Create or note Organization ID
6. Configure redirect URIs

### Notes

- Enterprise-focused
- Supports multiple SSO protocols
- Organization-based access control
- Two API key types: test (sk_test_) and live (sk_live_)

---

## General Best Practices

### 1. Environment Variables

```bash
# Use strong, unique secrets
export AUTH_SECRET="$(openssl rand -base64 32)"

# Keep environment files secure
chmod 600 .env
echo ".env" >> .gitignore
```

### 2. Configuration File

```bash
# Never commit secrets to git
echo "data/config.yaml" >> .gitignore

# Encrypt sensitive config in production
# Use secrets manager (AWS Secrets Manager, Vault, etc.)
```

### 3. Development vs Production

```yaml
# Development
auth:
  debug:
    # ... debug config
  azure:
    # ... azure config

# Production (debug removed)
auth:
  azure:
    # ... azure config
  github:
    # ... github config
```

### 4. Testing

- Use Debug provider for unit tests
- Use In-Memory provider for integration tests
- Mock external OAuth calls in tests
- Never use production credentials in tests

---

## Troubleshooting

### Common Issues

**"Invalid credentials"**

- Verify environment variables are set correctly
- Check that secrets haven't expired or been rotated
- Ensure callback/redirect URIs match exactly

**"Scope not available"**

- Verify scopes are supported by the provider
- Check if you have permission to request those scopes
- Some scopes require additional app permissions

**"CORS or redirect URI mismatch"**

- Ensure redirect URI is registered exactly in provider console
- Protocol matters (http vs https)
- Port matters (localhost:8000 vs localhost:3000)

**"Token introspection failed"**

- Verify introspection endpoint URL is correct
- Check that client credentials are correct
- Ensure network connectivity to introspection endpoint

---

## Additional Resources

- [FastMCP Auth Documentation](https://github.com/jlowin/fastmcp/tree/main/src/fastmcp/server/auth)
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [OpenID Connect Spec](https://openid.net/specs/openid-connect-core-1_0.html)
- [Token Introspection RFC 7662](https://tools.ietf.org/html/rfc7662)
- [JWT Specification RFC 7519](https://tools.ietf.org/html/rfc7519)


