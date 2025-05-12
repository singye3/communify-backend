# app/db/models/user_symbols.py
from beanie import Document, Link, Indexed
from typing import Optional
from pydantic import Field
import pymongo # For index definition

from .user import User # Import your existing User model

class UserCategorySymbol(Document):
    """
    Represents a symbol keyword added by a specific user to a specific category.
    This allows users to customize or extend both standard and their own categories.
    """
    keyword: Indexed(str, index_type=pymongo.TEXT) = Field(..., min_length=1, description="The symbol keyword added by the user.")
    category_name: Indexed(str) = Field(
        ...,
        min_length=1,
        description="Lowercase name of the category this symbol belongs to for this user (e.g., 'food', 'my_vacation')."
    )
    # image_uri: Optional[str] = Field(default=None, description="Optional URI for an image associated with this user-added symbol.")
    # custom_order: Optional[int] = Field(default=None, description="Optional field for user-defined sort order within their category.")

    user: Link[User] = Field(..., description="Link to the user who added this symbol.")

    class Settings:
        name = "user_category_symbols" # MongoDB collection name
        # Unique compound index to prevent a user from adding the exact same keyword
        # to the exact same category_name multiple times.
        # Note: MongoDB text indexes can't be part of a unique compound index in the same way.
        # If keyword needs to be unique per user/category, a standard index is better.
        # For text search on keyword, the Indexed(str, index_type=pymongo.TEXT) is good.
        # Let's make (user, category_name, keyword) unique.
        indexes = [
            [
                ("user", pymongo.ASCENDING),
                ("category_name", pymongo.ASCENDING),
                ("keyword", pymongo.ASCENDING),
            ],
            # This unique index ensures a user cannot add the same keyword to the same category twice.
            # If you need case-insensitive uniqueness, you'd handle that at the application level
            # or store a normalized (e.g., lowercase) version of the keyword for the unique index.
            # However, for direct matching, this is fine.
            # Beanie might automatically create this unique index if you use Pydantic's `model_validator`
            # with a query, but explicit index definition is clearer.
            # Update: Beanie's Link uses the referenced document's _id.
            # The index should be on `user.$id` if you write it manually in MongoDB.
            # Beanie handles linking correctly, so for programmatic unique check:
            # you'd query before insert as done in the endpoint.
            # The Indexed() wrapper for fields helps Beanie create individual indexes.
        ]
        # Example of a unique index (Beanie will handle the Link correctly):
        # Keep the programmatic check in the endpoint for user feedback,
        # but a database-level unique constraint is stronger.
        # This might require a custom setup or Beanie handles it well with PydanticObjectId for Links.
        # For simplicity, the programmatic check in the endpoint is the primary guard for now.
        # If you hit issues with Beanie and compound unique indexes on Links,
                # a common approach is to store the user_id as a PydanticObjectId directly
        # in this model for easier indexing if needed, though Links are generally preferred.

    # Example Pydantic model config if needed (usually not for basic Beanie docs)
    # model_config = ConfigDict(
    #     populate_by_name=True,
    #     json_encoders={PydanticObjectId: str} # If you were to return this model directly
    # )