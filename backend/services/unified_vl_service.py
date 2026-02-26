"""统一的 Qwen2.5-VL 模型服务

将 OCR 识别、发票分析、签名比对合并为统一服务，共享同一个模型实例。
优化显存占用，减少模型加载时间。

优化项：
- Flash Attention 2 加速
- torch.compile 编译优化
- 图像预处理缩放
- 精简 max_new_tokens
- 4bit 量化（可选）
"""

import os
import sys
import json
import torch
from typing import Dict, List, Optional, Tuple
from PIL import Image

# 设置环境变量
os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['FLAGS_enable_onednn'] = '0'
os.environ['FLAGS_use_mkldnn'] = '0'

from transformers import AutoModelForVision2Seq, AutoProcessor, BitsAndBytesConfig

from backend.config import settings
from backend.logger_config import logger

# 优化配置
USE_FLASH_ATTN = os.getenv("USE_FLASH_ATTN", "true").lower() == "true"
USE_TORCH_COMPILE = os.getenv("USE_TORCH_COMPILE", "false").lower() == "true"  # 首次编译较慢，默认关闭
MAX_IMAGE_SIZE = int(os.getenv("MAX_IMAGE_SIZE", "512"))  # 最大图像尺寸（降低以加速推理）
USE_4BIT_QUANT = os.getenv("USE_4BIT_QUANT", "false").lower() == "true"  # 4bit 量化，默认关闭


class UnifiedVLService:
    """统一的 Qwen2.5-VL 模型服务（单例模式）
    
    功能：
    - OCR 发票识别
    - 发票真伪分析
    - 签名比对
    
    优势：
    - 只加载一次模型，节省显存
    - 减少模型加载时间
    - Flash Attention 2 加速
    - 图像预处理优化
    """
    
    _instance = None
    _model = None
    _processor = None
    _loaded = False
    _compiled = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._loaded:
            self._load_model()
    
    def _resize_image(self, image: Image.Image, max_size: int = MAX_IMAGE_SIZE) -> Image.Image:
        """缩放图像到合适尺寸，减少计算量
        
        Args:
            image: PIL 图像
            max_size: 最大边长
            
        Returns:
            缩放后的图像
        """
        w, h = image.size
        if max(w, h) <= max_size:
            return image
        
        # 保持宽高比缩放
        if w > h:
            new_w = max_size
            new_h = int(h * max_size / w)
        else:
            new_h = max_size
            new_w = int(w * max_size / h)
        
        return image.resize((new_w, new_h), Image.LANCZOS)
    
    def _load_model(self):
        """加载模型（只加载一次）"""
        if self._loaded:
            return
        
        model_path = os.path.join(settings.MODEL_DIR, settings.QWEN_VL_MODEL)
        logger.info(f"[UnifiedVL] 加载模型: {model_path}")
        
        # 清理 GPU 缓存
        torch.cuda.empty_cache()
        import gc
        gc.collect()
        
        # 尝试使用 Flash Attention 2
        attn_implementation = "flash_attention_2" if USE_FLASH_ATTN else "eager"
        
        try:
            # 检查 Flash Attention 是否可用
            if USE_FLASH_ATTN:
                try:
                    import flash_attn
                    logger.info(f"[UnifiedVL] 使用 Flash Attention 2 (版本: {flash_attn.__version__})")
                except ImportError:
                    logger.warning("[UnifiedVL] Flash Attention 2 未安装，使用默认注意力机制")
                    attn_implementation = "eager"
            
            # 4bit 量化配置
            quantization_config = None
            if USE_4BIT_QUANT:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_use_double_quant=True,  # 双重量化进一步节省显存
                    bnb_4bit_quant_type="nf4"  # NormalFloat4 量化类型
                )
                logger.info("[UnifiedVL] 使用 4bit 量化")
            
            # 设置最大内存分配
            if USE_4BIT_QUANT:
                # 4bit 量化后显存占用更小，可以不限制
                max_memory = None
            else:
                max_memory = {
                    0: "20GB",
                    "cpu": "8GB"
                }
            
            self._model = AutoModelForVision2Seq.from_pretrained(
                model_path,
                torch_dtype=torch.bfloat16,
                device_map="auto",
                trust_remote_code=True,
                attn_implementation=attn_implementation,
                max_memory=max_memory,
                low_cpu_mem_usage=True,
                quantization_config=quantization_config
            )
            
            self._processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
            
            # 尝试 torch.compile 优化
            if USE_TORCH_COMPILE and hasattr(torch, 'compile'):
                try:
                    logger.info("[UnifiedVL] 启用 torch.compile 优化...")
                    self._model = torch.compile(self._model, mode="reduce-overhead")
                    self._compiled = True
                    logger.info("[UnifiedVL] torch.compile 优化完成")
                except Exception as e:
                    logger.warning(f"[UnifiedVL] torch.compile 失败: {e}")
                    self._compiled = False
            
            self._loaded = True
            
            # 加载后立即清理
            torch.cuda.empty_cache()
            gc.collect()
            
            logger.info(f"[UnifiedVL] 模型加载完成 (Flash Attention: {attn_implementation == 'flash_attention_2'}, Compile: {self._compiled})")
            
        except Exception as e:
            logger.error(f"[UnifiedVL] 模型加载失败: {e}")
            self._loaded = False
    
    def _parse_number(self, value) -> Optional[float]:
        """解析数字，移除货币符号和逗号"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace('¥', '').replace('￥', '').replace(',', '').replace(' ', '').strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None
    
    def _generate(self, messages: List[Dict], max_new_tokens: int = 1024) -> str:
        """统一的生成方法
        
        Args:
            messages: 消息列表
            max_new_tokens: 最大生成 token 数（默认 1024，精简输出）
            
        Returns:
            生成的文本
        """
        if not self._loaded or not self._model:
            raise RuntimeError("模型未加载")
        
        import gc
        
        # 激进的内存清理
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        
        # 应用聊天模板
        text = self._processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
        # 提取并预处理图片
        images = []
        for msg in messages:
            for content in msg.get("content", []):
                if content.get("type") == "image":
                    img = content.get("image")
                    if isinstance(img, str):
                        img = Image.open(img).convert("RGB")
                    elif isinstance(img, Image.Image):
                        img = img.convert("RGB")
                    
                    # 图像预处理：缩放到合适尺寸（更保守的尺寸以节省显存）
                    img = self._resize_image(img, MAX_IMAGE_SIZE)
                    images.append(img)
        
        # 再次清理
        gc.collect()
        torch.cuda.empty_cache()
        
        # 处理输入
        inputs = self._processor(
            text=[text],
            images=images if images else None,
            return_tensors="pt",
            padding=True
        )
        
        # 移动到GPU
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        
        # 生成（优化参数）
        # 4bit 量化时不需要 autocast，bitsandbytes 会自动处理
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                use_cache=True,  # 启用 KV 缓存
                pad_token_id=self._processor.tokenizer.pad_token_id
            )
        
        # 解码结果
        generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
        result = self._processor.decode(generated_ids, skip_special_tokens=True)
        
        # 清理中间变量
        del inputs, outputs, generated_ids, images
        gc.collect()
        torch.cuda.empty_cache()
        
        return result
    
    def _parse_json_response(self, text: str) -> Dict:
        """解析 JSON 响应"""
        try:
            # 尝试提取JSON部分
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
            else:
                json_str = text.strip()
            
            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            return {"raw_text": text}
    
    # ==================== OCR 相关方法 ====================
    
    def process_invoice(self, image_path: str) -> Dict:
        """处理发票图片，返回标准格式
        
        Args:
            image_path: 图片路径
            
        Returns:
            {'data': dict, 'confidence': float}
        """
        result = self.recognize_invoice(image_path)
        
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
            'confidence': 0.95
        }
    
    def recognize_invoice(self, image_path: str) -> Dict:
        """识别发票图片
        
        Args:
            image_path: 图片路径
            
        Returns:
            识别结果字典
        """
        logger.info(f"[UnifiedVL] OCR识别: {image_path}")
        
        image = Image.open(image_path).convert("RGB")
        
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

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        result_text = self._generate(messages, max_new_tokens=1024)  # OCR 精简输出
        logger.info(f"[UnifiedVL] OCR结果长度: {len(result_text)}")
        
        return self._parse_json_response(result_text)
    
    # ==================== LLM 分析方法 ====================
    
    def analyze_invoice_image(self, image_path: str, ocr_result: Dict) -> Dict:
        """分析发票真伪
        
        Args:
            image_path: 图片路径
            ocr_result: OCR识别结果
            
        Returns:
            分析结果字典
        """
        logger.info(f"[UnifiedVL] 发票分析: {image_path}")
        
        if not self._loaded or not self._model:
            return {
                'is_suspicious': False,
                'suspicious_points': [],
                'authenticity_score': 0.5,
                'analysis_summary': '模型未加载'
            }
        
        invoice_info = f"""
OCR识别结果：
- 发票号码：{ocr_result.get('invoice_no', 'N/A')}
- 开票日期：{ocr_result.get('date', 'N/A')}
- 金额：{ocr_result.get('amount', 'N/A')}
- 税额：{ocr_result.get('tax_amount', 'N/A')}
- 价税合计：{ocr_result.get('total_amount', 'N/A')}
- 销售方名称：{ocr_result.get('seller_name', 'N/A')}
- 销售方税号：{ocr_result.get('seller_tax_id', 'N/A')}
- 购买方名称：{ocr_result.get('buyer_name', 'N/A')}
"""
        
        prompt = f"""你是一个专业的财务发票审核专家。请仔细分析这张发票图片，结合OCR识别结果，判断发票是否存在以下问题：

1. 是否存在PS痕迹或人为修改的痕迹
2. 印章是否清晰完整
3. 字体是否规范（是否存在非标准字体）
4. 金额是否与商品明细匹配
5. 发票格式是否符合规范

OCR识别结果：
{invoice_info}

请以JSON格式返回分析结果：
{{
    "is_suspicious": true/false,
    "suspicious_points": ["具体可疑点1", "具体可疑点2"],
    "authenticity_score": 0.0-1.0,
    "analysis_summary": "简要分析说明"
}}
"""
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image_path},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        try:
            result_text = self._generate(messages, max_new_tokens=256)  # 分析结果精简
            result = self._parse_json_response(result_text)
            
            # 确保返回正确的字段
            return {
                'is_suspicious': result.get('is_suspicious', False),
                'suspicious_points': result.get('suspicious_points', []),
                'authenticity_score': result.get('authenticity_score', 0.8),
                'analysis_summary': result.get('analysis_summary', result.get('raw_text', '')[:500])
            }
            
        except Exception as e:
            logger.error(f"[UnifiedVL] 发票分析失败: {e}")
            return {
                'is_suspicious': False,
                'suspicious_points': [],
                'authenticity_score': 0.5,
                'analysis_summary': str(e)
            }
    
    def process_invoice_combined(self, image_path: str) -> Dict:
        """合并 OCR + 分析为一次推理（优化性能）
        
        一次推理同时完成：
        1. OCR 识别发票信息
        2. 分析发票真伪
        
        Args:
            image_path: 图片路径
            
        Returns:
            {
                'ocr': {'data': dict, 'confidence': float},
                'analysis': {'is_suspicious': bool, ...}
            }
        """
        logger.info(f"[UnifiedVL] 合并处理（OCR+分析）: {image_path}")
        
        if not self._loaded or not self._model:
            return {
                'ocr': {'data': {}, 'confidence': 0.0},
                'analysis': {
                    'is_suspicious': False,
                    'suspicious_points': [],
                    'authenticity_score': 0.5,
                    'analysis_summary': '模型未加载'
                }
            }
        
        image = Image.open(image_path).convert("RGB")
        
        # 合并后的精简 Prompt
        prompt = """识别这张发票并分析真伪，按以下JSON格式输出：
{
    "ocr": {
        "invoice_code": "发票代码",
        "invoice_no": "发票号码",
        "date": "开票日期",
        "buyer_name": "购买方名称",
        "buyer_tax_id": "购买方税号",
        "seller_name": "销售方名称",
        "seller_tax_id": "销售方税号",
        "amount": "金额(数字)",
        "tax_amount": "税额(数字)",
        "total_amount": "价税合计(数字)"
    },
    "analysis": {
        "is_suspicious": false,
        "suspicious_points": [],
        "authenticity_score": 0.95,
        "analysis_summary": "简要分析"
    }
}

分析要点：PS痕迹、印章清晰度、字体规范、金额匹配、格式合规。
只输出JSON，金额为纯数字。"""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        try:
            result_text = self._generate(messages, max_new_tokens=1024)
            result = self._parse_json_response(result_text)
            
            # 解析 OCR 结果
            ocr_data = result.get('ocr', {})
            ocr_result = {
                'data': {
                    'invoice_code': ocr_data.get('invoice_code'),
                    'invoice_no': ocr_data.get('invoice_no'),
                    'date': ocr_data.get('date'),
                    'buyer_name': ocr_data.get('buyer_name'),
                    'buyer_tax_id': ocr_data.get('buyer_tax_id'),
                    'seller_name': ocr_data.get('seller_name'),
                    'seller_tax_id': ocr_data.get('seller_tax_id'),
                    'amount': self._parse_number(ocr_data.get('amount')),
                    'tax_amount': self._parse_number(ocr_data.get('tax_amount')),
                    'total_amount': self._parse_number(ocr_data.get('total_amount')),
                    'raw_text': result.get('raw_text', '')
                },
                'confidence': 0.95
            }
            
            # 解析分析结果
            analysis_data = result.get('analysis', {})
            analysis_result = {
                'is_suspicious': analysis_data.get('is_suspicious', False),
                'suspicious_points': analysis_data.get('suspicious_points', []),
                'authenticity_score': analysis_data.get('authenticity_score', 0.8),
                'analysis_summary': analysis_data.get('analysis_summary', '')
            }
            
            logger.info(f"[UnifiedVL] 合并处理完成 - OCR字段: {len(ocr_result['data'])}, 分析完成")
            
            return {
                'ocr': ocr_result,
                'analysis': analysis_result
            }
            
        except Exception as e:
            logger.error(f"[UnifiedVL] 合并处理失败: {e}")
            return {
                'ocr': {'data': {}, 'confidence': 0.0},
                'analysis': {
                    'is_suspicious': False,
                    'suspicious_points': [],
                    'authenticity_score': 0.5,
                    'analysis_summary': str(e)
                }
            }
    
    def compare_signatures(self, signature1_path: str, signature2_path: str) -> Dict:
        """比对签名
        
        Args:
            signature1_path: 签名图片1路径
            signature2_path: 签名图片2路径
            
        Returns:
            比对结果字典
        """
        logger.info(f"[UnifiedVL] 签名比对: {signature1_path} vs {signature2_path}")
        
        if not self._loaded or not self._model:
            return {
                'similarity_score': 0.5,
                'is_match': False,
                'analysis': '模型未加载'
            }
        
        prompt = """对比这两张签名图像，分析笔迹相似度。
考虑因素：连笔习惯、字间距、笔画粗细、整体倾斜度、书写风格。
请以JSON格式返回：
{
    "similarity_score": 0.0-1.0,
    "is_match": true/false,
    "key_differences": ["差异点1", "差异点2"],
    "analysis": "简要分析"
}
"""
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": signature1_path},
                    {"type": "image", "image": signature2_path},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        try:
            result_text = self._generate(messages, max_new_tokens=256)  # 签名比对精简
            result = self._parse_json_response(result_text)
            
            return {
                'similarity_score': result.get('similarity_score', 0.5),
                'is_match': result.get('is_match', False),
                'key_differences': result.get('key_differences', []),
                'analysis': result.get('analysis', result.get('raw_text', '')[:500])
            }
            
        except Exception as e:
            logger.error(f"[UnifiedVL] 签名比对失败: {e}")
            return {
                'similarity_score': 0.5,
                'is_match': False,
                'analysis': str(e)
            }


# 全局单例
_unified_vl_service = None


def get_unified_vl_service() -> UnifiedVLService:
    """获取统一的 VL 服务实例"""
    global _unified_vl_service
    if _unified_vl_service is None:
        _unified_vl_service = UnifiedVLService()
    return _unified_vl_service
