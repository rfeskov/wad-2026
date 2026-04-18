# FastAPI LLM Chat Application

A complete web application using FastAPI, PostgreSQL, Redis, and llama-cpp-python, built with an MVC architecture returning server-rendered HTML (Jinja2). It includes secure JWT authentication, GitHub OAuth, and real-time streaming of local LLM responses.

## Setup Instructions

1. Start infrastructure services (PostgreSQL and Redis) using docker-compose:
```bash
docker-compose up -d
```

2. Create a `.env` file and set up necessary variables:
```
DATABASE_URL=postgresql+asyncpg://user:admin@localhost:5432/webdev
REDIS_URL=redis://localhost:6379
JWT_SECRET=yoursecret
GITHUB_CLIENT_ID=your_id
GITHUB_CLIENT_SECRET=your_secret
```

3. Install requirements (in your virtual environment):
```bash
pip install -r requirements.txt
pip install greenlet asyncpg alembic
```

4. Run the database migrations:
```bash
alembic upgrade head
```

5. Add your `model.gguf` for local LLM inference to the project root directory.

6. Start the uvicorn server:
```bash
uvicorn app.main:app --reload
```

Then visit http://localhost:8000.
