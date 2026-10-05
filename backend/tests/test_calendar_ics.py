import pytest
from datetime import datetime, timezone, date
from app.integrations.calendar_provider import CalendarProviderRegistry, LocalCalendarProvider
from app.services.ics_service import ICSExportService, ICSImportService
from app.models.entities import CalendarEventModel
from app.schemas.calendar import CalendarEventCreate
from app.services.calendar_service import calendar_service
from app.database.session import SessionLocal, init_db

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    with SessionLocal() as db:
        db.query(CalendarEventModel).delete()
        db.commit()

def test_provider_registry():
    registry = CalendarProviderRegistry()
    assert isinstance(registry.get_provider("local"), LocalCalendarProvider)
    assert registry.get_provider("unknown") is None
    assert "local" in registry.list_providers()

def test_ics_export():
    events = [
        CalendarEventModel(
            id="1",
            title="Test Event 1",
            description="Desc 1",
            location="Loc 1",
            start_datetime=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_datetime=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
            all_day=False,
            timezone="UTC",
            status="CONFIRMED",
            ics_uid="uid-1"
        ),
        CalendarEventModel(
            id="2",
            title="All Day Event",
            start_datetime=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
            end_datetime=datetime(2026, 1, 3, 0, 0, tzinfo=timezone.utc),
            all_day=True,
            timezone="UTC",
            status="TENTATIVE",
            ics_uid="uid-2"
        )
    ]
    
    ics_text = ICSExportService.export_events(events)
    assert "BEGIN:VCALENDAR" in ics_text
    assert "VERSION:2.0" in ics_text
    assert "SUMMARY:Test Event 1" in ics_text
    assert "SUMMARY:All Day Event" in ics_text
    assert "UID:uid-1" in ics_text
    assert "UID:uid-2" in ics_text
    assert "DESCRIPTION:Desc 1" in ics_text
    assert "LOCATION:Loc 1" in ics_text
    assert "STATUS:CONFIRMED" in ics_text
    assert "STATUS:TENTATIVE" in ics_text
    # Check CRLF
    assert "\r\n" in ics_text

def test_ics_import_single_and_multiple():
    ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
SUMMARY:Import Event
DTSTART;VALUE=DATE-TIME:20260101T100000Z
DTEND;VALUE=DATE-TIME:20260101T110000Z
UID:import-uid-1
DESCRIPTION:Imported desc
LOCATION:Imported loc
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
SUMMARY:Import All Day
DTSTART;VALUE=DATE:20260102
DTEND;VALUE=DATE:20260103
UID:import-uid-2
END:VEVENT
END:VCALENDAR"""

    results = ICSImportService.parse_ics(ics_content)
    assert results["created"] == 2
    assert results["errors"] == 0
    
    # Verify in DB
    ev1 = calendar_service.get_event_by_ics_uid("import-uid-1")
    assert ev1 is not None
    assert ev1.title == "Import Event"
    assert not ev1.all_day
    
    ev2 = calendar_service.get_event_by_ics_uid("import-uid-2")
    assert ev2 is not None
    assert ev2.all_day

def test_ics_import_malformed():
    ics_content = "This is not an ICS file"
    with pytest.raises(ValueError):
        ICSImportService.parse_ics(ics_content)

def test_ics_import_duplicate_uid():
    ics_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Dupe
DTSTART;VALUE=DATE-TIME:20260101T100000Z
DTEND;VALUE=DATE-TIME:20260101T110000Z
UID:dupe-1
END:VEVENT
END:VCALENDAR"""
    # Import first time
    res1 = ICSImportService.parse_ics(ics_content)
    assert res1["created"] == 1
    
    # Import second time with skip
    res2 = ICSImportService.parse_ics(ics_content, mode="skip")
    assert res2["skipped"] == 1
    assert res2["created"] == 0

def test_ics_import_invalid_datetime():
    ics_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Invalid DT
DTSTART:invalid
DTEND:invalid
UID:invalid-dt
END:VEVENT
END:VCALENDAR"""
    res = ICSImportService.parse_ics(ics_content)
    # icalendar parser might fail at parsing or we catch it
    # Just asserting it doesn't crash the whole process and handles it
    assert res["errors"] > 0

def test_ics_import_end_before_start():
    ics_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Reverse
DTSTART;VALUE=DATE-TIME:20260101T110000Z
DTEND;VALUE=DATE-TIME:20260101T100000Z
UID:reverse-1
END:VEVENT
END:VCALENDAR"""
    res = ICSImportService.parse_ics(ics_content)
    assert res["errors"] == 1
    assert res["created"] == 0
