from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.controllers.auth import router as auth_router
from app.controllers.chat import router as chat_router
from app.core.dependencies import get_current_user_optional
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import User

app = FastAPI(title="LLM Chat App")

templates = Jinja2Templates(directory="app/templates")

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])

@app.get("/", response_class=HTMLResponse)
async def render_home(request: Request, user: User = Depends(get_current_user_optional), db: AsyncSession = Depends(get_db)):
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    from sqlalchemy.orm import selectinload
    from sqlalchemy.future import select
    stmt = select(User).where(User.id == user.id).options(selectinload(User.chats))
    result = await db.execute(stmt)
    user_with_chats = result.scalars().first()
    return templates.TemplateResponse("index.html", {"request": request, "user": user_with_chats})

@app.on_event("startup")
async def startup_event():
    print("Application styling.")
