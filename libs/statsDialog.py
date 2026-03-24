
try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

from datetime import datetime

class StatisticsDialog(QDialog):
    def __init__(self, stats_data, parent=None):
        super(StatisticsDialog, self).__init__(parent)
        self.setWindowTitle("每日图片统计明细")
        self.resize(600, 400)
        
        layout = QVBoxLayout()
        
        # 标题和日期
        today = datetime.now().strftime("%Y-%m-%d")
        header = QLabel(f"当日统计 ({today})")
        header.setObjectName("StatsHeader")
        layout.addWidget(header)
        
        # 说明
        info = QLabel("注：统计数据每日凌晨 12:00 自动清空。相同路径下的图片将分组计数。")
        info.setObjectName("StatsInfo")
        layout.addWidget(info)

        # 表格显示明细
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["目录路径", "图片数量"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        
        layout.addWidget(self.table)
        
        # 总计显示
        self.total_label = QLabel("总计计数: 0")
        self.total_label.setObjectName("StatsTotal")
        layout.addWidget(self.total_label)
        
        # 底部按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        self.update_stats(stats_data)

    def update_stats(self, stats_data):
        """
        stats_data 结构示例:
        {
            'date': '2024-03-24',
            'paths': {
                'D:/Images/Set1': 50,
                'D:/Images/Set2': 30
            },
            'total': 80
        }
        """
        if not stats_data or 'paths' not in stats_data:
            self.table.setRowCount(0)
            self.total_label.setText("总计计数: 0")
            return
            
        paths = stats_data['paths']
        self.table.setRowCount(len(paths))
        
        total = 0
        for row, (path, count) in enumerate(paths.items()):
            self.table.setItem(row, 0, QTableWidgetItem(path))
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, count_item)
            total += count
            
        self.total_label.setText(f"总计计数: {total}")
