class ANSI:
    PRIMARY_CONTEXT = '\x1b[?1049l'
    SECONDARY_CONTEXT = '\x1b[?1049h'
    HIDE_CURSOR = '\x1b[?25l'
    SHOW_CURSOR = '\x1b[?25h'
    CLEAR_SCREEN = '\x1b[2J'
    MOVE_CURSOR = '\x1b[{};{}H'
    INVERT_COLORS = '\x1b[7m'
    REVERT_COLORS = '\x1b[27m'
    RESET_COLOR = '\x1b[0m'
    FOREGROUND_COLORS = {
        'black': '\x1b[30m',
        'red': '\x1b[31m',
        'green': '\x1b[32m',
        'yellow': '\x1b[33m',
        'blue': '\x1b[34m',
        'magenta': '\x1b[35m',
        'cyan': '\x1b[36m',
        'white': '\x1b[37m',
        'bright_black': '\x1b[90m',
        'bright_red': '\x1b[91m',
        'bright_green': '\x1b[92m',
        'bright_yellow': '\x1b[93m',
        'bright_blue': '\x1b[94m',
        'bright_magenta': '\x1b[95m',
        'bright_cyan': '\x1b[96m',
        'bright_white': '\x1b[97m',
    }
    BACKGROUND_COLORS = {
        'black': '\x1b[40m',
        'red': '\x1b[41m',
        'green': '\x1b[42m',
        'yellow': '\x1b[43m',
        'blue': '\x1b[44m',
        'magenta': '\x1b[45m',
        'cyan': '\x1b[46m',
        'white': '\x1b[47m',
        'bright_black': '\x1b[100m',
        'bright_red': '\x1b[101m',
        'bright_green': '\x1b[102m',
        'bright_yellow': '\x1b[103m',
        'bright_blue': '\x1b[104m',
        'bright_magenta': '\x1b[105m',
        'bright_cyan': '\x1b[106m',
        'bright_white': '\x1b[107m',
    }
