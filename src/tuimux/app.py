"""The tuimux application: a session list next to a live preview of the selected session."""

from __future__ import annotations

from pytui import App, Box, Button, ListView, Row, Style, Text, Widget

from . import tmux
from .dialogs import Confirm, Modal, Prompt
from .tmux import Session

REFRESH_INTERVAL = 0.5
PANEL = Style(border="rounded", border_fg="bright_black", focus_within=Style(border_fg="cyan"))
TAB = Style(bg="default", fg="bright_black", hover=Style(fg="white", bg="default"))
ACTIVE_TAB = Style(bg="default", fg="cyan", bold=True, hover=Style(fg="cyan", bg="default"))
SEPARATOR = Style(fg="bright_black", bg="default")
HELP = "↑/↓ select · ←/→ tab · enter/a attach · n new · r rename · d delete · q quit"


TABS = ("preview", "stats", "env", "config")


def size(n: float) -> str:
    for unit in ("B", "K", "M", "G"):
        if n < 1024 or unit == "G":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return ""


def stats_lines(session: Session) -> list[str]:
    procs = session.processes()
    windows = f"{session.windows} window" + "s" * (session.windows > 1)
    lines = [
        f"session {session.name} ({windows})",
        "",
        f"cpu     {sum(p.cpu for p in procs):.1f}%",
        f"memory  {size(sum(p.rss for p in procs))}",
        f"procs   {len(procs)}",
        "",
        f"{'PID':>7} {'CPU%':>6} {'MEM':>7}  COMMAND",
    ]
    return lines + [f"{p.pid:>7} {p.cpu:>6.1f} {size(p.rss):>7}  {p.command}" for p in procs]


def config_lines(session: Session) -> list[str]:
    info = session.info()
    rows = {
        "id": session.id[1:],
        "name": session.name,
        "windows": info["session_windows"],
        "attached": "yes" if session.attached else "no",
        "created": tmux.format_time(info["session_created"]),
        "last activity": tmux.format_time(info["session_activity"]),
        "start directory": info["session_path"],
        "current directory": info["pane_current_path"],
        "current command": info["pane_current_command"],
    }
    return [f"{key:<18}{value}" for key, value in rows.items()]


def env_lines(session: Session) -> list[str]:
    return [f"{key}={value}" for key, value in sorted(session.environment().items())]


class TuiMux:
    def __init__(self) -> None:
        self.sessions: list[Session] = []
        self.tab = TABS[0]
        self.list = ListView(on_highlight=lambda *_: self.select_changed(), flex_grow=1)
        self.preview = Text(overflow="scroll", text_wrap=False, height=0, flex_grow=1)
        self.tabs = {
            t: Button(
                t,
                lambda t=t: self.set_tab(t),
                focusable=False,
                style=ACTIVE_TAB if t == self.tab else TAB,
            )
            for t in TABS
        }
        self.preview_panel = Box(
            Row(*self.tab_bar(), position="absolute", top=-1, left=1),
            self.preview,
            style=PANEL | Style(overflow="visible"),
            width=0,  # size from flex_grow only, so long lines cannot squish the sessions
            flex_grow=1,
        )
        self.root = Box(
            Row(
                Box(self.list, style=PANEL, title="Sessions", width="30%", min_width=20),
                self.preview_panel,
                flex_grow=1,
            ),
            Text(HELP, dim=True, text_wrap=False, padding=(0, 1)),
        )

        self.app = App(self.root)
        self.list.bind("enter", self.attach)
        bindings = {"q escape": self.app.exit, "a": self.attach, "n": self.new}
        bindings |= {"r": self.rename, "d": self.delete}
        bindings |= {"right": lambda: self.switch(1), "left": lambda: self.switch(-1)}
        bindings |= {str(i): lambda t=t: self.set_tab(t) for i, t in enumerate(TABS, 1)}
        for keys, action in bindings.items():
            self.app.bind(keys, action)
        self.app.set_interval(REFRESH_INTERVAL, self.refresh)

    def tab_bar(self) -> list[Widget]:
        bar: list[Widget] = []
        for button in self.tabs.values():
            if bar:
                bar.append(Text("─", style=SEPARATOR, text_wrap=False))
            bar.append(button)
        return bar

    @property
    def selected(self) -> Session | None:
        return None if self.list.index is None else self.sessions[self.list.index]

    # --- refresh ------------------------------------------------------------

    def refresh(self, select: str | None = None) -> None:
        """Reload the sessions, keeping the selection (or selecting the ``select`` id)."""
        current = select or (self.selected and self.selected.id)
        self.sessions = tmux.sessions()
        self.list.items = [s.label for s in self.sessions]
        ids = [s.id for s in self.sessions]
        if current in ids:
            self.list.index = ids.index(current)
        self.refresh_preview()

    def refresh_preview(self) -> None:
        session = self.selected
        content = {
            "preview": lambda: session.capture(),
            "stats": lambda: stats_lines(session),
            "env": lambda: env_lines(session),
            "config": lambda: config_lines(session),
        }[self.tab]
        lines = content() if session else ["No sessions, press n to create one."]
        # Like a terminal, the preview keeps showing the bottom unless scrolled up.
        follow = self.tab == "preview" and self.preview.scroll_y >= self.preview.max_scroll_y
        self.preview.text = "\n".join(lines)
        if follow:
            self.preview.scroll_y = 2**31

    def reset_scroll(self) -> None:
        # Scroll positions are clamped when laid out, so a huge one means the bottom.
        self.preview.scroll_y = 2**31 if self.tab == "preview" else 0

    def select_changed(self) -> None:
        self.reset_scroll()
        self.refresh_preview()

    def set_tab(self, tab: str) -> None:
        self.tab = tab
        for name, button in self.tabs.items():
            button.style = ACTIVE_TAB if name == tab else TAB
        self.reset_scroll()
        self.refresh_preview()

    def switch(self, step: int) -> None:
        self.set_tab(TABS[(TABS.index(self.tab) + step) % len(TABS)])

    # --- actions ------------------------------------------------------------

    def show(self, modal: Modal) -> None:
        def close() -> None:
            self.list.focus()
            self.refresh()

        modal.on_close = close
        modal.open(self.root)

    def name_error(self, name: str, renamed: Session | None = None) -> str | None:
        if any(s.name == name and s != renamed for s in self.sessions):
            return f"a session is already named {name!r}"
        return None

    def new(self) -> None:
        self.show(
            Prompt(
                "New session",
                lambda name: self.refresh(select=tmux.new_session(name)),
                placeholder="leave empty to use the id",
                validate=self.name_error,
            )
        )

    def rename(self) -> None:
        if (session := self.selected) is None:
            return
        self.show(
            Prompt(
                f"Rename {session.name}",
                session.rename,
                value=session.name,
                validate=lambda name: (
                    self.name_error(name, session) or (None if name else "the name cannot be empty")
                ),
            )
        )

    def delete(self) -> None:
        if (session := self.selected) is None:
            return
        self.show(
            Confirm(
                "Delete session",
                f"Delete session {session.name!r} (id {session.id[1:]})?",
                session.kill,
            )
        )

    def attach(self) -> None:
        if self.selected is not None:
            self.app.exit(self.selected)

    # --- running ------------------------------------------------------------

    def run(self) -> None:
        """Run until quit; attaching leaves the UI and comes back on detach."""
        self.refresh()
        while (session := self.app.run()) is not None:
            session.attach()
            self.refresh()


def main() -> None:
    TuiMux().run()
