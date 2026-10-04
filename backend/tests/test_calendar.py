import pytest
from datetime import datetime, timezone, timedelta
from app.models.entities import CalendarEventModel
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate
from app.services.calendar_service import calendar_service
from app.integrations.calendar_provider import local_calendar_provider
from app.database.session import SessionLocal, init_db

def _cleanup(db, event_id):
    ev = db.query(CalendarEventModel).filter(CalendarEventModel.id == event_id).first()
    if ev:
        db.delete(ev)
        db.commit()

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

@pytest.fixture
def db():
    db = SessionLocal()
    yield db
    db.close()

def test_calendar_service_create_get_delete(db):
    now = datetime.now(timezone.utc)
    create_data = CalendarEventCreate(
        title="Test Event 1",
        description="A test event",
        location="Room A",
        start_datetime=now,
        end_datetime=now + timedelta(hours=1),
        timezone="UTC",
        calendar_id="test_calendar_123"
    )
    
    event = calendar_service.create_event(create_data)
    assert event.id is not None
    assert event.title == "Test Event 1"
    assert event.calendar_id == "test_calendar_123"
    assert event.start_datetime.tzinfo is not None
    
    fetched = calendar_service.get_event(event.id)
    assert fetched is not None
    assert fetched.id == event.id
    
    deleted = calendar_service.delete_event(event.id)
    assert deleted is True
    assert calendar_service.get_event(event.id) is None

def test_calendar_service_update(db):
    now = datetime.now(timezone.utc)
    event = calendar_service.create_event(CalendarEventCreate(
        title="Test Update",
        start_datetime=now,
        end_datetime=now + timedelta(hours=1),
        timezone="UTC"
    ))
    
    update_data = CalendarEventUpdate(title="Updated Title", location="New Room")
    updated = calendar_service.update_event(event.id, update_data)
    assert updated.title == "Updated Title"
    assert updated.location == "New Room"
    
    _cleanup(db, event.id)

def test_calendar_service_list_and_conflicts(db):
    now = datetime.now(timezone.utc)
    ev1 = calendar_service.create_event(CalendarEventCreate(
        title="Overlap 1",
        start_datetime=now,
        end_datetime=now + timedelta(hours=2),
        timezone="UTC"
    ))
    
    ev2 = calendar_service.create_event(CalendarEventCreate(
        title="Overlap 2",
        start_datetime=now + timedelta(hours=1),
        end_datetime=now + timedelta(hours=3),
        timezone="UTC"
    ))
    
    # Conflict detection
    conflicts = calendar_service.find_conflicts(
        start=now + timedelta(minutes=30),
        end=now + timedelta(minutes=90)
    )
    # Both events overlap with this window
    conflict_ids = {c.id for c in conflicts}
    assert ev1.id in conflict_ids
    assert ev2.id in conflict_ids
    
    _cleanup(db, ev1.id)
    _cleanup(db, ev2.id)

def test_calendar_service_recurrence(db):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    ev1 = calendar_service.create_event(CalendarEventCreate(
        title="Daily Standup",
        start_datetime=now,
        end_datetime=now + timedelta(minutes=30),
        timezone="UTC",
        recurrence_rule="FREQ=DAILY;COUNT=5"
    ))
    
    # list events for tomorrow
    tomorrow = now + timedelta(days=1)
    events = calendar_service.list_events(
        start=tomorrow - timedelta(minutes=10), 
        end=tomorrow + timedelta(minutes=40)
    )
    
    assert len(events) >= 1
    assert any(e.title == "Daily Standup" for e in events)
    
    _cleanup(db, ev1.id)
