import uuid
from app.database import Base
from sqlalchemy import Column, DateTime, func, ForeignKey, Text, UUID
from sqlalchemy.orm import relationship

class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True , default= uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable= False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable= False)
    body = Column(Text, nullable= False)
    created_at= Column(DateTime(timezone=True), server_default= func.now(), nullable= False )

    post = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments")