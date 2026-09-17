import math
from app.dependencies import get_current_user, get_db
from app.models.post import Post
from app.schemas.post import PaginatedPostsResponse, PostCreate, PostResponse, PostUpdate
from app.services import get_post_by_id
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, and_, asc, desc
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
    date_from : datetime | None = None,
    date_to : datetime | None = None,
    author_id : UUID | None = None,
    sort_by : str | None = None,
    order : str | None = "desc",
    db: Session = Depends(get_db)
):
    if sort_by and sort_by not in ("created_at", "title"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail = f"sort_by must be one of {["created_at", "title"]}")

    if order not in ("asc", "desc"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="order must be either 'asc' or 'desc'")
    
    limit, page = max(limit, 1), max(page, 1)
    limit = min(limit, 100)
    if (cursor_timestamp is None) != (cursor_id is None):
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail= "cursor_timestamp and cursor_id must be provided together."
        )
    
    query = db.query(Post)

    # Apply filters
    if author_id:
        query = query.filter(Post.author_id == author_id)
    if date_from:
        query = query.filter(Post.created_at >= date_from)
    if date_to:
        query = query.filter(Post.created_at <= date_to)

    #----Get filtered Post counts---
    total_posts = query.count()
    total_pages = math.ceil(total_posts/limit) if total_posts >0 else 1

    #----- Apply sorting-----
    if sort_by:
        sort_fn = asc if order == "asc" else desc
        column_attr = getattr(Post, sort_by)
        query = query.order_by(sort_fn(column_attr), sort_fn(Post.id))
    else:
        query = query.order_by(Post.created_at.desc())

    #------Apply Pagination-------
    
    next_cursor_id = None
    next_cursor_timestamp = None

    if cursor_timestamp and (not sort_by or sort_by == "created_at") and order == "desc":
        posts = (
            query.filter(
                or_(
                    Post.created_at < cursor_timestamp,
                    and_(Post.created_at == cursor_timestamp, Post.id < cursor_id)
                )
            )
            .limit(limit)
            .all()
        )
    else:
        offset = (page- 1) * limit
        posts = query.offset(offset).limit(limit).all()
    if posts:
        last_post = posts[-1]
        next_cursor_id = last_post.id
        next_cursor_timestamp = last_post.created_at
    
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
