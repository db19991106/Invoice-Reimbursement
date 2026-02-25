import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 必须在任何 Paddle 相关导入之前设置这些环境变量
os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['FLAGS_enable_onednn'] = '0'
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

import re
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import numpy as np
from PIL import Image
from backend.config import settings


class InvoiceOCR:
    def __init__(self, enable_preprocessing: bool = True):
        from paddleocr import PaddleOCR
        self.ocr = PaddleOCR(
            use_doc_orientation_classify=enable_preprocessing,
            use_doc_unwarping=enable_preprocessing,
            use_textline_orientation=enable_preprocessing,
            lang=settings.OCR_LANG
        )
        self.ocr_version = "PP-OCRv5"
        self.enable_preprocessing = enable_preprocessing
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """图像预处理：印章去除"""
        import cv2
        
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        h, w = img.shape[:2]
        
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = mask1 + mask2
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
        
        if cv2.countNonZero(red_mask) > h * w * 0.01:
            try:
                img = cv2.inpaint(img, red_mask, 3, cv2.INPAINT_TELEA)
            except:
                pass
        
        return img
    
    def extract_amount(self, text: str) -> Optional[float]:
        """提取金额"""
        patterns = [
            r'[￥¥￥]\s*(\d{1,10}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,10}(?:,\d{3})*(?:\.\d{2})?)\s*元',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    if 0 < amount < 1000000:
                        return amount
                except:
                    continue
        return None
    
    def extract_tax_id(self, text: str) -> Optional[str]:
        """提取税号"""
        patterns = [
            r'([0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10})',
            r'\b(\d{15})\b',
            r'\b(\d{20})\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, text.upper())
            if match:
                tax_id = match.group(1)
                if len(tax_id) == 18:
                    if tax_id[0:2] in ['11', '12', '13', '14', '15', '21', '22', '23', '31', '32', '33', '34', '35', '36', '37', '41', '42', '43', '44', '45', '46', '50', '51', '52', '53', '54', '61', '62', '63', '64', '65']:
                        return tax_id
                else:
                    return tax_id
        return None
    
    def extract_date(self, text: str) -> Optional[str]:
        """提取日期"""
        patterns = [
            r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})[日]?',
            r'(\d{4})(\d{2})(\d{2})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                if 2000 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                    return f"{year}-{month:02d}-{day:02d}"
        return None
    
    def extract_invoice_no(self, text: str) -> Optional[str]:
        """提取发票号码，限定8位"""
        patterns = [
            r'[发票号No№nO]{1,3}[：:\s]*(\d{8})',
            r'^(\d{8})$',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        match = re.search(r'(\d{8})', text)
        if match and '金额' not in text and '税额' not in text:
            return match.group(1)
        
        return None
    
    def parse_ocr_result(self, ocr_result) -> Tuple[List[Dict], int]:
        """解析OCR结果"""
        text_data = []
        image_height = 0
        
        for item in ocr_result:
            if hasattr(item, 'json') and 'res' in item.json:
                res = item.json['res']
                rec_texts = res.get('rec_texts', [])
                rec_scores = res.get('rec_scores', [])
                rec_boxes = res.get('rec_boxes', [])
                
                for text, score, box in zip(rec_texts, rec_scores, rec_boxes):
                    if text and text.strip():
                        y_center = (box[1] + box[3]) // 2
                        x_center = (box[0] + box[2]) // 2
                        image_height = max(image_height, box[3])
                        
                        text_data.append({
                            'text': text,
                            'confidence': float(score) if score else 0.9,
                            'y': y_center,
                            'x': x_center,
                            'box': box
                        })
        
        return text_data, image_height
    
    def validate_and_fix_amounts(self, result: Dict) -> Dict:
        """校验并修正金额关系"""
        amount = result.get('amount')
        tax_amount = result.get('tax_amount')
        total_amount = result.get('total_amount')
        
        if total_amount and amount and tax_amount:
            expected_total = round(amount + tax_amount, 2)
            if abs(total_amount - expected_total) < 0.1:
                return result
        
        if total_amount and amount:
            result['tax_amount'] = round(total_amount - amount, 2)
        elif total_amount and tax_amount:
            result['amount'] = round(total_amount - tax_amount, 2)
        elif amount and tax_amount:
            result['total_amount'] = round(amount + tax_amount, 2)
        
        if result.get('amount') and result.get('total_amount'):
            if result['amount'] > result['total_amount']:
                result['amount'], result['total_amount'] = result['total_amount'], result['amount']
                result['tax_amount'] = round(result['total_amount'] - result['amount'], 2)
        
        return result
    
    def extract_fields(self, text_data: List[Dict], image_height: int = 3120) -> Dict:
        """从OCR结果中提取关键字段"""
        
        result = {
            'invoice_no': None,
            'date': None,
            'amount': None,
            'tax_amount': None,
            'total_amount': None,
            'seller_name': None,
            'seller_tax_id': None,
            'seller_address': None,
            'seller_bank': None,
            'buyer_name': None,
            'buyer_tax_id': None,
            'buyer_address': None,
            'buyer_bank': None,
            'items': []
        }
        
        # 计算各区域边界
        body_start = int(image_height * 0.20)
        body_end = int(image_height * 0.60)
        amount_start = int(image_height * 0.70)
        amount_end = int(image_height * 0.95)
        
        # 1. 发票号码：从地址后面的8位数字提取
        for t in text_data:
            text = t['text']
            # 匹配 "地址...8位数字" 或单独的8位数字
            # 找最后一个8位数字（通常是发票号码）
            matches = re.findall(r'(\d{8})', text)
            if matches:
                # 取最后一个8位数字
                for no in reversed(matches):
                    if no not in ['00000000', '12345678', '11111111', '22222222', '33333333']:
                        result['invoice_no'] = no
                        break
                if result['invoice_no']:
                    break
        
        # 如果还没找到，扩大范围
        if not result['invoice_no']:
            for t in text_data:
                if body_start <= t['y'] <= body_end + 500:
                    text = t['text']
                    no = self.extract_invoice_no(text)
                    if no:
                        result['invoice_no'] = no
                        break
        
        # 2. 提取日期 - 在金额区域
        for t in text_data:
            if amount_start <= t['y'] <= amount_end:
                date = self.extract_date(t['text'])
                if date:
                    result['date'] = date
                    break
        
        # 3. 提取金额 - 在金额区域
        amounts = []
        taxes = []
        totals = []
        
        for t in text_data:
            if amount_start <= t['y'] <= amount_end:
                text = t['text']
                amt = self.extract_amount(text)
                if amt and amt > 0:
                    if '税' in text or '￥' in text or '¥' in text:
                        taxes.append((amt, t['y'], text))
                    else:
                        amounts.append((amt, t['y'], text))
                    totals.append((amt, t['y'], text))
        
        # 价税合计通常是最大的
        if totals:
            totals.sort(key=lambda x: x[0], reverse=True)
            result['total_amount'] = totals[0][0]
        
        # 金额通常是第二或第三个
        if len(totals) >= 2:
            result['amount'] = totals[1][0] if totals[1][0] <= (result.get('total_amount') or float('inf')) else totals[0][0]
        
        # 税额 = 价税合计 - 金额
        if result.get('total_amount') and result.get('amount'):
            result['tax_amount'] = round(result['total_amount'] - result['amount'], 2)
        
        # 4. 提取购销方信息
        # 发票排版：通常是 销售方名称 → 销售方税号 → 购买方名称 → 购买方税号
        
        # 按y坐标排序，收集所有公司名和税号
        company_candidates = []
        tax_id_candidates = []
        
        for t in text_data:
            if body_start <= t['y'] <= body_end + 400:
                text = t['text'].strip()
                if any(kw in text for kw in ['备注', '作废', '校验码', '密码区', '章', '国家', '合计', '税额', '金额', '地址', '开户行', '电话', '名称']):
                    continue
                
                # 公司名称
                if len(text) > 5 and ('公司' in text or '企业' in text):
                    if '银行' not in text:
                        company_candidates.append((t['y'], text))
                
                # 税号
                tax_id = self.extract_tax_id(text)
                if tax_id and len(tax_id) >= 15:
                    tax_id_candidates.append((t['y'], tax_id, text))
        
        # 按y坐标排序
        company_candidates.sort(key=lambda x: x[0])
        tax_id_candidates.sort(key=lambda x: x[0])
        
        # 分配：公司名第一个是销售方，最后一个是购买方（根据位置）
        # 税号也是类似逻辑，但需要结合公司位置判断
        
        if company_candidates:
            # 第一个公司通常是销售方，最后一个是购买方
            result['seller_name'] = company_candidates[0][1]
            if len(company_candidates) > 1:
                result['buyer_name'] = company_candidates[-1][1]
        
        # 税号：根据位置判断
        # 通常销售方税号在销售方名称下方，购买方税号在购买方名称下方
        if tax_id_candidates:
            # 如果只有一个税号，作为销售方税号
            if len(tax_id_candidates) == 1:
                result['seller_tax_id'] = tax_id_candidates[0][1]
            else:
                # 找最像销售方的税号（通常以9开头，18位统一代码）
                for y, tid, txt in tax_id_candidates:
                    if tid.startswith('9') and len(tid) == 18:
                        result['seller_tax_id'] = tid
                        break
                else:
                    result['seller_tax_id'] = tax_id_candidates[0][1]
                
                # 找最像购买方的税号
                for y, tid, txt in reversed(tax_id_candidates):
                    if tid != result['seller_tax_id']:
                        result['buyer_tax_id'] = tid
                        break
        
        # 5. 校验并修正金额
        result = self.validate_and_fix_amounts(result)
        
        return result
    
    def process_image(self, image_path: str) -> Tuple[Dict, float]:
        """处理发票图片"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        import cv2
        img = cv2.imread(image_path)
        if img is not None:
            image_height = img.shape[0]
        else:
            image_height = 3120
        
        processed_img = None
        if self.enable_preprocessing:
            processed_img = self.preprocess_image(image_path)
            if processed_img is not None:
                temp_path = image_path + '.tmp.jpg'
                cv2.imwrite(temp_path, processed_img)
                image_path = temp_path
        
        text_data = []
        actual_height = 0
        try:
            result = self.ocr.predict(image_path)
            result_list = list(result)
            text_data, actual_height = self.parse_ocr_result(result_list)
        
        except Exception as e:
            print(f"OCR predict() failed: {e}")
            import traceback
            traceback.print_exc()
            text_data = []
        finally:
            if processed_img is not None and os.path.exists(image_path + '.tmp.jpg'):
                try:
                    os.remove(image_path + '.tmp.jpg')
                except:
                    pass
        
        if not text_data:
            return {
                'invoice_no': None,
                'date': None,
                'amount': None,
                'tax_amount': None,
                'total_amount': None,
                'seller_name': None,
                'seller_tax_id': None,
                'items': [],
                'raw_text': []
            }, 0.0
        
        avg_confidence = np.mean([t['confidence'] for t in text_data]) if text_data else 0.0
        
        # 使用实际OCR识别的高度
        image_height = actual_height if actual_height > 0 else image_height
        
        fields = self.extract_fields(text_data, image_height)
        fields['raw_text'] = [t['text'] for t in text_data]
        
        return fields, avg_confidence
    
    def process_from_annotations(self, image_name: str, annotation: Dict) -> Dict:
        """从标注数据处理"""
        result = {
            'invoice_no': None,
            'date': None,
            'amount': None,
            'tax_amount': None,
            'total_amount': None,
            'seller_name': None,
            'seller_tax_id': None,
            'seller_address': None,
            'seller_bank': None,
            'buyer_name': None,
            'buyer_tax_id': None,
            'items': []
        }
        
        for item in annotation:
            text = item.get('transcription', '')
            label = item.get('label', '')
            
            if 'No' in label or '发票号' in label or '编号' in label:
                if text:
                    result['invoice_no'] = text
            
            if '日' in label or '日期' in label:
                result['date'] = self.extract_date(text) or text
            
            if '金额' in label:
                result['amount'] = self.extract_amount(text)
            
            if '税额' in label:
                result['tax_amount'] = self.extract_amount(text)
            
            if '价税合计' in label or '合计' in label:
                result['total_amount'] = self.extract_amount(text)
            
            if '名称' in label and '购买方' not in label:
                result['seller_name'] = text
            
            if '纳税人识别号' in label and '购买方' not in label:
                result['seller_tax_id'] = self.extract_tax_id(text)
            
            if '地址' in label and '购买方' not in label:
                result['seller_address'] = text
            
            if '开户行' in label:
                result['seller_bank'] = text
            
            if '购买方名称' in label:
                result['buyer_name'] = text
            
            if '购买方纳税人识别号' in label:
                result['buyer_tax_id'] = self.extract_tax_id(text)
        
        return result


def load_invoice_annotations(json_path: str) -> Dict[str, List]:
    """加载发票标注数据"""
    annotations = {}
    with open(json_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '\t' in line:
                img_name, data = line.strip().split('\t', 1)
                annotations[img_name] = json.loads(data)
    return annotations


if __name__ == "__main__":
    import glob
    
    ocr = InvoiceOCR(enable_preprocessing=False)
    
    test_dir = "/root/autodl-tmp/caiwubaoxiao/data/data"
    test_files = sorted(glob.glob(f"{test_dir}/b*.jpg"))[:10]
    
    for test_image in test_files:
        print(f"\n{'='*60}")
        print(f"测试: {os.path.basename(test_image)}")
        print('='*60)
        
        result, confidence = ocr.process_image(test_image)
        print('发票号码:', result.get("invoice_no"))
        print('日期:', result.get("date"))
        print('销售方:', result.get("seller_name"))
        print('购买方:', result.get("buyer_name"))
        print('金额:', result.get("amount"))
        print('税额:', result.get("tax_amount"))
        print('价税合计:', result.get("total_amount"))
        print('税号:', result.get("seller_tax_id"))
