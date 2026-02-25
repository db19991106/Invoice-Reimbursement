"""Qwen2.5-VL 模型服务，用于发票OCR识别"""

import os
import sys
import json
import torch
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image, ImageDraw, ImageFont

# 设置环境变量
os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['FLAGS_enable_onednn'] = '0'
os.environ['FLAGS_use_mkldnn'] = '0'

from transformers import AutoModelForVision2Seq, AutoProcessor

from backend.logger_config import logger

MODEL_PATH = "/root/autodl-tmp/models/Qwen2.5-VL-7B-Instruct"


class QwenVLService:
    """Qwen2.5-VL 模型服务单例"""
    
    _instance = None
    _model = None
    _processor = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        """加载模型"""
        logger.info(f"[QwenVL] 加载模型: {MODEL_PATH}")
        
        self._model = AutoModelForVision2Seq.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True
        )
        
        self._processor = AutoProcessor.from_pretrained(MODEL_PATH)
        
        logger.info("[QwenVL] 模型加载完成")
    
    def _parse_number(self, value) -> Optional[float]:
        """解析数字，移除货币符号和逗号"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # 移除货币符号、逗号、空格
            cleaned = value.replace('¥', '').replace('￥', '').replace(',', '').replace(' ', '').strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None
    
    def process_invoice(self, image_path: str) -> Dict:
        """处理发票图片，返回与 OCR 服务相同的格式
        
        Args:
            image_path: 图片路径
            
        Returns:
            {'data': dict, 'confidence': float}
        """
        result = self.recognize_invoice(image_path)
        
        # 转换字段名以匹配审核服务期望的格式
        data = {
            'invoice_code': result.get('invoice_code'),
            'invoice_no': result.get('invoice_no'),
            'date': result.get('date'),
            'buyer_name': result.get('buyer_name'),
            'buyer_tax_id': result.get('buyer_tax_id'),
            'buyer_address': result.get('buyer_address'),
            'buyer_bank': result.get('buyer_bank'),
            'seller_name': result.get('seller_name'),
            'seller_tax_id': result.get('seller_tax_id'),
            'seller_address': result.get('seller_address'),
            'seller_bank': result.get('seller_bank'),
            'amount': self._parse_number(result.get('amount')),
            'tax_amount': self._parse_number(result.get('tax_amount')),
            'total_amount': self._parse_number(result.get('total_amount')),
            'items': result.get('items', []),
            'raw_text': result.get('raw_text', '')
        }
        
        return {
            'data': data,
            'confidence': 0.95  # QwenVL 不返回置信度，使用固定值
        }
    
    def recognize_invoice(self, image_path: str) -> Dict:
        """识别发票图片
        
        Args:
            image_path: 图片路径
            
        Returns:
            识别结果字典
        """
        logger.info(f"[QwenVL] 开始识别: {image_path}")
        
        # 加载图片
        image = Image.open(image_path).convert("RGB")
        
        # 构建提示词
        prompt = """请识别这张发票图片中的所有文字信息，按以下JSON格式输出：
{
    "invoice_code": "发票代码",
    "invoice_no": "发票号码",
    "date": "开票日期",
    "buyer_name": "购买方名称",
    "buyer_tax_id": "购买方税号",
    "buyer_address": "购买方地址电话",
    "buyer_bank": "购买方银行账号",
    "seller_name": "销售方名称",
    "seller_tax_id": "销售方税号",
    "seller_address": "销售方地址电话",
    "seller_bank": "销售方银行账号",
    "amount": "金额不含税（数字）",
    "tax_amount": "税额（数字）",
    "total_amount": "价税合计（数字）",
    "items": [{"name": "商品名称", "spec": "规格", "unit": "单位", "quantity": "数量", "price": "单价", "amount": "金额"}]
}

注意：
1. amount、tax_amount、total_amount 请输出纯数字，不要带货币符号
2. 只输出JSON，不要其他内容"""

        # 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        # 应用聊天模板
        text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
        # 处理输入
        inputs = self._processor(
            text=[text],
            images=[image],
            return_tensors="pt",
            padding=True
        )
        
        # 移动到GPU
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        
        # 生成
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=2048,
                do_sample=False
            )
        
        # 解码结果
        generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
        result_text = self._processor.decode(generated_ids, skip_special_tokens=True)
        
        logger.info(f"[QwenVL] 识别完成，结果长度: {len(result_text)}")
        logger.info(f"[QwenVL] 识别结果: {result_text[:500]}...")
        
        # 解析JSON
        try:
            # 尝试提取JSON部分
            if "```json" in result_text:
                json_str = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                json_str = result_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = result_text.strip()
            
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"[QwenVL] JSON解析失败: {e}")
            result = {"raw_text": result_text}
        
        return result
    
    def recognize_with_boxes(self, image_path: str) -> List[Dict]:
        """识别图片中的文字并返回位置信息
        
        Args:
            image_path: 图片路径
            
        Returns:
            包含文字和位置信息的列表
        """
        logger.info(f"[QwenVL] 开始识别(带位置): {image_path}")
        
        # 加载图片
        image = Image.open(image_path).convert("RGB")
        w, h = image.size
        
        # 构建提示词 - 要求识别所有文字及大致位置
        prompt = """请识别这张发票图片中的所有文字内容，按行输出，每行格式：
行号. 文字内容

请尽可能完整地识别所有可见文字，包括：
- 发票标题
- 发票代码、号码、日期
- 购买方信息（名称、税号、地址、银行）
- 销售方信息（名称、税号、地址、银行）
- 商品明细（名称、规格、单位、数量、单价、金额）
- 合计金额（大写和小写）
- 密码区内容
- 其他所有可见文字

请逐行完整输出所有识别到的文字。"""

        # 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        # 应用聊天模板
        text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
        # 处理输入
        inputs = self._processor(
            text=[text],
            images=[image],
            return_tensors="pt",
            padding=True
        )
        
        # 移动到GPU
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        
        # 生成
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=4096,
                do_sample=False
            )
        
        # 解码结果
        generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
        result_text = self._processor.decode(generated_ids, skip_special_tokens=True)
        
        logger.info(f"[QwenVL] 识别完成，结果:\n{result_text[:500]}...")
        
        # 解析结果，模拟位置信息（QwenVL不返回精确位置）
        lines = []
        for i, line in enumerate(result_text.split('\n')):
            line = line.strip()
            if line and not line.startswith('行号') and not line.startswith('请'):
                # 移除行号前缀
                if '. ' in line and line.split('.')[0].isdigit():
                    text = line.split('. ', 1)[1] if '. ' in line else line
                else:
                    text = line
                
                if text:
                    lines.append({
                        'text': text,
                        'confidence': 0.95,
                        # 模拟位置（基于行号估算）
                        'box': [0, i * 30, min(len(text) * 12, w), (i + 1) * 30]
                    })
        
        return lines, result_text


# 全局服务实例
_qwen_service = None


def get_qwen_service() -> QwenVLService:
    """获取 QwenVL 服务实例"""
    global _qwen_service
    if _qwen_service is None:
        _qwen_service = QwenVLService()
    return _qwen_service
