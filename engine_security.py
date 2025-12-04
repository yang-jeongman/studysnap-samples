"""
엔진 보안 시스템
PDF AI 엔진의 외부 유출 방지 및 접근 제어
"""

import logging
import hashlib
import hmac
import secrets
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64

logger = logging.getLogger(__name__)


@dataclass
class APIKey:
    """API 키 정보"""
    key_id: str
    key_hash: str
    name: str
    permissions: List[str]
    created_at: str
    expires_at: Optional[str]
    is_active: bool
    usage_count: int
    last_used: Optional[str]


@dataclass
class AuditLog:
    """감사 로그"""
    log_id: str
    timestamp: str
    api_key_id: str
    action: str
    resource: str
    ip_address: Optional[str]
    success: bool
    details: Dict[str, Any]


class EngineSecurityManager:
    """엔진 보안 관리자"""

    def __init__(self, config_path: str = "security_config"):
        self.config_path = Path(config_path)
        self.config_path.mkdir(exist_ok=True)

        # 보안 파일
        self.keys_file = self.config_path / "api_keys.enc"
        self.audit_file = self.config_path / "audit_logs.enc"
        self.master_key_file = self.config_path / ".master_key"

        # 메모리 캐시
        self.api_keys: Dict[str, APIKey] = {}
        self.audit_logs: List[AuditLog] = []

        # 암호화 키
        self.cipher: Optional[Fernet] = None

        # 초기화
        self._initialize_security()

        logger.info("보안 시스템 초기화 완료")

    def _initialize_security(self):
        """보안 시스템 초기화"""
        # 마스터 키 로드 또는 생성
        if self.master_key_file.exists():
            with open(self.master_key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.master_key_file, 'wb') as f:
                f.write(key)
            # 파일 권한 제한 (읽기 전용)
            self.master_key_file.chmod(0o400)
            logger.warning("새 마스터 키 생성됨 - 백업 필요!")

        self.cipher = Fernet(key)

        # API 키 로드
        self._load_api_keys()

        # 감사 로그 로드
        self._load_audit_logs()

    def _load_api_keys(self):
        """API 키 로드"""
        try:
            if self.keys_file.exists():
                with open(self.keys_file, 'rb') as f:
                    encrypted_data = f.read()

                decrypted_data = self.cipher.decrypt(encrypted_data)
                keys_data = json.loads(decrypted_data.decode('utf-8'))

                for key_data in keys_data:
                    api_key = APIKey(**key_data)
                    self.api_keys[api_key.key_id] = api_key

                logger.info(f"{len(self.api_keys)}개 API 키 로드됨")
        except Exception as e:
            logger.error(f"API 키 로드 실패: {e}")

    def _save_api_keys(self):
        """API 키 저장"""
        try:
            keys_data = [
                {
                    "key_id": k.key_id,
                    "key_hash": k.key_hash,
                    "name": k.name,
                    "permissions": k.permissions,
                    "created_at": k.created_at,
                    "expires_at": k.expires_at,
                    "is_active": k.is_active,
                    "usage_count": k.usage_count,
                    "last_used": k.last_used
                }
                for k in self.api_keys.values()
            ]

            json_data = json.dumps(keys_data, ensure_ascii=False, indent=2)
            encrypted_data = self.cipher.encrypt(json_data.encode('utf-8'))

            with open(self.keys_file, 'wb') as f:
                f.write(encrypted_data)

            logger.info("API 키 저장 완료")
        except Exception as e:
            logger.error(f"API 키 저장 실패: {e}")

    def _load_audit_logs(self):
        """감사 로그 로드"""
        try:
            if self.audit_file.exists():
                with open(self.audit_file, 'rb') as f:
                    encrypted_data = f.read()

                decrypted_data = self.cipher.decrypt(encrypted_data)
                logs_data = json.loads(decrypted_data.decode('utf-8'))

                self.audit_logs = [AuditLog(**log_data) for log_data in logs_data]

                logger.info(f"{len(self.audit_logs)}개 감사 로그 로드됨")
        except Exception as e:
            logger.error(f"감사 로그 로드 실패: {e}")

    def _save_audit_logs(self):
        """감사 로그 저장"""
        try:
            # 최근 10000개만 유지
            recent_logs = self.audit_logs[-10000:]

            logs_data = [
                {
                    "log_id": log.log_id,
                    "timestamp": log.timestamp,
                    "api_key_id": log.api_key_id,
                    "action": log.action,
                    "resource": log.resource,
                    "ip_address": log.ip_address,
                    "success": log.success,
                    "details": log.details
                }
                for log in recent_logs
            ]

            json_data = json.dumps(logs_data, ensure_ascii=False, indent=2)
            encrypted_data = self.cipher.encrypt(json_data.encode('utf-8'))

            with open(self.audit_file, 'wb') as f:
                f.write(encrypted_data)

            logger.info("감사 로그 저장 완료")
        except Exception as e:
            logger.error(f"감사 로그 저장 실패: {e}")

    def create_api_key(
        self,
        name: str,
        permissions: List[str],
        expires_in_days: Optional[int] = None
    ) -> str:
        """
        API 키 생성

        Args:
            name: 키 이름
            permissions: 권한 목록
            expires_in_days: 만료 기간 (일)

        Returns:
            생성된 API 키 (평문)
        """
        # 랜덤 키 생성
        api_key = secrets.token_urlsafe(32)

        # 키 해시 생성
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # 키 ID 생성
        key_id = f"sk_{secrets.token_hex(8)}"

        # 만료일 계산
        expires_at = None
        if expires_in_days:
            expires_at = (
                datetime.now() + timedelta(days=expires_in_days)
            ).isoformat()

        # API 키 객체 생성
        api_key_obj = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            permissions=permissions,
            created_at=datetime.now().isoformat(),
            expires_at=expires_at,
            is_active=True,
            usage_count=0,
            last_used=None
        )

        self.api_keys[key_id] = api_key_obj
        self._save_api_keys()

        # 감사 로그
        self._add_audit_log(
            api_key_id=key_id,
            action="create_api_key",
            resource="api_key",
            success=True,
            details={"name": name, "permissions": permissions}
        )

        logger.info(f"API 키 생성: {name} ({key_id})")

        return api_key

    def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """
        API 키 검증

        Args:
            api_key: API 키 (평문)

        Returns:
            검증된 APIKey 객체 또는 None
        """
        # 키 해시 계산
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # 모든 키와 비교
        for api_key_obj in self.api_keys.values():
            if api_key_obj.key_hash == key_hash:
                # 활성 상태 확인
                if not api_key_obj.is_active:
                    logger.warning(f"비활성화된 API 키 사용 시도: {api_key_obj.key_id}")
                    return None

                # 만료 확인
                if api_key_obj.expires_at:
                    expires_at = datetime.fromisoformat(api_key_obj.expires_at)
                    if datetime.now() > expires_at:
                        logger.warning(f"만료된 API 키 사용 시도: {api_key_obj.key_id}")
                        return None

                # 사용 통계 업데이트
                api_key_obj.usage_count += 1
                api_key_obj.last_used = datetime.now().isoformat()
                self._save_api_keys()

                return api_key_obj

        logger.warning("유효하지 않은 API 키 사용 시도")
        return None

    def check_permission(self, api_key_obj: APIKey, required_permission: str) -> bool:
        """
        권한 확인

        Args:
            api_key_obj: API 키 객체
            required_permission: 필요한 권한

        Returns:
            권한 보유 여부
        """
        # 관리자 권한은 모든 권한 포함
        if "admin" in api_key_obj.permissions:
            return True

        # 특정 권한 확인
        if required_permission in api_key_obj.permissions:
            return True

        logger.warning(f"권한 부족: {api_key_obj.key_id} - {required_permission}")
        return False

    def _add_audit_log(
        self,
        api_key_id: str,
        action: str,
        resource: str,
        success: bool,
        details: Dict[str, Any],
        ip_address: Optional[str] = None
    ):
        """감사 로그 추가"""
        log = AuditLog(
            log_id=f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}",
            timestamp=datetime.now().isoformat(),
            api_key_id=api_key_id,
            action=action,
            resource=resource,
            ip_address=ip_address,
            success=success,
            details=details
        )

        self.audit_logs.append(log)

        # 주기적으로 저장 (100개마다)
        if len(self.audit_logs) % 100 == 0:
            self._save_audit_logs()

    def audit(
        self,
        api_key_obj: APIKey,
        action: str,
        resource: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """
        작업 감사

        Args:
            api_key_obj: API 키 객체
            action: 작업 유형
            resource: 리소스
            success: 성공 여부
            details: 상세 정보
            ip_address: IP 주소
        """
        self._add_audit_log(
            api_key_id=api_key_obj.key_id,
            action=action,
            resource=resource,
            success=success,
            details=details or {},
            ip_address=ip_address
        )

    def revoke_api_key(self, key_id: str):
        """API 키 비활성화"""
        if key_id in self.api_keys:
            self.api_keys[key_id].is_active = False
            self._save_api_keys()

            self._add_audit_log(
                api_key_id=key_id,
                action="revoke_api_key",
                resource="api_key",
                success=True,
                details={"key_id": key_id}
            )

            logger.info(f"API 키 비활성화: {key_id}")

    def get_security_report(self) -> Dict[str, Any]:
        """보안 리포트 생성"""
        active_keys = [k for k in self.api_keys.values() if k.is_active]
        recent_logs = self.audit_logs[-100:]

        return {
            "total_api_keys": len(self.api_keys),
            "active_api_keys": len(active_keys),
            "total_audit_logs": len(self.audit_logs),
            "recent_activities": [
                {
                    "timestamp": log.timestamp,
                    "action": log.action,
                    "success": log.success
                }
                for log in recent_logs
            ],
            "api_key_usage": [
                {
                    "name": k.name,
                    "usage_count": k.usage_count,
                    "last_used": k.last_used
                }
                for k in active_keys
            ]
        }

    def encrypt_data(self, data: bytes) -> bytes:
        """데이터 암호화"""
        return self.cipher.encrypt(data)

    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """데이터 복호화"""
        return self.cipher.decrypt(encrypted_data)


# 싱글톤 인스턴스
_security_manager = None

def get_security_manager() -> EngineSecurityManager:
    """보안 관리자 싱글톤 인스턴스"""
    global _security_manager
    if _security_manager is None:
        _security_manager = EngineSecurityManager()
    return _security_manager
