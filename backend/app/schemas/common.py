from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Serialises snake_case fields as camelCase (the frontend's convention for most objects)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class MessageResponse(BaseModel):
    message: str


class Page[T](CamelModel):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class NamedCount(BaseModel):
    name: str
    count: int
