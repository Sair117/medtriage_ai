from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Urgency(str, Enum):
    EMERGENCY = "emergency"
    URGENT = "urgent"
    ROUTINE = "routine"
    UNKNOWN = "unknown"


class Department(str, Enum):
    EMERGENCY = "Emergency Medicine"
    CARDIOLOGY = "Cardiology"
    ORTHOPEDICS = "Orthopedics"
    DERMATOLOGY = "Dermatology"
    GASTROENTEROLOGY = "Gastroenterology"
    NEUROLOGY = "Neurology"
    RESPIRATORY = "Respiratory / Pulmonology"
    ENT = "ENT (Ear, Nose & Throat)"
    GENERAL = "General Practice"
    MENTAL_HEALTH = "Mental Health"


class PatientInfo(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    symptoms: list[str] = Field(default_factory=list)
    symptom_duration: Optional[str] = None
    allergies: Optional[str] = None
    current_medications: Optional[str] = None
    medical_history: Optional[str] = None


class TriageSummary(BaseModel):
    urgency: Urgency = Urgency.UNKNOWN
    department: Optional[str] = None
    chief_complaint: Optional[str] = None
    summary: Optional[str] = None
    recommendations: Optional[str] = None
    escalation_reason: Optional[str] = None


class ConversationPhase(str, Enum):
    GREETING = "greeting"
    SYMPTOM_COLLECTION = "symptom_collection"
    URGENCY_ASSESSMENT = "urgency_assessment"
    INFO_GATHERING = "info_gathering"
    CLASSIFICATION = "classification"
    ROUTING = "routing"
    ESCALATION = "escalation"
    COMPLETE = "complete"


class AgentState(BaseModel):
    """Full state tracked across the conversation."""
    messages: list[dict] = Field(default_factory=list)
    phase: ConversationPhase = ConversationPhase.GREETING
    patient: PatientInfo = Field(default_factory=PatientInfo)
    triage: TriageSummary = Field(default_factory=TriageSummary)
    turn_count: int = 0
    needs_escalation: bool = False
    rag_context: Optional[str] = None
