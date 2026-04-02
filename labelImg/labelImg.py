#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import codecs
import distutils.spawn
import os.path
import platform
import re
import sys
import subprocess
import shutil
import webbrowser as wb

from functools import partial
from collections import defaultdict

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    # needed for py3+qt4
    # Ref:
    # http://pyqt.sourceforge.net/Docs/PyQt4/incompatible_apis.html
    # http://stackoverflow.com/questions/21217399/pyqt4-qtcore-qvariant-object-instead-of-a-string
    if sys.version_info.major >= 3:
        import sip
        sip.setapi('QVariant', 2)
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

from libs.combobox import ComboBox
from libs.resources import *
from libs.constants import *
from libs.utils import *
from libs.settings import Settings
from libs.shape import Shape, DEFAULT_LINE_COLOR, DEFAULT_FILL_COLOR
from libs.stringBundle import StringBundle
from libs.canvas import Canvas
from libs.zoomWidget import ZoomWidget
from libs.labelDialog import LabelDialog
from libs.colorDialog import ColorDialog
from libs.shortcutDialog import ShortcutDialog
from libs.statsDialog import StatisticsDialog
from libs.labelFile import LabelFile, LabelFileError, LabelFileFormat
from libs.toolBar import ToolBar
from libs.pascal_voc_io import PascalVocReader
from libs.pascal_voc_io import XML_EXT
from libs.yolo_io import YoloReader
from libs.yolo_io import TXT_EXT
from libs.create_ml_io import CreateMLReader
from libs.create_ml_io import JSON_EXT
from libs.ustr import ustr
from libs.hashableQListWidgetItem import HashableQListWidgetItem
from libs.theme import apply_theme

__appname__ = 'labelImg'


class WindowMixin(object):

    def menu(self, title, actions=None):
        menu = self.menuBar().addMenu(title)
        if actions:
            add_actions(menu, actions)
        return menu

    def toolbar(self, title, actions=None):
        toolbar = ToolBar(title)
        toolbar.setObjectName(u'%sToolBar' % title)
        # toolbar.setOrientation(Qt.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if actions:
            add_actions(toolbar, actions)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        return toolbar


class ImagePreloader(QThread):
    imageLoaded = pyqtSignal(str, object)
    
    def __init__(self, image_paths):
        super().__init__()
        self.image_paths = image_paths
        self.current_index = 0
        
    def run(self):
        # 预加载当前图片的前后3张
        for i in range(max(0, self.current_index-1), 
                      min(len(self.image_paths), self.current_index+4)):
            if i != self.current_index:  # 当前图片已经加载
                pixmap = QPixmap(self.image_paths[i])
                self.imageLoaded.emit(self.image_paths[i], pixmap)

class MainWindow(QMainWindow, WindowMixin):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = list(range(3))

    def __init__(self, default_filename=None, default_prefdef_class_file=None, default_save_dir=None):
        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)

        # Load setting in the main thread
        self.settings = Settings()
        self.settings.load()
        settings = self.settings

        self.os_name = platform.system()

        # Load string bundle for i18n
        self.string_bundle = StringBundle.get_bundle()
        get_str = lambda str_id: self.string_bundle.get_string(str_id)

        # Save as Pascal voc xml
        self.default_save_dir = default_save_dir
        self.label_file_format = settings.get(SETTING_LABEL_FILE_FORMAT, LabelFileFormat.PASCAL_VOC)

        # For loading all image under a directory
        self.m_img_list = []
        self.dir_name = None
        self.label_hist = []
        self.last_open_dir = None
        self.cur_img_idx = 0
        self.img_count = 1
        
        # UI state for directory display
        self.image_dir_label = None
        self.annotation_dir_label = None

        # Whether we need to save or not.
        self.dirty = False

        self._no_selection_slot = False
        self._beginner = True
        self.screencast = "https://youtu.be/p0nR2YsCY_U"

        # Load predefined classes to the list
        self.load_predefined_classes(default_prefdef_class_file)

        # Main widgets and related state.
        self.label_dialog = LabelDialog(parent=self, list_item=self.label_hist)

        self.items_to_shapes = {}
        self.shapes_to_items = {}
        self.prev_label_text = ''
        
        # Application state.
        self.image = QImage()
        self.file_path = ustr(default_filename)
        self.last_open_dir = None
        self._pixmap_cache = {}
        self._sam_predictor = None
        self._sam_mode = False
        self.recent_files = []
        self.max_recent = 7
        self.line_color = None
        self.fill_color = None
        self.zoom_level = 100
        self.fit_window = False
        self.difficult = False
        
        # Undo stack for annotation operations (stores up to 3 snapshots)
        self.undo_stack = []
        self.max_undo = 10

        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(0, 0, 0, 0)

        # Create a widget for using default label
        self.use_default_label_checkbox = QCheckBox(get_str('useDefaultLabel'))
        self.use_default_label_checkbox.setChecked(False)
        self.default_label_text_line = QLineEdit()
        use_default_label_qhbox_layout = QHBoxLayout()
        use_default_label_qhbox_layout.addWidget(self.use_default_label_checkbox)
        use_default_label_qhbox_layout.addWidget(self.default_label_text_line)
        use_default_label_container = QWidget()
        use_default_label_container.setLayout(use_default_label_qhbox_layout)

        self.single_target_checkbox = QCheckBox('单目标模式')
        self.single_target_checkbox.setChecked(settings.get(SETTING_SINGLE_TARGET, False))
        self.fast_annotate_checkbox = QCheckBox('快速标注')
        self.fast_annotate_checkbox.setChecked(settings.get(SETTING_FAST_ANNOTATE, False))
        self.diffc_button = QCheckBox()
        self.diffc_button.setChecked(False)
        self.diffc_button.setVisible(False)
        self.edit_button = QToolButton()
        self.edit_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # Add some of widgets to list_layout
        list_layout.addWidget(self.edit_button)
        list_layout.addWidget(self.single_target_checkbox)
        list_layout.addWidget(self.fast_annotate_checkbox)
        list_layout.addWidget(use_default_label_container)

        # Create and add combobox for showing unique labels in group
        self.combo_box = ComboBox(self)
        list_layout.addWidget(self.combo_box)

        # Create and add a widget for showing current label items
        self.label_list = QListWidget()
        # 允许标签列表多选，支持批量复制
        self.label_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        label_list_container = QWidget()
        label_list_container.setLayout(list_layout)
        self.label_list.itemActivated.connect(self.label_selection_changed)
        self.label_list.itemSelectionChanged.connect(self.label_selection_changed)
        self.label_list.itemDoubleClicked.connect(self.edit_label)
        # Connect to itemChanged to detect checkbox changes.
        self.label_list.itemChanged.connect(self.label_item_changed)
        list_layout.addWidget(self.label_list)



        self.dock = QDockWidget(get_str('boxLabelText'), self)
        self.dock.setObjectName(get_str('labels'))
        self.dock.setWidget(label_list_container)

        self.file_list_widget = QListWidget()
        self.file_list_widget.itemDoubleClicked.connect(self.file_item_double_clicked)
        file_list_layout = QVBoxLayout()
        file_list_layout.setContentsMargins(0, 0, 0, 0)
        file_list_layout.addWidget(self.file_list_widget)
        file_list_container = QWidget()
        file_list_container.setLayout(file_list_layout)
        self.file_dock = QDockWidget(get_str('fileList'), self)
        self.file_dock.setObjectName(get_str('files'))
        self.file_dock.setWidget(file_list_container)

        self.zoom_widget = ZoomWidget()
        self.color_dialog = ColorDialog(parent=self)

        self.canvas = Canvas(parent=self)
        self.canvas.zoomRequest.connect(self.zoom_request)
        self.canvas.set_drawing_shape_to_square(settings.get(SETTING_DRAW_SQUARE, False))

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(True)
        self.scroll_bars = {
            Qt.Vertical: scroll.verticalScrollBar(),
            Qt.Horizontal: scroll.horizontalScrollBar()
        }
        self.scroll_area = scroll
        self.canvas.scrollRequest.connect(self.scroll_request)

        # Directory display
        self.image_dir_label = QLabel('图片目录: 未设置')
        self.image_dir_label.setObjectName("ImageDirLabel")
        self.image_dir_label.setAlignment(Qt.AlignCenter)
        
        self.annotation_dir_label = QLabel('保存目录: 未设置')
        self.annotation_dir_label.setObjectName("AnnotationDirLabel")
        self.annotation_dir_label.setAlignment(Qt.AlignCenter)
        
        self.daily_total_label = QLabel('今日总计数: 0')
        self.daily_total_label.setObjectName("DailyTotalLabel")
        self.daily_total_label.setAlignment(Qt.AlignCenter)
        
        dir_layout = QHBoxLayout()
        dir_layout.setContentsMargins(10, 10, 10, 10)
        dir_layout.setSpacing(15)
        dir_layout.addWidget(self.image_dir_label, 1)
        dir_layout.addWidget(self.annotation_dir_label, 1)
        dir_layout.addWidget(self.daily_total_label, 1)
        
        dir_container = QWidget()
        dir_container.setObjectName("DirContainer")
        dir_container.setLayout(dir_layout)

        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(dir_container)
        central_layout.addWidget(scroll)
        central_widget = QWidget()
        central_widget.setLayout(central_layout)

        self.canvas.newShape.connect(self.new_shape)
        self.canvas.shapeMoved.connect(self.set_dirty)
        self.canvas.selectionChanged.connect(self.shape_selection_changed)
        self.canvas.drawingPolygon.connect(self.toggle_drawing_sensitive)

        self.setCentralWidget(central_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.file_dock)
        self.file_dock.setFeatures(QDockWidget.DockWidgetFloatable)

        self.update_dir_labels()

        self.dock_features = QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable
        self.dock.setFeatures(self.dock.features() ^ self.dock_features)

        # Actions
        action = partial(new_action, self)
        quit = action(get_str('quit'), self.close,
                      'Ctrl+Q', 'quit', get_str('quitApp'))

        open = action(get_str('openFile'), self.open_file,
                      'Ctrl+O', 'open', get_str('openFileDetail'))

        open_dir = action(get_str('openDir'), self.open_dir_dialog,
                          'Ctrl+u', 'open', get_str('openDir'))

        change_save_dir = action(get_str('changeSaveDir'), self.change_save_dir_dialog,
                                 'Ctrl+r', 'open', get_str('changeSavedAnnotationDir'))

        open_annotation = action(get_str('openAnnotation'), self.open_annotation_dialog,
                                 'Ctrl+Shift+O', 'open', get_str('openAnnotationDetail'))
        copy_prev_bounding = action(get_str('copyPrevBounding'), self.copy_previous_bounding_boxes, 'Ctrl+v', 'copy', get_str('copyPrevBounding'))

        # 复制选中标签到后续帧（5/10/25）
        copy_next_5 = action('复制选中到下5帧', partial(self.copy_selected_labels_to_next_frames, 5),
                             'Alt+5', 'copy', '将选中标签复制到接下来5帧')
        copy_next_10 = action('复制选中到下10帧', partial(self.copy_selected_labels_to_next_frames, 10),
                              'Alt+0', 'copy', '将选中标签复制到接下来10帧')
        copy_next_25 = action('复制选中到下25帧', partial(self.copy_selected_labels_to_next_frames, 25),
                              'Alt+2', 'copy', '将选中标签复制到接下来25帧')
        copy_next_custom = action('自定义复制到下N帧', self.copy_selected_labels_custom,
                                  'Alt+C', 'copy', '自定义复制选中标签到后续N帧')
        smart_copy = action('智能复制相似帧', self.smart_copy_similar,
                            'Alt+S', 'copy', '自动检测相似帧并复制选中标注')

        open_next_image = action(get_str('nextImg'), self.open_next_image,
                                 'd', 'next', get_str('nextImgDetail'))

        open_prev_image = action(get_str('prevImg'), self.open_prev_image,
                                 'a', 'prev', get_str('prevImgDetail'))

        verify = action(get_str('verifyImg'), self.verify_image,
                        'space', 'verify', get_str('verifyImgDetail'))

        save = action(get_str('save'), self.save_file,
                      'Ctrl+S', 'save', get_str('saveDetail'), enabled=False)

        def get_format_meta(format):
            """
            returns a tuple containing (title, icon_name) of the selected format
            """
            if format == LabelFileFormat.PASCAL_VOC:
                return '&PascalVOC', 'format_voc'
            elif format == LabelFileFormat.YOLO:
                return '&YOLO', 'format_yolo'
            elif format == LabelFileFormat.CREATE_ML:
                return '&CreateML', 'format_createml'

        save_format = action(get_format_meta(self.label_file_format)[0],
                             self.change_format, 'Ctrl+',
                             get_format_meta(self.label_file_format)[1],
                             get_str('changeSaveFormat'), enabled=True)

        save_as = action(get_str('saveAs'), self.save_file_as,
                         'Ctrl+Shift+S', 'save-as', get_str('saveAsDetail'), enabled=False)

        close = action(get_str('closeCur'), self.close_file, 'Ctrl+W', 'close', get_str('closeCurDetail'))

        delete_image = action(get_str('deleteImg'), self.delete_image, 'Ctrl+Shift+D', 'close', get_str('deleteImgDetail'))

        reset_all = action(get_str('resetAll'), self.reset_all, None, 'resetall', get_str('resetAllDetail'))

        color1 = action(get_str('boxLineColor'), self.choose_color1,
                        'Ctrl+L', 'color_line', get_str('boxLineColorDetail'))

        create_mode = action(get_str('crtBox'), self.set_create_mode,
                             'w', 'new', get_str('crtBoxDetail'), enabled=False)
        edit_mode = action(get_str('editBox'), self.set_edit_mode,
                           'Ctrl+J', 'edit', get_str('editBoxDetail'), enabled=False)

        create = action(get_str('crtBox'), self.create_shape,
                        'w', 'new', get_str('crtBoxDetail'), enabled=False)
        delete = action(get_str('delBox'), self.delete_selected_shape,
                        'Delete', 'delete', get_str('delBoxDetail'), enabled=False)
        copy = action(get_str('dupBox'), self.copy_selected_shape,
                      'Ctrl+D', 'copy', get_str('dupBoxDetail'),
                      enabled=False)
        
        undo = action('撤回上一步', self.undo_last_operation,
                      'Ctrl+Z', 'undo', '撤回最近一次操作（最多3步）', enabled=True)

        # Bind additional shortcut 'F' to delete (supports multi-select)
        QShortcut(QKeySequence('F'), self, activated=self.delete_selected_shapes)

        advanced_mode = action(get_str('advancedMode'), self.toggle_advanced_mode,
                               'Ctrl+Shift+A', 'expert', get_str('advancedModeDetail'),
                               checkable=True)

        hide_all = action(get_str('hideAllBox'), partial(self.toggle_polygons, False),
                          'Ctrl+H', 'hide', get_str('hideAllBoxDetail'),
                          enabled=False)
        show_all = action(get_str('showAllBox'), partial(self.toggle_polygons, True),
                          'Ctrl+A', 'hide', get_str('showAllBoxDetail'),
                          enabled=False)

        help_default = action(get_str('tutorialDefault'), self.show_default_tutorial_dialog, None, 'help', get_str('tutorialDetail'))
        show_info = action(get_str('info'), self.show_info_dialog, None, 'help', get_str('info'))
        show_shortcut = action(get_str('shortcut'), self.show_shortcuts_dialog, None, 'help', get_str('shortcut'))
        custom_shortcut = action("自定义快捷键", self.show_custom_shortcuts_dialog, None, 'help', "配置自定义快捷键")
        show_stats = action("查看每日统计", self.show_daily_stats_dialog, None, 'help', "查看今日打开图片的统计明细")

        zoom = QWidgetAction(self)
        zoom.setDefaultWidget(self.zoom_widget)
        self.zoom_widget.setWhatsThis(
            u"Zoom in or out of the image. Also accessible with"
            " %s and %s from the canvas." % (format_shortcut("Ctrl+[-+]"),
                                             format_shortcut("Ctrl+Wheel")))
        self.zoom_widget.setEnabled(False)

        zoom_in = action(get_str('zoomin'), partial(self.add_zoom, 10),
                         'Ctrl++', 'zoom-in', get_str('zoominDetail'), enabled=False)
        zoom_out = action(get_str('zoomout'), partial(self.add_zoom, -10),
                          'Ctrl+-', 'zoom-out', get_str('zoomoutDetail'), enabled=False)
        zoom_org = action(get_str('originalsize'), partial(self.set_zoom, 100),
                          'Ctrl+=', 'zoom', get_str('originalsizeDetail'), enabled=False)
        fit_window = action(get_str('fitWin'), self.set_fit_window,
                            'Ctrl+F', 'fit-window', get_str('fitWinDetail'),
                            checkable=True, enabled=False)
        fit_width = action(get_str('fitWidth'), self.set_fit_width,
                           'Ctrl+Shift+F', 'fit-width', get_str('fitWidthDetail'),
                           checkable=True, enabled=False)
        # Group zoom controls into a list for easier toggling.
        zoom_actions = (self.zoom_widget, zoom_in, zoom_out,
                        zoom_org, fit_window, fit_width)
        self.zoom_mode = self.MANUAL_ZOOM
        self.scalers = {
            self.FIT_WINDOW: self.scale_fit_window,
            self.FIT_WIDTH: self.scale_fit_width,
            # Set to one to scale to 100% when loading files.
            self.MANUAL_ZOOM: lambda: 1,
        }

        edit = action(get_str('editLabel'), self.edit_label,
                      'Ctrl+E', 'edit', get_str('editLabelDetail'),
                      enabled=False)
        self.edit_button.setDefaultAction(edit)

        shape_line_color = action(get_str('shapeLineColor'), self.choose_shape_line_color,
                                  icon='color_line', tip=get_str('shapeLineColorDetail'),
                                  enabled=False)
        shape_fill_color = action(get_str('shapeFillColor'), self.choose_shape_fill_color,
                                  icon='color', tip=get_str('shapeFillColorDetail'),
                                  enabled=False)

        labels = self.dock.toggleViewAction()
        labels.setText(get_str('showHide'))
        labels.setShortcut('Ctrl+Shift+L')

        # Label list context menu.
        label_menu = QMenu()
        add_actions(label_menu, (edit, delete))
        self.label_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.label_list.customContextMenuRequested.connect(
            self.pop_label_list_menu)

        # Draw squares/rectangles
        self.draw_squares_option = QAction(get_str('drawSquares'), self)
        self.draw_squares_option.setShortcut('Ctrl+Shift+R')
        self.draw_squares_option.setCheckable(True)
        self.draw_squares_option.setChecked(settings.get(SETTING_DRAW_SQUARE, False))
        self.draw_squares_option.triggered.connect(self.toggle_draw_square)

        # Store actions for further handling.
        self.actions = Struct(save=save, save_format=save_format, saveAs=save_as, open=open, close=close, resetAll=reset_all, deleteImg=delete_image,
                              lineColor=color1, create=create, delete=delete, edit=edit, copy=copy,
                              createMode=create_mode, editMode=edit_mode, advancedMode=advanced_mode,
                              shapeLineColor=shape_line_color, shapeFillColor=shape_fill_color,
                              zoom=zoom, zoomIn=zoom_in, zoomOut=zoom_out, zoomOrg=zoom_org,
                              fitWindow=fit_window, fitWidth=fit_width,
                              zoomActions=zoom_actions,
                              fileMenuActions=(
                                  open, open_dir, save, save_as, close, reset_all, quit),
                              beginner=(), advanced=(),
                              editMenu=(edit, copy, delete,
                                        None, color1, self.draw_squares_option),
                              beginnerContext=(create, edit, copy, delete, undo),
                              advancedContext=(create_mode, edit_mode, edit, copy,
                                               delete, shape_line_color, shape_fill_color, undo),
                              onLoadActive=(
                                  close, create, create_mode, edit_mode),
                              onShapesPresent=(save_as, hide_all, show_all))

        # 将复制到后续帧的动作加入 actions，便于统一管理
        self.actions.copyNext5 = copy_next_5
        self.actions.copyNext10 = copy_next_10
        self.actions.copyNext25 = copy_next_25
        self.actions.copyNextCustom = copy_next_custom
        self.actions.undo = undo
        # 扩展编辑菜单，加入批量复制功能
        self.actions.editMenu = (
            edit, copy, delete, undo,
            None, color1, self.draw_squares_option,
            None, copy_next_5, copy_next_10, copy_next_25, copy_next_custom,
            None, smart_copy
        )

        self.menus = Struct(
            file=self.menu(get_str('menu_file')),
            edit=self.menu(get_str('menu_edit')),
            view=self.menu(get_str('menu_view')),
            help=self.menu(get_str('menu_help')),
            recentFiles=QMenu(get_str('menu_openRecent')),
            labelList=label_menu)

        # Auto saving : Enable auto saving if pressing next
        self.auto_saving = QAction(get_str('autoSaveMode'), self)
        self.auto_saving.setCheckable(True)
        self.auto_saving.setChecked(settings.get(SETTING_AUTO_SAVE, False))
        # Auto save all operations: save on any modification without confirm
        self.auto_save_all = QAction('自动保存所有操作', self)
        self.auto_save_all.setCheckable(True)
        self.auto_save_all.setChecked(settings.get(SETTING_AUTO_SAVE_ALL, False))
        # Sync single class mode from PR#106
        self.single_class_mode = QAction(get_str('singleClsMode'), self)
        self.single_class_mode.setShortcut("Ctrl+Shift+S")
        self.single_class_mode.setCheckable(True)
        self.single_class_mode.setChecked(settings.get(SETTING_SINGLE_CLASS, False))
        self.lastLabel = None
        # Add option to enable/disable labels being displayed at the top of bounding boxes
        self.display_label_option = QAction(get_str('displayLabel'), self)
        self.display_label_option.setShortcut("Ctrl+Shift+P")
        self.display_label_option.setCheckable(True)
        self.display_label_option.setChecked(settings.get(SETTING_PAINT_LABEL, False))
        self.display_label_option.triggered.connect(self.toggle_paint_labels_option)

        yolo_predict_action = QAction('YOLO 模型预标注', self)
        yolo_predict_action.setShortcut('Ctrl+Y')
        yolo_predict_action.triggered.connect(self.show_yolo_predict_dialog)

        sam_action = QAction('SAM 半自动标注', self)
        sam_action.setShortcut('Ctrl+Shift+Y')
        sam_action.triggered.connect(self.show_sam_dialog)

        add_actions(self.menus.file,
                    (open, open_dir, change_save_dir, open_annotation, copy_prev_bounding, self.menus.recentFiles, save, save_format, save_as, close, reset_all, delete_image, None, yolo_predict_action, sam_action, quit))
        add_actions(self.menus.help, (help_default, show_info, show_shortcut, custom_shortcut, show_stats))
        add_actions(self.menus.view, (
            self.auto_saving,
            self.auto_save_all,
            self.single_class_mode,
            self.display_label_option,
            labels, advanced_mode, None,
            hide_all, show_all, None,
            zoom_in, zoom_out, zoom_org, None,
            fit_window, fit_width))

        # 可选：也把批量复制动作加入“文件”菜单，靠近“从上一帧复制”
        add_actions(self.menus.file, (copy_next_5, copy_next_10, copy_next_25, copy_next_custom))

        self.menus.file.aboutToShow.connect(self.update_file_menu)

        # Custom context menu for the canvas widget:
        add_actions(self.canvas.menus[0], self.actions.beginnerContext)
        add_actions(self.canvas.menus[1], (
            action('&Copy here', self.copy_shape),
            action('&Move here', self.move_shape)))

        self.tools = self.toolbar('Tools')
        self.actions.beginner = (
            open, open_dir, change_save_dir, open_next_image, open_prev_image, verify, save, save_format, None, create, copy, delete, None,
            zoom_in, zoom, zoom_out, fit_window, fit_width)

        self.actions.advanced = (
            open, open_dir, change_save_dir, open_next_image, open_prev_image, save, save_format, None,
            create_mode, edit_mode, None,
            hide_all, show_all)

        self.statusBar().showMessage('%s started.' % __appname__)
        self.statusBar().show()

        # Fix the compatible issue for qt4 and qt5. Convert the QStringList to python list
        if settings.get(SETTING_RECENT_FILES):
            if have_qstring():
                recent_file_qstring_list = settings.get(SETTING_RECENT_FILES)
                self.recent_files = [ustr(i) for i in recent_file_qstring_list]
            else:
                self.recent_files = recent_file_qstring_list = settings.get(SETTING_RECENT_FILES)

        size = settings.get(SETTING_WIN_SIZE, QSize(600, 500))
        position = QPoint(0, 0)
        saved_position = settings.get(SETTING_WIN_POSE, position)
        # Fix the multiple monitors issue
        for i in range(QApplication.desktop().screenCount()):
            if QApplication.desktop().availableGeometry(i).contains(saved_position):
                position = saved_position
                break
        self.resize(size)
        self.move(position)
        save_dir = ustr(settings.get(SETTING_SAVE_DIR, None))
        self.last_open_dir = ustr(settings.get(SETTING_LAST_OPEN_DIR, None))
        if self.default_save_dir is None and save_dir is not None and os.path.exists(save_dir):
            self.default_save_dir = save_dir
            self.statusBar().showMessage('%s started. Annotation will be saved to %s' %
                                         (__appname__, self.default_save_dir))
            self.statusBar().show()

        self.restoreState(settings.get(SETTING_WIN_STATE, QByteArray()))
        Shape.line_color = self.line_color = QColor(settings.get(SETTING_LINE_COLOR, DEFAULT_LINE_COLOR))
        Shape.fill_color = self.fill_color = QColor(settings.get(SETTING_FILL_COLOR, DEFAULT_FILL_COLOR))
        self.canvas.set_drawing_color(self.line_color)
        # Add chris
        Shape.difficult = self.difficult

        def xbool(x):
            if isinstance(x, QVariant):
                return x.toBool()
            return bool(x)

        if xbool(settings.get(SETTING_ADVANCE_MODE, False)):
            self.actions.advancedMode.setChecked(True)
            self.toggle_advanced_mode()

        # Populate the File menu dynamically.
        self.update_file_menu()

        # Since loading the file may take some time, make sure it runs in the background.
        if self.file_path and os.path.isdir(self.file_path):
            self.queue_event(partial(self.import_dir_images, self.file_path or ""))
        elif self.file_path:
            self.queue_event(partial(self.load_file, self.file_path or ""))

        # Callbacks:
        self.zoom_widget.valueChanged.connect(self.paint_canvas)

        self.populate_mode_actions()
        self.load_custom_shortcuts()

        # Display cursor coordinates at the right of status bar
        self.label_coordinates = QLabel('')
        self.statusBar().addPermanentWidget(self.label_coordinates)

        # Open Dir if default file
        if self.file_path and os.path.isdir(self.file_path):
            self.open_dir_dialog(dir_path=self.file_path, silent=True)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        if event.key() == Qt.Key_Control:
            self.canvas.set_drawing_shape_to_square(False)

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        if event.key() == Qt.Key_Control:
            # Draw rectangle if Ctrl is pressed
            self.canvas.set_drawing_shape_to_square(True)
        
        # 防止在绘图过程中触发可能导致冲突的快捷键逻辑
        if self.canvas.drawing() and self.canvas.current:
            # 如果正在绘图且按下了非控制键，可以考虑忽略或做特殊处理
            # 但 QAction 快捷键通常在 keyPressEvent 之前被拦截
            pass

    # Support Functions #
    def set_format(self, save_format):
        if save_format == FORMAT_PASCALVOC:
            self.actions.save_format.setText(FORMAT_PASCALVOC)
            self.actions.save_format.setIcon(new_icon("format_voc"))
            self.label_file_format = LabelFileFormat.PASCAL_VOC
            LabelFile.suffix = XML_EXT

        elif save_format == FORMAT_YOLO:
            self.actions.save_format.setText(FORMAT_YOLO)
            self.actions.save_format.setIcon(new_icon("format_yolo"))
            self.label_file_format = LabelFileFormat.YOLO
            LabelFile.suffix = TXT_EXT

        elif save_format == FORMAT_CREATEML:
            self.actions.save_format.setText(FORMAT_CREATEML)
            self.actions.save_format.setIcon(new_icon("format_createml"))
            self.label_file_format = LabelFileFormat.CREATE_ML
            LabelFile.suffix = JSON_EXT

    def show_custom_shortcuts_dialog(self):
        dialog = ShortcutDialog(self.actions, self)
        if dialog.exec_():
            shortcuts = dialog.get_shortcuts()
            self.settings[SETTING_CUSTOM_SHORTCUTS] = shortcuts
            self.settings.save()
            self.apply_custom_shortcuts(shortcuts)

    def apply_custom_shortcuts(self, shortcuts):
        for name, shortcut in shortcuts.items():
            if hasattr(self.actions, name):
                action = getattr(self.actions, name)
                if isinstance(action, QAction):
                    action.setShortcut(shortcut)
        
        # 显式确保 Ctrl+Z 绑定到撤回
        if hasattr(self.actions, 'undo'):
            self.actions.undo.setShortcut('Ctrl+Z')

    def load_custom_shortcuts(self):
        shortcuts = self.settings.get(SETTING_CUSTOM_SHORTCUTS)
        if shortcuts:
            self.apply_custom_shortcuts(shortcuts)

    def update_daily_stats(self, file_path):
        """更新每日图片打开统计"""
        if not file_path or os.path.isdir(file_path):
            return

        from datetime import datetime
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        # 获取现有统计
        stats = self.settings.get(SETTING_DAILY_STATS, {})
        
        # 跨天清空逻辑：如果记录的日期不是今天，则重置
        if stats.get('date') != today_str:
            stats = {
                'date': today_str,
                'paths': {},
                'opened_files': set() # 用于去重，防止重复打开同一张图重复计数
            }
        
        # 确保 opened_files 是集合
        if 'opened_files' not in stats or not isinstance(stats['opened_files'], set):
            stats['opened_files'] = set()

        # 如果该文件今天还没打开过，则计数
        abs_path = os.path.abspath(file_path)
        if abs_path not in stats['opened_files']:
            stats['opened_files'].add(abs_path)
            
            dir_path = os.path.dirname(abs_path)
            stats['paths'][dir_path] = stats['paths'].get(dir_path, 0) + 1
            
            # 保存更新
            self.settings[SETTING_DAILY_STATS] = stats
            self.settings.save()
            
            # 实时更新 UI 上的总计数标签
            self.update_daily_total_label()

    def show_daily_stats_dialog(self):
        """显示每日统计明细对话框"""
        stats = self.settings.get(SETTING_DAILY_STATS, {})
        
        # 再次检查日期，防止对话框显示旧数据
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")
        if stats.get('date') != today_str:
            stats = {'date': today_str, 'paths': {}}
            
        dialog = StatisticsDialog(stats, self)
        dialog.exec_()

    def change_format(self):
        if self.label_file_format == LabelFileFormat.PASCAL_VOC:
            self.set_format(FORMAT_YOLO)
        elif self.label_file_format == LabelFileFormat.YOLO:
            self.set_format(FORMAT_CREATEML)
        elif self.label_file_format == LabelFileFormat.CREATE_ML:
            self.set_format(FORMAT_PASCALVOC)
        else:
            raise ValueError('Unknown label file format.')
        self.set_dirty()

    def no_shapes(self):
        return not self.items_to_shapes

    def toggle_advanced_mode(self, value=True):
        self._beginner = not value
        self.canvas.set_editing(True)
        self.populate_mode_actions()
        self.edit_button.setVisible(not value)
        if value:
            self.actions.createMode.setEnabled(True)
            self.actions.editMode.setEnabled(False)
            self.dock.setFeatures(self.dock.features() | self.dock_features)
        else:
            self.dock.setFeatures(self.dock.features() ^ self.dock_features)

    def populate_mode_actions(self):
        if self.beginner():
            tool, menu = self.actions.beginner, self.actions.beginnerContext
        else:
            tool, menu = self.actions.advanced, self.actions.advancedContext
        self.tools.clear()
        add_actions(self.tools, tool)
        self.canvas.menus[0].clear()
        add_actions(self.canvas.menus[0], menu)
        self.menus.edit.clear()
        actions = (self.actions.create,) if self.beginner()\
            else (self.actions.createMode, self.actions.editMode)
        add_actions(self.menus.edit, actions + self.actions.editMenu)

    def set_beginner(self):
        self.tools.clear()
        add_actions(self.tools, self.actions.beginner)

    def set_advanced(self):
        self.tools.clear()
        add_actions(self.tools, self.actions.advanced)

    def set_dirty(self):
        self.dirty = True
        self.actions.save.setEnabled(True)
        # Auto save operations if enabled
        try:
            # Original auto_saving or custom auto_save_all
            if (hasattr(self, 'auto_save_all') and self.auto_save_all.isChecked()) or \
               (hasattr(self, 'auto_saving') and self.auto_saving.isChecked()):
                self.save_file()
        except Exception:
            # If saving fails unexpectedly, keep the app responsive
            pass

    def save_undo_snapshot(self):
        """保存当前所有标注的状态快照到撤回栈"""
        snapshot = []
        for shape in self.canvas.shapes:
            snapshot.append(shape.copy())
        
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)

    def undo_last_operation(self):
        """执行撤回操作，恢复到上一个状态快照"""
        if not self.undo_stack:
            self.status("没有可撤回的操作", 2000)
            return

        # 弹出最近的一个快照
        snapshot = self.undo_stack.pop()
        
        # 清除当前所有标注
        self.canvas.shapes = []
        self.label_list.clear()
        self.items_to_shapes.clear()
        self.shapes_to_items.clear()
        
        # 恢复快照中的标注
        for shape in snapshot:
            self.canvas.shapes.append(shape)
            self.add_label(shape)
            
        self.canvas.update()
        self.set_dirty()
        self.status("已撤回上一次操作", 2000)

    def set_clean(self):
        self.dirty = False
        self.actions.save.setEnabled(False)
        self.actions.create.setEnabled(True)

    def toggle_actions(self, value=True):
        """Enable/Disable widgets which depend on an opened image."""
        for z in self.actions.zoomActions:
            z.setEnabled(value)
        for action in self.actions.onLoadActive:
            action.setEnabled(value)

    def queue_event(self, function):
        QTimer.singleShot(0, function)

    def status(self, message, delay=5000):
        self.statusBar().showMessage(message, delay)

    def reset_state(self):
        self.items_to_shapes.clear()
        self.shapes_to_items.clear()
        self.label_list.clear()
        self.file_path = None
        self.image_data = None
        self.label_file = None
        self.canvas.reset_state()
        self.canvas.pixmap = QPixmap() # trigger background animation
        self.canvas.tech_timer.start(50)
        self.label_coordinates.clear()
        self.combo_box.cb.clear()

    def current_item(self):
        items = self.label_list.selectedItems()
        if items:
            return items[0]
        return None

    def add_recent_file(self, file_path):
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        elif len(self.recent_files) >= self.max_recent:
            self.recent_files.pop()
        self.recent_files.insert(0, file_path)

    def beginner(self):
        return self._beginner

    def advanced(self):
        return not self.beginner()

    def show_tutorial_dialog(self, browser='default', link=None):
        if link is None:
            link = self.screencast

        if browser.lower() == 'default':
            wb.open(link, new=2)
        elif browser.lower() == 'chrome' and self.os_name == 'Windows':
            if shutil.which(browser.lower()):  # 'chrome' not in wb._browsers in windows
                wb.register('chrome', None, wb.BackgroundBrowser('chrome'))
            else:
                chrome_path="D:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
                if os.path.isfile(chrome_path):
                    wb.register('chrome', None, wb.BackgroundBrowser(chrome_path))
            try:
                wb.get('chrome').open(link, new=2)
            except:
                wb.open(link, new=2)
        elif browser.lower() in wb._browsers:
            wb.get(browser.lower()).open(link, new=2)

    def show_default_tutorial_dialog(self):
        self.show_tutorial_dialog(browser='default')

    def show_info_dialog(self):
        from libs.__init__ import __version__
        msg = u'Name:{0} \nApp Version:{1} \n{2} '.format(__appname__, __version__, sys.version_info)
        QMessageBox.information(self, u'Information', msg)

    def show_shortcuts_dialog(self):
        self.show_tutorial_dialog(browser='default', link='https://github.com/tzutalin/labelImg#Hotkeys')

    def show_yolo_predict_dialog(self):
        from libs.yolo_predict_dialog import YOLOPredictDialog
        dialog = YOLOPredictDialog(self, parent=self)
        dialog.exec_()

    def show_sam_dialog(self):
        from libs.sam_dialog import SAMDialog
        dialog = SAMDialog(self, parent=self)
        dialog.exec_()

    def _sam_click(self, x, y):
        if not hasattr(self, '_sam_predictor') or self._sam_predictor is None:
            return
        import numpy as np
        from PyQt5.QtCore import QPointF
        from libs.shape import Shape
        from libs.utils import generate_color_by_text
        self.save_undo_snapshot()
        mask = self._sam_predictor.predict_box([x - 50, y - 50, x + 50, y + 50])
        if mask is None:
            return
        bbox = self._sam_predictor.mask_to_bbox(mask)
        if bbox is None:
            return
        x1, y1, x2, y2 = bbox
        label = self.label_dialog.pop_up(text='sam_target')
        if not label:
            return
        shape = Shape(label=label)
        shape.add_point(QPointF(x1, y1))
        shape.add_point(QPointF(x2, y1))
        shape.add_point(QPointF(x2, y2))
        shape.add_point(QPointF(x1, y2))
        shape.close()
        shape.line_color = generate_color_by_text(label)
        shape.fill_color = generate_color_by_text(label)
        self.canvas.shapes.append(shape)
        self.add_label(shape)
        self.set_dirty()
        self.canvas.update()

    def load_yolo_detections(self, detections):
        from PyQt5.QtCore import QPointF
        from libs.shape import Shape
        from libs.utils import generate_color_by_text
        self.save_undo_snapshot()
        for det in detections:
            shape = Shape(label=det['label'])
            for x, y in det['points']:
                shape.add_point(QPointF(x, y))
            shape.close()
            shape.line_color = generate_color_by_text(det['label'])
            shape.fill_color = generate_color_by_text(det['label'])
            self.canvas.shapes.append(shape)
            self.add_label(shape)
        self.set_dirty()
        self.canvas.update()

    def hasAnnotationFile(self, img_path):
        if not img_path:
            return False
        if self.default_save_dir:
            base = os.path.splitext(os.path.basename(img_path))[0]
            for ext in [XML_EXT, TXT_EXT, JSON_EXT]:
                if os.path.isfile(os.path.join(self.default_save_dir, base + ext)):
                    return True
        else:
            base_name = os.path.splitext(img_path)[0]
            for ext in ['.xml', '.txt', '.json']:
                if os.path.exists(base_name + ext):
                    return True
        return False

    def create_shape(self):
        assert self.beginner()
        self.canvas.set_editing(False)
        self.actions.create.setEnabled(False)

    def toggle_drawing_sensitive(self, drawing=True):
        """In the middle of drawing, toggling between modes should be disabled."""
        self.actions.editMode.setEnabled(not drawing)
        if not drawing and self.beginner():
            # Cancel creation.
            print('Cancel creation.')
            self.canvas.set_editing(True)
            self.canvas.restore_cursor()
            self.actions.create.setEnabled(True)

    def toggle_draw_mode(self, edit=True):
        self.canvas.set_editing(edit)
        self.actions.createMode.setEnabled(edit)
        self.actions.editMode.setEnabled(not edit)

    def set_create_mode(self):
        assert self.advanced()
        self.toggle_draw_mode(False)

    def set_edit_mode(self):
        assert self.advanced()
        self.toggle_draw_mode(True)
        self.label_selection_changed()

    def update_file_menu(self):
        curr_file_path = self.file_path

        def exists(filename):
            return os.path.exists(filename)
        menu = self.menus.recentFiles
        menu.clear()
        files = [f for f in self.recent_files if f !=
                 curr_file_path and exists(f)]
        for i, f in enumerate(files):
            icon = new_icon('labels')
            action = QAction(
                icon, '&%d %s' % (i + 1, QFileInfo(f).fileName()), self)
            action.triggered.connect(partial(self.load_recent, f))
            menu.addAction(action)

    def pop_label_list_menu(self, point):
        self.menus.labelList.exec_(self.label_list.mapToGlobal(point))

    def edit_label(self):
        if not self.canvas.editing():
            return
        item = self.current_item()
        if not item:
            return
        text = self.label_dialog.pop_up(item.text())
        if text is not None:
            item.setText(text)
            item.setBackground(generate_color_by_text(text))
            self.set_dirty()
            self.update_combo_box()

    # Tzutalin 20160906 : Add file list and dock to move faster
    def file_item_double_clicked(self, item=None):
        self.cur_img_idx = self.m_img_list.index(ustr(item.text()))
        filename = self.m_img_list[self.cur_img_idx]
        if filename:
            self.load_file(filename)

    # Add chris
    def button_state(self, item=None):
        """ Function to handle difficult examples
        Update on each object """
        if not self.canvas.editing():
            return

        item = self.current_item()
        if not item:  # If not selected Item, take the first one
            item = self.label_list.item(self.label_list.count() - 1)

        difficult = self.diffc_button.isChecked()

        try:
            shape = self.items_to_shapes[item]
        except:
            pass
        # Checked and Update
        try:
            if difficult != shape.difficult:
                shape.difficult = difficult
                self.set_dirty()
            else:  # User probably changed item visibility
                self.canvas.set_shape_visible(shape, item.checkState() == Qt.Checked)
        except:
            pass

    # React to canvas signals.
    def shape_selection_changed(self, selected=False):
        if self._no_selection_slot:
            self._no_selection_slot = False
        else:
            shape = self.canvas.selected_shape
            if shape:
                if shape in self.shapes_to_items:
                    self.shapes_to_items[shape].setSelected(True)
                else:
                    # 映射不存在时尝试刷新映射或忽略，防止 KeyError 导致闪退
                    pass
            else:
                self.label_list.clearSelection()
        self.actions.delete.setEnabled(selected)
        self.actions.copy.setEnabled(selected)
        self.actions.edit.setEnabled(selected)
        self.actions.shapeLineColor.setEnabled(selected)
        self.actions.shapeFillColor.setEnabled(selected)
        # 选中时启用批量复制动作
        if hasattr(self.actions, 'copyNext5'):
            self.actions.copyNext5.setEnabled(selected)
        if hasattr(self.actions, 'copyNext10'):
            self.actions.copyNext10.setEnabled(selected)
        if hasattr(self.actions, 'copyNext25'):
            self.actions.copyNext25.setEnabled(selected)

    def add_label(self, shape):
        shape.paint_label = self.display_label_option.isChecked()
        item = HashableQListWidgetItem(shape.label)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)
        item.setBackground(generate_color_by_text(shape.label))
        self.items_to_shapes[item] = shape
        self.shapes_to_items[shape] = item
        self.label_list.addItem(item)
        for action in self.actions.onShapesPresent:
            action.setEnabled(True)
        self.update_combo_box()

    def remove_label(self, shape):
        if shape is None:
            return
        if shape in self.shapes_to_items:
            item = self.shapes_to_items[shape]
            self.label_list.takeItem(self.label_list.row(item))
            del self.shapes_to_items[shape]
            if item in self.items_to_shapes:
                del self.items_to_shapes[item]
            self.update_combo_box()
        if shape in self.canvas.shapes:
            self.canvas.shapes.remove(shape)
            self.canvas.update()

    def load_labels(self, shapes):
        s = []
        for label, points, line_color, fill_color, difficult in shapes:
            shape = Shape(label=label)
            for x, y in points:

                # Ensure the labels are within the bounds of the image. If not, fix them.
                x, y, snapped = self.canvas.snap_point_to_canvas(x, y)
                if snapped:
                    self.set_dirty()

                shape.add_point(QPointF(x, y))
            shape.difficult = difficult
            shape.close()
            s.append(shape)

            if line_color:
                shape.line_color = QColor(*line_color)
            else:
                shape.line_color = generate_color_by_text(label)

            if fill_color:
                shape.fill_color = QColor(*fill_color)
            else:
                shape.fill_color = generate_color_by_text(label)

            self.add_label(shape)
        self.update_combo_box()
        self.canvas.load_shapes(s)

    def update_combo_box(self):
        # Get the unique labels and add them to the Combobox.
        items_text_list = [str(self.label_list.item(i).text()) for i in range(self.label_list.count())]

        unique_text_list = list(set(items_text_list))
        # Add a null row for showing all the labels
        unique_text_list.append("")
        unique_text_list.sort()

        self.combo_box.update_items(unique_text_list)

    def save_labels(self, annotation_file_path):
        annotation_file_path = ustr(annotation_file_path)
        if self.label_file is None:
            self.label_file = LabelFile()
            self.label_file.verified = self.canvas.verified

        def format_shape(s):
            return dict(label=s.label,
                        line_color=s.line_color.getRgb(),
                        fill_color=s.fill_color.getRgb(),
                        points=[(p.x(), p.y()) for p in s.points],
                        # add chris
                        difficult=s.difficult)

        shapes = [format_shape(shape) for shape in self.canvas.shapes]
        # Can add different annotation formats here
        try:
            if self.label_file_format == LabelFileFormat.PASCAL_VOC:
                if annotation_file_path[-4:].lower() != ".xml":
                    annotation_file_path += XML_EXT
                self.label_file.save_pascal_voc_format(annotation_file_path, shapes, self.file_path, self.image_data,
                                                       self.line_color.getRgb(), self.fill_color.getRgb())
            elif self.label_file_format == LabelFileFormat.YOLO:
                if annotation_file_path[-4:].lower() != ".txt":
                    annotation_file_path += TXT_EXT
                self.label_file.save_yolo_format(annotation_file_path, shapes, self.file_path, self.image_data, self.label_hist,
                                                 self.line_color.getRgb(), self.fill_color.getRgb())
            elif self.label_file_format == LabelFileFormat.CREATE_ML:
                if annotation_file_path[-5:].lower() != ".json":
                    annotation_file_path += JSON_EXT
                self.label_file.save_create_ml_format(annotation_file_path, shapes, self.file_path, self.image_data,
                                                      self.label_hist, self.line_color.getRgb(), self.fill_color.getRgb())
            else:
                self.label_file.save(annotation_file_path, shapes, self.file_path, self.image_data,
                                     self.line_color.getRgb(), self.fill_color.getRgb())
            print('Image:{0} -> Annotation:{1}'.format(self.file_path, annotation_file_path))
            return True
        except LabelFileError as e:
            self.error_message(u'Error saving label data', u'<b>%s</b>' % e)
            return False

    def copy_selected_shape(self):
        self.discard_drawing()
        self.save_undo_snapshot()
        self.add_label(self.canvas.copy_selected_shape())
        # fix copy and delete
        self.shape_selection_changed(True)

    def combo_selection_changed(self, index):
        text = self.combo_box.cb.itemText(index)
        for i in range(self.label_list.count()):
            if text == "":
                self.label_list.item(i).setCheckState(2)
            elif text != self.label_list.item(i).text():
                self.label_list.item(i).setCheckState(0)
            else:
                self.label_list.item(i).setCheckState(2)

    def label_selection_changed(self):
        item = self.current_item()
        if item and self.canvas.editing():
            self._no_selection_slot = True
            self.canvas.select_shape(self.items_to_shapes[item])
            shape = self.items_to_shapes[item]
            # Add Chris
            self.diffc_button.setChecked(shape.difficult)

    def label_item_changed(self, item):
        shape = self.items_to_shapes[item]
        label = item.text()
        if label != shape.label:
            shape.label = item.text()
            shape.line_color = generate_color_by_text(shape.label)
            self.set_dirty()
        else:  # User probably changed item visibility
            self.canvas.set_shape_visible(shape, item.checkState() == Qt.Checked)

    # Callback functions:
    def new_shape(self):
        """Pop-up and give focus to the label editor.

        position MUST be in global coordinates.
        """
        self.save_undo_snapshot()
        if not self.use_default_label_checkbox.isChecked() or not self.default_label_text_line.text():
            if len(self.label_hist) > 0:
                self.label_dialog = LabelDialog(
                    parent=self, list_item=self.label_hist)

            # Sync single class mode from PR#106
            if self.single_class_mode.isChecked() and self.lastLabel:
                text = self.lastLabel
            else:
                text = self.label_dialog.pop_up(text=self.prev_label_text)
                self.lastLabel = text
        else:
            text = self.default_label_text_line.text()

        # Add Chris
        self.diffc_button.setChecked(False)
        if text is not None:
            self.prev_label_text = text
            generate_color = generate_color_by_text(text)
            shape = self.canvas.set_last_label(text, generate_color, generate_color)
            self.add_label(shape)

            if self.single_target_checkbox.isChecked():
                for s in list(self.canvas.shapes):
                    if s is not shape:
                        self.remove_label(s)
                self.canvas.update()

            if self.beginner():  # Switch to edit mode.
                self.canvas.set_editing(True)
                self.actions.create.setEnabled(True)
            else:
                self.actions.editMode.setEnabled(True)
            self.set_dirty()

            if text not in self.label_hist:
                self.label_hist.append(text)

            if self.fast_annotate_checkbox.isChecked():
                if self.dirty:
                    self.save_file()
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(50, self._fast_annotate_advance)
        else:
            # User cancelled the label dialog, remove the last shape added in Canvas.finalise
            self.canvas.pop_shape()
            self.canvas.reset_all_lines()

    def scroll_request(self, delta, orientation):
        units = - delta / (8 * 15)
        bar = self.scroll_bars[orientation]
        bar.setValue(int(bar.value() + bar.singleStep() * units))

    def set_zoom(self, value):
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoom_mode = self.MANUAL_ZOOM
        self.zoom_widget.setValue(int(value))

    def add_zoom(self, increment=10):
        self.set_zoom(self.zoom_widget.value() + increment)

    def zoom_request(self, delta):
        # get the current scrollbar positions
        # calculate the percentages ~ coordinates
        h_bar = self.scroll_bars[Qt.Horizontal]
        v_bar = self.scroll_bars[Qt.Vertical]

        # get the current maximum, to know the difference after zooming
        h_bar_max = h_bar.maximum()
        v_bar_max = v_bar.maximum()

        # get the cursor position and canvas size
        # calculate the desired movement from 0 to 1
        # where 0 = move left
        #       1 = move right
        # up and down analogous
        cursor = QCursor()
        pos = cursor.pos()
        relative_pos = QWidget.mapFromGlobal(self, pos)

        cursor_x = relative_pos.x()
        cursor_y = relative_pos.y()

        w = self.scroll_area.width()
        h = self.scroll_area.height()

        # the scaling from 0 to 1 has some padding
        # you don't have to hit the very leftmost pixel for a maximum-left movement
        margin = 0.1
        move_x = (cursor_x - margin * w) / (w - 2 * margin * w)
        move_y = (cursor_y - margin * h) / (h - 2 * margin * h)

        # clamp the values from 0 to 1
        move_x = min(max(move_x, 0), 1)
        move_y = min(max(move_y, 0), 1)

        # zoom in
        units = delta / (8 * 15)
        scale = 10
        self.add_zoom(scale * units)

        # get the difference in scrollbar values
        # this is how far we can move
        d_h_bar_max = h_bar.maximum() - h_bar_max
        d_v_bar_max = v_bar.maximum() - v_bar_max

        # get the new scrollbar values
        new_h_bar_value = h_bar.value() + move_x * d_h_bar_max
        new_v_bar_value = v_bar.value() + move_y * d_v_bar_max

        h_bar.setValue(int(new_h_bar_value))
        v_bar.setValue(int(new_v_bar_value))

    def set_fit_window(self, value=True):
        if value:
            self.actions.fitWidth.setChecked(False)
        self.zoom_mode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjust_scale()

    def set_fit_width(self, value=True):
        if value:
            self.actions.fitWindow.setChecked(False)
        self.zoom_mode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjust_scale()

    def toggle_polygons(self, value):
        for item, shape in self.items_to_shapes.items():
            item.setCheckState(Qt.Checked if value else Qt.Unchecked)

    def load_file(self, file_path=None):
        """Load the specified file, or the last opened file if None."""
        self.reset_state()
        self.canvas.setEnabled(False)
        if file_path is None:
            file_path = self.settings.get(SETTING_FILENAME)

        # 每日图片统计逻辑
        self.update_daily_stats(file_path)

        # Make sure that filePath is a regular python string, rather than QString
        file_path = ustr(file_path)

        # Fix bug: An  index error after select a directory when open a new file.
        unicode_file_path = ustr(file_path)
        unicode_file_path = os.path.abspath(unicode_file_path)
        # Tzutalin 20160906 : Add file list and dock to move faster
        # Highlight the file item
        if unicode_file_path and self.file_list_widget.count() > 0:
            if unicode_file_path in self.m_img_list:
                index = self.m_img_list.index(unicode_file_path)
                file_widget_item = self.file_list_widget.item(index)
                file_widget_item.setSelected(True)
            else:
                self.file_list_widget.clear()
                self.m_img_list.clear()

        if unicode_file_path and os.path.exists(unicode_file_path):
            if LabelFile.is_label_file(unicode_file_path):
                try:
                    self.label_file = LabelFile(unicode_file_path)
                except LabelFileError as e:
                    self.error_message(u'Error opening file',
                                       (u"<p><b>%s</b></p>"
                                        u"<p>Make sure <i>%s</i> is a valid label file.")
                                       % (e, unicode_file_path))
                    self.status("Error reading %s" % unicode_file_path)
                    return False
                self.image_data = self.label_file.image_data
                self.line_color = QColor(*self.label_file.lineColor)
                self.fill_color = QColor(*self.label_file.fillColor)
                self.canvas.verified = self.label_file.verified
            else:
                self.image_data = read(unicode_file_path, None)
                self.label_file = None
                self.canvas.verified = False

            if unicode_file_path in self._pixmap_cache:
                pixmap = self._pixmap_cache[unicode_file_path]
                image = pixmap.toImage()
            else:
                if isinstance(self.image_data, QImage):
                    image = self.image_data
                else:
                    image = QImage.fromData(self.image_data)
                if image.isNull():
                    self.error_message(u'Error opening file',
                                       u"<p>Make sure <i>%s</i> is a valid image file." % unicode_file_path)
                    self.status("Error reading %s" % unicode_file_path)
                    return False
                pixmap = QPixmap.fromImage(image)
                self._pixmap_cache[unicode_file_path] = pixmap
                if len(self._pixmap_cache) > 50:
                    oldest = list(self._pixmap_cache.keys())[0]
                    del self._pixmap_cache[oldest]

            self.status("Loaded %s" % os.path.basename(unicode_file_path))
            self.image = image
            self.file_path = unicode_file_path
            self.canvas.load_pixmap(pixmap)
            if self.label_file:
                self.load_labels(self.label_file.shapes)

            self.canvas.setEnabled(True)
            self.adjust_scale(initial=True)
            self.paint_canvas()
            self.add_recent_file(self.file_path)
            self.update_dir_labels()
            self.toggle_actions(True)
            self.show_bounding_box_from_annotation_file(file_path)

            if self.single_target_checkbox.isChecked() and len(self.canvas.shapes) > 1:
                self._prompt_single_target_selection()

            self.set_clean()
            counter = self.counter_str()
            self.setWindowTitle(__appname__ + ' ' + file_path + ' ' + counter)

            # Default : select last item if there is at least one item
            if self.label_list.count():
                self.label_list.setCurrentItem(self.label_list.item(self.label_list.count() - 1))
                self.label_list.item(self.label_list.count() - 1).setSelected(True)

            self.canvas.setFocus(True)
            self._preload_adjacent()
            return True
        return False

    def _preload_adjacent(self):
        from threading import Thread
        try:
            idx = self.m_img_list.index(self.file_path)
        except ValueError:
            return
        cache = self._pixmap_cache
        paths = []
        for pi in [idx + 1, idx + 2, idx - 1]:
            if 0 <= pi < len(self.m_img_list):
                p = self.m_img_list[pi]
                if p not in cache:
                    paths.append(p)
        if not paths:
            return
        def _load():
            for path in paths:
                if path in cache:
                    continue
                try:
                    pm = QPixmap(path)
                    if not pm.isNull():
                        cache[path] = pm
                        if len(cache) > 50:
                            oldest = list(cache.keys())[0]
                            del cache[oldest]
                except Exception:
                    pass
        t = Thread(target=_load, daemon=True)
        t.start()

    def _prompt_single_target_selection(self):
        shapes = list(self.canvas.shapes)
        if len(shapes) <= 1:
            return
        labels = [s.label for s in shapes]
        label, ok = QInputDialog.getItem(
            self, '单目标模式', '检测到多个标注框，请选择要保留的目标：',
            labels, 0, False)
        if not ok:
            return
        keep_shape = None
        for s in shapes:
            if s.label == label and keep_shape is None:
                keep_shape = s
        if keep_shape is None:
            return
        to_remove = [s for s in shapes if s is not keep_shape]
        self.canvas.shapes = [keep_shape]
        for s in to_remove:
            if s in self.shapes_to_items:
                item = self.shapes_to_items[s]
                self.label_list.takeItem(self.label_list.row(item))
                del self.shapes_to_items[s]
                if item in self.items_to_shapes:
                    del self.items_to_shapes[item]
        self.update_combo_box()
        self.canvas.update()
        self.save_file()

    def _fast_annotate_advance(self):
        if self.fast_annotate_checkbox.isChecked():
            self.open_next_image()

    def counter_str(self):
        """
        Converts image counter to string representation.
        """
        if not self.m_img_list:
            self.canvas.clear()
            self.canvas.pixmap = QPixmap() # ensure pixmap is completely null to show animation
            self.canvas.tech_timer.start(50)
            return '[0 / 0]'
        
        total_images = len(self.m_img_list)
        current_index = self.m_img_list.index(self.file_path) if self.file_path in self.m_img_list else 0
        
        # Count annotated images
        annotated_count = sum(1 for img_path in self.m_img_list 
                             if self.hasAnnotationFile(img_path))
        
        return '[{} / {} | 已标注: {} / {} ({:.1f}%)]'.format(
            current_index + 1, 
            total_images,
            annotated_count,
            total_images,
            annotated_count/total_images*100 if total_images > 0 else 0
        )

    def validateAnnotations(self):
        """验证标注数据质量"""
        issues = []
        
        for shape in self.canvas.shapes:
            # 检查标注框是否过小
            if self.getShapeArea(shape) < 100:  # 像素
                issues.append(f"标注框过小: {shape.label}")
            
            # 检查标注框是否超出图像边界
            if self.isShapeOutOfBounds(shape):
                issues.append(f"标注框超出边界: {shape.label}")
            
            # 检查标签是否为空
            if not shape.label or shape.label.strip() == "":
                issues.append("存在空标签")
        
        if issues:
            QMessageBox.warning(self, "数据质量检查", "\n".join(issues))
        else:
            QMessageBox.information(self, "数据质量检查", "标注数据质量良好！")

    def show_bounding_box_from_annotation_file(self, file_path):
        if self.default_save_dir is not None:
            basename = os.path.basename(os.path.splitext(file_path)[0])
            xml_path = os.path.join(self.default_save_dir, basename + XML_EXT)
            txt_path = os.path.join(self.default_save_dir, basename + TXT_EXT)
            json_path = os.path.join(self.default_save_dir, basename + JSON_EXT)

            """Annotation file priority:
            PascalXML > YOLO
            """
            if os.path.isfile(xml_path):
                self.load_pascal_xml_by_filename(xml_path)
            elif os.path.isfile(txt_path):
                self.load_yolo_txt_by_filename(txt_path)
            elif os.path.isfile(json_path):
                self.load_create_ml_json_by_filename(json_path, file_path)

        else:
            xml_path = os.path.splitext(file_path)[0] + XML_EXT
            txt_path = os.path.splitext(file_path)[0] + TXT_EXT
            if os.path.isfile(xml_path):
                self.load_pascal_xml_by_filename(xml_path)
            elif os.path.isfile(txt_path):
                self.load_yolo_txt_by_filename(txt_path)

    def resizeEvent(self, event):
        if self.canvas and not self.image.isNull()\
           and self.zoom_mode != self.MANUAL_ZOOM:
            self.adjust_scale()
        super(MainWindow, self).resizeEvent(event)

    def paint_canvas(self):
        assert not self.image.isNull(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoom_widget.value()
        self.canvas.label_font_size = int(0.02 * max(self.image.width(), self.image.height()))
        self.canvas.adjustSize()
        self.canvas.update()

    def adjust_scale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoom_mode]()
        self.zoom_widget.setValue(int(100 * value))

    def scale_fit_window(self):
        """Figure out the size of the pixmap in order to fit the main widget."""
        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scale_fit_width(self):
        # The epsilon does not seem to work too well here.
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def closeEvent(self, event):
        if not self.may_continue():
            event.ignore()
        settings = self.settings
        # If it loads images from dir, don't load it at the beginning
        if self.dir_name is None:
            settings[SETTING_FILENAME] = self.file_path if self.file_path else ''
        else:
            settings[SETTING_FILENAME] = ''

        settings[SETTING_WIN_SIZE] = self.size()
        settings[SETTING_WIN_POSE] = self.pos()
        settings[SETTING_WIN_STATE] = self.saveState()
        settings[SETTING_LINE_COLOR] = self.line_color
        settings[SETTING_FILL_COLOR] = self.fill_color
        settings[SETTING_RECENT_FILES] = self.recent_files
        settings[SETTING_ADVANCE_MODE] = not self._beginner
        if self.default_save_dir and os.path.exists(self.default_save_dir):
            settings[SETTING_SAVE_DIR] = ustr(self.default_save_dir)
        else:
            settings[SETTING_SAVE_DIR] = ''

        if self.last_open_dir and os.path.exists(self.last_open_dir):
            settings[SETTING_LAST_OPEN_DIR] = self.last_open_dir
        else:
            settings[SETTING_LAST_OPEN_DIR] = ''

        settings[SETTING_AUTO_SAVE] = self.auto_saving.isChecked()
        settings[SETTING_AUTO_SAVE_ALL] = self.auto_save_all.isChecked()
        settings[SETTING_SINGLE_CLASS] = self.single_class_mode.isChecked()
        settings[SETTING_PAINT_LABEL] = self.display_label_option.isChecked()
        settings[SETTING_SINGLE_TARGET] = self.single_target_checkbox.isChecked()
        settings[SETTING_FAST_ANNOTATE] = self.fast_annotate_checkbox.isChecked()
        settings[SETTING_DRAW_SQUARE] = self.draw_squares_option.isChecked()
        settings[SETTING_LABEL_FILE_FORMAT] = self.label_file_format
        settings[SETTING_SINGLE_TARGET] = self.single_target_checkbox.isChecked()
        settings[SETTING_FAST_ANNOTATE] = self.fast_annotate_checkbox.isChecked()
        settings.save()

    def load_recent(self, filename):
        if self.may_continue():
            self.load_file(filename)

    def scan_all_images(self, folder_path):
        extensions = ['.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        images = []

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    relative_path = os.path.join(root, file)
                    path = ustr(os.path.abspath(relative_path))
                    images.append(path)
        natural_sort(images, key=lambda x: x.lower())
        return images

    def change_save_dir_dialog(self, _value=False):
        if self.default_save_dir is not None:
            path = ustr(self.default_save_dir)
        else:
            path = '.'

        dir_path = ustr(QFileDialog.getExistingDirectory(self,
                                                         '%s - Save annotations to the directory' % __appname__, path,  QFileDialog.ShowDirsOnly
                                                         | QFileDialog.DontResolveSymlinks))

        if dir_path is not None and len(dir_path) > 1:
            self.default_save_dir = dir_path
            self.update_dir_labels()

        self.statusBar().showMessage('%s . Annotation will be saved to %s' %
                                     ('Change saved folder', self.default_save_dir))
        self.statusBar().show()

    def open_annotation_dialog(self, _value=False):
        if self.file_path is None:
            self.statusBar().showMessage('Please select image first')
            self.statusBar().show()
            return

        path = os.path.dirname(ustr(self.file_path))\
            if self.file_path else '.'
        if self.label_file_format == LabelFileFormat.PASCAL_VOC:
            filters = "Open Annotation XML file (%s)" % ' '.join(['*.xml'])
            filename = ustr(QFileDialog.getOpenFileName(self, '%s - Choose a xml file' % __appname__, path, filters))
            if filename:
                if isinstance(filename, (tuple, list)):
                    filename = filename[0]
            self.load_pascal_xml_by_filename(filename)

    def open_dir_dialog(self, _value=False, dir_path=None, silent=False):
        if not self.may_continue():
            return

        default_open_dir_path = dir_path if dir_path else '.'
        if self.last_open_dir and os.path.exists(self.last_open_dir):
            default_open_dir_path = self.last_open_dir
        else:
            default_open_dir_path = os.path.dirname(self.file_path) if self.file_path else '.'
        if silent != True:
            target_dir_path = ustr(QFileDialog.getExistingDirectory(self,
                                                                    '%s - Open Directory' % __appname__, default_open_dir_path,
                                                                    QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks))
        else:
            target_dir_path = ustr(default_open_dir_path)
        self.last_open_dir = target_dir_path
        self.import_dir_images(target_dir_path)

    def import_dir_images(self, dir_path):
        if not self.may_continue() or not dir_path:
            return

        self.last_open_dir = dir_path
        self.dir_name = dir_path
        self.update_dir_labels()
        self.file_path = None
        self.file_list_widget.clear()
        self.m_img_list = self.scan_all_images(dir_path)
        self.img_count = len(self.m_img_list)
        self.open_next_image()
        for imgPath in self.m_img_list:
            item = QListWidgetItem(imgPath)
            self.file_list_widget.addItem(item)

    def verify_image(self, _value=False):
        # Proceeding next image without dialog if having any label
        if self.file_path is not None:
            try:
                self.label_file.toggle_verify()
            except AttributeError:
                # If the labelling file does not exist yet, create if and
                # re-save it with the verified attribute.
                self.save_file()
                if self.label_file is not None:
                    self.label_file.toggle_verify()
                else:
                    return

            self.canvas.verified = self.label_file.verified
            self.paint_canvas()
            self.save_file()

    def open_prev_image(self, _value=False):
        self.discard_drawing()
        if self.auto_saving.isChecked() or self.auto_save_all.isChecked():
            if self.dirty is True:
                self.save_file()
        else:
            if not self.may_continue():
                return

        if self.img_count <= 0:
            return

        if self.file_path is None:
            return

        if self.cur_img_idx - 1 >= 0:
            self.cur_img_idx -= 1
            filename = self.m_img_list[self.cur_img_idx]
            if filename:
                self.load_file(filename)

    def open_next_image(self, _value=False):
        self.discard_drawing()
        if self.auto_saving.isChecked() or self.auto_save_all.isChecked():
            if self.dirty is True:
                self.save_file()
        else:
            if not self.may_continue():
                return

        if self.img_count <= 0:
            return

        filename = None
        if self.file_path is None:
            filename = self.m_img_list[0]
            self.cur_img_idx = 0
        else:
            if self.cur_img_idx + 1 < self.img_count:
                self.cur_img_idx += 1
                filename = self.m_img_list[self.cur_img_idx]

        if filename:
            self.load_file(filename)

    def open_file(self, _value=False):
        self.discard_drawing()
        if not self.may_continue():
            return
        path = os.path.dirname(ustr(self.file_path)) if self.file_path else '.'
        formats = ['*.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        filters = "Image & Label files (%s)" % ' '.join(formats + ['*%s' % LabelFile.suffix])
        filename = QFileDialog.getOpenFileName(self, '%s - Choose Image or Label file' % __appname__, path, filters)
        if filename:
            if isinstance(filename, (tuple, list)):
                filename = filename[0]
            self.cur_img_idx = 0
            self.img_count = 1
            self.load_file(filename)

    def save_file(self, _value=False):
        self.discard_drawing()
        if self.default_save_dir is not None and len(ustr(self.default_save_dir)):
            if self.file_path:
                image_file_name = os.path.basename(self.file_path)
                saved_file_name = os.path.splitext(image_file_name)[0]
                saved_path = os.path.join(ustr(self.default_save_dir), saved_file_name)
                return self._save_file(saved_path)
        else:
            image_file_dir = os.path.dirname(self.file_path)
            image_file_name = os.path.basename(self.file_path)
            saved_file_name = os.path.splitext(image_file_name)[0]
            saved_path = os.path.join(image_file_dir, saved_file_name)
            return self._save_file(saved_path if self.label_file
                                  else self.save_file_dialog(remove_ext=False))
        return False

    def save_file_as(self, _value=False):
        self.discard_drawing()
        assert not self.image.isNull(), "cannot save empty image"
        return self._save_file(self.save_file_dialog())

    def save_file_dialog(self, remove_ext=True):
        caption = '%s - Choose File' % __appname__
        filters = 'File (*%s)' % LabelFile.suffix
        open_dialog_path = self.current_path()
        dlg = QFileDialog(self, caption, open_dialog_path, filters)
        dlg.setDefaultSuffix(LabelFile.suffix[1:])
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        filename_without_extension = os.path.splitext(self.file_path)[0]
        dlg.selectFile(filename_without_extension)
        dlg.setOption(QFileDialog.DontUseNativeDialog, False)
        if dlg.exec_():
            full_file_path = ustr(dlg.selectedFiles()[0])
            if remove_ext:
                return os.path.splitext(full_file_path)[0]  # Return file path without the extension.
            else:
                return full_file_path
        return ''

    def _save_file(self, annotation_file_path):
        try:
            if annotation_file_path and self.save_labels(annotation_file_path):
                self.set_clean()
                self.statusBar().showMessage('Saved to  %s' % annotation_file_path)
                self.statusBar().show()
                return True
        except Exception as e:
            self.statusBar().showMessage('保存失败: 权限不足或文件被占用')
            self.statusBar().show()
            print('保存标注文件失败: {}'.format(e))
        return False

    def close_file(self, _value=False):
        if not self.may_continue():
            return
        self.reset_state()
        self.set_clean()
        self.toggle_actions(False)
        self.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)

    def delete_image(self):
        delete_path = self.file_path
        if delete_path is not None:
            self.open_next_image()
            self.cur_img_idx -= 1
            self.img_count -= 1
            if os.path.exists(delete_path):
                os.remove(delete_path)
            self.import_dir_images(self.last_open_dir)

    def reset_all(self):
        self.settings.reset()
        self.close()
        process = QProcess()
        process.startDetached(os.path.abspath(__file__))

    def hasAnnotationFile(self, image_path):
        """Check if image has annotation file"""
        if not image_path:
            return False
        base_name = os.path.splitext(image_path)[0]
        xml_file = base_name + '.xml'
        txt_file = base_name + '.txt'
        json_file = base_name + '.json'
        return os.path.exists(xml_file) or os.path.exists(txt_file) or os.path.exists(json_file)

    def may_continue(self):
        if not self.dirty:
            return True
        else:
            discard_changes = self.discard_changes_dialog()
            if discard_changes == QMessageBox.No:
                return True
            elif discard_changes == QMessageBox.Yes:
                return self.save_file()
            else:
                return False

    def discard_changes_dialog(self):
        yes, no, cancel = QMessageBox.Yes, QMessageBox.No, QMessageBox.Cancel
        msg = u'You have unsaved changes, would you like to save them and proceed?\nClick "No" to undo all changes.'
        return QMessageBox.warning(self, u'Attention', msg, yes | no | cancel)

    def error_message(self, title, message):
        return QMessageBox.critical(self, title,
                                    '<p><b>%s</b></p>%s' % (title, message))

    def current_path(self):
        return os.path.dirname(self.file_path) if self.file_path else '.'

    def choose_color1(self):
        color = self.color_dialog.getColor(self.line_color, u'Choose line color',
                                           default=DEFAULT_LINE_COLOR)
        if color:
            self.line_color = color
            Shape.line_color = color
            self.canvas.set_drawing_color(color)
            self.canvas.update()
            self.set_dirty()

    def discard_drawing(self):
        """如果正在绘图，丢弃当前绘图状态，防止操作冲突导致崩溃"""
        if self.canvas.drawing() and self.canvas.current:
            self.canvas.reset_all_lines()
            self.canvas.repaint()
            return True
        return False

    def delete_selected_shape(self):
        self.discard_drawing()
        self.save_undo_snapshot()
        self.canvas.delete_selected()
        self.set_dirty()
        if self.no_shapes():
            for action in self.actions.onShapesPresent:
                action.setEnabled(False)

    def delete_selected_shapes(self):
        # Delete multiple shapes mapped from selected label items; fallback to single-delete
        self.save_undo_snapshot()
        try:
            selected_items = self.label_list.selectedItems()
        except Exception:
            selected_items = []

        if not selected_items:
            # No multi-selection; use existing single-delete behavior
            return self.delete_selected_shape()

        shapes = []
        for item in selected_items:
            shape = self.items_to_shapes.get(item)
            if shape:
                shapes.append(shape)

        if not shapes:
            return

        # Delete each shape and remove its label item
        for shape in shapes:
            # Prefer direct removal to avoid interfering with current selection
            if hasattr(self.canvas, 'remove_shape'):
                self.canvas.remove_shape(shape)
            else:
                # Fallback: select then delete
                self.canvas.select_shape(shape)
                self.canvas.delete_selected()
            self.remove_label(shape)

        self.set_dirty()
        if self.no_shapes():
            for action in self.actions.onShapesPresent:
                action.setEnabled(False)

    def choose_shape_line_color(self):
        color = self.color_dialog.getColor(self.line_color, u'Choose Line Color',
                                           default=DEFAULT_LINE_COLOR)
        if color:
            self.canvas.selected_shape.line_color = color
            self.canvas.update()
            self.set_dirty()

    def choose_shape_fill_color(self):
        color = self.color_dialog.getColor(self.fill_color, u'Choose Fill Color',
                                           default=DEFAULT_FILL_COLOR)
        if color:
            self.canvas.selected_shape.fill_color = color
            self.canvas.update()
            self.set_dirty()

    def copy_shape(self):
        self.canvas.end_move(copy=True)
        self.add_label(self.canvas.selected_shape)
        self.set_dirty()

    def move_shape(self):
        self.canvas.end_move(copy=False)
        self.set_dirty()

    def load_predefined_classes(self, predef_classes_file):
        if predef_classes_file and os.path.exists(predef_classes_file):
            with codecs.open(predef_classes_file, 'r', 'utf8') as f:
                for line in f:
                    line = line.strip()
                    if self.label_hist is None:
                        self.label_hist = [line]
                    else:
                        self.label_hist.append(line)

    def load_pascal_xml_by_filename(self, xml_path):
        if self.file_path is None:
            return
        if os.path.isfile(xml_path) is False:
            return

        self.set_format(FORMAT_PASCALVOC)

        t_voc_parse_reader = PascalVocReader(xml_path)
        shapes = t_voc_parse_reader.get_shapes()
        self.load_labels(shapes)
        self.canvas.verified = t_voc_parse_reader.verified

    def load_yolo_txt_by_filename(self, txt_path):
        if self.file_path is None:
            return
        if os.path.isfile(txt_path) is False:
            return

        self.set_format(FORMAT_YOLO)
        t_yolo_parse_reader = YoloReader(txt_path, self.image)
        shapes = t_yolo_parse_reader.get_shapes()
        print(shapes)
        self.load_labels(shapes)
        self.canvas.verified = t_yolo_parse_reader.verified

    def load_create_ml_json_by_filename(self, json_path, file_path):
        if self.file_path is None:
            return
        if os.path.isfile(json_path) is False:
            return

        self.set_format(FORMAT_CREATEML)

        create_ml_parse_reader = CreateMLReader(json_path, file_path)
        shapes = create_ml_parse_reader.get_shapes()
        self.load_labels(shapes)
        self.canvas.verified = create_ml_parse_reader.verified

    def copy_previous_bounding_boxes(self):
        current_index = self.m_img_list.index(self.file_path)
        if current_index - 1 >= 0:
            prev_file_path = self.m_img_list[current_index - 1]
            self.show_bounding_box_from_annotation_file(prev_file_path)
            self.save_file()

    def copy_selected_labels_custom(self):
        """弹出对话框让用户输入复制帧数"""
        count, ok = QInputDialog.getInt(self, "自定义复制", "请输入要复制到的后续帧数:", 1, 1, 1000, 1)
        if ok:
            # 批量复制前不在这里保存快照，因为它不影响当前帧
            self.copy_selected_labels_to_next_frames(count)

    def copy_selected_labels_to_next_frames(self, count):
        """将当前选中的标签复制到后续 count 帧，并写入对应标注文件。
        不切换当前图片，仅对目标图片的标注文件进行覆盖写入。
        如果目标图片已有标注，则会被清除，只保留当前复制的框。"""
        # 选中项
        selected_items = self.label_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, '提示', '请先在右侧标签列表中选择一个或多个标签。')
            return

        # 选中形状
        selected_shapes = []
        for item in selected_items:
            if item in self.items_to_shapes:
                selected_shapes.append(self.items_to_shapes[item])
        if not selected_shapes:
            QMessageBox.information(self, '提示', '未获取到选中的标注形状。')
            return

        # 辅助：将 Shape 转为保存所需的 dict
        def format_shape(s):
            return dict(
                label=s.label,
                line_color=s.line_color.getRgb(),
                fill_color=s.fill_color.getRgb(),
                points=[(p.x(), p.y()) for p in s.points],
                difficult=getattr(s, 'difficult', False)
            )

        # 执行复制
        try:
            current_index = self.m_img_list.index(self.file_path)
        except ValueError:
            QMessageBox.warning(self, '警告', '当前文件不在图片列表中，无法定位后续帧。')
            return

        total = len(self.m_img_list)
        appended = 0
        for step in range(1, count + 1):
            idx = current_index + step
            if idx >= total:
                break
            target_img_path = self.m_img_list[idx]

            # 目标标注文件路径（考虑默认保存目录）
            if self.default_save_dir:
                base = os.path.basename(os.path.splitext(target_img_path)[0])
                xml_path = os.path.join(self.default_save_dir, base + XML_EXT)
                txt_path = os.path.join(self.default_save_dir, base + TXT_EXT)
                json_path = os.path.join(self.default_save_dir, base + JSON_EXT)
            else:
                base = os.path.splitext(target_img_path)[0]
                xml_path = base + XML_EXT
                txt_path = base + TXT_EXT
                json_path = base + JSON_EXT

            # 判定采用的格式：若已有文件则沿用其格式，否则用当前设置格式
            use_format = None
            if os.path.isfile(xml_path):
                use_format = LabelFileFormat.PASCAL_VOC
            elif os.path.isfile(txt_path):
                use_format = LabelFileFormat.YOLO
            elif os.path.isfile(json_path):
                use_format = LabelFileFormat.CREATE_ML
            else:
                use_format = self.label_file_format

            # 仅包含选中的形状（不保留目标帧原有的标注）
            shapes_to_write = [format_shape(s) for s in selected_shapes]

            # 写入目标文件
            lf = LabelFile()
            lf.verified = self.canvas.verified
            try:
                target_img_data = read(target_img_path, None)
                if use_format == LabelFileFormat.PASCAL_VOC:
                    out_path = xml_path
                    if out_path[-4:].lower() != '.xml':
                        out_path = out_path + XML_EXT
                    lf.save_pascal_voc_format(out_path, shapes_to_write, target_img_path, target_img_data,
                                              self.line_color.getRgb(), self.fill_color.getRgb())
                elif use_format == LabelFileFormat.YOLO:
                    out_path = txt_path
                    if out_path[-4:].lower() != '.txt':
                        out_path = out_path + TXT_EXT
                    lf.save_yolo_format(out_path, shapes_to_write, target_img_path, target_img_data, self.label_hist,
                                        self.line_color.getRgb(), self.fill_color.getRgb())
                elif use_format == LabelFileFormat.CREATE_ML:
                    out_path = json_path
                    if out_path[-5:].lower() != '.json':
                        out_path = out_path + JSON_EXT
                    lf.save_create_ml_format(out_path, shapes_to_write, target_img_path, target_img_data,
                                             self.label_hist, self.line_color.getRgb(), self.fill_color.getRgb())
                else:
                    # 兜底：通用保存（PascalVOC风格）
                    out_path = xml_path
                    lf.save(out_path, shapes_to_write, target_img_path, target_img_data,
                            self.line_color.getRgb(), self.fill_color.getRgb())
                appended += 1
            except Exception as e:
                # 捕获所有异常（包括权限错误、路径占用等），记录日志但不中断循环，防止闪退
                print('保存失败: {} -> {} ({})'.format(target_img_path, out_path, e))
                self.status('保存到第 {} 帧失败: 权限不足或文件被占用'.format(idx + 1))
                continue

        self.status('已覆盖并复制选中标签到后续 {} 帧，成功 {} 张'.format(count, appended))
        self.statusBar().show()

    def smart_copy_similar(self):
        selected_items = self.label_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, '提示', '请先在右侧标签列表中选择要复制的标签。')
            return
        if not self.file_path:
            return

        from libs.similarity import find_similar_range
        try:
            current_index = self.m_img_list.index(self.file_path)
        except ValueError:
            return

        similar_count, _ = find_similar_range(self.m_img_list, current_index)
        if similar_count <= 0:
            QMessageBox.information(self, '智能复制', '未检测到相似后续帧。')
            return

        ret = QMessageBox.question(
            self, '智能复制相似帧',
            f'检测到后续 {similar_count} 帧与当前帧高度相似。\n'
            f'是否将选中的 {len(selected_items)} 个标签复制到这些帧？',
            QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            self.copy_selected_labels_to_next_frames(similar_count)

    def toggle_paint_labels_option(self):
        for shape in self.canvas.shapes:
            shape.paint_label = self.display_label_option.isChecked()

    def toggle_draw_square(self):
        self.canvas.set_drawing_shape_to_square(self.draw_squares_option.isChecked())

    def update_dir_labels(self):
        """Update the directory display labels"""
        if self.image_dir_label:
            dir_path = self.dir_name
            if not dir_path and self.file_path:
                dir_path = os.path.dirname(self.file_path)
            
            if dir_path:
                self.image_dir_label.setText(f'图片目录: {dir_path}')
                self.image_dir_label.setToolTip(dir_path)
            else:
                self.image_dir_label.setText('图片目录: 未设置')
        
        if self.annotation_dir_label:
            if self.default_save_dir:
                self.annotation_dir_label.setText(f'保存目录: {self.default_save_dir}')
                self.annotation_dir_label.setToolTip(self.default_save_dir)
            else:
                self.annotation_dir_label.setText('保存目录: 未设置')
        
        # 同时更新今日总计数标签
        self.update_daily_total_label()

    def update_daily_total_label(self):
        """实时更新界面上的今日总计数标签"""
        if not hasattr(self, 'daily_total_label'):
            return
            
        stats = self.settings.get(SETTING_DAILY_STATS, {})
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        total = 0
        if stats.get('date') == today_str:
            # 计算所有路径下的图片总数
            total = sum(stats.get('paths', {}).values())
        
        self.daily_total_label.setText(f'今日总计数: {total}')

def inverted(color):
    return QColor(*[255 - v for v in color.getRgb()])


def read(filename, default=None):
    try:
        reader = QImageReader(filename)
        reader.setAutoTransform(True)
        return reader.read()
    except:
        return default


def get_main_app(argv=[]):
    """
    Standard boilerplate Qt application code.
    Do everything but app.exec_() -- so that we can test the application in one thread
    """
    app = QApplication(argv)
    app.setApplicationName(__appname__)
    app.setWindowIcon(new_icon("app"))
    # Tzutalin 201705+: Accept extra agruments to change predefined class file
    argparser = argparse.ArgumentParser()
    argparser.add_argument("image_dir", nargs="?")
    argparser.add_argument("class_file",
                           default=os.path.join(os.path.dirname(__file__), "data", "predefined_classes.txt"),
                           nargs="?")
    argparser.add_argument("save_dir", nargs="?")
    args = argparser.parse_args(argv[1:])

    args.image_dir = args.image_dir and os.path.normpath(args.image_dir)
    args.class_file = args.class_file and os.path.normpath(args.class_file)
    args.save_dir = args.save_dir and os.path.normpath(args.save_dir)

    # Apply modern UI theme
    apply_theme(app)

    # Usage : labelImg.py image classFile saveDir
    win = MainWindow(args.image_dir,
                     args.class_file,
                     args.save_dir)
    win.show()
    return app, win


def main():
    """construct main app and run it"""
    app, _win = get_main_app(sys.argv)
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main())
