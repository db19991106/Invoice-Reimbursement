"""vLLM 加速的 Qwen2.5-VL 模型服务"""

import os
import sys
import json
import torch
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image

# 在导入其他模块前初始化 CUDA
if torch.cuda.is_available():
    torch.cuda.init()

from backend.config import settings
from backend.logger_config import logger

# vLLM 导入
from vllm import LLM, SamplingParams


class VLLMService:
    """vLLM 加速的 VL 模型服务单例"""
    
    _instance = None
    _llm = None
    _loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        pass  # 不在初始化时加载模型，改为延迟加载
    
    def _ensure_loaded(self):
        """确保模型已加载"""
        if not self._loaded:
            self._load_model()
    
    def _load_model(self):
        """加载 vLLM 引擎"""
        if self._loaded:
            return
        
        model_path = os.path.join(settings.MODEL_DIR, settings.QWEN_VL_MODEL)
        
        logger.info(f"[vLLM] 开始加载模型: {model_path}")
        
        try:
            # 配置图片处理器参数，限制最大分辨率以减少tokens
            mm_processor_kwargs = {
                "min_pixels": 256 * 28 * 28,  # 最小分辨率
                "max_pixels": 512 * 28 * 28,  # 最大分辨率 (降低以节省显存)
            }
            
            self._llm = LLM(
                model=model_path,
                dtype="bfloat16",
                max_model_len=8192,  # 降低以适应 GPU 显存限制
                gpu_memory_utilization=0.85,  # 留空间给模型和KV cache
                trust_remote_code=True,
                limit_mm_per_prompt={"image": 1},
                allowed_local_media_path="/root/autodl-tmp",  # 允许加载本地图片
                enforce_eager=True,  # 禁用 CUDA Graphs 以节省显存
                mm_processor_kwargs=mm_processor_kwargs  # 图片处理参数
            )
            self._loaded = True
            logger.info("[vLLM] 模型加载完成")
        except Exception as e:
            logger.error(f"[vLLM] 模型加载失败: {e}")
            raise
    
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
    
    def process_invoice(self, image_path: str) -> Dict:
        """处理发票图片，返回与 OCR 服务相同的格式
        
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
        """使用 vLLM 识别发票图片
        
        Args:
            image_path: 图片路径
            
        Returns:
            识别结果字典
        """
        self._ensure_loaded()
        logger.info(f"[vLLM] 开始识别: {image_path}")
        
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
                    {"type": "image_url", "image_url": {"url": f"file://{image_path}"}},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        sampling_params = SamplingParams(
            temperature=0.1,
            top_p=0.9,
            max_tokens=2048
        )
        
        try:
            outputs = self._llm.chat(messages, sampling_params)
            result_text = outputs[0].outputs[0].text
            
            logger.info(f"[vLLM] 识别完成，结果长度: {len(result_text)}")
            logger.info(f"[vLLM] 识别结果: {result_text[:500]}...")
            
            # 解析JSON
            if "```json" in result_text:
                json_str = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                json_str = result_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = result_text.strip()
            
            result = json.loads(json_str)
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"[vLLM] JSON解析失败: {e}")
            return {"raw_text": result_text if 'result_text' in dir() else ""}
        except Exception as e:
            logger.error(f"[vLLM] 识别失败: {e}")
            return {"raw_text": str(e)}
    
    def analyze_invoice_image(self, image_path: str, ocr_result: Dict) -> Dict:
        """分析发票真伪
        
        Args:
            image_path: 图片路径
            ocr_result: OCR识别结果
            
        Returns:
            分析结果字典
        """
        self._ensure_loaded()
        logger.info(f"[vLLM] 开始分析发票真伪: {image_path}")
        
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
}}"""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"file://{image_path}"}},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        sampling_params = SamplingParams(
            temperature=0.3,
            top_p=0.9,
            max_tokens=512
        )
        
        try:
            outputs = self._llm.chat(messages, sampling_params)
            result_text = outputs[0].outputs[0].text
            
            logger.info(f"[vLLM] 分析完成: {result_text[:300]}...")
            
            # 解析JSON
            if "```json" in result_text:
                json_str = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                json_str = result_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = result_text.strip()
            
            result = json.loads(json_str)
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"[vLLM] JSON解析失败: {e}")
            return {
                'is_suspicious': False,
                'suspicious_points': [],
                'authenticity_score': 0.8,
                'analysis_summary': result_text[:500] if 'result_text' in dir() else '解析失败'
            }
        except Exception as e:
            logger.error(f"[vLLM] 分析失败: {e}")
            return {
                'is_suspicious': False,
                'suspicious_points': [],
                'authenticity_score': 0.5,
                'error': str(e)
            }
    
    def process_invoice_combined(self, image_path: str) -> Dict:
        """合并 OCR + 分析为一次推理（优化性能）
        
        Args:
            image_path: 图片路径
            
        Returns:
            {'ocr': ocr_result, 'analysis': analysis_result}
        """
        self._ensure_loaded()
        logger.info(f"[vLLM] 合并处理（OCR+分析）: {image_path}")
        
        prompt = """请识别这张发票并进行真伪分析，按以下JSON格式输出：
{
    "ocr": {
        "invoice_code": "发票代码",
        "invoice_no": "发票号码",
        "date": "开票日期",
        "buyer_name": "购买方名称",
        "buyer_tax_id": "购买方税号",
        "seller_name": "销售方名称",
        "seller_tax_id": "销售方税号",
        "amount": "金额不含税（数字）",
        "tax_amount": "税额（数字）",
        "total_amount": "价税合计（数字）"
    },
    "analysis": {
        "is_suspicious": true/false,
        "suspicious_points": ["可疑点1", "可疑点2"],
        "authenticity_score": 0.0-1.0,
        "analysis_summary": "简要分析"
    }
}

注意：
1. amount、tax_amount、total_amount 请输出纯数字
2. 检查是否存在PS痕迹、印章是否清晰、字体是否规范
3. 只输出JSON，不要其他内容"""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"file://{image_path}"}},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        sampling_params = SamplingParams(
            temperature=0.1,
            top_p=0.9,
            max_tokens=2048
        )
        
        try:
            outputs = self._llm.chat(messages, sampling_params)
            result_text = outputs[0].outputs[0].text
            
            logger.info(f"[vLLM] 合并处理完成，结果长度: {len(result_text)}")
            
            # 解析JSON
            if "```json" in result_text:
                json_str = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                json_str = result_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = result_text.strip()
            
            result = json.loads(json_str)
            
            # 构建 OCR 结果
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
                },
                'confidence': 0.95
            }
            
            # 构建分析结果
            analysis_result = result.get('analysis', {
                'is_suspicious': False,
                'suspicious_points': [],
                'authenticity_score': 0.8
            })
            
            # 输出详细的OCR识别结果日志
            logger.info("=" * 60)
            logger.info("[OCR识别结果]")
            logger.info(f"  发票代码: {ocr_result['data'].get('invoice_code', 'N/A')}")
            logger.info(f"  发票号码: {ocr_result['data'].get('invoice_no', 'N/A')}")
            logger.info(f"  开票日期: {ocr_result['data'].get('date', 'N/A')}")
            logger.info(f"  购买方: {ocr_result['data'].get('buyer_name', 'N/A')}")
            logger.info(f"  购买方税号: {ocr_result['data'].get('buyer_tax_id', 'N/A')}")
            logger.info(f"  销售方: {ocr_result['data'].get('seller_name', 'N/A')}")
            logger.info(f"  销售方税号: {ocr_result['data'].get('seller_tax_id', 'N/A')}")
            logger.info(f"  金额(不含税): {ocr_result['data'].get('amount', 'N/A')}")
            logger.info(f"  税额: {ocr_result['data'].get('tax_amount', 'N/A')}")
            logger.info(f"  价税合计: {ocr_result['data'].get('total_amount', 'N/A')}")
            logger.info(f"  置信度: {ocr_result['confidence']}")
            
            # 输出详细的分析结果日志
            logger.info("-" * 60)
            logger.info("[发票真伪分析结果]")
            logger.info(f"  是否可疑: {analysis_result.get('is_suspicious', False)}")
            logger.info(f"  真实性评分: {analysis_result.get('authenticity_score', 0.0):.2f}")
            suspicious_points = analysis_result.get('suspicious_points', [])
            if suspicious_points:
                logger.info(f"  可疑点: {suspicious_points}")
            summary = analysis_result.get('analysis_summary', '')
            if summary:
                logger.info(f"  分析摘要: {summary}")
            logger.info("=" * 60)
            
            return {
                'ocr': ocr_result,
                'analysis': analysis_result
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"[vLLM] JSON解析失败: {e}")
            # 返回默认结果
            return {
                'ocr': {
                    'data': {'raw_text': result_text if 'result_text' in dir() else ''},
                    'confidence': 0.5
                },
                'analysis': {
                    'is_suspicious': False,
                    'suspicious_points': [],
                    'authenticity_score': 0.5
                }
            }
        except Exception as e:
            logger.error(f"[vLLM] 合并处理失败: {e}")
            return {
                'ocr': {
                    'data': {'error': str(e)},
                    'confidence': 0.0
                },
                'analysis': {
                    'is_suspicious': False,
                    'suspicious_points': [],
                    'authenticity_score': 0.5,
                    'error': str(e)
                }
            }
    
    def compare_signatures(self, signature1_path: str, signature2_path: str) -> Dict:
        """比对两个签名
        
        Args:
            signature1_path: 签名1路径
            signature2_path: 签名2路径
            
        Returns:
            比对结果字典
        """
        self._ensure_loaded()
        logger.info(f"[vLLM] 开始比对签名")
        
        prompt = """对比这两张签名图像，分析笔迹相似度。
考虑因素：连笔习惯、字间距、笔画粗细、整体倾斜度、书写风格。
请以JSON格式返回：
{
    "similarity_score": 0.0-1.0,
    "is_match": true/false,
    "key_differences": ["差异点1", "差异点2"],
    "analysis": "简要分析"
}"""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"file://{signature1_path}"}},
                    {"type": "image_url", "image_url": {"url": f"file://{signature2_path}"}},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        sampling_params = SamplingParams(
            temperature=0.3,
            max_tokens=512
        )
        
        try:
            outputs = self._llm.chat(messages, sampling_params)
            result_text = outputs[0].outputs[0].text
            
            # 解析JSON
            if "```json" in result_text:
                json_str = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                json_str = result_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = result_text.strip()
            
            result = json.loads(json_str)
            return result
            
        except Exception as e:
            logger.error(f"[vLLM] 签名比对失败: {e}")
            return {
                'similarity_score': 0.5,
                'is_match': False,
                'analysis': str(e)
            }


# 全局服务实例
_vllm_service = None


def get_vllm_service() -> VLLMService:
    """获取 vLLM 服务实例"""
    global _vllm_service
    if _vllm_service is None:
        _vllm_service = VLLMService()
    return _vllm_service
