import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Optional
from backend.config import settings
from backend.logger_config import logger


class OCRService:
    """OCR 服务 - 使用 QwenVL 模型进行发票识别"""
    
    def __init__(self):
        self._qwen_service = None
        self.annotations = {}
    
    @property
    def qwen_service(self):
        """延迟加载 QwenVL 服务"""
        if self._qwen_service is None:
            from backend.services.qwen_vl_service import get_qwen_service
            self._qwen_service = get_qwen_service()
        return self._qwen_service
    
    def process_image(self, image_path: str) -> Dict:
        """处理图片，使用 QwenVL 进行识别
        
        Args:
            image_path: 图片路径
            
        Returns:
            {'data': dict, 'confidence': float}
        """
        logger.info(f"[OCR] 使用 QwenVL 处理图片: {image_path}")
        return self.qwen_service.process_invoice(image_path)
    
    def process_invoice(self, image_path: str) -> Dict:
        """处理发票图片
        
        Args:
            image_path: 图片路径
            
        Returns:
            {'data': dict, 'confidence': float}
        """
        return self.process_image(image_path)


ocr_service = OCRService()


def get_ocr_service() -> OCRService:
    return ocr_service
