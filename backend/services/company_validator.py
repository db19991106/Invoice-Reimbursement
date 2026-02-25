from typing import List, Dict, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import json
import os


@dataclass
class CompanyMatchResult:
    is_match: bool
    matched_company: Optional[Dict]
    match_type: str
    message: str
    confidence: float


class CompanyValidator:
    def __init__(self):
        self._whitelist = []
        self._buyer_whitelist = []  # 购买方白名单
        self._initialized = False
        self._config_path = "/root/autodl-tmp/caiwubaoxiao/data/company_whitelist.json"
    
    def init_default_companies(self):
        # 尝试从配置文件加载
        if self._load_from_config():
            return
        
        # 默认购买方公司（本公司）
        self._buyer_whitelist = [
            {
                "id": 1,
                "name": "中航电测仪器(西安)有限公司",
                "short_name": "中航电测",
                "tax_id": "91610131742598XXXX",
                "aliases": [
                    "中航电测仪器（西安）有限公司",
                    "中航电测仪器西安有限公司"
                ]
            }
        ]
        
        # 默认销售方公司白名单
        self._whitelist = [
            {
                "id": 1,
                "name": "示例科技有限公司",
                "short_name": "示例科技",
                "tax_id": "91110000123456789X"
            }
        ]
        
        self._initialized = True
    
    def _load_from_config(self):
        """从配置文件加载公司白名单"""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._buyer_whitelist = config.get('buyer_companies', [])
                    self._whitelist = config.get('seller_companies', [])
                    self._initialized = True
                    return True
        except Exception as e:
            print(f"加载公司配置失败: {e}")
        return False
    
    def save_to_config(self):
        """保存公司白名单到配置文件"""
        config = {
            'buyer_companies': self._buyer_whitelist,
            'seller_companies': self._whitelist
        }
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        with open(self._config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def add_buyer_company(self, company: Dict):
        """添加购买方公司"""
        if not self._initialized:
            self.init_default_companies()
        
        company["id"] = max([c.get("id", 0) for c in self._buyer_whitelist], default=0) + 1
        self._buyer_whitelist.append(company)
        self.save_to_config()
    
    def add_seller_company(self, company: Dict):
        """添加销售方公司"""
        if not self._initialized:
            self.init_default_companies()
        
        company["id"] = max([c.get("id", 0) for c in self._whitelist], default=0) + 1
        self._whitelist.append(company)
        self.save_to_config()
    
    def set_buyer_whitelist(self, companies: List[Dict]):
        """设置购买方白名单"""
        self._buyer_whitelist = companies
        self.save_to_config()
    
    def get_buyer_whitelist(self) -> List[Dict]:
        if not self._initialized:
            self.init_default_companies()
        return self._buyer_whitelist
    
    def set_whitelist(self, companies: List[Dict]):
        self._whitelist = companies
        self.save_to_config()
    
    def add_company(self, company: Dict):
        if not self._initialized:
            self.init_default_companies()
        
        company["id"] = max([c.get("id", 0) for c in self._whitelist], default=0) + 1
        self._whitelist.append(company)
        self.save_to_config()
    
    def get_whitelist(self) -> List[Dict]:
        if not self._initialized:
            self.init_default_companies()
        return self._whitelist
    
    def validate_buyer(
        self,
        buyer_name: str,
        buyer_tax_id: str,
        require_exact_match: bool = False
    ) -> CompanyMatchResult:
        """验证购买方公司是否在白名单中（需要同时匹配名称和税号）"""
        if not self._initialized:
            self.init_default_companies()
        
        if not buyer_name and not buyer_tax_id:
            return CompanyMatchResult(
                is_match=True,  # 如果没有购买方信息，默认通过
                matched_company=None,
                match_type="none",
                message="缺少购买方信息，默认通过",
                confidence=0.0
            )
        
        # 标准化后的购买方信息
        normalized_name = self._normalize(buyer_name) if buyer_name else ""
        normalized_tax_id = buyer_tax_id.strip().upper() if buyer_tax_id else ""
        
        # 第一优先级：税号精确匹配
        if normalized_tax_id:
            for company in self._buyer_whitelist:
                company_tax_id = company.get("tax_id", "").upper()
                if company_tax_id and company_tax_id == normalized_tax_id:
                    # 税号匹配，检查名称是否也匹配
                    company_name_normalized = self._normalize(company.get("name", ""))
                    name_matched = (normalized_name == company_name_normalized or 
                                   any(normalized_name == self._normalize(alias) 
                                       for alias in company.get("aliases", [])))
                    
                    if name_matched:
                        return CompanyMatchResult(
                            is_match=True,
                            matched_company=company,
                            match_type="both",
                            message=f"购买方名称和税号均匹配: {company['name']}",
                            confidence=1.0
                        )
                    else:
                        # 税号匹配但名称不匹配，可能是异常
                        return CompanyMatchResult(
                            is_match=False,
                            matched_company=company,
                            match_type="tax_id_only",
                            message=f"购买方税号匹配但名称不匹配: 发票显示'{buyer_name}'，应为'{company['name']}'",
                            confidence=0.5
                        )
        
        # 第二优先级：名称匹配
        for company in self._buyer_whitelist:
            company_name_normalized = self._normalize(company.get("name", ""))
            company_tax_id = company.get("tax_id", "").upper()
            
            # 名称精确匹配（标准化后）
            name_matched = (normalized_name and normalized_name == company_name_normalized)
            
            # 检查别名
            if not name_matched:
                for alias in company.get("aliases", []):
                    if normalized_name and normalized_name == self._normalize(alias):
                        name_matched = True
                        break
            
            if name_matched:
                # 名称匹配，检查税号
                if company_tax_id:
                    if normalized_tax_id and normalized_tax_id == company_tax_id:
                        return CompanyMatchResult(
                            is_match=True,
                            matched_company=company,
                            match_type="both",
                            message=f"购买方名称和税号均匹配: {company['name']}",
                            confidence=1.0
                        )
                    elif normalized_tax_id:
                        # 名称匹配但税号不匹配
                        return CompanyMatchResult(
                            is_match=False,
                            matched_company=company,
                            match_type="name_only",
                            message=f"购买方名称匹配但税号不匹配: 发票显示'{buyer_tax_id}'，应为'{company_tax_id}'",
                            confidence=0.5
                        )
                    else:
                        # 名称匹配但发票没有税号
                        return CompanyMatchResult(
                            is_match=False,
                            matched_company=company,
                            match_type="name_only",
                            message=f"购买方名称匹配但发票缺少税号，应为'{company_tax_id}'",
                            confidence=0.6
                        )
        
        # 模糊匹配
        if buyer_name:
            best_match = None
            best_score = 0.0
            
            for company in self._buyer_whitelist:
                company_name = company.get("name", "")
                short_name = company.get("short_name", "")
                
                score1 = self._fuzzy_match(buyer_name, company_name)
                score2 = self._fuzzy_match(buyer_name, short_name) if short_name else 0
                
                # 检查别名
                for alias in company.get("aliases", []):
                    score3 = self._fuzzy_match(buyer_name, alias)
                    score2 = max(score2, score3)
                
                score = max(score1, score2)
                
                if score > best_score:
                    best_score = score
                    best_match = company
            
            if best_score >= 0.85 and best_match:
                return CompanyMatchResult(
                    is_match=False,
                    matched_company=best_match,
                    match_type="name_fuzzy",
                    message=f"购买方名称模糊匹配: '{buyer_name}' 疑似 '{best_match['name']}' ({best_score:.0%})，需人工确认",
                    confidence=best_score
                )
        
        return CompanyMatchResult(
            is_match=False,
            matched_company=None,
            match_type="none",
            message=f"购买方不在白名单中: {buyer_name} ({buyer_tax_id})",
            confidence=0.0
        )
    
    def validate(
        self,
        seller_name: str,
        seller_tax_id: str,
        require_exact_match: bool = False
    ) -> CompanyMatchResult:
        """验证销售方公司（原有逻辑）"""
        if not self._initialized:
            self.init_default_companies()
        
        if not seller_name and not seller_tax_id:
            return CompanyMatchResult(
                is_match=True,  # 如果没有销售方信息，默认通过
                matched_company=None,
                match_type="none",
                message="缺少销售方信息，默认通过",
                confidence=0.0
            )
        
        if seller_tax_id:
            for company in self._whitelist:
                if company.get("tax_id", "").upper() == seller_tax_id.upper():
                    return CompanyMatchResult(
                        is_match=True,
                        matched_company=company,
                        match_type="tax_id",
                        message=f"税号精确匹配: {company['name']}",
                        confidence=1.0
                    )
        
        if seller_name:
            best_match = None
            best_score = 0.0
            
            for company in self._whitelist:
                company_name = company.get("name", "")
                short_name = company.get("short_name", "")
                
                score1 = self._fuzzy_match(seller_name, company_name)
                score2 = self._fuzzy_match(seller_name, short_name) if short_name else 0
                score3 = self._fuzzy_match(seller_name.replace("有限公司", "").replace("股份有限公司", ""), 
                                            company_name.replace("有限公司", "").replace("股份有限公司", ""))
                
                score = max(score1, score2, score3)
                
                if score > best_score:
                    best_score = score
                    best_match = company
            
            if best_score >= 0.85:
                return CompanyMatchResult(
                    is_match=True,
                    matched_company=best_match,
                    match_type="name",
                    message=f"发票抬头匹配: {best_match['name']}",
                    confidence=best_score
                )
            elif best_score >= 0.6:
                if require_exact_match:
                    return CompanyMatchResult(
                        is_match=False,
                        matched_company=best_match,
                        match_type="name_fuzzy",
                        message=f"发票抬头疑似 {best_match['name']}，但匹配度仅 {best_score:.0%}",
                        confidence=best_score
                    )
                else:
                    return CompanyMatchResult(
                        is_match=True,
                        matched_company=best_match,
                        match_type="name_fuzzy",
                        message=f"发票抬头模糊匹配: {best_match['name']}",
                        confidence=best_score
                    )
        
        # 如果不在白名单，默认通过（不强制要求）
        return CompanyMatchResult(
            is_match=True,
            matched_company=None,
            match_type="not_in_whitelist",
            message=f"销售方不在白名单中: {seller_name} ({seller_tax_id})，默认通过",
            confidence=0.0
        )
    
    def _fuzzy_match(self, text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0
        
        text1 = self._normalize(text1)
        text2 = self._normalize(text2)
        
        if text1 == text2:
            return 1.0
        
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _normalize(self, text: str) -> str:
        """标准化文本：统一括号、去除空格等"""
        if not text:
            return ""
        text = text.strip().upper()
        text = re.sub(r'\s+', '', text)
        # 统一中文括号和英文括号
        text = text.replace('（', '(').replace('）', ')')
        text = text.replace('【', '[').replace('】', ']')
        # 去除常见后缀进行比对
        text = text.replace('有限公司', '').replace('股份有限公司', '')
        text = text.replace('LIMITED', '').replace('LTD', '')
        return text
    
    def validate_tax_id_format(self, tax_id: str) -> Dict:
        if not tax_id:
            return {"valid": False, "message": "税号为空"}
        
        if len(tax_id) not in [15, 18, 20]:
            return {"valid": False, "message": f"税号长度 {len(tax_id)} 非法(应为15/18/20位)"}
        
        if not re.match(r'^[0-9A-Z]+$', tax_id.upper()):
            return {"valid": False, "message": "税号只能包含数字和大写字母"}
        
        return {"valid": True, "message": "税号格式正确"}


company_validator = CompanyValidator()


def get_company_validator() -> CompanyValidator:
    return company_validator
