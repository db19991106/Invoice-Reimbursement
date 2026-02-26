"""测试 vLLM 和 Unified VL 服务的性能对比"""

import os
import sys
import time
import torch
import gc

# 设置路径
sys.path.insert(0, '/root/autodl-tmp/caiwubaoxiao')

def clear_gpu_memory():
    """清理 GPU 显存"""
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.synchronize()
    print(f"[显存] 已清理，当前使用: {torch.cuda.memory_allocated()/1024**3:.2f} GB")

def test_vllm(image_path: str):
    """测试 vLLM 服务"""
    print("\n" + "="*60)
    print("测试 vLLM 服务")
    print("="*60)
    
    clear_gpu_memory()
    
    try:
        from vllm import LLM, SamplingParams
        
        model_path = "/root/autodl-tmp/models/Qwen2.5-VL-7B-Instruct"
        
        # 记录加载时间
        print(f"[vLLM] 开始加载模型: {model_path}")
        load_start = time.time()
        
        llm = LLM(
            model=model_path,
            dtype="bfloat16",
            max_model_len=32768,  # 增大以容纳图像 tokens
            gpu_memory_utilization=0.9,  # 提高显存利用率
            trust_remote_code=True,
            limit_mm_per_prompt={"image": 1},
            enforce_eager=True,
            allowed_local_media_path="/root/autodl-tmp"
        )
        
        load_time = time.time() - load_start
        print(f"[vLLM] 模型加载完成，耗时: {load_time:.2f}秒")
        print(f"[vLLM] 显存使用: {torch.cuda.memory_allocated()/1024**3:.2f} GB")
        
        # 测试 OCR 推理
        prompt = """请识别这张发票图片中的所有文字信息，按以下JSON格式输出：
{
    "invoice_code": "发票代码",
    "invoice_no": "发票号码",
    "date": "开票日期",
    "buyer_name": "购买方名称",
    "seller_name": "销售方名称",
    "amount": "金额",
    "total_amount": "价税合计"
}
只输出JSON，不要其他内容。"""

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
            max_tokens=1024
        )
        
        # 预热
        print("[vLLM] 预热推理...")
        _ = llm.chat(messages, sampling_params)
        clear_gpu_memory()
        
        # 正式测试
        print("[vLLM] 开始 OCR 推理测试...")
        inference_times = []
        for i in range(3):
            start = time.time()
            outputs = llm.chat(messages, sampling_params)
            inference_time = time.time() - start
            inference_times.append(inference_time)
            print(f"[vLLM] 第 {i+1} 次 OCR 推理耗时: {inference_time:.2f}秒")
        
        avg_inference_time = sum(inference_times) / len(inference_times)
        
        result_text = outputs[0].outputs[0].text
        print(f"[vLLM] OCR 结果: {result_text[:200]}...")
        
        # 清理
        del llm
        clear_gpu_memory()
        
        return {
            'load_time': load_time,
            'avg_inference_time': avg_inference_time,
            'inference_times': inference_times,
            'success': True
        }
        
    except Exception as e:
        print(f"[vLLM] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        clear_gpu_memory()
        return {
            'success': False,
            'error': str(e)
        }

def test_unified_vl(image_path: str):
    """测试 Unified VL 服务"""
    print("\n" + "="*60)
    print("测试 Unified VL 服务")
    print("="*60)
    
    clear_gpu_memory()
    
    try:
        from backend.services.unified_vl_service import UnifiedVLService
        
        # 记录加载时间
        print("[UnifiedVL] 开始加载模型...")
        load_start = time.time()
        
        service = UnifiedVLService()
        
        load_time = time.time() - load_start
        print(f"[UnifiedVL] 模型加载完成，耗时: {load_time:.2f}秒")
        print(f"[UnifiedVL] 显存使用: {torch.cuda.memory_allocated()/1024**3:.2f} GB")
        
        # 预热
        print("[UnifiedVL] 预热推理...")
        _ = service.process_invoice(image_path)
        clear_gpu_memory()
        
        # 正式测试
        print("[UnifiedVL] 开始推理测试...")
        inference_times = []
        for i in range(3):
            start = time.time()
            result = service.process_invoice(image_path)
            inference_time = time.time() - start
            inference_times.append(inference_time)
            print(f"[UnifiedVL] 第 {i+1} 次推理耗时: {inference_time:.2f}秒")
        
        avg_inference_time = sum(inference_times) / len(inference_times)
        
        print(f"[UnifiedVL] OCR 结果: {result.get('data', {})}")
        
        # 测试合并模式
        print("[UnifiedVL] 测试合并模式 (OCR + 分析)...")
        combined_times = []
        for i in range(3):
            start = time.time()
            result = service.process_invoice_combined(image_path)
            combined_time = time.time() - start
            combined_times.append(combined_time)
            print(f"[UnifiedVL] 第 {i+1} 次合并推理耗时: {combined_time:.2f}秒")
        
        avg_combined_time = sum(combined_times) / len(combined_times)
        
        # 清理
        del service
        clear_gpu_memory()
        
        return {
            'load_time': load_time,
            'avg_inference_time': avg_inference_time,
            'inference_times': inference_times,
            'avg_combined_time': avg_combined_time,
            'combined_times': combined_times,
            'success': True
        }
        
    except Exception as e:
        print(f"[UnifiedVL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        clear_gpu_memory()
        return {
            'success': False,
            'error': str(e)
        }

def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--vllm', action='store_true', help='只测试 vLLM')
    parser.add_argument('--unified', action='store_true', help='只测试 Unified VL')
    args = parser.parse_args()
    
    # 测试图片
    image_path = "/root/autodl-tmp/caiwubaoxiao/data/data/b0.jpg"
    
    if not os.path.exists(image_path):
        print(f"测试图片不存在: {image_path}")
        return
    
    print(f"测试图片: {image_path}")
    
    results = {}
    
    if args.vllm:
        # 只测试 vLLM
        results['vllm'] = test_vllm(image_path)
    elif args.unified:
        # 只测试 Unified VL
        results['unified_vl'] = test_unified_vl(image_path)
    else:
        # 默认：先测试 Unified VL，再测试 vLLM
        results['unified_vl'] = test_unified_vl(image_path)
        results['vllm'] = test_vllm(image_path)
    
    # 打印对比结果
    print("\n" + "="*60)
    print("性能对比结果")
    print("="*60)
    
    if 'unified_vl' in results and results['unified_vl']['success']:
        print(f"\nUnified VL 服务:")
        print(f"  - 模型加载时间: {results['unified_vl']['load_time']:.2f}秒")
        print(f"  - OCR 平均推理时间: {results['unified_vl']['avg_inference_time']:.2f}秒")
        print(f"  - 合并模式平均时间: {results['unified_vl']['avg_combined_time']:.2f}秒")
    elif 'unified_vl' in results:
        print(f"\nUnified VL 服务测试失败: {results['unified_vl'].get('error', 'Unknown error')}")
    
    if 'vllm' in results and results['vllm']['success']:
        print(f"\nvLLM 服务:")
        print(f"  - 模型加载时间: {results['vllm']['load_time']:.2f}秒")
        print(f"  - OCR 平均推理时间: {results['vllm']['avg_inference_time']:.2f}秒")
    elif 'vllm' in results:
        print(f"\nvLLM 服务测试失败: {results['vllm'].get('error', 'Unknown error')}")
    
    # 结论
    print("\n" + "="*60)
    print("结论")
    print("="*60)
    
    if 'unified_vl' in results and 'vllm' in results and results['unified_vl']['success'] and results['vllm']['success']:
        unified_time = results['unified_vl']['avg_combined_time']
        vllm_time = results['vllm']['avg_inference_time']
        
        if vllm_time < unified_time:
            speedup = (unified_time - vllm_time) / unified_time * 100
            print(f"vLLM 更快，提速 {speedup:.1f}%")
            print("建议: 切换到 vLLM 方案")
        else:
            speedup = (vllm_time - unified_time) / unified_time * 100
            print(f"Unified VL 更快，提速 {speedup:.1f}%")
            print("建议: 继续使用 Unified VL 方案")

if __name__ == "__main__":
    main()
