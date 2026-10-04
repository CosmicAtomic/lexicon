# Lexicon

Lexicon is a versioned blogging platform API built with FastAPI. It provides user registration, two authentication strategies, post and comment management, pagination and filtering, rate limiting, idempotent post creation, and asynchronous comment webhook notifications.

The API is exposed under the `/v1` prefix, while the health endpoint remains available at `/health`.

See [performance/PERFORMANCE.md](performance/PERFORMANCE.md) for load/stress testing results.

## Features

- User signup with unique email and username validation.
- JWT bearer-token authentication.
- Cookie-based session authentication with CSRF protection for logout.
- Argon2 password hashing through `pwdlib`.
- Authenticated post creation, update, and deletion with author ownership checks.
- Public post retrieval with page-based pagination, cursor pagination, date filters, author filters, and sorting.
- Authenticated comment creation and public comment listing.
- Background webhook notification after a comment is created.
- Per-client authentication rate limiting: 5 login attempts per minute.
- Optional 24-hour idempotency caching for post creation.
- SQLAlchemy models with Alembic migrations.
- Automated pytest coverage for unit, integration, end-to-end, auth, CSRF, rate-limit, and idempotency behavior.

## Technology Stack

- Python
- FastAPI and Starlette
- Pydantic v2 and `pydantic-settings`
- SQLAlchemy 2
- PostgreSQL with `psycopg`
- Alembic
- PyJWT
- `pwdlib` with Argon2
- SlowAPI
- pytest and pytest-asyncio
- Locust for load and stress testing
- Schemathesis for OpenAPI contract testing

## Project Structure

```text
.
├── app/
│   ├── auth/             # JWT and session authentication routes
│   ├── models/           # SQLAlchemy database models
│   ├── routes/           # Post and comment endpoints
│   ├── schemas/          # Request and response validation models
│   ├── config.py         # Environment-backed application settings
│   ├── database.py       # SQLAlchemy engine, sessions, and Base
│   ├── dependencies.py   # DB, auth, CSRF, and idempotency dependencies
│   ├── limiter.py        # SlowAPI rate limiter
│   ├── security.py       # Password, JWT, and CSRF helpers
│   └── main.py           # FastAPI application assembly
├── alembic/              # Database migration configuration and revisions
├── performance/         # Locust, Schemathesis, and performance notes
├── tests/                # Automated test suite
├── alembic.ini
├── requirements.txt
└── pytest.ini
```

## Requirements

- Python 3.10 or newer
- PostgreSQL for normal application operation
- A database created for Lexicon

The test suite uses a local SQLite database defined in `tests/conftest.py`, so PostgreSQL is not required to run the automated tests when the Python dependencies are installed.

## Installation

Create and activate a virtual environment, then install the pinned dependencies.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root. `.env` is ignored by Git and must not be committed.

```env
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/lexicon
JWT_SECRET_KEY=replace-with-a-long-random-jwt-secret
SESSION_SECRET_KEY=replace-with-a-long-random-session-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SESSION_EXPIRE_MINUTES=30
WEBHOOK_URL=https://example.com/webhooks/comments
```

`ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, and `SESSION_EXPIRE_MINUTES` have defaults in the application settings, but defining them explicitly makes deployments easier to audit. `WEBHOOK_URL` is required because it is used by the comment notification task.

Generate strong secrets rather than using the example values. On Windows PowerShell, a quick option is:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Database Setup

Apply the existing Alembic migrations from the project root:

```bash
alembic upgrade head
```

The current schema contains:

- `users`: UUID identity, email, username, optional OAuth provider IDs, and hashed password.
- `posts`: UUID identity, author, title, body, and creation timestamp.
- `comments`: UUID identity, post, author, body, and creation timestamp.

Posts and comments use cascading foreign keys when their author or parent post is deleted.

## Running the API

Start the development server from the project root:

```bash
uvicorn app.main:app --reload
```

The API is then available at `http://localhost:8000`.

FastAPI's interactive documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI schema: `http://localhost:8000/openapi.json`

Health check:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{ "message": "Application running successfully" }
```

## API Reference

All paths below include the `/v1` prefix.

### Authentication and Users

| Method | Path                   | Auth                         | Description                              |
| ------ | ---------------------- | ---------------------------- | ---------------------------------------- |
| `POST` | `/auth/signup`         | Public                       | Create a user. Returns `201 Created`.    |
| `POST` | `/auth/jwt/login`      | Public                       | Validate credentials and return a JWT.   |
| `GET`  | `/auth/jwt/me`         | Bearer token                 | Return the authenticated JWT user.       |
| `POST` | `/auth/session/login`  | Public                       | Create a cookie session and CSRF cookie. |
| `GET`  | `/auth/session/me`     | Session cookie               | Return the authenticated session user.   |
| `POST` | `/auth/session/logout` | Session cookie + CSRF header | Delete the session and both cookies.     |

Signup and login payloads use this shape:

```json
{
  "email": "writer@example.com",
  "username": "writer",
  "password": "strong-password"
}
```

JWT login returns:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Use the token on protected requests:

```http
Authorization: Bearer <jwt>
```

Session login sets an HTTP-only `session_id` cookie and a readable `csrfToken` cookie. For logout, send the CSRF cookie value in `X-CSRF-Token`:

```http
X-CSRF-Token: <csrfToken>
```

### Posts

| Method   | Path               | Auth         | Description                                       |
| -------- | ------------------ | ------------ | ------------------------------------------------- |
| `POST`   | `/posts`           | Bearer token | Create a post.                                    |
| `GET`    | `/posts`           | Public       | List posts with pagination, filters, and sorting. |
| `GET`    | `/posts/{post_id}` | Public       | Retrieve one post.                                |
| `PUT`    | `/posts/{post_id}` | Bearer token | Update a post owned by the current user.          |
| `DELETE` | `/posts/{post_id}` | Bearer token | Delete a post owned by the current user.          |

Create payload:

```json
{
  "title": "My first post",
  "body": "Published from Lexicon."
}
```

The optional `Idempotency-Key` header can be used on `POST /v1/posts`. Repeating the same key for the same authenticated user within 24 hours returns the cached response without creating a second post.

Post list query parameters:

| Parameter          | Description                                                 |
| ------------------ | ----------------------------------------------------------- |
| `page`             | Page number, minimum 1. Defaults to `1`.                    |
| `limit`            | Page size, clamped to 1-100. Defaults to `10`.              |
| `cursor_timestamp` | Cursor timestamp; must be supplied with `cursor_id`.        |
| `cursor_id`        | Cursor post UUID; must be supplied with `cursor_timestamp`. |
| `date_from`        | Include posts created at or after this timestamp.           |
| `date_to`          | Include posts created at or before this timestamp.          |
| `author_id`        | Filter posts by author UUID.                                |
| `sort_by`          | `created_at` or `title`.                                    |
| `order`            | `asc` or `desc`; defaults to `desc`.                        |

By default, posts are returned newest first. Cursor pagination is used for descending `created_at` queries when both cursor values are supplied; other combinations use page/offset pagination.

### Comments

| Method | Path                        | Auth         | Description                           |
| ------ | --------------------------- | ------------ | ------------------------------------- |
| `POST` | `/posts/{post_id}/comments` | Bearer token | Create a comment on an existing post. |
| `GET`  | `/posts/{post_id}/comments` | Public       | List comments for an existing post.   |

Comment list parameters are `page` and `limit`. The limit is clamped to 1-120 and comments are returned newest first.

After a successful comment creation, Lexicon sends the serialized comment to `WEBHOOK_URL` as a background task. Webhook delivery failures are logged and do not undo the already-committed comment.

## Error Responses and Limits

- `400 Bad Request`: invalid request or duplicate email/username.
- `401 Unauthorized`: missing, invalid, expired, or incorrect authentication.
- `403 Forbidden`: failed CSRF validation or an ownership violation.
- `404 Not Found`: requested post or parent resource does not exist.
- `429 Too Many Requests`: the authentication rate limit was exceeded.

JWT and session login endpoints are limited to 5 requests per minute per remote address. This limiter is intended to reduce credential-guessing traffic; failed login attempts still consume the limit.

## Testing

Run the full automated suite from the project root:

```bash
pytest
```

The tests cover:

- Health checks and signup validation.
- Password hashing and duplicate identity rejection.
- JWT login, protected routes, invalid tokens, and expiration.
- Session creation, expiration, logout, and CSRF failures.
- Post creation, retrieval, pagination, filtering, and idempotency.
- Comment creation and webhook dispatch.
- Authentication rate-limit behavior.
- A complete signup-to-comment end-to-end flow.

## Performance and Contract Testing

Start the API before running the performance tools.

### Locust

```bash
locust -f performance/locustfile.py --host http://localhost:8000
```

The Locust scenario exercises JWT login and post listing. Authentication traffic is intentionally rate limited, so login failures at higher concurrency are expected `429` responses rather than necessarily application failures.

### Schemathesis

The hook prepares test credentials and adds JWT or session/CSRF authentication to generated cases:

```bash
set SCHEMATHESIS_HOOKS=performance/schemathesis_hook.py
schemathesis run http://localhost:8000/openapi.json --exclude-path="/session/logout" --checks=not_a_server_error,response_schema_conformance
```

For PowerShell, use `$env:SCHEMATHESIS_HOOKS = "performance/schemathesis_hook.py"` instead of `set`.

See [performance/PERFORMANCE.md](performance/PERFORMANCE.md) for the recorded load and stress results, known bottlenecks, test limitations, and recommendations.

## Current Implementation Notes

- Session records and idempotency records are stored in process memory. They are lost on restart and are not shared across workers, so a production deployment should move them to a shared store such as Redis.
- The default session middleware and session cookies are configured for local development (`https_only=False` and `secure=False`). HTTPS and secure cookie settings should be enabled before production deployment.
- The performance report records Windows-specific socket and connection-pool ceilings. Its benchmark values are approximate and should be repeated in the target deployment environment.
- `origins` is currently empty in `app/main.py`; add the deployed frontend origin before making browser-based cross-origin requests.
- `WEBHOOK_URL` must point to a reachable receiver in an environment where comment notifications are expected.

## Project Origin

Built as an implementation of [Bloggin Platform API from roadmap.sh](https://roadmap.sh/projects/blogging-platform-api).
