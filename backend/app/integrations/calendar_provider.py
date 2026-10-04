from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate
from app.models.entities import CalendarEventModel

class BaseCalendarProvider(ABC):
    """Abstract base class for calendar providers (Local, Google, Microsoft)."""

    @abstractmethod
    def create_event(self, data: CalendarEventCreate) -> CalendarEventModel:
        pass

    @abstractmethod
    def get_event(self, event_id: str) -> Optional[CalendarEventModel]:
        pass

    @abstractmethod
    def update_event(self, event_id: str, data: CalendarEventUpdate) -> Optional[CalendarEventModel]:
        pass

    @abstractmethod
    def delete_event(self, event_id: str) -> bool:
        pass

    @abstractmethod
    def list_events(self, start: datetime, end: datetime, calendar_name: Optional[str] = None, limit: int = 100) -> List[CalendarEventModel]:
        pass

class LocalCalendarProvider(BaseCalendarProvider):
    """Implementation of CalendarProvider that uses the local CalendarService and SQLite."""
    
    def __init__(self):
        from app.services.calendar_service import calendar_service
        self.service = calendar_service

    def create_event(self, data: CalendarEventCreate) -> CalendarEventModel:
        return self.service.create_event(data)

    def get_event(self, event_id: str) -> Optional[CalendarEventModel]:
        return self.service.get_event(event_id)

    def update_event(self, event_id: str, data: CalendarEventUpdate) -> Optional[CalendarEventModel]:
        return self.service.update_event(event_id, data)

    def delete_event(self, event_id: str) -> bool:
        return self.service.delete_event(event_id)

    def list_events(self, start: datetime, end: datetime, calendar_name: Optional[str] = None, limit: int = 100) -> List[CalendarEventModel]:
        return self.service.list_events(start, end, calendar_name, limit)

# Registry or active provider can be managed here.
local_calendar_provider = LocalCalendarProvider()
