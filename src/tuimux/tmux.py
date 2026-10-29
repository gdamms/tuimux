"""A thin wrapper around the tmux command line."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

_FIELDS = ("session_id", "session_name", "session_windows", "session_attached")
_SEP = "\x1f"


class TmuxError(RuntimeError):
    pass


def tmux(*args: str, check: bool = True) -> str:
    result = subprocess.run(["tmux", *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise TmuxError(result.stderr.strip() or f"tmux {args[0]} failed")
    return result.stdout


@dataclass(frozen=True)
class Session:
    id: str
    name: str
    windows: int
    attached: bool

    @property
    def label(self) -> str:
        return f"{self.id[1:]}: {self.name}" + (" *" if self.attached else "")

    def capture(self) -> list[str]:
        """Visible content of the session's active pane, without trailing blank lines."""
        lines = tmux("capture-pane", "-p", "-t", self.id, check=False).splitlines()
        while lines and not lines[-1].strip():
            lines.pop()
        return lines

    def rename(self, name: str) -> None:
        tmux("rename-session", "-t", self.id, name)

    def kill(self) -> None:
        tmux("kill-session", "-t", self.id)

    def attach(self) -> None:
        """Attach the terminal to the session, or switch to it when already inside tmux."""
        command = "switch-client" if os.environ.get("TMUX") else "attach-session"
        subprocess.run(["tmux", command, "-t", self.id])


def sessions() -> list[Session]:
    # Fails when no server is running, which just means there are no sessions.
    output = tmux("list-sessions", "-F", _SEP.join(f"#{{{f}}}" for f in _FIELDS), check=False)
    found = []
    for line in output.splitlines():
        id, name, windows, attached = line.split(_SEP)
        found.append(Session(id, name, int(windows), attached != "0"))
    return sorted(found, key=lambda s: int(s.id[1:]))


def new_session(name: str = "") -> str:
    """Create a detached session and return its id."""
    args = ["new-session", "-d", "-P", "-F", "#{session_id}"]
    if name:
        args += ["-s", name]
    return tmux(*args).strip()
