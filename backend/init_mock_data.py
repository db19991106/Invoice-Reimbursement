import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, Employee, Invoice, init_db
from backend.config import settings


def create_mock_employees(db):
    employees_data = [
        {"name": "张三", "department": "技术部", "level": 10},
        {"name": "李四", "department": "市场部", "level": 9},
        {"name": "王五", "department": "财务部", "level": 11},
        {"name": "赵六", "department": "人事部", "level": 9},
        {"name": "钱七", "department": "运营部", "level": 12},
    ]
    
    employees = []
    for emp_data in employees_data:
        emp = Employee(
            name=emp_data["name"],
            department=emp_data["department"],
            level=emp_data["level"]
        )
        db.add(emp)
        employees.append(emp)
    
    db.commit()
    print(f"Created {len(employees)} employees")
    return employees


def create_mock_invoices(db, employees):
    invoice_dir = os.path.join(settings.INVOICE_DATA_DIR, "imgs")
    
    if not os.path.exists(invoice_dir):
        print(f"Invoice directory not found: {invoice_dir}")
        return
    
    image_files = [f for f in os.listdir(invoice_dir) if f.endswith('.jpg')][:20]
    
    invoices = []
    for i, img_file in enumerate(image_files):
        emp = employees[i % len(employees)] if employees else None
        
        invoice = Invoice(
            employee_id=emp.id if emp else None,
            file_path=os.path.join(invoice_dir, img_file),
            status="pending"
        )
        db.add(invoice)
        invoices.append(invoice)
    
    db.commit()
    print(f"Created {len(invoices)} invoices")


def main():
    print("Initializing database...")
    init_db()
    
    db = SessionLocal()
    try:
        existing_employees = db.query(Employee).count()
        if existing_employees > 0:
            print(f"Database already has {existing_employees} employees")
            return
        
        print("Creating mock employees...")
        employees = create_mock_employees(db)
        
        print("Creating mock invoices...")
        create_mock_invoices(db, employees)
        
        print("Mock data created successfully!")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
