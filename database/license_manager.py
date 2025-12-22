"""
StudySnap Backend - 라이선스 관리 시스템
15일 체험판 라이선스 관리 및 사용량 제한
"""

import os
import json
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 라이선스 데이터 파일 경로
LICENSE_FILE = Path(__file__).parent / "license_data.json"


class LicenseManager:
    """라이선스 관리 클래스"""

    def __init__(self):
        self.license_data = self._load_license_data()
        self.trial_days = int(os.environ.get('TRIAL_DAYS', 15))
        self.daily_limit = int(os.environ.get('DAILY_CONVERT_LIMIT', 10))
        self.max_bulletins = int(os.environ.get('MAX_BULLETINS', 30))

    def _load_license_data(self) -> Dict:
        """라이선스 데이터 로드"""
        if LICENSE_FILE.exists():
            try:
                with open(LICENSE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"라이선스 데이터 로드 실패: {e}")

        # 기본 라이선스 데이터
        return {
            "licenses": {},
            "usage": {},
            "created_at": datetime.now().isoformat()
        }

    def _save_license_data(self):
        """라이선스 데이터 저장"""
        try:
            with open(LICENSE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.license_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"라이선스 데이터 저장 실패: {e}")

    def create_trial_license(self, church_id: str, church_name: str = "",
                             days: int = None) -> Dict[str, Any]:
        """
        15일 체험판 라이선스 생성

        Args:
            church_id: 교회 고유 ID
            church_name: 교회 이름
            days: 사용 기간 (기본값: TRIAL_DAYS 환경변수)

        Returns:
            라이선스 정보 딕셔너리
        """
        if days is None:
            days = self.trial_days

        # 라이선스 키 생성
        license_key = self._generate_license_key(church_id)

        # 시작일 및 만료일 계산
        start_date = datetime.now()
        expire_date = start_date + timedelta(days=days)

        license_info = {
            "license_key": license_key,
            "church_id": church_id,
            "church_name": church_name,
            "plan_type": "trial",
            "days": days,
            "start_date": start_date.isoformat(),
            "expire_date": expire_date.isoformat(),
            "daily_limit": self.daily_limit,
            "max_bulletins": self.max_bulletins,
            "is_active": True,
            "created_at": start_date.isoformat()
        }

        # 저장
        self.license_data["licenses"][license_key] = license_info
        self._save_license_data()

        logger.info(f"체험판 라이선스 생성: {church_name} ({church_id}), {days}일")
        return license_info

    def _generate_license_key(self, church_id: str) -> str:
        """라이선스 키 생성"""
        random_part = secrets.token_hex(8)
        hash_part = hashlib.sha256(f"{church_id}{random_part}".encode()).hexdigest()[:8]
        return f"FGFC-{hash_part.upper()}-{random_part.upper()[:8]}"

    def validate_license(self, license_key: str) -> Dict[str, Any]:
        """
        라이선스 유효성 검증

        Returns:
            {
                "valid": bool,
                "message": str,
                "remaining_days": int,
                "daily_remaining": int,
                "license_info": dict
            }
        """
        license_info = self.license_data["licenses"].get(license_key)

        if not license_info:
            return {
                "valid": False,
                "message": "유효하지 않은 라이선스 키입니다.",
                "remaining_days": 0,
                "daily_remaining": 0,
                "license_info": None
            }

        if not license_info.get("is_active"):
            return {
                "valid": False,
                "message": "비활성화된 라이선스입니다.",
                "remaining_days": 0,
                "daily_remaining": 0,
                "license_info": license_info
            }

        # 만료일 확인
        expire_date = datetime.fromisoformat(license_info["expire_date"])
        now = datetime.now()

        if now > expire_date:
            return {
                "valid": False,
                "message": f"라이선스가 만료되었습니다. (만료일: {expire_date.strftime('%Y-%m-%d')})",
                "remaining_days": 0,
                "daily_remaining": 0,
                "license_info": license_info
            }

        # 남은 일수 계산
        remaining_days = (expire_date - now).days

        # 일일 사용량 확인
        daily_remaining = self._get_daily_remaining(license_key)

        return {
            "valid": True,
            "message": f"유효한 라이선스입니다. (남은 기간: {remaining_days}일)",
            "remaining_days": remaining_days,
            "daily_remaining": daily_remaining,
            "license_info": license_info
        }

    def _get_daily_remaining(self, license_key: str) -> int:
        """일일 남은 사용 횟수 조회"""
        today = datetime.now().strftime("%Y-%m-%d")
        usage_key = f"{license_key}_{today}"

        usage = self.license_data.get("usage", {})
        today_usage = usage.get(usage_key, 0)

        license_info = self.license_data["licenses"].get(license_key, {})
        daily_limit = license_info.get("daily_limit", self.daily_limit)

        return max(0, daily_limit - today_usage)

    def record_usage(self, license_key: str, action: str = "convert") -> Dict[str, Any]:
        """
        사용량 기록

        Returns:
            {"success": bool, "message": str, "daily_remaining": int}
        """
        # 라이선스 검증
        validation = self.validate_license(license_key)
        if not validation["valid"]:
            return {
                "success": False,
                "message": validation["message"],
                "daily_remaining": 0
            }

        # 일일 제한 확인 (개발 모드에서는 비활성화)
        # if validation["daily_remaining"] <= 0:
        #     return {
        #         "success": False,
        #         "message": "오늘의 사용 한도를 초과했습니다. 내일 다시 시도해주세요.",
        #         "daily_remaining": 0
        #     }

        # 사용량 기록
        today = datetime.now().strftime("%Y-%m-%d")
        usage_key = f"{license_key}_{today}"

        if "usage" not in self.license_data:
            self.license_data["usage"] = {}

        self.license_data["usage"][usage_key] = \
            self.license_data["usage"].get(usage_key, 0) + 1

        self._save_license_data()

        daily_remaining = validation["daily_remaining"] - 1
        logger.info(f"사용량 기록: {license_key}, {action}, 남은 횟수: {daily_remaining}")

        return {
            "success": True,
            "message": "사용량이 기록되었습니다.",
            "daily_remaining": daily_remaining
        }

    def get_license_status(self, license_key: str) -> Dict[str, Any]:
        """라이선스 상태 조회"""
        validation = self.validate_license(license_key)

        if not validation["license_info"]:
            return {
                "status": "invalid",
                "message": "등록되지 않은 라이선스입니다."
            }

        license_info = validation["license_info"]

        return {
            "status": "active" if validation["valid"] else "expired",
            "church_name": license_info.get("church_name", ""),
            "plan_type": license_info.get("plan_type", "trial"),
            "start_date": license_info.get("start_date"),
            "expire_date": license_info.get("expire_date"),
            "remaining_days": validation["remaining_days"],
            "daily_limit": license_info.get("daily_limit", self.daily_limit),
            "daily_remaining": validation["daily_remaining"],
            "max_bulletins": license_info.get("max_bulletins", self.max_bulletins)
        }

    def get_remaining_days(self, license_key: str) -> int:
        """남은 사용일 반환"""
        validation = self.validate_license(license_key)
        return validation["remaining_days"]

    def deactivate_license(self, license_key: str) -> bool:
        """라이선스 비활성화"""
        if license_key in self.license_data["licenses"]:
            self.license_data["licenses"][license_key]["is_active"] = False
            self._save_license_data()
            logger.info(f"라이선스 비활성화: {license_key}")
            return True
        return False

    def extend_license(self, license_key: str, days: int) -> bool:
        """라이선스 연장"""
        if license_key not in self.license_data["licenses"]:
            return False

        license_info = self.license_data["licenses"][license_key]
        current_expire = datetime.fromisoformat(license_info["expire_date"])

        # 이미 만료된 경우 현재 날짜부터 연장
        if current_expire < datetime.now():
            current_expire = datetime.now()

        new_expire = current_expire + timedelta(days=days)
        license_info["expire_date"] = new_expire.isoformat()
        license_info["is_active"] = True
        license_info["days"] += days

        self._save_license_data()
        logger.info(f"라이선스 연장: {license_key}, +{days}일")
        return True

    def get_all_licenses(self) -> list:
        """모든 라이선스 목록"""
        licenses = []
        for key, info in self.license_data.get("licenses", {}).items():
            validation = self.validate_license(key)
            licenses.append({
                "license_key": key,
                **info,
                "remaining_days": validation["remaining_days"],
                "is_valid": validation["valid"]
            })
        return licenses

    def cleanup_old_usage(self, days_to_keep: int = 30):
        """오래된 사용량 데이터 정리"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        usage = self.license_data.get("usage", {})
        keys_to_delete = [
            key for key in usage.keys()
            if key.split("_")[-1] < cutoff_str
        ]

        for key in keys_to_delete:
            del self.license_data["usage"][key]

        if keys_to_delete:
            self._save_license_data()
            logger.info(f"오래된 사용량 데이터 {len(keys_to_delete)}개 삭제")


# 싱글톤 인스턴스
_license_manager: Optional[LicenseManager] = None


def get_license_manager() -> LicenseManager:
    """라이선스 매니저 싱글톤 인스턴스"""
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager


# ============================================
# 여의도순복음교회 전용 체험판 생성
# ============================================

def create_fgfc_trial_license() -> Dict[str, Any]:
    """여의도순복음교회 15일 체험판 라이선스 생성"""
    manager = get_license_manager()

    # 기존 라이선스 확인
    for key, info in manager.license_data.get("licenses", {}).items():
        if info.get("church_id") == "fgfc" and info.get("is_active"):
            validation = manager.validate_license(key)
            if validation["valid"]:
                logger.info(f"기존 유효한 라이선스 사용: {key}")
                return {
                    "license_key": key,
                    **info,
                    "remaining_days": validation["remaining_days"],
                    "is_new": False
                }

    # 새 라이선스 생성
    license_info = manager.create_trial_license(
        church_id="fgfc",
        church_name="여의도순복음교회",
        days=15
    )

    return {
        **license_info,
        "is_new": True
    }


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)

    # 여의도순복음교회 체험판 라이선스 생성
    result = create_fgfc_trial_license()
    print("\n=== 여의도순복음교회 체험판 라이선스 ===")
    print(f"라이선스 키: {result['license_key']}")
    print(f"시작일: {result['start_date']}")
    print(f"만료일: {result['expire_date']}")
    print(f"사용 기간: {result['days']}일")
    print(f"일일 제한: {result['daily_limit']}회")
    print(f"새로 생성됨: {result.get('is_new', False)}")

    # 검증 테스트
    manager = get_license_manager()
    validation = manager.validate_license(result['license_key'])
    print(f"\n검증 결과: {validation['message']}")
    print(f"남은 일수: {validation['remaining_days']}일")
    print(f"오늘 남은 횟수: {validation['daily_remaining']}회")

    # 사용량 기록 테스트
    usage_result = manager.record_usage(result['license_key'], "convert")
    print(f"\n사용량 기록: {usage_result['message']}")
    print(f"남은 횟수: {usage_result['daily_remaining']}회")
