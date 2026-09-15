from app.models.post import Post
from app.models.user import User
from sqlalchemy.orm import Session

def get_user_by_email(db: Session, email):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_github_id(db: Session, github_id):
    return db.query(User).filter(User.github_id == str(github_id)).first()

def get_user_by_google_id(db: Session, google_id):
    return db.query(User).filter(User.google_id == str(google_id)).first()

def get_user_by_username(db: Session, username):
    return db.query(User).filter(User.username == username).first()

def get_post_by_id(db: Session, post_id):
    return db.query(Post).filter(Post.id == post_id).first()