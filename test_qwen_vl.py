#!/usr/bin/env python3
"""测试 Qwen2.5-VL 模型识别发票"""

import sys
import os

# 设置环境变量
os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['FLAGS_enable_onednn'] = '0'
os.environ['FLAGS_use_mkldnn'] = '0'

from transformers import AutoModelForVision2Seq, AutoProcessor
from PIL import Image
import torch

MODEL_PATH = "/root/autodl-tmp/models/Qwen2.5-VL-7B-Instruct"

def test_invoice_ocr(image_path: str):
    """使用 Qwen2.5-VL 识别发票"""
    
    print(f"加载模型: {MODEL_PATH}")
    
    # 加载模型
    model = AutoModelForVision2Seq.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    
    # 加载处理器
    processor = AutoProcessor.from_pretrained(MODEL_PATH)
    
    print("模型加载完成")
    
    # 加载图片
    print(f"处理图片: {image_path}")
    image = Image.open(image_path).convert("RGB")
    
    # 构建提示词
    prompt = """请识别这张发票图片中的所有文字信息，按以下格式输出：

1. 发票代码：
2. 发票号码：
3. 开票日期：
4. 购买方名称：
5. 购买方税号：
6. 销售方名称：
7. 销售方税号：
8. 金额(不含税)：
9. 税额：
10. 价税合计：
11. 商品明细：

请尽可能完整地识别所有文字，包括表格中的内容。"""

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
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    # 处理输入
    inputs = processor(
        text=[text],
        images=[image],
        return_tensors="pt",
        padding=True
    )
    
    # 移动到GPU
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    
    print("开始识别...")
    
    # 生成
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=2048,
            do_sample=False
        )
    
    # 解码结果
    generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
    result = processor.decode(generated_ids, skip_special_tokens=True)
    
    print("\n" + "="*50)
    print("识别结果:")
    print("="*50)
    print(result)
    
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_qwen_vl.py <图片路径>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"图片不存在: {image_path}")
        sys.exit(1)
    
    test_invoice_ocr(image_path)
