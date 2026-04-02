from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFileDialog, QSlider, QGroupBox,
                             QProgressBar, QRadioButton, QButtonGroup, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import os


class PredictThread(QThread):
    progress = pyqtSignal(int, int)
    result = pyqtSignal(str, list)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, predictor, img_paths):
        super().__init__()
        self.predictor = predictor
        self.img_paths = img_paths

    def run(self):
        try:
            from PIL import Image
            import numpy as np
            total = len(self.img_paths)
            count = 0
            for img_path in self.img_paths:
                img = Image.open(img_path).convert('RGB')
                img_rgb = np.array(img)
                detections = self.predictor.predict_image(img_rgb)
                self.result.emit(img_path, detections)
                count += 1
                self.progress.emit(count, total)
            self.finished.emit(count)
        except Exception as e:
            self.error.emit(str(e))


class YOLOPredictDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.predictor = None
        self.predict_thread = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle('YOLO 模型辅助预标注')
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        model_group = QGroupBox('模型设置')
        model_layout = QVBoxLayout(model_group)

        path_layout = QHBoxLayout()
        self.model_path_label = QLabel('未选择模型')
        self.model_path_label.setWordWrap(True)
        self.model_path_label.setStyleSheet('color: #757575;')
        btn_browse = QPushButton('选择 ONNX 模型')
        btn_browse.clicked.connect(self._browse_model)
        path_layout.addWidget(self.model_path_label, 1)
        path_layout.addWidget(btn_browse)
        model_layout.addLayout(path_layout)

        class_layout = QHBoxLayout()
        self.class_path_label = QLabel('未选择类别文件（可选）')
        self.class_path_label.setWordWrap(True)
        self.class_path_label.setStyleSheet('color: #757575;')
        btn_class = QPushButton('选择 classes.txt')
        btn_class.clicked.connect(self._browse_classes)
        class_layout.addWidget(self.class_path_label, 1)
        class_layout.addWidget(btn_class)
        model_layout.addLayout(class_layout)

        layout.addWidget(model_group)

        param_group = QGroupBox('推理参数')
        param_layout = QVBoxLayout(param_group)

        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel('置信度阈值:'))
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(5, 95)
        self.conf_slider.setValue(25)
        self.conf_label = QLabel('0.25')
        self.conf_label.setMinimumWidth(40)
        self.conf_slider.valueChanged.connect(
            lambda v: self.conf_label.setText(f'{v / 100:.2f}'))
        conf_layout.addWidget(self.conf_slider, 1)
        conf_layout.addWidget(self.conf_label)
        param_layout.addLayout(conf_layout)

        iou_layout = QHBoxLayout()
        iou_layout.addWidget(QLabel('NMS 阈值:'))
        self.iou_slider = QSlider(Qt.Horizontal)
        self.iou_slider.setRange(10, 90)
        self.iou_slider.setValue(45)
        self.iou_label = QLabel('0.45')
        self.iou_label.setMinimumWidth(40)
        self.iou_slider.valueChanged.connect(
            lambda v: self.iou_label.setText(f'{v / 100:.2f}'))
        iou_layout.addWidget(self.iou_slider, 1)
        iou_layout.addWidget(self.iou_label)
        param_layout.addLayout(iou_layout)

        layout.addWidget(param_group)

        scope_group = QGroupBox('预标注范围')
        scope_layout = QHBoxLayout(scope_group)
        self.scope_group = QButtonGroup(self)
        self.rb_current = QRadioButton('当前图片')
        self.rb_all = QRadioButton('目录全部图片')
        self.rb_unlabeled = QRadioButton('未标注图片')
        self.rb_current.setChecked(True)
        self.scope_group.addButton(self.rb_current, 0)
        self.scope_group.addButton(self.rb_all, 1)
        self.scope_group.addButton(self.rb_unlabeled, 2)
        scope_layout.addWidget(self.rb_current)
        scope_layout.addWidget(self.rb_all)
        scope_layout.addWidget(self.rb_unlabeled)
        layout.addWidget(scope_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton('开始预标注')
        self.btn_run.setStyleSheet(
            'background-color:#2196F3; color:white; font-weight:bold; padding:8px 20px; border-radius:4px;')
        self.btn_run.clicked.connect(self._run_predict)
        self.btn_cancel = QPushButton('取消')
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_run)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _browse_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '选择 ONNX 模型文件', '', 'ONNX Files (*.onnx)')
        if path:
            self.model_path_label.setText(path)
            self.model_path_label.setStyleSheet('color: #333333;')

    def _browse_classes(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '选择类别文件', '', 'Text Files (*.txt)')
        if path:
            self.class_path_label.setText(path)
            self.class_path_label.setStyleSheet('color: #333333;')

    def _load_class_names(self):
        path = self.class_path_label.text()
        if path and os.path.isfile(path) and '未选择' not in path:
            with open(path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        return []

    def _get_target_images(self):
        scope_id = self.scope_group.checkedId()
        if scope_id == 0:
            if self.main_window.file_path:
                return [self.main_window.file_path]
            return []
        elif scope_id == 1:
            return list(self.main_window.m_img_list)
        elif scope_id == 2:
            return [p for p in self.main_window.m_img_list
                    if not self.main_window.hasAnnotationFile(p)]
        return []

    def _run_predict(self):
        model_path = self.model_path_label.text()
        if '未选择' in model_path or not os.path.isfile(model_path):
            QMessageBox.warning(self, '错误', '请先选择有效的 ONNX 模型文件')
            return

        from libs.yolo_predictor import YOLOPredictor
        class_names = self._load_class_names()
        conf = self.conf_slider.value() / 100
        iou = self.iou_slider.value() / 100

        self.predictor = YOLOPredictor(
            model_path, class_names=class_names,
            conf_threshold=conf, iou_threshold=iou)

        self.status_label.setText('正在加载模型...')
        self.btn_run.setEnabled(False)
        QApplication.processEvents()

        if not self.predictor.load_model():
            self.status_label.setText('模型加载失败')
            self.btn_run.setEnabled(True)
            return

        img_paths = self._get_target_images()
        if not img_paths:
            QMessageBox.warning(self, '错误', '没有可预标注的图片')
            self.btn_run.setEnabled(True)
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(img_paths))
        self.progress_bar.setValue(0)
        self.status_label.setText(f'正在推理 {len(img_paths)} 张图片...')

        self.predict_thread = PredictThread(self.predictor, img_paths)
        self.predict_thread.progress.connect(self._on_progress)
        self.predict_thread.result.connect(self._on_result)
        self.predict_thread.finished.connect(self._on_finished)
        self.predict_thread.error.connect(self._on_error)
        self.predict_thread.start()

    def _on_progress(self, current, total):
        self.progress_bar.setValue(current)
        self.status_label.setText(f'正在处理: {current}/{total}')

    def _on_result(self, img_path, detections):
        if not detections:
            return
        if img_path == self.main_window.file_path:
            self.main_window.load_yolo_detections(detections)

    def _on_finished(self, count):
        self.status_label.setText(f'完成！共处理 {count} 张图片')
        self.btn_run.setEnabled(True)
        QMessageBox.information(self, '完成', f'预标注完成，共处理 {count} 张图片')

    def _on_error(self, msg):
        self.status_label.setText(f'错误: {msg}')
        self.btn_run.setEnabled(True)
        QMessageBox.critical(self, '错误', msg)


from PyQt5.QtWidgets import QApplication
