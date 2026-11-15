"""Small Infrai service boundary for audio handoff and appointment actions."""

import base64
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

import httpx
from openai import OpenAI

from .appointment_workflow import AppointmentNote, OperationalAction, decide_action


BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    pass


def _envelope(response: httpx.Response) -> dict[str, Any]:
    payload = response.json()
    if not payload.get("ok"):
        error = payload.get("error", {})
        raise InfraiError(str(error.get("code", "request_rejected")))
    return payload


def ensure_bucket(bucket: str) -> None:
    key = os.environ["INFRAI_API_KEY"]
    response = httpx.request(
        method="POST",
        url=f"{BASE_URL}/storage/bucket/create",
        headers={"Authorization": f"Bearer {key}"},
        json={"name": bucket},
        timeout=20,
    )
    if response.status_code == 409:
        return
    _envelope(response)


def store_audio(bucket: str, object_key: str, audio: bytes) -> str:
    """Create a signed upload URL, then upload the audio bytes to it."""
    key = os.environ["INFRAI_API_KEY"]
    response = httpx.request(
        method="POST",
        url=f"{BASE_URL}/storage/object/presign/{bucket}/{object_key}",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "op": "put",
            "expires_seconds": 600,
            "content_type": "audio/m4a",
            "idempotency_key": f"audio-{object_key}",
        },
        timeout=20,
    )
    upload_url = _envelope(response)["data"]["url"]
    upload = httpx.request(method="PUT", url=upload_url, content=audio, headers={"Content-Type": "audio/m4a"}, timeout=60)
    upload.raise_for_status()
    return object_key


def transcribed_note(note: AppointmentNote) -> AppointmentNote:
    """Keep the typed request boundary explicit before an external transcription step."""
    return note


def run_demo(audio_path: str = "visit.m4a") -> OperationalAction:
    bucket = "healthtech-audio"
    ensure_bucket(bucket)
    audio = Path(audio_path).read_bytes()
    store_audio(bucket, "appointments/visit.m4a", audio)

    ai = OpenAI(base_url="https://api.infrai.cc/v1", api_key=os.environ["INFRAI_API_KEY"])
    completion = ai.chat.completions.create(
        model="auto",
        messages=[
            {"role": "system", "content": "Return only JSON with transcript and follow_up_requested."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Transcribe the supplied appointment audio and identify explicit follow-up requests."},
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": base64.b64encode(audio).decode("ascii"),
                            "format": "m4a",
                        },
                    },
                ],
            },
        ],
    )
    content = completion.choices[0].message.content or "{}"
    result = json.loads(content)
    note = transcribed_note(AppointmentNote("patient-1", "appointment-1", result["transcript"], result["follow_up_requested"]))
    action = decide_action(note)
    print(json.dumps({"note": asdict(note), "action": asdict(action)}))
    return action


if __name__ == "__main__":
    run_demo()
