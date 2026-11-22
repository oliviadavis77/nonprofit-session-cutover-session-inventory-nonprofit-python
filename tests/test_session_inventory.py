import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from session_inventory import SessionRecord, keep_current_session


def test_nonprofit_operator_keeps_current_session_and_signs_out_others() -> None:
    sessions = [
        SessionRecord("mobile", "phone", False),
        SessionRecord("desk", "browser", True),
        SessionRecord("tablet", "tablet", False),
    ]

    retained, revoked = keep_current_session(sessions)

    assert [session.session_id for session in retained] == ["desk"]
    assert revoked == ["mobile", "tablet"]
