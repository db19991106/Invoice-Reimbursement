import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import List, Optional
from pathlib import Path
import shutil
import uuid
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db, Invoice, Employee, init_db
from backend.models.schemas import (
    InvoiceResponse, 
    InvoiceCreate, 
    InvoiceUpdate,
    UploadResponse, 
    EmployeeCreate, 
    EmployeeResponse,
    EmployeeCreateFull,
    AuditResult,
    AuditResultFull
)
from backend.services.audit_service import get_audit_service
from backend.config import settings
from backend.logger_config import logger

router = APIRouter()


@router.on_event("startup")
def startup_event():
    init_db()


def pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 200) -> List[str]:
    """将 PDF 文件转换为图片
    
    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录
        dpi: 图片分辨率
        
    Returns:
        生成的图片路径列表
    """
    import fitz  # PyMuPDF
    
    logger.info(f"[PDF转换] 开始转换: {pdf_path}")
    
    pdf_doc = fitz.open(pdf_path)
    image_paths = []
    
    base_name = Path(pdf_path).stem
    
    for page_num in range(len(pdf_doc)):
        page = pdf_doc[page_num]
        
        # 设置缩放矩阵以获得高质量图片
        zoom = dpi / 72  # 72 是 PDF 的默认 DPI
        mat = fitz.Matrix(zoom, zoom)
        
        # 渲染页面为图片
        pix = page.get_pixmap(matrix=mat)
        
        # 生成输出路径
        image_path = os.path.join(output_dir, f"{base_name}_page_{page_num + 1}.png")
        pix.save(image_path)
        
        image_paths.append(image_path)
        logger.info(f"[PDF转换] 页面 {page_num + 1} 已保存: {image_path}")
    
    pdf_doc.close()
    logger.info(f"[PDF转换] 完成，共生成 {len(image_paths)} 张图片")
    
    return image_paths


@router.post("/upload", response_model=UploadResponse)
async def upload_invoice(
    file: UploadFile = File(...),
    employee_id: int = None,
    expense_type: str = Query("accommodation", description="费用类型: accommodation/transport_air/transport_train/city_transport/meal/business_entertainment"),
    destination_city: str = Query("北京", description="出差目的地城市"),
    person_count: int = Query(1, description="人数"),
    trip_days: int = Query(1, description="出差天数"),
    auto_audit: bool = True,
    db: Session = Depends(get_db)
):
    logger.info(f"Uploading file: {file.filename}, expense_type: {expense_type}, city: {destination_city}")
    
    # 支持 PDF 和图片文件
    allowed_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.pdf')
    if not file.filename.lower().endswith(allowed_extensions):
        logger.warning(f"Invalid file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Only image and PDF files are allowed")
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    is_pdf = file_ext == '.pdf'
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 如果是 PDF，转换为图片
    if is_pdf:
        logger.info(f"[上传] 检测到 PDF 文件，开始转换...")
        try:
            image_paths = pdf_to_images(file_path, settings.UPLOAD_DIR)
            if image_paths:
                # 使用第一页作为主图片
                file_path = image_paths[0]
                logger.info(f"[上传] PDF 转换完成，使用第一页: {file_path}")
            else:
                logger.error(f"[上传] PDF 转换失败，未生成图片")
                raise HTTPException(status_code=400, detail="Failed to convert PDF to image")
        except Exception as e:
            logger.error(f"[上传] PDF 转换失败: {str(e)}")
            raise HTTPException(status_code=400, detail=f"PDF conversion failed: {str(e)}")
    
    employee_level = 9
    if employee_id:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if employee:
            employee_level = employee.level or 9
    
    invoice = Invoice(
        employee_id=employee_id,
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
    
    logger.info(f"File uploaded successfully: {unique_filename}, invoice_id: {invoice.id}")
    
    if auto_audit:
        logger.info(f"Starting auto-audit for invoice_id: {invoice.id}")
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
            logger.info(f"Auto-audit completed: decision={result.decision}, risk_level={result.risk_level}")
            return UploadResponse(
                file_id=invoice.id,
                filename=unique_filename,
                status=result.decision
            )
        except Exception as e:
            logger.error(f"Auto-audit failed: {str(e)}")
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
    
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    logger.info(f"File uploaded successfully: {unique_filename}, invoice_id: {invoice.id}")
    
    if auto_audit:
        logger.info(f"Starting auto-audit for invoice_id: {invoice.id}")
        audit_service = get_audit_service()
        try:
            result = audit_service.process_audit(invoice.id, db)
            logger.info(f"Auto-audit completed: decision={result.decision}, risk_level={result.risk_level}")
            return UploadResponse(
                file_id=invoice.id,
                filename=unique_filename,
                status=result.decision
            )
        except Exception as e:
            logger.error(f"Auto-audit failed: {str(e)}")
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


@router.get("/invoices", response_model=List[InvoiceResponse])
def get_invoices(
    skip: int = 0,
    limit: int = 20,
    status: str = None,
    db: Session = Depends(get_db)
):
    logger.info(f"Fetching invoices: skip={skip}, limit={limit}, status={status}")
    query = db.query(Invoice)
    
    if status:
        query = query.filter(Invoice.status == status)
    
    invoices = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
    
    return invoices


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    logger.info(f"Fetching invoice: {invoice_id}")
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    
    if not invoice:
        logger.warning(f"Invoice not found: {invoice_id}")
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice


@router.get("/invoices/{invoice_id}/image")
def get_invoice_image(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    
    if not invoice or not os.path.exists(invoice.file_path):
        logger.warning(f"Image not found for invoice: {invoice_id}")
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(invoice.file_path)


@router.post("/audit/{invoice_id}", response_model=AuditResult)
def audit_invoice(
    invoice_id: int,
    expense_type: str = Query("accommodation", description="费用类型"),
    destination_city: str = Query("北京", description="出差目的地城市"),
    person_count: int = Query(1, description="人数"),
    trip_days: int = Query(1, description="出差天数"),
    db: Session = Depends(get_db)
):
    logger.info(f"Starting audit for invoice: {invoice_id}")
    audit_service = get_audit_service()
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    employee_level = 9
    if invoice.employee_id:
        employee = db.query(Employee).filter(Employee.id == invoice.employee_id).first()
        if employee:
            employee_level = employee.level or 9
    
    try:
        result = audit_service.process_audit(
            invoice_id,
            db,
            expense_type=expense_type,
            destination_city=destination_city,
            employee_level=employee_level,
            person_count=person_count,
            trip_days=trip_days
        )
        logger.info(f"Audit completed for invoice: {invoice_id}, decision: {result.decision}")
        return result
    except ValueError as e:
        logger.error(f"Audit failed for invoice {invoice_id}: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Audit error for invoice {invoice_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


@router.get("/audit/{invoice_id}", response_model=AuditResultFull)
def get_audit_result(invoice_id: int, db: Session = Depends(get_db)):
    logger.info(f"Fetching audit result for invoice: {invoice_id}")
    audit_service = get_audit_service()
    
    result = audit_service.get_audit_result(invoice_id, db)
    
    if not result:
        logger.warning(f"Audit result not found for invoice: {invoice_id}")
        raise HTTPException(status_code=404, detail="Audit result not found")
    
    return result


@router.get("/employees", response_model=List[EmployeeResponse])
def get_employees(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    logger.info(f"Fetching employees: skip={skip}, limit={limit}")
    employees = db.query(Employee).offset(skip).limit(limit).all()
    return employees


@router.post("/employees", response_model=EmployeeResponse)
def create_employee(
    employee: EmployeeCreateFull,
    signature_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    logger.info(f"Creating employee: {employee.name}")
    signature_path = None
    
    if signature_file:
        file_ext = os.path.splitext(signature_file.filename)[1]
        unique_filename = f"signature_{uuid.uuid4()}{file_ext}"
        signature_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        with open(signature_path, "wb") as buffer:
            shutil.copyfileobj(signature_file.file, buffer)
        
        logger.info(f"Signature uploaded for {employee.name}: {unique_filename}")
    
    new_employee = Employee(
        name=employee.name,
        department=employee.department,
        signature_path=signature_path,
        level=employee.level
    )
    
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    
    logger.info(f"Employee created: {new_employee.name}, ID: {new_employee.id}, Level: {new_employee.level}")
    
    return new_employee


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    logger.info("Fetching stats")
    total = db.query(Invoice).count()
    pending = db.query(Invoice).filter(Invoice.status == "pending").count()
    approved = db.query(Invoice).filter(Invoice.status == "approve").count()
    rejected = db.query(Invoice).filter(Invoice.status == "reject").count()
    review = db.query(Invoice).filter(Invoice.status == "review").count()
    
    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "review": review
    }


@router.post("/ocr/visualize")
async def ocr_visualize(
    file: UploadFile = File(...),
):
    """OCR可视化：返回带标注的图片"""
    logger.info(f"[OCR预览] ========== 开始OCR预览请求 ==========")
    logger.info(f"[OCR预览] 上传文件名: {file.filename}, Content-Type: {file.content_type}")
    
    # 支持 PDF 和图片文件
    allowed_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.pdf')
    if not file.filename.lower().endswith(allowed_extensions):
        logger.warning(f"[OCR预览] 不支持的文件类型: {file.filename}")
        raise HTTPException(status_code=400, detail="Only image and PDF files are allowed")
    
    # 保留原始文件名
    original_filename = file.filename
    file_ext = os.path.splitext(original_filename)[1].lower()
    is_pdf = file_ext == '.pdf'
    unique_filename = f"ocr_viz_{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    logger.info(f"[OCR预览] 保存临时文件: {file_path}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    logger.info(f"[OCR预览] 临时文件保存完成")
    
    # 如果是 PDF，转换为图片
    if is_pdf:
        logger.info(f"[OCR预览] 检测到 PDF 文件，开始转换...")
        try:
            image_paths = pdf_to_images(file_path, settings.UPLOAD_DIR)
            if image_paths:
                file_path = image_paths[0]
                # 修改原始文件名为转换后的图片名
                original_filename = Path(original_filename).stem + "_page_1.png"
                logger.info(f"[OCR预览] PDF 转换完成，使用第一页: {file_path}")
            else:
                raise HTTPException(status_code=400, detail="Failed to convert PDF to image")
        except Exception as e:
            logger.error(f"[OCR预览] PDF 转换失败: {str(e)}")
            raise HTTPException(status_code=400, detail=f"PDF conversion failed: {str(e)}")
    
    try:
        ocr_dir = Path("/root/autodl-tmp/caiwubaoxiao/data/ocrdata")
        ocr_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"[OCR预览] OCR输出目录: {ocr_dir}")
        
        # 使用原始文件名生成标注图片
        logger.info(f"[OCR预览] 调用 visualize_ocr_result...")
        annotated_path = visualize_ocr_result(file_path, ocr_dir, original_filename)
        
        logger.info(f"[OCR预览] ========== OCR预览完成 ==========")
        logger.info(f"[OCR预览] 返回图片URL: /api/ocr/image/{Path(annotated_path).name}")
        
        return {
            "image_url": f"/api/ocr/image/{Path(annotated_path).name}",
            "image_name": Path(annotated_path).name
        }
    except Exception as e:
        logger.error(f"[OCR预览] 处理失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OCR visualize failed: {str(e)}")


@router.get("/ocr/image/{image_name}")
async def get_ocr_image(image_name: str):
    """获取OCR可视化图片"""
    image_path = Path("/root/autodl-tmp/caiwubaoxiao/data/ocrdata") / image_name
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path, media_type="image/jpeg")


def visualize_ocr_result(image_path: str, output_dir: Path = None, original_filename: str = None) -> str:
    """使用 QwenVL 模型识别发票并生成标注图片
    
    Args:
        image_path: 输入图片路径
        output_dir: 输出目录
        original_filename: 原始文件名，用于保存标注图片
    
    Returns:
        标注图片的保存路径
    """
    logger.info(f"[OCR可视化] 开始处理 - 输入图片: {image_path}, 原始文件名: {original_filename}")
    
    from pathlib import Path
    from PIL import Image, ImageDraw, ImageFont
    
    if output_dir is None:
        output_dir = Path("/root/autodl-tmp/caiwubaoxiao/data/ocrdata")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"[OCR可视化] 输出目录: {output_dir}")
    
    # 使用 QwenVL 模型识别
    logger.info("[OCR可视化] 加载 QwenVL 服务...")
    from backend.services.qwen_vl_service import get_qwen_service
    qwen_service = get_qwen_service()
    
    logger.info("[OCR可视化] 开始 QwenVL 识别...")
    result = qwen_service.recognize_invoice(image_path)
    logger.info(f"[OCR可视化] QwenVL 识别完成: {result}")
    
    # 读取原始图片
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"[OCR可视化] 无法读取图片: {image_path}")
        raise ValueError("Cannot read image")
    
    h, w = img.shape[:2]
    logger.info(f"[OCR可视化] 图片尺寸: {w} x {h}")
    
    # 在图片右侧添加识别结果文本区域
    # 创建一个新的画布，宽度增加以容纳文本
    text_area_width = 600
    new_width = w + text_area_width
    new_img = 255 * np.ones((h, new_width, 3), dtype=np.uint8)  # 白色背景
    
    # 复制原图到新画布左侧
    new_img[:h, :w] = img
    
    # 使用 PIL 绘制中文文本
    pil_img = Image.fromarray(cv2.cvtColor(new_img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    
    # 尝试加载中文字体
    try:
        # 优先使用中文字体
        font = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 16)
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 18)
    except:
        try:
            # 备选：AR PL UKai
            font = ImageFont.truetype("/usr/share/fonts/truetype/arphic/ukai.ttc", 16)
            font_bold = ImageFont.truetype("/usr/share/fonts/truetype/arphic/ukai.ttc", 18)
        except:
            font = ImageFont.load_default()
            font_bold = font
    
    # 绘制识别结果文本
    x_offset = w + 20
    y_offset = 20
    line_height = 25
    
    # 标题
    draw.text((x_offset, y_offset), "OCR识别结果 (QwenVL)", fill=(0, 0, 255), font=font_bold)
    y_offset += line_height + 10
    
    # 绘制分割线
    draw.line([(x_offset, y_offset), (new_width - 20, y_offset)], fill=(200, 200, 200), width=1)
    y_offset += 10
    
    # 定义字段显示顺序
    fields = [
        ("发票代码", "invoice_code"),
        ("发票号码", "invoice_no"),
        ("开票日期", "date"),
        ("购买方名称", "buyer_name"),
        ("购买方税号", "buyer_tax_id"),
        ("销售方名称", "seller_name"),
        ("销售方税号", "seller_tax_id"),
        ("金额(不含税)", "amount"),
        ("税额", "tax_amount"),
        ("价税合计", "total_amount"),
    ]
    
    # 绘制字段
    for label, key in fields:
        value = result.get(key, "-")
        if value:
            text = f"{label}: {value}"
            # 截断过长的文本
            if len(text) > 35:
                text = text[:35] + "..."
            draw.text((x_offset, y_offset), text, fill=(0, 0, 0), font=font)
            y_offset += line_height
            
            if y_offset > h - 50:
                break
    
    # 绘制商品明细
    if "items" in result and result["items"]:
        y_offset += 10
        draw.text((x_offset, y_offset), "商品明细:", fill=(0, 0, 255), font=font_bold)
        y_offset += line_height
        
        for item in result["items"][:3]:  # 最多显示3个商品
            name = item.get("name", "")[:30]
            if name:
                draw.text((x_offset, y_offset), f"- {name}", fill=(0, 100, 0), font=font)
                y_offset += line_height
                if y_offset > h - 50:
                    break
    
    # 转换回 OpenCV 格式
    new_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    # 使用原始文件名保存，保持一致
    if original_filename:
        output_path = output_dir / original_filename
    else:
        input_name = Path(image_path).stem
        output_path = output_dir / f"{input_name}.jpg"
    
    logger.info(f"[OCR可视化] 保存标注图片到: {output_path}")
    cv2.imwrite(str(output_path), new_img)
    logger.info(f"[OCR可视化] 处理完成 - 输出文件: {output_path}")
    
    return str(output_path)
