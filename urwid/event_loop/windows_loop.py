from .abstract_loop import EventLoop, ExitMainLoop
import os
import typing
from typing import Callable
import msvcrt
from . import win32
import ctypes.wintypes


class WindowsEventLoop(EventLoop):
    def __init__(self) -> None:
        # self.iocp = CreateIoCompletionPort(INVALID_HANDLE_VALUE, None, None, 0)
        self.watch = None
        self.records = (win32.INPUT_RECORD * 128)()
        self.size = (ctypes.wintypes.DWORD * 1)()
        self.idle = None

    def alarm(
        self, seconds: float | int, callback: Callable[[], typing.Any]
    ) -> typing.Any:
        # raise NotImplementedError()
        pass

    def enter_idle(self, callback):
        # raise NotImplementedError()
        self.idle = callback

    def remove_alarm(self, handle) -> bool:
        raise NotImplementedError()

    def remove_enter_idle(self, handle) -> bool:
        # raise NotImplementedError()
        pass

    def remove_watch_file(self, handle) -> bool:
        # raise NotImplementedError()
        pass

    def run(self) -> None:
        assert self.watch
        handle, callback = self.watch
        assert self.idle
        idle = self.idle
        while True:
            idle()
            if not win32.ReadConsoleInputW(handle, self.records, 128, self.size):
                raise Exception("ReadConsoleInput")
            if self.size[0] > 0:
                callback()

    def watch_file(self, fd: int, callback: Callable[[], typing.Any]):
        # raise NotImplementedError()
        assert os.isatty(fd), "not term"
        handle = msvcrt.get_osfhandle(fd)
        self.watch = (handle, callback)
        return self.watch
