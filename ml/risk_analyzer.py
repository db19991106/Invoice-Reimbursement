import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import faiss
import numpy as np
import pickle
from typing import List, Dict, Optional
from pathlib import Path
from sentence_transformers import SentenceTransformer
from backend.config import settings


class RiskAnalyzer:
    def __init__(self):
        self.embedding_model = None
        self.faiss_index = None
        self.invoice_vectors = []
        self.invoice_ids = []
        self._initialized = False
        
        # 使用本地 BGE-large-zh-v1.5 模型
        self.model_path = "/root/autodl-tmp/models/bge-large-zh-v1.5"
        self.embedding_dim = 1024  # BGE-large-zh-v1.5 的向量维度
    
    def init_embedding_model(self):
        if self._initialized:
            return
        try:
            print(f"Loading embedding model from: {self.model_path}")
            # 强制使用 CPU，为 vLLM 腾出 GPU 显存
            self.embedding_model = SentenceTransformer(self.model_path, device='cpu')
            self._initialized = True
            print("Embedding model loaded successfully (BGE-large-zh-v1.5) on CPU")
        except Exception as e:
            print(f"Failed to load embedding model: {e}")
            # 回退到默认模型
            try:
                self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device='cpu')
                self.embedding_dim = 384
                self._initialized = True
                print("Fallback to default embedding model on CPU")
            except Exception as e2:
                print(f"Failed to load fallback model: {e2}")
    
    def _parse_date(self, date_str: str) -> Optional[tuple]:
        """解析多种日期格式，返回 (year, month, day) 元组
        
        支持格式：
        - YYYY-MM-DD
        - YYYY/MM/DD
        - YYYY年MM月DD日
        - YYYYMMDD
        """
        import re
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # 格式1: YYYY年MM月DD日
        match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
        if match:
            return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        
        # 格式2: YYYY-MM-DD 或 YYYY/MM/DD
        match = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str)
        if match:
            return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        
        # 格式3: YYYYMMDD
        match = re.match(r'(\d{4})(\d{2})(\d{2})', date_str)
        if match:
            return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        
        return None
    
    def create_index(self):
        self.init_embedding_model()
        self.faiss_index = faiss.IndexFlatL2(self.embedding_dim)
        print(f"FAISS index created with dimension {self.embedding_dim}")
    
    def add_invoice(self, invoice_id: int, invoice_text: str):
        if not self.faiss_index:
            self.create_index()
        
        if self.embedding_model:
            vector = self.embedding_model.encode([invoice_text])[0]
            self.faiss_index.add(np.array([vector]).astype('float32'))
            self.invoice_ids.append(invoice_id)
            self.invoice_vectors.append(invoice_text)
    
    def find_similar(self, invoice_text: str, top_k: int = 5) -> List[Dict]:
        if not self.faiss_index or not self.embedding_model:
            return []
        
        query_vector = self.embedding_model.encode([invoice_text])[0]
        distances, indices = self.faiss_index.search(
            np.array([query_vector]).astype('float32'), 
            min(top_k, len(self.invoice_ids))
        )
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.invoice_ids):
                results.append({
                    'invoice_id': self.invoice_ids[idx],
                    'text': self.invoice_vectors[idx],
                    'distance': float(dist),
                    'similarity': float(1 / (1 + dist))
                })
        return results
    
    def save_index(self, path: str):
        if self.faiss_index:
            faiss.write_index(self.faiss_index, f"{path}/index.faiss")
            with open(f"{path}/metadata.pkl", 'wb') as f:
                pickle.dump({
                    'ids': self.invoice_ids,
                    'vectors': self.invoice_vectors
                }, f)
            print(f"Index saved to {path}")
    
    def load_index(self, path: str):
        if os.path.exists(f"{path}/index.faiss"):
            self.faiss_index = faiss.read_index(f"{path}/index.faiss")
            with open(f"{path}/metadata.pkl", 'rb') as f:
                data = pickle.load(f)
                self.invoice_ids = data['ids']
                self.invoice_vectors = data['vectors']
            self._initialized = True
            print(f"Index loaded from {path}")
    
    def calculate_risk_score(
        self,
        invoice_data: Dict,
        ocr_confidence: float,
        signature_score: Optional[float] = None,
        similar_invoices: Optional[List[Dict]] = None
    ) -> Dict:
        risk_factors = []
        risk_score = 0.0
        
        if ocr_confidence < 0.7:
            risk_score += 0.3
            risk_factors.append(f"OCR识别置信度较低 ({ocr_confidence:.2f})")
        
        amount = invoice_data.get('amount', 0)
        total = invoice_data.get('total_amount', 0)
        
        if amount and amount > 10000:
            risk_score += 0.2
            risk_factors.append(f"发票金额较大 (¥{amount:.2f})")
        
        if similar_invoices:
            for sim in similar_invoices:
                if sim['similarity'] > 0.9:
                    risk_score += 0.4
                    risk_factors.append(f"疑似重复报销 (相似度: {sim['similarity']:.2f})")
                    break
        
        if signature_score is not None:
            if signature_score < 0.5:
                risk_score += 0.4
                risk_factors.append(f"签名不匹配 (相似度: {signature_score:.2f})")
            elif signature_score < 0.7:
                risk_score += 0.2
                risk_factors.append(f"签名存疑 (相似度: {signature_score:.2f})")
        
        date = invoice_data.get('date')
        if date:
            parsed_date = self._parse_date(date)
            if parsed_date:
                year, month, day = parsed_date
                if month > 12 or month < 1 or day > 31 or day < 1:
                    risk_score += 0.2
                    risk_factors.append("发票日期格式异常")
                if year < 2020 or year > 2030:
                    risk_score += 0.15
                    risk_factors.append("发票年份异常")
            else:
                risk_score += 0.1
                risk_factors.append("无法解析发票日期")
        
        seller_tax_id = invoice_data.get('seller_tax_id')
        if seller_tax_id:
            # 纳税人识别号：15位(老版)、17位(部分统一信用代码)、18位(统一信用代码)、20位
            if len(seller_tax_id) not in [15, 17, 18, 20]:
                risk_score += 0.15
                risk_factors.append("纳税人识别号格式异常")
        
        risk_score = min(risk_score, 1.0)
        
        if risk_score >= 0.8:
            risk_level = "high"
        elif risk_score >= 0.5:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors
        }
    
    def make_decision(self, risk_level: str, risk_score: float) -> str:
        if risk_level == "high":
            return "reject"
        elif risk_level == "medium":
            return "review"
        else:
            return "approve"


risk_analyzer = RiskAnalyzer()
