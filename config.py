import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).parent

# 输出目录
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# MIMO API
MIMO_API_KEY = os.getenv("MIMO_API_KEY", "")
MIMO_BASE_URL = os.getenv("MIMO_BASE_URL", "https://api.siliconflow.cn/v1")
MIMO_MODEL = os.getenv("MIMO_MODEL", "Qwen/MiMo-7B-RL")

# 即梦 API（火山引擎 AK/SK）
JIMENG_AK = os.getenv("JIMENG_AK", "")
JIMENG_SK = os.getenv("JIMENG_SK", "")

# CSDN Cookie
CSDN_COOKIE = os.getenv("CSDN_COOKIE", "")

# LLM 默认参数
LLM_TEMPERATURE = 0.6
LLM_MAX_TOKENS = 8192
