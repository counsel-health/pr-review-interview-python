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


def get_patient_by_phone(phone: str) -> ApiUser | None:
    """
    The patient registered at a phone number, or None if there isn't one.

    Used by the inbound Relay webhook to map a message's ``from`` address onto a
    patient.
    """
    patient = Patient.objects.filter(phone=phone).first()
    return to_user(patient) if patient else None
