try:
    from PyQt5.QtGui import QColor, QPalette
except ImportError:
    from PyQt4.QtGui import QColor, QPalette


THEMES = {
    "Apple Pro": {
        "bg_color": "#18191b",
        "fg_color": "#f5f5f7",
        "primary": "#0a84ff",
        "primary_hover": "#409cff",
        "primary_pressed": "#0071e3",
        "panel_bg": "#242529",
        "border": "#3a3b40",
        "hover_bg": "#303136",
        "selected_bg": "#0a84ff",
        "selected_fg": "#ffffff",
        "canvas_verified": "#15271d",
        "canvas_bg": "#111214",
        "canvas_grid": "#202124",
    },
    "Cursor Dark": {
        "bg_color": "#1e1e1e",
        "fg_color": "#cccccc",
        "primary": "#0e639c",
        "primary_hover": "#1177bb",
        "primary_pressed": "#094771",
        "panel_bg": "#252526",
        "border": "#3c3c3c",
        "hover_bg": "#424242",
        "selected_bg": "#37373d",
        "selected_fg": "#ffffff",
        "canvas_verified": "#1e342d",
        "canvas_bg": "#121212",
        "canvas_grid": "#1e1e1e",
    },
    "Notion Light": {
        "bg_color": "#ffffff",
        "fg_color": "#37352f",
        "primary": "#2383e2",
        "primary_hover": "#1b6cb8",
        "primary_pressed": "#14518a",
        "panel_bg": "#f7f7f5",
        "border": "#e9e9e7",
        "hover_bg": "#efefe9",
        "selected_bg": "#e6f3ff",
        "selected_fg": "#2383e2",
        "canvas_verified": "#eaf5ea",
        "canvas_bg": "#f9f9f8",
        "canvas_grid": "#e9e9e7",
    },
    "Stripe Light": {
        "bg_color": "#f6f9fc",
        "fg_color": "#1a1f36",
        "primary": "#635bff",
        "primary_hover": "#726aff",
        "primary_pressed": "#4f45e0",
        "panel_bg": "#ffffff",
        "border": "#d3deeb",
        "hover_bg": "#f3f8ff",
        "selected_bg": "#e3efff",
        "selected_fg": "#154f93",
        "canvas_verified": "#e6f6ee",
        "canvas_bg": "#eef2f7",
        "canvas_grid": "#d9e2ef",
    },
    "Raycast Dark": {
        "bg_color": "#0b0f17",
        "fg_color": "#e7ecf5",
        "primary": "#ff6363",
        "primary_hover": "#ff8585",
        "primary_pressed": "#e55959",
        "panel_bg": "#111a28",
        "border": "#27374b",
        "hover_bg": "#1a2940",
        "selected_bg": "#233a58",
        "selected_fg": "#ffffff",
        "canvas_verified": "#122a1f",
        "canvas_bg": "#05070a",
        "canvas_grid": "#0b0f17",
    },
}

_THEME_EXTRAS = {
    "Apple Pro": {
        "field_bg": "#2c2d31",
        "field_fg": "#f5f5f7",
        "placeholder": "#8e8e93",
        "muted": "#a1a1a6",
        "tooltip_bg": "#34353a",
        "tooltip_fg": "#ffffff",
        "status_bg": "#202124",
    },
    "Cursor Dark": {
        "field_bg": "#303033",
        "field_fg": "#f2f2f2",
        "placeholder": "#a8a8a8",
        "muted": "#b8b8b8",
        "tooltip_bg": "#3b3b3d",
        "tooltip_fg": "#ffffff",
        "status_bg": "#252526",
    },
    "Notion Light": {
        "field_bg": "#ffffff",
        "field_fg": "#25241f",
        "placeholder": "#77746d",
        "muted": "#6f6d67",
        "tooltip_bg": "#25241f",
        "tooltip_fg": "#ffffff",
        "status_bg": "#f1f1ef",
    },
    "Stripe Light": {
        "field_bg": "#ffffff",
        "field_fg": "#1a1f36",
        "placeholder": "#697386",
        "muted": "#596780",
        "tooltip_bg": "#1a1f36",
        "tooltip_fg": "#ffffff",
        "status_bg": "#eef3f8",
    },
    "Raycast Dark": {
        "field_bg": "#172233",
        "field_fg": "#f4f7fb",
        "placeholder": "#91a1b8",
        "muted": "#aab6c7",
        "tooltip_bg": "#27374b",
        "tooltip_fg": "#ffffff",
        "status_bg": "#111a28",
    },
}

CURRENT_THEME = "Apple Pro"


def _theme_tokens(theme_name):
    base = THEMES.get(theme_name, THEMES[CURRENT_THEME]).copy()
    base.update(_THEME_EXTRAS.get(theme_name, _THEME_EXTRAS[CURRENT_THEME]))
    return base


def apply_theme(app, theme_name=CURRENT_THEME):
    global CURRENT_THEME

    if theme_name not in THEMES:
        theme_name = CURRENT_THEME
    CURRENT_THEME = theme_name
    t = _theme_tokens(theme_name)

    qss = f"""
    * {{
        font-family: "Segoe UI Variable", "Microsoft YaHei UI";
        font-size: 13px;
        color: {t['fg_color']};
    }}

    QMainWindow, QDialog {{
        background-color: {t['bg_color']};
    }}

    QWidget {{
        color: {t['fg_color']};
    }}

    QWidget#DirContainer {{
        background-color: {t['panel_bg']};
        border-bottom: 1px solid {t['border']};
    }}

    QWidget#CanvasHeader,
    QWidget#TimelineBar,
    QWidget#InspectorPanel,
    QWidget#DockPanel {{
        background-color: {t['panel_bg']};
    }}

    QWidget#DockPanel QStackedWidget,
    QWidget#DockPanel QStackedWidget > QWidget,
    QWidget#DockPanel QLabel,
    QWidget#DockPanel QCheckBox {{
        background-color: transparent;
    }}

    QLabel#SectionTitle {{
        color: {t['selected_fg']};
        font-size: 17px;
        font-weight: 600;
    }}

    QLabel#MutedLabel,
    QLabel#CanvasMeta,
    QLabel#ShortcutHint {{
        color: {t['muted']};
    }}

    QLabel#SaveStatus {{
        color: #30d158;
        font-weight: 600;
    }}

    QWidget#ImageDirRow,
    QWidget#AnnotationDirRow {{
        border: 1px solid {t['border']};
        border-radius: 8px;
        background-color: {t['bg_color']};
    }}

    QWidget#ImageDirRow {{
        border-left: 3px solid #0a84ff;
    }}

    QWidget#AnnotationDirRow {{
        border-left: 3px solid #30d158;
    }}

    QLabel#ImageDirLabel,
    QLabel#AnnotationDirLabel {{
        background: transparent;
        padding: 0;
        font-weight: 600;
    }}

    QLabel#ImageDirBadge,
    QLabel#AnnotationDirBadge {{
        min-width: 54px;
        border-radius: 5px;
        padding: 2px 5px;
        font-weight: 600;
        font-size: 11px;
    }}

    QLabel#ImageDirBadge {{
        background-color: rgba(10, 132, 255, 38);
        color: #70b7ff;
    }}

    QLabel#AnnotationDirBadge {{
        background-color: rgba(48, 209, 88, 34);
        color: #65df88;
    }}

    QLabel#DailyTotalLabel {{
        border: 1px solid {t['border']};
        border-radius: 8px;
        background-color: {t['bg_color']};
        padding: 6px 10px;
        font-weight: 600;
    }}

    QMenuBar {{
        background-color: {t['panel_bg']};
        border-bottom: 1px solid {t['border']};
    }}

    QMenuBar::item {{
        color: {t['fg_color']};
        padding: 6px 10px;
        background: transparent;
    }}

    QMenuBar::item:selected {{
        background-color: {t['hover_bg']};
        color: {t['selected_fg']};
    }}

    QMenu {{
        background-color: {t['panel_bg']};
        color: {t['fg_color']};
        border: 1px solid {t['border']};
        padding: 4px 0px;
    }}

    QMenu::item {{
        padding: 6px 24px;
    }}

    QMenu::item:disabled {{
        color: {t['placeholder']};
    }}

    QMenu::item:selected {{
        background-color: {t['primary']};
        color: #ffffff;
    }}

    QToolBar {{
        background-color: {t['panel_bg']};
        border: none;
        border-bottom: 1px solid {t['border']};
        spacing: 3px;
        padding: 7px 10px;
    }}

    QToolButton {{
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 6px 9px;
        color: {t['fg_color']};
    }}

    QToolButton:hover {{
        background-color: {t['hover_bg']};
        color: {t['selected_fg']};
    }}

    QToolButton:pressed {{
        background-color: {t['selected_bg']};
    }}

    QToolButton:checked {{
        background-color: {t['selected_bg']};
        border: 1px solid {t['primary']};
    }}

    QDockWidget {{
        border: none;
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
    }}

    QDockWidget::title {{
        background-color: {t['panel_bg']};
        padding: 10px 12px;
        color: {t['fg_color']};
        font-weight: 600;
    }}

    QGroupBox {{
        border: 1px solid {t['border']};
        border-radius: 4px;
        margin-top: 10px;
        padding: 12px 10px 10px 10px;
        background-color: {t['panel_bg']};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 0 4px;
        color: {t['selected_fg']};
        font-weight: 600;
        background-color: {t['panel_bg']};
    }}

    QListWidget {{
        background-color: transparent;
        border: none;
        outline: none;
    }}

    QListWidget::viewport {{
        background-color: transparent;
    }}

    QListWidget#FileList::item {{
        color: {t['fg_color']};
        padding: 9px 10px;
        margin: 2px 4px;
        border-radius: 8px;
    }}

    QListWidget#FileList::item:hover {{
        background-color: {t['hover_bg']};
    }}

    QListWidget#FileList::item:selected {{
        background-color: {t['selected_bg']};
        color: {t['selected_fg']};
    }}

    QListWidget#LabelList::item {{
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 8px 10px;
        margin: 3px 0px;
        font-weight: 600;
        background-color: transparent;
    }}

    QListWidget#LabelList::item:hover {{
        border: 1px solid {t['primary_hover']};
        background-color: {t['hover_bg']};
    }}

    QListWidget#LabelList::item:selected {{
        border: 1px solid {t['primary']};
        background-color: {t['selected_bg']};
        color: {t['selected_fg']};
    }}

    QLabel#StatusLogo {{
        padding: 2px 6px;
        background-color: transparent;
    }}

    QLineEdit,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QTextEdit,
    QPlainTextEdit {{
        border: 1px solid {t['border']};
        border-radius: 8px;
        background-color: {t['field_bg']};
        color: {t['field_fg']};
        padding: 7px 9px;
        selection-background-color: {t['primary']};
        selection-color: #ffffff;
    }}

    QLineEdit:focus,
    QComboBox:focus {{
        border: 1px solid {t['primary']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {t['field_bg']};
        color: {t['field_fg']};
        border: 1px solid {t['border']};
        outline: none;
        selection-background-color: {t['primary']};
        selection-color: #ffffff;
    }}

    QToolTip {{
        color: {t['tooltip_fg']};
        background-color: {t['tooltip_bg']};
        border: 1px solid {t['border']};
        border-radius: 5px;
        padding: 6px 8px;
    }}

    QPushButton {{
        background-color: {t['field_bg']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        color: {t['fg_color']};
        padding: 7px 12px;
    }}

    QPushButton:hover {{
        background-color: {t['hover_bg']};
    }}

    QPushButton:pressed {{
        background-color: {t['selected_bg']};
    }}

    QPushButton:disabled,
    QToolButton:disabled,
    QLineEdit:disabled,
    QComboBox:disabled,
    QSpinBox:disabled {{
        color: {t['placeholder']};
        background-color: {t['panel_bg']};
        border-color: {t['border']};
    }}

    QPushButton#PrimaryActionButton {{
        background-color: {t['primary']};
        color: #ffffff;
        border: none;
    }}

    QPushButton#PrimaryActionButton:hover {{
        background-color: {t['primary_hover']};
    }}

    QPushButton#PrimaryActionButton:pressed {{
        background-color: {t['primary_pressed']};
    }}

    QCheckBox {{
        spacing: 6px;
        color: {t['fg_color']};
    }}

    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {t['border']};
        border-radius: 2px;
        background-color: {t['bg_color']};
    }}

    QCheckBox::indicator:hover {{
        border: 1px solid {t['primary']};
    }}

    QCheckBox::indicator:checked {{
        border: 1px solid {t['primary']};
        background-color: {t['primary']};
    }}

    QProgressBar {{
        border: 1px solid {t['border']};
        background-color: {t['panel_bg']};
        text-align: center;
        color: {t['fg_color']};
    }}

    QProgressBar::chunk {{
        background-color: {t['primary']};
    }}

    QStatusBar {{
        background-color: {t['status_bg']};
        color: {t['muted']};
        border-top: 1px solid {t['border']};
    }}

    QStatusBar QLabel {{
        color: {t['muted']};
    }}

    QScrollBar:vertical, QScrollBar:horizontal {{
        border: none;
        background-color: {t['bg_color']};
        width: 8px;
        height: 8px;
        margin: 0;
    }}

    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background-color: {t['hover_bg']};
        border-radius: 4px;
        min-height: 20px;
        min-width: 20px;
    }}

    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
        background-color: {t['border']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
        height: 0;
    }}

    QFrame#InspectorSeparator {{
        border: none;
        border-top: 1px solid {t['border']};
        background-color: transparent;
        max-height: 1px;
    }}

    QSplitter::handle {{
        background-color: {t['border']};
    }}

    QSlider::groove:horizontal {{
        height: 4px;
        background: {t['border']};
        border-radius: 2px;
    }}

    QSlider::sub-page:horizontal {{
        background: {t['primary']};
        border-radius: 2px;
    }}

    QSlider::handle:horizontal {{
        background: #ffffff;
        border: 2px solid {t['primary']};
        width: 14px;
        margin: -6px 0;
        border-radius: 7px;
    }}

    QToolButton#InspectorTab {{
        background-color: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        border-radius: 0;
        color: {t['muted']};
        padding: 8px 10px;
        font-weight: 600;
    }}

    QToolButton#InspectorTab:hover {{
        color: {t['fg_color']};
        background-color: transparent;
    }}

    QToolButton#InspectorTab:checked {{
        color: {t['fg_color']};
        border-bottom-color: {t['primary']};
        background-color: transparent;
    }}

    QPushButton#RouteTargetButton {{
        text-align: left;
        padding: 9px 10px;
        border: 1px solid {t['border']};
        border-radius: 8px;
        background-color: transparent;
        color: {t['fg_color']};
        font-weight: 600;
    }}

    QPushButton#RouteTargetButton:hover,
    QPushButton#RouteTargetButton[dragActive="true"] {{
        border: 1px solid {t['primary']};
        background-color: {t['hover_bg']};
        color: {t['selected_fg']};
    }}
    """

    app.setStyleSheet(qss)

    palette = app.palette()
    palette.setColor(QPalette.Window, QColor(t["bg_color"]))
    palette.setColor(QPalette.WindowText, QColor(t["fg_color"]))
    palette.setColor(QPalette.Base, QColor(t["field_bg"]))
    palette.setColor(QPalette.Text, QColor(t["field_fg"]))
    palette.setColor(QPalette.Button, QColor(t["field_bg"]))
    palette.setColor(QPalette.ButtonText, QColor(t["field_fg"]))
    palette.setColor(QPalette.Highlight, QColor(t["primary"]))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipBase, QColor(t["tooltip_bg"]))
    palette.setColor(QPalette.ToolTipText, QColor(t["tooltip_fg"]))
    if hasattr(QPalette, "PlaceholderText"):
        palette.setColor(QPalette.PlaceholderText, QColor(t["placeholder"]))
    app.setPalette(palette)
