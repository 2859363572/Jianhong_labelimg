"""SAM3 transport and reference protocol; not a LuoHuaLabel API contract."""

import base64
import json
import math
from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol, Tuple
from urllib.parse import urlsplit

from PyQt5.QtCore import QCoreApplication, QEventLoop, QTimer, QUrl
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from PIL import Image, ImageOps


class SAM3Error(Exception):
    """A safe, user-displayable inference failure."""


@dataclass(frozen=True)
class SAM3Config:
    endpoint: str
    timeout_seconds: float = 30.0
    token: str = field(default="", repr=False)

    def __post_init__(self):
        parsed = urlsplit(self.endpoint)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("SAM3 endpoint must be a complete HTTP(S) URL")
        parsed.port  # Validate malformed or out-of-range ports before starting a worker.
        if parsed.username or parsed.password or parsed.fragment or parsed.query:
            raise ValueError("Put credentials in token, not in the endpoint URL")
        if not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 600:
            raise ValueError("SAM3 timeout must be between 0 and 600 seconds")
        if any(ord(char) < 33 or ord(char) > 126 for char in self.token):
            raise ValueError("SAM3 token must contain printable ASCII without spaces")


@dataclass(frozen=True)
class PointPrompt:
    x: float
    y: float
    positive: bool = True


@dataclass(frozen=True)
class SAM3Request:
    image_path: str
    label: str
    text: str = ""
    points: Tuple[PointPrompt, ...] = ()
    box: Optional[Tuple[float, float, float, float]] = None
    threshold: float = 0.5

    def __post_init__(self):
        if not self.image_path or not self.label.strip():
            raise ValueError("Image path and output label are required")
        if not self.text.strip() and not self.points and self.box is None:
            raise ValueError("Provide a text, point, or box prompt")
        if not math.isfinite(self.threshold) or not 0 <= self.threshold <= 1:
            raise ValueError("Threshold must be between 0 and 1")


@dataclass(frozen=True)
class SAM3Detection:
    label: str
    bbox: Tuple[float, float, float, float]
    score: float

    def as_shape(self):
        x1, y1, x2, y2 = self.bbox
        return {"label": self.label,
                "points": [(x1, y1), (x2, y1), (x2, y2), (x1, y2)],
                "confidence": self.score, "difficult": False}


class SAM3Protocol(Protocol):
    def encode(self, request: SAM3Request, image: bytes, width: int, height: int) -> dict:
        ...

    def decode(self, response: object, request: SAM3Request,
               width: int, height: int) -> Tuple[SAM3Detection, ...]:
        ...


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Expected a finite number")
    return float(value)


def _box(value, width, height):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError("Expected an xyxy box")
    x1, y1, x2, y2 = map(_number, value)
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        raise ValueError("Box is outside the original image or has no area")
    return x1, y1, x2, y2


class ReferenceJSONProtocol:
    """Explicit mock/reference contract until the real server API is inspected."""

    def encode(self, request, image, width, height):
        points = []
        for point in request.points:
            x, y = _number(point.x), _number(point.y)
            if not 0 <= x <= width or not 0 <= y <= height or not isinstance(point.positive, bool):
                raise ValueError("Invalid point prompt")
            points.append({"x": x, "y": y, "positive": point.positive})
        box = _box(request.box, width, height) if request.box is not None else None
        return {"image_base64": base64.b64encode(image).decode("ascii"),
                "width": width, "height": height, "text": request.text,
                "points": points, "box_xyxy": box, "threshold": request.threshold}

    def decode(self, response, request, width, height):
        if not isinstance(response, dict) or not isinstance(response.get("detections"), list):
            raise ValueError("Missing detections array")
        detections = []
        for item in response["detections"]:
            if not isinstance(item, dict):
                raise ValueError("Invalid detection")
            bbox = _box(item.get("bbox_xyxy"), width, height)
            score = _number(item.get("score"))
            if not 0 <= score <= 1:
                raise ValueError("Invalid confidence score")
            if score >= request.threshold:
                detections.append(SAM3Detection(request.label, bbox, score))
        return tuple(detections)


class SAM3Cancelled(SAM3Error):
    """The caller cancelled a request; no result should be applied."""


def _post_json(config: SAM3Config, payload: bytes, limit: int,
               cancelled: Callable[[], bool]) -> bytes:
    if cancelled():
        raise SAM3Cancelled("SAM3 request cancelled")
    if QCoreApplication.instance() is None:
        raise SAM3Error("A Qt application is required for SAM3 networking")
    # All network objects and their event loop belong to the calling worker.
    manager = QNetworkAccessManager()
    request = QNetworkRequest(QUrl(config.endpoint))
    request.setRawHeader(b"Content-Type", b"application/json")
    request.setRawHeader(b"Accept", b"application/json")
    request.setAttribute(QNetworkRequest.RedirectPolicyAttribute,
                         QNetworkRequest.ManualRedirectPolicy)
    if config.token:
        request.setRawHeader(b"Authorization", ("Bearer " + config.token).encode("ascii"))
    reply = manager.post(request, payload)
    reply.setReadBufferSize(64 * 1024)
    loop = QEventLoop()
    deadline = QTimer()
    deadline.setSingleShot(True)
    cancellation = QTimer()
    cancellation.setInterval(20)
    body = bytearray()
    failure = []

    def stop(message):
        if not failure:
            failure.append(message)
        reply.abort()
        loop.quit()

    def read_available():
        if reply.isOpen():
            body.extend(bytes(reply.readAll()))
        if len(body) > limit:
            stop("SAM3 response exceeds the size limit")

    def check_cancelled():
        if cancelled():
            stop("SAM3 request cancelled")

    reply.readyRead.connect(read_available)
    reply.finished.connect(loop.quit)
    deadline.timeout.connect(lambda: stop("SAM3 request timed out"))
    cancellation.timeout.connect(check_cancelled)
    deadline.start(max(1, math.ceil(config.timeout_seconds * 1000)))
    cancellation.start()
    try:
        if not reply.isFinished():
            loop.exec_()
        # Cancellation wins even if a response arrived in the same event turn.
        if cancelled():
            raise SAM3Cancelled("SAM3 request cancelled")
        read_available()
        if failure:
            raise SAM3Error(failure[0])
        status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if status is not None and not 200 <= int(status) < 300:
            raise SAM3Error("SAM3 HTTP error: {}".format(int(status)))
        if reply.error() != QNetworkReply.NoError or status is None:
            raise SAM3Error("Cannot connect to SAM3 service")
        return bytes(body)
    finally:
        deadline.stop()
        cancellation.stop()
        if not reply.isFinished():
            reply.abort()
        reply.deleteLater()


class SAM3Client:
    MAX_IMAGE_BYTES = 20 * 1024 * 1024
    MAX_RESPONSE_BYTES = 4 * 1024 * 1024

    def __init__(self, config: SAM3Config, protocol: SAM3Protocol):
        self.config = config
        self.protocol = protocol

    def predict(self, request: SAM3Request,
                cancelled: Callable[[], bool] = lambda: False) -> Tuple[SAM3Detection, ...]:
        if cancelled():
            raise SAM3Cancelled("SAM3 request cancelled")
        try:
            with open(request.image_path, "rb") as source:
                image_bytes = source.read(self.MAX_IMAGE_BYTES + 1)
            if len(image_bytes) > self.MAX_IMAGE_BYTES:
                raise SAM3Error("Image exceeds the 20 MiB upload limit")
            # Inspect exactly the bytes uploaded, not a second version of the file.
            from io import BytesIO
            with Image.open(BytesIO(image_bytes)) as image:
                image.verify()
            with Image.open(BytesIO(image_bytes)) as image:
                width, height = image.size
                orientation = image.getexif().get(274, 1)
            # Match QImageReader.setAutoTransform(True) used by the canvas.
            if orientation not in (None, 1):
                with Image.open(BytesIO(image_bytes)) as image:
                    transformed = ImageOps.exif_transpose(image)
                    width, height = transformed.size
                    buffer = BytesIO()
                    transformed.save(buffer, format="PNG")
                    image_bytes = buffer.getvalue()
                if len(image_bytes) > self.MAX_IMAGE_BYTES:
                    raise SAM3Error("Oriented image exceeds the 20 MiB upload limit")
            payload = self.protocol.encode(request, image_bytes, width, height)
        except SAM3Error:
            raise
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
            raise SAM3Error("Cannot read image or encode SAM3 prompt") from exc

        try:
            encoded = json.dumps(payload, allow_nan=False).encode("utf-8")
        except (ValueError, TypeError, OverflowError, RecursionError) as exc:
            raise SAM3Error("Cannot encode SAM3 prompt") from exc
        body = _post_json(self.config, encoded, self.MAX_RESPONSE_BYTES, cancelled)
        try:
            return self.protocol.decode(json.loads(body), request, width, height)
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
            raise SAM3Error("Invalid SAM3 response; check the API protocol") from exc
