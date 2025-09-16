import libtmux

from pytui import PyTUI, Element


class TuiMux:
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

                sessions_col = Element()
                sessions_col.border = Element.BORDER_ROUNDED
                sessions_col.height = Element.FILL_PARENT
                sessions_col.width = 40
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

            tui.root_element.key_event_listeners.append(quit)
            tui.root_element.key_event_listeners.append(key_move_session)
            tui.root_element.render_listeners.append(layout)

            tui.run()
