# tuimux

A terminal UI to manage tmux sessions, in the spirit of lazydocker: your sessions on the
left, a live preview of the selected one on the right. Built with
[pytui](https://github.com/gdamms/pytui).

## Features

- list sessions, with a live preview of each session's active pane
- create a session (named, or named after its id)
- rename a session
- delete a session (asks for confirmation)
- attach to a session (switches client when already inside tmux), back to tuimux on detach
- keyboard and mouse

## Installation

```sh
uv tool install gdamms-tuimux
```

## Usage

```sh
tuimux
```

Controls:
| Key | Action |
| --- | --- |
| `↑` / `↓` | select a session |
| `enter` / `a` | attach |
| `n` | new session |
| `r` | rename session |
| `d` | delete session |
| `q` / `esc` | quit (or close a dialog) |

## TODO

- copy a session's environment
- session stats (cpu, mem, etc)
