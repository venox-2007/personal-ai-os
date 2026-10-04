import json
from typing import Dict, Any, List
from datetime import datetime
from dateutil import tz
import logging

from app.tools.base import BaseTool, ToolResult, PermissionLevel
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate
from app.integrations.calendar_provider import local_calendar_provider
from app.services.calendar_service import calendar_service

logger = logging.getLogger(__name__)

def _serialize_event(ev) -> Dict[str, Any]:
    return {
        "id": ev.id,
        "title": ev.title,
        "description": ev.description,
        "location": ev.location,
        "start_datetime": ev.start_datetime.isoformat() if ev.start_datetime else None,
        "end_datetime": ev.end_datetime.isoformat() if ev.end_datetime else None,
        "all_day": ev.all_day,
        "timezone": ev.timezone,
        "recurrence_rule": ev.recurrence_rule,
        "status": ev.status,
        "calendar_name": ev.calendar_name,
        "calendar_id": ev.calendar_id,
    }

class CalendarCreateEventTool(BaseTool):
    name: str = "calendar_create_event"
    description: str = "Create a new event on the local calendar."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT

    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "start_datetime": {"type": "string", "description": "ISO 8601 datetime string"},
            "end_datetime": {"type": "string", "description": "ISO 8601 datetime string"},
            "timezone": {"type": "string", "description": "IANA timezone identifier (e.g. 'Asia/Kolkata')"},
            "description": {"type": "string"},
            "location": {"type": "string"},
            "all_day": {"type": "boolean"},
            "recurrence_rule": {"type": "string", "description": "Standard RRULE string"}
        },
        "required": ["title", "start_datetime", "end_datetime", "timezone"]
    }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            data = CalendarEventCreate(**kwargs)
            event = local_calendar_provider.create_event(data)
            return ToolResult(success=True, output={"event": _serialize_event(event)})
        except ValueError as e:
            return ToolResult(success=False, error=f"Validation error: {e}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class CalendarUpdateEventTool(BaseTool):
    name: str = "calendar_update_event"
    description: str = "Update an existing event on the local calendar."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT

    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "event_id": {"type": "string"},
            "title": {"type": "string"},
            "start_datetime": {"type": "string"},
            "end_datetime": {"type": "string"},
            "timezone": {"type": "string"},
            "description": {"type": "string"},
            "location": {"type": "string"},
            "all_day": {"type": "boolean"},
            "recurrence_rule": {"type": "string"},
            "status": {"type": "string", "enum": ["CONFIRMED", "TENTATIVE", "CANCELLED"]}
        },
        "required": ["event_id"]
    }

    async def execute(self, **kwargs) -> ToolResult:
        event_id = kwargs.pop("event_id")
        try:
            update_data = CalendarEventUpdate(**kwargs)
            event = local_calendar_provider.update_event(event_id, update_data)
            if not event:
                return ToolResult(success=False, error=f"Event {event_id} not found.")
            return ToolResult(success=True, output={"event": _serialize_event(event)})
        except ValueError as e:
            return ToolResult(success=False, error=f"Validation error: {e}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CalendarDeleteEventTool(BaseTool):
    name: str = "calendar_delete_event"
    description: str = "Delete an event from the calendar."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT

    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "event_id": {"type": "string"}
        },
        "required": ["event_id"]
    }

    async def execute(self, **kwargs) -> ToolResult:
        event_id = kwargs.get("event_id")
        success = local_calendar_provider.delete_event(event_id)
        if success:
            return ToolResult(success=True, output={"message": "Event deleted successfully."})
        return ToolResult(success=False, error=f"Event {event_id} not found.")


class CalendarListEventsTool(BaseTool):
    name: str = "calendar_list_events"
    description: str = "List events within a given date range."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY

    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "start_datetime": {"type": "string", "description": "ISO 8601 start bound"},
            "end_datetime": {"type": "string", "description": "ISO 8601 end bound"}
        },
        "required": ["start_datetime", "end_datetime"]
    }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            start = datetime.fromisoformat(kwargs["start_datetime"].replace('Z', '+00:00'))
            end = datetime.fromisoformat(kwargs["end_datetime"].replace('Z', '+00:00'))
            events = local_calendar_provider.list_events(start, end)
            return ToolResult(success=True, output={"events": [_serialize_event(e) for e in events]})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CalendarSearchEventsTool(BaseTool):
    name: str = "calendar_search"
    description: str = "Search events by keywords in title, description, or location."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY

    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword"}
        },
        "required": ["query"]
    }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            query = kwargs["query"]
            events = calendar_service.search_events(query)
            return ToolResult(success=True, output={"events": [_serialize_event(e) for e in events]})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CalendarUpcomingEventsTool(BaseTool):
    name: str = "calendar_upcoming"
    description: str = "Get the next upcoming events in the next 30 days."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY

    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer"}
        }
    }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            limit = kwargs.get("limit", 10)
            events = calendar_service.get_upcoming_events(limit=limit)
            return ToolResult(success=True, output={"events": [_serialize_event(e) for e in events]})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CalendarFindConflictsTool(BaseTool):
    name: str = "calendar_find_conflicts"
    description: str = "Check if a given time slot conflicts with existing events."
    permission_level: PermissionLevel = PermissionLevel.LEVEL_0_READ_ONLY

    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "start_datetime": {"type": "string"},
            "end_datetime": {"type": "string"},
            "ignore_event_id": {"type": "string", "description": "Event ID to ignore (e.g. if updating it)"}
        },
        "required": ["start_datetime", "end_datetime"]
    }

    async def execute(self, **kwargs) -> ToolResult:
        try:
            start = datetime.fromisoformat(kwargs["start_datetime"].replace('Z', '+00:00'))
            end = datetime.fromisoformat(kwargs["end_datetime"].replace('Z', '+00:00'))
            ignore_id = kwargs.get("ignore_event_id")
            
            conflicts = calendar_service.find_conflicts(start, end, ignore_id)
            return ToolResult(success=True, output={
                "has_conflict": len(conflicts) > 0,
                "conflicts": [_serialize_event(e) for e in conflicts]
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))
