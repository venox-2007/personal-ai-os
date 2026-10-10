from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.recommendation import RecommendationListResponse, RecommendationResponse
from app.services.proactive_service import proactive_service

router = APIRouter()

@router.get("", response_model=RecommendationListResponse)
def get_recommendations(db: Session = Depends(get_db)):
    """Retrieve active recommendations."""
    # Ensure they are up-to-date
    proactive_service.refresh_recommendations()
    
    recs = proactive_service.get_active_recommendations(db)
    return RecommendationListResponse(
        items=recs,
        total=len(recs)
    )

@router.post("/refresh", response_model=dict)
def refresh_recommendations_endpoint():
    """Trigger a recommendation refresh manually."""
    proactive_service.refresh_recommendations(force=True)
    return {"status": "success", "message": "Recommendations refreshed."}

@router.patch("/{rec_id}/dismiss", response_model=dict)
def dismiss_recommendation(rec_id: str, db: Session = Depends(get_db)):
    """Dismiss a recommendation."""
    success = proactive_service.update_status(db, rec_id, "dismissed")
    if not success:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return {"status": "success", "message": "Recommendation dismissed."}

@router.patch("/{rec_id}/complete", response_model=dict)
def complete_recommendation(rec_id: str, db: Session = Depends(get_db)):
    """Mark a recommendation completed."""
    success = proactive_service.update_status(db, rec_id, "completed")
    if not success:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return {"status": "success", "message": "Recommendation completed."}
