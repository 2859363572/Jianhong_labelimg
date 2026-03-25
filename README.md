# Jianhong_labelimg

<div align="center">
  <img src="https://raw.githubusercontent.com/tzutalin/labelImg/master/resources/icons/app.png" width="100">
  <h3>AI 驱动的高级图像标注工具</h3>
  <p>轻量级 | 多格式支持 | 自动化统计 | 自定义快捷键 | 撤回机制</p>
  
  <p>
    <a href="https://github.com/2859363572/Jianhong_labelimg">简体中文</a> ·
    <a href="https://github.com/2859363572/Jianhong_labelimg">English</a>
  </p>
</div>

---

## 项目亮点

| 功能 | 描述 |
| :--- | :--- |
| **每日工作量统计** | 自动记录每日标注数量，每日零点重置 |
| **批量帧复制** | Alt+5/0/2 快速复制标注到后续 5/10/25 帧 |
| **跳过OK确认** | 启用后可直接完成标注，无需每次点击确认 |
| **预设标签** | 预先设置常用标签，标注时快速切换选择 |
| **10步高精度撤回** | 支持多步历史记录恢复 |
| **自定义快捷键** | 灵活配置个性化快捷键方案 |
| **多格式支持** | Pascal VOC / YOLO / CreateML |
| **防崩溃保护** | IO异常捕捉，友好错误提示 |

## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [快捷键参考](#快捷键参考)
- [目录结构](#目录结构)
- [打包说明](#打包说明)
- [许可证](#许可证)

## 项目简介

**Jianhong_labelimg** 是一款基于经典开源工具 `labelImg` 深度定制的增强版图像标注软件。它针对大规模标注场景进行了多项优化，特别适合需要批量处理图像的 AI 训练数据准备工作。

## 核心特性

### 快速标注模式
- **跳过OK确认**: 勾选后可直接完成标注，显著提升标注效率
- **预设标签**: 预先配置常用标签，标注时快速切换

### 智能统计
- **每日工作量统计**: 实时显示当日标注数量
- **分组明细**: 按图片路径自动分组统计
- **每日零点重置**: 统计数据每日自动清零

### 批量处理
- **批量帧复制**: 使用 `Alt+5/0/2` 将当前标注快速复制到后续 5/10/25 帧
- **覆盖模式**: 自动清空目标帧原有标注，避免重复

### 数据安全
- **多步撤回**: 支持 10 步操作历史恢复
- **异常保护**: IO错误友好提示，防止意外崩溃
- **状态持久化**: 标签列表和设置自动保存

## 快速开始

### 方式一：使用预编译版本

下载 `labelImg.exe` 或 `labelImg_plus.exe` 直接运行。

### 方式二：从源码运行

```bash
# 克隆项目
git clone https://github.com/2859363572/Jianhong_labelimg.git
cd Jianhong_labelimg

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Windows)
.\.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动程序
python run.py
```

## 使用指南

### 基本操作

1. 点击 **Open Dir** 选择图像目录
2. 点击 **Change Save Dir** 选择标注文件保存目录
3. 选择输出格式（Pascal VOC / YOLO / CreateML）
4. 使用快捷键 `W` 创建标注框
5. 按 `Ctrl+S` 保存标注

### 快速标注模式

1. 勾选 "跳过OK确认" 复选框
2. 在预设标签下拉框中选择标签
3. 直接绘制标注框，标签自动应用

### 设置预设标签

点击菜单 **帮助** → **设置预设标签**，输入常用标签（每行一个），点击确定保存。

## 快捷键参考

| 动作 | 快捷键 | 说明 |
| :--- | :--- | :--- |
| 创建选框 | `W` | 进入画框模式 |
| 下一张 | `D` | 保存并加载下一张 |
| 上一张 | `A` | 保存并加载上一张 |
| 删除选框 | `Del` / `F` | 删除当前选中标注 |
| 撤回 | `Ctrl+Z` | 回退操作（支持10步） |
| 全选 | `Ctrl+A` | 选择所有标注 |
| 缩放适应 | `Ctrl+0` | 自适应窗口 |
| 放大 | `Ctrl++` | 放大图像 |
| 缩小 | `Ctrl+-` | 缩小图像 |
| 批量复制5帧 | `Alt+5` | 复制到后续5帧 |
| 批量复制10帧 | `Alt+0` | 复制到后续10帧 |
| 批量复制25帧 | `Alt+2` | 复制到后续25帧 |
| 查看统计 | `Ctrl+Shift+S` | 打开统计对话框 |
| 自定义快捷键 | `Ctrl+H` | 打开快捷键配置 |

## 目录结构

```
Jianhong_labelimg/
├── labelImg/              # 主程序包
│   └── labelImg.py        # 核心窗口和逻辑
├── libs/                  # 组件库
│   ├── canvas.py          # 画布组件
│   ├── labelDialog.py     # 标签对话框
│   ├── statsDialog.py     # 统计对话框
│   ├── shortcutDialog.py  # 快捷键配置
│   ├── settings.py        # 设置管理
│   ├── shape.py           # 标注形状
│   ├── pascal_voc_io.py   # VOC格式读写
│   ├── yolo_io.py         # YOLO格式读写
│   └── create_ml_io.py    # CreateML格式读写
├── img/                   # 图标资源
├── run.py                 # 启动入口
├── requirements.txt       # 依赖清单
└── README.md              # 项目文档
```

## 打包说明

```bash
# 安装PyInstaller
pip install pyinstaller

# 打包（无控制台窗口）
pyinstaller run.spec

# 或使用快捷打包
pyinstaller run.py -wD -i "img/market-bull.ico"
```

打包完成后，可执行文件位于 `dist/labelImg/` 目录下。

## 技术栈

- **GUI框架**: PyQt5
- **图像处理**: Pillow
- **数据格式**: lxml (XML), pickle (设置)
- **打包工具**: PyInstaller

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

<div align="center">
  <p>Made with ❤️ by Jianhong</p>
  <p>如果这个项目对你有帮助，请考虑给它一个 ⭐ Star！</p>
</div>
