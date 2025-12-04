"""
모듈화된 PDF 엔진 API
재사용 가능한 PDF 변환 엔진 인터페이스
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

from intelligent_layout_engine import get_layout_engine, IntelligentLayoutEngine
from pdf_ai_agent import get_ai_agent, PDFAIAgent
from engine_security import get_security_manager, EngineSecurityManager, APIKey

logger = logging.getLogger(__name__)


class EngineType(Enum):
    """엔진 타입"""
    LAYOUT = "layout"  # 레이아웃 엔진
    AI_AGENT = "ai_agent"  # AI 에이전트
    SECURITY = "security"  # 보안 엔진
    EXTRACTION = "extraction"  # 추출 엔진
    CONVERSION = "conversion"  # 변환 엔진


class EngineVersion(Enum):
    """엔진 버전"""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


@dataclass
class EngineInfo:
    """엔진 정보"""
    engine_type: EngineType
    version: EngineVersion
    name: str
    description: str
    capabilities: List[str]
    dependencies: List[str]


class BaseEngine(ABC):
    """기본 엔진 인터페이스"""

    @abstractmethod
    def get_info(self) -> EngineInfo:
        """엔진 정보 반환"""
        pass

    @abstractmethod
    def process(self, input_data: Any, **kwargs) -> Any:
        """엔진 처리"""
        pass

    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """입력 데이터 검증"""
        pass


class LayoutEngineAPI(BaseEngine):
    """레이아웃 엔진 API"""

    def __init__(self):
        self.engine: IntelligentLayoutEngine = get_layout_engine()

    def get_info(self) -> EngineInfo:
        return EngineInfo(
            engine_type=EngineType.LAYOUT,
            version=EngineVersion.V1_0,
            name="Intelligent Layout Engine",
            description="PDF 객체 인식 및 모바일 최적 레이아웃 자동 생성",
            capabilities=[
                "object_recognition",
                "object_grouping",
                "mobile_layout_optimization",
                "html_generation"
            ],
            dependencies=[]
        )

    def validate_input(self, input_data: Any) -> bool:
        """입력 데이터 검증"""
        if not isinstance(input_data, dict):
            return False

        # 필수 필드 확인
        required_fields = ["structured_data", "content_type"]
        return all(field in input_data for field in required_fields)

    def process(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        레이아웃 엔진 처리

        Args:
            input_data: 추출된 PDF 데이터
            **kwargs: 추가 옵션

        Returns:
            레이아웃 구조
        """
        if not self.validate_input(input_data):
            raise ValueError("Invalid input data for Layout Engine")

        layout_structure = self.engine.analyze_document(input_data)

        return {
            "success": True,
            "layout_structure": layout_structure,
            "engine_info": self.get_info().__dict__
        }

    def generate_html(self, layout_structure: Dict[str, Any]) -> str:
        """HTML 생성"""
        return self.engine.generate_mobile_html_structure(layout_structure)


class AIAgentEngineAPI(BaseEngine):
    """AI 에이전트 엔진 API"""

    def __init__(self):
        self.agent: PDFAIAgent = get_ai_agent()

    def get_info(self) -> EngineInfo:
        return EngineInfo(
            engine_type=EngineType.AI_AGENT,
            version=EngineVersion.V1_0,
            name="Self-Learning PDF AI Agent",
            description="자기학습 PDF 변환 AI 에이전트",
            capabilities=[
                "pattern_learning",
                "conversion_optimization",
                "quality_assessment",
                "continuous_improvement"
            ],
            dependencies=[]
        )

    def validate_input(self, input_data: Any) -> bool:
        """입력 데이터 검증"""
        if isinstance(input_data, bytes):
            return True
        if isinstance(input_data, dict):
            return "pdf_data" in input_data or "conversion_result" in input_data
        return False

    def process(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """
        AI 에이전트 처리

        Args:
            input_data: PDF 데이터 또는 변환 결과
            **kwargs: 추가 옵션

        Returns:
            분석 결과 또는 학습 결과
        """
        if not self.validate_input(input_data):
            raise ValueError("Invalid input data for AI Agent")

        action = kwargs.get("action", "analyze")

        if action == "analyze":
            # PDF 분석
            pdf_data = input_data if isinstance(input_data, bytes) else input_data.get("pdf_data")
            content_type = kwargs.get("content_type", "general")

            analysis = self.agent.analyze_pdf(pdf_data, content_type)

            return {
                "success": True,
                "analysis": analysis,
                "engine_info": self.get_info().__dict__
            }

        elif action == "learn":
            # 변환 결과로부터 학습
            pdf_data = input_data.get("pdf_data")
            conversion_result = input_data.get("conversion_result")
            user_feedback = kwargs.get("user_feedback")

            self.agent.learn_from_conversion(pdf_data, conversion_result, user_feedback)

            return {
                "success": True,
                "message": "Learning completed",
                "engine_info": self.get_info().__dict__
            }

        elif action == "insights":
            # 학습 인사이트 제공
            insights = self.agent.get_learning_insights()

            return {
                "success": True,
                "insights": insights,
                "engine_info": self.get_info().__dict__
            }

        else:
            raise ValueError(f"Unknown action: {action}")


class SecurityEngineAPI(BaseEngine):
    """보안 엔진 API"""

    def __init__(self):
        self.security: EngineSecurityManager = get_security_manager()

    def get_info(self) -> EngineInfo:
        return EngineInfo(
            engine_type=EngineType.SECURITY,
            version=EngineVersion.V1_0,
            name="Engine Security Manager",
            description="엔진 보안 및 접근 제어 시스템",
            capabilities=[
                "api_key_management",
                "access_control",
                "audit_logging",
                "data_encryption"
            ],
            dependencies=[]
        )

    def validate_input(self, input_data: Any) -> bool:
        """입력 데이터 검증"""
        return isinstance(input_data, dict)

    def process(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        보안 엔진 처리

        Args:
            input_data: 보안 작업 데이터
            **kwargs: 추가 옵션

        Returns:
            보안 작업 결과
        """
        if not self.validate_input(input_data):
            raise ValueError("Invalid input data for Security Engine")

        action = input_data.get("action", "validate")

        if action == "validate":
            # API 키 검증
            api_key = input_data.get("api_key")
            api_key_obj = self.security.validate_api_key(api_key)

            if api_key_obj:
                return {
                    "success": True,
                    "valid": True,
                    "key_info": {
                        "key_id": api_key_obj.key_id,
                        "name": api_key_obj.name,
                        "permissions": api_key_obj.permissions
                    }
                }
            else:
                return {
                    "success": True,
                    "valid": False
                }

        elif action == "create_key":
            # API 키 생성
            name = input_data.get("name")
            permissions = input_data.get("permissions", [])
            expires_in_days = input_data.get("expires_in_days")

            api_key = self.security.create_api_key(name, permissions, expires_in_days)

            return {
                "success": True,
                "api_key": api_key,
                "message": "API key created successfully"
            }

        elif action == "check_permission":
            # 권한 확인
            api_key = input_data.get("api_key")
            required_permission = input_data.get("permission")

            api_key_obj = self.security.validate_api_key(api_key)

            if api_key_obj:
                has_permission = self.security.check_permission(api_key_obj, required_permission)

                return {
                    "success": True,
                    "has_permission": has_permission
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid API key"
                }

        elif action == "audit":
            # 감사 로그 기록
            api_key = input_data.get("api_key")
            operation = input_data.get("operation")
            resource = input_data.get("resource")
            success = input_data.get("success", True)
            details = input_data.get("details", {})

            api_key_obj = self.security.validate_api_key(api_key)

            if api_key_obj:
                self.security.audit(
                    api_key_obj,
                    operation,
                    resource,
                    success,
                    details
                )

                return {
                    "success": True,
                    "message": "Audit log recorded"
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid API key"
                }

        elif action == "report":
            # 보안 리포트
            report = self.security.get_security_report()

            return {
                "success": True,
                "report": report,
                "engine_info": self.get_info().__dict__
            }

        else:
            raise ValueError(f"Unknown action: {action}")


class EngineRegistry:
    """엔진 레지스트리"""

    def __init__(self):
        self.engines: Dict[EngineType, BaseEngine] = {}
        self._register_default_engines()

    def _register_default_engines(self):
        """기본 엔진 등록"""
        self.register_engine(EngineType.LAYOUT, LayoutEngineAPI())
        self.register_engine(EngineType.AI_AGENT, AIAgentEngineAPI())
        self.register_engine(EngineType.SECURITY, SecurityEngineAPI())

        logger.info(f"{len(self.engines)}개 엔진 등록됨")

    def register_engine(self, engine_type: EngineType, engine: BaseEngine):
        """엔진 등록"""
        self.engines[engine_type] = engine
        logger.info(f"엔진 등록: {engine_type.value}")

    def get_engine(self, engine_type: EngineType) -> Optional[BaseEngine]:
        """엔진 가져오기"""
        return self.engines.get(engine_type)

    def list_engines(self) -> List[EngineInfo]:
        """등록된 엔진 목록"""
        return [engine.get_info() for engine in self.engines.values()]


class PDFEngineAPI:
    """통합 PDF 엔진 API"""

    def __init__(self, require_authentication: bool = False):
        self.registry = EngineRegistry()
        self.require_authentication = require_authentication
        self.security_engine: SecurityEngineAPI = self.registry.get_engine(EngineType.SECURITY)

    def authenticate(self, api_key: str) -> Optional[APIKey]:
        """인증"""
        if not self.require_authentication:
            return None

        result = self.security_engine.process({
            "action": "validate",
            "api_key": api_key
        })

        if result.get("valid"):
            return result.get("key_info")
        else:
            raise PermissionError("Invalid API key")

    def use_engine(
        self,
        engine_type: EngineType,
        input_data: Any,
        api_key: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        엔진 사용

        Args:
            engine_type: 엔진 타입
            input_data: 입력 데이터
            api_key: API 키 (인증 필요 시)
            **kwargs: 추가 옵션

        Returns:
            엔진 처리 결과
        """
        # 인증
        api_key_info = None
        if self.require_authentication:
            api_key_info = self.authenticate(api_key)

        # 엔진 가져오기
        engine = self.registry.get_engine(engine_type)

        if not engine:
            raise ValueError(f"Engine not found: {engine_type}")

        # 엔진 처리
        try:
            result = engine.process(input_data, **kwargs)

            # 감사 로그 (인증된 경우)
            if api_key_info and engine_type != EngineType.SECURITY:
                self.security_engine.process({
                    "action": "audit",
                    "api_key": api_key,
                    "operation": "use_engine",
                    "resource": engine_type.value,
                    "success": True,
                    "details": {"engine_type": engine_type.value}
                })

            return result

        except Exception as e:
            logger.error(f"엔진 처리 실패: {e}")

            # 감사 로그 (실패)
            if api_key_info and engine_type != EngineType.SECURITY:
                self.security_engine.process({
                    "action": "audit",
                    "api_key": api_key,
                    "operation": "use_engine",
                    "resource": engine_type.value,
                    "success": False,
                    "details": {"error": str(e)}
                })

            raise

    def get_engine_info(self, engine_type: EngineType) -> Optional[EngineInfo]:
        """엔진 정보 가져오기"""
        engine = self.registry.get_engine(engine_type)
        if engine:
            return engine.get_info()
        return None

    def list_available_engines(self) -> List[Dict[str, Any]]:
        """사용 가능한 엔진 목록"""
        engines_info = self.registry.list_engines()

        return [
            {
                "engine_type": info.engine_type.value,
                "version": info.version.value,
                "name": info.name,
                "description": info.description,
                "capabilities": info.capabilities
            }
            for info in engines_info
        ]


# 싱글톤 인스턴스
_engine_api = None

def get_engine_api(require_authentication: bool = False) -> PDFEngineAPI:
    """엔진 API 싱글톤 인스턴스"""
    global _engine_api
    if _engine_api is None:
        _engine_api = PDFEngineAPI(require_authentication=require_authentication)
    return _engine_api
