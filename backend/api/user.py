"""用户 API 路由"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import shutil
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from backend.database import get_db, Invoice, User, InvoiceModifyRecord, Employee, AuditRecord
from backend.models.schemas import (
    UserRegister,
    UserLogin,
    UserResponse,
    UserUpdate,
    UserPasswordChange,
    InvoiceResponse,
    InvoiceModifyRecordResponse,
    UploadResponse
)
from backend.services.user_service import get_user_auth_service, user_auth_service
from backend.services.audit_service import get_audit_service
from backend.config import settings
from backend.logger_config import logger

router = APIRouter()


def get_current_user(user_id: int = None, db: Session = Depends(get_db)) -> User:
    """获取当前登录的用户"""
    if user_id is None:
        raise HTTPException(status_code=401, detail="未登录")
    
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    
    return user


@router.post("/user/register", response_model=UserResponse)
def register(
    data: UserRegister,
    db: Session = Depends(get_db)
):
    """用户注册"""
    logger.info(f"用户注册请求: {data.username}")
    
    try:
        user = user_auth_service.create_user(
            db=db,
            username=data.username,
            password=data.password,
            name=data.name,
            email=data.email,
            phone=data.phone,
            department=data.department
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/user/login", response_model=UserResponse)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """用户登录"""
    logger.info(f"用户登录请求: {credentials.username}")
    
    user = user_auth_service.authenticate(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    return user


@router.post("/user/logout")
def logout():
    """用户登出"""
    return {"message": "已登出"}


@router.get("/user/me", response_model=UserResponse)
def get_current_user_info(user_id: int = None, db: Session = Depends(get_db)):
    """获取当前登录用户信息"""
    user = get_current_user(user_id, db)
    return user


@router.put("/user/me", response_model=UserResponse)
def update_current_user_info(
    update_data: UserUpdate,
    user_id: int = None,
    db: Session = Depends(get_db)
):
    """更新当前用户信息"""
    user = get_current_user(user_id, db)
    
    updated_user = user_auth_service.update_user(
        db=db,
        user_id=user.id,
        name=update_data.name,
        email=update_data.email,
        phone=update_data.phone,
        department=update_data.department
    )
    
    return updated_user


@router.post("/user/change-password")
def change_password(
    data: UserPasswordChange,
    user_id: int = None,
    db: Session = Depends(get_db)
):
    """修改密码"""
    get_current_user(user_id, db)
    
    if not user_auth_service.change_password(db, user_id, data.old_password, data.new_password):
        raise HTTPException(status_code=400, detail="旧密码错误")
    
    return {"message": "密码修改成功"}


@router.get("/user/invoices", response_model=List[InvoiceResponse])
def get_my_invoices(
    skip: int = 0,
    limit: int = 20,
    status: str = None,
    user_id: int = None,
    db: Session = Depends(get_db)
):
    """获取当前用户上传的发票列表"""
    user = get_current_user(user_id, db)
    
    query = db.query(Invoice).filter(Invoice.user_id == user.id)
    
    if status:
        query = query.filter(Invoice.status == status)
    
    invoices = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
    
    return invoices


@router.get("/user/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_my_invoice(
    invoice_id: int,
    user_id: int = None,
    db: Session = Depends(get_db)
):
    """获取当前用户上传的发票详情"""
    from backend.models.schemas import AuditRecordResponse
    
    user = get_current_user(user_id, db)
    
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == user.id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    # 构建返回数据
    response_data = {
        "id": invoice.id,
        "employee_id": invoice.employee_id,
        "user_id": invoice.user_id,
        "file_path": invoice.file_path,
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
        "status": invoice.status,
        "channel": invoice.channel,
        "expense_type": invoice.expense_type,
        "destination_city": invoice.destination_city,
        "person_count": invoice.person_count,
        "trip_days": invoice.trip_days,
        "created_at": invoice.created_at,
        "audit_record": None
    }
    
    # 添加审核记录
    if invoice.audit_record:
        audit = invoice.audit_record
        # 解析 JSON 字段
        risk_reasons = []
        if audit.risk_reasons:
            try:
                risk_reasons = json.loads(audit.risk_reasons)
            except:
                risk_reasons = []
        
        validation_items = []
        if audit.validation_items:
            try:
                validation_items = json.loads(audit.validation_items)
            except:
                validation_items = []
        
        response_data["audit_record"] = {
            "id": audit.id,
            "invoice_id": audit.invoice_id,
            "signature_score": audit.signature_score,
            "ocr_confidence": audit.ocr_confidence,
            "risk_level": audit.risk_level,
            "risk_score": audit.risk_score,
            "risk_reasons": risk_reasons,
            "decision": audit.decision,
            "channel": audit.channel,
            "validation_items": validation_items,
            "stamp_detected": audit.stamp_detected == "true" if audit.stamp_detected else None,
            "duplicate_checked": audit.duplicate_checked,
            "company_matched": audit.company_matched,
            "reviewed_at": audit.reviewed_at
        }
    
    return InvoiceResponse(**response_data)


@router.get("/user/invoices/{invoice_id}/image")
def get_my_invoice_image(
    invoice_id: int,
    user_id: int = None,
    db: Session = Depends(get_db)
):
    """获取发票图片"""
    user = get_current_user(user_id, db)
    
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == user.id
    ).first()
    
    if not invoice or not invoice.file_path:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    import os
    if not os.path.exists(invoice.file_path):
        raise HTTPException(status_code=404, detail="图片文件不存在")
    
    return FileResponse(invoice.file_path)


@router.get("/user/invoices/{invoice_id}/history", response_model=List[InvoiceModifyRecordResponse])
def get_invoice_modify_history(
    invoice_id: int,
    user_id: int = None,
    db: Session = Depends(get_db)
):
    """获取发票修改历史"""
    user = get_current_user(user_id, db)
    
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == user.id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    records = db.query(InvoiceModifyRecord).filter(
        InvoiceModifyRecord.invoice_id == invoice_id
    ).order_by(InvoiceModifyRecord.created_at.desc()).all()
    
    return records


@router.get("/user/stats")
def get_user_stats(
    user_id: int = None,
    db: Session = Depends(get_db)
):
    """获取用户上传统计"""
    user = get_current_user(user_id, db)
    
    total = db.query(Invoice).filter(Invoice.user_id == user.id).count()
    pending = db.query(Invoice).filter(Invoice.user_id == user.id, Invoice.status == "pending").count()
    approved = db.query(Invoice).filter(Invoice.user_id == user.id, Invoice.status == "approve").count()
    rejected = db.query(Invoice).filter(Invoice.user_id == user.id, Invoice.status == "reject").count()
    processing = db.query(Invoice).filter(Invoice.user_id == user.id, Invoice.status == "processing").count()
    
    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "processing": processing
    }


def pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 200) -> List[str]:
    """将 PDF 文件转换为图片"""
    import fitz
    
    logger.info(f"[PDF转换] 开始转换: {pdf_path}")
    
    pdf_doc = fitz.open(pdf_path)
    image_paths = []
    
    base_name = Path(pdf_path).stem
    
    for page_num in range(len(pdf_doc)):
        page = pdf_doc[page_num]
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        image_path = os.path.join(output_dir, f"{base_name}_page_{page_num + 1}.png")
        pix.save(image_path)
        
        image_paths.append(image_path)
        logger.info(f"[PDF转换] 页面 {page_num + 1} 已保存: {image_path}")
    
    pdf_doc.close()
    logger.info(f"[PDF转换] 完成，共生成 {len(image_paths)} 张图片")
    
    return image_paths


@router.post("/user/upload", response_model=UploadResponse)
async def user_upload_invoice(
    file: UploadFile = File(...),
    employee_id: int = None,
    expense_type: str = Query("accommodation", description="费用类型"),
    destination_city: str = Query("北京", description="出差目的地城市"),
    person_count: int = Query(1, description="人数"),
    trip_days: int = Query(1, description="出差天数"),
    auto_audit: bool = True,
    user_id: int = None,
    db: Session = Depends(get_db)
):
    """用户上传发票"""
    user = get_current_user(user_id, db)
    
    logger.info(f"用户上传文件: {file.filename}, user: {user.username}")
    
    allowed_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.pdf')
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="只支持图片和PDF文件")
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    is_pdf = file_ext == '.pdf'
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    if is_pdf:
        try:
            image_paths = pdf_to_images(file_path, settings.UPLOAD_DIR)
            if image_paths:
                file_path = image_paths[0]
        except Exception as e:
            logger.error(f"[上传] PDF 转换失败: {str(e)}")
            raise HTTPException(status_code=400, detail=f"PDF转换失败: {str(e)}")
    
    employee_level = 9
    if employee_id:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if employee:
            employee_level = employee.level or 9
    
    invoice = Invoice(
        employee_id=employee_id,
        user_id=user.id,
        file_path=file_path,
        status="processing",
        expense_type=expense_type,
        destination_city=destination_city,
        person_count=person_count,
        trip_days=trip_days
    )
    
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    logger.info(f"用户上传成功: {unique_filename}, invoice_id: {invoice.id}")
    
    if auto_audit:
        audit_service = get_audit_service()
        try:
            result = audit_service.process_audit(
                invoice.id,
                db,
                expense_type=expense_type,
                destination_city=destination_city,
                employee_level=employee_level,
                person_count=person_count,
                trip_days=trip_days
            )
            
            # 获取审核记录
            db.refresh(invoice)
            validation_items = []
            risk_reasons = []
            if invoice.audit_record:
                if invoice.audit_record.validation_items:
                    try:
                        validation_items = json.loads(invoice.audit_record.validation_items)
                    except:
                        validation_items = []
                if invoice.audit_record.risk_reasons:
                    try:
                        risk_reasons = json.loads(invoice.audit_record.risk_reasons)
                    except:
                        risk_reasons = []
            
            return UploadResponse(
                file_id=invoice.id,
                filename=unique_filename,
                status=result.decision,
                invoice_no=invoice.invoice_no,
                invoice_code=invoice.invoice_code,
                total_amount=invoice.total_amount,
                seller_name=invoice.seller_name,
                date=invoice.date,
                decision=result.decision,
                channel=invoice.channel,
                risk_level=invoice.audit_record.risk_level if invoice.audit_record else None,
                risk_score=invoice.audit_record.risk_score if invoice.audit_record else None,
                validation_items=validation_items,
                risk_reasons=risk_reasons
            )
        except Exception as e:
            logger.error(f"自动审核失败: {str(e)}")
            invoice.status = "error"
            db.commit()
            return UploadResponse(
                file_id=invoice.id,
                filename=unique_filename,
                status="error"
            )
    
    return UploadResponse(
        file_id=invoice.id,
        filename=unique_filename,
        status="pending"
    )


@router.get("/user/employees", response_model=List[dict])
def get_employees_for_user(
    user_id: int = None,
    db: Session = Depends(get_db)
):
    """获取员工列表（供用户选择报销人）"""
    get_current_user(user_id, db)
    
    employees = db.query(Employee).all()
    return [{"id": e.id, "name": e.name, "department": e.department, "level": e.level} for e in employees]
