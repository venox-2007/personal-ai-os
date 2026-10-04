from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from dateutil import tz

class CalendarEventBase(BaseModel):
    title: str = Field(..., description="The title of the event")
    description: Optional[str] = Field(None, description="Detailed description of the event")
    location: Optional[str] = Field(None, description="Location of the event")
    start_datetime: datetime = Field(..., description="Start time of the event (ISO 8601)")
    end_datetime: datetime = Field(..., description="End time of the event (ISO 8601)")
    all_day: bool = Field(False, description="Whether the event is all-day")
    timezone: str = Field(..., description="IANA timezone identifier (e.g., 'Asia/Kolkata')")
    recurrence_rule: Optional[str] = Field(None, description="RRULE string for recurring events")
    status: str = Field("CONFIRMED", description="Event status: CONFIRMED, TENTATIVE, CANCELLED")
    calendar_name: str = Field("Default", description="Name of the calendar")
    calendar_id: str = Field("default", description="ID of the calendar")

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if not tz.gettz(v):
            raise ValueError(f"Invalid IANA timezone identifier: {v}")
        return v
        
    @field_validator("end_datetime")
    @classmethod
    def validate_end_after_start(cls, v: datetime, info) -> datetime:
        if "start_datetime" in info.data and v < info.data["start_datetime"]:
            raise ValueError("end_datetime must be after start_datetime")
        return v

class CalendarEventCreate(CalendarEventBase):
    pass

class CalendarEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    all_day: Optional[bool] = None
    timezone: Optional[str] = None
    recurrence_rule: Optional[str] = None
    status: Optional[str] = None
    calendar_name: Optional[str] = None
    calendar_id: Optional[str] = None
    
    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v and not tz.gettz(v):
            raise ValueError(f"Invalid IANA timezone identifier: {v}")
        return v

class CalendarEventResponse(CalendarEventBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CalendarConflictResponse(BaseModel):
    has_conflict: bool
    conflicting_events: List[CalendarEventResponse]
