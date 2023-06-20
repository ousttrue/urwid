import sys
import urwid.raw_display
from urwid.display_common import BaseScreen
from urwid import escape, AttrSpec


class Screen(urwid.raw_display.Screen):
    def __init__(self, input=sys.stdin, output=sys.stdout):
        try:
            super().__init__(input, output)
        except Exception as ex:
            pass

    def _start(self, alternate_buffer=True):
        """
        Initialize the screen and input mode.

        alternate_buffer -- use alternate screen buffer
        """
        if alternate_buffer:
            self.write(escape.SWITCH_TO_ALTERNATE_BUFFER)
            self._rows_used = None
        else:
            self._rows_used = 0

        # fd = self._input_fileno()
        # if fd is not None and os.isatty(fd):
        #     self._old_termios_settings = termios.tcgetattr(fd)
        #     tty.setcbreak(fd)

        # self.signal_init()
        self._alternate_buffer = alternate_buffer
        self._next_timeout = self.max_wait

        # if not self._signal_keys_set:
        #     self._old_signal_keys = self.tty_signal_keys(fileno=fd)

        # signals.emit_signal(self, INPUT_DESCRIPTORS_CHANGED)
        # restore mouse tracking to previous state
        self._mouse_tracking(self._mouse_tracking_enabled)

        return BaseScreen._start(self)

    def _stop(self):
        """
        Restore the screen.
        """
        self.clear()

        # signals.emit_signal(self, INPUT_DESCRIPTORS_CHANGED)

        # self.signal_restore()

        # fd = self._input_fileno()
        # if fd is not None and os.isatty(fd):
        #     termios.tcsetattr(fd, termios.TCSADRAIN, self._old_termios_settings)

        self._mouse_tracking(False)

        move_cursor = ""
        if self._alternate_buffer:
            move_cursor = escape.RESTORE_NORMAL_BUFFER
        elif self.maxrow is not None:
            move_cursor = escape.set_cursor_position(0, self.maxrow)
        self.write(
            self._attrspec_to_escape(AttrSpec("", ""))
            + escape.SI
            + move_cursor
            + escape.SHOW_CURSOR
        )
        self.flush()

        # if self._old_signal_keys:
        #     self.tty_signal_keys(*(self._old_signal_keys + (fd,)))

        BaseScreen._stop(self)
