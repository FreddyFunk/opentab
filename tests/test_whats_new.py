import json
from unittest.mock import patch

import opentab as ot
from opentab import whats_new


def test_bundled_release_notes_match_the_installed_version_and_schema():
    notes = whats_new.load_release_notes(ot.__version__)
    assert notes is not None
    assert notes["version"] == ot.__version__
    assert notes["sections"]
    assert notes["release_url"].endswith("/tag/v" + ot.__version__)


def test_release_notes_fail_closed_for_missing_malformed_and_mismatched_resources():
    for raw in ("{broken", "[]", json.dumps({"version": ot.__version__})):
        with patch.object(whats_new, "_resource_text", return_value=raw):
            assert whats_new.load_release_notes(ot.__version__) is None
    with patch.object(whats_new, "_resource_text", side_effect=FileNotFoundError):
        assert whats_new.load_release_notes(ot.__version__) is None
    assert whats_new.load_release_notes("9.9.9") is None


def test_upgrade_detection_is_numeric_stable_and_requires_matching_notes():
    notes = {"version": "1.10.0"}
    assert whats_new.should_announce("1.9.0", "1.10.0", notes)
    for stored, installed in (
        (None, "1.10.0"),
        ("broken", "1.10.0"),
        ("1.10.0", "1.10.0"),
        ("1.11.0", "1.10.0"),
        ("1.9.0rc1", "1.10.0"),
        ("1.9.0", "1.10.0rc1"),
    ):
        assert not whats_new.should_announce(stored, installed, notes)
    assert not whats_new.should_announce("1.9.0", "1.10.0", None)
    assert not whats_new.should_announce("1.9.0", "1.10.0", {"version": "1.9.0"})


def test_release_notes_allow_a_single_fix_without_features_or_promotional_copy():
    for title in ("New", "Improved", "Fixed"):
        notes = {
            "version": ot.__version__,
            "release_url": whats_new.RELEASES_URL + "/tag/v" + ot.__version__,
            "sections": [{"title": title, "items": [{"text": "A user-visible change."}]}],
        }
        with patch.object(whats_new, "_resource_text", return_value=json.dumps(notes)):
            assert whats_new.load_release_notes() == notes
            assert whats_new.public_payload(ot.__version__) == notes


def test_release_note_sections_reject_empty_duplicate_and_malformed_entries():
    fixed = {"title": "Fixed", "items": [{"text": "Corrected an estimate."}]}
    bad_sections = (
        None,
        [],
        {},
        [None],
        [fixed, fixed],
        [{"title": [], "items": fixed["items"]}],
        [{"title": "Unknown", "items": fixed["items"]}],
        [{"title": "New", "items": []}],
        [{"title": "Fixed", "items": [None]}],
        [{"title": "Fixed", "items": [{"text": " "}]}],
        [{"title": "Fixed", "items": [{"text": "a", "availability": []}]}],
        [{"title": "Fixed", "items": [{"text": "a", "hint": "bad"}]}],
        [{"title": "Fixed", "items": [{"text": "a", "hint": {"text": "b", "binding": {}}}]}],
    )
    for sections in bad_sections:
        notes = {
            "version": ot.__version__,
            "release_url": whats_new.RELEASES_URL + "/tag/v" + ot.__version__,
            "sections": sections,
        }
        with patch.object(whats_new, "_resource_text", return_value=json.dumps(notes)):
            assert whats_new.load_release_notes() is None


def test_stable_version_rejects_malformed_types_and_oversized_digits():
    for value in (None, 1, [], {}, ["1.2.3"], "1.2", "01.2.3", "1.2.3.4"):
        assert whats_new.stable_version(value) is None
    assert whats_new.stable_version("9" * 10_000 + ".2.3") is None


def test_marker_merge_never_replaces_a_newer_valid_disk_value():
    assert whats_new.marker_to_save("1.22.0", "1.21.0") == "1.22.0"
    assert whats_new.marker_to_save("1.20.0", "1.21.0") == "1.21.0"
    assert whats_new.marker_to_save("broken", "1.21.0") == "1.21.0"
    assert whats_new.marker_to_save("1.22.0", "broken") == "1.22.0"


def test_public_payload_degrades_to_the_official_releases_page():
    with patch.object(whats_new, "load_release_notes", return_value=None):
        payload = whats_new.public_payload("1.21.0")
    assert payload == {
        "version": "1.21.0",
        "unavailable": True,
        "release_url": whats_new.RELEASES_URL,
    }


def test_disabled_automatic_hints_stay_quiet_but_manual_viewing_works():
    from tests._support import app_with

    app = app_with([])
    app.last_announced_version = "1.20.0"
    assert app.whats_new_marker_to_save is None
    app.configure_whats_new_hint(ot.__version__, enabled=False)
    assert not app._whats_new_hint_pending and not app.notice
    assert app.whats_new_marker_to_save is None
    app.open_whats_new()
    assert app.whats_new and app.whats_new_marker_to_save == ot.__version__
