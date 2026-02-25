import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Optional, List
import json
import time
import psutil
import tracemalloc

from backend.database import get_db, Invoice, AuditRecord, Employee
from backend.models.schemas import AuditResult, AuditResultFull, ValidationItem
from backend.services.ocr_service import get_ocr_service
from backend.services.llm_service import get_llm_service
from backend.services.duplicate_checker import get_duplicate_checker
from backend.services.company_validator import get_company_validator
from ml.risk_analyzer import risk_analyzer
from ml.stamp_detector import get_stamp_detector
from backend.rules.engine import (
    get_rule_engine,
    ExpenseType,
    CheckResult
)
from backend.config import settings
from backend.logger_config import logger


def get_memory_usage():
    """获取当前进程的内存使用情况"""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return {
        'rss': mem_info.rss / 1024 / 1024,  # 物理内存 MB
        'vms': mem_info.vms / 1024 / 1024,  # 虚拟内存 MB
    }


class AuditService:
    def __init__(self):
        self.ocr_service = get_ocr_service()
        self.llm_service = get_llm_service()
        self.duplicate_checker = get_duplicate_checker()
        self.company_validator = get_company_validator()
        self.stamp_detector = get_stamp_detector()
        self.rule_engine = get_rule_engine()
    
    def process_audit(
        self,
        invoice_id: int,
        db,
        expense_type: str = "accommodation",
        destination_city: str = "北京",
        employee_level: int = 9,
        person_count: int = 1,
        trip_days: int = 1,
        has_entertainment: bool = False,
        entertainment_amount: float = 0
    ) -> AuditResult:
        # 记录开始时间和内存
        start_time = time.time()
        start_mem = get_memory_usage()
        tracemalloc.start()
        
        logger.info(f"========== 开始审核发票 ==========")
        logger.info(f"发票ID: {invoice_id}")
        logger.info(f"费用类型: {expense_type}, 目的地: {destination_city}, 员工级别: {employee_level}")
        logger.info(f"起始内存: RSS={start_mem['rss']:.1f}MB, VMS={start_mem['vms']:.1f}MB")
        
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        
        if not invoice:
            logger.error(f"Invoice {invoice_id} not found")
            raise ValueError(f"Invoice {invoice_id} not found")
        
        invoice.expense_type = expense_type
        invoice.destination_city = destination_city
        invoice.person_count = person_count
        invoice.trip_days = trip_days
        
        invoice_data = {}
        ocr_confidence = 0.0
        ocr_time = 0
        ocr_mem_delta = 0
        
        try:
            ocr_start = time.time()
            ocr_mem_before = get_memory_usage()
            logger.info(f"[OCR] 开始处理: {invoice.file_path}")
            ocr_result = self.ocr_service.process_invoice(invoice.file_path)
            invoice_data = ocr_result['data']
            ocr_confidence = ocr_result['confidence']
            ocr_time = time.time() - ocr_start
            ocr_mem_after = get_memory_usage()
            ocr_mem_delta = ocr_mem_after['rss'] - ocr_mem_before['rss']
            logger.info(f"[OCR] 完成 - 耗时: {ocr_time:.2f}秒, 内存变化: {ocr_mem_delta:+.1f}MB, 置信度: {ocr_confidence:.2f}")
        except Exception as e:
            logger.error(f"[OCR] 处理失败: {str(e)}")
            invoice_data = {'error': str(e)}
        
        try:
            invoice.invoice_code = invoice_data.get('invoice_code')
            invoice.invoice_no = invoice_data.get('invoice_no')
            invoice.amount = invoice_data.get('amount')
            invoice.tax_amount = invoice_data.get('tax_amount')
            invoice.total_amount = invoice_data.get('total_amount')
            invoice.date = invoice_data.get('date')
            invoice.seller_name = invoice_data.get('seller_name')
            invoice.seller_tax_id = invoice_data.get('seller_tax_id')
            invoice.seller_address = invoice_data.get('seller_address')
            invoice.seller_bank = invoice_data.get('seller_bank')
            invoice.buyer_name = invoice_data.get('buyer_name')
            invoice.buyer_tax_id = invoice_data.get('buyer_tax_id')
            db.commit()
        except Exception as e:
            logger.error(f"Failed to update invoice data: {str(e)}")
        
        validation_items = []
        validation_results = []
        
        stamp_result = None
        try:
            stamp_result = self.stamp_detector.detect_stamp(invoice.file_path)
            validation_items.append(ValidationItem(
                rule_name="stamp_detection",
                result="pass" if stamp_result.has_stamp else "warning",
                message=stamp_result.message,
                details={
                    "has_stamp": stamp_result.has_stamp,
                    "confidence": stamp_result.confidence
                }
            ))
            if not stamp_result.has_stamp:
                validation_results.append(("stamp", CheckResult.REJECT))
        except Exception as e:
            logger.warning(f"Stamp detection failed: {str(e)}")
        
        duplicate_result = None
        if invoice.invoice_no and invoice.amount:
            try:
                duplicate_result = self.duplicate_checker.check_duplicate(
                    invoice_code=invoice_data.get('invoice_code', ''),
                    invoice_no=invoice.invoice_no,
                    amount=invoice.amount,
                    db=db,
                    auto_lock=True
                )
                
                validation_items.append(ValidationItem(
                    rule_name="duplicate_check",
                    result="reject" if duplicate_result.is_duplicate else "pass",
                    message=duplicate_result.message,
                    details={"existing_id": duplicate_result.existing_invoice_id}
                ))
                
                if duplicate_result.is_duplicate:
                    validation_results.append(("duplicate", CheckResult.REJECT))
            except Exception as e:
                logger.warning(f"Duplicate check failed: {str(e)}")
        
        if invoice.seller_name or invoice.seller_tax_id:
            try:
                company_result = self.company_validator.validate(
                    seller_name=invoice.seller_name,
                    seller_tax_id=invoice.seller_tax_id
                )
                
                validation_items.append(ValidationItem(
                    rule_name="seller_match",
                    result="pass" if company_result.is_match else "pass",  # 销售方不强制匹配
                    message=company_result.message,
                    details={
                        "confidence": company_result.confidence,
                        "match_type": company_result.match_type
                    }
                ))
                
                # 销售方不在白名单不拦截，仅记录
            except Exception as e:
                logger.warning(f"Company validation failed: {str(e)}")
        
        # 验证购买方公司（本公司）
        buyer_name = invoice_data.get('buyer_name')
        buyer_tax_id = invoice_data.get('buyer_tax_id')
        if buyer_name or buyer_tax_id:
            try:
                buyer_result = self.company_validator.validate_buyer(
                    buyer_name=buyer_name,
                    buyer_tax_id=buyer_tax_id
                )
                
                validation_items.append(ValidationItem(
                    rule_name="company_match",
                    result="pass" if buyer_result.is_match else "reject",
                    message=buyer_result.message,
                    details={
                        "confidence": buyer_result.confidence,
                        "match_type": buyer_result.match_type
                    }
                ))
                
                if not buyer_result.is_match:
                    validation_results.append(("company", CheckResult.REJECT))
            except Exception as e:
                logger.warning(f"Buyer validation failed: {str(e)}")
        
        try:
            expense_enum = ExpenseType(expense_type) if expense_type else ExpenseType.ACCOMMODATION
            rule_result = self.rule_engine.validate(
                employee_level=employee_level,
                destination_city=destination_city,
                expense_type=expense_enum,
                invoice_data=invoice_data,
                days=trip_days,
                person_count=person_count,
                has_entertainment=has_entertainment,
                entertainment_amount=entertainment_amount
            )
            
            for item in rule_result.items:
                validation_items.append(ValidationItem(
                    rule_name=item.rule_name,
                    result=item.result.value,
                    message=item.message,
                    details=item.details
                ))
                
                if item.result == CheckResult.REJECT:
                    validation_results.append((item.rule_name, CheckResult.REJECT))
                elif item.result == CheckResult.WARNING:
                    validation_results.append((item.rule_name, CheckResult.WARNING))
            
            channel = rule_result.channel
        except Exception as e:
            logger.warning(f"Rule engine failed: {str(e)}")
            channel = "yellow"
        
        similar_invoices = []
        try:
            invoice_text = f"{invoice_data.get('seller_name', '')} {invoice_data.get('invoice_no', '')} {invoice_data.get('amount', '')}"
            similar_invoices = risk_analyzer.find_similar(invoice_text)
        except Exception as e:
            logger.warning(f"Similar invoice search failed: {str(e)}")
        
        invoice_analysis = {}
        llm_time = 0
        llm_mem_delta = 0
        try:
            llm_start = time.time()
            llm_mem_before = get_memory_usage()
            logger.info("[LLM] 开始分析发票...")
            invoice_analysis = self.llm_service.analyze_invoice_image(
                invoice.file_path, 
                invoice_data
            )
            llm_time = time.time() - llm_start
            llm_mem_after = get_memory_usage()
            llm_mem_delta = llm_mem_after['rss'] - llm_mem_before['rss']
            logger.info(f"[LLM] 分析完成 - 耗时: {llm_time:.2f}秒, 内存变化: {llm_mem_delta:+.1f}MB")
        except Exception as e:
            logger.warning(f"[LLM] 分析失败: {str(e)}")
            invoice_analysis = {'is_suspicious': False, 'authenticity_score': 0.5, 'suspicious_points': []}
        
        signature_score = None
        if invoice.employee_id:
            employee = db.query(Employee).filter(Employee.id == invoice.employee_id).first()
            if employee and employee.signature_path and os.path.exists(employee.signature_path):
                logger.info("Comparing signatures...")
                signature_result = self.llm_service.compare_signatures(
                    employee.signature_path,
                    invoice.file_path
                )
                signature_score = signature_result.get('similarity_score', 0.5)
        
        logger.info("Calculating risk score...")
        risk_result = risk_analyzer.calculate_risk_score(
            invoice_data=invoice_data,
            ocr_confidence=ocr_confidence,
            signature_score=signature_score,
            similar_invoices=similar_invoices
        )
        
        if invoice_analysis.get('is_suspicious'):
            risk_result['risk_score'] = min(risk_result['risk_score'] + 0.2, 1.0)
            risk_result['risk_factors'].extend(invoice_analysis.get('suspicious_points', []))
        
        has_reject = any(r == CheckResult.REJECT for _, r in validation_results)
        
        if has_reject:
            decision = "reject"
            if channel not in ["red"]:
                channel = "red"
        else:
            has_warning = any(r == CheckResult.WARNING for _, r in validation_results)
            if has_warning:
                decision = "review"
                if channel not in ["yellow", "red"]:
                    channel = "yellow"
            else:
                decision = "approve"
                channel = "green"
        
        invoice.status = decision
        invoice.channel = channel
        
        logger.info(f"Risk score: {risk_result['risk_score']:.2f}, Decision: {decision}, Channel: {channel}")
        
        existing_record = db.query(AuditRecord).filter(AuditRecord.invoice_id == invoice.id).first()
        if existing_record:
            logger.info(f"Updating existing audit record for invoice {invoice.id}")
            existing_record.signature_score = signature_score
            existing_record.ocr_result = json.dumps(invoice_data, ensure_ascii=False)
            existing_record.ocr_confidence = ocr_confidence
            existing_record.risk_level = risk_result['risk_level']
            existing_record.risk_score = risk_result['risk_score']
            existing_record.risk_reasons = json.dumps(risk_result['risk_factors'], ensure_ascii=False)
            existing_record.decision = decision
            existing_record.channel = channel
            existing_record.validation_items = json.dumps([v.dict() for v in validation_items], ensure_ascii=False)
            existing_record.stamp_detected = "true" if stamp_result and stamp_result.has_stamp else "false"
            existing_record.duplicate_checked = duplicate_result is not None
            existing_record.company_matched = "true" if company_result and company_result.is_match else "false" if company_result else "none"
            audit_record = existing_record
        else:
            audit_record = AuditRecord(
                invoice_id=invoice.id,
                signature_score=signature_score,
                ocr_result=json.dumps(invoice_data, ensure_ascii=False),
                ocr_confidence=ocr_confidence,
                risk_level=risk_result['risk_level'],
                risk_score=risk_result['risk_score'],
                risk_reasons=json.dumps(risk_result['risk_factors'], ensure_ascii=False),
                decision=decision,
                channel=channel,
                validation_items=json.dumps([v.dict() for v in validation_items], ensure_ascii=False),
                stamp_detected="true" if stamp_result and stamp_result.has_stamp else "false",
                duplicate_checked=duplicate_result is not None,
                company_matched="true" if company_result and company_result.is_match else "false" if company_result else "none"
            )
            db.add(audit_record)
        
        # 只有通过(approve)或审核中(review)的发票才注册到重复检测系统
        if decision in ["approve", "review"] and invoice.invoice_no and invoice.amount:
            try:
                self.duplicate_checker.register_invoice(
                    invoice_id=invoice.id,
                    invoice_code=invoice_data.get('invoice_code', ''),
                    invoice_no=invoice.invoice_no,
                    amount=invoice.amount,
                    db=db
                )
                logger.info(f"发票已注册到重复检测系统: {invoice.invoice_no}")
            except Exception as e:
                logger.warning(f"注册发票指纹失败: {str(e)}")
        
        db.commit()
        db.refresh(audit_record)
        
        # 只有通过的发票才添加到风险分析索引
        if decision == "approve":
            try:
                risk_analyzer.add_invoice(
                    invoice.id,
                    f"{invoice_data.get('seller_name', '')} {invoice_data.get('invoice_no', '')} {invoice_data.get('amount', '')}"
                )
            except Exception as e:
                logger.warning(f"添加发票到风险索引失败: {str(e)}")
        
        # 不再删除驳回的发票记录，保留以便用户查看驳回原因
        # 用户可以修改后重新提交
        
        # 计算总耗时和内存
        total_time = time.time() - start_time
        end_mem = get_memory_usage()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        mem_delta = end_mem['rss'] - start_mem['rss']
        
        # ========== 详细审核结果日志 ==========
        logger.info("=" * 60)
        logger.info(f"【审核结果汇总】发票ID: {invoice_id}")
        logger.info("-" * 60)
        
        # 审核决策
        decision_text = {"approve": "✅ 通过", "review": "⚠️ 需复核", "reject": "❌ 驳回"}.get(decision, decision)
        channel_text = {"green": "🟢 绿色通道", "yellow": "🟡 黄色通道", "red": "🔴 红色通道"}.get(channel, channel)
        logger.info(f"审核决策: {decision_text}")
        logger.info(f"审核通道: {channel_text}")
        
        # 报销标准对比
        logger.info("-" * 60)
        logger.info("【报销标准对比】")
        if validation_items:
            for item in validation_items:
                result_icon = {"pass": "✅", "warning": "⚠️", "reject": "❌"}.get(item.result, "❓")
                rule_name_cn = {
                    "accommodation_standard": "住宿费标准",
                    "air_standard": "机票舱位",
                    "train_standard": "火车席别",
                    "city_transport_standard": "市内交通",
                    "meal_standard": "伙食补助",
                    "business_entertainment_standard": "业务招待",
                    "invoice_date": "发票日期",
                    "company_match": "公司抬头",
                    "stamp_detection": "印章检测",
                    "duplicate_check": "重复检测",
                    "seller_match": "销售方验证"
                }.get(item.rule_name, item.rule_name)
                
                # 提取实际值和标准值
                actual_val = "-"
                standard_val = "-"
                if item.details:
                    d = item.details
                    if item.rule_name == "accommodation_standard":
                        actual_val = f"¥{d.get('actual_daily', 0):.2f}/晚" if d.get('actual_daily') else "-"
                        standard_val = f"≤¥{d.get('daily_limit', 0):.0f}/晚" if d.get('daily_limit') else "-"
                    elif item.rule_name in ["air_standard", "train_standard"]:
                        actual_val = d.get("seat_type", "-")
                        standard_val = "/".join(d.get("allowed", [])) if d.get("allowed") else "-"
                    elif item.rule_name == "city_transport_standard":
                        actual_val = f"¥{d.get('actual', 0):.2f}" if d.get('actual') else "-"
                        standard_val = f"¥{d.get('daily_limit', 0)}/天 × {d.get('days', 1)}天" if d.get('daily_limit') else "-"
                    elif item.rule_name == "business_entertainment_standard":
                        actual_val = f"¥{d.get('actual_per_person', 0):.2f}/人" if d.get('actual_per_person') else "-"
                        standard_val = f"≤¥{d.get('per_person_limit', 0)}/人" if d.get('per_person_limit') else "-"
                    elif item.rule_name == "invoice_date":
                        actual_val = f"{d.get('days_diff', 0)}天前" if d.get('days_diff') else "-"
                        standard_val = f"≤{d.get('max_days', 30)}天内"
                    elif item.rule_name == "stamp_detection":
                        actual_val = "有印章" if d.get("has_stamp") else "无印章"
                        standard_val = "需有印章"
                    elif item.rule_name == "duplicate_check":
                        actual_val = f"重复发票 #{d.get('existing_id')}" if d.get('existing_id') else "无重复"
                        standard_val = "不可重复"
                    elif item.rule_name == "company_match":
                        actual_val = "已验证"
                        standard_val = "需匹配本公司"
                
                logger.info(f"  {result_icon} {rule_name_cn}: 实际值[{actual_val}] 标准[{standard_val}]")
                if item.result != "pass":
                    logger.info(f"      └─ {item.message}")
        else:
            logger.info("  无校验项目")
        
        # 风险分析
        logger.info("-" * 60)
        logger.info("【风险分析】")
        logger.info(f"  OCR置信度: {ocr_confidence * 100:.0f}%")
        logger.info(f"  风险等级: {risk_result['risk_level']}")
        logger.info(f"  风险评分: {risk_result['risk_score'] * 100:.0f}%")
        if risk_result['risk_factors']:
            logger.info(f"  风险因素:")
            for factor in risk_result['risk_factors']:
                logger.info(f"    - {factor}")
        
        # 性能统计
        logger.info("-" * 60)
        logger.info("【性能统计】")
        logger.info(f"  OCR耗时: {ocr_time:.2f}秒")
        logger.info(f"  LLM分析耗时: {llm_time:.2f}秒")
        logger.info(f"  总耗时: {total_time:.2f}秒")
        logger.info(f"  内存变化: {mem_delta:+.1f}MB (峰值: {peak/1024/1024:.1f}MB)")
        logger.info(f"  当前内存: RSS={end_mem['rss']:.1f}MB")
        logger.info("=" * 60)
        
        return AuditResult(
            invoice_id=invoice.id,
            signature_score=signature_score,
            ocr_confidence=ocr_confidence,
            risk_level=risk_result['risk_level'],
            risk_score=risk_result['risk_score'],
            risk_reasons=risk_result['risk_factors'],
            decision=decision,
            invoice_data=invoice_data
        )
    
    def get_audit_result(self, invoice_id: int, db) -> Optional[AuditResultFull]:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice or not invoice.audit_record:
            return None
        
        audit = invoice.audit_record
        
        validation_items = []
        if audit.validation_items:
            try:
                validation_items = [ValidationItem(**v) for v in json.loads(audit.validation_items)]
            except:
                validation_items = []
        
        return AuditResultFull(
            invoice_id=invoice.id,
            signature_score=audit.signature_score,
            ocr_confidence=audit.ocr_confidence,
            risk_level=audit.risk_level,
            risk_score=audit.risk_score,
            risk_reasons=json.loads(audit.risk_reasons) if audit.risk_reasons else [],
            decision=audit.decision,
            channel=audit.channel or "pending",
            validation_items=validation_items,
            stamp_detected=audit.stamp_detected == "true" if audit.stamp_detected else None,
            duplicate_checked=audit.duplicate_checked,
            company_matched=audit.company_matched if audit.company_matched != "none" else None,
            invoice_data=json.loads(audit.ocr_result) if audit.ocr_result else {}
        )


audit_service = AuditService()


def get_audit_service() -> AuditService:
    return audit_service
