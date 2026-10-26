"""Non-destructive persistence for SAM3 rectangle prelabels.

Existing YOLO class maps are immutable. Unknown labels require an explicit user
migration outside this helper, rather than changing IDs in an existing dataset.
CreateML output is per-image JSON; shared CreateML records are only inspected.
"""

import json
import math
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Sequence, Tuple

from PyQt5.QtGui import QImageReader

from libs.create_ml_io import CreateMLWriter
from libs.labelFile import LabelFileFormat
from libs.pascal_voc_io import PascalVocWriter
from libs.sam3_client import SAM3Detection, SAM3Error
from libs.yolo_io import YOLOWriter


class SAM3AnnotationError(SAM3Error):
    """An expected persistence or annotation-validation failure."""


_EXTENSIONS = (".xml", ".txt", ".json")
_FORMAT_EXTENSIONS = {
    LabelFileFormat.PASCAL_VOC: ".xml",
    LabelFileFormat.YOLO: ".txt",
    LabelFileFormat.CREATE_ML: ".json",
}


def annotation_paths(image_path: str, save_dir: Optional[str] = None) -> Tuple[str, ...]:
    """Return unique absolute output sidecars, then image-beside sidecars.

    Each group is ordered XML, TXT, JSON. This function performs no file I/O.
    """
    try:
        image = Path(os.path.abspath(os.fspath(image_path)))
        if not image_path or not image.stem:
            raise ValueError("An image path is required")
        output = Path(os.path.abspath(os.fspath(save_dir))) if save_dir else image.parent
        result = []
        seen = set()
        for directory in (output, image.parent):
            for extension in _EXTENSIONS:
                path = str(directory / (image.stem + extension))
                key = os.path.normcase(path)
                if key not in seen:
                    seen.add(key)
                    result.append(path)
        return tuple(result)
    except (OSError, TypeError, ValueError) as exc:
        raise SAM3AnnotationError("Invalid annotation path: {}".format(exc)) from exc


def _has_annotations(image: Path, paths: Tuple[str, ...]) -> bool:
    if any(os.path.lexists(path) for path in paths):
        return True
    # The existing CreateML writer also supports one JSON file for many images.
    # Never update such a file, but do not duplicate one of its image records.
    for directory in {Path(path).parent for path in paths}:
        if not directory.exists():
            continue
        for candidate in directory.iterdir():
            if candidate.suffix.lower() != ".json" or not candidate.is_file():
                continue
            try:
                with candidate.open("r", encoding="utf-8-sig") as source:
                    records = json.load(source)
            except (ValueError, UnicodeError) as exc:
                raise SAM3AnnotationError(
                    "Cannot check existing JSON annotations: {}".format(candidate)) from exc
            if isinstance(records, list):
                for record in records:
                    if not isinstance(record, dict) or "annotations" not in record:
                        continue
                    name = record.get("image")
                    if isinstance(name, str) and name.replace("\\", "/").rsplit("/", 1)[-1] == image.name:
                        return True
    return False


@contextmanager
def _directory_lock(directory: Path):
    """Coordinate helper calls across threads/processes, without stale takeover."""
    lock = directory / ".sam3-annotations.lock"
    deadline = time.monotonic() + 5.0
    while True:
        try:
            descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError as exc:
            if time.monotonic() >= deadline:
                raise SAM3AnnotationError(
                    "Annotation directory is busy (or has a stale SAM3 lock): {}".format(directory)) from exc
            time.sleep(0.02)
    try:
        os.close(descriptor)
        yield
    finally:
        lock.unlink()


def _validate_names(names: Sequence[str]) -> list:
    result = list(names)
    if any(not isinstance(name, str) or not name.strip() or name != name.strip()
           or any(ord(char) < 32 for char in name) for name in result):
        raise ValueError("Class names must be nonempty single-line labels without edge whitespace")
    if len(set(result)) != len(result):
        raise ValueError("Duplicate class names make YOLO class IDs ambiguous")
    return result


def _yolo_classes(directory: Path, class_names: Sequence[str], labels: Sequence[str]) -> list:
    class_file = directory / "classes.txt"
    if os.path.lexists(str(class_file)):
        # Match the existing YOLO reader's locale encoding and preserve line IDs.
        with class_file.open("r") as source:
            classes = _validate_names(source.read().splitlines())
    else:
        # Without a map, existing text annotations cannot safely be assigned IDs.
        if any(path.suffix.lower() == ".txt" for path in directory.iterdir()):
            raise ValueError("Existing TXT files have no classes.txt; refusing to invent a class map")
        classes = _validate_names(class_names)
    missing = sorted(set(labels).difference(classes))
    if missing:
        raise ValueError("YOLO labels absent from the stable class map: {}".format(", ".join(missing)))
    if not classes:
        raise ValueError("YOLO requires a nonempty class map")
    return classes


def _validate_detections(detections: Sequence[SAM3Detection], width: int, height: int) -> list:
    shapes = []
    for detection in detections:
        if not isinstance(detection, SAM3Detection):
            raise ValueError("Expected SAM3Detection rectangles")
        _validate_names([detection.label])
        if not isinstance(detection.bbox, (tuple, list)) or len(detection.bbox) != 4:
            raise ValueError("Expected an xyxy rectangle")
        values = tuple(detection.bbox) + (detection.score,)
        if any(isinstance(value, bool) or not isinstance(value, (float, int))
               or not math.isfinite(value) for value in values):
            raise ValueError("Detection coordinates and score must be finite numbers")
        x1, y1, x2, y2 = detection.bbox
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError("Detection rectangle is outside the image or has no area")
        if not 0 <= detection.score <= 1:
            raise ValueError("Detection score must be between zero and one")
        shapes.append(detection.as_shape())
    return shapes


def _publish(source: Path, destination: Path) -> bool:
    """Atomically expose a completed file, never replace an existing path.

    Hard links keep the guarantee on Windows and POSIX. Unsupported filesystems
    fail explicitly; copying to the destination would expose partial contents.
    """
    with source.open("rb+") as completed:
        os.fsync(completed.fileno())
    try:
        os.link(str(source), str(destination))
    except FileExistsError:
        return False
    return True


def save_new_annotations(image_path: str, detections: Sequence[SAM3Detection],
                         format: LabelFileFormat, save_dir: Optional[str],
                         class_names: Sequence[str]) -> bool:
    """Write only a new annotation; return False for existing or empty results.

    Expected path, image, class-map, writer and I/O failures raise
    SAM3AnnotationError. Output directories are created as needed. Publication
    never replaces a destination, and calls targeting one directory coordinate
    their format checks and YOLO map creation. External editors do not honor our
    lock, but even a destination created during publication is never replaced.
    """
    try:
        if format not in _FORMAT_EXTENSIONS:
            raise ValueError("Unsupported annotation format")
        paths = annotation_paths(image_path, save_dir)
        image_path = os.path.abspath(os.fspath(image_path))
        image = Path(image_path)
        output = Path(paths[0]).parent
        if not detections or _has_annotations(image, paths):
            return False
        reader = QImageReader(image_path)
        reader.setAutoTransform(True)
        bitmap = reader.read()
        if bitmap.isNull():
            raise ValueError("Cannot read image: {}".format(image))
        shapes = _validate_detections(detections, bitmap.width(), bitmap.height())
        output.mkdir(parents=True, exist_ok=True)
        destination = output / (image.stem + _FORMAT_EXTENSIONS[format])
        if format == LabelFileFormat.YOLO and destination.name.lower() == "classes.txt":
            raise ValueError("Image name 'classes' conflicts with the YOLO class map")
        with _directory_lock(output):
            if _has_annotations(image, paths):
                return False
            classes = (_yolo_classes(output, class_names, [shape["label"] for shape in shapes])
                       if format == LabelFileFormat.YOLO else [])
            # Writers can overwrite or create classes.txt. Confine all such writes
            # to our own directory; only finished files are linked into output.
            with tempfile.TemporaryDirectory(prefix=".sam3-", dir=str(output)) as temporary:
                temporary = Path(temporary)
                staged = temporary / destination.name
                image_size = [bitmap.height(), bitmap.width(), 1 if bitmap.isGrayscale() else 3]
                if format == LabelFileFormat.CREATE_ML:
                    CreateMLWriter(image.parent.name, image.name, image_size, shapes,
                                   str(staged), local_img_path=image_path).write()
                else:
                    writer_class = YOLOWriter if format == LabelFileFormat.YOLO else PascalVocWriter
                    writer = writer_class(image.parent.name, image.name, image_size,
                                          local_img_path=image_path)
                    for detection in detections:
                        x1, y1, x2, y2 = detection.bbox
                        if format == LabelFileFormat.PASCAL_VOC:
                            x1, y1, x2, y2 = math.floor(x1), math.floor(y1), math.ceil(x2), math.ceil(y2)
                        writer.add_bnd_box(x1, y1, x2, y2, detection.label, False)
                    if format == LabelFileFormat.YOLO:
                        writer.save(class_list=classes.copy(), target_file=str(staged))
                    else:
                        writer.save(target_file=str(staged))
                if _has_annotations(image, paths):
                    return False
                if format == LabelFileFormat.YOLO:
                    class_file = output / "classes.txt"
                    if not os.path.lexists(str(class_file)):
                        if not _publish(temporary / "classes.txt", class_file):
                            # A non-cooperating writer may have published a map.
                            if _yolo_classes(output, class_names, classes) != classes:
                                raise ValueError("YOLO class map changed during publication")
                    elif _yolo_classes(output, class_names, classes) != classes:
                        raise ValueError("YOLO class map changed during publication")
                return _publish(staged, destination)
    except SAM3AnnotationError:
        raise
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        raise SAM3AnnotationError("Cannot save SAM3 annotations: {}".format(exc)) from exc
