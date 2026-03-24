import sys
import os

# 导入 labelImg 并运行
try:
    from labelImg.labelImg import main
except ImportError:
    # 兼容旧版本结构或直接运行
    from labelImg import main

if __name__ == '__main__':
    sys.exit(main())
