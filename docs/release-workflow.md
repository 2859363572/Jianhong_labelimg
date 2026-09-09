# 发布流程

## 当前约定

- 最终可用产物存放在 `release/labelImg.exe`
- 打包时使用根目录的 `labelImg.spec`
- 资源图标保留 `img/labelimg.ico`

## 推荐步骤

1. 修改 `labelImg/labelImg.py` 和相关 `libs/*.py`。
2. 本地运行 `python -m py_compile ...` 和导入 smoke test。
3. 使用 `PyInstaller` 输出到新的临时 `dist-*` 目录。
4. 验证后把最终 exe 复制到 `release/labelImg.exe`。
5. 删除旧 `build-*`、`dist-*` 和反编译目录。

## 禁止保留

- 历史 `dist-*` / `build-*`
- `*_extracted/`
- 临时预览图和缓存
- 旧版本测试 exe
