"""Shared schema helpers: pagination envelope."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


def make_page(items: list, total: int, page: int, page_size: int) -> Page:
    pages = (total + page_size - 1) // page_size if page_size else 1
    return Page(items=items, total=total, page=page, page_size=page_size, pages=pages)
