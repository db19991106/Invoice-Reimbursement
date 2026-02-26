import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    PROJECT_NAME: str = "财务报销智能审核系统"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    DATABASE_PATH: Path = DATA_DIR / "invoices.db"
    FAISS_INDEX_DIR: Path = DATA_DIR / "faiss_index"
    
    MODEL_DIR: Path = Path("/root/autodl-tmp/models")
    QWEN_VL_MODEL: str = "Qwen2.5-VL-7B-Instruct"
    QWEN_LLM_MODEL: str = "Qwen2.5-7B-Instruct"
    
    INVOICE_DATA_DIR: Path = Path("/root/autodl-tmp/caiwubaoxiao/zzsfp")
    SIGNATURE_DATA_DIR: Path = Path("/root/autodl-tmp/caiwubaoxiao/ChiSig")
    
    OCR_LANG: str = "ch"
    OCR_USE_GPU: bool = True
    
    # vLLM 配置
    # 设为 True 启用 vLLM 加速（推理速度更快，加载时间较长）
    # 设为 False 使用 Transformers（加载快，推理较慢）
    USE_VLLM: bool = os.getenv("USE_VLLM", "true").lower() == "true"
    
    # 合并 OCR + LLM 分析（一次推理完成两项任务，加速 20-30%）
    USE_COMBINED_OCR_LLM: bool = os.getenv("USE_COMBINED_OCR_LLM", "true").lower() == "true"
    
    RISK_THRESHOLDS: dict = {
        "low": 0.3,
        "medium": 0.6,
        "high": 0.8
    }
    
    def __init__(self):
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
