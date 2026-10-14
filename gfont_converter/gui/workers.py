"""Фоновые потоки: окно никогда не ждёт движок.

EngineWorker живёт в отдельном QThread и ОДИН работает с открытым шрифтом
(fontTools не потокобезопасен): предпросмотр строки и фоновый анализ всех
символов набора (по одному символу за итерацию цикла событий, поэтому
запросы предпросмотра не ждут окончания анализа).

TaskWorker — длительные операции (сохранение, N вариантов, калибровка)
с прогрессом и отменой.
"""

from __future__ import annotations

import threading
import traceback
from typing import Callable, List, Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from gfont.errors import Cancelled, UserError
from gfont.session import FontSession, UiParams


class EngineWorker(QObject):
    sessionLoaded = Signal(object)            # FontSession
    sessionFailed = Signal(str)
    previewReady = Signal(int, object)        # req_id, dict
    glyphReady = Signal(int, object)          # gen_id, GlyphResult
    analysisProgress = Signal(int, int, int)  # gen_id, done, total
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.session: Optional[FontSession] = None
        # последние номера запросов выставляет GUI-поток ДО отправки сигнала
        self.latest_preview = 0
        self.latest_analysis = 0
        self._an_gen = 0
        self._an_codes: List[int] = []
        self._an_params: Optional[UiParams] = None
        self._an_pos = 0

    @Slot(str)
    def loadFont(self, path: str) -> None:
        try:
            self.session = FontSession(path)
        except UserError as exc:
            self.sessionFailed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — показываем пользователю
            self.sessionFailed.emit(f"Не удалось открыть шрифт: {exc}")
            return
        self._an_codes = []
        self.sessionLoaded.emit(self.session)

    @Slot(int, str, object, bool)
    def requestPreview(self, req_id: int, text: str, params: UiParams, with_source: bool) -> None:
        if req_id != self.latest_preview or self.session is None:
            return
        try:
            glyphs = {}
            outlines = {}
            for ch in dict.fromkeys(text):
                if ch.isspace():
                    continue
                if req_id != self.latest_preview:
                    return  # пришёл более новый запрос
                r = self.session.glyph(ord(ch), params)
                glyphs[ch] = r
                if with_source and r.src_code is not None:
                    outlines[ch] = self.session.outline(ord(ch), params, r.cx)
            self.previewReady.emit(req_id, {"glyphs": glyphs, "outlines": outlines,
                                            "params": params, "text": text})
        except Exception:  # noqa: BLE001
            self.error.emit("Ошибка предпросмотра:\n" + traceback.format_exc())

    @Slot(int, object, object)
    def startAnalysis(self, gen_id: int, codes: list, params: UiParams) -> None:
        self._an_gen = gen_id
        self._an_codes = list(codes)
        self._an_params = params
        self._an_pos = 0
        QTimer.singleShot(0, self._analysis_step)

    def _analysis_step(self) -> None:
        gen = self._an_gen
        if gen != self.latest_analysis or self.session is None:
            return
        if self._an_pos >= len(self._an_codes):
            return
        code = self._an_codes[self._an_pos]
        self._an_pos += 1
        try:
            r = self.session.glyph(code, self._an_params)
        except Exception as exc:  # noqa: BLE001
            from gfont.session import GlyphResult
            r = GlyphResult(code, [], [f"ошибка: {exc}"], None)
        self.glyphReady.emit(gen, r)
        self.analysisProgress.emit(gen, self._an_pos, len(self._an_codes))
        if self._an_pos < len(self._an_codes):
            QTimer.singleShot(0, self._analysis_step)


class EngineThread:
    """QThread + EngineWorker с удобными методами для окна."""

    def __init__(self):
        self.thread = QThread()
        self.thread.setObjectName("engine")
        self.worker = EngineWorker()
        self.worker.moveToThread(self.thread)
        self.thread.start()

    def stop(self) -> None:
        self.worker.latest_preview = -1
        self.worker.latest_analysis = -1
        self.thread.quit()
        self.thread.wait(5000)


class TaskWorker(QThread):
    """Длительная операция в отдельном потоке: fn(progress, cancel, log) -> результат."""
    progress = Signal(int, int, str)
    logLine = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, fn: Callable, title: str):
        super().__init__()
        self.fn = fn
        self.title = title
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def run(self) -> None:
        try:
            result = self.fn(lambda d, t, msg="": self.progress.emit(d, t, msg),
                             self.is_cancelled, self.logLine.emit)
        except Cancelled:
            self.cancelled.emit()
        except UserError as exc:
            self.failed.emit(str(exc))
        except Exception:  # noqa: BLE001
            self.failed.emit(f"{self.title}: непредвиденная ошибка.\n\n{traceback.format_exc()}")
        else:
            self.succeeded.emit(result)
