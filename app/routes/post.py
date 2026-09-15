# Build create/read/update/delete for posts, and create/read for comments — nested under a post (/posts/{id}/comments).
# Protect create/update/delete with your existing get_current_user dependency; reads can stay public.
# Gotcha: make sure a user can only edit/delete their own posts — check author_id == current_user.id, don't just check "is logged in."

from app.dependencies import get_current_user, get_db
from app.models.post import Post
from app.schemas.post import PostCreate, PostResponse, PostUpdate
from app.services import get_post_by_id
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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

@post_router.get('/posts')
def get_all_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).all()
    return posts

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




