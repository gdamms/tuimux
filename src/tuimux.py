import sys

import libtmux

from pytui import PyTUI, Element, ANSI


class TuiMux:

    SESSIONS_WIDTH = 0.35
    NEW_SESSION_WIDTH = 30
    NEW_SESSION_HEIGHT = 5
    REFRESH_RATE = 10

    def __init__(self):
        self.tmux_server = libtmux.Server()
        self.session_cursor = 0

    @property
    def sessions(self):
        return sorted(self.tmux_server.list_sessions(), key=lambda s: int((s.id or '$-1')[1:]))

    def run(self):
        with PyTUI(refresh_rate=self.REFRESH_RATE) as tui:

            def quit(tui, key):
                if key.key == 'q' or key.key == 'Q' or key.key == 'ESCAPE':
                    tui.quit()
            tui.key_event_listeners.append(quit)

            def arrow_session(el, key):
                # TODO: handle scroll
                # TODO: handle more sessions than lines (roll over)
                if key.key == 'UP':
                    self.session_cursor = (self.session_cursor - 1) % len(self.sessions)
                elif key.key == 'DOWN':
                    self.session_cursor = (self.session_cursor + 1) % len(self.sessions)
                else:
                    return

                for child in el.children:
                    child.style = Element.STYLE_NORMAL
                if len(el.children) > 1:
                    el.children[self.session_cursor + 1].style = Element.STYLE_INVERTED

            def build_session_col(lines_width, nb_lines):
                col = Element()
                col.border = Element.BORDER_ROUNDED
                col.height = Element.FILL_PARENT
                col.width = int(lines_width)

                col_title = Element()
                col_title.text = "╴Sessions╶"
                col_title.y = -1
                col.add_child(col_title)

                nb_sessions = len(self.sessions)
                nb_lines = min(nb_lines, nb_sessions)
                for i in range(nb_lines):
                    session = self.sessions[i]
                    session_id = session.id or '$?'
                    session_name = session.name or 'unnamed'
                    line_el = Element()
                    line_el.y = i
                    line_el.width = Element.FILL_PARENT
                    line_el.text = f"{session_id}: {session_name}"
                    if i == self.session_cursor:
                        line_el.style = Element.STYLE_INVERTED
                    col.add_child(line_el)

                col.key_event_listeners.append(arrow_session)

                return col

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

            # TODO: replace this with a percentage width element and fill parents that adjust to remaining space
            sessions_width = int(self.SESSIONS_WIDTH * tui.root_element.actual_content_width)
            pane_width = tui.root_element.actual_content_width - sessions_width

            self.session_cursor = min(self.session_cursor, len(self.sessions) - 1)

            sessions_col = build_session_col(sessions_width, tui.root_element.actual_content_height)
            tui.root_element.add_child(sessions_col)
            sessions_col.focus()

            def terminal_size_change(tui, size):
                nonlocal sessions_col
                tui.root_element.remove_child(sessions_col)
                sessions_width = int(self.SESSIONS_WIDTH * tui.root_element.actual_content_width)
                sessions_col = build_session_col(sessions_width, size[1])
                tui.root_element.add_child(sessions_col)
            tui.terminal_resize_listeners.append(terminal_size_change)

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

            def on_focus(el):
                el.style = Element.STYLE_NORMAL

            def on_blur(el):
                el.style = Element.STYLE_HIDDEN

            def new_session(tui, key):
                if key.key == 'n' or key.key == 'N':
                    if new_session_el.style == Element.STYLE_HIDDEN:
                        new_session_el.focus()
                    else:
                        new_session_el.blur()
            tui.key_event_listeners.append(new_session)
            new_session_el.focus_listeners.append(on_focus)
            new_session_el.blur_listeners.append(on_blur)
            tui.root_element.add_child(new_session_el)

            tui.run()
