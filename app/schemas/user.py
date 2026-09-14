import uuid
from pydantic import BaseModel, ConfigDict, EmailStr

class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = 'bearer'

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
