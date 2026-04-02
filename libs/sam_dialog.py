from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFileDialog, QGroupBox, QMessageBox,
                             QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import os


class SAMDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.predictor = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle('SAM 半自动标注')
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        model_group = QGroupBox('模型设置')
        model_layout = QVBoxLayout(model_group)

        enc_layout = QHBoxLayout()
        self.encoder_label = QLabel('未选择编码器模型')
        self.encoder_label.setStyleSheet('color: #757575;')
        self.encoder_label.setWordWrap(True)
        btn_enc = QPushButton('选择编码器 (.onnx)')
        btn_enc.clicked.connect(self._browse_encoder)
        enc_layout.addWidget(self.encoder_label, 1)
        enc_layout.addWidget(btn_enc)
        model_layout.addLayout(enc_layout)

        dec_layout = QHBoxLayout()
        self.decoder_label = QLabel('未选择解码器模型')
        self.decoder_label.setStyleSheet('color: #757575;')
        self.decoder_label.setWordWrap(True)
        btn_dec = QPushButton('选择解码器 (.onnx)')
        btn_dec.clicked.connect(self._browse_decoder)
        dec_layout.addWidget(self.decoder_label, 1)
        dec_layout.addWidget(btn_dec)
        model_layout.addLayout(dec_layout)

        layout.addWidget(model_group)

        help_group = QGroupBox('使用说明')
        help_layout = QVBoxLayout(help_group)
        help_text = QLabel(
            '1. 加载模型后，点击"嵌入当前图片"提取特征\n'
            '2. 在图片上点击目标位置，自动生成分割框\n'
            '3. 按住 Ctrl 点击可添加正样本点（精细调整）\n'
            '4. 按住 Alt 点击可添加负样本点（排除区域）')
        help_text.setWordWrap(True)
        help_layout.addWidget(help_text)
        layout.addWidget(help_group)

        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.btn_embed = QPushButton('嵌入当前图片')
        self.btn_embed.setEnabled(False)
        self.btn_embed.clicked.connect(self._embed_image)
        btn_layout.addWidget(self.btn_embed)
        self.btn_cancel = QPushButton('关闭')
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _browse_encoder(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '选择 SAM 编码器', '', 'ONNX Files (*.onnx)')
        if path:
            self.encoder_label.setText(path)
            self.encoder_label.setStyleSheet('color: #333333;')
            self._try_load()

    def _browse_decoder(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '选择 SAM 解码器', '', 'ONNX Files (*.onnx)')
        if path:
            self.decoder_label.setText(path)
            self.decoder_label.setStyleSheet('color: #333333;')
            self._try_load()

    def _try_load(self):
        enc_path = self.encoder_label.text()
        dec_path = self.decoder_label.text()
        if '未选择' in enc_path or '未选择' in dec_path:
            return
        if not os.path.isfile(enc_path) or not os.path.isfile(dec_path):
            return
        try:
            from libs.sam_predictor import SAMOnnxPredictor
            self.predictor = SAMOnnxPredictor(enc_path, dec_path)
            self.predictor.load_model()
            self.btn_embed.setEnabled(True)
            self.status_label.setText('模型加载成功')
        except Exception as e:
            self.status_label.setText(f'模型加载失败: {e}')
            self.predictor = None

    def _embed_image(self):
        if not self.predictor:
            return
        if not self.main_window.file_path:
            QMessageBox.warning(self, '提示', '请先打开一张图片')
            return
        self.status_label.setText('正在嵌入图片特征...')
        QApplication.processEvents()
        try:
            from PIL import Image
            import numpy as np
            img = Image.open(self.main_window.file_path).convert('RGB')
            img_rgb = np.array(img)
            self.predictor.set_image(img_rgb)
            self.status_label.setText('嵌入完成！在图片上点击目标即可生成标注框')
            self.main_window._sam_predictor = self.predictor
            self.main_window._sam_mode = True
        except Exception as e:
            self.status_label.setText(f'嵌入失败: {e}')


from PyQt5.QtWidgets import QApplication
