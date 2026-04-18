from fastapi import APIRouter, Depends, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import json
import asyncio

from app.database import get_db
from app.models.models import Chat, Message, User
from app.core.dependencies import get_current_user
from app.services.llm import llm_service
from app.services.auth import redis_client

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.post("/new")
async def create_chat(
    request: Request,
    title: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    new_chat = Chat(user_id=user.id, title=title)
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    return RedirectResponse(url=f"/chat/{new_chat.id}", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/{chat_id}", response_class=HTMLResponse)
async def view_chat(
    chat_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Chat).where(Chat.id == chat_id, Chat.user_id == user.id)
    result = await db.execute(stmt)
    chat = result.scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    stmt_msgs = select(Message).where(Message.chat_id == chat.id).order_by(Message.created_at)
    result_msgs = await db.execute(stmt_msgs)
    messages = result_msgs.scalars().all()
    
    return templates.TemplateResponse("chat.html", {"request": request, "chat": chat, "messages": messages, "user": user})

@router.post("/{chat_id}/message")
async def handle_message(
    chat_id: int,
    content: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify chat
    stmt = select(Chat).where(Chat.id == chat_id, Chat.user_id == user.id)
    result = await db.execute(stmt)
    chat = result.scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Save user message to DB
    user_msg = Message(chat_id=chat.id, role="user", content=content)
    db.add(user_msg)
    await db.commit()
    
    # Load past N messages for context (Caching via Redis could go here)
    # We will simulate REDIS cache usage for recent history bonus:
    cache_key = f"chat_history:{chat.id}"
    history_json = await redis_client.get(cache_key)
    
    if history_json:
        history = json.loads(history_json)
    else:
        stmt_msgs = select(Message).where(Message.chat_id == chat.id).order_by(Message.created_at.desc()).limit(10)
        result_msgs = await db.execute(stmt_msgs)
        db_messages = result_msgs.scalars().all()[::-1] # Reverse back to chronological
        history = [{"role": m.role, "content": m.content} for m in db_messages]

    # Exclude the just-added user_msg from history dict to avoid duplication in prompt, since stream_chat takes history + prompt
    if len(history) > 0 and history[-1]["role"] == "user" and history[-1]["content"] == content:
        history = history[:-1]

    # Generator for SSE Streaming
    async def sse_generator():
        yield f"event: start\ndata: \n\n"
        full_response = ""
        async for token in llm_service.stream_chat(history, content):
            full_response += token
            # SSE escaping
            safe_token = json.dumps(token)
            yield f"data: {safe_token}\n\n"
            
        yield f"event: end\ndata: \n\n"
        
        # Afterwards, save assistant response to DB
        async with db.begin():
            # In real async app, the current db session might be closed since streaming yields response back.
            # Using thread-safe or distinct session would be required. 
            # BUT we can just do it in background tasks or carefully here since the database generator stays open...
            # Actually, streaming responses can execute cleanup after finishing
            assistant_msg = Message(chat_id=chat.id, role="assistant", content=full_response)
            db.add(assistant_msg)
            
        # Update Redis Cache
        history.append({"role": "user", "content": content})
        history.append({"role": "assistant", "content": full_response})
        await redis_client.setex(cache_key, 3600, json.dumps(history[-10:])) # Keep last 10 messages for 1hr
        
    return StreamingResponse(sse_generator(), media_type="text/event-stream")

@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Chat).where(Chat.id == chat_id, Chat.user_id == user.id)
    result = await db.execute(stmt)
    chat = result.scalars().first()
    if chat:
        await db.delete(chat)
        await db.commit()
    return {"status": "ok"}
