"""A thin wrapper around the tmux command line."""

from __future__ import annotations

import os
import subprocess
import time
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

    def pane_pids(self) -> list[int]:
        """Pids of the processes started in each pane of the session."""
        out = tmux("list-panes", "-s", "-t", self.id, "-F", "#{pane_pid}", check=False)
        return [int(p) for p in out.split()]

    def processes(self) -> list[Process]:
        """Every process running in the session's panes (shells and their descendants)."""
        table = process_table()
        children: dict[int, list[Process]] = {}
        for proc in table.values():
            children.setdefault(proc.ppid, []).append(proc)
        found: list[Process] = []
        stack = [table[p] for p in self.pane_pids() if p in table]
        while stack:
            proc = stack.pop()
            found.append(proc)
            stack.extend(children.get(proc.pid, []))
        return sorted(found, key=lambda p: (-p.cpu, -p.rss, p.pid))

    def environment(self) -> dict[str, str]:
        """Environment of the active pane's process, or tmux's session environment."""
        pid = self.info().get("pane_pid", "")
        try:
            with open(f"/proc/{pid}/environ", "rb") as f:
                raw = f.read().decode(errors="replace")
            return dict(item.partition("=")[::2] for item in raw.split("\0") if item)
        except OSError:
            out = tmux("show-environment", "-t", self.id, check=False)
            return dict(line.partition("=")[::2] for line in out.splitlines() if "=" in line)

    def info(self) -> dict[str, str]:
        """Formats describing the session and its active pane."""
        keys = ("session_created", "session_activity", "session_path", "pane_current_path")
        keys += ("pane_current_command", "pane_pid", "session_windows")
        out = tmux("display-message", "-p", "-t", self.id, _SEP.join(f"#{{{k}}}" for k in keys))
        return dict(zip(keys, out.rstrip("\n").split(_SEP)))

    def rename(self, name: str) -> None:
        tmux("rename-session", "-t", self.id, name)

    def kill(self) -> None:
        tmux("kill-session", "-t", self.id)

    def attach(self) -> None:
        """Attach the terminal to the session, or switch to it when already inside tmux."""
        command = "switch-client" if os.environ.get("TMUX") else "attach-session"
        subprocess.run(["tmux", command, "-t", self.id])


@dataclass(frozen=True)
class Process:
    pid: int
    ppid: int
    cpu: float
    rss: int  # bytes
    command: str


def process_table() -> dict[int, Process]:
    out = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,pcpu=,rss=,args="], capture_output=True, text=True
    ).stdout
    table = {}
    for line in out.splitlines():
        pid, ppid, cpu, rss, *command = line.split(None, 4)
        table[int(pid)] = Process(
            int(pid), int(ppid), float(cpu), int(rss) * 1024, "".join(command)
        )
    return table


def format_time(timestamp: str) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(timestamp)))


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
