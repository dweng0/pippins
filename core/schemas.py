"""
Pydantic schemas for validating input at the boundary (form POSTs, JSON API).
Kept separate from Django's ModelForm/serializer machinery deliberately —
this is the validation layer for hand-rolled views, not a DRF replacement.
"""

from pydantic import BaseModel, Field, field_validator


class TaskCreateSchema(BaseModel):
    title: str = Field(min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title cannot be blank")
        return stripped
