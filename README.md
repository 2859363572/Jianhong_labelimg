# Jianhong_labelimg

基于 `labelImg` 深度定制的高效率标注工具，面向视频序列和大批量数据集场景。

## 核心特性

| 模块 | 功能 |
| :--- | :--- |
| 标注模式 | 单目标/多目标切换（单目标下自动约束仅保留一个框） |
| 快速流 | 快速标注模式（自动保存 + 自动下一帧） |
| 预标注 | YOLO ONNX 预标注（当前图/全目录/仅未标注） |
| 半自动 | SAM ONNX 半自动标注（点击目标生成框） |
| 批处理 | 复制选中框到后续 N 帧（5/10/25/自定义） |
| 智能复制 | 相似帧检测后批量复制（感知哈希） |
| 数据格式 | Pascal VOC / YOLO / CreateML |
| 稳定性 | 10步撤回、异常保护、设置持久化 |

## 快速开始

### 方式一：直接运行

使用打包产物：`dist/labelImg.exe`

### 方式二：源码运行

```bash
git clone https://github.com/2859363572/Jianhong_labelimg.git
cd Jianhong_labelimg

python -m venv .venv
.\.venv\Scripts\activate

pip install -r requirements.txt
pip install onnxruntime

python run.py
```

## 使用说明

### 1) 基础标注

1. `Open Dir` 选择图像目录
2. `Change Save Dir` 选择标注保存目录
3. 选择输出格式（VOC/YOLO/CreateML）
4. `W` 进入画框模式

### 2) 单目标模式

- 勾选右侧 `单目标模式`
- 当切换到多框帧时，会弹窗选择保留目标，其他框自动删除并保存

### 3) 快速标注流

- 勾选 `快速标注`
- 搭配默认标签/单类模式，可形成连续高效标注流程

### 4) YOLO 预标注

- 菜单：`文件 -> YOLO 模型预标注`（`Ctrl+Y`）
- 选择 `.onnx` 模型（可选 `classes.txt`）
- 选择作用范围并执行

### 5) SAM 半自动标注

- 菜单：`文件 -> SAM 半自动标注`（`Ctrl+Shift+Y`）
- 选择 SAM 编码器与解码器 ONNX
- 对当前图片做 embedding 后，在画布点击目标区域生成标注

### 6) 智能复制相似帧

- 在当前帧选择要复制的框
- 菜单：`编辑 -> 智能复制相似帧`（`Alt+S`）
- 系统自动检测后续相似帧并确认复制范围

## 常用快捷键

| 动作 | 快捷键 |
| :--- | :--- |
| 创建框 | `W` |
| 下一张 | `D` |
| 上一张 | `A` |
| 删除选中框 | `Del` / `F` |
| 撤回 | `Ctrl+Z` |
| YOLO 预标注 | `Ctrl+Y` |
| SAM 半自动标注 | `Ctrl+Shift+Y` |
| 智能复制相似帧 | `Alt+S` |
| 复制到下5/10/25帧 | `Alt+5` / `Alt+0` / `Alt+2` |
| 自定义复制到下N帧 | `Alt+C` |

## 打包

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --name labelImg --icon "img/1.ico" --hidden-import onnxruntime run.py
```

输出文件：`dist/labelImg.exe`

## 目录结构

```
Jianhong_labelimg/
├── labelImg/
│   └── labelImg.py
├── libs/
│   ├── canvas.py
│   ├── shape.py
│   ├── yolo_predictor.py
│   ├── yolo_predict_dialog.py
│   ├── similarity.py
│   ├── sam_predictor.py
│   └── sam_dialog.py
├── img/
├── run.py
└── README.md
```

## 许可证

本项目基于 MIT License。
