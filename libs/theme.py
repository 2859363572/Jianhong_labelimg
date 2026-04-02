# libs/theme.py

def apply_theme(app):
    qss = """
    /* Global Font and Background */
    * {
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-size: 13px;
        color: #333333;
    }
    
    QMainWindow, QDialog, QWidget {
        background-color: #F8F9FA;
    }

    /* Top Status Bar (Directory labels) */
    QWidget#DirContainer {
        background-color: #FFFFFF;
        border-bottom: 2px solid #E0E0E0;
    }
    QLabel#ImageDirLabel {
        color: #1976D2;
        background-color: #E3F2FD;
        border: 1px solid #BBDEFB;
        border-radius: 6px;
        padding: 6px 12px;
        font-weight: bold;
    }
    QLabel#AnnotationDirLabel {
        color: #388E3C;
        background-color: #E8F5E9;
        border: 1px solid #C8E6C9;
        border-radius: 6px;
        padding: 6px 12px;
        font-weight: bold;
    }
    QLabel#DailyTotalLabel {
        color: #D32F2F;
        background-color: #FFEBEE;
        border: 1px solid #FFCDD2;
        border-radius: 6px;
        padding: 6px 12px;
        font-weight: bold;
    }

    /* Menus and Menu Bar */
    QMenuBar {
        background-color: #FFFFFF;
        border-bottom: 1px solid #E0E0E0;
    }
    QMenuBar::item {
        background-color: transparent;
        padding: 6px 12px;
    }
    QMenuBar::item:selected {
        background-color: #E3F2FD;
        color: #1976D2;
        border-radius: 4px;
    }
    QMenu {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 4px;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 24px;
        border-radius: 4px;
    }
    QMenu::item:selected {
        background-color: #1976D2;
        color: white;
    }

    /* ToolBar */
    QToolBar {
        background-color: #FFFFFF;
        border: none;
        border-right: 1px solid #E0E0E0;
        border-bottom: 1px solid #E0E0E0;
        spacing: 8px;
        padding: 8px;
    }
    QToolButton {
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 6px;
        color: #555555;
        font-weight: bold;
    }
    QToolButton:hover {
        background-color: #E3F2FD;
        border: 1px solid #90CAF9;
        color: #1976D2;
    }
    QToolButton:pressed {
        background-color: #BBDEFB;
        border: 1px solid #42A5F5;
    }
    QToolButton:checked {
        background-color: #E3F2FD;
        border: 1px solid #2196F3;
        color: #1565C0;
    }

    /* Dock Widgets */
    QDockWidget {
        border: 1px solid #E0E0E0;
        font-weight: bold;
        color: #333333;
    }
    QDockWidget::title {
        background-color: #F5F5F5;
        padding: 8px;
        border-bottom: 1px solid #E0E0E0;
        color: #424242;
    }

    /* List Widgets */
    QListWidget {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 6px;
        outline: 0;
    }
    QListWidget::item {
        padding: 8px;
        border-radius: 4px;
        margin: 2px;
        border: 1px solid transparent;
        color: #424242;
    }
    QListWidget::item:hover {
        background-color: #F5F5F5;
        border: 1px solid #90CAF9;
        color: #1976D2;
    }
    QListWidget::item:selected {
        background-color: #E3F2FD;
        color: #0D47A1;
        border: 1px solid #2196F3;
        font-weight: bold;
    }

    /* Status Bar */
    QStatusBar {
        background-color: #F5F5F5;
        color: #424242;
        border-top: 1px solid #E0E0E0;
    }
    QStatusBar QLabel {
        color: #424242;
    }

    /* Stats Dialog */
    QLabel#StatsHeader {
        font-size: 16px;
        font-weight: bold;
        color: #1976D2;
        margin-bottom: 10px;
    }
    QLabel#StatsInfo {
        color: #757575;
        font-size: 12px;
        margin-bottom: 10px;
    }
    QLabel#StatsTotal {
        font-size: 14px;
        font-weight: bold;
        color: #D32F2F;
        margin-top: 10px;
    }

    /* ScrollBars */
    QScrollBar:vertical {
        border: none;
        background-color: #F5F5F5;
        width: 10px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background-color: #BDBDBD;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: #9E9E9E;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar:horizontal {
        border: none;
        background-color: #F5F5F5;
        height: 10px;
        margin: 0px;
    }
    QScrollBar::handle:horizontal {
        background-color: #BDBDBD;
        min-width: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal:hover {
        background-color: #9E9E9E;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }

    /* Buttons */
    QPushButton {
        background-color: #2196F3;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #42A5F5;
        border: 1px solid #64B5F6;
    }
    QPushButton:pressed {
        background-color: #1565C0;
        border: 1px solid #0D47A1;
    }
    QPushButton:disabled {
        background-color: #E0E0E0;
        color: #9E9E9E;
    }

    /* CheckBox */
    QCheckBox {
        spacing: 8px;
        font-size: 13px;
        color: #333333;
        padding: 2px 0px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 2px solid #BDBDBD;
        border-radius: 3px;
        background-color: #FFFFFF;
    }
    QCheckBox::indicator:hover {
        border: 2px solid #42A5F5;
        background-color: #F5F5F5;
    }
    QCheckBox::indicator:checked {
        border: 2px solid #1976D2;
        background-color: #1976D2;
    }
    QCheckBox::indicator:checked:hover {
        border: 2px solid #1565C0;
        background-color: #1565C0;
    }

    /* Inputs */
    QLineEdit, QComboBox {
        background-color: #FFFFFF;
        border: 1px solid #BDBDBD;
        border-radius: 4px;
        padding: 6px 10px;
        color: #333333;
    }
    QLineEdit:focus, QComboBox:focus {
        border: 2px solid #64B5F6;
        background-color: #FAFAFA;
    }
    QComboBox::drop-down {
        border: none;
        width: 24px;
    }
    
    /* Table Widgets */
    QTableWidget, QTableView {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 4px;
        gridline-color: #E0E0E0;
        alternate-background-color: #FAFAFA;
        color: #333333;
    }
    QTableWidget::item {
        padding: 4px;
    }
    QTableWidget::item:selected {
        background-color: #E3F2FD;
        color: #0D47A1;
        font-weight: bold;
    }
    QHeaderView::section {
        background-color: #F5F5F5;
        color: #1976D2;
        padding: 6px;
        border: 1px solid #E0E0E0;
        font-weight: bold;
    }
    """
    app.setStyleSheet(qss)
