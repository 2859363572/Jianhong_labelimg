import sys
import os

# 将 .venv 中的库路径加入 sys.path
venv_path = os.path.join(os.getcwd(), '.venv', 'Lib', 'site-packages')
sys.path.append(venv_path)

# 导入 labelImg 并运行
from labelImg.labelImg import main
if __name__ == '__main__':
    sys.exit(main())
