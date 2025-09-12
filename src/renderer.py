import os

from .ansi import ANSI


class Renderer:

    BOX_CORNER_TOP_LEFT = '╭'
    BOX_CORNER_TOP_RIGHT = '╮'
    BOX_CORNER_BOTTOM_LEFT = '╰'
    BOX_CORNER_BOTTOM_RIGHT = '╯'
    BOX_HORIZONTAL = '─'
    BOX_VERTICAL = '│'
    BOX_TITLE_LEFT = '╴'
    BOX_TITLE_RIGHT = '╶'

    def __init__(self):
        self.buffer = ''

    def render(self, file=None):
        self.move_cursor(1, 1)
        print(self.buffer, file=file, end='', flush=True)
        self.clear()

    def clear(self):
        self.buffer = ''

    def write(self, x):
        self.buffer += x

    def hide_cursor(self):
        self.write(ANSI.HIDE_CURSOR)

    def show_cursor(self):
        self.write(ANSI.SHOW_CURSOR)

    def primary_context(self):
        self.write(ANSI.PRIMARY_CONTEXT)

    def secondary_context(self):
        self.write(ANSI.SECONDARY_CONTEXT)

    def clear_screen(self):
        self.write(ANSI.CLEAR_SCREEN)

    def move_cursor(self, x, y):
        self.write(ANSI.MOVE_CURSOR.format(y, x))

    def invert_colors(self):
        self.write(ANSI.INVERT_COLORS)

    def revert_colors(self):
        self.write(ANSI.REVERT_COLORS)

    def reset_color(self):
        self.write(ANSI.RESET_COLOR)

    def color(self, foreground=None, background=None):
        if foreground is None and background is None:
            self.reset_color()
            return

        if foreground in ANSI.FOREGROUND_COLORS:
            self.write(ANSI.FOREGROUND_COLORS[foreground])
        if background in ANSI.BACKGROUND_COLORS:
            self.write(ANSI.BACKGROUND_COLORS[background])

    def box(self, x, y, w, h, title=None):
        max_w, max_h = os.get_terminal_size()

        assert x >= 1 and y >= 1 and w >= 2 and h >= 2
        assert x + w - 1 <= max_w and y + h - 1 <= max_h
        assert title is None or len(title) <= w - 4

        self.move_cursor(x, y)
        self.write(self.BOX_CORNER_TOP_LEFT)
        if title:
            top_bar = self.BOX_TITLE_LEFT + title + self.BOX_TITLE_RIGHT
            top_bar = top_bar.ljust(w - 2, self.BOX_HORIZONTAL)
        else:
            top_bar = self.BOX_HORIZONTAL * (w - 2)
        self.write(top_bar)
        self.write(self.BOX_CORNER_TOP_RIGHT)
        for i in range(h - 2):
            self.move_cursor(x, y + i + 1)
            self.write(self.BOX_VERTICAL)
            self.move_cursor(x + w - 1, y + i + 1)
            self.write(self.BOX_VERTICAL)
        self.move_cursor(x, y + h - 1)
        self.write(self.BOX_CORNER_BOTTOM_LEFT)
        self.write(self.BOX_HORIZONTAL * (w - 2))
        self.write(self.BOX_CORNER_BOTTOM_RIGHT)
