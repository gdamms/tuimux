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

    @staticmethod
    def hide_cursor():
        print(ANSI.HIDE_CURSOR, end='', flush=True)

    @staticmethod
    def show_cursor():
        print(ANSI.SHOW_CURSOR, end='', flush=True)

    @staticmethod
    def primary_context():
        print(ANSI.PRIMARY_CONTEXT, end='', flush=True)

    @staticmethod
    def secondary_context():
        print(ANSI.SECONDARY_CONTEXT, end='', flush=True)

    @staticmethod
    def clear_screen():
        print(ANSI.CLEAR_SCREEN, end='', flush=True)

    @staticmethod
    def move_cursor(x, y):
        print(ANSI.MOVE_CURSOR.format(y, x), end='', flush=True)

    @staticmethod
    def invert_colors():
        print('\x1b[7m', end='', flush=True)

    @staticmethod
    def revert_colors():
        print('\x1b[27m', end='', flush=True)


class Tmuxui:
    def __init__(self):
        self.session_selector = 0

    def __enter__(self):
        ANSI.hide_cursor()
        ANSI.secondary_context()

    def __exit__(self, exc_type, exc_val, exc_tb):
        ANSI.primary_context()
        ANSI.show_cursor()


def box(x, y, width, height):
    max_x, max_y = os.get_terminal_size()
    width = min(width, max_x - x)
    height = min(height, max_y - y)
    ANSI.move_cursor(x, y)
    print('╭', end='')
    print('─' * (width - 2), end='')
    print('╮')
    for i in range(height - 1):
        ANSI.move_cursor(x, y + i + 1)
        print('│', end='')
        ANSI.move_cursor(x + width - 1, y + i + 1)
        print('│', end='')
    ANSI.move_cursor(x, y + height)
    print('╰', end='')
    print('─' * (width - 2), end='')
    print('╯', end='', flush=True)


def log(x):
    print(x, file=open('log2.txt', 'a'))
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


MIN_WIDTH = 20
MIN_HEIGHT = 5

SESSION_WIDTH = 80


def main():
    tmuxui = Tmuxui()
    renaming = None
    rename = ''

    with tmuxui:
        server = libtmux.Server()

        while True:
            tw, th = os.get_terminal_size()
            if tw < MIN_WIDTH or th < MIN_HEIGHT:
                ANSI.clear_screen()
                ANSI.move_cursor(1, 1)
                print('Terminal size is too small.')
                time.sleep(1)
                continue

            dh = th - 2
            SESSIONS_WIDTH = tw - SESSION_WIDTH - 2

            box(1, 1, SESSIONS_WIDTH, dh)
            for session_i, session in enumerate(server.sessions):
                if session_i >= dh - 2:
                    break
                name = session.name or ""
                name = name[:SESSIONS_WIDTH - 2]
                name = name.ljust(SESSIONS_WIDTH - 2)

                if session_i == tmuxui.session_selector:
                    ANSI.invert_colors()
                ANSI.move_cursor(2, 2 + session_i)
                print(name, end='', flush=True)
                if session_i == tmuxui.session_selector:
                    ANSI.revert_colors()

            box(SESSIONS_WIDTH + 1, 1, tw - SESSIONS_WIDTH, dh)
            if len(server.sessions) > 0:
                focus_session = server.sessions[tmuxui.session_selector]
                window = focus_session.active_window
                pane = window.active_pane
                pane_width = tw - SESSIONS_WIDTH
                pane_height = dh
                if pane:
                    pane_content = pane.capture_pane(start='-')
                    if not isinstance(pane_content, str):
                        pane_content.reverse()
                        for line_i, line in enumerate(pane_content):
                            if line_i > pane_height - 3:
                                break
                            line = line[:pane_width - 3]
                            ANSI.move_cursor(SESSIONS_WIDTH + 2, pane_height - 1 - line_i)
                            print(line, end='', flush=True)

            #display helper on the bottom
            if not renaming:
                message = 'q: quit; ↑/↓: select session; n: new; d: delete; r: rename'
            else:
                message = 'Session name: ' + rename
            ANSI.move_cursor(1, th)
            message = message + ' ' * (tw - len(message))
            print(message, end='', flush=True)

            key = get_key()
            if renaming is not None:
                # escape
                if key == '\x1b':
                    renaming = None
                # backspace
                elif key == '\x7f':
                    rename = rename[:-1]
                # enter
                elif key == '\n':
                    server.sessions[tmuxui.session_selector].rename_session(rename)
                    renaming = None
                # any other key
                elif key is not None:
                    rename += key
                if key is not None:
                    print(key, rename, file=open('log.txt', 'a'))
            else:
                if key == '\x1b[A':
                    if len(server.sessions) > 0:
                        tmuxui.session_selector -= 1
                        tmuxui.session_selector %= len(server.sessions)
                elif key == '\x1b[B':
                    if len(server.sessions) > 0:
                        tmuxui.session_selector += 1
                        tmuxui.session_selector %= len(server.sessions)
                elif key == 'q':
                    break
                elif key == '\x1b':
                    break
                elif key == 'n':
                    renaming = server.new_session(x=SESSION_WIDTH)
                    rename = ''
                elif key == 'd':
                    if len(server.sessions) > 0:
                        server.sessions[tmuxui.session_selector].kill()
                elif key == 'r':
                    if len(server.sessions) > 0:
                        renaming = server.sessions[tmuxui.session_selector]
                        rename = server.sessions[tmuxui.session_selector].name or ''
                else:
                    pass


if __name__ == '__main__':
    main()
