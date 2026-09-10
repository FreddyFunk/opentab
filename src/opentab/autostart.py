"""Install the live web report as a systemd user service."""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import tempfile

SERVICE_NAME = "opentab-web.service"


def service_path() -> str:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if not config_home or not os.path.isabs(config_home):
        config_home = os.path.expanduser("~/.config")
    return os.path.join(config_home, "systemd", "user", SERVICE_NAME)


def is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        return True
    try:
        with open("/proc/sys/kernel/osrelease", encoding="utf-8") as fh:
            return "microsoft" in fh.read().lower()
    except OSError:
        return False


def _quote(value: object) -> str:
    text = str(value).replace("%", "%%").replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def _service_argv(args, executable: str) -> list[str]:
    argv = [executable, "-m", "opentab", "web", "--headless"]
    value_options = (
        ("source", "--harness"),
        ("db", "--db"),
        ("claude_dir", "--claude-dir"),
        ("codex_dir", "--codex-dir"),
        ("hermes_db", "--hermes-db"),
        ("copilot_dir", "--copilot-dir"),
        ("vscode_dir", "--vscode-dir"),
        ("pi_dir", "--pi-dir"),
        ("omp_dir", "--omp-dir"),
        ("openclaw_dir", "--openclaw-dir"),
        ("zaly_dir", "--zaly-dir"),
        ("gemini_dir", "--gemini-dir"),
        ("antigravity_dir", "--antigravity-dir"),
        ("csv", "--csv"),
        ("jsonl", "--jsonl"),
        ("days", "--days"),
        ("since", "--since"),
        ("until", "--until"),
        ("demo", "--demo"),
        ("remotes", "--remotes"),
        ("label", "--label"),
        ("theme", "--theme"),
        ("port", "--port"),
        ("bind", "--bind"),
    )
    for attr, option in value_options:
        value = getattr(args, attr, None)
        if value is not None:
            argv.extend((option, value))
    for attr, option in (
        ("no_state", "--no-state"),
        ("no_worktrees", "--no-worktrees"),
        ("no_cache", "--no-cache"),
    ):
        if getattr(args, attr, False):
            argv.append(option)
    return argv


def systemd_unit(args, executable: str | None = None) -> str:
    argv = _service_argv(args, executable or sys.executable)
    command = " ".join(_quote(part) for part in argv)
    return (
        "[Unit]\n"
        "Description=OpenTab web report\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"ExecStart={command}\n"
        "Restart=on-failure\n"
        "RestartSec=3\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def _write_atomic(path: str, content: str) -> None:
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".opentab-web-", dir=directory, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        try:
            os.remove(temporary)
        except FileNotFoundError:
            pass


def _run_systemctl(*arguments: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["systemctl", "--user", *arguments],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"could not run systemctl --user: {exc}") from exc


def _failure(result: subprocess.CompletedProcess) -> SystemExit:
    detail = (result.stderr or result.stdout or "systemctl failed").strip()
    if is_wsl():
        return SystemExit(
            "WSL autostart requires systemd. Add these lines to /etc/wsl.conf:\n"
            "\n[boot]\nsystemd=true\n\n"
            "Then run `wsl.exe --shutdown` from Windows, reopen WSL, and retry.\n"
            f"systemctl: {detail}"
        )
    return SystemExit(f"could not configure the OpenTab user service: {detail}")


def configure(action: str, args) -> int:
    if platform.system() != "Linux":
        raise SystemExit("web autostart currently requires Linux or WSL with systemd")

    path = service_path()
    if action == "status":
        enabled = _run_systemctl("is-enabled", SERVICE_NAME)
        active = _run_systemctl("is-active", SERVICE_NAME)
        print(
            f"OpenTab web autostart: {(enabled.stdout or 'disabled').strip()}; "
            f"service: {(active.stdout or 'inactive').strip()}"
        )
        return 0 if enabled.returncode == 0 and active.returncode == 0 else 1

    if action == "remove":
        _run_systemctl("disable", "--now", SERVICE_NAME)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        result = _run_systemctl("daemon-reload")
        if result.returncode:
            raise _failure(result)
        print("OpenTab web autostart removed")
        return 0

    _write_atomic(path, systemd_unit(args))
    result = _run_systemctl("daemon-reload")
    if result.returncode:
        raise _failure(result)
    result = _run_systemctl("enable", "--now", SERVICE_NAME)
    if result.returncode:
        raise _failure(result)
    print("OpenTab web will start automatically at http://localhost:%s/" % args.port)
    return 0
