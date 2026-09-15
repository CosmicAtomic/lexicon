

from app.dependencies import get_db, get_current_user
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentResponse
from app.services import get_post_by_id
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

comment_router = APIRouter()


@comment_router.post('/posts/{post_id}/comments', response_model = CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(post_id, payload: CommentCreate, db: Session =Depends(get_db), current_user=Depends(get_current_user)):
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
    return new_comment

@comment_router.get('/posts/{post_id}/comments')
def get_all_comments(post_id, db: Session = Depends(get_db)):
    post = get_post_by_id(db, post_id=post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail= "Post not found")
    comments = db.query(Comment).filter(Comment.post_id == post_id).all()
    return comments
