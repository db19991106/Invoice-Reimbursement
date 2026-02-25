import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import hashlib
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
import redis
from datetime import datetime
from sqlalchemy.orm import Session

from backend.database import Invoice
from backend.config import settings
from backend.logger_config import logger


@dataclass
class DuplicateCheckResult:
    is_duplicate: bool
    message: str
    existing_invoice_id: Optional[int] = None
    locked: bool = False


class DuplicateChecker:
    def __init__(self):
        self._redis_client = None
        self._lock_timeout = 30
        self._use_redis = True
        self._try_init_redis()
    
    def _try_init_redis(self):
        import threading
        # 始终初始化本地锁管理器
        self._local_locks = {}
        self._lock_manager = {}
        self._lock_mutex = threading.Lock()
        
        try:
            self._redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=2
            )
            self._redis_client.ping()
            logger.info("Redis connection established for duplicate checker")
        except Exception as e:
            logger.warning(f"Redis not available, using local lock only: {e}")
            self._use_redis = False
    
    def generate_fingerprint(
        self,
        invoice_code: str,
        invoice_no: str,
        amount: float
    ) -> str:
        key_string = f"{invoice_code}:{invoice_no}:{amount}"
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def acquire_lock(self, fingerprint: str) -> bool:
        lock_key = f"invoice_lock:{fingerprint}"
        
        if self._use_redis and self._redis_client:
            try:
                result = self._redis_client.set(
                    lock_key,
                    f"locked:{datetime.now().isoformat()}",
                    nx=True,
                    ex=self._lock_timeout
                )
                return bool(result)
            except Exception as e:
                logger.warning(f"Redis lock failed: {e}")
                return self._acquire_local_lock(fingerprint)
        
        return self._acquire_local_lock(fingerprint)
    
    def _acquire_local_lock(self, fingerprint: str) -> bool:
        import threading
        with self._lock_mutex:
            if fingerprint not in self._lock_manager:
                self._lock_manager[fingerprint] = threading.Lock()
        
        return self._lock_manager[fingerprint].acquire(blocking=False)
    
    def release_lock(self, fingerprint: str):
        lock_key = f"invoice_lock:{fingerprint}"
        
        if self._use_redis and self._redis_client:
            try:
                self._redis_client.delete(lock_key)
            except Exception as e:
                logger.warning(f"Redis lock release failed: {e}")
        
        if hasattr(self, '_lock_manager') and fingerprint in self._lock_manager:
            try:
                self._lock_manager[fingerprint].release()
            except:
                pass
    
    def check_duplicate(
        self,
        invoice_code: str,
        invoice_no: str,
        amount: float,
        db: Session,
        auto_lock: bool = True
    ) -> DuplicateCheckResult:
        if not invoice_code or not invoice_no or not amount:
            return DuplicateCheckResult(
                is_duplicate=False,
                message="缺少发票代码/号码/金额信息，跳过重复检查"
            )
        
        fingerprint = self.generate_fingerprint(invoice_code, invoice_no, amount)
        
        # 只检测已通过(approve)或审核中(review)的发票
        existing = db.query(Invoice).filter(
            Invoice.invoice_code == invoice_code,
            Invoice.invoice_no == invoice_no,
            Invoice.amount == amount,
            Invoice.status.in_(["approve", "review"])
        ).first()
        
        if existing:
            return DuplicateCheckResult(
                is_duplicate=True,
                message=f"检测到重复发票，已存在于ID={existing.id}的报销单中",
                existing_invoice_id=existing.id
            )
        
        if auto_lock:
            locked = self.acquire_lock(fingerprint)
            if not locked:
                return DuplicateCheckResult(
                    is_duplicate=True,
                    message="该发票正在被其他人提交，请稍后重试",
                    locked=True
                )
        
        return DuplicateCheckResult(
            is_duplicate=False,
            message="未检测到重复发票",
            locked=auto_lock and self.acquire_lock(fingerprint) if auto_lock else False
        )
    
    def register_invoice(
        self,
        invoice_id: int,
        invoice_code: str,
        invoice_no: str,
        amount: float,
        db: Session
    ) -> bool:
        fingerprint = self.generate_fingerprint(invoice_code, invoice_no, amount)
        
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice:
            invoice.invoice_code = invoice_code
            invoice.fingerprint = fingerprint
            db.commit()
            logger.info(f"Registered invoice fingerprint: {fingerprint}")
        
        self.release_lock(fingerprint)
        return True
    
    def release_invoice_lock(
        self,
        invoice_code: str,
        invoice_no: str,
        amount: float
    ):
        fingerprint = self.generate_fingerprint(invoice_code, invoice_no, amount)
        self.release_lock(fingerprint)
        logger.info(f"Released lock for fingerprint: {fingerprint}")


duplicate_checker = DuplicateChecker()


def get_duplicate_checker() -> DuplicateChecker:
    return duplicate_checker
