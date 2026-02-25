"""审核人 API 路由"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import json

from backend.database import get_db, init_db, Invoice, AuditRecord, Auditor
from backend.models.schemas import (
    AuditorLogin,
    AuditorCreate,
    AuditorResponse,
    AuditorUpdate,
    PasswordChange,
    InvoiceResponse,
    InvoiceReview,
    AuditResultFull,
    ValidationItem
)
from backend.services.auth_service import get_auth_service, auth_service
from backend.logger_config import logger

router = APIRouter()


# 简单的会话存储（生产环境应使用 Redis 或 JWT）
_active_sessions = {}


def get_current_auditor(auditor_id: int = None, db: Session = Depends(get_db)) -> Auditor:
    """获取当前登录的审核人"""
    if auditor_id is None:
        raise HTTPException(status_code=401, detail="未登录")
    
    auditor = db.query(Auditor).filter(Auditor.id == auditor_id, Auditor.is_active == True).first()
    if not auditor:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    
    return auditor


@router.post("/login", response_model=AuditorResponse)
def login(
    credentials: AuditorLogin,
    db: Session = Depends(get_db)
):
    """审核人登录"""
    logger.info(f"审核人登录请求: {credentials.username}")
    
    auditor = auth_service.authenticate(db, credentials.username, credentials.password)
    if not auditor:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 存储会话
    _active_sessions[auditor.id] = auditor
    
    return auditor


@router.post("/logout")
def logout(auditor_id: int = None):
    """审核人登出"""
    if auditor_id and auditor_id in _active_sessions:
        del _active_sessions[auditor_id]
    return {"message": "已登出"}


@router.get("/me", response_model=AuditorResponse)
def get_current_user(auditor_id: int = None, db: Session = Depends(get_db)):
    """获取当前登录审核人信息"""
    auditor = get_current_auditor(auditor_id, db)
    return auditor


@router.put("/me", response_model=AuditorResponse)
def update_current_user(
    update_data: AuditorUpdate,
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """更新当前审核人信息"""
    auditor = get_current_auditor(auditor_id, db)
    
    if update_data.name:
        auditor.name = update_data.name
    if update_data.email:
        auditor.email = update_data.email
    
    db.commit()
    db.refresh(auditor)
    
    logger.info(f"审核人更新信息: {auditor.username}")
    return auditor


@router.post("/change-password")
def change_password(
    data: PasswordChange,
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """修改密码"""
    auditor = get_current_auditor(auditor_id, db)
    
    if not auth_service.change_password(db, auditor.id, data.old_password, data.new_password):
        raise HTTPException(status_code=400, detail="旧密码错误")
    
    return {"message": "密码修改成功"}


@router.get("/invoices", response_model=List[InvoiceResponse])
def list_invoices(
    status: str = None,
    skip: int = 0,
    limit: int = 20,
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """获取发票列表（审核人权限）"""
    get_current_auditor(auditor_id, db)
    
    query = db.query(Invoice)
    
    if status:
        query = query.filter(Invoice.status == status)
    
    invoices = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
    
    return invoices


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """获取发票详情"""
    get_current_auditor(auditor_id, db)
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    return invoice


@router.get("/invoices/{invoice_id}/audit", response_model=AuditResultFull)
def get_invoice_audit(
    invoice_id: int,
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """获取发票审核结果"""
    get_current_auditor(auditor_id, db)
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    if not invoice.audit_record:
        raise HTTPException(status_code=404, detail="审核记录不存在")
    
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


@router.put("/invoices/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: int,
    update_data: InvoiceReview,
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """修改发票信息（审核人权限）"""
    auditor = get_current_auditor(auditor_id, db)
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    logger.info(f"审核人 {auditor.username} 修改发票信息: invoice_id={invoice_id}")
    
    # 更新发票信息
    if update_data.invoice_code is not None:
        invoice.invoice_code = update_data.invoice_code
    if update_data.invoice_no is not None:
        invoice.invoice_no = update_data.invoice_no
    if update_data.amount is not None:
        invoice.amount = update_data.amount
    if update_data.tax_amount is not None:
        invoice.tax_amount = update_data.tax_amount
    if update_data.total_amount is not None:
        invoice.total_amount = update_data.total_amount
    if update_data.date is not None:
        invoice.date = update_data.date
    if update_data.seller_name is not None:
        invoice.seller_name = update_data.seller_name
    if update_data.seller_tax_id is not None:
        invoice.seller_tax_id = update_data.seller_tax_id
    if update_data.buyer_name is not None:
        invoice.buyer_name = update_data.buyer_name
    if update_data.buyer_tax_id is not None:
        invoice.buyer_tax_id = update_data.buyer_tax_id
    if update_data.expense_type is not None:
        invoice.expense_type = update_data.expense_type
    if update_data.destination_city is not None:
        invoice.destination_city = update_data.destination_city
    if update_data.person_count is not None:
        invoice.person_count = update_data.person_count
    if update_data.trip_days is not None:
        invoice.trip_days = update_data.trip_days
    
    # 记录审核人
    if invoice.audit_record:
        invoice.audit_record.reviewed_by = auditor.id
    
    db.commit()
    db.refresh(invoice)
    
    return invoice


@router.post("/invoices/{invoice_id}/approve")
def approve_invoice(
    invoice_id: int,
    note: str = "",
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """通过发票审核"""
    auditor = get_current_auditor(auditor_id, db)
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    invoice.status = "approve"
    invoice.channel = "green"
    
    if invoice.audit_record:
        invoice.audit_record.decision = "approve"
        invoice.audit_record.reviewed_by = auditor.id
    
    db.commit()
    
    logger.info(f"审核人 {auditor.username} 通过发票: invoice_id={invoice_id}, note={note}")
    
    return {"message": "审核通过", "invoice_id": invoice_id}


@router.post("/invoices/{invoice_id}/reject")
def reject_invoice(
    invoice_id: int,
    reason: str,
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """驳回发票"""
    auditor = get_current_auditor(auditor_id, db)
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    invoice.status = "reject"
    
    if invoice.audit_record:
        invoice.audit_record.decision = "reject"
        invoice.audit_record.reviewed_by = auditor.id
        # 添加驳回原因到风险因素
        risk_reasons = json.loads(invoice.audit_record.risk_reasons) if invoice.audit_record.risk_reasons else []
        risk_reasons.append(f"人工驳回: {reason}")
        invoice.audit_record.risk_reasons = json.dumps(risk_reasons, ensure_ascii=False)
    
    db.commit()
    
    logger.info(f"审核人 {auditor.username} 驳回发票: invoice_id={invoice_id}, reason={reason}")
    
    return {"message": "已驳回", "invoice_id": invoice_id}


@router.get("/invoices/{invoice_id}/image")
def get_invoice_image(
    invoice_id: int,
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """获取发票图片"""
    get_current_auditor(auditor_id, db)
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice or not invoice.file_path:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    import os
    if not os.path.exists(invoice.file_path):
        raise HTTPException(status_code=404, detail="图片文件不存在")
    
    return FileResponse(invoice.file_path)


@router.get("/stats")
def get_audit_stats(
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """获取审核统计"""
    get_current_auditor(auditor_id, db)
    
    total = db.query(Invoice).count()
    pending = db.query(Invoice).filter(Invoice.status == "pending").count()
    approve = db.query(Invoice).filter(Invoice.status == "approve").count()
    reject = db.query(Invoice).filter(Invoice.status == "reject").count()
    review = db.query(Invoice).filter(Invoice.status == "review").count()
    
    return {
        "total": total,
        "pending": pending,
        "approved": approve,
        "rejected": reject,
        "review": review
    }


# ===== 管理员功能 =====

@router.post("/auditors", response_model=AuditorResponse)
def create_auditor(
    data: AuditorCreate,
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """创建审核人账号（管理员权限）"""
    current = get_current_auditor(auditor_id, db)
    
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    try:
        auditor = auth_service.create_auditor(
            db=db,
            username=data.username,
            password=data.password,
            name=data.name,
            email=data.email,
            role=data.role
        )
        return auditor
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/auditors", response_model=List[AuditorResponse])
def list_auditors(
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """列出所有审核人（管理员权限）"""
    current = get_current_auditor(auditor_id, db)
    
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    return auth_service.list_auditors(db)
