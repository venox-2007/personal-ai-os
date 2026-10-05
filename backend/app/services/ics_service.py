import uuid
from typing import List, Optional
from datetime import datetime
from icalendar import Calendar, Event, vText
from icalendar.prop import vRecur
import pytz

from app.models.entities import CalendarEventModel
from app.schemas.calendar import CalendarEventCreate
from app.services.calendar_service import calendar_service

class ICSExportService:
    @staticmethod
    def export_events(events: List[CalendarEventModel]) -> str:
        cal = Calendar()
        cal.add('prodid', '-//Personal AI OS//EN')
        cal.add('version', '2.0')

        for ev in events:
            ievent = Event()
            ievent.add('summary', ev.title)
            
            tz = pytz.timezone(ev.timezone) if ev.timezone else pytz.UTC
            
            if ev.all_day:
                ievent.add('dtstart', ev.start_datetime.date())
                ievent.add('dtend', ev.end_datetime.date())
            else:
                ievent.add('dtstart', tz.localize(ev.start_datetime) if ev.start_datetime.tzinfo is None else ev.start_datetime)
                ievent.add('dtend', tz.localize(ev.end_datetime) if ev.end_datetime.tzinfo is None else ev.end_datetime)
            
            ievent.add('uid', ev.ics_uid or str(ev.id))
            
            if ev.description:
                ievent.add('description', ev.description)
            if ev.location:
                ievent.add('location', ev.location)
            if ev.status:
                ievent.add('status', ev.status)
                
            if ev.recurrence_rule:
                # icalendar expects vRecur or dict. Rrule strings are easily parsed by vRecur.from_ical
                try:
                    ievent.add('rrule', vRecur.from_ical(ev.recurrence_rule))
                except Exception:
                    pass

            cal.add_component(ievent)
        
        return cal.to_ical().decode("utf-8")

class ICSImportService:
    @staticmethod
    def parse_ics(content: str, mode: str = "skip", calendar_name: str = "Default") -> dict:
        try:
            cal = Calendar.from_ical(content)
        except ValueError:
            raise ValueError("Invalid ICS content")

        results = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

        for component in cal.walk():
            if component.name == "VEVENT":
                try:
                    summary = str(component.get('summary', 'Untitled Event'))
                    description = str(component.get('description', ''))
                    location = str(component.get('location', ''))
                    uid = str(component.get('uid', str(uuid.uuid4())))
                    
                    dtstart = component.get('dtstart')
                    dtend = component.get('dtend')
                    
                    if not dtstart or not dtend:
                        results["errors"] += 1
                        continue
                        
                    start_dt = dtstart.dt
                    end_dt = dtend.dt
                    
                    all_day = False
                    if not isinstance(start_dt, datetime):
                        start_dt = datetime.combine(start_dt, datetime.min.time())
                        all_day = True
                    if not isinstance(end_dt, datetime):
                        end_dt = datetime.combine(end_dt, datetime.min.time())
                        
                    if end_dt < start_dt:
                        results["errors"] += 1
                        continue
                    
                    tz_name = "UTC"
                    # Attempt to extract tzinfo properly. 
                    if hasattr(start_dt, 'tzinfo') and start_dt.tzinfo:
                        try:
                            # Usually icalendar uses tzutc() or tzfile
                            if str(start_dt.tzinfo) != "tzutc()":
                                # Extract string name if possible, default UTC
                                tz_name = str(start_dt.tzinfo)
                        except:
                            pass
                            
                    status = str(component.get('status', 'CONFIRMED'))
                    
                    # Convert start/end back to naive for schema if needed, but schema accepts aware
                    
                    rrule = component.get('rrule')
                    rrule_str = None
                    if rrule:
                        rrule_str = rrule.to_ical().decode('utf-8')

                    existing = calendar_service.get_event_by_ics_uid(uid)
                    if existing:
                        if mode == "skip":
                            results["skipped"] += 1
                            continue
                        elif mode == "update":
                            # Simplification: we delete and recreate, or skip
                            # In production, we'd update.
                            results["skipped"] += 1
                            continue
                            
                    create_data = CalendarEventCreate(
                        title=summary,
                        description=description if description else None,
                        location=location if location else None,
                        start_datetime=start_dt,
                        end_datetime=end_dt,
                        all_day=all_day,
                        timezone=tz_name if tz_name else "UTC",
                        recurrence_rule=rrule_str,
                        status=status,
                        calendar_name=calendar_name,
                        ics_uid=uid
                    )
                    calendar_service.create_event(create_data)
                    results["created"] += 1
                    
                except Exception as e:
                    results["errors"] += 1
                    
        return results
