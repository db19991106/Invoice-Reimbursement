#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['FLAGS_enable_onednn'] = '0'
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

from ml.invoice_ocr import InvoiceOCR

def main():
    ocr = InvoiceOCR(enable_preprocessing=False)
    
    test_file = "/root/autodl-tmp/caiwubaoxiao/data/data/b14.jpg"
    
    print("=" * 70)
    print("发票识别测试")
    print("=" * 70)
    print(f"测试文件: {test_file}")
    print()
    
    result, confidence = ocr.process_image(test_file)
    
    print("【识别结果】")
    print("-" * 50)
    fields = [
        ("发票号码", result.get("invoice_no")),
        ("开票日期", result.get("date")),
        ("销售方名称", result.get("seller_name")),
        ("购买方名称", result.get("buyer_name")),
        ("金额", result.get("amount")),
        ("税额", result.get("tax_amount")),
        ("价税合计", result.get("total_amount")),
        ("销售方税号", result.get("seller_tax_id")),
        ("购买方税号", result.get("buyer_tax_id")),
    ]
    
    for name, value in fields:
        print(f"{name:12s}: {value}")
    
    print()
    print("【预期结果】")
    print("-" * 50)
    expected = [
        ("发票号码", "66215500"),
        ("开票日期", "2016-06-12"),
        ("销售方名称", "广州晶东贸易有限公司"),
        ("购买方名称", "深圳市购机汇网络有限公司"),
        ("金额", "2987.18"),
        ("税额", "507.82"),
        ("价税合计", "3495.00"),
        ("销售方税号", "91440101664041243T"),
    ]
    
    for name, value in expected:
        print(f"{name:12s}: {value}")
    
    print()
    print("【对比结果】")
    print("-" * 50)
    match = 0
    total = len(expected)
    for (name, exp_val), (_, act_val) in zip(expected, fields):
        status = "✓" if str(act_val) == str(exp_val) else "✗"
        print(f"{status} {name:12s}: 识别={act_val} | 预期={exp_val}")
        if str(act_val) == str(exp_val):
            match += 1
    
    print()
    print(f"准确率: {match}/{total} = {match*100//total}%")

if __name__ == "__main__":
    main()
