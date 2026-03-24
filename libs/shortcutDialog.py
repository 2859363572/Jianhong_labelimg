
try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

class ShortcutDialog(QDialog):
    def __init__(self, actions, parent=None):
        super(ShortcutDialog, self).__init__(parent)
        self.setWindowTitle("自定义快捷键")
        self.setMinimumWidth(400)
        self.actions = actions
        self.new_shortcuts = {}

        layout = QVBoxLayout()
        
        # 说明
        info_label = QLabel("点击输入框并按下快捷键进行修改。留空表示清除快捷键。")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.grid_layout = QGridLayout(content_widget)
        
        # 排除一些不建议修改的动作
        exclude_actions = ['zoom', 'zoomActions', 'fileMenuActions', 'beginner', 'advanced', 
                           'editMenu', 'beginnerContext', 'advancedContext', 'onLoadActive', 'onShapesPresent']
        
        row = 0
        for name, action in self.actions.__dict__.items():
            if name in exclude_actions or not isinstance(action, QAction):
                continue
            
            label = QLabel(action.text().replace('&', ''))
            line_edit = ShortcutLineEdit(action.shortcut().toString())
            line_edit.setObjectName(name)
            
            self.grid_layout.addWidget(label, row, 0)
            self.grid_layout.addWidget(line_edit, row, 1)
            row += 1

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Reset)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self.reset_shortcuts)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def reset_shortcuts(self):
        # 逻辑由外部处理，这里只是发信号或清空
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if isinstance(widget, ShortcutLineEdit):
                widget.clear()

    def get_shortcuts(self):
        shortcuts = {}
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if isinstance(widget, ShortcutLineEdit):
                name = widget.objectName()
                shortcuts[name] = widget.text()
        return shortcuts

class ShortcutLineEdit(QLineEdit):
    def __init__(self, text="", parent=None):
        super(ShortcutLineEdit, self).__init__(text, parent)
        self.setReadOnly(True)
        self.setPlaceholderText("按下快捷键...")

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Backspace or key == Qt.Key_Delete:
            self.clear()
            return

        modifiers = event.modifiers()
        key_sequence = []

        if modifiers & Qt.ControlModifier:
            key_sequence.append("Ctrl")
        if modifiers & Qt.ShiftModifier:
            key_sequence.append("Shift")
        if modifiers & Qt.AltModifier:
            key_sequence.append("Alt")
        if modifiers & Qt.MetaModifier:
            key_sequence.append("Meta")

        # 排除单纯的修饰键
        if key not in [Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta]:
            key_text = QKeySequence(key).toString()
            if key_text:
                key_sequence.append(key_text)
                self.setText("+".join(key_sequence))

    def mousePressEvent(self, event):
        self.selectAll()
        super(ShortcutLineEdit, self).mousePressEvent(event)
