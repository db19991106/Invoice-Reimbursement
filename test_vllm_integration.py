"""测试 vLLM 方案集成"""

import sys
import os
import time

sys.path.insert(0, '/root/autodl-tmp/caiwubaoxiao')

def test_vllm_integration():
    print("="*60)
    print("测试 vLLM 方案集成")
    print("="*60)
    
    # 1. 检查配置
    from backend.config import settings
    print(f"\n[配置检查]")
    print(f"  USE_VLLM: {settings.USE_VLLM}")
    print(f"  USE_COMBINED_OCR_LLM: {settings.USE_COMBINED_OCR_LLM}")
    
    if not settings.USE_VLLM:
        print("错误: USE_VLLM 为 False，请修改配置")
        return
    
    # 2. 测试 vLLM 服务
    print(f"\n[加载 vLLM 服务]")
    start = time.time()
    
    from backend.services.vllm_service import get_vllm_service
    service = get_vllm_service()
    
    load_time = time.time() - start
    print(f"  加载时间: {load_time:.2f}秒")
    
    # 3. 测试合并处理
    image_path = "/root/autodl-tmp/caiwubaoxiao/data/data/b0.jpg"
    
    print(f"\n[测试合并处理（OCR+分析）]")
    print(f"  图片: {image_path}")
    
    start = time.time()
    result = service.process_invoice_combined(image_path)
    process_time = time.time() - start
    
    print(f"  处理时间: {process_time:.2f}秒")
    print(f"  OCR 结果: {result['ocr']['data']}")
    print(f"  分析结果: is_suspicious={result['analysis'].get('is_suspicious')}, score={result['analysis'].get('authenticity_score')}")
    
    # 4. 再次测试（热启动）
    print(f"\n[再次测试（热启动）]")
    start = time.time()
    result = service.process_invoice_combined(image_path)
    process_time2 = time.time() - start
    print(f"  处理时间: {process_time2:.2f}秒")
    
    print("\n" + "="*60)
    print("测试完成！vLLM 方案集成成功")
    print("="*60)
    
    print(f"\n性能总结:")
    print(f"  模型加载时间: {load_time:.2f}秒")
    print(f"  首次推理时间: {process_time:.2f}秒")
    print(f"  二次推理时间: {process_time2:.2f}秒")

if __name__ == "__main__":
    test_vllm_integration()
