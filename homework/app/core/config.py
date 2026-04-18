import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://user:admin@localhost:5432/webdev")
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
    JWT_SECRET = os.environ.get("JWT_SECRET", "supersecret")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 30
    
    GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")

settings = Settings()
