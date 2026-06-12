"""Contact form schemas"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class ContactRequest(BaseModel):
    """Contact form request schema"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    subject: str = Field(..., min_length=5, max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)


class ContactResponse(BaseModel):
    """Contact form response schema"""
    success: bool
    message: str
    data: Optional[dict] = None
