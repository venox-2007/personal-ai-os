from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import PlainTextResponse
from typing import List, Optional
from datetime import datetime

from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate, CalendarEventResponse
from app.integrations.calendar_provider import local_calendar_provider, provider_registry
from app.services.calendar_service import calendar_service
from app.services.ics_service import ICSExportService
from app.services.approval_service import approval_service
from app.permissions.models import PermissionLevel

router = APIRouter(prefix="/calendar", tags=["Calendar"])

@router.get("/providers", response_model=List[str])
def list_providers():
    return provider_registry.list_providers()

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

@router.get("/export/ics/{event_id}", response_class=PlainTextResponse)
def export_event_ics(event_id: str):
    event = local_calendar_provider.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    ics_content = ICSExportService.export_events([event])
    return ics_content

@router.get("/export/ics", response_class=PlainTextResponse)
def export_calendar_ics(start_datetime: Optional[datetime] = None, end_datetime: Optional[datetime] = None):
    # If no range, just get all or upcoming. For safety let's use a large range if none provided
    if not start_datetime:
        start_datetime = datetime.now().replace(year=datetime.now().year - 5)
    if not end_datetime:
        end_datetime = datetime.now().replace(year=datetime.now().year + 5)
        
    events = local_calendar_provider.list_events(start_datetime, end_datetime, limit=1000)
    ics_content = ICSExportService.export_events(events)
    return ics_content

@router.post("/import/ics")
async def import_calendar_ics(file: UploadFile = File(...), mode: str = "skip", calendar_name: str = "Default"):
    content = await file.read()
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Must be UTF-8.")
        
    req = approval_service.create_request(
        run_id=None,
        conversation_id=None,
        tool_name="calendar_import_ics",
        tool_description="Import calendar events from an uploaded ICS file",
        permission_level=PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT,
        action_description=f"Import {len(text_content)} bytes of ICS data into calendar '{calendar_name}' (mode: {mode}).",
        arguments={"ics_content": text_content, "mode": mode, "calendar_name": calendar_name},
        execution_context={}
    )
    
    return {"message": "Approval request created for ICS import", "approval_id": req.id}

@router.get("/upcoming", response_model=List[CalendarEventResponse])
def get_upcoming_events(limit: int = 10):
    return calendar_service.get_upcoming_events(limit)

@router.get("/search", response_model=List[CalendarEventResponse])
def search_events(query: str, limit: int = 50):
    return calendar_service.search_events(query, limit)

@router.get("/conflicts", response_model=List[CalendarEventResponse])
def find_conflicts(start_datetime: datetime, end_datetime: datetime, ignore_event_id: Optional[str] = None):
    return calendar_service.find_conflicts(start_datetime, end_datetime, ignore_event_id)
