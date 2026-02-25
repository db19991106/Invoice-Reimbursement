import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from backend.config import settings

engine = create_engine(f"sqlite:///{settings.DATABASE_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    department = Column(String(100))
    signature_path = Column(String(255))
    credit_score = Column(Float, default=100.0)
    level = Column(Integer, default=9)
    created_at = Column(DateTime, default=datetime.now)
    
    invoices = relationship("Invoice", back_populates="employee")

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    file_path = Column(String(255), nullable=False)
    invoice_code = Column(String(50))
    invoice_no = Column(String(50))
    fingerprint = Column(String(64))
    amount = Column(Float)
    tax_amount = Column(Float)
    total_amount = Column(Float)
    date = Column(String(20))
    seller_name = Column(String(200))
    seller_tax_id = Column(String(50))
    seller_address = Column(String(255))
    seller_bank = Column(String(255))
    buyer_name = Column(String(200))
    buyer_tax_id = Column(String(50))
    buyer_address = Column(String(255))
    buyer_bank = Column(String(255))
    items = Column(Text)
    status = Column(String(20), default="pending")
    channel = Column(String(20), default="pending")
    expense_type = Column(String(50))
    destination_city = Column(String(100))
    person_count = Column(Integer, default=1)
    trip_days = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    
    employee = relationship("Employee", back_populates="invoices")
    audit_record = relationship("AuditRecord", back_populates="invoice", uselist=False)

class AuditRecord(Base):
    __tablename__ = "audit_records"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), unique=True)
    signature_score = Column(Float)
    ocr_result = Column(Text)
    ocr_confidence = Column(Float)
    risk_level = Column(String(20))
    risk_score = Column(Float)
    risk_reasons = Column(Text)
    decision = Column(String(20))
    channel = Column(String(20))
    validation_items = Column(Text)
    stamp_detected = Column(String(10))
    duplicate_checked = Column(Boolean, default=False)
    company_matched = Column(String(10))
    reviewed_at = Column(DateTime, default=datetime.now)
    reviewed_by = Column(Integer, ForeignKey("auditors.id"), nullable=True)  # 审核人ID
    
    invoice = relationship("Invoice", back_populates="audit_record")
    auditor = relationship("Auditor", back_populates="audit_records")


class Auditor(Base):
    """审核人账号"""
    __tablename__ = "auditors"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)  # 登录用户名
    password_hash = Column(String(255), nullable=False)  # 密码哈希
    name = Column(String(50), nullable=False)  # 显示名称
    email = Column(String(100))
    role = Column(String(20), default="auditor")  # 角色: admin/auditor
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime)
    
    audit_records = relationship("AuditRecord", back_populates="auditor")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
