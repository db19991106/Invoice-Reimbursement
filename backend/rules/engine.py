from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import re
from datetime import datetime, date


class EmployeeType(Enum):
    REGULAR = "regular"      # 普通员工 9-10级
    MANAGEMENT = "management"  # 管理层 11级+


class CityTier(Enum):
    TIER_1 = "tier_1"      # 一类城市: 北上广深
    TIER_2 = "tier_2"      # 二类城市: 省会/计划单列市
    TIER_3 = "tier_3"      # 三类及以下


class ExpenseType(Enum):
    ACCOMMODATION = "accommodation"  # 住宿费
    TRANSPORT_AIR = "transport_air"  # 飞机
    TRANSPORT_TRAIN = "transport_train"  # 高铁/动车
    TRANSPORT_REGULAR = "transport_regular"  # 普通火车
    TRANSPORT_SHIP = "transport_ship"  # 轮船
    CITY_TRANSPORT = "city_transport"  # 市内交通
    MEAL = "meal"  # 伙食补助
    BUSINESS_ENTERTAINMENT = "business_entertainment"  # 业务招待


class CheckResult(Enum):
    PASS = "pass"
    WARNING = "warning"
    REJECT = "reject"


@dataclass
class RuleCheckItem:
    rule_name: str
    result: CheckResult
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    channel: str  # green, yellow, red
    items: List[RuleCheckItem] = field(default_factory=list)
    summary: str = ""
    
    @property
    def is_pass(self) -> bool:
        return self.channel in ["green", "yellow"]
    
    @property
    def is_auto_pass(self) -> bool:
        return self.channel == "green"
    
    @property
    def has_reject(self) -> bool:
        return any(item.result == CheckResult.REJECT for item in self.items)


class RuleEngine:
    def __init__(self):
        self._standards = {}
        self._company_whitelist = []
        self._load_standards()
    
    def _load_standards(self):
        from backend.rules.standards import (
            accommodation_standards,
            transport_standards,
            daily_standards,
            business_entertainment_standards
        )
        self._standards = {
            ExpenseType.ACCOMMODATION: accommodation_standards,
            ExpenseType.TRANSPORT_AIR: transport_standards.get("air", {}),
            ExpenseType.TRANSPORT_TRAIN: transport_standards.get("train", {}),
            ExpenseType.TRANSPORT_REGULAR: transport_standards.get("regular", {}),
            ExpenseType.TRANSPORT_SHIP: transport_standards.get("ship", {}),
            ExpenseType.CITY_TRANSPORT: daily_standards.get("city_transport", {}),
            ExpenseType.MEAL: daily_standards.get("meal", {}),
            ExpenseType.BUSINESS_ENTERTAINMENT: business_entertainment_standards,
        }
    
    def set_company_whitelist(self, whitelist: List[Dict]):
        self._company_whitelist = whitelist
    
    def get_employee_type(self, level: int) -> EmployeeType:
        if level >= 11:
            return EmployeeType.MANAGEMENT
        return EmployeeType.REGULAR
    
    def get_city_tier(self, city_name: str) -> CityTier:
        tier1_cities = ["北京", "上海", "广州", "深圳", "北京市", "上海市", "广州市", "深圳市"]
        tier2_cities = [
            "天津", "重庆", "成都", "杭州", "南京", "武汉", "西安", "郑州", "长沙", "沈阳",
            "青岛", "济南", "大连", "宁波", "厦门", "福州", "无锡", "合肥", "昆明", "哈尔滨",
            "长春", "南昌", "贵阳", "太原", "石家庄", "兰州", "乌鲁木齐", "呼和浩特", "银川", "西宁",
            "拉萨", "海口", "三亚", "苏州", "东莞", "佛山", "温州", "泉州", "无锡", "徐州"
        ]
        
        for city in tier1_cities:
            if city in city_name:
                return CityTier.TIER_1
        
        for city in tier2_cities:
            if city in city_name:
                return CityTier.TIER_2
        
        return CityTier.TIER_3
    
    def get_standard(self, expense_type: ExpenseType, employee_type: EmployeeType, city_tier: CityTier) -> Optional[Dict]:
        standards = self._standards.get(expense_type, {})
        if not standards:
            return None
        
        emp_key = employee_type.value
        tier_key = city_tier.value
        
        return standards.get(tier_key, {}).get(emp_key)
    
    def validate_accommodation(
        self,
        total_amount: float,
        days: int,
        city_tier: CityTier,
        employee_type: EmployeeType,
        detail_type: str = None
    ) -> RuleCheckItem:
        standard = self.get_standard(ExpenseType.ACCOMMODATION, employee_type, city_tier)
        if not standard:
            return RuleCheckItem(
                rule_name="accommodation_standard",
                result=CheckResult.PASS,
                message="无住宿费标准限制"
            )
        
        daily_limit = standard.get("daily_limit", 99999)
        actual_daily = total_amount / days if days > 0 else total_amount
        
        if actual_daily <= daily_limit:
            return RuleCheckItem(
                rule_name="accommodation_standard",
                result=CheckResult.PASS,
                message=f"住宿费日均 ¥{actual_daily:.2f}，未超标",
                details={"daily_limit": daily_limit, "actual_daily": actual_daily}
            )
        else:
            excess = actual_daily - daily_limit
            excess_pct = (excess / daily_limit) * 100
            
            if excess_pct > 10:
                return RuleCheckItem(
                    rule_name="accommodation_standard",
                    result=CheckResult.REJECT,
                    message=f"住宿费日均 ¥{actual_daily:.2f} 超出标准 ¥{daily_limit}，超标 {excess_pct:.1f}%，需自费或重新提交",
                    details={"daily_limit": daily_limit, "actual_daily": actual_daily, "excess": excess}
                )
            else:
                return RuleCheckItem(
                    rule_name="accommodation_standard",
                    result=CheckResult.WARNING,
                    message=f"住宿费日均 ¥{actual_daily:.2f} 略超标准 ¥{daily_limit}，请确认",
                    details={"daily_limit": daily_limit, "actual_daily": actual_daily, "excess": excess}
                )
    
    def validate_transport_air(
        self,
        seat_type: str,
        employee_type: EmployeeType
    ) -> RuleCheckItem:
        standard = self._standards.get(ExpenseType.TRANSPORT_AIR, {})
        if not standard:
            return RuleCheckItem(
                rule_name="air_standard",
                result=CheckResult.PASS,
                message="无机票标准限制"
            )
        
        allowed_seats = standard.get(employee_type.value, ["经济舱"])
        seat_map = {
            "经济舱": 1, "公务舱": 2, "头等舱": 3,
            "商务舱": 2, "全价经济舱": 1
        }
        
        recognized_seat = self._recognize_seat(seat_type)
        recognized_level = seat_map.get(recognized_seat, 1)
        
        max_allowed = max([seat_map.get(s, 1) for s in allowed_seats], default=1)
        
        if recognized_level <= max_allowed:
            return RuleCheckItem(
                rule_name="air_standard",
                result=CheckResult.PASS,
                message=f"机票舱位 {seat_type} 符合标准",
                details={"seat_type": seat_type, "allowed": allowed_seats}
            )
        else:
            return RuleCheckItem(
                rule_name="air_standard",
                result=CheckResult.REJECT,
                message=f"普通员工({employee_type.value})不允许乘坐 {seat_type}，仅允许 {'/'.join(allowed_seats)}",
                details={"seat_type": seat_type, "allowed": allowed_seats}
            )
    
    def validate_transport_train(
        self,
        seat_type: str,
        employee_type: EmployeeType,
        duration_hours: float = None
    ) -> RuleCheckItem:
        standard = self._standards.get(ExpenseType.TRANSPORT_TRAIN, {})
        if not standard:
            return RuleCheckItem(
                rule_name="train_standard",
                result=CheckResult.PASS,
                message="无火车标准限制"
            )
        
        allowed_seats = standard.get(employee_type.value, ["二等座"])
        recognized_seat = self._recognize_seat(seat_type)
        
        if recognized_seat in allowed_seats:
            return RuleCheckItem(
                rule_name="train_standard",
                result=CheckResult.PASS,
                message=f"火车席别 {seat_type} 符合标准",
                details={"seat_type": seat_type, "allowed": allowed_seats}
            )
        
        if duration_hours and duration_hours > 6:
            night_allowed = standard.get("night_allowed", {}).get(employee_type.value, [])
            if recognized_seat in night_allowed:
                return RuleCheckItem(
                    rule_name="train_standard",
                    result=CheckResult.PASS,
                    message=f"夜间车次(>{duration_hours}小时)允许乘坐 {seat_type}",
                    details={"seat_type": seat_type, "duration_hours": duration_hours}
                )
        
        return RuleCheckItem(
            rule_name="train_standard",
            result=CheckResult.REJECT,
            message=f"火车席别 {seat_type} 不符合标准，仅允许 {'/'.join(allowed_seats)}",
            details={"seat_type": seat_type, "allowed": allowed_seats}
        )
    
    def validate_city_transport(
        self,
        days: int,
        amount: float,
        employee_type: EmployeeType
    ) -> RuleCheckItem:
        standard = self._standards.get(ExpenseType.CITY_TRANSPORT, {}).get(employee_type.value, {})
        daily_limit = standard.get("daily", 80)
        total_limit = daily_limit * days
        
        if amount <= total_limit:
            return RuleCheckItem(
                rule_name="city_transport_standard",
                result=CheckResult.PASS,
                message=f"市内交通费 ¥{amount:.2f}，{days}天共计 ¥{total_limit:.2f}，未超标",
                details={"daily_limit": daily_limit, "days": days, "total_limit": total_limit, "actual": amount}
            )
        else:
            excess = amount - total_limit
            return RuleCheckItem(
                rule_name="city_transport_standard",
                result=CheckResult.WARNING,
                message=f"市内交通费 ¥{amount:.2f} 超标 ¥{excess:.2f}，按标准应发 ¥{total_limit:.2f}",
                details={"daily_limit": daily_limit, "days": days, "total_limit": total_limit, "actual": amount, "excess": excess}
            )
    
    def validate_meal(
        self,
        days: int,
        has_entertainment: bool,
        entertainment_amount: float,
        employee_type: EmployeeType
    ) -> RuleCheckItem:
        standard = self._standards.get(ExpenseType.MEAL, {}).get(employee_type.value, {})
        daily_limit = standard.get("daily", 100)
        total_allowance = daily_limit * days
        
        if has_entertainment and entertainment_amount > 0:
            deduction = min(entertainment_amount, daily_limit * len([1 for _ in range(days) if True]))
            total_allowance = max(0, total_allowance - deduction)
        
        return RuleCheckItem(
            rule_name="meal_standard",
            result=CheckResult.PASS,
            message=f"伙食补助标准 ¥{total_allowance:.2f}/天 × {days}天",
            details={"daily_limit": daily_limit, "days": days, "total": total_allowance}
        )
    
    def validate_business_entertainment(
        self,
        total_amount: float,
        person_count: int,
        employee_type: EmployeeType
    ) -> RuleCheckItem:
        standard = self._standards.get(ExpenseType.BUSINESS_ENTERTAINMENT, {}).get(employee_type.value, {})
        per_person_limit = standard.get("per_person", 150)
        total_limit = per_person_limit * person_count
        
        if total_amount <= total_limit:
            return RuleCheckItem(
                rule_name="business_entertainment_standard",
                result=CheckResult.PASS,
                message=f"业务招待人均 ¥{total_amount/person_count:.2f}/人，未超标",
                details={"per_person_limit": per_person_limit, "person_count": person_count, "actual_per_person": total_amount/person_count}
            )
        else:
            excess = (total_amount / person_count) - per_person_limit
            return RuleCheckItem(
                rule_name="business_entertainment_standard",
                result=CheckResult.WARNING,
                message=f"业务招待人均 ¥{total_amount/person_count:.2f} 超标 ¥{excess:.2f}",
                details={"per_person_limit": per_person_limit, "person_count": person_count, "actual_per_person": total_amount/person_count}
            )
    
    def validate_invoice_date(
        self,
        invoice_date: str,
        max_days: int = 30
    ) -> RuleCheckItem:
        try:
            inv_date = self._parse_date(invoice_date)
            if inv_date is None:
                return RuleCheckItem(
                    rule_name="invoice_date",
                    result=CheckResult.WARNING,
                    message=f"无法解析发票日期: {invoice_date}",
                    details={"invoice_date": invoice_date, "error": "日期格式不支持"}
                )
            
            days_diff = (date.today() - inv_date).days
            formatted_date = inv_date.strftime("%Y-%m-%d")
            
            if days_diff <= max_days:
                return RuleCheckItem(
                    rule_name="invoice_date",
                    result=CheckResult.PASS,
                    message=f"发票日期 {formatted_date}，距今天 {days_diff} 天，未超期",
                    details={"days_diff": days_diff, "max_days": max_days, "parsed_date": formatted_date}
                )
            elif days_diff <= max_days + 30:
                return RuleCheckItem(
                    rule_name="invoice_date",
                    result=CheckResult.WARNING,
                    message=f"发票已逾期 {days_diff} 天，超过 {max_days} 天限制，请填写逾期说明",
                    details={"days_diff": days_diff, "max_days": max_days, "parsed_date": formatted_date}
                )
            else:
                return RuleCheckItem(
                    rule_name="invoice_date",
                    result=CheckResult.REJECT,
                    message=f"发票逾期 {days_diff} 天，超过报销时限，无法报销",
                    details={"days_diff": days_diff, "max_days": max_days, "parsed_date": formatted_date}
                )
        except Exception as e:
            return RuleCheckItem(
                rule_name="invoice_date",
                result=CheckResult.WARNING,
                message=f"无法解析发票日期: {invoice_date}",
                details={"invoice_date": invoice_date, "error": str(e)}
            )
    
    def _parse_date(self, date_str) -> Optional[date]:
        """解析多种日期格式，返回 date 对象"""
        if not date_str:
            return None
        
        if isinstance(date_str, date):
            return date_str
        
        if isinstance(date_str, datetime):
            return date_str.date()
        
        date_str = str(date_str).strip()
        
        # 支持的日期格式列表
        date_formats = [
            "%Y-%m-%d",           # 2025-10-15
            "%Y/%m/%d",           # 2025/10/15
            "%Y.%m.%d",           # 2025.10.15
            "%Y年%m月%d日",        # 2025年10月15日
            "%Y年%m月%d",         # 2025年10月15
            "%d/%m/%Y",           # 15/10/2025
            "%d-%m-%Y",           # 15-10-2025
            "%m/%d/%Y",           # 10/15/2025
            "%m-%d-%Y",           # 10-15-2025
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # 尝试正则提取中文日期
        import re
        cn_pattern = r"(\d{4})年(\d{1,2})月(\d{1,2})日?"
        match = re.match(cn_pattern, date_str)
        if match:
            try:
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                return date(year, month, day)
            except:
                pass
        
        return None
    
    def validate_company_match(
        self,
        seller_name: str,
        seller_tax_id: str
    ) -> RuleCheckItem:
        if not self._company_whitelist:
            return RuleCheckItem(
                rule_name="company_match",
                result=CheckResult.PASS,
                message="未配置公司白名单，跳过校验"
            )
        
        for company in self._company_whitelist:
            expected_name = company.get("name", "")
            expected_tax_id = company.get("tax_id", "")
            
            if expected_tax_id and seller_tax_id == expected_tax_id:
                return RuleCheckItem(
                    rule_name="company_match",
                    result=CheckResult.PASS,
                    message=f"税号匹配成功: {seller_name}",
                    details={"matched_company": company}
                )
            
            if expected_name and self._fuzzy_match(seller_name, expected_name):
                return RuleCheckItem(
                    rule_name="company_match",
                    result=CheckResult.PASS,
                    message=f"抬头匹配成功: {seller_name}",
                    details={"matched_company": company}
                )
        
        return RuleCheckItem(
            rule_name="company_match",
            result=CheckResult.REJECT,
            message=f"发票抬头/税号不匹配: {seller_name} ({seller_tax_id})",
            details={"seller_name": seller_name, "seller_tax_id": seller_tax_id}
        )
    
    def _recognize_seat(self, seat_text: str) -> str:
        seat_text = seat_text.lower() if seat_text else ""
        if "公务" in seat_text or "商务" in seat_text:
            return "公务舱" if "公务" in seat_text else "商务舱"
        if "头等" in seat_text:
            return "头等舱"
        if "经济" in seat_text or "全价" in seat_text:
            return "经济舱"
        if "一等" in seat_text:
            return "一等座"
        if "二等" in seat_text:
            return "二等座"
        if "软卧" in seat_text:
            return "软卧"
        if "硬卧" in seat_text:
            return "硬卧"
        if "软座" in seat_text:
            return "软座"
        if "硬座" in seat_text:
            return "硬座"
        return seat_text
    
    def _fuzzy_match(self, text1: str, text2: str) -> bool:
        if not text1 or not text2:
            return False
        text1 = text1.lower().replace(" ", "").replace("有限公司", "").replace("股份有限公司", "")
        text2 = text2.lower().replace(" ", "").replace("有限公司", "").replace("股份有限公司", "")
        return text1 in text2 or text2 in text1
    
    def determine_channel(self, validation_items: List[RuleCheckItem]) -> str:
        has_reject = any(item.result == CheckResult.REJECT for item in validation_items)
        has_warning = any(item.result == CheckResult.WARNING for item in validation_items)
        
        if has_reject:
            return "red"
        elif has_warning:
            return "yellow"
        else:
            return "green"
    
    def validate(
        self,
        employee_level: int,
        destination_city: str,
        expense_type: ExpenseType,
        invoice_data: Dict,
        **kwargs
    ) -> ValidationResult:
        employee_type = self.get_employee_type(employee_level)
        city_tier = self.get_city_tier(destination_city)
        
        items = []
        
        if expense_type == ExpenseType.ACCOMMODATION:
            total_amount = invoice_data.get("total_amount", 0) or invoice_data.get("amount", 0)
            days = kwargs.get("days", 1)
            detail_type = kwargs.get("detail_type")
            items.append(self.validate_accommodation(total_amount, days, city_tier, employee_type, detail_type))
        
        elif expense_type == ExpenseType.TRANSPORT_AIR:
            seat_type = invoice_data.get("seat_type", "")
            items.append(self.validate_transport_air(seat_type, employee_type))
        
        elif expense_type == ExpenseType.TRANSPORT_TRAIN:
            seat_type = invoice_data.get("seat_type", "")
            duration_hours = kwargs.get("duration_hours")
            items.append(self.validate_transport_train(seat_type, employee_type, duration_hours))
        
        elif expense_type == ExpenseType.CITY_TRANSPORT:
            days = kwargs.get("days", 1)
            amount = invoice_data.get("total_amount", 0) or invoice_data.get("amount", 0)
            items.append(self.validate_city_transport(days, amount, employee_type))
        
        elif expense_type == ExpenseType.MEAL:
            days = kwargs.get("days", 1)
            has_entertainment = kwargs.get("has_entertainment", False)
            entertainment_amount = kwargs.get("entertainment_amount", 0)
            items.append(self.validate_meal(days, has_entertainment, entertainment_amount, employee_type))
        
        elif expense_type == ExpenseType.BUSINESS_ENTERTAINMENT:
            total_amount = invoice_data.get("total_amount", 0) or invoice_data.get("amount", 0)
            person_count = kwargs.get("person_count", 1)
            items.append(self.validate_business_entertainment(total_amount, person_count, employee_type))
        
        invoice_date = invoice_data.get("date")
        if invoice_date:
            items.append(self.validate_invoice_date(invoice_date))
        
        seller_name = invoice_data.get("seller_name", "")
        seller_tax_id = invoice_data.get("seller_tax_id", "")
        if seller_name or seller_tax_id:
            items.append(self.validate_company_match(seller_name, seller_tax_id))
        
        channel = self.determine_channel(items)
        
        return ValidationResult(
            channel=channel,
            items=items,
            summary=f"共 {len(items)} 项校验，{len([i for i in items if i.result == CheckResult.PASS])} 通过，{len([i for i in items if i.result == CheckResult.WARNING])} 预警，{len([i for i in items if i.result == CheckResult.REJECT])} 驳回"
        )


rule_engine = RuleEngine()


def get_rule_engine() -> RuleEngine:
    return rule_engine
