import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Optional, List
import torch
from PIL import Image
import json

from backend.config import settings


class LLMService:
    def __init__(self):
        self.vl_model = None
        self.llm_model = None
        self.tokenizer = None
        self.processor = None
        self._vl_loaded = False
        self._llm_loaded = False
        self.process_vision_info = None
    
    def load_vl_model(self):
        if self._vl_loaded:
            return
        
        try:
            from transformers import AutoProcessor, AutoModelForVision2Seq
            from qwen_vl_utils import process_vision_info
            self.process_vision_info = process_vision_info
            
            model_path = os.path.join(settings.MODEL_DIR, settings.QWEN_VL_MODEL)
            
            print(f"Loading Qwen2.5-VL model from {model_path}...")
            
            self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
            self.vl_model = AutoModelForVision2Seq.from_pretrained(
                model_path,
                torch_dtype=torch.bfloat16,
                device_map="auto",
                trust_remote_code=True
            )
            
            self._vl_loaded = True
            print("Qwen2.5-VL model loaded successfully")
            
        except Exception as e:
            print(f"Failed to load Qwen2.5-VL model: {e}")
            self._vl_loaded = False
    
    def analyze_invoice_image(self, image_path: str, ocr_result: Dict) -> Dict:
        if not self._vl_loaded:
            self.load_vl_model()
        
        if not self._vl_loaded or not self.vl_model:
            return {
                'analysis': 'Model not loaded',
                'suspicious_points': [],
                'authenticity_score': 0.5
            }
        
        try:
            image = Image.open(image_path)
            
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
                        {"image": f"file://{image_path}"},
                        {"text": prompt}
                    ]
                }
            ]
            
            text = self.processor.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
            
            image_inputs, _ = self.process_vision_info(messages)
            
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                return_tensors="pt",
                padding=True
            )
            
            inputs = {k: v.to(self.vl_model.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                generated_ids = self.vl_model.generate(
                    **inputs,
                    max_new_tokens=512,
                    do_sample=False
                )
            
            generated_ids_trimmed = [
                out_ids[len(in_ids):] 
                for in_ids, out_ids in zip(inputs['input_ids'], generated_ids)
            ]
            
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, 
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            )[0]
            
            try:
                result = json.loads(output_text)
            except:
                result = {
                    'is_suspicious': False,
                    'suspicious_points': [],
                    'authenticity_score': 0.8,
                    'analysis_summary': output_text[:500]
                }
            
            return result
            
        except Exception as e:
            print(f"Error analyzing invoice: {e}")
            return {
                'is_suspicious': False,
                'suspicious_points': [],
                'authenticity_score': 0.5,
                'error': str(e)
            }
    
    def compare_signatures(self, signature1_path: str, signature2_path: str) -> Dict:
        if not self._vl_loaded:
            self.load_vl_model()
        
        if not self._vl_loaded or not self.vl_model:
            return {
                'similarity_score': 0.5,
                'analysis': 'Model not loaded',
                'is_match': False
            }
        
        try:
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
                        {"image": f"file://{signature1_path}"},
                        {"image": f"file://{signature2_path}"},
                        {"text": prompt}
                    ]
                }
            ]
            
            text = self.processor.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
            
            image_inputs, _ = self.process_vision_info(messages)
            
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                return_tensors="pt",
                padding=True
            )
            
            inputs = {k: v.to(self.vl_model.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                generated_ids = self.vl_model.generate(
                    **inputs,
                    max_new_tokens=512,
                    do_sample=False
                )
            
            generated_ids_trimmed = [
                out_ids[len(in_ids):] 
                for in_ids, out_ids in zip(inputs['input_ids'], generated_ids)
            ]
            
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, 
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            )[0]
            
            try:
                result = json.loads(output_text)
            except:
                result = {
                    'similarity_score': 0.5,
                    'is_match': False,
                    'analysis': output_text[:500]
                }
            
            return result
            
        except Exception as e:
            print(f"Error comparing signatures: {e}")
            return {
                'similarity_score': 0.5,
                'is_match': False,
                'error': str(e)
            }
    
    def make_decision(
        self,
        signature_score: Optional[float],
        invoice_analysis: Dict,
        risk_score: float,
        invoice_data: Dict
    ) -> Dict:
        try:
            prompt = f"""作为财务审核决策系统，请根据以下信息给出最终审核决策：

1. 签名比对分数：{signature_score if signature_score else '未进行签名验证'}
2. 发票真伪分析：{invoice_analysis.get('analysis_summary', 'N/A')}
3. 发票真实性得分：{invoice_analysis.get('authenticity_score', 0.5)}
4. 当前风险评分：{risk_score:.2f}
5. 发票金额：{invoice_data.get('amount', 'N/A')}
6. 发票日期：{invoice_data.get('date', 'N/A')}

请以JSON格式返回决策结果：
{{
    "decision": "approve/review/reject",
    "reason": "简要决策理由",
    "risk_level": "low/medium/high",
    "suggestions": ["建议1", "建议2"]
}}
"""
            
            return {
                'decision': 'review' if risk_score > 0.5 else 'approve',
                'reason': '基于风险评分自动决策',
                'risk_level': 'high' if risk_score > 0.8 else ('medium' if risk_score > 0.5 else 'low'),
                'suggestions': invoice_analysis.get('suspicious_points', [])
            }
            
        except Exception as e:
            print(f"Error making decision: {e}")
            return {
                'decision': 'review',
                'reason': '系统异常，默认人工审核',
                'risk_level': 'medium',
                'suggestions': [str(e)]
            }


llm_service = LLMService()


def get_llm_service() -> LLMService:
    return llm_service
