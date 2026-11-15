from src.appointment_workflow import AppointmentNote, decide_action


def test_explicit_follow_up_requests_a_neutral_notification():
    note = AppointmentNote("p-7", "a-3", "Please arrange a follow-up visit.", True)

    action = decide_action(note)

    assert action.status == "notify"
    assert "neutral reminder" in action.message
