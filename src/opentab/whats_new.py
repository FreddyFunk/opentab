"""Validated, offline release highlights shared by the TUI and web report."""

from __future__ import annotations

import json
import re

RELEASES_URL = "https://github.com/hamidi-dev/opentab/releases"
_STABLE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def stable_version(value) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    match = _STABLE.fullmatch(value)
    if not match:
        return None
    if any(len(part) > 32 for part in match.groups()):
        return None
    try:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    except ValueError:
        # Python 3.11+ rejects excessively long decimal strings. State is authored
        # input, so an absurd version must degrade like any other malformed value.
        return None


def _resource_text() -> str:
    from importlib.resources import files

    return files("opentab").joinpath("data").joinpath("whats-new.json").read_text("utf-8")


def load_release_notes(installed_version: str | None = None) -> dict | None:
    """Load only a complete resource for the requested installed stable release."""
    if installed_version is None:
        from opentab import __version__

        installed_version = __version__
    try:
        data = json.loads(_resource_text())
    except Exception:  # noqa: BLE001 -- a missing/broken package resource is non-fatal
        return None
    if not isinstance(data, dict) or stable_version(installed_version) is None:
        return None
    if data.get("version") != installed_version:
        return None
    if not isinstance(data.get("release_url"), str):
        return None
    if not data["release_url"].startswith("https://github.com/hamidi-dev/opentab/releases/"):
        return None
    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        return None
    seen = set()
    for section in sections:
        if not isinstance(section, dict):
            return None
        title = section.get("title")
        if title not in ("New", "Improved", "Fixed") or title in seen:
            return None
        seen.add(title)
        items = section.get("items")
        if not isinstance(items, list) or not items:
            return None
        for item in items:
            if not isinstance(item, dict):
                return None
            if not isinstance(item.get("text"), str) or not item["text"].strip():
                return None
            if item.get("availability", "both") not in ("both", "tui", "web"):
                return None
            hint = item.get("hint")
            if hint is None:
                continue
            if not isinstance(hint, dict) or not isinstance(hint.get("text"), str):
                return None
            binding = hint.get("binding")
            if binding is not None and (
                not isinstance(binding, dict)
                or not isinstance(binding.get("context"), str)
                or not isinstance(binding.get("action"), str)
            ):
                return None
    return data


def should_announce(stored_version, installed_version: str, notes: dict | None) -> bool:
    stored = stable_version(stored_version)
    installed = stable_version(installed_version)
    return bool(
        stored
        and installed
        and notes
        and notes.get("version") == installed_version
        and installed > stored
    )


def marker_to_save(disk_value, installed_version: str) -> str:
    """Keep a newer valid marker written by another or downgraded process."""
    disk = stable_version(disk_value)
    installed = stable_version(installed_version)
    if disk and (not installed or disk > installed):
        return str(disk_value)
    return installed_version if installed else (str(disk_value) if disk else "")


def public_payload(installed_version: str) -> dict:
    notes = load_release_notes(installed_version)
    if notes is not None:
        return notes
    return {
        "version": installed_version,
        "unavailable": True,
        "release_url": RELEASES_URL,
    }
