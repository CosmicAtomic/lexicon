import uuid
from app.database import Base
from sqlalchemy import Column, UUID, String
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key= True, default=uuid.uuid4)
    github_id = Column(String, nullable= True, unique= True)
    google_id = Column(String, nullable= True, unique= True)
    email= Column(String, unique= True, nullable= True)
    username = Column(String, nullable = False, unique= True)
    hashed_password = Column(String, nullable = False)

    posts = relationship("Post", back_populates="author")
    comments = relationship("Comment", back_populates="author", passive_deletes=True)