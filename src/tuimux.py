import sys

import libtmux

from pytui import PyTUI, Element, ANSI


class TuiMux:

    SESSIONS_WIDTH = 0.35
    NEW_SESSION_WIDTH = 30
    NEW_SESSION_HEIGHT = 5

    def __init__(self):
        self.tmux_server = libtmux.Server()
        self.session_cursor = 0

    @property
    def sessions(self):
        return sorted(self.tmux_server.list_sessions(), key=lambda s: int((s.id or '$-1')[1:]))

    def run(self):
        with PyTUI(refresh_rate=10) as tui:

            def quit(el, key):
                if key.key == 'q' or key.key == 'Q' or key.key == 'ESCAPE':
                    tui.quit()

            def key_move_session(el, key):
                if key.key == 'UP':
                    self.session_cursor = (self.session_cursor - 1) % len(self.sessions)
                elif key.key == 'DOWN':
                    self.session_cursor = (self.session_cursor + 1) % len(self.sessions)
                el.text = sessions_text()

            def sessions_text():
                lines = []
                for session_i, session in enumerate(self.sessions):
                    session_id = session.id or '$?'
                    session_name = session.name or 'unnamed'
                    text = f"{session_id}: {session_name}"
                    if session_i == self.session_cursor:
                        text = ANSI.INVERT_COLORS + text + ANSI.REVERT_COLORS
                    lines.append(text)
                return "\n".join(lines)

            def update_pane_content(el):
                if len(self.sessions) == 0:
                    el.text = "No sessions"
                else:
                    focus_session = self.sessions[self.session_cursor]
                    window = focus_session.active_window
                    pane = window.active_pane
                    pane_height = el.actual_content_height
                    if pane is None:
                        el.text = "No panes"
                    else:
                        pane_content = pane.capture_pane(start='-')
                        if isinstance(pane_content, str):
                            el.text = pane_content
                        else:
                            el.text = "\n".join(pane_content[-pane_height:])

            def new_session(el, key):
                if key.key == 'n' or key.key == 'N':
                    if el.style == Element.STYLE_NORMAL:
                        el.style = Element.STYLE_HIDDEN
                    else:
                        el.style = Element.STYLE_NORMAL

            sessions_width = int(self.SESSIONS_WIDTH * tui.root_element.actual_content_width)
            pane_width = tui.root_element.actual_content_width - sessions_width

            sessions_col = Element()
            sessions_col.border = Element.BORDER_ROUNDED
            sessions_col.height = Element.FILL_PARENT
            sessions_col.width = int(sessions_width)
            sessions_col.text = sessions_text()
            sessions_col.key_event_listeners.append(key_move_session)
            tui.root_element.add_child(sessions_col)

            session_col_title = Element()
            session_col_title.text = "╴Sessions╶"
            session_col_title.y = -1
            sessions_col.add_child(session_col_title)

            self.session_cursor = min(self.session_cursor, len(self.sessions) - 1)

            pane_el = Element()
            pane_el.x = sessions_width
            pane_el.width = pane_width
            pane_el.height = Element.FILL_PARENT
            pane_el.border = Element.BORDER_ROUNDED
            pane_el.render_listeners.append(update_pane_content)
            tui.root_element.add_child(pane_el)

            panel_el_title = Element()
            panel_el_title.text = "╴Pane content╶"
            panel_el_title.y = -1
            pane_el.add_child(panel_el_title)

            new_session_el = Element()
            new_session_el.border = Element.BORDER_HEAVY
            new_session_el.width = self.NEW_SESSION_WIDTH
            new_session_el.height = self.NEW_SESSION_HEIGHT
            new_session_el.style = Element.STYLE_HIDDEN
            new_session_el.x = (tui.root_element.actual_content_width - new_session_el.width) // 2
            new_session_el.y = (tui.root_element.actual_content_height - new_session_el.height) // 2
            new_session_el.key_event_listeners.append(new_session)
            tui.root_element.add_child(new_session_el)

            tui.root_element.key_event_listeners.append(quit)

            tui.run()
