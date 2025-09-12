import os
import sys
import termios
import select
import time

import libtmux

from .renderer import Renderer


class Tuimux:

    MIN_WIDTH = 40
    MIN_HEIGHT = 10
    SESSIONS_WIDTH_MIN = 10

    def __init__(self):
        self.session_selector = 0
        self.renderer = Renderer()
        self.server = libtmux.Server()

        self.renaming = None
        self.rename = ''

        self.newname = None

        self.deleting = None
        self.deleting_yes = False

    def __enter__(self):
        self.setup_terminal()
        self.renderer.hide_cursor()
        self.renderer.secondary_context()
        self.renderer.clear_screen()
        self.renderer.render()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.renderer.primary_context()
        self.renderer.show_cursor()
        self.renderer.render()
        self.restore_terminal()
        return False

    @property
    def SESSIONS_WIDTH(self):
        tw, th = os.get_terminal_size()
        return max(self.SESSIONS_WIDTH_MIN, tw // 4)

    def setup_terminal(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
        new_settings = termios.tcgetattr(sys.stdin)
        new_settings[3] = new_settings[3] & ~(termios.ECHO | termios.ICANON)  # lflags
        new_settings[6][termios.VMIN] = 0  # cc
        new_settings[6][termios.VTIME] = 0  # cc
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, new_settings)
        self.enable_mouse()

    def enable_mouse(self):
        sys.stdout.write("\x1b[?1000h")
        sys.stdout.write("\x1b[?1006h")
        sys.stdout.flush()

    def disable_mouse(self):
        sys.stdout.write("\x1b[?1000l")
        sys.stdout.write("\x1b[?1006l")
        sys.stdout.flush()

    def get_key(self):
        if select.select([sys.stdin], [], [], 0.1)[0]:
            ch_set = ''
            ch = os.read(self.fd, 1)
            while ch is not None and ch != b'':
                ch_set += ch.decode('ISO-8859-1')
                ch = os.read(self.fd, 1)
            return ch_set
        return None

    def restore_terminal(self):
        self.disable_mouse()
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, self.old_settings)

    @property
    def is_terminal_size_sufficiant(self):
        tw, th = os.get_terminal_size()
        return tw >= self.MIN_WIDTH and th >= self.MIN_HEIGHT

    def render_too_small(self):
        self.renderer.reset_color()
        self.renderer.move_cursor(1, 1)
        self.renderer.write('Terminal size is too small.')
        time.sleep(1)

    def render(self):
        if not self.is_terminal_size_sufficiant:
            self.render_too_small()
        else:
            self.render_sessions_column()
            self.render_selected_session()
            self.render_renaming()
            self.render_new_session()
            self.render_deleting()
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

        self.renderer.reset_color()
        self.renderer.box(1, 1, self.SESSIONS_WIDTH, dh, title='Sessions')
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

        self.renderer.reset_color()
        self.renderer.box(self.SESSIONS_WIDTH + 1, 1, tw - self.SESSIONS_WIDTH, dh, title='View')
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

        self.renderer.reset_color()
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
                self.renderer.color('red')
                break

        self.renderer.reset_color()
        self.renderer.box(box_x, box_y, box_w, box_h)
        self.renderer.move_cursor(box_x + 1, box_y + 1)
        self.renderer.write('Session name: ')
        if self.rename:
            self.renderer.write(self.rename)
        else:
            self.renderer.color('bright_black')
            self.renderer.write('empty name not allowed')

    def render_new_session(self):
        if self.newname is None:
            return

        tw, th = os.get_terminal_size()
        box_y = th // 2
        box_h = 3
        box_x = tw // 2 - 20
        box_w = 40

        session_name_msg = 'Session name: '
        session_name_msg_w = len(session_name_msg)
        max_name_w = box_w - 2 - session_name_msg_w

        for session in self.sessions:
            if session.name == self.newname:
                color = '\x1b[31m'
                self.renderer.write(color)
                break

        self.renderer.reset_color()
        self.renderer.box(box_x, box_y, box_w, box_h)
        self.renderer.move_cursor(box_x + 1, box_y + 1)
        self.renderer.write(session_name_msg)
        if self.newname:
            if len(self.newname) <= max_name_w:
                self.renderer.write(self.newname)
            else:
                newname_msg = '...' + self.newname[-(max_name_w - 3):]
                self.renderer.write(newname_msg)
        else:
            self.renderer.color('bright_black')
            self.renderer.write('use id as name')

    def render_deleting(self):
        if self.deleting is None:
            return

        tw, th = os.get_terminal_size()
        box_y = th // 2
        box_h = 4
        box_x = tw // 2 - 30

        session_name = self.deleting.name or ''
        session_id = (self.deleting.id or '')[1:]
        msg = f'Delete session "{session_name}" (id {session_id})?'
        yes_msg = ' Yes '
        no_msg = ' No '
        sep_msg = ' '

        yes_no_w = len(yes_msg) + len(no_msg) + len(sep_msg)
        box_w = max(len(msg), yes_no_w) + 2
        yes_no_x = box_x + (box_w - yes_no_w) // 2

        self.renderer.reset_color()
        self.renderer.box(box_x, box_y, box_w, box_h)
        self.renderer.move_cursor(box_x + 1, box_y + 1)
        self.renderer.write(msg)

        self.renderer.move_cursor(yes_no_x, box_y + 2)
        if self.deleting_yes:
            self.renderer.invert_colors()
        self.renderer.write(yes_msg)
        self.renderer.reset_color()

        self.renderer.write(sep_msg)

        if not self.deleting_yes:
            self.renderer.invert_colors()
        self.renderer.write(no_msg)

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
                if self.rename:
                    self.sessions[self.session_selector].rename_session(self.rename)
                self.renaming = None
        # any other key
        elif key in list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
            self.rename += key

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
                self.server.new_session(session_name=self.newname or None)
                self.session_selector = len(self.sessions) - 1
                self.newname = None
        # any other key
        elif key in list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
            self.newname += key

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
                self.deleting = self.sessions[self.session_selector]
                self.deleting_yes = False
        elif key == 'r':
            if len(self.sessions) > 0:
                self.renaming = self.sessions[self.session_selector]
                self.rename = self.sessions[self.session_selector].name or ''
        elif key == 'a':
            if len(self.sessions) > 0:
                self.sessions[self.session_selector].attach_session()
                self.renderer.hide_cursor()

        return True

    def process_deleting(self):
        assert self.deleting is not None

        if self.deleting_yes:
            self.deleting.kill_session()
        self.deleting = None
        self.deleting_yes = False
        self.session_selector = min(self.session_selector, len(self.sessions) - 1)

    def handle_deleting(self, key):
        assert self.deleting is not None

        if key == '\x1b[A' or key == '\x1b[B' or key == '\x1b[C' or key == '\x1b[D':
            self.deleting_yes = not self.deleting_yes
        elif key == 'y' or key == 'd':
            if self.deleting_yes:
                self.process_deleting()
            else:
                self.deleting_yes = True
        elif key == 'n' or key == '\x1b' or key == 'q':
            if not self.deleting_yes:
                self.process_deleting()
            else:
                self.deleting_yes = False
        elif key == '\n':
            self.process_deleting()

        return True

    def handle(self, key):
        if self.renaming is not None:
            return self.handle_renaming(key)
        elif self.newname is not None:
            return self.handle_new_session(key)
        elif self.deleting is not None:
            return self.handle_deleting(key)
        else:
            return self.handle_normal(key)
