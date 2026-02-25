#!/usr/bin/env python3
import os
os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['FLAGS_enable_onednn'] = '0'
os.environ['FLAGS_use_mkldnn'] = '0'

import sys
sys.path.insert(0, '/root/autodl-tmp/caiwubaoxiao')
sys.path.insert(0, '/root/autodl-tmp/caiwubaoxiao/backend')

from ml.invoice_ocr import InvoiceOCR
import json

ocr = InvoiceOCR()
print('OCR initialized')

test_image = '/root/autodl-tmp/caiwubaoxiao/ChiSig/丁会-107-1.jpg'
result, confidence = ocr.process_image(test_image)

print(f'Confidence: {confidence}')
print(f'Raw text count: {len(result.get("raw_text", []))}')
print('Extracted fields:')
for key, value in result.items():
    if key != 'raw_text':
        print(f'  {key}: {value}')
print()
print('Sample raw text (first 10):')
for i, text in enumerate(result.get('raw_text', [])[:10]):
    print(f'  {i+1}. {text}')
