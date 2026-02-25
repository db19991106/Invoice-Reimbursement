"""审核人认证服务"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import hashlib
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.database import Auditor
from backend.logger_config import logger


class AuthService:
    """审核人认证服务"""
    
    def __init__(self):
        self._session_key = "auditor_session"
    
    def hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def create_auditor(
        self,
        db: Session,
        username: str,
        password: str,
        name: str,
        email: str = None,
        role: str = "auditor"
    ) -> Auditor:
        """创建审核人账号"""
        # 检查用户名是否已存在
        existing = db.query(Auditor).filter(Auditor.username == username).first()
        if existing:
            raise ValueError(f"用户名已存在: {username}")
        
        auditor = Auditor(
            username=username,
            password_hash=self.hash_password(password),
            name=name,
            email=email,
            role=role,
            is_active=True
        )
        
        db.add(auditor)
        db.commit()
        db.refresh(auditor)
        
        logger.info(f"创建审核人账号: {username} ({name})")
        return auditor
    
    def authenticate(
        self,
        db: Session,
        username: str,
        password: str
    ) -> Optional[Auditor]:
        """验证登录"""
        auditor = db.query(Auditor).filter(
            Auditor.username == username,
            Auditor.is_active == True
        ).first()
        
        if not auditor:
            logger.warning(f"登录失败: 用户不存在或已禁用 - {username}")
            return None
        
        if auditor.password_hash != self.hash_password(password):
            logger.warning(f"登录失败: 密码错误 - {username}")
            return None
        
        # 更新最后登录时间
        auditor.last_login = datetime.now()
        db.commit()
        
        logger.info(f"审核人登录成功: {username}")
        return auditor
    
    def get_auditor(self, db: Session, auditor_id: int) -> Optional[Auditor]:
        """获取审核人信息"""
        return db.query(Auditor).filter(Auditor.id == auditor_id).first()
    
    def update_auditor(
        self,
        db: Session,
        auditor_id: int,
        name: str = None,
        email: str = None,
        password: str = None
    ) -> Optional[Auditor]:
        """更新审核人信息"""
        auditor = db.query(Auditor).filter(Auditor.id == auditor_id).first()
        if not auditor:
            return None
        
        if name:
            auditor.name = name
        if email:
            auditor.email = email
        if password:
            auditor.password_hash = self.hash_password(password)
        
        db.commit()
        db.refresh(auditor)
        
        logger.info(f"更新审核人信息: {auditor.username}")
        return auditor
    
    def change_password(
        self,
        db: Session,
        auditor_id: int,
        old_password: str,
        new_password: str
    ) -> bool:
        """修改密码"""
        auditor = db.query(Auditor).filter(Auditor.id == auditor_id).first()
        if not auditor:
            return False
        
        if auditor.password_hash != self.hash_password(old_password):
            logger.warning(f"修改密码失败: 旧密码错误 - auditor_id={auditor_id}")
            return False
        
        auditor.password_hash = self.hash_password(new_password)
        db.commit()
        
        logger.info(f"审核人修改密码成功: {auditor.username}")
        return True
    
    def list_auditors(self, db: Session, skip: int = 0, limit: int = 50):
        """列出所有审核人"""
        return db.query(Auditor).offset(skip).limit(limit).all()
    
    def disable_auditor(self, db: Session, auditor_id: int) -> bool:
        """禁用审核人账号"""
        auditor = db.query(Auditor).filter(Auditor.id == auditor_id).first()
        if not auditor:
            return False
        
        auditor.is_active = False
        db.commit()
        
        logger.info(f"禁用审核人账号: {auditor.username}")
        return True
    
    def init_default_auditor(self, db: Session):
        """初始化默认审核人账号"""
        existing = db.query(Auditor).first()
        if existing:
            return
        
        # 创建默认管理员账号
        self.create_auditor(
            db=db,
            username="admin",
            password="admin123",
            name="系统管理员",
            role="admin"
        )
        
        # 创建默认审核人账号
        self.create_auditor(
            db=db,
            username="auditor",
            password="auditor123",
            name="审核员",
            role="auditor"
        )
        
        logger.info("已初始化默认审核人账号")


# 全局服务实例
auth_service = AuthService()


def get_auth_service() -> AuthService:
    return auth_service
