"""SAM3 desktop workflow using an explicitly selected API protocol."""

import os
from collections import Counter
from functools import partial

from PyQt5.QtCore import QEvent, QObject, QPoint, QRect, Qt
from PyQt5.QtWidgets import (QAction, QComboBox, QDialog, QDoubleSpinBox,
                             QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                             QMessageBox, QProgressBar, QPushButton, QRubberBand,
                             QSpinBox, QVBoxLayout)

from libs.sam3_annotations import SAM3AnnotationError, annotation_paths, save_new_annotations
from libs.sam3_client import (PointPrompt, ReferenceJSONProtocol, SAM3Client,
                             SAM3Config, SAM3Request)
from libs.sam3_worker import SAM3Worker


class SAM3Dialog(QDialog):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller
        self.setWindowTitle('SAM3 API')
        self.setMinimumWidth(480)
        self.setModal(True)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.endpoint = QLineEdit(controller.window.settings.get('sam3_endpoint', ''))
        self.endpoint.setPlaceholderText('https://host:port/path')
        self.token = QLineEdit(controller.token)
        self.token.setEchoMode(QLineEdit.Password)
        self.protocol = QComboBox()
        self.protocol.addItem('参考 JSON（待服务端验证）')
        self.prompt = QLineEdit(controller.prompt)
        self.label = QLineEdit(controller.label)
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0, 1)
        self.threshold.setSingleStep(.05)
        self.threshold.setValue(controller.threshold)
        self.timeout = QSpinBox()
        self.timeout.setRange(1, 600)
        self.timeout.setSuffix(' s')
        self.timeout.setValue(controller.timeout)
        self.scope = QComboBox()
        self.scope.addItem('当前帧：追加到画布', 'current')
        self.scope.addItem('全部帧：跳过已有标注', 'all')
        self.scope.addItem('未标注帧', 'unlabeled')
        for name, control in [('接口地址', self.endpoint), ('Token', self.token),
                              ('协议', self.protocol), ('提示词', self.prompt),
                              ('输出标签', self.label), ('置信度', self.threshold),
                              ('请求截止时间', self.timeout), ('范围', self.scope)]:
            form.addRow(name, control)
        layout.addLayout(form)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.status = QLabel('未连接')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.run_button = QPushButton('开始预标注')
        self.run_button.clicked.connect(self.start)
        self.manual_button = QPushButton('启用点 / 框提示')
        self.manual_button.clicked.connect(self.enable_manual)
        self.cancel_button = QPushButton('关闭')
        self.cancel_button.clicked.connect(self.reject)
        for button in (self.run_button, self.manual_button, self.cancel_button):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.controls = [self.endpoint, self.token, self.protocol, self.prompt,
                         self.label, self.threshold, self.timeout, self.scope,
                         self.run_button, self.manual_button]
        self.close_pending = False

    def configure(self):
        try:
            config = SAM3Config(self.endpoint.text().strip(), self.timeout.value(),
                                self.token.text().strip())
            if not self.label.text().strip():
                raise ValueError('请输入输出标签')
            self.controller.configure(config, self.prompt.text().strip(),
                                      self.label.text().strip(), self.threshold.value())
            return True
        except ValueError as exc:
            QMessageBox.warning(self, 'SAM3', str(exc))
            return False

    def start(self):
        if not self.prompt.text().strip():
            QMessageBox.warning(self, 'SAM3', '请输入提示词')
            return
        if self.configure():
            self.controller.start_text(self.scope.currentData())

    def enable_manual(self):
        if self.configure():
            self.controller.manual_action.setChecked(True)
            self.accept()

    def set_busy(self, busy):
        for control in self.controls:
            control.setEnabled(not busy)
        self.cancel_button.setText('取消任务' if busy else '关闭')

    def reject(self):
        if self.controller.busy:
            self.close_pending = True
            self.controller.cancel()
            self.status.setText('正在取消...')
            return
        super().reject()

    def closeEvent(self, event):
        if self.controller.busy:
            self.reject()
            event.ignore()
        else:
            event.accept()


class SAM3Controller(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.dialog = None
        self.worker = None
        self.client = None
        self.token = ''
        self.prompt = ''
        self.label = ''
        self.threshold = .5
        self.timeout = 30
        self.generation = 0
        self.batch = False
        self.cancelled = False
        self.closing = False
        self.origin = None
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, window.canvas)
        self.manual_action = QAction('SAM3 点 / 框提示', window)
        self.manual_action.setCheckable(True)
        self.manual_action.toggled.connect(self.set_manual)
        self.cancel_action = QAction('取消 SAM3 请求', window)
        self.cancel_action.triggered.connect(self.cancel)
        self.cancel_action.setEnabled(False)
        window.canvas.installEventFilter(self)

    @property
    def busy(self):
        # Retain even a stopped thread until its queued result slots drain.
        return self.worker is not None

    def show(self):
        if self.dialog is None:
            self.dialog = SAM3Dialog(self)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def configure(self, config, prompt, label, threshold):
        self.client = SAM3Client(config, ReferenceJSONProtocol())
        self.token, self.prompt, self.label = config.token, prompt, label
        self.threshold, self.timeout = threshold, int(config.timeout_seconds)
        self.window.settings['sam3_endpoint'] = config.endpoint

    def set_manual(self, enabled):
        self.origin = None
        self.rubber_band.hide()
        if enabled and self.client is None:
            self.manual_action.setChecked(False)
            self.show()
            return
        if enabled:
            self.window._sam_mode = False
        self.window.status('SAM3 点 / 框提示已启用' if enabled else 'SAM3 点 / 框提示已关闭')

    def invalidate_frame(self):
        self.generation += 1
        self.origin = None
        self.rubber_band.hide()
        if self.busy and not self.batch:
            self.cancel()

    def cancel(self):
        self.cancelled = True
        if self.worker is not None:
            self.worker.requestInterruption()

    def can_close(self):
        if self.busy:
            self.closing = True
            self.cancel()
            return False
        return True

    def signature(self):
        return tuple((shape.label, shape.difficult,
                      tuple((p.x(), p.y()) for p in shape.points))
                     for shape in self.window.canvas.shapes)

    def start_text(self, scope):
        if self.busy:
            return
        window = self.window
        if not window.file_path or window.canvas.current:
            QMessageBox.warning(self.dialog, 'SAM3', '请先打开图片并完成当前绘框')
            return
        paths = [window.file_path] if scope == 'current' else list(window.m_img_list)
        self.batch = scope != 'current'
        if self.batch:
            output = window.default_save_dir
            names = Counter(os.path.normcase(os.path.splitext(annotation_paths(p, output)[0])[0])
                            for p in paths)
            if any(count > 1 for count in names.values()):
                QMessageBox.warning(self.dialog, 'SAM3', '图片共享同一标注文件名，输出会产生冲突')
                return
            paths = [p for p in paths if not any(os.path.exists(a) for a in annotation_paths(p, output))
                     and not (p == window.file_path and (window.dirty or window.canvas.shapes))]
        if not paths:
            self.dialog.status.setText('没有可处理的未标注图片')
            return
        requests = [SAM3Request(p, self.label, text=self.prompt, threshold=self.threshold) for p in paths]
        self._start(requests)

    def _start(self, requests):
        self.cancelled = False
        self.request_generation = self.generation
        self.request_signature = self.signature()
        self.request_path = self.window.file_path
        self.output_dir = self.window.default_save_dir
        self.output_format = self.window.label_file_format
        self.class_names = list(self.window.label_hist)
        if self.label not in self.class_names:
            self.class_names.append(self.label)
        self.written = 0
        self.received = 0
        self.error_message = ''
        persist = (partial(save_new_annotations, format=self.output_format,
                           save_dir=self.output_dir, class_names=self.class_names)
                   if self.batch else None)
        self.worker = SAM3Worker(self.client, requests, self, persist=persist)
        self.worker.result.connect(self._result)
        self.worker.persisted.connect(self._persisted)
        self.worker.progress.connect(self._progress)
        self.worker.failed.connect(self._failed)
        self.worker.finished.connect(self._finished)
        self.cancel_action.setEnabled(True)
        if self.dialog is not None:
            self.dialog.set_busy(True)
            self.dialog.progress.setRange(0, len(requests))
            self.dialog.progress.setValue(0)
            self.dialog.status.setText('正在请求 SAM3...')
        self.window.status('正在请求 SAM3...')
        self.worker.start()

    def _result(self, image_path, detections):
        if self.cancelled:
            return
        try:
            if not self.batch:
                if (self.generation != self.request_generation or image_path != self.window.file_path
                        or self.signature() != self.request_signature):
                    self.error_message = '图片或标注已变化，已丢弃过期结果'
                    return
                self.apply_detections(detections)
            self.received += len(detections)
        except (OSError, ValueError, SAM3AnnotationError) as exc:
            self._failed(image_path, '保存标注失败：{}'.format(exc))
            self.cancel()

    def _persisted(self, image_path, written):
        if written:
            self.written += 1
            if image_path not in self.window._annotated_paths:
                self.window._annotated_paths.add(image_path)
                self.window._annotated_count_cache += 1

    def apply_detections(self, detections):
        from PyQt5.QtCore import QPointF
        from libs.shape import Shape
        from libs.utils import generate_color_by_text
        if not detections:
            return
        window = self.window
        window.save_undo_snapshot()
        for detection in detections:
            shape = Shape(label=detection.label)
            for x, y in detection.as_shape()['points']:
                shape.add_point(QPointF(x, y))
            shape.close()
            shape.line_color = generate_color_by_text(detection.label)
            shape.fill_color = generate_color_by_text(detection.label)
            if detection.label not in window.label_hist:
                window.label_hist.append(detection.label)
            window.canvas.shapes.append(shape)
            window.add_label(shape)
        window.set_dirty()
        window.canvas.update()

    def _progress(self, count, total):
        if self.dialog is not None:
            self.dialog.progress.setValue(count)
            self.dialog.status.setText('已处理 {} / {}'.format(count, total))

    def _failed(self, image_path, message):
        self.error_message = '{}：{}'.format(os.path.basename(image_path), message)

    def _finished(self):
        worker, self.worker = self.worker, None
        worker.deleteLater()
        self.cancel_action.setEnabled(False)
        message = self.error_message or ('已取消' if self.cancelled else
                   '完成：{} 个框，{} 帧已写入'.format(self.received, self.written))
        self.window.status(message, 15000)
        if self.batch and self.written:
            # Only reload an unchanged, originally empty current frame.
            if (self.generation == self.request_generation and self.window.file_path == self.request_path
                    and self.signature() == self.request_signature and not self.window.dirty):
                self.window.load_file(self.window.file_path)
        if self.dialog is not None:
            self.dialog.set_busy(False)
            self.dialog.status.setText(message)
            if self.dialog.close_pending:
                self.dialog.close_pending = False
                self.dialog.reject()
        if self.closing:
            self.closing = False
            self.window.close()

    def eventFilter(self, watched, event):
        if watched is not self.window.canvas or not self.manual_action.isChecked():
            return False
        canvas = self.window.canvas
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            self.cancel()
            self.manual_action.setChecked(False)
            return True
        if event.type() not in (QEvent.MouseButtonPress, QEvent.MouseMove,
                                QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick):
            return False
        if event.type() == QEvent.MouseButtonDblClick:
            return True
        if self.busy:
            return True
        if canvas.pixmap.isNull() or canvas.current:
            return False
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            pos = canvas.transform_pos(event.pos())
            if not canvas.out_of_pixmap(pos):
                self.origin = event.pos()
                self.rubber_band.setGeometry(QRect(self.origin, self.origin))
                self.rubber_band.show()
            return True
        if event.type() == QEvent.MouseMove and self.origin is not None:
            self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())
            return True
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            origin, self.origin = self.origin, None
            self.rubber_band.hide()
            if origin is None:
                return True
            start = canvas.transform_pos(origin)
            end = canvas.transform_pos(event.pos())
            end.setX(min(max(end.x(), 0), canvas.pixmap.width()))
            end.setY(min(max(end.y(), 0), canvas.pixmap.height()))
            box = None
            points = ()
            if (event.pos() - origin).manhattanLength() < 5:
                points = (PointPrompt(start.x(), start.y()),)
            elif abs(start.x() - end.x()) > 0 and abs(start.y() - end.y()) > 0:
                box = (min(start.x(), end.x()), min(start.y(), end.y()),
                       max(start.x(), end.x()), max(start.y(), end.y()))
            else:
                return True
            self.batch = False
            self._start([SAM3Request(self.window.file_path, self.label,
                                     points=points, box=box, threshold=self.threshold)])
            return True
        return False
