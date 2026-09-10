import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import opentab.autostart as autostart

from tests._support import _parse


def test_web_autostart_cli_defaults_to_install_and_rejects_static_html():
    args = _parse(["web", "--autostart"])
    assert args.autostart == "install"
    assert args.web is False and args.serve is False

    try:
        _parse(["web", "--autostart", "--html"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("autostart and --html must be mutually exclusive")


def test_web_autostart_cli_names_the_removal_action_remove():
    assert _parse(["web", "--autostart", "remove"]).autostart == "remove"
    try:
        _parse(["web", "--autostart", "uninstall"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("the old uninstall action must not remain in the interface")


def test_systemd_unit_runs_this_install_headlessly_with_web_options():
    args = SimpleNamespace(
        source="all",
        port=9444,
        bind="127.0.0.1",
        vscode_dir="/mnt/c/Users/Fred/App Data/Roaming/Code/User",
        no_cache=True,
    )
    unit = autostart.systemd_unit(
        args, executable="/home/fred/.local/pipx/venvs/opentab/bin/python"
    )

    assert "ExecStart=" in unit
    assert (
        '"/home/fred/.local/pipx/venvs/opentab/bin/python" "-m" "opentab" "web" "--headless"'
        in unit
    )
    assert '"--harness" "all"' in unit
    assert '"--port" "9444"' in unit
    assert '"--vscode-dir" "/mnt/c/Users/Fred/App Data/Roaming/Code/User"' in unit
    assert '"--no-cache"' in unit
    assert "Restart=on-failure" in unit
    assert "WantedBy=default.target" in unit


def test_install_and_remove_manage_the_user_service_atomically():
    with tempfile.TemporaryDirectory() as tmp:
        unit = os.path.join(tmp, "systemd", "user", "opentab-web.service")
        args = SimpleNamespace(
            source="auto", port=8321, bind="127.0.0.1", vscode_dir=None, no_cache=False
        )
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with patch.object(autostart, "service_path", return_value=unit), patch.object(
            autostart.subprocess, "run", side_effect=run
        ):
            assert autostart.configure("install", args) == 0
            assert os.path.isfile(unit)
            assert calls == [
                ["systemctl", "--user", "daemon-reload"],
                ["systemctl", "--user", "enable", "--now", "opentab-web.service"],
            ]
            calls.clear()
            assert autostart.configure("remove", args) == 0
            assert not os.path.exists(unit)
            assert calls == [
                ["systemctl", "--user", "disable", "--now", "opentab-web.service"],
                ["systemctl", "--user", "daemon-reload"],
            ]


def test_wsl_systemd_failure_explains_how_to_enable_it():
    args = SimpleNamespace(
        source="auto", port=8321, bind="127.0.0.1", vscode_dir=None, no_cache=False
    )
    failed = SimpleNamespace(returncode=1, stdout="", stderr="Failed to connect to bus")
    with tempfile.TemporaryDirectory() as tmp, patch.object(
        autostart, "service_path", return_value=os.path.join(tmp, "opentab-web.service")
    ), patch.object(autostart, "is_wsl", return_value=True), patch.object(
        autostart.subprocess, "run", return_value=failed
    ):
        try:
            autostart.configure("install", args)
        except SystemExit as exc:
            text = str(exc)
            assert "/etc/wsl.conf" in text
            assert "systemd=true" in text
            assert "wsl.exe --shutdown" in text
        else:
            raise AssertionError("a failed WSL systemd command must be actionable")
