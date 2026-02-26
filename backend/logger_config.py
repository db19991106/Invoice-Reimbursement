import logging
import os
import sys
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

# 文件处理器 - 禁用缓冲，立即写入
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8',
    delay=False  # 立即打开文件
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# 控制台处理器 - 禁用缓冲
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)
console_handler.stream = os.fdopen(console_handler.stream.fileno(), 'w', buffering=1)  # 行缓冲

# 配置根日志
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# 应用日志器
logger = logging.getLogger("财务审核系统")

# 记录启动日志
logger.info("=" * 50)
logger.info("日志系统初始化完成")
logger.info(f"日志文件路径: {LOG_FILE}")
logger.info("=" * 50)
