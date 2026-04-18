# Chat MVP - Technical Report

## Architecture
- **Frontend Mode:** Server-rendered HTML HTML (MVC pattern).
- **Explanation:** Routes on backend FastAPI code map exactly to HTML templates via Jinja2 engine, returning text/html rendering the logic directly avoiding single-page REST interactions. The only exception was streaming response for token completion.
- **JWT & Redis interaction**: When a user connects to GitHub or standard login it creates an access token via HS256 algorithm securely held server memory logic via dependency injection `get_current_user`, whilst pushing UUID-driven refresh tokens mapped strictly inside Redis to enforce simple yet exact log-outs. 

## Code Structure
- **app/core:** Contains environment values settings, cryptographic operations (`security.py`), and FastAPI user resolution `dependencies.py`
- **app/database:** Global asyncpg session-maker singleton and base metadata declaratives
- **app/controllers:** Routes mappings separating isolated concepts (AUTH vs CHAT mechanics).  
- **app/models:** Standard structured DB models
- **app/services:** `auth.py` containing redis communication logic and `llm.py` wrapping llama-cpp-python in thread-safe generation for streaming output.
- **app/templates:** HTML Views mapped by UI controllers

## Database & Redis Models structure
* Postgres
  - Users: `[id: int(PK), email: str(U), password_hash: str, github_id: str(U)]`
  - Chats: `[id: int(PK), user_id: int(FK), title: str, created_at: dt]` 
  - Messages: `[id: int(PK), chat_id: int(FK), role: str, content: str, created_at: dt]`

* Redis:
  - Tokens: `refresh_token:<string-uuid> -> string(user_id)`
  - Chat Cache: `chat_history:<integer-id> -> array(dict(role, content))`

## API Structure:
- `GET /` -> Redirect to login or show index.html
- `POST /auth/register` -> Form registering
- `POST /auth/login` -> Form logic issuing JWT + Redis creation mapped via http-only cookies
- `GET /auth/github/login` -> Intercept GitHub
- `GET /auth/github/callback` -> Redirect URI handler
- `POST /chat/new` -> Inserts new grouping row in database and redirects HTML scope
- `POST /chat/{id}/message` -> Generator based endpoint parsing Redis cache + Database storing -> yielding SSE protocol events to Vanilla JS connection.
