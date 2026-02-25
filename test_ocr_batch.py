import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['FLAGS_enable_onednn'] = '0'
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

from ml.invoice_ocr import InvoiceOCR
import glob

ocr = InvoiceOCR(enable_preprocessing=False)

# 测试多张图片
test_dir = "/root/autodl-tmp/caiwubaoxiao/data/data"
test_files = sorted(glob.glob(f"{test_dir}/b*.jpg"))[:5]

for test_image in test_files:
    print("="*70)
    print(f"测试文件: {os.path.basename(test_image)}")
    print("="*70)
    
    result, confidence = ocr.process_image(test_image)
    
    print(f"\n【识别结果】(置信度: {confidence:.2%})")
    print("-"*50)
    print(f"发票号码: {result.get('invoice_no')}")
    print(f"开票日期: {result.get('date')}")
    print(f"销售方: {result.get('seller_name')}")
    print(f"购买方: {result.get('buyer_name')}")
    print(f"金额: {result.get('amount')}")
    print(f"税额: {result.get('tax_amount')}")
    print(f"价税合计: {result.get('total_amount')}")
    print(f"销售方税号: {result.get('seller_tax_id')}")
    print(f"购买方税号: {result.get('buyer_tax_id')}")
    print()
