import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class CommentCreate(BaseModel):
    body: str

class CommentResponse(BaseModel):
    id : uuid.UUID
    body: str
    author_id : uuid.UUID
    post_id : uuid.UUID
    created_at : datetime

    model_config = ConfigDict(from_attributes=True)