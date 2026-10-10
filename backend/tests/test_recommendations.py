import pytest
from datetime import datetime, timedelta, timezone
from app.models.entities import CalendarEventModel, WorkflowModel, RecommendationModel
from app.services.proactive_service import proactive_service
from app.database.session import SessionLocal, init_db

@pytest.fixture
def db_session():
    init_db()
    with SessionLocal() as db:
        # cleanup
        db.query(RecommendationModel).delete()
        db.query(CalendarEventModel).delete()
        db.query(WorkflowModel).delete()
        db.commit()
        yield db
        db.query(RecommendationModel).delete()
        db.query(CalendarEventModel).delete()
        db.query(WorkflowModel).delete()
        db.commit()

def test_empty_sources(db_session):
    proactive_service.refresh_recommendations(force=True)
    db_session.expire_all()
    recs = proactive_service.get_active_recommendations(db_session)
    assert len(recs) == 0

def test_calendar_recommendations(db_session):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    # Event starting in 12 hours (High priority)
    ev1 = CalendarEventModel(
        title="Important Meeting",
        start_datetime=now + timedelta(hours=12),
        end_datetime=now + timedelta(hours=13)
    )
    # Event starting in 36 hours (Low priority)
    ev2 = CalendarEventModel(
        title="Future Sync",
        start_datetime=now + timedelta(hours=36),
        end_datetime=now + timedelta(hours=37)
    )
    
    db_session.add(ev1)
    db_session.add(ev2)
    db_session.commit()

    proactive_service.refresh_recommendations(force=True)
    db_session.expire_all()
    recs = proactive_service.get_active_recommendations(db_session)
    
    assert len(recs) == 2
    # Ensure ranked by priority (2 > 1)
    assert recs[0].priority == 2
    assert "Important Meeting" in recs[0].title
    assert recs[1].priority == 1
    assert "Future Sync" in recs[1].title

def test_deduplication(db_session):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ev1 = CalendarEventModel(
        title="Deduplication Test",
        start_datetime=now + timedelta(hours=12),
        end_datetime=now + timedelta(hours=13)
    )
    db_session.add(ev1)
    db_session.commit()

    # First refresh
    proactive_service.refresh_recommendations(force=True)
    db_session.expire_all()
    recs1 = proactive_service.get_active_recommendations(db_session)
    assert len(recs1) == 1

    # Second refresh
    proactive_service.refresh_recommendations(force=True)
    db_session.expire_all()
    recs2 = proactive_service.get_active_recommendations(db_session)
    assert len(recs2) == 1
    assert recs1[0].id == recs2[0].id

def test_dismissal_and_completion(db_session):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    wf = WorkflowModel(name="Stuck Workflow", goal="Test", status="PENDING")
    db_session.add(wf)
    db_session.commit()

    proactive_service.refresh_recommendations(force=True)
    db_session.expire_all()
    recs = proactive_service.get_active_recommendations(db_session)
    assert len(recs) == 1
    rec_id = recs[0].id

    # Dismiss
    assert proactive_service.update_status(db_session, rec_id, "dismissed") == True
    db_session.expire_all()
    recs = proactive_service.get_active_recommendations(db_session)
    assert len(recs) == 0

def test_stale_expiration(db_session):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    # Create a recommendation that was due 2 hours ago
    rec = RecommendationModel(
        category="calendar",
        title="Expired Event",
        description="This event has passed",
        reason="Testing expiration",
        priority=1,
        status="active",
        deduplication_key="test_stale_1",
        due_at=now - timedelta(hours=2)
    )
    db_session.add(rec)
    db_session.commit()

    db_session.expire_all()
    recs = proactive_service.get_active_recommendations(db_session)
    assert len(recs) == 1

    proactive_service.refresh_recommendations(force=True)
    
    db_session.expire_all()
    recs = proactive_service.get_active_recommendations(db_session)
    assert len(recs) == 0
