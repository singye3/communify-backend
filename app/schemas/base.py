# app/schemas/base.py
from pydantic import BaseModel

class BaseSchema(BaseModel):
    class Config:
        # For Pydantic V2
        from_attributes = True # Renamed from orm_mode
        # For Pydantic V1
        # orm_mode = True