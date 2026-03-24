from math import sqrt
from libs.ustr import ustr
import hashlib
import xxhash
import re
import sys
import colorsys
import random

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
    QT5 = True
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
    QT5 = False


def new_icon(icon):
    return QIcon(':/' + icon)


def new_button(text, icon=None, slot=None):
    b = QPushButton(text)
    if icon is not None:
        b.setIcon(new_icon(icon))
    if slot is not None:
        b.clicked.connect(slot)
    return b


def new_action(parent, text, slot=None, shortcut=None, icon=None,
               tip=None, checkable=False, enabled=True):
    """Create a new action and assign callbacks, shortcuts, etc."""
    a = QAction(text, parent)
    if icon is not None:
        a.setIcon(new_icon(icon))
    if shortcut is not None:
        if isinstance(shortcut, (list, tuple)):
            a.setShortcuts(shortcut)
        else:
            a.setShortcut(shortcut)
    if tip is not None:
        a.setToolTip(tip)
        a.setStatusTip(tip)
    if slot is not None:
        a.triggered.connect(slot)
    if checkable:
        a.setCheckable(True)
    a.setEnabled(enabled)
    return a


def add_actions(widget, actions):
    for action in actions:
        if action is None:
            widget.addSeparator()
        elif isinstance(action, QMenu):
            widget.addMenu(action)
        else:
            widget.addAction(action)


def label_validator():
    return QRegExpValidator(QRegExp(r'^[^ \t].+'), None)


class Struct(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def distance(p):
    return sqrt(p.x() * p.x() + p.y() * p.y())


def format_shortcut(text):
    mod, key = text.split('+', 1)
    return '<b>%s</b>+<b>%s</b>' % (mod, key)


def generate_color_by_text(text):
    """
    使用预定义的鲜艳颜色表，确保高对比度和视觉效果
    """
    # 鲜艳颜色表 - 高饱和度，适中明度
    vibrant_colors = [
        (255, 0, 0),     # 鲜红色
        (0, 255, 0),     # 鲜绿色
        (0, 0, 255),     # 鲜蓝色
        (255, 255, 0),   # 鲜黄色
        (255, 0, 255),   # 鲜品红色
        (0, 255, 255),   # 鲜青色
        (255, 165, 0),   # 鲜橙色
        (128, 0, 128),   # 鲜紫色
        (255, 20, 147),  # 深粉红色
        (0, 191, 255),   # 深天蓝色
        (50, 205, 50),   # 酸橙绿色
        (255, 69, 0),    # 橙红色
        (138, 43, 226),  # 蓝紫色
        (255, 140, 0),   # 深橙色
        (220, 20, 60),   # 深红色
        (0, 206, 209),   # 深绿松石色
        (255, 215, 0),   # 金色
        (218, 112, 214), # 兰花紫
        (127, 255, 0),   # 春绿色
        (255, 105, 180)  # 热粉红色
    ]
    
    # 使用哈希确保颜色分布均匀
    s = str(text)
    hash_code = xxhash.xxh32(s.encode('utf-8')).intdigest()
    idx = hash_code % len(vibrant_colors)
    r, g, b = vibrant_colors[idx]
    
    # 返回QColor对象，透明度设置为180
    return QColor(r, g, b, 180)


def have_qstring():
    """p3/qt5 get rid of QString wrapper as py3 has native unicode str type"""
    return not (sys.version_info.major >= 3 or QT_VERSION_STR.startswith('5.'))


def util_qt_strlistclass():
    return QStringList if have_qstring() else list


def natural_sort(list, key=lambda s:s):
    """
    Sort the list into natural alphanumeric order.
    """
    def get_alphanum_key_func(key):
        convert = lambda text: int(text) if text.isdigit() else text
        return lambda s: [convert(c) for c in re.split('([0-9]+)', key(s))]
    sort_key = get_alphanum_key_func(key)
    list.sort(key=sort_key)


# QT4 has a trimmed method, in QT5 this is called strip
if QT5:
    def trimmed(text):
        return text.strip()
else:
    def trimmed(text):
        return text.trimmed()
