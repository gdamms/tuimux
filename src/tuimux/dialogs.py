"""Modal dialogs drawn over the main screen."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pytui import Box, Button, Input, KeyEvent, Row, Style, Text, Widget

from .tmux import TmuxError

DIALOG = Style(
    border="rounded",
    border_fg="cyan",
    bg="default",
    padding=(0, 1),
    gap=1,
    width=50,
    max_width="90%",
)
HINT = Style(dim=True, text_align="center")
INVALID = Style(fg="red", focus=Style(fg="red"))


class Modal(Box):
    """A full-screen overlay holding a centered dialog.

    Covering the screen keeps mouse clicks from reaching the widgets below, and
    handling every key keeps them away from the app bindings.
    """

    DEFAULT_STYLE = Style(
        position="absolute",
        top=0,
        right=0,
        bottom=0,
        left=0,
        align_items="center",
        justify_content="center",
    )

    def __init__(
        self, *children: Widget, title: str, hint: str, focus: Widget | None = None
    ) -> None:
        self.error = Text("", fg="red", display="none")
        super().__init__(
            Box(*children, self.error, Text(hint, style=HINT), style=DIALOG, title=title)
        )
        self.initial_focus = focus
        self.on_close: Callable[[], Any] = lambda: None
        self.bind("escape", self.close)

    def open(self, parent: Widget) -> None:
        parent.mount(self)
        (self.initial_focus or self._focusables()[0]).focus()

    def close(self) -> None:
        self.remove()
        self.on_close()

    def show_error(self, message: str | None) -> None:
        self.error.text = message or ""
        self.error.hidden = not message

    def submit(self, action: Callable[[], Any]) -> None:
        """Run ``action`` and close, or keep the dialog open to show a tmux error."""
        try:
            action()
        except TmuxError as error:
            self.show_error(str(error))
        else:
            self.close()

    def _focusables(self) -> list[Widget]:
        return [w for w in self.walk() if w.focusable]

    def on_key(self, event: KeyEvent) -> bool:
        steps = {"tab": 1, "right": 1, "shift+tab": -1, "left": -1}
        if event.key in steps and self.app is not None:
            widgets = self._focusables()
            current = widgets.index(self.app.focused) if self.app.focused in widgets else 0
            widgets[(current + steps[event.key]) % len(widgets)].focus()
        return True


class Prompt(Modal):
    """Ask for a line of text. ``validate(value)`` returns an error message or None."""

    def __init__(
        self,
        title: str,
        on_submit: Callable[[str], Any],
        *,
        value: str = "",
        placeholder: str = "",
        validate: Callable[[str], str | None] = lambda _: None,
    ) -> None:
        self.validate = validate
        self.on_submit = on_submit
        self.input = Input(
            value, placeholder=placeholder, on_change=self._check, on_submit=self._submit
        )
        super().__init__(self.input, title=title, hint="enter: confirm · esc: cancel")

    def _check(self, value: str) -> str | None:
        error = self.validate(value)
        self.show_error(error)
        self.input.style = INVALID if error else Style()
        return error

    def _submit(self, value: str) -> None:
        if self._check(value) is None:
            self.submit(lambda: self.on_submit(value))


class Confirm(Modal):
    """Ask a yes/no question; "No" is focused by default."""

    def __init__(self, title: str, message: str, on_yes: Callable[[], Any]) -> None:
        yes = Button("Yes", on_press=lambda: self.submit(on_yes))
        no = Button("No", on_press=self.close)
        super().__init__(
            Text(message),
            Row(yes, no, gap=2, justify_content="center", align_self="stretch"),
            title=title,
            hint="y: yes · n/esc: no",
            focus=no,
        )
        self.bind("y", yes.press)
        self.bind("n", self.close)
