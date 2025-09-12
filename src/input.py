import re


class TuimuxMouseInput:

    CODE_EXPR = r'\x1b\[<(?P<button>\d+);(?P<x>\d+);(?P<y>\d+)(?P<release>[mM]?)'
    CODE_RE = re.compile(CODE_EXPR)

    BUTTON_LEFT = 0
    BUTTON_MIDDLE = 1
    BUTTON_RIGHT = 2
    BUTTON_SCROLL_UP = 64
    BUTTON_SCROLL_DOWN = 65

    PRESS = 'M'
    REALEASE = 'm'

    def __init__(self, x, y, button, event_type):
        self.x = x
        self.y = y
        self.button = button
        self.event_type = event_type

    @classmethod
    def is_mouse_event(cls, code):
        return cls.CODE_RE.match(code) is not None

    @classmethod
    def from_code(cls, code):
        m = cls.CODE_RE.match(code)
        if not m:
            raise ValueError('Not a mouse event')
        gd = m.groupdict()

        return cls(
            x=int(gd['x']),
            y=int(gd['y']),
            button=int(gd['button']),
            event_type=gd['event_type'],
        )


class TuimuxKeyInput:

    KEY_MAP = {
        '\x1b[A': 'UP',
        '\x1b[B': 'DOWN',
        '\x1b[C': 'RIGHT',
        '\x1b[D': 'LEFT',
        '\x1b[H': 'HOME',
        '\x1b[F': 'END',
        '\x1b[5~': 'PAGE_UP',
        '\x1b[6~': 'PAGE_DOWN',
        '\x1b[3~': 'DELETE',
        '\x1b[2~': 'INSERT',
        '\x1bOP': 'F1',
        '\x1bOQ': 'F2',
        '\x1bOR': 'F3',
        '\x1bOS': 'F4',
        '\x1b[15~': 'F5',
        '\x1b[17~': 'F6',
        '\x1b[18~': 'F7',
        '\x1b[19~': 'F8',
        '\x1b[20~': 'F9',
        '\x1b[21~': 'F10',
        '\x1b[23~': 'F11',
        '\x1b[24~': 'F12',
        '\t': 'TAB',
        '\n': 'ENTER',
        '\r': 'ENTER',
        '\x7f': 'BACKSPACE',
        '\x08': 'BACKSPACE',
        '\x1b': 'ESCAPE',
        '\x03': 'CTRL_C',
        '\x04': 'CTRL_D',
        '\x16': 'CTRL_V',
    }

    @classmethod
    def is_key_event(cls, code):
        return code in cls.KEY_MAP or (len(code) == 1 and 32 <= ord(code) <= 126)

    @classmethod
    def from_code(cls, code):
        if code in cls.KEY_MAP:
            return cls.KEY_MAP[code]
        elif len(code) == 1 and 32 <= ord(code) <= 126:
            return code
        else:
            raise ValueError('Not a key event')
