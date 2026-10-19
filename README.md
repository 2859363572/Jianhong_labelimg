# Jianhong LabelImg

基于 [labelImg](https://github.com/tzutalin/labelImg) 深度定制的桌面标注工具，面向视频帧、图像序列和大批量数据集场景。项目使用 PyQt5 构建，支持 Pascal VOC、YOLO 和 CreateML 标注格式，并提供批量复制、模型辅助标注、图片分流等效率功能。

> 本 README 以当前仓库代码为准。YOLO/SAM 辅助标注需要额外准备对应的 ONNX 模型文件；未配置模型时不影响基础框选标注。

## 功能概览

- **基础标注**：打开单张图片或递归扫描图片目录，创建、编辑、复制、删除矩形框，支持多选标签和标签筛选。
- **三种输出格式**：Pascal VOC（XML）、YOLO（TXT）和 CreateML（JSON），可在菜单中切换。
- **序列导航**：左侧帧列表支持搜索，中间底部提供上一帧/下一帧、滑块跳转和按帧号跳转，并显示已标注进度。
- **单目标模式**：一张图片存在多个框时选择保留目标，其他框自动移除并保存。
- **快速标注**：开启后完成当前图片标注会自动保存并进入下一张图片。
- **自动保存**：支持切换图片时自动保存，以及对标注操作自动保存。
- **批量复制**：将当前选中的一个或多个标签复制到后续 5、10、25 或自定义数量的帧，同时保留目标帧已有标注。
- **智能复制相似帧**：使用感知哈希检测连续相似帧，确认后批量复制选中的标注。
- **YOLO ONNX 预标注**：对当前图片、目录全部图片或未标注图片运行模型推理；可调置信度阈值和 NMS 阈值，可选 `classes.txt`，并显示批量处理进度。
- **SAM ONNX 半自动标注**：加载编码器和解码器模型，为当前图片提取 embedding，通过点击目标附近区域生成框。
- **图片分流**：创建最多 9 个目标类别和目录，将当前图片移动到目标目录；支持按钮、快捷键、拖放分流，重名文件会自动生成新名称。
- **主题与设置**：内置 Apple Pro、Cursor Dark、Notion Light、Stripe Light、Raycast Dark 五套主题；窗口、最近文件、格式、目录、快捷键等设置会持久化到用户目录。
- **稳定性辅助**：支持最多 10 步标注撤回、删除图片撤回、上次退出位置恢复、相邻帧预加载和图像缓存。
- **统计与检查**：记录每日打开过的图片数量，可查看每日统计；提供标注框过小、越界和空标签检查能力。

## 环境要求

- Windows、Linux 或 macOS
- Python 3.9+（建议使用 Python 3.10 或更高版本）
- PyQt5 5.15+
- 使用 YOLO/SAM ONNX 功能时，还需要 `onnxruntime`、Pillow 和 NumPy

## 快速开始

### 方式一：运行已打包程序

如果已有发布产物，直接运行：

```text
release/labelImg.exe
```

### 方式二：从源码运行

在仓库根目录执行：

```bash
git clone http://10.234.115.20:3000/liujianhong/labelimg.git
cd labelimg

python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Windows CMD：.venv\Scripts\activate.bat

python -m pip install -r requirements.txt
# YOLO/SAM ONNX 功能的额外依赖
python -m pip install onnxruntime

python run.py
```

也可以直接向启动脚本传入图片目录、预定义类别文件和标注输出目录：

```bash
python run.py <image_dir> [class_file] [save_dir]
```

例如：

```bash
python run.py .\images .\data\predefined_classes.txt .\annotations
```

### 基础标注流程

1. 运行程序后点击 `Open Dir`，选择图片目录；也可以使用 `Open` 打开单张图片。
2. 使用 `Change Save Dir` 设置标注输出目录；不设置时，标注文件默认与图片同目录保存。
3. 在 `File -> Save Format` 中选择 Pascal VOC、YOLO 或 CreateML。
4. 按 `W` 进入画框模式，在图片上拖拽创建矩形框并输入标签。
5. 使用 `Ctrl+S` 保存；开启自动保存后可减少手动保存操作。
6. 左侧可以搜索帧或按帧号跳转，右侧标签列表支持多选，便于批量复制。

## 高效标注功能

### 单目标和快速标注

- 在右侧 `Annotations` 面板勾选 `单目标模式`：打开包含多个标注框的图片时，选择要保留的目标，其余框会移除并保存。
- 勾选 `快速标注`：当前图片完成标注后自动保存并进入下一帧。建议与默认标签、单类模式配合使用。

### 复制标签到后续帧

1. 在右侧标签列表中选择一个或多个对象。
2. 通过 `Edit` 菜单或快捷键执行复制：
   - `Alt+5`：复制到后续 5 帧
   - `Alt+0`：复制到后续 10 帧
   - `Alt+2`：复制到后续 25 帧
   - `Alt+C`：输入自定义帧数
3. 程序按目标图片已有格式写入标注文件，并避免重复写入相同的标签和框。

### YOLO ONNX 预标注

1. 打开 `File -> YOLO 模型预标注`，或按 `Ctrl+Y`。
2. 选择 `.onnx` 模型；如模型类别顺序需要外部映射，可额外选择每行一个类别名的 `classes.txt`。
3. 调整置信度阈值和 NMS 阈值。
4. 选择范围：`当前图片`、`目录全部图片` 或 `未标注图片`。
5. 点击 `开始预标注`。当前打开的图片会把检测结果载入画布，确认后请按项目选定格式保存；目录级推理会显示处理进度。

### SAM ONNX 半自动标注

1. 打开 `File -> SAM 半自动标注`，或按 `Ctrl+Shift+Y`。
2. 分别选择 SAM 编码器和解码器的 `.onnx` 文件。
3. 点击 `嵌入当前图片`，等待状态显示嵌入完成。
4. 在画布上点击目标附近区域，程序基于该位置周围的提示框生成标注框；随后输入标签并按所选格式保存。

### 图片分流

1. 切换右侧面板的 `Image Routing` 标签，点击 `Add`，为类别设置名称和目标目录。
2. 当前图片可以通过以下方式分流：
   - 点击对应的目标按钮；
   - 使用 `Ctrl+Alt+1` 至 `Ctrl+Alt+9`；
   - 在画布上右键双击后拖到目标按钮；
   - 将当前图片拖到目标按钮。
3. 分流会移动原图片并从当前帧列表移除；如目标目录存在同名文件，程序会自动追加序号，不会直接覆盖。
4. 在目标按钮上打开右键菜单，可以修改名称、修改目录或删除类别。

## 常用快捷键

| 操作 | 快捷键 |
| :--- | :--- |
| 打开文件 / 打开目录 | `Ctrl+O` / `Ctrl+U` |
| 修改标注保存目录 | `Ctrl+R` |
| 保存 / 另存为 | `Ctrl+S` / `Ctrl+Shift+S` |
| 创建框 | `W` |
| 编辑框 | `Ctrl+J` |
| 删除选中框 | `Delete` / `F` |
| 复制选中框 | `Ctrl+D` |
| 撤回上一步 | `Ctrl+Z` |
| 上一张 / 下一张 | `A` / `D` |
| 验证当前图片 | `Space` |
| YOLO 预标注 | `Ctrl+Y` |
| SAM 半自动标注 | `Ctrl+Shift+Y` |
| 智能复制相似帧 | `Alt+S` |
| 复制到后续 5/10/25 帧 | `Alt+5` / `Alt+0` / `Alt+2` |
| 自定义复制到后续 N 帧 | `Alt+C` |
| 放大 / 缩小 / 原始大小 | `Ctrl++` / `Ctrl+-` / `Ctrl+=` |
| 适应窗口 / 适应宽度 | `Ctrl+F` / `Ctrl+Shift+F` |
| 切换标签显示 | `Ctrl+Shift+P` |
| 切换方形绘制 | `Ctrl+Shift+R` |
| 显示/隐藏标签面板 | `Ctrl+Shift+L` |
| 切换高级模式 | `Ctrl+Shift+A` |
| 图片分流到第 1–9 类别 | `Ctrl+Alt+1` … `Ctrl+Alt+9` |

快捷键可以在 `Help -> 自定义快捷键` 中调整；`Ctrl+Z` 始终保留为撤回操作。

## 打包 Windows 可执行文件

项目提供 `labelImg.spec`，建议在仓库根目录使用当前 Python 环境执行：

```bash
python -m pip install -r requirements.txt
python -m pip install onnxruntime
python -m pip install pyinstaller
pyinstaller labelImg.spec
```

构建完成后，可执行文件通常位于 `dist/labelImg.exe`。spec 文件会收集 `img/` 资源、PyQt5 Qt 运行库、`libs` 子模块，并将 `onnxruntime` 和 `xxhash` 作为隐藏导入；如果不需要模型功能，可以按实际环境调整构建配置。

## 项目结构

```text
labelImg/
├── labelImg/              # 主窗口和程序入口
│   └── labelImg.py
├── libs/                  # 标注格式、画布、设置、主题、模型等模块
│   ├── canvas.py
│   ├── labelFile.py
│   ├── sam_*.py
│   ├── yolo_*.py
│   ├── similarity.py
│   └── theme.py
├── img/                   # 图标和界面资源
├── tools/                 # 辅助工具
├── run.py                 # 源码启动入口
├── requirements.txt       # Python 依赖
├── labelImg.spec          # PyInstaller 构建配置
└── README.md
```

运行时设置默认保存在用户目录下的 `.labelImgSettings.pkl`。该文件包含窗口、最近文件、主题和标注偏好等本地配置，不应提交到仓库。

## 注意事项

- YOLO 和 SAM 功能依赖兼容的 ONNX 模型；模型输入输出格式应与项目中的 predictor 实现匹配。
- 批量复制会写入后续帧的标注文件，执行前请确认当前输出目录和选中标签。
- 图片分流是移动文件操作，建议在执行前确认目标目录和备份策略。
- `requirements.txt` 中的 `matplotlib`、`pandas`、`seaborn` 等依赖主要用于扩展或数据处理，不是基础 GUI 启动的全部必要条件。
- 主题、快捷键、自动保存等设置会持久化到当前用户配置文件。

## 许可证

本项目基于 MIT License。原始 labelImg 项目及其相关组件请同时遵循各自的许可证和版权声明。
