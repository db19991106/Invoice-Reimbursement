import os
import cv2
import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class StampDetectionResult:
    has_stamp: bool
    confidence: float
    stamp_area_ratio: float
    stamp_positions: list
    message: str


class StampDetector:
    def __init__(self):
        self.red_lower1 = np.array([0, 100, 100])
        self.red_upper1 = np.array([10, 255, 255])
        self.red_lower2 = np.array([160, 100, 100])
        self.red_upper2 = np.array([180, 255, 255])
        self.min_stamp_area = 5000
        self.max_stamp_area_ratio = 0.3
    
    def detect_stamp(self, image_path: str) -> StampDetectionResult:
        if not os.path.exists(image_path):
            return StampDetectionResult(
                has_stamp=False,
                confidence=0.0,
                stamp_area_ratio=0.0,
                stamp_positions=[],
                message="图片文件不存在"
            )
        
        try:
            img = cv2.imread(image_path)
            if img is None:
                return StampDetectionResult(
                    has_stamp=False,
                    confidence=0.0,
                    stamp_area_ratio=0.0,
                    stamp_positions=[],
                    message="无法读取图片"
                )
            
            h, w = img.shape[:2]
            total_area = h * w
            
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            mask1 = cv2.inRange(hsv, self.red_lower1, self.red_upper1)
            mask2 = cv2.inRange(hsv, self.red_lower2, self.red_upper2)
            red_mask = mask1 + mask2
            
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
            red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
            
            contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            stamp_contours = []
            stamp_positions = []
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < self.min_stamp_area:
                    continue
                
                x, y, cw, ch = cv2.boundingRect(contour)
                aspect_ratio = float(cw) / ch if ch > 0 else 0
                
                if 0.5 <= aspect_ratio <= 2.0:
                    stamp_contours.append(contour)
                    stamp_positions.append({
                        "x": int(x),
                        "y": int(y),
                        "width": int(cw),
                        "height": int(ch),
                        "area": int(area)
                    })
            
            if not stamp_contours:
                return StampDetectionResult(
                    has_stamp=False,
                    confidence=0.2,
                    stamp_area_ratio=0.0,
                    stamp_positions=[],
                    message="未检测到红色印章"
                )
            
            total_stamp_area = sum(c['area'] for c in stamp_positions)
            stamp_area_ratio = total_stamp_area / total_area
            
            confidence = min(0.5 + 0.5 * len(stamp_contours), 0.99)
            
            if stamp_area_ratio > self.max_stamp_area_ratio:
                confidence *= 0.8
            
            if confidence > 0.7:
                message = f"检测到 {len(stamp_contours)} 个印章"
            else:
                message = "印章检测结果不确定"
            
            return StampDetectionResult(
                has_stamp=len(stamp_contours) > 0,
                confidence=confidence,
                stamp_area_ratio=stamp_area_ratio,
                stamp_positions=stamp_positions,
                message=message
            )
            
        except Exception as e:
            return StampDetectionResult(
                has_stamp=False,
                confidence=0.0,
                stamp_area_ratio=0.0,
                stamp_positions=[],
                message=f"印章检测失败: {str(e)}"
            )
    
    def preprocess_for_ocr(self, image_path: str) -> Tuple[Optional[np.ndarray], StampDetectionResult]:
        stamp_result = self.detect_stamp(image_path)
        
        if not os.path.exists(image_path):
            return None, stamp_result
        
        img = cv2.imread(image_path)
        if img is None:
            return None, stamp_result
        
        if stamp_result.has_stamp:
            try:
                mask = np.zeros(img.shape[:2], dtype=np.uint8)
                
                for pos in stamp_result.stamp_positions:
                    x, y, w, h = pos['x'], pos['y'], pos['width'], pos['height']
                    cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)
                
                img_inpainted = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
                return img_inpainted, stamp_result
            except Exception:
                return img, stamp_result
        
        return img, stamp_result


stamp_detector = StampDetector()


def get_stamp_detector() -> StampDetector:
    return stamp_detector
