from datetime import datetime, timedelta, timezone
import hashlib
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.entities import (
    CalendarEventModel,
    WorkflowModel,
    MemoryModel,
    RecommendationModel
)
from app.database.session import SessionLocal

def compute_dedup_key(category: str, entity_id: str, rule: str) -> str:
    """Generate a stable deduplication key for a recommendation."""
    raw = f"{category}:{entity_id}:{rule}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

class ProactiveService:
    def refresh_recommendations(self):
        """Generates proactive recommendations based on existing local data."""
        with SessionLocal() as db:
            self._expire_stale_recommendations(db)
            self._generate_calendar_recommendations(db)
            self._generate_workflow_recommendations(db)
            db.commit()

    def _expire_stale_recommendations(self, db: Session):
        """Expire recommendations whose due date has passed by a margin, or events that happened."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        active_recs = db.query(RecommendationModel).filter(RecommendationModel.status == "active").all()
        for rec in active_recs:
            if rec.due_at and now > rec.due_at + timedelta(hours=1):
                rec.status = "expired"

    def _generate_calendar_recommendations(self, db: Session):
        """Recommend preparation for upcoming meetings."""
        now = datetime.now(timezone.utc).replace(tzinfo=None) # Align with DB timezone logic
        upcoming_window = now + timedelta(days=2)
        
        events = db.query(CalendarEventModel).filter(
            CalendarEventModel.start_datetime >= now,
            CalendarEventModel.start_datetime <= upcoming_window,
            CalendarEventModel.status != "CANCELLED"
        ).all()
        
        for ev in events:
            # E.g., remind user to prepare for meeting
            dedup_key = compute_dedup_key("calendar", ev.id, "upcoming_prep")
            
            # Check if exists
            existing = db.query(RecommendationModel).filter(RecommendationModel.deduplication_key == dedup_key).first()
            if not existing:
                time_until = ev.start_datetime - now
                if time_until < timedelta(hours=24):
                    priority = 2
                else:
                    priority = 1
                    
                rec = RecommendationModel(
                    category="calendar",
                    title=f"Prepare for: {ev.title}",
                    description=f"You have an event coming up. Consider preparing notes or reviewing materials.",
                    reason=f"Event '{ev.title}' starts on {ev.start_datetime.strftime('%Y-%m-%d %H:%M')}.",
                    priority=priority,
                    status="active",
                    deduplication_key=dedup_key,
                    suggested_agent="Research",
                    suggested_workflow_goal=f"Research background context for my upcoming event: {ev.title}",
                    due_at=ev.start_datetime
                )
                db.add(rec)

    def _generate_workflow_recommendations(self, db: Session):
        """Recommend returning to interrupted or pending workflows."""
        workflows = db.query(WorkflowModel).filter(
            WorkflowModel.status.in_(["PENDING", "WAITING_APPROVAL"])
        ).all()
        
        for wf in workflows:
            dedup_key = compute_dedup_key("workflow", wf.id, "pending_attention")
            existing = db.query(RecommendationModel).filter(RecommendationModel.deduplication_key == dedup_key).first()
            
            if not existing:
                rec = RecommendationModel(
                    category="workflow",
                    title=f"Action required: Workflow '{wf.name}'",
                    description=f"A workflow is currently stuck in {wf.status} state.",
                    reason=f"Workflow was created at {wf.created_at.strftime('%Y-%m-%d')} and needs attention.",
                    priority=3 if wf.status == "WAITING_APPROVAL" else 2,
                    status="active",
                    deduplication_key=dedup_key
                )
                db.add(rec)

    def get_active_recommendations(self, db: Session) -> List[RecommendationModel]:
        return db.query(RecommendationModel).filter(RecommendationModel.status == "active").order_by(RecommendationModel.priority.desc(), RecommendationModel.created_at.desc()).all()

    def update_status(self, db: Session, rec_id: str, new_status: str) -> bool:
        rec = db.query(RecommendationModel).filter(RecommendationModel.id == rec_id).first()
        if rec and new_status in ["active", "dismissed", "completed", "expired"]:
            rec.status = new_status
            db.commit()
            return True
        return False

proactive_service = ProactiveService()
