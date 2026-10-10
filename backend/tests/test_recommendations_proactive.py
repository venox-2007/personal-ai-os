import pytest
from datetime import datetime, timedelta, timezone
from app.services.proactive_service import proactive_service, ProactiveService
from app.models.entities import RecommendationModel, CalendarEventModel, WorkflowModel
from app.database.session import SessionLocal

@pytest.fixture
def db_session():
    db = SessionLocal()
    # Clean up recommendations and events for the test
    db.query(RecommendationModel).delete()
    db.query(CalendarEventModel).delete()
    db.query(WorkflowModel).delete()
    db.commit()
    yield db
    db.query(RecommendationModel).delete()
    db.query(CalendarEventModel).delete()
    db.query(WorkflowModel).delete()
    db.commit()
    db.close()

def test_refresh_debounce(db_session):
    """Ensure refresh_recommendations respects the 5-minute cooldown."""
    service = ProactiveService()
    
    # First call should succeed and set last_refresh_time
    service.refresh_recommendations()
    assert service._last_refresh_time is not None
    
    first_refresh = service._last_refresh_time
    
    # Second call immediately should be ignored
    service.refresh_recommendations()
    assert service._last_refresh_time == first_refresh
    
    # Force call should override
    service.refresh_recommendations(force=True)
    assert service._last_refresh_time > first_refresh

def test_duplicate_prevention_and_dismissal(db_session):
    """Ensure dismissed recommendations do not reappear."""
    service = ProactiveService()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    # Create an upcoming event
    event = CalendarEventModel(
        title="Test Sync",
        start_datetime=now + timedelta(hours=10),
        end_datetime=now + timedelta(hours=11)
    )
    db_session.add(event)
    db_session.commit()
    
    # First refresh generates the recommendation
    service.refresh_recommendations(force=True)
    recs = service.get_active_recommendations(db_session)
    assert len(recs) == 1
    assert "Test Sync" in recs[0].title
    
    rec_id = recs[0].id
    
    # Dismiss it
    success = service.update_status(db_session, rec_id, "dismissed")
    assert success
    
    # Refresh again (forced)
    service.refresh_recommendations(force=True)
    
    # Should not reappear as active
    recs_after = service.get_active_recommendations(db_session)
    assert len(recs_after) == 0

def test_truncation_safety(db_session):
    """Ensure extremely long titles do not crash the DB."""
    service = ProactiveService()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    long_title = "A" * 300
    event = CalendarEventModel(
        title=long_title,
        start_datetime=now + timedelta(hours=10),
        end_datetime=now + timedelta(hours=11)
    )
    db_session.add(event)
    db_session.commit()
    
    # Should not raise DataError/String data right truncation
    service.refresh_recommendations(force=True)
    recs = service.get_active_recommendations(db_session)
    assert len(recs) == 1
    assert len(recs[0].title) <= 255
