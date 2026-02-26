"""普通用户认证服务"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import hashlib
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.database import User
from backend.logger_config import logger


class UserAuthService:
    """普通用户认证服务"""
    
    def hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def create_user(
        self,
        db: Session,
        username: str,
        password: str,
        name: str,
        email: str = None,
        phone: str = None,
        department: str = None
    ) -> User:
        """创建用户账号"""
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            raise ValueError(f"用户名已存在: {username}")
        
        user = User(
            username=username,
            password_hash=self.hash_password(password),
            name=name,
            email=email,
            phone=phone,
            department=department,
            is_active=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"创建用户账号: {username} ({name})")
        return user
    
    def authenticate(
        self,
        db: Session,
        username: str,
        password: str
    ) -> Optional[User]:
        """验证登录"""
        user = db.query(User).filter(
            User.username == username,
            User.is_active == True
        ).first()
        
        if not user:
            logger.warning(f"登录失败: 用户不存在或已禁用 - {username}")
            return None
        
        if user.password_hash != self.hash_password(password):
            logger.warning(f"登录失败: 密码错误 - {username}")
            return None
        
        user.last_login = datetime.now()
        db.commit()
        
        logger.info(f"用户登录成功: {username}")
        return user
    
    def get_user(self, db: Session, user_id: int) -> Optional[User]:
        """获取用户信息"""
        return db.query(User).filter(User.id == user_id).first()
    
    def update_user(
        self,
        db: Session,
        user_id: int,
        name: str = None,
        email: str = None,
        phone: str = None,
        department: str = None
    ) -> Optional[User]:
        """更新用户信息"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        if name:
            user.name = name
        if email:
            user.email = email
        if phone:
            user.phone = phone
        if department:
            user.department = department
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"更新用户信息: {user.username}")
        return user
    
    def change_password(
        self,
        db: Session,
        user_id: int,
        old_password: str,
        new_password: str
    ) -> bool:
        """修改密码"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        if user.password_hash != self.hash_password(old_password):
            logger.warning(f"修改密码失败: 旧密码错误 - user_id={user_id}")
            return False
        
        user.password_hash = self.hash_password(new_password)
        db.commit()
        
        logger.info(f"用户修改密码成功: {user.username}")
        return True
    
    def list_users(self, db: Session, skip: int = 0, limit: int = 50):
        """列出所有用户"""
        return db.query(User).offset(skip).limit(limit).all()
    
    def disable_user(self, db: Session, user_id: int) -> bool:
        """禁用用户账号"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_active = False
        db.commit()
        
        logger.info(f"禁用用户账号: {user.username}")
        return True
    
    def get_user_count(self, db: Session) -> int:
        """获取用户总数"""
        return db.query(User).count()


user_auth_service = UserAuthService()


def get_user_auth_service() -> UserAuthService:
    return user_auth_service
