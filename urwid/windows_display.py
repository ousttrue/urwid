import sys
from typing import Optional, List
import urwid.raw_display
from urwid.display_common import BaseScreen
from urwid import escape, AttrSpec
import ctypes
import ctypes.wintypes
from .event_loop import win32

STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12
INVALID_HANDLE_VALUE = ctypes.c_uint64(-1).value
ENABLE_PROCESSED_INPUT = 0x0001
ENABLE_LINE_INPUT = 0x0002
ENABLE_ECHO_INPUT = 0x0004
ENABLE_WINDOW_INPUT = 0x0008
ENABLE_MOUSE_INPUT = 0x0010
ENABLE_INSERT_MODE = 0x0020
ENABLE_QUICK_EDIT_MODE = 0x0040
ENABLE_EXTENDED_FLAGS = 0x0080
ENABLE_AUTO_POSITION = 0x0100
ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200
ENABLE_PROCESSED_OUTPUT = 0x0001
ENABLE_WRAP_AT_EOL_OUTPUT = 0x0002
ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
DISABLE_NEWLINE_AUTO_RETURN = 0x0008
ENABLE_LVB_GRID_WORLDWIDE = 0x0010


class COORD(ctypes.Structure):
    _fields_ = (
        ("X", ctypes.wintypes.SHORT),
        ("Y", ctypes.wintypes.SHORT),
    )


class SMALL_RECT(ctypes.Structure):
    _fields_ = (
        ("Left", ctypes.wintypes.SHORT),
        ("Top", ctypes.wintypes.SHORT),
        ("Right", ctypes.wintypes.SHORT),
        ("Bottom", ctypes.wintypes.SHORT),
    )


class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
    _fields_ = (
        ("dwSize", COORD),
        ("dwCursorPosition", COORD),
        ("wAttributes", ctypes.wintypes.WORD),
        ("srWindow", SMALL_RECT),
        ("dwMaximumWindowSize", COORD),
    )


GetStdHandle = ctypes.windll.kernel32.GetStdHandle
GetStdHandle.restype = ctypes.wintypes.HANDLE
GetStdHandle.argtypes = (ctypes.wintypes.DWORD,)  # nStdHandle

GetConsoleMode = ctypes.windll.kernel32.GetConsoleMode
GetConsoleMode.restype = ctypes.wintypes.BOOL
GetConsoleMode.argtypes = (
    ctypes.wintypes.HANDLE,  # hConsoleHandle
    ctypes.wintypes.LPDWORD,  # lpMode
)

SetConsoleMode = ctypes.windll.kernel32.SetConsoleMode
SetConsoleMode.restype = ctypes.wintypes.BOOL
SetConsoleMode.argtypes = (
    ctypes.wintypes.HANDLE,  # hConsoleHandle
    ctypes.wintypes.DWORD,  # dwMode
)

GetConsoleScreenBufferInfo = ctypes.windll.kernel32.GetConsoleScreenBufferInfo
GetConsoleScreenBufferInfo.restype = ctypes.wintypes.BOOL
GetConsoleScreenBufferInfo.argtypes = (
    ctypes.wintypes.HANDLE,  #                      hConsoleOutput,
    ctypes.POINTER(CONSOLE_SCREEN_BUFFER_INFO),  # lpConsoleScreenBufferInfo
)


class Screen(urwid.raw_display.Screen):
    def __init__(self, input=sys.stdin, output=sys.stdout):
        self.event_loop = None
        try:
            super().__init__(input, output)
        except Exception as ex:
            pass
        self.cols_rows = (0, 0)
        self.hStdin = None

    def _start(self, alternate_buffer=True):
        """
        Initialize the screen and input mode.

        alternate_buffer -- use alternate screen buffer
        """
        self.hStdin = GetStdHandle(STD_INPUT_HANDLE)
        if self.hStdin == INVALID_HANDLE_VALUE:
            raise Exception("GetStdHandle")
        inMode = (ctypes.wintypes.DWORD * 1)()
        if not GetConsoleMode(self.hStdin, inMode):
            raise Exception("GetConsoleMode")
        if not SetConsoleMode(
            self.hStdin,
            inMode[0]
            | ENABLE_WINDOW_INPUT
            | ENABLE_MOUSE_INPUT
            | ENABLE_VIRTUAL_TERMINAL_INPUT,
        ):
            raise Exception("SetConsoleMode")

        hStdout = GetStdHandle(STD_OUTPUT_HANDLE)
        if hStdout == INVALID_HANDLE_VALUE:
            raise Exception("GetStdHandle")
        outMode = (ctypes.wintypes.DWORD * 1)()
        if not GetConsoleMode(hStdout, outMode):
            raise Exception("GetConsoleMode")
        if not SetConsoleMode(
            hStdout,
            outMode[0]
            | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            | DISABLE_NEWLINE_AUTO_RETURN,
        ):
            raise Exception("SetConsoleMode")

        # dwOutMode = win32.DWORD(
        #     self._dwOriginalOutMode.value | win32.ENABLE_VIRTUAL_TERMINAL_PROCESSING | win32.DISABLE_NEWLINE_AUTO_RETURN)
        # dwInMode = win32.DWORD(
        #     self._dwOriginalInMode.value | win32.ENABLE_WINDOW_INPUT | win32.ENABLE_VIRTUAL_TERMINAL_INPUT
        # )

        info = CONSOLE_SCREEN_BUFFER_INFO()
        if not GetConsoleScreenBufferInfo(hStdout, ctypes.pointer(info)):
            raise Exception()

        self.cols_rows = (
            info.srWindow.Right - info.srWindow.Left + 1,
            info.srWindow.Bottom - info.srWindow.Top + 1,
        )

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

    def get_input_descriptors(self) -> list[int]:
        """
        Return a list of integer file descriptors that should be
        polled in external event loops to check for user input.

        Use this method if you are implementing your own event loop.

        This method is only called by `hook_event_loop`, so if you override
        that, you can safely ignore this.
        """
        if not self._started:
            return []

        fd_list = []
        fd = self._input_fileno()
        if fd is not None:
            fd_list.append(fd)
        # if self.gpm_mev is not None:
        #     fd_list.append(self.gpm_mev.stdout.fileno())
        return fd_list

    def _wait_for_input_ready(self, timeout):
        ready = None
        if not self.event_loop:
            from urwid.event_loop.windows_loop import WindowsEventLoop
            self.event_loop = WindowsEventLoop()
        self.event_loop.poll(self.hStdin)
        return ready
    
    def get_input(self, raw_keys: bool = False) -> list[str] | tuple[list[str], list[int]]:
        assert self._started

        self._wait_for_input_ready(self._next_timeout)
        keys, raw = self.parse_input(None, None, self.get_available_raw_input())

        # Avoid pegging CPU at 100% when slowly resizing
        if keys == ['window resize'] and self.prev_input_resize:
            while True:
                self._wait_for_input_ready(self.resize_wait)
                keys, raw2 = self.parse_input(None, None, self.get_available_raw_input())
                raw += raw2
                # if not keys:
                #     keys, raw2 = self._get_input(
                #         self.resize_wait)
                #     raw += raw2
                if keys != ['window resize']:
                    break
            if keys[-1:] != ['window resize']:
                keys.append('window resize')

        if keys == ['window resize']:
            self.prev_input_resize = 2
        elif self.prev_input_resize == 2 and not keys:
            self.prev_input_resize = 1
        else:
            self.prev_input_resize = 0

        if raw_keys:
            return keys, raw
        return keys

    def get_available_raw_input(self):
        """
        Return any currently-available input.  Does not block.

        This method is only used by the default `hook_event_loop`
        implementation; you can safely ignore it if you implement your own.
        """
        codes = []

        if self.event_loop and self.event_loop.records:
            for record in self.event_loop.records[0 : self.event_loop.size[0]]:
                if record.EventType == win32.EventType.KEY_EVENT:
                    e = record.Event.KeyEvent
                    if e.bKeyDown:
                        if e.uChar.UnicodeChar > 0:
                            codes.append(e.uChar.UnicodeChar)
                        else:
                            codes.append(e.wVirtualKeyCode)

        return codes

    def hook_event_loop(self, event_loop, callback):
        self.event_loop = event_loop
        super().hook_event_loop(event_loop, callback)

    def get_cols_rows(self):
        """Return the terminal dimensions (num columns, num rows)."""
        return self.cols_rows
