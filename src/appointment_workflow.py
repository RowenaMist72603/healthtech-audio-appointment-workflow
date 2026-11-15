"""Patient-safe appointment actions after an audio note is transcribed."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AppointmentNote:
    patient_id: str
    appointment_id: str
    transcript: str
    follow_up_requested: bool


@dataclass(frozen=True)
class OperationalAction:
    status: Literal["review", "notify"]
    message: str


def decide_action(note: AppointmentNote) -> OperationalAction:
    """Only send a neutral reminder when the note explicitly requests follow-up."""
    if not note.transcript.strip() or not note.patient_id or not note.appointment_id:
        return OperationalAction("review", "A clinician must review this appointment note.")
    if not note.follow_up_requested:
        return OperationalAction("review", "No patient notification was requested.")
    return OperationalAction("notify", "Appointment follow-up requested; send a neutral reminder.")
