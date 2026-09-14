import uuid
from app.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, func, String, Text, UUID
from sqlalchemy.orm import relationship

class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key= True, default= uuid.uuid4)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete= "CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable= False)
    created_at = Column(DateTime(timezone=True), server_default= func.now(), nullable= False)

    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", passive_deletes=True)