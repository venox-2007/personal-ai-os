from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_, and_, select
from sqlalchemy.orm import Session
from dateutil.rrule import rrulestr
from dateutil import tz

from app.database.session import SessionLocal
from app.models.entities import CalendarEventModel
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate

class CalendarServiceError(Exception):
    pass

class CalendarService:
    def _get_db(self) -> Session:
        return SessionLocal()

    def _ensure_aware(self, dt: datetime, tz_name: str = "UTC") -> datetime:
        """Ensure datetime is timezone aware."""
        if dt.tzinfo is None:
            zone = tz.gettz(tz_name) or tz.UTC
            return dt.replace(tzinfo=zone)
        return dt

    def create_event(self, data: CalendarEventCreate) -> CalendarEventModel:
        with self._get_db() as db:
            event = CalendarEventModel(
                title=data.title,
                description=data.description,
                location=data.location,
                start_datetime=self._ensure_aware(data.start_datetime, data.timezone).astimezone(timezone.utc).replace(tzinfo=None),
                end_datetime=self._ensure_aware(data.end_datetime, data.timezone).astimezone(timezone.utc).replace(tzinfo=None),
                all_day=data.all_day,
                timezone=data.timezone,
                recurrence_rule=data.recurrence_rule,
                status=data.status,
                calendar_name=data.calendar_name,
                calendar_id=data.calendar_id,
                ics_uid=data.ics_uid
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            # Re-attach timezone awareness for the returned object to match schemas
            return self._hydrate_tz(event)

    def _hydrate_tz(self, event: CalendarEventModel) -> CalendarEventModel:
        """SQLite strips tzinfo, we must restore it as UTC, then return."""
        if event.start_datetime and event.start_datetime.tzinfo is None:
            event.start_datetime = event.start_datetime.replace(tzinfo=timezone.utc)
        if event.end_datetime and event.end_datetime.tzinfo is None:
            event.end_datetime = event.end_datetime.replace(tzinfo=timezone.utc)
        if event.created_at and event.created_at.tzinfo is None:
            event.created_at = event.created_at.replace(tzinfo=timezone.utc)
        if event.updated_at and event.updated_at.tzinfo is None:
            event.updated_at = event.updated_at.replace(tzinfo=timezone.utc)
        return event

    def get_event(self, event_id: str) -> Optional[CalendarEventModel]:
        with self._get_db() as db:
            event = db.query(CalendarEventModel).filter(CalendarEventModel.id == event_id).first()
            if event:
                return self._hydrate_tz(event)
            return None

    def get_event_by_ics_uid(self, ics_uid: str) -> Optional[CalendarEventModel]:
        with self._get_db() as db:
            event = db.query(CalendarEventModel).filter(CalendarEventModel.ics_uid == ics_uid).first()
            if event:
                return self._hydrate_tz(event)
            return None

    def update_event(self, event_id: str, data: CalendarEventUpdate) -> Optional[CalendarEventModel]:
        with self._get_db() as db:
            event = db.query(CalendarEventModel).filter(CalendarEventModel.id == event_id).first()
            if not event:
                return None
                
            update_data = data.model_dump(exclude_unset=True)
            
            # Need to carefully handle datetimes because they might be updated without timezone being updated, 
            # or timezone updated without datetimes.
            current_tz = update_data.get("timezone", event.timezone)
            
            for key, value in update_data.items():
                if key in ("start_datetime", "end_datetime") and value is not None:
                    # Convert to naive UTC for storage
                    dt = self._ensure_aware(value, current_tz)
                    value = dt.astimezone(timezone.utc).replace(tzinfo=None)
                setattr(event, key, value)
                
            db.commit()
            db.refresh(event)
            return self._hydrate_tz(event)

    def delete_event(self, event_id: str) -> bool:
        with self._get_db() as db:
            event = db.query(CalendarEventModel).filter(CalendarEventModel.id == event_id).first()
            if not event:
                return False
            db.delete(event)
            db.commit()
            return True

    def list_events(self, start: datetime, end: datetime, calendar_name: Optional[str] = None, limit: int = 100) -> List[CalendarEventModel]:
        with self._get_db() as db:
            start_utc = self._ensure_aware(start).astimezone(timezone.utc).replace(tzinfo=None)
            end_utc = self._ensure_aware(end).astimezone(timezone.utc).replace(tzinfo=None)
            
            query = db.query(CalendarEventModel)
            if calendar_name:
                query = query.filter(CalendarEventModel.calendar_name == calendar_name)
                
            # Fetch events that overlap OR are recurring
            events = query.filter(
                or_(
                    and_(CalendarEventModel.start_datetime <= end_utc, CalendarEventModel.end_datetime >= start_utc),
                    CalendarEventModel.recurrence_rule.isnot(None)
                )
            ).all()
            
            expanded_events = []
            for ev in events:
                ev = self._hydrate_tz(ev)
                if not ev.recurrence_rule:
                    if ev.start_datetime <= self._ensure_aware(end) and ev.end_datetime >= self._ensure_aware(start):
                        expanded_events.append(ev)
                else:
                    expanded_events.extend(self._expand_recurring(ev, self._ensure_aware(start), self._ensure_aware(end)))
                    
            # Sort by start time and limit
            expanded_events.sort(key=lambda x: x.start_datetime)
            return expanded_events[:limit]

    def _expand_recurring(self, event: CalendarEventModel, window_start: datetime, window_end: datetime) -> List[CalendarEventModel]:
        """Expands a recurring event within the window."""
        try:
            event_tz = tz.gettz(event.timezone) or tz.UTC
            start_local = event.start_datetime.astimezone(event_tz)
            
            # Using rrule
            rule = rrulestr(event.recurrence_rule, dtstart=start_local)
            
            # Duration
            duration = event.end_datetime - event.start_datetime
            
            instances = []
            
            # Find occurrences in window. RRule between is inclusive.
            # We must account for the duration of the event overlapping the window.
            # So we check from window_start - duration to window_end.
            search_start = (window_start - duration).astimezone(event_tz).replace(tzinfo=None)
            search_end = window_end.astimezone(event_tz).replace(tzinfo=None)
            
            # rrule between requires naive datetimes if dtstart is naive, but we made dtstart aware?
            # actually rrulestr handles aware if dtstart is aware. Let's keep it aware.
            for dt in rule.between(window_start - duration, window_end, inc=True):
                # dt is aware because dtstart was aware
                occ = CalendarEventModel(
                    id=event.id, # Keep same ID or composite ID? We keep same ID for the model representation here
                    title=event.title,
                    description=event.description,
                    location=event.location,
                    start_datetime=dt,
                    end_datetime=dt + duration,
                    all_day=event.all_day,
                    timezone=event.timezone,
                    recurrence_rule=event.recurrence_rule,
                    status=event.status,
                    calendar_name=event.calendar_name,
                    calendar_id=event.calendar_id,
                    ics_uid=event.ics_uid,
                    created_at=event.created_at,
                    updated_at=event.updated_at
                )
                instances.append(occ)
            return instances
        except Exception:
            return []

    def search_events(self, query_str: str, limit: int = 50) -> List[CalendarEventModel]:
        with self._get_db() as db:
            like_str = f"%{query_str}%"
            events = db.query(CalendarEventModel).filter(
                or_(
                    CalendarEventModel.title.ilike(like_str),
                    CalendarEventModel.description.ilike(like_str),
                    CalendarEventModel.location.ilike(like_str)
                )
            ).order_by(CalendarEventModel.start_datetime.desc()).limit(limit).all()
            
            return [self._hydrate_tz(ev) for ev in events]

    def get_upcoming_events(self, limit: int = 10) -> List[CalendarEventModel]:
        now = datetime.now(timezone.utc)
        # Look ahead up to 30 days for upcoming
        return self.list_events(start=now, end=now + timedelta(days=30), limit=limit)

    def find_conflicts(self, start: datetime, end: datetime, ignore_event_id: Optional[str] = None) -> List[CalendarEventModel]:
        # Simple overlap logic for list_events output
        events_in_window = self.list_events(start, end)
        conflicts = []
        
        start_aware = self._ensure_aware(start)
        end_aware = self._ensure_aware(end)
        
        for ev in events_in_window:
            if ignore_event_id and ev.id == ignore_event_id:
                continue
            if ev.status == "CANCELLED":
                continue
            
            # Overlap condition: A.start < B.end AND A.end > B.start (strict overlap, adjacent is fine)
            if ev.start_datetime < end_aware and ev.end_datetime > start_aware:
                conflicts.append(ev)
                
        return conflicts

calendar_service = CalendarService()
