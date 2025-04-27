# app/db/models/settings.py
from typing import Optional, List, Annotated 
from datetime import datetime
from beanie import Document, Link, Indexed
from pydantic import Field, EmailStr 
from .enums import AsdLevel, DayOfWeek

class ParentalSettings(Document):
    user: Annotated[Link["User"], Indexed(unique=True)] 
    block_violence: bool = False
    block_inappropriate: bool = False
    daily_limit_hours: Optional[str] = None
    asd_level: Optional[AsdLevel] = None
    downtime_enabled: bool = False
    downtime_days: List[DayOfWeek] = Field(default_factory=list)
    downtime_start: str = "21:00"
    downtime_end: str = "07:00"
    require_passcode: bool = False
    notify_emails: List[EmailStr] = Field(default_factory=list) 
    data_sharing_preference: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Settings: name = "parental_settings"
    async def before_save(self): self.updated_at = datetime.now()

from .user import User 
ParentalSettings.model_rebuild() 