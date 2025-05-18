# app/db/models/user_symbols.py

from beanie import Document, Link, Indexed
from typing import Optional
from pydantic import Field
import pymongo
from .user import User

class UserCategorySymbol(Document):
    keyword: Indexed(str, index_type=pymongo.TEXT) = Field(
        ..., min_length=1, description="The symbol keyword added by the user."
    )
    category_name: Indexed(str) = Field(
        ...,
        min_length=1,
        description="Lowercase name of the category this symbol belongs to for this user (e.g., 'food', 'my_vacation').",
    )
    user: Link[User] = Field(..., description="Link to the user who added this symbol.")

    class Settings:
        name = "user_category_symbols"
        indexes = [
            [
                ("user", pymongo.ASCENDING),
                ("category_name", pymongo.ASCENDING),
                ("keyword", pymongo.ASCENDING),
            ],
        ]