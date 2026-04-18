## Plan: FastAPI LLM Chat Application

A complete web application using FastAPI, PostgreSQL, Redis, and llama-cpp-python, built with an MVC architecture returning server-rendered HTML (Jinja2). It includes secure JWT authentication, GitHub OAuth, and real-time streaming of local LLM responses.

**Steps**

*Phase 1: Project Setup & Infrastructure*
1. Initialize the FastAPI application structure in `homework/app/`.
2. Configure Docker Compose for PostgreSQL and Redis services (can borrow from lesson examples).
3. Setup Alembic for database migrations.

*Phase 2: Data Layer (Models)*
4. Define SQLAlchemy models for `User` (id, email, password_hash, github_id), `Chat` (id, user_id, title, created_at), and `Message` (id, chat_id, role, content, created_at).
5. Generate initial Alembic migration for these models.

*Phase 3: Authentication System*
6. Implement password hashing (e.g., passlib/bcrypt).
7. Implement JWT utility for generating access tokens.
8. Implement Redis session storage for storing refresh tokens (30-day TTL).
9. Implement GitHub OAuth login flow.

*Phase 4: Core Logic & LLM Integration*
10. Encapsulate the `llama-cpp-python` logic into an LLM service class, supporting streaming mode.
11. Implement a Chat caching layer in Redis to store recent message history and reduce database read loads.

*Phase 5: API & Web Controllers*
12. Create Auth controller endpoints (Register, Login, OAuth callback, Logout) returning templates or redirects.
13. Create Chat controller endpoints (List chats, Create chat, View chat).
14. Create an endpoint for receiving a user message and returning a StreamingResponse connected to the LLM generator (for the streaming bonus).

*Phase 6: Frontend Views (Jinja2)*
15. Create base layout template (`base.html`).
16. Create authentication templates (`login.html`, `register.html`).
17. Create chat dashboard and chat session templates.
18. Implement vanilla JavaScript in the chat template to handle Server-Sent Events (SSE) or chunked streams for the LLM output.

*Phase 7: Deliverables*
19. Finalize `README.md` with setup instructions.
20. Prepare the required PDF report (API structure, MVC explanation, UI screenshots, ERD).

**Relevant files**
- [requirements.txt](homework/requirements.txt) — Needs updates for SQLAlchemy, asyncpg, passlib, python-jose, httpx (for OAuth).
- `homework/app/database.py` — SQLAlchemy and Redis engine configurations.
- `homework/app/models/` — SQLAlchemy domain models.
- `homework/app/controllers/` — FastAPI routers (auth, chat).
- `homework/app/services/llm.py` — Encapsulation of logic from [base.py](homework/base.py) / [streaming.py](homework/streaming.py).
- `homework/app/templates/` — Jinja2 HTML templates.

**Verification**
1. Run `docker-compose up` to verify DB and Redis start cleanly.
2. Run Alembic migrations and inspect the Postgres schema.
3. Test a full user registration and login flow (verify JWT access token in cookies/headers and refresh token in Redis).
4. Create a chat, send a message, and verify that the LLM streaming response displays incrementally in the browser.
5. Verify chat history persists across server restarts (fetching from DB/Cache).

**Decisions**
- **Architecture**: **MVC**. FastAPI routes act as Controllers serving `Jinja2` Views.
- **Database**: PostgreSQL with async driver (`asyncpg`) and `SQLAlchemy`.
- **LLM Prompting**: Minimal stateless prompting per request as allowed, retrieving recent messages from Redis cache for memory context.
- **Streaming UI**: The chat view will use fetch API or EventSource in JS to read the stream from a FastAPI `StreamingResponse`.

**Further Considerations**
1. Do you want to use frontend CSS frameworks like Bootstrap or Tailwind via CDN to quickly make the UI look presentable for the screenshots?
2. Should the LLM model file (`model.gguf`) be placed in a specific shared volume or downloaded dynamically?