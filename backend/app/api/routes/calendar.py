from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime

from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate, CalendarEventResponse
from app.integrations.calendar_provider import local_calendar_provider
from app.services.calendar_service import calendar_service

router = APIRouter(prefix="/calendar", tags=["Calendar"])

@router.get("/events", response_model=List[CalendarEventResponse])
def list_events(start_datetime: datetime, end_datetime: datetime, calendar_name: Optional[str] = None, limit: int = 100):
    events = local_calendar_provider.list_events(start_datetime, end_datetime, calendar_name, limit)
    return events

@router.get("/events/{event_id}", response_model=CalendarEventResponse)
def get_event(event_id: str):
    event = local_calendar_provider.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event





@router.get("/upcoming", response_model=List[CalendarEventResponse])
def get_upcoming_events(limit: int = 10):
    return calendar_service.get_upcoming_events(limit)

@router.get("/search", response_model=List[CalendarEventResponse])
def search_events(query: str, limit: int = 50):
    return calendar_service.search_events(query, limit)

@router.get("/conflicts", response_model=List[CalendarEventResponse])
def find_conflicts(start_datetime: datetime, end_datetime: datetime, ignore_event_id: Optional[str] = None):
    return calendar_service.find_conflicts(start_datetime, end_datetime, ignore_event_id)
