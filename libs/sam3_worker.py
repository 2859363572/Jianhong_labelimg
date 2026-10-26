"""Qt bridge: synchronous HTTP runs off the GUI thread, one image at a time."""

import logging
from typing import Callable, Optional, Sequence

from PyQt5.QtCore import QThread, pyqtSignal

from libs.sam3_client import SAM3Cancelled, SAM3Client, SAM3Error, SAM3Request


class SAM3Worker(QThread):
    result = pyqtSignal(str, object)
    progress = pyqtSignal(int, int)
    failed = pyqtSignal(str, str)
    completed = pyqtSignal(int, bool)
    persisted = pyqtSignal(str, bool)

    def __init__(self, client: SAM3Client, requests: Sequence[SAM3Request], parent=None,
                 persist: Optional[Callable] = None):
        super().__init__(parent)
        self.client = client
        self.requests = tuple(requests)
        self.persist = persist

    def run(self):
        count = 0
        for request in self.requests:
            if self.isInterruptionRequested():
                break
            try:
                detections = self.client.predict(request, cancelled=self.isInterruptionRequested)
                if self.isInterruptionRequested():
                    break
                if self.persist is not None:
                    written = self.persist(request.image_path, detections)
                    self.persisted.emit(request.image_path, written)
            except SAM3Cancelled:
                break
            except SAM3Error as exc:
                self.failed.emit(request.image_path, str(exc))
                break
            except Exception:
                # Keep unexpected adapter bugs from escaping a Qt thread entry.
                logging.getLogger(__name__).error("Unexpected SAM3 adapter failure")
                self.failed.emit(request.image_path, "Unexpected SAM3 adapter failure")
                break
            # Do not publish results if cancellation raced with completion.
            if self.isInterruptionRequested():
                break
            self.result.emit(request.image_path, detections)
            count += 1
            self.progress.emit(count, len(self.requests))
        self.completed.emit(count, self.isInterruptionRequested())
