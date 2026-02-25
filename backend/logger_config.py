import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

# 使用绝对路径
LOG_DIR = Path("/root/autodl-tmp/caiwubaoxiao/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"

# 创建格式化器 - 中文格式
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 文件处理器
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# 配置根日志
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

# 应用日志器
logger = logging.getLogger("财务审核系统")

# 记录启动日志
logger.info("=" * 50)
logger.info("日志系统初始化完成")
logger.info(f"日志文件路径: {LOG_FILE}")
logger.info("=" * 50)
