import httpx2
import math
from app.config import settings
from app.dependencies import get_db, get_current_user
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentResponse
from app.services import get_post_by_id
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

comment_router = APIRouter()

async def notify_comment_created(data):
    try:
        async with httpx2.AsyncClient(timeout=5.0) as client:
            response = await client.post(settings.WEBHOOK_URL, json= data)
            if response.status_code >= 400:
                print(f"Webhook rejected: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Webhook delivery failed: {e}")

@comment_router.post('/posts/{post_id}/comments', response_model = CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    post_id, payload: CommentCreate, 
    background_tasks: BackgroundTasks,
    db: Session =Depends(get_db), 
    current_user=Depends(get_current_user)
):
    if not get_post_by_id(db, post_id=post_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail= "Post not found")
    new_comment = Comment(
        body = payload.body,
        author_id = current_user.id,
        post_id = post_id
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    comment_data = CommentResponse.model_validate(new_comment).model_dump(mode="json")
    background_tasks.add_task(notify_comment_created, comment_data)
    return new_comment

@comment_router.get('/posts/{post_id}/comments')
def get_all_comments(post_id, page: int = 1, limit: int = 20, db: Session = Depends(get_db)):
    post = get_post_by_id(db, post_id=post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail= "Post not found")
    
    limit, page = max(limit, 1), max(page, 1)
    limit = min(limit, 120)
    offset = (page-1) * limit

    comments = db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at.desc()).offset(offset).limit(limit).all()
    total_comments = db.query(func.count(Comment.id)).filter(Comment.id == post_id).scalar()
    total_pages = math.ceil(total_comments/ limit) if total_comments > 0 else 1

    return {
        "page": page,
        "limit" : limit,
        "total_comments" : total_comments,
        "total_pages" : total_pages,
        "results" : comments
    }
