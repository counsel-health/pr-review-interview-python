"""Read access to patients, mapped to the ApiUser DTO."""

from __future__ import annotations

from core.dto import ApiUser
from core.models import Patient


def to_user(patient: Patient) -> ApiUser:
    return {"id": patient.id, "name": patient.name, "is_physician": False}


def list_patients() -> list[ApiUser]:
    return [to_user(p) for p in Patient.objects.all()]


def get_patient_by_id(patient_id: str) -> ApiUser | None:
    patient = Patient.objects.filter(id=patient_id).first()
    return to_user(patient) if patient else None
