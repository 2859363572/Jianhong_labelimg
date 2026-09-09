# 项目结构

## 保留层

- `labelImg/`: 主窗口与业务入口
- `libs/`: 共享 UI、标注、格式、配置和工具逻辑
- `img/`: 图标和少量静态资源
- `run.py`: 本地启动入口
- `labelImg.spec`: PyInstaller 打包入口
- `requirements.txt`: 依赖清单
- `release/`: 当前稳定发布包
- `docs/`: 说明、结构、迭代和打包流程

## 一次性层

- `build-*/` 和 `dist-*/`: 历史打包缓存和试验产物
- `*_extracted/`: exe 解包目录，禁止保留在仓库
- `__pycache__/` 和 `*.pyc`: Python 缓存
- `node_cache/`: 本地工具缓存
- `nul`: Windows 残留设备名，不应作为项目文件存在

## 迭代原则

1. 所有源码变更只进 `labelImg/` 或 `libs/`。
2. 所有发布物只进 `release/`。
3. 所有临时构建只放在 `build-*` / `dist-*`，完成后立即清理。
4. 任何新文档先放 `docs/`，不要再堆到根目录。
