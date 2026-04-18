from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

import httpx

from app.database import get_db
from app.models.models import User
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.dependencies import get_current_user_optional, get_current_user
from app.services.auth import create_refresh_token, verify_refresh_token, delete_refresh_token
from app.core.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        samesite="lax"
    )

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    if result.scalars().first():
        return templates.TemplateResponse("register.html", {"request": request, "error": "Email already registered"})
        
    user = User(
        email=email,
        password_hash=get_password_hash(password)
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return templates.TemplateResponse("register.html", {"request": request, "error": "Error creating user"})
        
    return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
        
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = await create_refresh_token(user.id)
    
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookies(response, access_token, refresh_token)
    return response

@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    refresh_token_cookie = request.cookies.get("refresh_token")
    if not refresh_token_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")
        
    user_id = await verify_refresh_token(refresh_token_cookie)
    access_token = create_access_token(data={"sub": str(user_id)})
    
    # We do not rotate refresh token here, but could if we want strictly 1-time use
    set_auth_cookies(response, access_token, refresh_token_cookie)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/logout")
async def logout(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await delete_refresh_token(refresh_token)
        
    response = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response

# GitHub OAuth
@router.get("/github/login")
async def github_login():
    github_auth_url = f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&scope=user"
    return RedirectResponse(url=github_auth_url)

@router.get("/github/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    if not code:
        raise HTTPException(status_code=400, detail="Code missing from GitHub callback")
        
    async with httpx.AsyncClient() as client:
        # 1. Exchange code for access token
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
        )
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get GitHub access token")
            
        # 2. Get user profile
        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_data = user_response.json()
        github_id = str(user_data.get("id"))
        email = user_data.get("email") # Could be null if private
        
        if not github_id:
            raise HTTPException(status_code=400, detail="Failed to get GitHub user profile")
            
    # 3. Find or create user
    stmt = select(User).where(User.github_id == github_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        # If GitHub email is duplicate with password account but not linked, we should handle error.
        # Simplifying here by just trying to set it.
        user = User(github_id=github_id, email=email)
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="Email already registered with another account")
            
    # 4. Login the user
    app_access_token = create_access_token(data={"sub": str(user.id)})
    app_refresh_token = await create_refresh_token(user.id)
    
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    set_auth_cookies(response, app_access_token, app_refresh_token)
    return response
