"""The tuimux application: a session list next to a live preview of the selected session."""

from __future__ import annotations

from pytui import App, Box, ListView, Row, Style, Text, Widget
from pytui.text import truncate

from . import tmux
from .dialogs import Confirm, Modal, Prompt
from .tmux import Session

REFRESH_INTERVAL = 0.5
PANEL = Style(border="rounded", border_fg="bright_black", focus_within=Style(border_fg="cyan"))
HELP = "↑/↓ select · enter/a attach · n new · r rename · d delete · q quit"


class Preview(Widget):
    """The bottom of a list of lines, like a terminal screen."""

    DEFAULT_STYLE = Style(flex_grow=1)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.lines: list[str] = []

    def render(self, canvas) -> None:
        area = self.content_region
        if area.empty:
            return
        for row, line in enumerate(self.lines[-area.height :]):
            canvas.text(area.x, area.y + row, truncate(line, area.width), self.text_style)


class TuiMux:
    def __init__(self) -> None:
        self.sessions: list[Session] = []
        self.list = ListView(on_highlight=lambda *_: self.refresh_preview(), flex_grow=1)
        self.preview = Preview()
        self.preview_panel = Box(self.preview, style=PANEL, flex_grow=1)
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
        for keys, action in bindings.items():
            self.app.bind(keys, action)
        self.app.set_interval(REFRESH_INTERVAL, self.refresh)

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
        if session is None:
            self.preview_panel.title = "Preview"
            self.preview.lines = ["No sessions, press n to create one."]
        else:
            windows = f"{session.windows} window" + "s" * (session.windows > 1)
            self.preview_panel.title = f"{session.name} ({windows})"
            self.preview.lines = session.capture()

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
