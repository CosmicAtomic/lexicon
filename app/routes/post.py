import math
from app.dependencies import get_current_user, get_db
from app.models.post import Post
from app.schemas.post import PaginatedPostsResponse, PostCreate, PostResponse, PostUpdate
from app.services import get_post_by_id
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session
from uuid import UUID

post_router = APIRouter()

@post_router.post('/posts', response_model = PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(payload: PostCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    new_post = Post(
        title = payload.title,
        body = payload.body,
        author_id = current_user.id
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post

@post_router.get('/posts', response_model=PaginatedPostsResponse)
def get_all_posts(
    cursor_timestamp: datetime | None = None, 
    cursor_id: UUID | None = None, 
    limit: int | None = 10, 
    page: int | None = 1, 
    db: Session = Depends(get_db)
):
    limit, page = max(limit, 1), max(page, 1)
    limit = min(limit, 100)
    if (cursor_timestamp is None) != (cursor_id is None):
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail= "cursor_timestamp and cursor_id must be provided together."
        )
    next_cursor_id = None
    next_cursor_timestamp = None
    if cursor_timestamp is not None:
        posts = (
            db.query(Post)
            .filter(
                or_(
                    Post.created_at < cursor_timestamp,
                    and_(Post.created_at == cursor_timestamp, Post.id < cursor_id)
                )
            )
            .order_by(Post.created_at.desc(), Post.id.desc())
            .limit(limit)
            .all()
        )
    else:
        offset = (page- 1) * limit
        posts = db.query(Post).order_by(Post.created_at.desc()).offset(offset).limit(limit).all()
    if posts:
        last_post = posts[-1]
        next_cursor_id = last_post.id
        next_cursor_timestamp = last_post.created_at
    total_posts = db.query(func.count(Post.id)).scalar()
    total_pages = math.ceil(total_posts/limit) if total_posts>0 else 1
    return {
        "page" : page,
        "limit": limit,
        "total_posts": total_posts,
        "total_pages" : total_pages,
        "next_cursor_timestamp": next_cursor_timestamp,
        "next_cursor_id": next_cursor_id,
        "posts": posts
    }

@post_router.get('/posts/{post_id}', response_model= PostResponse, status_code= status.HTTP_200_OK)
def get_post(post_id, db: Session = Depends(get_db)):
    post = get_post_by_id(db, post_id= post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail= "Post not found")
    return post

@post_router.put('/posts/{post_id}', response_model= PostResponse)
def update_post(payload: PostUpdate, post_id, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    post = get_post_by_id(db, post_id= post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail= "Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail= "You're not allowed to update this post")
    if payload.title and (payload.title != ""):
        post.title = payload.title
    if payload.body and (payload.body != ""):
        post.body = payload.body
    db.commit()
    db.refresh(post)
    return post

@post_router.delete('/posts/{post_id}', status_code=status.HTTP_200_OK)
def delete_post(post_id, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    post = get_post_by_id(db, post_id= post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail= "Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail= "You're not allowed to delete this post")
    db.delete(post)
    db.commit()
