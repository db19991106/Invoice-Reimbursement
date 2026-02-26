import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Optional
from backend.config import settings
from backend.logger_config import logger


class OCRService:
    """OCR 服务 - 使用统一的 VL 服务进行发票识别
    
    注：此服务现在只是统一 VL 服务的包装器，保持向后兼容
    """
    
    def __init__(self):
        self._vl_service = None
        self.annotations = {}
    
    @property
    def vl_service(self):
        """延迟加载统一 VL 服务"""
        if self._vl_service is None:
            from backend.services.unified_vl_service import get_unified_vl_service
            self._vl_service = get_unified_vl_service()
        return self._vl_service
    
    def process_image(self, image_path: str) -> Dict:
        """处理图片，使用统一 VL 服务进行识别
        
        Args:
            image_path: 图片路径
            
        Returns:
            {'data': dict, 'confidence': float}
        """
        logger.info(f"[OCR] 使用统一 VL 服务处理图片: {image_path}")
        return self.vl_service.process_invoice(image_path)
    
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
