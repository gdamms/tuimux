import sys

import libtmux

from pytui import PyTUI, Element


class TuiMux:

    SESSIONS_WIDTH = 0.35
    PANE_WIDTH = 80

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

            def layout(el):
                el.clear_children()

                sessions_width = int(self.SESSIONS_WIDTH * el.actual_content_width)
                pane_width = el.actual_content_width - sessions_width

                sessions_col = Element()
                sessions_col.border = Element.BORDER_ROUNDED
                sessions_col.height = Element.FILL_PARENT
                sessions_col.width = int(sessions_width)
                tui.root_element.add_child(sessions_col)

                session_col_title = Element()
                session_col_title.text = "╴Sessions╶"
                session_col_title.y = -1
                sessions_col.add_child(session_col_title)

                self.session_cursor = min(self.session_cursor, len(self.sessions) - 1)

                for session_i, session in enumerate(self.sessions):
                    session_id = session.id or '$?'
                    session_name = session.name or 'unnamed'
                    session_el = Element()
                    session_el.text = f"{session_id}: {session_name}"
                    session_el.y = session_i
                    session_el.width = Element.FILL_PARENT
                    if session_i == self.session_cursor:
                        session_el.style = Element.STYLE_INVERTED
                    sessions_col.add_child(session_el)

                pane_el = Element()
                pane_el.x = sessions_width
                pane_el.width = pane_width
                pane_el.height = Element.FILL_PARENT
                pane_el.border = Element.BORDER_ROUNDED

                if len(self.sessions) == 0:
                    pane_el.text = "No sessions"
                else:
                    focus_session = self.sessions[self.session_cursor]
                    window = focus_session.active_window
                    pane = window.active_pane
                    pane_height = pane_el.actual_content_height
                    if pane is None:
                        pane_el.text = "No panes"
                    else:
                        pane_content = pane.capture_pane(start='-')
                        if isinstance(pane_content, str):
                            pane_el.text = pane_content
                        else:
                            pane_el.text = "\n".join(pane_content[-pane_height:])
                    tui.root_element.add_child(pane_el)

            tui.root_element.key_event_listeners.append(quit)
            tui.root_element.key_event_listeners.append(key_move_session)
            tui.root_element.render_listeners.append(layout)

            tui.run()
