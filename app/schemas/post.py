import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator

class PostCreate(BaseModel):
    title: str
    body: str

    @field_validator('title', 'body')
    @classmethod
    def check_nul_characters(cls, value: str) -> str:
        # Check if the string contains a NUL byte character
        if "\x00" in value:
            raise ValueError("String literals cannot contain NUL (0x00) characters")
        return value

class PostUpdate(BaseModel):
    title: str | None = None
    body: str | None = None

class PostResponse(BaseModel):
    id : uuid.UUID
    title: str
    body: str
    author_id : uuid.UUID
    created_at : datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedPostsResponse(BaseModel):
    page: int
    limit: int
    total_posts: int
    total_pages : int
    next_cursor_timestamp : datetime | None
    next_cursor_id : uuid.UUID | None
    posts: list[PostResponse]