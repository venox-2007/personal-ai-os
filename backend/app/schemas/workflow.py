from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class WorkflowPlanStep(BaseModel):
    step_id: str = Field(..., description="Unique logical ID for this step, e.g., 'step_1'")
    agent: str = Field(..., description="Agent name to execute this step")
    action: str = Field(..., description="Description of what this step does")
    tool_name: str = Field(..., description="Exact registered tool name to execute")
    input_mapping: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments, supporting references like ${step_1.output.id}")
    depends_on: List[str] = Field(default_factory=list, description="List of step_ids this step depends on")
    requires_approval: bool = Field(False, description="Whether this step inherently requires user approval (derived from tool permissions)")
    on_failure: str = Field("FAIL", description="Action on failure: 'FAIL' or 'SKIP'")

class WorkflowPlan(BaseModel):
    goal: str = Field(..., description="The overall goal of this workflow")
    steps: List[WorkflowPlanStep] = Field(..., description="Sequential list of steps to execute")
    max_steps: int = Field(10, description="Maximum number of steps")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class WorkflowStepResponse(BaseModel):
    id: str
    step_id: str
    sequence: int
    agent_name: str
    tool_name: str
    input_mapping_json: str
    depends_on_json: str
    status: str
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    requires_approval: bool
    on_failure: str
    output_json: Optional[str] = None
    approval_id: Optional[str] = None
    
    class Config:
        from_attributes = True

class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    goal: str
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    synthesis_result: Optional[str] = None
    steps: List[WorkflowStepResponse] = []

    class Config:
        from_attributes = True
