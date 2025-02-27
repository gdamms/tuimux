import time
import os
import libtmux
import tty
import termios
import sys
import select


class ANSI:
    PRIMARY_CONTEXT = '\x1b[?1049l'
    SECONDARY_CONTEXT = '\x1b[?1049h'
    HIDE_CURSOR = '\x1b[?25l'
    SHOW_CURSOR = '\x1b[?25h'
    CLEAR_SCREEN = '\x1b[2J'
    MOVE_CURSOR = '\x1b[{};{}H'


class Renderer:
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
        self.write('\x1b[7m')

    def revert_colors(self):
        self.write('\x1b[27m')

    def box(self, x, y, w, h):
        max_w, max_h = os.get_terminal_size()
        assert x >= 1 and y >= 1 and w >= 2 and h >= 2
        assert x + w - 1 <= max_w and y + h - 1 <= max_h
        self.move_cursor(x, y)
        self.write('╭')
        self.write('─' * (w - 2))
        self.write('╮')
        for i in range(h - 2):
            self.move_cursor(x, y + i + 1)
            self.write('│')
            self.move_cursor(x + w - 1, y + i + 1)
            self.write('│')
        self.move_cursor(x, y + h - 1)
        self.write('╰')
        self.write('─' * (w - 2))
        self.write('╯')


class Tuimux:

    MIN_WIDTH = 80
    MIN_HEIGHT = 10
    SESSIONS_WIDTH = 10

    def __init__(self):
        self.session_selector = 0
        self.renderer = Renderer()
        self.server = libtmux.Server()

        self.renaming = None
        self.rename = ''

        self.newname = None

    def __enter__(self):
        self.renderer.hide_cursor()
        self.renderer.secondary_context()
        self.renderer.clear_screen()
        self.renderer.render()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.renderer.primary_context()
        self.renderer.show_cursor()
        self.renderer.render()
        self.renderer.clear()
        return False

    @property
    def is_terminal_size_sufficiant(self):
        tw, th = os.get_terminal_size()
        return tw >= self.MIN_WIDTH and th >= self.MIN_HEIGHT

    def render_too_small(self):
        self.renderer.move_cursor(1, 1)
        self.renderer.write('Terminal size is too small.')

    def render(self):
        if not self.is_terminal_size_sufficiant:
            self.render_too_small()
        else:
            self.render_sessions_column()
            self.render_selected_session()
            self.render_renaming()
            self.render_new_session()
            self.render_help()

    @property
    def sessions(self):
        return sorted(self.server.sessions, key=lambda x: int((x.id or '$-1')[1:]))

    def blink(self):
        self.renderer.move_cursor(1, 1)
        self.renderer.render()
        self.renderer.clear_screen()

    def render_sessions_column(self):
        tw, th = os.get_terminal_size()
        dh = th - 1

        self.renderer.box(1, 1, self.SESSIONS_WIDTH, dh)
        for session_i, session in enumerate(self.sessions):
            if session_i >= dh - 2:
                break
            name = session.name or ""

            id = (session.id or " ")[1:]

            line = f'{id}: {name}'
            line = line[:self.SESSIONS_WIDTH - 2]
            line = line.ljust(self.SESSIONS_WIDTH - 2)

            if session_i == self.session_selector:
                self.renderer.invert_colors()
            self.renderer.move_cursor(2, 2 + session_i)
            self.renderer.write(line)
            if session_i == self.session_selector:
                self.renderer.revert_colors()

    def render_selected_session(self):
        tw, th = os.get_terminal_size()
        dh = th - 1

        self.renderer.box(self.SESSIONS_WIDTH + 1, 1, tw - self.SESSIONS_WIDTH, dh)
        if len(self.sessions) > 0:
            focus_session = self.sessions[self.session_selector]
            window = focus_session.active_window
            pane = window.active_pane
            pane_width = tw - self.SESSIONS_WIDTH
            pane_height = dh
            if pane:
                pane_content = pane.capture_pane(start='-')
                if not isinstance(pane_content, str):
                    pane_content.reverse()
                    for line_i, line in enumerate(pane_content):
                        if line_i > pane_height - 3:
                            break
                        line = line[:pane_width - 3]
                        self.renderer.move_cursor(self.SESSIONS_WIDTH + 2, pane_height - 1 - line_i)
                        self.renderer.write(line)

    @property
    def help(self):
        if self.renaming is not None:
            return 'esc: cancel; enter: save'
        else:
            return 'q: quit; ↑/↓: select session; n: new; d: delete; r: rename; a: attach'

    def render_help(self):
        tw, th = os.get_terminal_size()
        self.renderer.move_cursor(1, th)
        self.renderer.write(self.help)

    def render_renaming(self):
        if self.renaming is None:
            return
        tw, th = os.get_terminal_size()
        box_y = th // 2
        box_h = 3
        box_x = tw // 2 - 20
        box_w = 40

        for session in self.sessions:
            if session != self.renaming and session.name == self.rename:
                color = '\x1b[31m'
                self.renderer.write(color)
                break

        self.renderer.box(box_x, box_y, box_w, box_h)
        self.renderer.move_cursor(box_x + 1, box_y + 1)
        self.renderer.write('Session name: ' + self.rename)

        self.renderer.write('\x1b[0m')

    def render_new_session(self):
        if self.newname is None:
            return
        tw, th = os.get_terminal_size()
        box_y = th // 2
        box_h = 3
        box_x = tw // 2 - 20
        box_w = 40

        for session in self.sessions:
            if session.name == self.newname:
                color = '\x1b[31m'
                self.renderer.write(color)
                break

        self.renderer.box(box_x, box_y, box_w, box_h)
        self.renderer.move_cursor(box_x + 1, box_y + 1)
        self.renderer.write('Session name: ' + self.newname)

        self.renderer.write('\x1b[0m')

    def handle_renaming(self, key):
        # escape
        if key == '\x1b':
            self.renaming = None
        # backspace
        elif key == '\x7f':
            self.rename = self.rename[:-1]
        # enter
        elif key == '\n':
            for session in self.sessions:
                if session != self.renaming and session.name == self.rename:
                    break
            else:
                self.sessions[self.session_selector].rename_session(self.rename)
                self.renaming = None
        # any other key
        elif key in list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
            self.rename += key
        elif key is not None:
            log((key, self.rename))

        return True

    def handle_new_session(self, key):
        assert self.newname is not None

        # escape
        if key == '\x1b':
            self.newname = None
        # backspace
        elif key == '\x7f':
            self.newname = self.newname[:-1]
        # enter
        elif key == '\n':
            for session in self.sessions:
                if session.name == self.newname:
                    break
            else:
                self.server.new_session(session_name=self.newname)
                self.newname = None
        # any other key
        elif key in list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
            self.newname += key
        elif key is not None:
            log((key, self.newname))

        return True

    def handle_normal(self, key):
        if key == '\x1b[A':
            if len(self.sessions) > 0:
                self.session_selector -= 1
                self.session_selector %= len(self.sessions)
        elif key == '\x1b[B':
            if len(self.sessions) > 0:
                self.session_selector += 1
                self.session_selector %= len(self.sessions)
        elif key == 'q':
            return False
        elif key == '\x1b':
            return False
        elif key == 'n':
            self.newname = ''
        elif key == 'd':
            if len(self.sessions) > 0:
                self.sessions[self.session_selector].kill()
        elif key == 'r':
            if len(self.sessions) > 0:
                self.renaming = self.sessions[self.session_selector]
                self.rename = self.sessions[self.session_selector].name or ''
        elif key == 'a':
            if len(self.sessions) > 0:
                self.sessions[self.session_selector].attach_session()
                self.renderer.hide_cursor()

        return True

    def handle(self, key):
        if self.renaming is not None:
            return self.handle_renaming(key)
        elif self.newname is not None:
            return self.handle_new_session(key)
        else:
            return self.handle_normal(key)


def log(x):
    print(x, file=open('log.txt', 'a'))
    return x


def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    new_settings = termios.tcgetattr(sys.stdin)
    new_settings[3] = new_settings[3] & ~(termios.ECHO | termios.ICANON)  # lflags
    new_settings[6][termios.VMIN] = 0  # cc
    new_settings[6][termios.VTIME] = 0  # cc
    try:
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, new_settings)
        if select.select([sys.stdin], [], [], 0.1)[0]:
            ch_set = ''
            ch = os.read(fd, 1)
            while ch is not None and ch != b'':
                ch_set += ch.decode('ISO-8859-1')
                ch = os.read(fd, 1)
            return ch_set
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, old_settings)
    return None


SESSION_WIDTH = 80


def main():
    tuimux = Tuimux()

    with tuimux:
        while True:
            key = get_key()
            if not tuimux.handle(key):
                break
            tuimux.render()
            tuimux.blink()


if __name__ == '__main__':
    main()
