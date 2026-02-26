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

from backend.database import get_db, init_db, Invoice, AuditRecord, Auditor, InvoiceModifyRecord
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
    
    old_data = {
        "invoice_code": invoice.invoice_code,
        "invoice_no": invoice.invoice_no,
        "amount": invoice.amount,
        "tax_amount": invoice.tax_amount,
        "total_amount": invoice.total_amount,
        "date": invoice.date,
        "seller_name": invoice.seller_name,
        "seller_tax_id": invoice.seller_tax_id,
        "buyer_name": invoice.buyer_name,
        "buyer_tax_id": invoice.buyer_tax_id,
        "expense_type": invoice.expense_type,
        "destination_city": invoice.destination_city,
        "person_count": invoice.person_count,
        "trip_days": invoice.trip_days
    }
    
    new_data = {}
    
    # 更新发票信息
    if update_data.invoice_code is not None:
        invoice.invoice_code = update_data.invoice_code
        new_data["invoice_code"] = update_data.invoice_code
    if update_data.invoice_no is not None:
        invoice.invoice_no = update_data.invoice_no
        new_data["invoice_no"] = update_data.invoice_no
    if update_data.amount is not None:
        invoice.amount = update_data.amount
        new_data["amount"] = update_data.amount
    if update_data.tax_amount is not None:
        invoice.tax_amount = update_data.tax_amount
        new_data["tax_amount"] = update_data.tax_amount
    if update_data.total_amount is not None:
        invoice.total_amount = update_data.total_amount
        new_data["total_amount"] = update_data.total_amount
    if update_data.date is not None:
        invoice.date = update_data.date
        new_data["date"] = update_data.date
    if update_data.seller_name is not None:
        invoice.seller_name = update_data.seller_name
        new_data["seller_name"] = update_data.seller_name
    if update_data.seller_tax_id is not None:
        invoice.seller_tax_id = update_data.seller_tax_id
        new_data["seller_tax_id"] = update_data.seller_tax_id
    if update_data.buyer_name is not None:
        invoice.buyer_name = update_data.buyer_name
        new_data["buyer_name"] = update_data.buyer_name
    if update_data.buyer_tax_id is not None:
        invoice.buyer_tax_id = update_data.buyer_tax_id
        new_data["buyer_tax_id"] = update_data.buyer_tax_id
    if update_data.expense_type is not None:
        invoice.expense_type = update_data.expense_type
        new_data["expense_type"] = update_data.expense_type
    if update_data.destination_city is not None:
        invoice.destination_city = update_data.destination_city
        new_data["destination_city"] = update_data.destination_city
    if update_data.person_count is not None:
        invoice.person_count = update_data.person_count
        new_data["person_count"] = update_data.person_count
    if update_data.trip_days is not None:
        invoice.trip_days = update_data.trip_days
        new_data["trip_days"] = update_data.trip_days
    
    if new_data:
        modify_record = InvoiceModifyRecord(
            invoice_id=invoice_id,
            user_id=auditor.id,
            user_name=auditor.name,
            old_data=json.dumps(old_data, ensure_ascii=False),
            new_data=json.dumps(new_data, ensure_ascii=False),
            modify_reason=update_data.review_note or "信息修改"
        )
        db.add(modify_record)
    
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


@router.get("/users", response_model=List[dict])
def list_users(
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """列出所有用户（管理员权限）"""
    current = get_current_auditor(auditor_id, db)
    
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    from backend.services.user_service import get_user_auth_service
    user_service = get_user_auth_service()
    users = user_service.list_users(db)
    
    return [
        {
            "id": u.id,
            "username": u.username,
            "name": u.name,
            "email": u.email,
            "phone": u.phone,
            "department": u.department,
            "is_active": u.is_active,
            "created_at": u.created_at,
            "last_login": u.last_login,
            "invoice_count": db.query(Invoice).filter(Invoice.user_id == u.id).count()
        }
        for u in users
    ]


@router.get("/users/{user_id}/invoices", response_model=List[InvoiceResponse])
def get_user_invoices(
    user_id: int,
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """获取指定用户上传的发票列表（管理员权限）"""
    current = get_current_auditor(auditor_id, db)
    
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    invoices = db.query(Invoice).filter(Invoice.user_id == user_id).order_by(Invoice.created_at.desc()).all()
    return invoices


@router.delete("/invoices/{invoice_id}")
def delete_invoice(
    invoice_id: int,
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """删除发票（管理员权限）"""
    current = get_current_auditor(auditor_id, db)
    
    if current.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    db.delete(invoice)
    db.commit()
    
    logger.info(f"管理员 {current.username} 删除了发票: invoice_id={invoice_id}")
    
    return {"message": "发票删除成功"}


@router.get("/invoices/{invoice_id}/modify-history", response_model=List[dict])
def get_invoice_modify_history(
    invoice_id: int,
    auditor_id: int = None,
    db: Session = Depends(get_db)
):
    """获取发票修改历史"""
    current = get_current_auditor(auditor_id, db)
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    records = db.query(InvoiceModifyRecord).filter(
        InvoiceModifyRecord.invoice_id == invoice_id
    ).order_by(InvoiceModifyRecord.created_at.desc()).all()
    
    return [
        {
            "id": r.id,
            "user_name": r.user_name,
            "old_data": r.old_data,
            "new_data": r.new_data,
            "modify_reason": r.modify_reason,
            "created_at": r.created_at
        }
        for r in records
    ]
