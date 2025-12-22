"""
StudySnap Backend - PDF to Mobile HTML Converter
FastAPI 기반 백엔드 서버
"""

import os
import uuid
import shutil
import logging
import zipfile
import io
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from urllib.parse import unquote, quote
from dotenv import load_dotenv

from pdf_converter import PDFConverter
from html_generator import HTMLGenerator
from learning_system import get_learning_system
from universal_parser import get_universal_parser
from template_engine import get_template_engine
from localization import get_localization_manager
from verification_system import get_verification_system, get_church_bulletin_verifier
from intelligent_layout_engine import get_layout_engine

# 데이터베이스 연결
from database.db_connection import (
    get_db, init_db,
    DocumentRepository, ChurchBulletinRepository, AuditLogger
)

# 라이선스 관리
from database.license_manager import (
    get_license_manager, create_fgfc_trial_license, LicenseManager
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 시스템 초기화
learning_system = get_learning_system()
universal_parser = get_universal_parser()
template_engine = get_template_engine()
localization_manager = get_localization_manager()
verification_system = get_verification_system()
church_bulletin_verifier = get_church_bulletin_verifier()
layout_engine = get_layout_engine()

# 데이터베이스 초기화
try:
    db_manager = init_db()
    doc_repo = DocumentRepository(db_manager)
    bulletin_repo = ChurchBulletinRepository(db_manager)
    audit_logger = AuditLogger(db_manager)
    logger.info("데이터베이스 초기화 완료")
except Exception as db_err:
    logger.warning(f"데이터베이스 초기화 실패: {db_err} - DB 기능 비활성화")
    db_manager = None
    doc_repo = None
    bulletin_repo = None
    audit_logger = None

# 환경변수 로드
load_dotenv()

# FastAPI 앱 생성
app = FastAPI(
    title="StudySnap API",
    description="PDF를 모바일 최적화 HTML로 변환하는 API",
    version="1.0.0"
)

# ============================================
# 한글 URL 인코딩 미들웨어
# ============================================
class KoreanURLMiddleware(BaseHTTPMiddleware):
    """
    한글 URL을 올바르게 처리하는 미들웨어
    Windows에서 외부 접속 시 한글 깨짐 문제 해결
    """
    async def dispatch(self, request: Request, call_next):
        # 원본 경로 가져오기
        original_path = request.scope.get('path', '')

        # URL 디코딩 시도 (이미 디코딩된 경우 그대로 유지)
        try:
            # UTF-8로 URL 디코딩
            decoded_path = unquote(original_path, encoding='utf-8')

            # CP949로 잘못 인코딩된 경우 복구 시도
            if decoded_path != original_path:
                try:
                    # CP949로 인코딩된 바이트를 UTF-8로 재해석
                    test_bytes = decoded_path.encode('latin-1')
                    try:
                        # CP949로 디코딩 시도
                        cp949_decoded = test_bytes.decode('cp949')
                        # UTF-8로 다시 인코딩하여 올바른 경로 생성
                        decoded_path = cp949_decoded
                        logger.debug(f"CP949 복구: {original_path} -> {decoded_path}")
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        pass
                except (UnicodeDecodeError, UnicodeEncodeError):
                    pass

            # 경로 업데이트
            request.scope['path'] = decoded_path

        except Exception as e:
            logger.warning(f"URL 디코딩 실패: {original_path} - {e}")

        response = await call_next(request)
        return response

# 미들웨어 등록 (순서 중요: 가장 먼저 실행되어야 함)
app.add_middleware(KoreanURLMiddleware)

# CORS 설정 (프론트엔드에서 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://studysnap-demo.netlify.app",
        "*"  # 개발 중에는 모든 origin 허용
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 디렉토리 설정
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMPLATES_DIR = BASE_DIR / "templates"

# 디렉토리 생성
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

# 정적 파일 서빙
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

# static 폴더는 StaticFiles로 서빙 (영문 파일명만 있음)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

# outputs 폴더는 한글 지원을 위해 커스텀 라우터로 처리 (아래 serve_outputs_file 참조)
# app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")  # 비활성화

# PDF 변환기 및 HTML 생성기 초기화
pdf_converter = PDFConverter()
html_generator = HTMLGenerator()


# ============================================
# 유틸리티 함수
# ============================================

def cleanup_temp_files(job_id: str = None, keep_outputs: bool = True, cleanup_old_files: bool = False, max_age_hours: int = 24):
    """
    임시 파일 정리 함수

    Parameters:
    - job_id: 특정 작업 ID의 파일만 삭제 (None이면 모든 임시 파일)
    - keep_outputs: outputs 폴더의 최종 결과물 유지 (기본값: True)
    - cleanup_old_files: 오래된 파일 자동 정리 (기본값: False)
    - max_age_hours: 파일 보관 시간 (시간 단위, 기본값: 24시간)
    """
    deleted_files = []
    from datetime import datetime, timedelta

    try:
        # uploads 폴더 정리
        if job_id:
            # 특정 job_id의 파일만 삭제
            for file_path in UPLOAD_DIR.glob(f"{job_id}_*"):
                try:
                    file_path.unlink()
                    deleted_files.append(str(file_path))
                    logger.info(f"임시 파일 삭제: {file_path.name}")
                except Exception as e:
                    logger.warning(f"파일 삭제 실패 ({file_path.name}): {str(e)}")

        elif cleanup_old_files:
            # 오래된 파일 자동 정리 (max_age_hours 이상 된 파일)
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            for file_path in UPLOAD_DIR.glob("*"):
                if file_path.is_file():
                    try:
                        # 파일 수정 시간 확인
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                        if file_mtime < cutoff_time:
                            file_path.unlink()
                            deleted_files.append(str(file_path))
                            logger.info(f"오래된 임시 파일 삭제 ({max_age_hours}시간 경과): {file_path.name}")
                    except Exception as e:
                        logger.warning(f"파일 삭제 실패 ({file_path.name}): {str(e)}")

        else:
            # 모든 임시 파일 삭제 (수동 호출 시)
            for file_path in UPLOAD_DIR.glob("*"):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        deleted_files.append(str(file_path))
                        logger.info(f"임시 파일 삭제: {file_path.name}")
                    except Exception as e:
                        logger.warning(f"파일 삭제 실패 ({file_path.name}): {str(e)}")

        # outputs 폴더는 keep_outputs=False일 때만 정리
        if not keep_outputs:
            if job_id:
                for file_path in OUTPUT_DIR.glob(f"{job_id}_*"):
                    try:
                        file_path.unlink()
                        deleted_files.append(str(file_path))
                        logger.info(f"출력 파일 삭제: {file_path.name}")
                    except Exception as e:
                        logger.warning(f"파일 삭제 실패 ({file_path.name}): {str(e)}")

            elif cleanup_old_files:
                # 오래된 출력 파일도 정리 (선택적)
                cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

                for file_path in OUTPUT_DIR.glob("*.html"):
                    try:
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                        if file_mtime < cutoff_time:
                            file_path.unlink()
                            deleted_files.append(str(file_path))
                            logger.info(f"오래된 출력 파일 삭제 ({max_age_hours}시간 경과): {file_path.name}")
                    except Exception as e:
                        logger.warning(f"파일 삭제 실패 ({file_path.name}): {str(e)}")

            else:
                for file_path in OUTPUT_DIR.glob("*"):
                    if file_path.is_file():
                        try:
                            file_path.unlink()
                            deleted_files.append(str(file_path))
                            logger.info(f"출력 파일 삭제: {file_path.name}")
                        except Exception as e:
                            logger.warning(f"파일 삭제 실패 ({file_path.name}): {str(e)}")

        if deleted_files:
            logger.info(f"총 {len(deleted_files)}개 파일 삭제 완료")

        return deleted_files

    except Exception as e:
        logger.error(f"파일 정리 중 오류: {str(e)}", exc_info=True)
        return deleted_files


@app.get("/")
async def root():
    """API 상태 확인"""
    return {
        "status": "running",
        "service": "StudySnap API",
        "version": "1.0.0",
        "message": "PDF를 모바일 최적화 HTML로 변환합니다"
    }


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트 (Railway 배포용)"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "service": "StudySnap Backend"
    }


# ============================================
# 라이선스 관리 API (15일 체험판)
# ============================================

@app.post("/api/license/create-trial")
async def create_trial_license(
    church_id: str = Form(...),
    church_name: str = Form(""),
    days: Optional[int] = Form(None)
):
    """
    체험판 라이선스 생성 (기간 직접 지정 가능)

    Args:
        church_id: 교회 고유 ID
        church_name: 교회 이름
        days: 사용 기간 (일) - 미지정 시 환경변수 TRIAL_DAYS 사용 (기본 15일)
    """
    try:
        manager = get_license_manager()
        license_info = manager.create_trial_license(church_id, church_name, days=days)

        return JSONResponse({
            "success": True,
            "message": f"{license_info['days']}일 체험판 라이선스가 생성되었습니다.",
            "license": {
                "license_key": license_info["license_key"],
                "church_name": license_info["church_name"],
                "expire_date": license_info["expire_date"],
                "daily_limit": license_info["daily_limit"],
                "max_bulletins": license_info["max_bulletins"]
            }
        })
    except Exception as e:
        logger.error(f"라이선스 생성 실패: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/api/license/status/{license_key}")
async def get_license_status(license_key: str):
    """라이선스 상태 조회"""
    try:
        manager = get_license_manager()
        status = manager.get_license_status(license_key)

        return JSONResponse({
            "success": True,
            **status
        })
    except Exception as e:
        logger.error(f"라이선스 상태 조회 실패: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.post("/api/license/validate")
async def validate_license(license_key: str = Form(...)):
    """라이선스 유효성 검증"""
    try:
        manager = get_license_manager()
        validation = manager.validate_license(license_key)

        return JSONResponse({
            "success": True,
            **validation
        })
    except Exception as e:
        logger.error(f"라이선스 검증 실패: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.post("/api/license/fgfc-trial")
async def create_fgfc_trial():
    """여의도순복음교회 전용 15일 체험판 라이선스 생성"""
    try:
        license_info = create_fgfc_trial_license()

        return JSONResponse({
            "success": True,
            "message": "여의도순복음교회 체험판 라이선스",
            "is_new": license_info.get("is_new", False),
            "license": {
                "license_key": license_info["license_key"],
                "church_name": license_info["church_name"],
                "expire_date": license_info["expire_date"],
                "remaining_days": license_info.get("remaining_days", license_info["days"]),
                "daily_limit": license_info["daily_limit"],
                "max_bulletins": license_info["max_bulletins"]
            }
        })
    except Exception as e:
        logger.error(f"FGFC 라이선스 생성 실패: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


# ========== 캐시 관리 API ==========

@app.post("/api/cache/clear")
async def clear_all_cache():
    """
    모든 캐시 및 임시 파일 삭제
    - 업로드된 PDF 파일
    - OCR 캐시
    - 세션 데이터
    """
    import shutil
    import glob

    deleted_files = []
    errors = []

    try:
        # 1. 업로드 폴더 정리
        upload_patterns = [
            str(UPLOAD_DIR / "*.pdf"),
            str(UPLOAD_DIR / "*.jpg"),
            str(UPLOAD_DIR / "*.png"),
        ]
        for pattern in upload_patterns:
            for file_path in glob.glob(pattern):
                try:
                    os.remove(file_path)
                    deleted_files.append(file_path)
                except Exception as e:
                    errors.append(f"{file_path}: {str(e)}")

        # 2. 임시 폴더 정리
        temp_patterns = [
            str(BASE_DIR / "temp" / "*"),
            str(BASE_DIR / "tmp" / "*"),
        ]
        for pattern in temp_patterns:
            for file_path in glob.glob(pattern):
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    deleted_files.append(file_path)
                except Exception as e:
                    errors.append(f"{file_path}: {str(e)}")

        # 3. VisionOCR 캐시 초기화 (메모리)
        global vision_ocr_cache
        vision_ocr_cache = {}

        logger.info(f"캐시 삭제 완료: {len(deleted_files)}개 파일")

        return JSONResponse({
            "success": True,
            "message": f"캐시가 완전히 삭제되었습니다. ({len(deleted_files)}개 파일)",
            "deleted_count": len(deleted_files),
            "errors": errors if errors else None
        })

    except Exception as e:
        logger.error(f"캐시 삭제 실패: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.post("/api/cache/clear-church/{church_name}")
async def clear_church_cache(church_name: str):
    """특정 교회의 캐시만 삭제"""
    import glob

    deleted_files = []

    try:
        # 교회 폴더의 임시 파일만 삭제 (HTML 결과물은 유지)
        church_folder = OUTPUT_DIR / "Church" / church_name

        if church_folder.exists():
            # 임시 파일 패턴만 삭제
            temp_patterns = [
                str(church_folder / "*.tmp"),
                str(church_folder / "*.bak"),
                str(church_folder / "*_temp.*"),
            ]
            for pattern in temp_patterns:
                for file_path in glob.glob(pattern):
                    os.remove(file_path)
                    deleted_files.append(file_path)

        logger.info(f"{church_name} 캐시 삭제: {len(deleted_files)}개")

        return JSONResponse({
            "success": True,
            "message": f"{church_name} 캐시가 삭제되었습니다.",
            "deleted_count": len(deleted_files)
        })

    except Exception as e:
        logger.error(f"교회 캐시 삭제 실패: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


# VisionOCR 캐시 (메모리)
vision_ocr_cache = {}


@app.get("/api/license/list")
async def list_all_licenses():
    """모든 라이선스 목록 조회 (관리자용)"""
    try:
        manager = get_license_manager()
        licenses = manager.get_all_licenses()

        return JSONResponse({
            "success": True,
            "count": len(licenses),
            "licenses": licenses
        })
    except Exception as e:
        logger.error(f"라이선스 목록 조회 실패: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.post("/api/license/extend")
async def extend_license(
    license_key: str = Form(...),
    days: int = Form(...)
):
    """라이선스 연장"""
    try:
        manager = get_license_manager()
        success = manager.extend_license(license_key, days)

        if success:
            status = manager.get_license_status(license_key)
            return JSONResponse({
                "success": True,
                "message": f"라이선스가 {days}일 연장되었습니다.",
                "new_expire_date": status.get("expire_date"),
                "remaining_days": status.get("remaining_days")
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "라이선스를 찾을 수 없습니다."
            }, status_code=404)
    except Exception as e:
        logger.error(f"라이선스 연장 실패: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


def check_license_and_record_usage(license_key: str, action: str = "convert") -> dict:
    """
    라이선스 검증 및 사용량 기록 헬퍼 함수

    Returns:
        {"valid": bool, "message": str, "remaining": int}
    """
    # 개발 모드: 항상 통과
    return {"valid": True, "message": "개발 모드 - 무제한", "remaining": 9999}

    # if not license_key:
    #     # 라이선스 키 없이 요청 시 (개발 모드 또는 데모)
    #     return {"valid": True, "message": "데모 모드", "remaining": -1}
    #
    # manager = get_license_manager()
    #
    # # 라이선스 검증
    # validation = manager.validate_license(license_key)
    # if not validation["valid"]:
    #     return {
    #         "valid": False,
    #         "message": validation["message"],
    #         "remaining": 0
    #     }
    #
    # # 사용량 기록
    # usage_result = manager.record_usage(license_key, action)
    #
    # return {
    #     "valid": usage_result["success"],
    #     "message": usage_result["message"],
    #     "remaining": usage_result["daily_remaining"]
    # }


# ============================================
# 한글 파일명 지원 outputs 라우터
# ============================================
@app.get("/outputs/{file_path:path}")
async def serve_outputs_file(file_path: str, request: Request):
    """
    outputs 폴더의 파일을 한글 파일명 지원하여 서빙
    StaticFiles의 한글 인코딩 문제를 우회

    예: /outputs/민주-류삼영/류삼영_with_images.html
    """
    import mimetypes

    try:
        # URL 디코딩 (미들웨어에서 이미 처리되었을 수 있음)
        decoded_path = unquote(file_path, encoding='utf-8')

        # 경로 보안 검증
        full_path = OUTPUT_DIR / decoded_path

        try:
            resolved_path = full_path.resolve()
            base_resolved = OUTPUT_DIR.resolve()

            # 경로 순회 공격 방지
            if not str(resolved_path).startswith(str(base_resolved)):
                raise HTTPException(status_code=403, detail="접근이 허용되지 않은 경로입니다")
        except Exception:
            raise HTTPException(status_code=400, detail="잘못된 경로입니다")

        # 파일 존재 확인
        if not full_path.exists():
            # CP949 인코딩으로 재시도
            try:
                cp949_path = decoded_path.encode('utf-8').decode('cp949', errors='ignore')
                alt_path = OUTPUT_DIR / cp949_path
                if alt_path.exists():
                    full_path = alt_path
                else:
                    raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {decoded_path}")
            except:
                raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {decoded_path}")

        if full_path.is_dir():
            raise HTTPException(status_code=400, detail="디렉토리는 직접 접근할 수 없습니다")

        # MIME 타입 결정
        mime_type, _ = mimetypes.guess_type(str(full_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        # 파일 반환
        return FileResponse(
            path=str(full_path),
            media_type=mime_type,
            filename=full_path.name,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f"inline; filename*=UTF-8''{quote(full_path.name)}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 서빙 실패: {file_path} - {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 서빙 실패: {str(e)}")


@app.post("/api/convert")
async def convert_pdf(
    file: UploadFile = File(...),
    content_type: str = Form(default="general"),
    title: Optional[str] = Form(default=None),
    exclude_pages: Optional[str] = Form(default=None)
):
    """
    PDF 파일을 모바일 최적화 HTML로 변환

    - file: PDF 파일
    - content_type: 콘텐츠 유형 (lecture, election, church, general)
    - title: 결과물 제목 (선택사항)
    - exclude_pages: 제외할 페이지 번호 (쉼표로 구분, 예: "2,3,5")
    """

    # 파일 검증
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")

    # 파일 크기 제한 (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="파일 크기는 50MB를 초과할 수 없습니다")

    # 고유 ID 생성
    job_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 파일 저장
    original_filename = file.filename
    safe_filename = f"{job_id}_{timestamp}.pdf"
    upload_path = UPLOAD_DIR / safe_filename

    try:
        with open(upload_path, "wb") as f:
            f.write(content)

        # PDF 변환 처리
        logger.info(f"[{job_id}] PDF 변환 시작: {original_filename} (content_type: {content_type})")

        # 제외할 페이지 처리
        exclude_pages_list = []
        if exclude_pages:
            try:
                exclude_pages_list = [int(p.strip()) for p in exclude_pages.split(',') if p.strip()]
                logger.info(f"[{job_id}] 제외할 페이지: {exclude_pages_list}")
            except ValueError:
                logger.warning(f"[{job_id}] 잘못된 exclude_pages 형식: {exclude_pages}")

        # 1. PDF에서 텍스트와 이미지 추출
        try:
            extracted_data = pdf_converter.extract_from_pdf(
                str(upload_path),
                content_type=content_type,
                exclude_pages=exclude_pages_list
            )
        except Exception as e:
            logger.error(f"[{job_id}] PDF 추출 실패: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"PDF 파일 처리 중 오류가 발생했습니다: {str(e)}")

        if not extracted_data:
            logger.error(f"[{job_id}] PDF 추출 결과가 없음")
            raise HTTPException(status_code=500, detail="PDF 처리 중 오류가 발생했습니다")

        logger.info(f"[{job_id}] PDF 추출 완료: {extracted_data.get('page_count', 0)}페이지")

        # 2. HTML 생성
        result_title = title or Path(original_filename).stem
        output_filename = f"{job_id}_{timestamp}.html"
        output_path = OUTPUT_DIR / output_filename

        try:
            html_content = html_generator.generate_html(
                extracted_data=extracted_data,
                title=result_title,
                content_type=content_type,
                job_id=job_id
            )
        except Exception as e:
            logger.error(f"[{job_id}] HTML 생성 실패: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"HTML 생성 중 오류가 발생했습니다: {str(e)}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"[{job_id}] 변환 완료: {output_filename}")

        # 3. 자동 검증 시스템 실행
        verification_result = None
        try:
            logger.info(f"[{job_id}] 자동 검증 시작")
            verification_result = verification_system.verify_conversion(
                original_pdf_path=str(upload_path),
                generated_html_path=str(output_path),
                extracted_data=extracted_data
            )

            logger.info(f"[{job_id}] 검증 완료: {verification_result['status']} "
                       f"(오류: {verification_result['statistics']['total_errors']}, "
                       f"경고: {verification_result['statistics']['total_warnings']})")

            # 자동 수정 적용
            if verification_result.get("corrections"):
                logger.info(f"[{job_id}] 자동 수정 적용 중 ({len(verification_result['corrections'])}개)")
                correction_applied = verification_system.apply_corrections(
                    str(output_path),
                    verification_result["corrections"]
                )
                if correction_applied:
                    logger.info(f"[{job_id}] 자동 수정 완료")
                    verification_result["auto_corrected"] = True

        except Exception as e:
            logger.error(f"[{job_id}] 검증 중 오류 (계속 진행): {str(e)}", exc_info=True)
            verification_result = {
                "status": "error",
                "message": f"검증 실패: {str(e)}"
            }

        # 4. 임시 파일 정리 (uploads 폴더의 원본 PDF)
        try:
            cleanup_temp_files(job_id=job_id, keep_outputs=True)
            logger.info(f"[{job_id}] 임시 파일 정리 완료")
        except Exception as e:
            logger.error(f"[{job_id}] 임시 파일 정리 실패 (계속 진행): {str(e)}")

        # 학습 시스템에 변환 기록
        try:
            learning_system.log_conversion(job_id, {
                "filename": original_filename,
                "content_type": content_type,
                "page_count": extracted_data.get("page_count", 0),
                "is_image_based": extracted_data.get("is_image_based", False),
                "ocr_used": extracted_data.get("ocr_used", False),
                "processing_time": 0,  # TODO: 실제 처리 시간 추가
                "structured_data": extracted_data.get("structured_data", {})
            })
        except Exception as e:
            logger.error(f"학습 데이터 기록 실패: {str(e)}")

        # 결과 URL 생성
        result_url = f"/outputs/{output_filename}"

        # 응답 데이터 구성
        response_data = {
            "success": True,
            "job_id": job_id,
            "message": "변환이 완료되었습니다",
            "result": {
                "url": result_url,
                "filename": output_filename,
                "original_filename": original_filename,
                "content_type": content_type,
                "title": result_title,
                "page_count": extracted_data.get("page_count", 0),
                "created_at": datetime.now().isoformat()
            }
        }

        # 검증 결과 추가
        if verification_result:
            response_data["verification"] = {
                "status": verification_result.get("status", "unknown"),
                "accuracy": verification_result.get("statistics", {}).get("ocr_accuracy", 0),
                "similarity": verification_result.get("statistics", {}).get("similarity_score", 0),
                "errors": verification_result.get("statistics", {}).get("total_errors", 0),
                "warnings": verification_result.get("statistics", {}).get("total_warnings", 0),
                "auto_corrected": verification_result.get("auto_corrected", False),
                "recommendations": verification_result.get("recommendations", [])
            }

        return JSONResponse(response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{job_id}] 예상치 못한 오류: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"변환 중 오류가 발생했습니다: {str(e)}")
    finally:
        # 업로드 파일 정리 (선택적)
        # if upload_path.exists():
        #     upload_path.unlink()
        pass


@app.get("/api/result/{job_id}")
async def get_result(job_id: str):
    """변환 결과 조회"""

    # outputs 디렉토리에서 job_id로 시작하는 파일 찾기
    for file_path in OUTPUT_DIR.glob(f"{job_id}_*.html"):
        return FileResponse(
            path=str(file_path),
            media_type="text/html",
            filename=file_path.name
        )

    raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다")


@app.delete("/api/result/{job_id}")
async def delete_result(job_id: str):
    """변환 결과 삭제"""

    deleted = False

    # outputs 디렉토리에서 파일 삭제
    for file_path in OUTPUT_DIR.glob(f"{job_id}_*"):
        file_path.unlink()
        deleted = True

    # uploads 디렉토리에서 파일 삭제
    for file_path in UPLOAD_DIR.glob(f"{job_id}_*"):
        file_path.unlink()
        deleted = True

    if deleted:
        return {"success": True, "message": "삭제되었습니다"}

    raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")


@app.get("/api/content-types")
async def get_content_types():
    """지원하는 콘텐츠 유형 목록"""
    return {
        "content_types": [
            {
                "id": "lecture",
                "name": "강의자료",
                "description": "수업 강의노트, 프레젠테이션 자료",
                "icon": "📚"
            },
            {
                "id": "election",
                "name": "선거 홍보물",
                "description": "후보자 소개, 공약, 선거 포스터",
                "icon": "🗳️"
            },
            {
                "id": "church",
                "name": "교회 주보",
                "description": "주일 예배 순서, 교회 소식",
                "icon": "⛪"
            },
            {
                "id": "general",
                "name": "일반 문서",
                "description": "기타 PDF 문서",
                "icon": "📄"
            }
        ]
    }


# ============================================
# 학습 시스템 API 엔드포인트
# ============================================

@app.post("/api/feedback")
async def submit_feedback(
    job_id: str = Form(...),
    rating: int = Form(...),
    accuracy: Optional[int] = Form(None),
    completeness: Optional[int] = Form(None),
    issues: Optional[str] = Form(None),
    comment: Optional[str] = Form(None)
):
    """
    변환 결과에 대한 피드백 제출

    Parameters:
    - job_id: 변환 작업 ID
    - rating: 전체 만족도 (1-5)
    - accuracy: OCR 정확도 (1-5)
    - completeness: 완성도 (1-5)
    - issues: 발견된 문제들 (콤마로 구분)
    - comment: 상세 코멘트
    """
    try:
        # issues 문자열을 리스트로 변환
        issues_list = [i.strip() for i in issues.split(",")] if issues else []

        feedback_data = {
            "rating": rating,
            "accuracy": accuracy or rating,
            "completeness": completeness or rating,
            "issues": issues_list,
            "comment": comment or "",
            "corrections": {}
        }

        learning_system.log_feedback(job_id, feedback_data)

        return JSONResponse({
            "success": True,
            "message": "피드백이 저장되었습니다. 감사합니다!",
            "job_id": job_id
        })

    except Exception as e:
        logger.error(f"피드백 저장 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"피드백 저장 실패: {str(e)}")


@app.get("/api/statistics")
async def get_statistics():
    """전체 변환 통계 및 학습 데이터 조회"""
    try:
        stats = learning_system.get_statistics()
        suggestions = learning_system.get_improvement_suggestions()

        return JSONResponse({
            "success": True,
            "statistics": stats,
            "improvement_suggestions": suggestions,
            "generated_at": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"통계 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")


@app.get("/api/learning/insights")
async def get_learning_insights():
    """학습 시스템 인사이트 조회 - 개선 제안 및 패턴 분석"""
    try:
        stats = learning_system.get_statistics()
        suggestions = learning_system.get_improvement_suggestions()

        insights = {
            "summary": {
                "total_conversions": stats.get("total_conversions", 0),
                "feedback_rate": f"{(stats.get('feedback_count', 0) / max(stats.get('total_conversions', 1), 1) * 100):.1f}%",
                "average_rating": f"{stats.get('average_rating', 0):.2f}/5.0",
                "success_rate": f"{stats.get('success_rate', 0):.1f}%"
            },
            "top_content_types": dict(stats.get("content_types", {})),
            "common_issues": dict(stats.get("common_issues", {})),
            "improvement_suggestions": suggestions,
            "system_health": "good" if stats.get("average_rating", 0) >= 4 else "needs_improvement"
        }

        return JSONResponse({
            "success": True,
            "insights": insights,
            "generated_at": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"인사이트 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"인사이트 조회 실패: {str(e)}")


@app.post("/api/learning/export")
async def export_learning_data():
    """학습 데이터 내보내기 (JSON 형식)"""
    try:
        export_filename = f"learning_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        export_path = OUTPUT_DIR / export_filename

        success = learning_system.export_training_data(str(export_path))

        if success:
            return JSONResponse({
                "success": True,
                "message": "학습 데이터가 성공적으로 내보내졌습니다",
                "download_url": f"/outputs/{export_filename}",
                "filename": export_filename
            })
        else:
            raise HTTPException(status_code=500, detail="학습 데이터 내보내기 실패")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"학습 데이터 내보내기 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"내보내기 실패: {str(e)}")


# ============================================
# 능동형 AI 학습 API (v2.0)
# ============================================

# 능동형 학습 엔진 초기화
try:
    from learning_data.active_learning import get_learning_engine
    active_learning_engine = get_learning_engine()
    logger.info("능동형 AI 학습 엔진 로드됨")
except ImportError as e:
    active_learning_engine = None
    logger.warning(f"능동형 학습 엔진 로드 실패: {e}")


@app.get("/api/learning/stats")
async def get_active_learning_stats():
    """능동형 AI 학습 통계 조회"""
    try:
        if active_learning_engine is None:
            return JSONResponse({"error": "학습 엔진이 초기화되지 않았습니다"}, status_code=500)

        stats = active_learning_engine.get_learning_stats()
        return JSONResponse(stats)
    except Exception as e:
        logger.error(f"학습 통계 조회 실패: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/learning/feedback")
async def submit_learning_feedback(request: Request):
    """사용자 피드백 수집 및 학습"""
    try:
        if active_learning_engine is None:
            return JSONResponse({"error": "학습 엔진이 초기화되지 않았습니다"}, status_code=500)

        data = await request.json()

        feedback = active_learning_engine.add_feedback(
            job_id=data.get("job_id", "unknown"),
            rating=data.get("rating", 3),
            feedback_type=data.get("feedback_type", "rating"),
            category=data.get("category", "overall"),
            original_value=data.get("original_value", ""),
            corrected_value=data.get("corrected_value", ""),
            comment=data.get("comment", "")
        )

        logger.info(f"피드백 수신: job={data.get('job_id')}, rating={data.get('rating')}")

        return JSONResponse({
            "success": True,
            "message": "피드백이 저장되고 학습에 반영되었습니다",
            "feedback_id": feedback.job_id
        })
    except Exception as e:
        logger.error(f"피드백 저장 실패: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/learning/html-diff")
async def save_html_diff(request: Request):
    """HTML 변경 비교 저장 및 패턴 학습"""
    try:
        if active_learning_engine is None:
            return JSONResponse({"error": "학습 엔진이 초기화되지 않았습니다"}, status_code=500)

        data = await request.json()

        diff = active_learning_engine.save_html_diff(
            job_id=data.get("job_id", "unknown"),
            original_html=data.get("original_html", ""),
            modified_html=data.get("modified_html", "")
        )

        logger.info(f"HTML 변경 저장: job={data.get('job_id')}, changes={len(diff.changes)}")

        return JSONResponse({
            "success": True,
            "message": f"{len(diff.changes)}개 변경점 분석, {len(diff.extracted_patterns)}개 패턴 추출됨",
            "changes_count": len(diff.changes),
            "patterns_count": len(diff.extracted_patterns)
        })
    except Exception as e:
        logger.error(f"HTML diff 저장 실패: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/learning/report")
async def get_learning_report():
    """AI 학습 개선 리포트"""
    try:
        if active_learning_engine is None:
            return JSONResponse({"error": "학습 엔진이 초기화되지 않았습니다"}, status_code=500)

        report = active_learning_engine.get_improvement_report()
        stats = active_learning_engine.get_learning_stats()

        return JSONResponse({
            "success": True,
            "report": report,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"리포트 생성 실패: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/learning/status")
async def get_learning_status():
    """
    통합 학습 시스템 상태 확인 API

    - 변환 기록 수
    - 피드백 수
    - 학습된 규칙 수
    - 정당별/후보유형별 통계
    """
    try:
        result = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "engines": {
                "active_learning": active_learning_engine is not None,
                "learning_system": learning_system is not None
            },
            "stats": {}
        }

        # 능동형 학습 엔진 통계
        if active_learning_engine is not None:
            stats = active_learning_engine.get_learning_stats()
            result["stats"]["active_learning"] = {
                "total_feedbacks": stats.get("total_feedbacks", 0),
                "corrections_count": stats.get("corrections_count", 0),
                "rules_generated": stats.get("rules_generated", 0),
                "rules_improved": stats.get("rules_improved", 0),
                "active_rules": stats.get("active_rules", 0),
                "high_confidence_rules": stats.get("high_confidence_rules", 0),
                "conversion_count": stats.get("conversion_count", 0),
                "party_stats": stats.get("party_stats", {}),
                "candidate_type_stats": stats.get("candidate_type_stats", {})
            }

        # 기존 학습 시스템 통계
        if learning_system is not None:
            try:
                ls_stats = learning_system.get_stats()
                result["stats"]["learning_system"] = ls_stats
            except Exception:
                result["stats"]["learning_system"] = {"status": "error"}

        # 학습 데이터 파일 확인
        learning_data_dir = BASE_DIR / "learning_data"
        if learning_data_dir.exists():
            files_info = {}
            for file in learning_data_dir.glob("*.json*"):
                try:
                    files_info[file.name] = {
                        "size_kb": round(file.stat().st_size / 1024, 2),
                        "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                    }
                except Exception:
                    pass
            result["learning_files"] = files_info

        return JSONResponse(result)

    except Exception as e:
        logger.error(f"학습 상태 조회 실패: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ============================================
# 범용 변환 시스템 API
# ============================================

@app.get("/api/formats/supported")
async def get_supported_formats():
    """지원하는 모든 파일 형식 조회"""
    try:
        formats = universal_parser.get_supported_formats()
        templates = template_engine.list_templates()

        return JSONResponse({
            "success": True,
            "supported_formats": formats,
            "output_templates": templates,
            "total_formats": sum(len(v) for v in formats.values()),
            "total_templates": len(templates)
        })

    except Exception as e:
        logger.error(f"형식 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/convert/universal")
async def universal_convert(
    file: UploadFile = File(...),
    content_type: str = Form("general"),
    output_format: str = Form("mobile_html"),
    title: Optional[str] = Form(None),
    language: str = Form("ko"),
    custom_options: Optional[str] = Form(None)
):
    """
    범용 문서 변환 API - 모든 파일 형식 지원

    Parameters:
    - file: 변환할 파일 (PDF, Word, PowerPoint, Excel, 이미지 등)
    - content_type: 콘텐츠 타입 (election, lecture, church, general)
    - output_format: 출력 템플릿 (mobile_html, json, markdown, print_html 등)
    - title: 문서 제목
    - language: 언어 (ko, en, ja, zh)
    - custom_options: 커스텀 옵션 (JSON 문자열)
    """
    job_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        # 파일 저장
        content = await file.read()
        original_filename = file.filename
        file_extension = Path(original_filename).suffix
        safe_filename = f"{job_id}_{timestamp}{file_extension}"
        upload_path = UPLOAD_DIR / safe_filename

        with open(upload_path, "wb") as f:
            f.write(content)

        logger.info(f"[{job_id}] 범용 변환 시작: {original_filename} (출력: {output_format})")

        # 범용 파서로 문서 파싱
        parse_options = {
            'content_type': content_type,
            'output_format': output_format,
            'language': language
        }

        if custom_options:
            try:
                parse_options.update(json.loads(custom_options))
            except:
                pass

        extracted_data = universal_parser.parse_document(str(upload_path), parse_options)

        if 'error' in extracted_data:
            raise HTTPException(status_code=400, detail=extracted_data['error'])

        logger.info(f"[{job_id}] 파싱 완료: {extracted_data.get('parser_used', 'Unknown')} 사용")

        # 출력 생성
        result_title = title or Path(original_filename).stem
        output_filename = f"{job_id}_{timestamp}.html"
        output_path = OUTPUT_DIR / output_filename

        # 템플릿으로 렌더링
        template_data = {
            'title': result_title,
            'language': language,
            'content': extracted_data.get('pages', [{}])[0].get('text', ''),
            'pages': extracted_data.get('pages', []),
            'data': extracted_data,
            'metadata': extracted_data.get('metadata', {})
        }

        output_content = template_engine.render(output_format, template_data)

        if output_content:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output_content)
        else:
            # 템플릿이 없으면 기본 HTML 생성기 사용
            html_content = html_generator.generate_html(
                extracted_data=extracted_data,
                title=result_title,
                content_type=content_type,
                job_id=job_id
            )
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

        # 학습 데이터 기록
        try:
            learning_system.log_conversion(job_id, {
                "filename": original_filename,
                "content_type": content_type,
                "page_count": extracted_data.get("page_count", 0),
                "is_image_based": extracted_data.get("is_image_based", False),
                "ocr_used": extracted_data.get("ocr_used", False),
                "processing_time": 0,
                "structured_data": extracted_data.get("structured_data", {}),
                "format": extracted_data.get("detected_format", "unknown"),
                "output_format": output_format
            })
        except Exception as e:
            logger.error(f"학습 데이터 기록 실패: {str(e)}")

        logger.info(f"[{job_id}] 범용 변환 완료: {output_filename}")

        return JSONResponse({
            "success": True,
            "job_id": job_id,
            "message": "변환이 완료되었습니다",
            "result": {
                "url": f"/outputs/{output_filename}",
                "filename": output_filename,
                "original_filename": original_filename,
                "detected_format": extracted_data.get("detected_format", "unknown"),
                "parser_used": extracted_data.get("parser_used", "Unknown"),
                "content_type": content_type,
                "output_format": output_format,
                "title": result_title,
                "page_count": extracted_data.get("page_count", 0),
                "created_at": datetime.now().isoformat()
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{job_id}] 범용 변환 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"변환 실패: {str(e)}")


# ============================================
# 템플릿 관리 API
# ============================================

@app.get("/api/templates")
async def list_templates():
    """사용 가능한 모든 출력 템플릿 목록"""
    try:
        templates = template_engine.list_templates()
        return JSONResponse({
            "success": True,
            "templates": templates,
            "count": len(templates)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates/custom")
async def create_custom_template(
    template_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(...),
    template_content: str = Form(...)
):
    """사용자 정의 템플릿 생성"""
    try:
        success = template_engine.create_custom_template(
            template_id, name, description, template_content
        )

        if success:
            return JSONResponse({
                "success": True,
                "message": "커스텀 템플릿이 생성되었습니다",
                "template_id": template_id
            })
        else:
            raise HTTPException(status_code=400, detail="템플릿 생성 실패")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"템플릿 생성 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 다국어 지원 API
# ============================================

@app.get("/api/languages")
async def get_supported_languages():
    """지원하는 모든 언어 목록"""
    try:
        languages = localization_manager.get_supported_languages()
        return JSONResponse({
            "success": True,
            "languages": languages,
            "count": len(languages)
        })
    except Exception as e:
        logger.error(f"언어 목록 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/languages/detect")
async def detect_language(text: str = Form(...)):
    """텍스트에서 언어 자동 감지"""
    try:
        detected = localization_manager.detect_language(text)
        return JSONResponse({
            "success": True,
            "detected_language": detected
        })
    except Exception as e:
        logger.error(f"언어 감지 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 고급 커스터마이징 API
# ============================================

@app.post("/api/convert/custom")
async def custom_convert(
    file: UploadFile = File(...),
    content_type: str = Form("general"),
    output_format: str = Form("mobile_html"),
    title: Optional[str] = Form(None),
    language: str = Form("ko"),
    color_scheme: Optional[str] = Form(None),
    font_family: Optional[str] = Form(None),
    include_images: bool = Form(True),
    max_image_width: int = Form(800),
    custom_css: Optional[str] = Form(None),
    custom_header: Optional[str] = Form(None),
    custom_footer: Optional[str] = Form(None)
):
    """
    고급 커스터마이징 변환 API

    Parameters:
    - file: 변환할 파일
    - content_type: 콘텐츠 타입
    - output_format: 출력 형식
    - title: 문서 제목
    - language: 언어 코드
    - color_scheme: 색상 테마 (예: "blue", "green", "#FF5733")
    - font_family: 폰트 (예: "Malgun Gothic", "Arial")
    - include_images: 이미지 포함 여부
    - max_image_width: 최대 이미지 너비
    - custom_css: 커스텀 CSS 스타일
    - custom_header: 커스텀 헤더 HTML
    - custom_footer: 커스텀 푸터 HTML
    """
    job_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        # 파일 저장
        content = await file.read()
        original_filename = file.filename
        file_extension = Path(original_filename).suffix
        safe_filename = f"{job_id}_{timestamp}{file_extension}"
        upload_path = UPLOAD_DIR / safe_filename

        with open(upload_path, "wb") as f:
            f.write(content)

        logger.info(f"[{job_id}] 고급 커스터마이징 변환 시작: {original_filename}")

        # 커스텀 옵션 구성
        custom_options = {
            'content_type': content_type,
            'output_format': output_format,
            'language': language,
            'color_scheme': color_scheme,
            'font_family': font_family,
            'include_images': include_images,
            'max_image_width': max_image_width,
        }

        # 범용 파서로 문서 파싱
        extracted_data = universal_parser.parse_document(str(upload_path), custom_options)

        if 'error' in extracted_data:
            raise HTTPException(status_code=400, detail=extracted_data['error'])

        # 출력 생성
        result_title = title or Path(original_filename).stem
        output_filename = f"{job_id}_{timestamp}.html"
        output_path = OUTPUT_DIR / output_filename

        # 템플릿 데이터 준비
        template_data = {
            'title': result_title,
            'language': language,
            'content': extracted_data.get('pages', []),
            'data': extracted_data
        }

        # 커스텀 스타일 적용
        custom_styles = []
        if custom_css:
            custom_styles.append(custom_css)

        if color_scheme:
            custom_styles.append(f"""
                :root {{
                    --primary-color: {color_scheme};
                }}
            """)

        if font_family:
            custom_styles.append(f"""
                body {{
                    font-family: {font_family}, sans-serif;
                }}
            """)

        if custom_styles:
            template_data['custom_css'] = '\n'.join(custom_styles)

        if custom_header:
            template_data['custom_header'] = custom_header

        if custom_footer:
            template_data['custom_footer'] = custom_footer

        # 템플릿 렌더링
        rendered_output = template_engine.render(output_format, template_data)

        if not rendered_output:
            raise HTTPException(status_code=400, detail=f"템플릿 렌더링 실패: {output_format}")

        # 파일 저장
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered_output)

        logger.info(f"[{job_id}] 고급 커스터마이징 변환 완료: {output_filename}")

        # 학습 시스템에 기록
        learning_system.log_conversion(job_id, {
            "filename": original_filename,
            "content_type": content_type,
            "page_count": extracted_data.get("page_count", 0),
            "is_image_based": extracted_data.get("is_image_based", False),
            "ocr_used": extracted_data.get("ocr_used", False),
            "structured_data": extracted_data.get("structured_data", {}),
        })

        return JSONResponse({
            "success": True,
            "job_id": job_id,
            "message": "고급 커스터마이징 변환이 완료되었습니다",
            "result": {
                "url": f"/outputs/{output_filename}",
                "filename": output_filename,
                "original_filename": original_filename,
                "title": result_title,
                "customizations": {
                    "color_scheme": color_scheme,
                    "font_family": font_family,
                    "include_images": include_images,
                    "has_custom_css": bool(custom_css),
                    "has_custom_header": bool(custom_header),
                    "has_custom_footer": bool(custom_footer)
                },
                "created_at": datetime.now().isoformat()
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{job_id}] 고급 커스터마이징 변환 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"변환 실패: {str(e)}")


# ============================================
# 파일 관리 API
# ============================================

@app.post("/api/cleanup")
async def cleanup_files(
    cleanup_uploads: bool = True,
    cleanup_outputs: bool = False,
    max_age_hours: int = 24
):
    """
    임시 파일 수동 정리 API

    Parameters:
    - cleanup_uploads: uploads 폴더 정리 (기본값: True)
    - cleanup_outputs: outputs 폴더 정리 (기본값: False)
    - max_age_hours: 삭제할 파일의 최소 보관 시간 (시간 단위, 기본값: 24시간)
    """
    try:
        deleted_count = 0

        if cleanup_uploads:
            deleted_files = cleanup_temp_files(
                job_id=None,
                keep_outputs=True,
                cleanup_old_files=True,
                max_age_hours=max_age_hours
            )
            deleted_count += len(deleted_files)

        if cleanup_outputs:
            deleted_files = cleanup_temp_files(
                job_id=None,
                keep_outputs=False,
                cleanup_old_files=True,
                max_age_hours=max_age_hours
            )
            deleted_count += len(deleted_files)

        return JSONResponse({
            "success": True,
            "message": f"{deleted_count}개의 오래된 파일을 삭제했습니다",
            "deleted_count": deleted_count,
            "max_age_hours": max_age_hours
        })

    except Exception as e:
        logger.error(f"파일 정리 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/cleanup/all")
async def cleanup_all_files(confirm: bool = False):
    """
    모든 임시 파일 강제 삭제 API (주의: outputs 폴더 포함)

    Parameters:
    - confirm: 삭제 확인 (True여야 실행됨)
    """
    if not confirm:
        return JSONResponse({
            "success": False,
            "message": "삭제를 확인하려면 confirm=true를 전달하세요",
            "warning": "이 작업은 모든 uploads 및 outputs 파일을 삭제합니다"
        }, status_code=400)

    try:
        # uploads 폴더 전체 삭제
        uploads_deleted = cleanup_temp_files(job_id=None, keep_outputs=True, cleanup_old_files=False)

        # outputs 폴더 전체 삭제
        outputs_deleted = cleanup_temp_files(job_id=None, keep_outputs=False, cleanup_old_files=False)

        total_deleted = len(uploads_deleted) + len(outputs_deleted)

        return JSONResponse({
            "success": True,
            "message": f"총 {total_deleted}개 파일 삭제 완료",
            "uploads_deleted": len(uploads_deleted),
            "outputs_deleted": len(outputs_deleted)
        })

    except Exception as e:
        logger.error(f"전체 파일 정리 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/storage/status")
async def storage_status():
    """저장소 상태 확인 API"""
    try:
        import os

        # uploads 폴더 통계
        uploads_files = list(UPLOAD_DIR.glob("*"))
        uploads_count = len([f for f in uploads_files if f.is_file()])
        uploads_size = sum(f.stat().st_size for f in uploads_files if f.is_file())

        # outputs 폴더 통계
        outputs_files = list(OUTPUT_DIR.glob("*.html"))
        outputs_count = len(outputs_files)
        outputs_size = sum(f.stat().st_size for f in outputs_files)

        return JSONResponse({
            "success": True,
            "storage": {
                "uploads": {
                    "file_count": uploads_count,
                    "total_size_bytes": uploads_size,
                    "total_size_mb": round(uploads_size / 1024 / 1024, 2)
                },
                "outputs": {
                    "file_count": outputs_count,
                    "total_size_bytes": outputs_size,
                    "total_size_mb": round(outputs_size / 1024 / 1024, 2)
                },
                "total": {
                    "file_count": uploads_count + outputs_count,
                    "total_size_bytes": uploads_size + outputs_size,
                    "total_size_mb": round((uploads_size + outputs_size) / 1024 / 1024, 2)
                }
            }
        })

    except Exception as e:
        logger.error(f"저장소 상태 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 파일 브라우저 API
# ============================================

def fix_korean_filename(name: str) -> str:
    """
    Windows에서 한글 파일명의 surrogate escape 문제 해결
    Python pathlib이 반환하는 surrogate-escaped 문자열을 정상 한글로 변환
    """
    try:
        # 이미 정상적인 문자열인 경우 그대로 반환
        name.encode('utf-8')
        return name
    except UnicodeEncodeError:
        # surrogate escape가 있는 경우
        try:
            # surrogateescape로 바이트로 변환 후 cp949로 디코드 시도
            raw_bytes = name.encode('utf-8', errors='surrogateescape')
            return raw_bytes.decode('cp949', errors='replace')
        except Exception:
            try:
                # euc-kr 시도
                raw_bytes = name.encode('utf-8', errors='surrogateescape')
                return raw_bytes.decode('euc-kr', errors='replace')
            except Exception:
                # 최후의 수단: replace 에러 핸들러 사용
                return name.encode('utf-8', errors='replace').decode('utf-8')

@app.get("/api/files/{folder:path}")
async def list_folder_files(folder: str, subpath: str = ""):
    """
    폴더별 파일 목록 반환 (파일 브라우저용)
    하위 폴더 탐색 지원

    - folder: outputs, uploads, static, templates, root 또는 outputs/하위폴더
    - subpath: 하위 경로 (쿼리 파라미터)
    """
    try:
        # 기본 폴더 매핑
        base_folders = {
            'outputs': OUTPUT_DIR,
            'uploads': UPLOAD_DIR,
            'static': STATIC_DIR,
            'templates': TEMPLATES_DIR,
            'root': BASE_DIR
        }

        # folder가 "outputs/국민-나경원" 형태인 경우 파싱
        parts = folder.split('/')
        base_folder = parts[0]
        sub_path = '/'.join(parts[1:]) if len(parts) > 1 else ""

        if base_folder not in base_folders:
            raise HTTPException(status_code=400, detail=f"허용되지 않은 폴더: {base_folder}")

        folder_path = base_folders[base_folder]

        # 하위 경로가 있으면 적용
        if sub_path:
            folder_path = folder_path / sub_path

        # 경로 순회 공격 방지
        try:
            folder_path = folder_path.resolve()
            base_path = base_folders[base_folder].resolve()
            if not str(folder_path).startswith(str(base_path)):
                raise HTTPException(status_code=403, detail="접근이 허용되지 않은 경로입니다")
        except Exception:
            raise HTTPException(status_code=400, detail="잘못된 경로입니다")

        if not folder_path.exists():
            return JSONResponse({
                "success": True,
                "files": [],
                "folders": [],
                "count": 0,
                "folder": folder,
                "current_path": sub_path,
                "total_size": 0
            })

        files = []
        folders = []
        total_size = 0

        for item_path in folder_path.iterdir():
            try:
                # 한글 파일명 인코딩 문제 해결
                fixed_name = fix_korean_filename(item_path.name)

                if item_path.is_dir():
                    # 하위 폴더
                    folder_files = list(item_path.glob('*'))
                    folders.append({
                        "name": fixed_name,
                        "type": "folder",
                        "file_count": len([f for f in folder_files if f.is_file()]),
                        "path": f"{base_folder}/{sub_path}/{fixed_name}".replace('//', '/')
                    })
                elif item_path.is_file():
                    # 파일
                    stat = item_path.stat()
                    total_size += stat.st_size

                    # URL 경로 구성
                    if sub_path:
                        url = f"/{base_folder}/{sub_path}/{fixed_name}"
                    else:
                        url = f"/{base_folder}/{fixed_name}"

                    files.append({
                        "name": fixed_name,
                        "type": "file",
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "url": url,
                        "folder_path": sub_path
                    })
            except Exception as e:
                logger.warning(f"항목 정보 조회 실패: {item_path} - {str(e)}")

        # 폴더는 이름순, 파일은 최신순 정렬
        folders.sort(key=lambda x: x["name"])
        files.sort(key=lambda x: x["modified"], reverse=True)

        import json
        return JSONResponse(
            content={
                "success": True,
                "files": files,
                "folders": folders,
                "count": len(files),
                "folder_count": len(folders),
                "folder": base_folder,
                "current_path": sub_path,
                "total_size": total_size
            },
            media_type="application/json; charset=utf-8"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"폴더 파일 목록 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 목록 조회 실패: {str(e)}")


@app.get("/api/editor/file/{filepath:path}")
async def get_editor_file(filepath: str):
    """
    편집기용 파일 내용 읽기 API

    - filepath: outputs/Church/여의도순복음교회/index.html 형태의 경로

    Returns:
    - success: 성공 여부
    - content: HTML 파일 내용
    - filename: 파일명
    """
    try:
        from urllib.parse import unquote
        # URL 디코딩
        filepath = unquote(filepath)

        # 경로 검증 - outputs로 시작해야 함
        if not filepath.startswith('outputs/'):
            raise HTTPException(status_code=400, detail="outputs 폴더 내 파일만 접근 가능합니다")

        # outputs/ 이후 경로 추출
        relative_path = filepath[8:]  # 'outputs/' 제거

        # 실제 파일 경로
        file_path = OUTPUT_DIR / relative_path

        # 경로 순회 공격 방지
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(OUTPUT_DIR.resolve())):
                raise HTTPException(status_code=403, detail="접근이 허용되지 않은 경로입니다")
        except Exception:
            raise HTTPException(status_code=400, detail="잘못된 경로입니다")

        # 파일 존재 확인
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {filepath}")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="파일이 아닙니다")

        # HTML 파일만 허용
        if not file_path.suffix.lower() in ['.html', '.htm']:
            raise HTTPException(status_code=400, detail="HTML 파일만 편집 가능합니다")

        # 파일 내용 읽기
        file_content = file_path.read_text(encoding='utf-8')

        return JSONResponse({
            "success": True,
            "content": file_content,
            "filename": file_path.name,
            "filepath": filepath
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 읽기 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 읽기 실패: {str(e)}")



@app.get("/api/serve/{file_path:path}")
async def serve_file(file_path: str):
    """
    한글 경로를 지원하는 파일 서빙 API
    StaticFiles의 한글 인코딩 문제를 우회

    사용법: /api/serve/outputs/민주-류삼영/류삼영_with_images.html
    """
    try:
        from urllib.parse import unquote

        # URL 디코딩 (한글 처리)
        decoded_path = unquote(file_path)

        # outputs, uploads, static 폴더만 허용
        allowed_prefixes = {
            'outputs': OUTPUT_DIR,
            'uploads': UPLOAD_DIR,
            'static': STATIC_DIR,
        }

        # 경로 파싱
        parts = decoded_path.split('/')
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="잘못된 경로입니다")

        base_folder = parts[0]
        if base_folder not in allowed_prefixes:
            raise HTTPException(status_code=400, detail=f"허용되지 않은 폴더: {base_folder}")

        # 실제 파일 경로 구성
        relative_path = '/'.join(parts[1:])
        full_path = allowed_prefixes[base_folder] / relative_path

        # 경로 순회 공격 방지
        full_path = full_path.resolve()
        base_path = allowed_prefixes[base_folder].resolve()
        if not str(full_path).startswith(str(base_path)):
            raise HTTPException(status_code=403, detail="접근이 허용되지 않은 경로입니다")

        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {decoded_path}")

        if not full_path.is_file():
            raise HTTPException(status_code=400, detail="디렉토리는 서빙할 수 없습니다")

        # MIME 타입 결정
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(full_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        return FileResponse(
            path=str(full_path),
            media_type=mime_type,
            filename=full_path.name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 서빙 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 서빙 실패: {str(e)}")


@app.delete("/api/files/{folder}/{filename}")
async def delete_folder_file(folder: str, filename: str):
    """
    폴더에서 파일 삭제
    """
    try:
        # 허용된 폴더만 접근 가능
        allowed_folders = {
            'outputs': OUTPUT_DIR,
            'uploads': UPLOAD_DIR,
            'static': STATIC_DIR,
            'templates': TEMPLATES_DIR,
            'root': BASE_DIR  # 루트 폴더 (Python 파일용)
        }

        if folder not in allowed_folders:
            raise HTTPException(status_code=400, detail=f"허용되지 않은 폴더: {folder}")

        # 보안: 파일명 검증 (경로 조작 방지)
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="잘못된 파일명입니다")

        folder_path = allowed_folders[folder]
        file_path = folder_path / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="파일만 삭제할 수 있습니다")

        file_path.unlink()
        logger.info(f"파일 삭제 완료: {folder}/{filename}")

        return JSONResponse({
            "success": True,
            "message": "파일이 삭제되었습니다",
            "folder": folder,
            "filename": filename
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 삭제 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 삭제 실패: {str(e)}")


@app.get("/api/editor/files")
async def list_html_files():
    """
    편집 가능한 HTML 파일 목록 반환
    """
    try:
        files = []
        for file_path in OUTPUT_DIR.glob("*.html"):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "url": f"/outputs/{file_path.name}"
                })

        # 최신 파일 우선 정렬
        files.sort(key=lambda x: x["modified"], reverse=True)

        return JSONResponse({
            "success": True,
            "files": files,
            "count": len(files)
        })

    except Exception as e:
        logger.error(f"파일 목록 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 목록 조회 실패: {str(e)}")




@app.post("/api/convert-pdf")
async def convert_pdf_for_editor(
    file: UploadFile = File(...),
    output_name: Optional[str] = Form(default=None)
):
    """
    에디터용 간소화된 PDF 변환 API
    
    - file: PDF 파일
    - output_name: 출력 파일명 (선택사항)
    
    Returns:
    - success: 성공 여부
    - filename: 생성된 HTML 파일명
    - url: 파일 URL
    """
    
    # 파일 검증
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")
    
    # 파일 크기 제한 (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    pdf_content = await file.read()
    if len(pdf_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="파일 크기는 50MB를 초과할 수 없습니다")
    
    # 고유 ID 생성
    job_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 파일 저장
    original_filename = file.filename
    safe_filename = f"{job_id}_{timestamp}.pdf"
    upload_path = UPLOAD_DIR / safe_filename
    
    try:
        with open(upload_path, "wb") as f:
            f.write(pdf_content)
        
        logger.info(f"[{job_id}] 에디터 PDF 변환 시작: {original_filename}")
        
        # 1. PDF에서 텍스트와 이미지 추출
        try:
            extracted_data = pdf_converter.extract_from_pdf(
                str(upload_path),
                content_type="general",
                exclude_pages=[]
            )
        except Exception as e:
            logger.error(f"[{job_id}] PDF 추출 실패: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"PDF 파일 처리 중 오류가 발생했습니다: {str(e)}")
        
        if not extracted_data:
            logger.error(f"[{job_id}] PDF 추출 결과가 없음")
            raise HTTPException(status_code=500, detail="PDF 처리 중 오류가 발생했습니다")
        
        logger.info(f"[{job_id}] PDF 추출 완료: {extracted_data.get('page_count', 0)}페이지")
        
        # 2. HTML 생성
        result_title = output_name if output_name else Path(original_filename).stem
        
        # 출력 파일명 생성 - output_name이 있으면 사용, 없으면 자동 생성
        if output_name:
            # 사용자 지정 파일명 (확장자 처리)
            if not output_name.lower().endswith('.html'):
                output_name += '.html'
            output_filename = output_name
        else:
            # 원본 PDF 파일명 기반 자동 생성
            safe_pdf_name = Path(original_filename).stem
            safe_pdf_name = "".join(c for c in safe_pdf_name if c.isalnum() or c in ('_', '-', ' ', '가', '나', '다') or ord(c) > 127).strip()
            if not safe_pdf_name:
                safe_pdf_name = "document"
            output_filename = f"{safe_pdf_name}_{timestamp}.html"
        
        output_path = OUTPUT_DIR / output_filename
        
        try:
            html_content = html_generator.generate_html(
                extracted_data=extracted_data,
                title=result_title,
                content_type="general",
                job_id=job_id
            )
        except Exception as e:
            logger.error(f"[{job_id}] HTML 생성 실패: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"HTML 생성 중 오류가 발생했습니다: {str(e)}")
        
        # HTML 파일 저장
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"[{job_id}] HTML 변환 완료: {output_filename}")
        
        # 임시 파일 정리
        cleanup_temp_files(job_id=job_id, keep_outputs=True)
        
        result_url = f"/outputs/{output_filename}"
        
        return JSONResponse({
            "success": True,
            "filename": output_filename,
            "url": result_url,
            "title": result_title,
            "page_count": extracted_data.get('page_count', 0)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{job_id}] PDF 변환 실패: {str(e)}", exc_info=True)
        # 임시 파일 정리
        cleanup_temp_files(job_id=job_id, keep_outputs=False)
        raise HTTPException(status_code=500, detail=f"PDF 변환 중 오류가 발생했습니다: {str(e)}")


@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """
    이미지 파일 업로드 API (에디터용)

    - file: 업로드할 이미지 파일 (jpg, jpeg, png, gif, webp, svg)

    Returns:
    - success: 성공 여부
    - url: 업로드된 이미지 URL
    - filename: 저장된 파일명
    """
    try:
        # 지원하는 이미지 확장자
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'}

        original_filename = file.filename
        file_extension = Path(original_filename).suffix.lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 이미지 형식입니다. 지원 형식: {', '.join(allowed_extensions)}"
            )

        # 파일 크기 제한 (10MB)
        MAX_IMAGE_SIZE = 10 * 1024 * 1024
        content = await file.read()

        if len(content) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail="이미지 크기는 10MB를 초과할 수 없습니다")

        # 고유 파일명 생성 (원본 이름 유지 + 타임스탬프)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = Path(original_filename).stem
        # 파일명에서 안전하지 않은 문자 제거
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in ('_', '-', ' ')).strip()
        if not safe_name:
            safe_name = "image"

        new_filename = f"{safe_name}_{timestamp}{file_extension}"

        # static/images 디렉토리 확인 및 생성
        images_dir = STATIC_DIR / "images"
        images_dir.mkdir(exist_ok=True)

        # 파일 저장
        file_path = images_dir / new_filename

        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"이미지 업로드 완료: {new_filename} ({len(content)} bytes)")

        return JSONResponse({
            "success": True,
            "message": "이미지가 업로드되었습니다",
            "url": f"/static/images/{new_filename}",
            "filename": new_filename,
            "original_filename": original_filename,
            "size": len(content)
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 업로드 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"이미지 업로드 실패: {str(e)}")


@app.get("/api/images")
async def list_images():
    """
    서버에 저장된 이미지 목록 반환 (에디터 갤러리용)
    """
    try:
        images_dir = STATIC_DIR / "images"

        if not images_dir.exists():
            return JSONResponse({
                "success": True,
                "images": [],
                "count": 0
            })

        images = []
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.ico'}

        for file_path in images_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in allowed_extensions:
                try:
                    stat = file_path.stat()
                    images.append({
                        "name": file_path.name,
                        "url": f"/static/images/{file_path.name}",
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                except Exception as e:
                    logger.warning(f"이미지 정보 조회 실패: {file_path.name} - {str(e)}")

        # 최신 파일 우선 정렬
        images.sort(key=lambda x: x["modified"], reverse=True)

        return JSONResponse({
            "success": True,
            "images": images,
            "count": len(images)
        })

    except Exception as e:
        logger.error(f"이미지 목록 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"이미지 목록 조회 실패: {str(e)}")


# ============================================
# 폴더 ZIP 다운로드 API
# ============================================

@app.get("/api/download/folder/{folder_path:path}")
async def download_folder_as_zip(folder_path: str):
    """
    outputs 폴더 내 특정 폴더를 ZIP 파일로 다운로드

    예: /api/download/folder/Minjoo/류삼영 -> Minjoo/류삼영 폴더를 ZIP으로 다운로드
    """
    try:
        # 폴더 경로 검증
        folder_path = unquote(folder_path)
        target_path = OUTPUT_DIR / folder_path

        # 경로 순회 공격 방지
        try:
            target_path = target_path.resolve()
            if not str(target_path).startswith(str(OUTPUT_DIR.resolve())):
                raise HTTPException(status_code=403, detail="접근이 허용되지 않은 경로입니다")
        except Exception:
            raise HTTPException(status_code=400, detail="잘못된 경로입니다")

        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"폴더를 찾을 수 없습니다: {folder_path}")

        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail="폴더가 아닙니다")

        # ZIP 파일 생성 (메모리에)
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 폴더 내 모든 파일 추가
            for file_path in target_path.rglob('*'):
                if file_path.is_file():
                    # ZIP 내 상대 경로 계산
                    arcname = file_path.relative_to(target_path.parent)
                    zip_file.write(file_path, arcname)

        zip_buffer.seek(0)

        # 파일명 설정 (마지막 폴더명 사용)
        zip_filename = f"{target_path.name}.zip"

        # 한글 파일명 인코딩
        encoded_filename = quote(zip_filename)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"폴더 ZIP 다운로드 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"ZIP 다운로드 실패: {str(e)}")


# ============================================
# 서버 관리 API
# ============================================

import subprocess
import signal

# 실행 중인 서버 프로세스 추적
running_servers = {}

@app.post("/api/server/start")
async def start_server(request: Request):
    """
    로컬 서버 시작 API
    """
    try:
        data = await request.json()
        server_id = data.get('id')
        server_path = data.get('path')
        server_type = data.get('type')
        port = data.get('port', 8000)
        custom_cmd = data.get('cmd')

        if not server_path or not os.path.exists(server_path):
            return JSONResponse({
                "success": False,
                "error": f"경로를 찾을 수 없습니다: {server_path}"
            })

        # 이미 실행 중인지 확인
        if server_id in running_servers:
            proc = running_servers[server_id]
            if proc.poll() is None:  # 아직 실행 중
                return JSONResponse({
                    "success": False,
                    "error": "서버가 이미 실행 중입니다"
                })

        # 서버 타입별 명령어 생성
        if custom_cmd:
            cmd = custom_cmd.split()
        elif server_type == 'django':
            cmd = ['python', 'manage.py', 'runserver', f'0.0.0.0:{port}']
        elif server_type == 'fastapi':
            cmd = ['python', '-m', 'uvicorn', 'app:app', '--host', '0.0.0.0', '--port', str(port)]
        elif server_type == 'flask':
            cmd = ['python', '-m', 'flask', 'run', '--host', '0.0.0.0', '--port', str(port)]
        else:
            return JSONResponse({
                "success": False,
                "error": f"지원하지 않는 서버 타입: {server_type}"
            })

        # 서버 시작 (백그라운드)
        process = subprocess.Popen(
            cmd,
            cwd=server_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )

        running_servers[server_id] = process

        logger.info(f"서버 시작됨: {server_id} (PID: {process.pid})")

        return JSONResponse({
            "success": True,
            "message": f"서버가 시작되었습니다",
            "pid": process.pid,
            "port": port
        })

    except Exception as e:
        logger.error(f"서버 시작 실패: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@app.post("/api/server/stop")
async def stop_server(request: Request):
    """
    로컬 서버 중지 API
    """
    try:
        data = await request.json()
        server_id = data.get('id')
        port = data.get('port')

        # 추적 중인 프로세스가 있으면 종료
        if server_id in running_servers:
            proc = running_servers[server_id]
            if proc.poll() is None:
                if os.name == 'nt':
                    # Windows: taskkill 사용
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                                   capture_output=True)
                else:
                    # Unix: SIGTERM
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)

                del running_servers[server_id]
                logger.info(f"서버 중지됨: {server_id}")

                return JSONResponse({
                    "success": True,
                    "message": "서버가 중지되었습니다"
                })

        # 포트로 프로세스 찾아서 종료 (Windows)
        if port and os.name == 'nt':
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True, capture_output=True, text=True
            )
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'LISTENING' in line:
                        parts = line.split()
                        pid = parts[-1]
                        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                        logger.info(f"포트 {port} 프로세스 종료: PID {pid}")

                return JSONResponse({
                    "success": True,
                    "message": f"포트 {port} 서버가 중지되었습니다"
                })

        return JSONResponse({
            "success": False,
            "error": "실행 중인 서버를 찾을 수 없습니다"
        })

    except Exception as e:
        logger.error(f"서버 중지 실패: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@app.get("/api/server/status/{server_id}")
async def get_server_status(server_id: str):
    """
    서버 상태 확인 API
    """
    try:
        # 추적 중인 프로세스 확인
        if server_id in running_servers:
            proc = running_servers[server_id]
            running = proc.poll() is None
            return JSONResponse({
                "success": True,
                "running": running,
                "pid": proc.pid if running else None
            })

        return JSONResponse({
            "success": True,
            "running": False
        })

    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


# ============================================
# 외부 폴더 관리 API (터미널/파일 실행)
# ============================================

# 허용된 외부 폴더 목록 (보안)
ALLOWED_EXTERNAL_FOLDERS = {
    'k-mart': Path('C:/k-mart'),
    'studysnap': Path('C:/StudySnap-Backend'),
}

@app.get("/api/external/folders")
async def list_external_folders():
    """등록된 외부 폴더 목록"""
    folders = []
    for name, path in ALLOWED_EXTERNAL_FOLDERS.items():
        folders.append({
            "name": name,
            "path": str(path),
            "exists": path.exists()
        })
    return JSONResponse({"success": True, "folders": folders})


@app.get("/api/external/browse/{folder_name}")
async def browse_external_folder(folder_name: str, subpath: str = ""):
    """외부 폴더 탐색"""
    try:
        if folder_name not in ALLOWED_EXTERNAL_FOLDERS:
            raise HTTPException(status_code=403, detail=f"허용되지 않은 폴더: {folder_name}")

        base_path = ALLOWED_EXTERNAL_FOLDERS[folder_name]
        target_path = base_path / subpath if subpath else base_path

        # 경로 순회 공격 방지
        target_path = target_path.resolve()
        if not str(target_path).startswith(str(base_path.resolve())):
            raise HTTPException(status_code=403, detail="접근이 허용되지 않은 경로")

        if not target_path.exists():
            raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다")

        items = []
        for item in target_path.iterdir():
            try:
                stat = item.stat()
                items.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size": stat.st_size if item.is_file() else 0,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "extension": item.suffix.lower() if item.is_file() else ""
                })
            except Exception:
                continue

        # 폴더 먼저, 그 다음 파일 (이름순)
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

        return JSONResponse({
            "success": True,
            "folder_name": folder_name,
            "current_path": subpath,
            "full_path": str(target_path),
            "items": items
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"외부 폴더 탐색 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/external/execute")
async def execute_command(request: Request):
    """
    외부 폴더에서 명령어 실행 (터미널)
    보안: 허용된 폴더 내에서만 실행 가능
    """
    try:
        data = await request.json()
        folder_name = data.get('folder')
        command = data.get('command', '').strip()
        timeout = data.get('timeout', 30)

        if not folder_name or folder_name not in ALLOWED_EXTERNAL_FOLDERS:
            return JSONResponse({
                "success": False,
                "error": "허용되지 않은 폴더입니다"
            })

        if not command:
            return JSONResponse({
                "success": False,
                "error": "명령어를 입력해주세요"
            })

        # 위험한 명령어 차단
        dangerous_commands = ['rm -rf /', 'format', 'del /s', 'rmdir /s']
        if any(dc in command.lower() for dc in dangerous_commands):
            return JSONResponse({
                "success": False,
                "error": "위험한 명령어는 실행할 수 없습니다"
            })

        work_dir = ALLOWED_EXTERNAL_FOLDERS[folder_name]

        # 명령어 실행
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )

        return JSONResponse({
            "success": True,
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })

    except subprocess.TimeoutExpired:
        return JSONResponse({
            "success": False,
            "error": f"명령어 실행 시간 초과 ({timeout}초)"
        })
    except Exception as e:
        logger.error(f"명령어 실행 실패: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@app.post("/api/external/run-script")
async def run_script(request: Request):
    """
    Python/Batch 스크립트 실행
    """
    try:
        data = await request.json()
        folder_name = data.get('folder')
        script_path = data.get('script')  # 상대 경로
        script_type = data.get('type', 'python')  # python, batch
        args = data.get('args', [])
        background = data.get('background', False)

        if folder_name not in ALLOWED_EXTERNAL_FOLDERS:
            return JSONResponse({
                "success": False,
                "error": "허용되지 않은 폴더입니다"
            })

        base_path = ALLOWED_EXTERNAL_FOLDERS[folder_name]
        full_script_path = (base_path / script_path).resolve()

        # 경로 검증
        if not str(full_script_path).startswith(str(base_path.resolve())):
            return JSONResponse({
                "success": False,
                "error": "접근이 허용되지 않은 경로입니다"
            })

        if not full_script_path.exists():
            return JSONResponse({
                "success": False,
                "error": f"스크립트를 찾을 수 없습니다: {script_path}"
            })

        # 명령어 구성
        if script_type == 'python':
            cmd = ['python', str(full_script_path)] + args
        elif script_type == 'batch':
            cmd = [str(full_script_path)] + args
        else:
            return JSONResponse({
                "success": False,
                "error": f"지원하지 않는 스크립트 타입: {script_type}"
            })

        if background:
            # 백그라운드 실행
            process = subprocess.Popen(
                cmd,
                cwd=str(base_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            return JSONResponse({
                "success": True,
                "message": "스크립트가 백그라운드에서 실행되었습니다",
                "pid": process.pid
            })
        else:
            # 동기 실행 (30초 타임아웃)
            result = subprocess.run(
                cmd,
                cwd=str(base_path),
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace'
            )
            return JSONResponse({
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            })

    except subprocess.TimeoutExpired:
        return JSONResponse({
            "success": False,
            "error": "스크립트 실행 시간 초과 (30초)"
        })
    except Exception as e:
        logger.error(f"스크립트 실행 실패: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@app.post("/api/external/upload")
async def upload_to_external(
    folder: str = Form(...),
    subpath: str = Form(""),
    file: UploadFile = File(...)
):
    """외부 폴더에 파일 업로드"""
    try:
        if folder not in ALLOWED_EXTERNAL_FOLDERS:
            raise HTTPException(status_code=403, detail="허용되지 않은 폴더")

        base_path = ALLOWED_EXTERNAL_FOLDERS[folder]
        target_dir = (base_path / subpath).resolve() if subpath else base_path.resolve()

        # 경로 검증
        if not str(target_dir).startswith(str(base_path.resolve())):
            raise HTTPException(status_code=403, detail="접근이 허용되지 않은 경로")

        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / file.filename

        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)

        return JSONResponse({
            "success": True,
            "message": f"파일 업로드 완료: {file.filename}",
            "path": str(file_path)
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/external/read/{folder_name}")
async def read_external_file(folder_name: str, filepath: str):
    """외부 폴더의 파일 내용 읽기"""
    try:
        if folder_name not in ALLOWED_EXTERNAL_FOLDERS:
            raise HTTPException(status_code=403, detail="허용되지 않은 폴더")

        base_path = ALLOWED_EXTERNAL_FOLDERS[folder_name]
        file_path = (base_path / filepath).resolve()

        # 경로 검증
        if not str(file_path).startswith(str(base_path.resolve())):
            raise HTTPException(status_code=403, detail="접근이 허용되지 않은 경로")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

        # 텍스트 파일만 읽기
        text_extensions = {'.py', '.txt', '.json', '.html', '.css', '.js', '.md', '.yaml', '.yml', '.bat', '.sh', '.env', '.gitignore'}
        if file_path.suffix.lower() not in text_extensions:
            raise HTTPException(status_code=400, detail="텍스트 파일만 읽을 수 있습니다")

        content = file_path.read_text(encoding='utf-8', errors='replace')

        return JSONResponse({
            "success": True,
            "filename": file_path.name,
            "content": content,
            "size": len(content)
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 읽기 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 학습 시스템 API
# ============================================

@app.post("/api/learning/classify")
async def classify_text(request: Request):
    """
    텍스트 객체 분류 API

    텍스트와 스타일 정보를 받아 PDF 객체 유형을 분류합니다.
    """
    try:
        from learning_data import ObjectClassifier, TextStyle, FontStyle, BoundingBox

        data = await request.json()
        text = data.get("text", "")
        style_data = data.get("style", {})
        bbox_data = data.get("bbox", {})

        classifier = ObjectClassifier()

        # 스타일 객체 생성
        style = None
        if style_data:
            style = TextStyle(
                font_name=style_data.get("font_name", "Unknown"),
                font_size=float(style_data.get("font_size", 12.0)),
                font_style=FontStyle(style_data.get("font_style", "regular")),
                color=style_data.get("color", "#000000")
            )

        # 바운딩 박스 생성
        bbox = None
        if bbox_data:
            bbox = BoundingBox(
                x=float(bbox_data.get("x", 0)),
                y=float(bbox_data.get("y", 0)),
                width=float(bbox_data.get("width", 0)),
                height=float(bbox_data.get("height", 0)),
                page=int(bbox_data.get("page", 1))
            )

        # 분류 실행
        obj_type, confidence = classifier.classify(text, style, bbox)

        return JSONResponse({
            "success": True,
            "text": text[:100],
            "classification": {
                "type": obj_type.value,
                "type_name": obj_type.name,
                "confidence": round(confidence, 4)
            },
            "html_mapping": classifier._get_html_mapping(obj_type)
        })

    except Exception as e:
        logger.error(f"텍스트 분류 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"텍스트 분류 실패: {str(e)}")


@app.post("/api/learning/validate")
async def validate_text(request: Request):
    """
    텍스트 검증 API

    원본 텍스트와 변환된 텍스트를 비교하여 오류를 검출합니다.
    """
    try:
        from learning_data import TextValidator

        data = await request.json()
        original = data.get("original", "")
        converted = data.get("converted", "")

        if not original or not converted:
            raise HTTPException(status_code=400, detail="original과 converted 텍스트가 필요합니다")

        validator = TextValidator()
        report = validator.validate(original, converted)

        return JSONResponse({
            "success": True,
            "validation": report.to_dict()
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"텍스트 검증 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"텍스트 검증 실패: {str(e)}")


@app.post("/api/learning/validate-document")
async def validate_document(request: Request):
    """
    문서 전체 검증 API

    여러 페이지의 원본과 변환 텍스트를 비교합니다.
    """
    try:
        from learning_data import BatchValidator

        data = await request.json()
        original_pages = data.get("original_pages", [])
        converted_pages = data.get("converted_pages", [])

        if not original_pages or not converted_pages:
            raise HTTPException(status_code=400, detail="original_pages와 converted_pages가 필요합니다")

        validator = BatchValidator()
        result = validator.validate_document(original_pages, converted_pages)

        # 중요 오류만 별도 추출
        critical_errors = validator.get_critical_errors(min_confidence=0.8)

        return JSONResponse({
            "success": True,
            "document_validation": result,
            "critical_errors": critical_errors[:20]  # 상위 20개만
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 검증 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"문서 검증 실패: {str(e)}")


@app.get("/api/learning/object-types")
async def get_object_types():
    """
    지원하는 객체 유형 목록 반환
    """
    try:
        from learning_data import ObjectType, ELECTION_MAPPINGS

        types = []
        for obj_type in ObjectType:
            mapping = ELECTION_MAPPINGS.get(obj_type)
            types.append({
                "code": obj_type.value,
                "name": obj_type.name,
                "has_template": mapping is not None,
                "css_class": mapping.css_class if mapping else None
            })

        return JSONResponse({
            "success": True,
            "object_types": types,
            "total": len(types)
        })

    except Exception as e:
        logger.error(f"객체 유형 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/learning/diff")
async def get_text_diff(request: Request):
    """
    원본과 변환 텍스트의 차이를 HTML로 반환
    """
    try:
        from learning_data import TextValidator

        data = await request.json()
        original = data.get("original", "")
        converted = data.get("converted", "")

        validator = TextValidator()
        diff_html = validator.get_diff_html(original, converted)

        return JSONResponse({
            "success": True,
            "diff_html": diff_html
        })

    except Exception as e:
        logger.error(f"차이 비교 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/editor/save")
async def save_html_file(request: Request):
    """
    HTML 에디터에서 파일 저장 (하위 폴더 지원) + 자동 학습

    - filename: 저장할 파일명 또는 경로 (예: 국민-나경원/NA_xxx.html, outputs/국민-나경원/NA_xxx.html)
    - content: HTML 내용

    저장 시 원본과 비교하여 자동으로 학습 데이터 수집
    """
    try:
        # UTF-8 인코딩으로 명시적으로 body 읽기
        body = await request.body()
        text = body.decode('utf-8')
        import json
        data = json.loads(text)
        filename = data.get("filename")
        content = data.get("content")

        if not filename or not content:
            raise HTTPException(status_code=400, detail="filename과 content가 필요합니다")

        # 보안: 상위 디렉토리 접근 방지
        if ".." in filename:
            raise HTTPException(status_code=400, detail="잘못된 파일명입니다")

        # 파일 경로 정규화
        # outputs/하위폴더/파일명 또는 하위폴더/파일명 형태 지원
        filename = filename.replace("\\", "/")  # 윈도우 경로 정규화

        if filename.startswith("outputs/"):
            filename = filename[8:]  # "outputs/" 제거

        if not filename.endswith(".html"):
            raise HTTPException(status_code=400, detail="HTML 파일만 저장할 수 있습니다")

        # 파일 저장 경로
        file_path = OUTPUT_DIR / filename

        # 경로 순회 공격 방지
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(OUTPUT_DIR.resolve())):
                raise HTTPException(status_code=403, detail="접근이 허용되지 않은 경로입니다")
        except Exception:
            raise HTTPException(status_code=400, detail="잘못된 경로입니다")

        # 하위 폴더가 있으면 생성
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # ========================================
        # 자동 학습: 원본과 비교하여 변경점 학습
        # ========================================
        learning_result = None
        original_html = ""

        if file_path.exists() and active_learning_engine is not None:
            try:
                # 원본 HTML 읽기
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_html = f.read()

                # 내용이 변경된 경우에만 학습
                if original_html.strip() != content.strip():
                    # job_id 생성 (파일명 기반)
                    import hashlib
                    job_id = hashlib.md5(filename.encode()).hexdigest()[:8]

                    # HTML diff 분석 및 패턴 학습
                    diff = active_learning_engine.save_html_diff(
                        job_id=job_id,
                        original_html=original_html,
                        modified_html=content
                    )

                    # 후보자 정보 추출 (학습 메타데이터)
                    import re
                    candidate_match = re.search(r'<h1[^>]*class="[^"]*hero-name[^"]*"[^>]*>([^<]+)</h1>', content)
                    party_match = re.search(r'<span[^>]*class="[^"]*party-badge[^"]*"[^>]*>([^<]+)</span>', content)

                    learning_result = {
                        "changes_count": len(diff.changes),
                        "patterns_count": len(diff.extracted_patterns),
                        "candidate": candidate_match.group(1) if candidate_match else None,
                        "party": party_match.group(1) if party_match else None
                    }

                    logger.info(f"[자동학습] {filename}: {len(diff.changes)}개 변경, {len(diff.extracted_patterns)}개 패턴 추출")

            except Exception as e:
                logger.warning(f"자동 학습 실패 (계속 진행): {e}")

        # 파일 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"HTML 파일 저장 완료: {filename} ({len(content)} bytes)")

        response_data = {
            "success": True,
            "message": "파일이 저장되었습니다",
            "filename": filename,
            "size": len(content)
        }

        # 학습 결과 포함
        if learning_result:
            response_data["learning"] = learning_result
            response_data["message"] = f"파일 저장 + {learning_result['changes_count']}개 변경점 학습됨"

        return JSONResponse(response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 저장 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {str(e)}")


@app.post("/api/editor/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder: str = Form(default="outputs"),
    subfolder: str = Form(default="")
):
    """
    파일 업로드 (HTML, Python, 이미지)

    - 로컬에서 작업한 파일을 서버에 업로드
    - folder 파라미터로 저장 위치 선택 가능 (outputs, static, uploads)
    - subfolder 파라미터로 하위 폴더 경로 지정 가능 (예: Minjoo/images)
    - 허용 파일: .html, .htm, .py, .png, .jpg, .jpeg, .gif, .svg, .webp
    """
    try:
        # 허용된 폴더만 사용 가능
        allowed_folders = {
            "outputs": OUTPUT_DIR,
            "static": STATIC_DIR,
            "uploads": UPLOAD_DIR,
            "root": BASE_DIR  # 루트 폴더 (Python 파일용)
        }

        if folder not in allowed_folders:
            raise HTTPException(status_code=400, detail=f"허용되지 않은 폴더입니다. 사용 가능: {list(allowed_folders.keys())}")

        target_dir = allowed_folders[folder]

        # 파일 확장자 검증
        allowed_extensions = ['.html', '.htm', '.py', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']
        file_ext = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"허용되지 않는 파일 형식입니다. 허용: {', '.join(allowed_extensions)}")

        # 이미지 파일 여부 확인
        is_image = file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']

        # 보안: 파일명 검증 (경로 조작 방지)
        filename = file.filename
        if ".." in filename:
            raise HTTPException(status_code=400, detail="잘못된 파일명입니다")

        # subfolder 경로 검증 및 처리
        if subfolder:
            # 경로 구분자 정규화 및 보안 검사
            subfolder = subfolder.replace("\\", "/").strip("/")
            if ".." in subfolder:
                raise HTTPException(status_code=400, detail="잘못된 하위 폴더 경로입니다")
            # 하위 폴더 경로를 target_dir에 추가
            target_dir = target_dir / subfolder

        # 타겟 디렉토리가 없으면 생성
        target_dir.mkdir(parents=True, exist_ok=True)

        # 파일 내용 읽기
        content = await file.read()

        # 파일 저장 경로
        file_path = target_dir / filename

        if is_image:
            # 이미지 파일은 바이너리로 저장
            with open(file_path, 'wb') as f:
                f.write(content)
            file_size = len(content)
        else:
            # 텍스트 파일은 UTF-8로 저장
            try:
                content_str = content.decode('utf-8')
            except UnicodeDecodeError:
                content_str = content.decode('cp949')  # 한글 Windows 인코딩

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content_str)
            file_size = len(content_str)

        # 전체 저장 경로 계산
        full_path = f"{folder}/{subfolder}/{filename}" if subfolder else f"{folder}/{filename}"
        logger.info(f"파일 업로드 완료: {full_path} ({file_size} bytes)")

        return JSONResponse({
            "success": True,
            "message": f"파일이 {full_path}에 업로드되었습니다",
            "filename": filename,
            "folder": folder,
            "subfolder": subfolder,
            "size": file_size,
            "url": f"/{full_path}"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")


# ============================================
# 범용 폴더 탐색 API (윈도우 탐색기 스타일)
# ============================================

@app.get("/api/browse")
async def browse_folder(path: str = ""):
    """
    범용 폴더 탐색 API - 윈도우 탐색기처럼 임의 경로 탐색

    - path가 비어있으면 프로젝트 루트(BASE_DIR)의 내용 반환
    - path가 있으면 해당 경로의 폴더/파일 목록 반환
    - 보안: BASE_DIR 하위만 접근 가능
    """
    try:
        # 경로 정규화
        path = path.replace("\\", "/").strip("/")

        # 보안 검사
        if ".." in path:
            raise HTTPException(status_code=400, detail="잘못된 경로입니다")

        # 전체 경로 계산
        if path:
            target_path = BASE_DIR / path
        else:
            target_path = BASE_DIR

        # 경로가 BASE_DIR 하위인지 확인
        try:
            target_path.resolve().relative_to(BASE_DIR.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="접근이 허용되지 않은 경로입니다")

        # 경로 존재 확인
        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"경로를 찾을 수 없습니다: {path}")

        # 파일인 경우
        if target_path.is_file():
            stat = target_path.stat()
            return JSONResponse({
                "success": True,
                "type": "file",
                "path": path,
                "name": target_path.name,
                "size": stat.st_size,
                "modified": stat.st_mtime
            })

        # 폴더인 경우 - 내용 목록 반환
        items = []
        folders = []
        files = []

        for item in target_path.iterdir():
            try:
                stat = item.stat()
                item_info = {
                    "name": item.name,
                    "path": f"{path}/{item.name}" if path else item.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "is_dir": item.is_dir()
                }

                if item.is_dir():
                    # 폴더 내 항목 수 계산
                    try:
                        item_info["children_count"] = len(list(item.iterdir()))
                    except:
                        item_info["children_count"] = 0
                    folders.append(item_info)
                else:
                    # 파일 확장자
                    item_info["extension"] = item.suffix.lower()
                    files.append(item_info)
            except Exception as e:
                # 접근 권한 없는 파일 스킵
                continue

        # 정렬: 폴더 먼저, 이름순
        folders.sort(key=lambda x: x["name"].lower())
        files.sort(key=lambda x: x["name"].lower())
        items = folders + files

        # 상위 경로 계산
        parent_path = "/".join(path.split("/")[:-1]) if path else None

        return JSONResponse({
            "success": True,
            "type": "directory",
            "path": path,
            "name": target_path.name if path else "root",
            "parent": parent_path,
            "items": items,
            "folders_count": len(folders),
            "files_count": len(files)
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"폴더 탐색 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"폴더 탐색 실패: {str(e)}")


@app.post("/api/browse/upload")
async def browse_upload(
    file: UploadFile = File(...),
    path: str = Form(default="")
):
    """
    범용 파일 업로드 - 지정된 경로에 파일 업로드

    - path: 업로드할 폴더 경로 (BASE_DIR 기준 상대 경로)
    - 보안: BASE_DIR 하위만 접근 가능
    """
    try:
        # 경로 정규화
        path = path.replace("\\", "/").strip("/")

        # 보안 검사
        if ".." in path:
            raise HTTPException(status_code=400, detail="잘못된 경로입니다")

        # 전체 경로 계산
        if path:
            target_dir = BASE_DIR / path
        else:
            target_dir = BASE_DIR

        # 경로가 BASE_DIR 하위인지 확인
        try:
            target_dir.resolve().relative_to(BASE_DIR.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="접근이 허용되지 않은 경로입니다")

        # 타겟 디렉토리 생성
        target_dir.mkdir(parents=True, exist_ok=True)

        # 파일명 검증
        filename = file.filename
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="잘못된 파일명입니다")

        # 파일 저장 경로
        file_path = target_dir / filename

        # 파일 내용 읽기
        content = await file.read()

        # 이미지 파일 여부 확인
        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        is_binary = file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.pdf', '.zip']

        if is_binary:
            with open(file_path, 'wb') as f:
                f.write(content)
        else:
            try:
                content_str = content.decode('utf-8')
            except UnicodeDecodeError:
                content_str = content.decode('cp949', errors='replace')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content_str)

        full_path = f"{path}/{filename}" if path else filename
        logger.info(f"범용 업로드 완료: {full_path} ({len(content)} bytes)")

        return JSONResponse({
            "success": True,
            "message": f"파일이 업로드되었습니다",
            "filename": filename,
            "path": path,
            "full_path": full_path,
            "size": len(content)
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"범용 업로드 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")


@app.post("/api/browse/create-folder")
async def create_folder(path: str = Form(...)):
    """
    새 폴더 생성

    - path: 생성할 폴더의 전체 경로 (BASE_DIR 기준)
    """
    try:
        path = path.replace("\\", "/").strip("/")

        if ".." in path:
            raise HTTPException(status_code=400, detail="잘못된 경로입니다")

        target_path = BASE_DIR / path

        try:
            target_path.resolve().relative_to(BASE_DIR.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="접근이 허용되지 않은 경로입니다")

        if target_path.exists():
            raise HTTPException(status_code=400, detail="이미 존재하는 폴더입니다")

        target_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"폴더 생성: {path}")

        return JSONResponse({
            "success": True,
            "message": "폴더가 생성되었습니다",
            "path": path
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"폴더 생성 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"폴더 생성 실패: {str(e)}")


# ============================================
# 완전 자동화 변환 API
# ============================================

# 자동화 변환기 초기화
try:
    from auto_election_converter import AutoElectionConverter
    auto_converter = AutoElectionConverter()
    logger.info("완전 자동화 변환기 초기화 완료")
except Exception as e:
    auto_converter = None
    logger.warning(f"완전 자동화 변환기 초기화 실패: {e}")


@app.post("/api/auto-convert")
async def auto_convert_election(
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    save_folder: Optional[str] = Form(default=None),
    create_images_folder: Optional[str] = Form(default=None)
):
    """
    완전 자동화 선거공보물 변환 API

    - PDF 업로드 시 자동으로:
      1. 정당 감지 및 테마 적용
      2. 후보자 정보 추출
      3. 공약/경력 구조화
      4. 모바일 최적화 HTML 생성

    Parameters:
    - file: PDF 파일
    - title: 출력 파일 제목 (선택사항)
    - save_folder: 저장할 하위 폴더명 (선택사항, 예: 민주-이광재)
    - create_images_folder: images 하위 폴더 생성 여부 (선택사항, "true"인 경우 생성)

    Returns:
    - success: 성공 여부
    - result: 변환 결과 (URL, 파일명, 추출된 정보)
    """
    if auto_converter is None:
        raise HTTPException(
            status_code=500,
            detail="자동화 변환기가 초기화되지 않았습니다"
        )

    # 파일 검증
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")

    # 파일 크기 제한 (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="파일 크기는 50MB를 초과할 수 없습니다")

    # 고유 ID 생성
    job_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 파일 저장
    original_filename = file.filename
    safe_filename = f"{job_id}_{timestamp}.pdf"
    upload_path = UPLOAD_DIR / safe_filename

    try:
        with open(upload_path, "wb") as f:
            f.write(content)

        logger.info(f"[{job_id}] 완전 자동화 변환 시작: {original_filename}")

        # 자동 변환 실행 (원본 파일명 전달)
        brochure = auto_converter.convert(str(upload_path), original_filename=original_filename)

        # 출력 파일명 생성
        if title:
            safe_title = "".join(c for c in title if c.isalnum() or c in ('_', '-', ' ') or ord(c) > 127).strip()
            output_filename = f"{safe_title}_{timestamp}.html"
        elif brochure.candidate.name:
            output_filename = f"{brochure.candidate.name}_{timestamp}.html"
        else:
            output_filename = f"AUTO_{job_id}_{timestamp}.html"

        # 저장 경로 설정 (하위 폴더 지원)
        if save_folder:
            # 보안: 상위 디렉토리 접근 방지
            if ".." in save_folder:
                raise HTTPException(status_code=400, detail="잘못된 폴더명입니다")
            # 하위 폴더 생성
            output_dir = OUTPUT_DIR / save_folder
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_filename
            output_url_path = f"/outputs/{save_folder}/{output_filename}"

            # images 폴더 생성 (create_images_folder가 "true"인 경우)
            if create_images_folder == "true":
                images_dir = output_dir / "images"
                images_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"[{job_id}] images 폴더 생성됨: {images_dir}")
        else:
            output_dir = OUTPUT_DIR
            output_path = OUTPUT_DIR / output_filename
            output_url_path = f"/outputs/{output_filename}"

        # HTML 생성 (이미지 폴더 경로 전달)
        html_content = auto_converter.generate_html(brochure, output_folder=str(output_dir))

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"[{job_id}] 완전 자동화 변환 완료: {output_filename}")

        # 임시 파일 정리
        cleanup_temp_files(job_id=job_id, keep_outputs=True)

        # 학습 시스템에 기록 (기존 + 능동형 학습)
        try:
            # 기존 학습 시스템
            learning_system.log_conversion(job_id, {
                "filename": original_filename,
                "content_type": "election",
                "page_count": len(brochure.raw_pages),
                "is_image_based": any(p.get("ocr_used") for p in brochure.raw_pages),
                "ocr_used": any(p.get("ocr_used") for p in brochure.raw_pages),
                "auto_converted": True,
                "party_detected": brochure.candidate.party,
                "candidate_name": brochure.candidate.name
            })

            # 능동형 학습 엔진에도 기록
            if active_learning_engine is not None:
                active_learning_engine.record_conversion({
                    "candidate_name": brochure.candidate.name,
                    "party": brochure.candidate.party,
                    "candidate_type": brochure.candidate_type,
                    "region": f"{brochure.region_metro}/{brochure.region_district}",
                    "pledge_count": len(brochure.core_pledges),
                    "career_count": len(brochure.careers),
                    "page_count": len(brochure.raw_pages),
                    "filename": original_filename,
                    "job_id": job_id,
                    "output_path": str(output_path),
                    "theme_color": brochure.theme.primary_color if brochure.theme else "#6366F1"
                })
                logger.info(f"[{job_id}] 능동형 학습 엔진에 변환 기록 완료")

        except Exception as e:
            logger.error(f"학습 데이터 기록 실패: {str(e)}")

        return JSONResponse({
            "success": True,
            "job_id": job_id,
            "message": "완전 자동화 변환이 완료되었습니다",
            "result": {
                "url": output_url_path,
                "filename": output_filename,
                "save_folder": save_folder or "",
                "original_filename": original_filename,
                "candidate": {
                    "name": brochure.candidate.name,
                    "party": brochure.candidate.party,
                    "symbol": brochure.candidate.symbol,
                    "position": brochure.candidate.position,
                    "district": brochure.candidate.district
                },
                "statistics": {
                    "page_count": len(brochure.raw_pages),
                    "pledge_count": len(brochure.core_pledges),
                    "career_count": len(brochure.careers),
                    "ocr_pages": sum(1 for p in brochure.raw_pages if p.get("ocr_used"))
                },
                "theme": {
                    "party_color": brochure.theme.primary_color if brochure.theme else "#6366F1"
                },
                "created_at": datetime.now().isoformat()
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{job_id}] 완전 자동화 변환 실패: {str(e)}", exc_info=True)
        cleanup_temp_files(job_id=job_id, keep_outputs=False)
        raise HTTPException(status_code=500, detail=f"변환 실패: {str(e)}")


@app.get("/api/auto-convert/status")
async def get_auto_convert_status():
    """
    완전 자동화 변환 시스템 상태 확인
    """
    return JSONResponse({
        "success": True,
        "auto_converter_ready": auto_converter is not None,
        "vision_ocr_ready": auto_converter.vision_ocr is not None if auto_converter else False,
        "supported_parties": [
            {"id": "ppp", "name": "국민의힘", "color": "#E11D48"},
            {"id": "dpk", "name": "더불어민주당", "color": "#004EA2"},
            {"id": "jp", "name": "정의당", "color": "#FFCC00"},
            {"id": "pp", "name": "국민의당", "color": "#EA5504"},
            {"id": "rp", "name": "개혁신당", "color": "#FF6B35"},
            {"id": "nrp", "name": "새로운미래", "color": "#10B981"},
            {"id": "independent", "name": "무소속", "color": "#6B7280"}
        ],
        "features": [
            "정당 자동 감지",
            "테마 색상 자동 적용",
            "후보자 정보 자동 추출",
            "공약/경력 구조화",
            "모바일 최적화 HTML",
            "SNS 링크 자동 연결",
            "전화번호 클릭 통화"
        ]
    })


# ==================== 교회 주보 변환 API ====================

def parse_bulletin_text(text: str, church_name: str = "") -> dict:
    """
    주보 PDF 텍스트에서 구조화된 데이터 추출
    명성교회, 여의도순복음교회 등 대형교회 주보 형식 지원

    v2.0 개선사항:
    - 예배 중복 제거 및 순서 정렬
    - 목사님 이름 정확한 추출 (원로목사, 담임목사 형식)
    - 성경책 이름 검증 (교회소식 등 제외)
    - 예배 순서 상세 내용 추출
    """
    import re

    result = {
        "today_verse": {"text": "", "reference": ""},
        "worship_services": [],
        "sermon": {"title": "", "scripture": "", "pastor": "", "content": ""},
        "choir": [],
        "news": [],
        "staff": [],
        "volume": "",
        "issue": ""
    }

    lines = text.split('\n')
    lines = [l.strip() for l in lines if l.strip()]
    full_text = text

    # 성경책 이름 목록 (유효성 검사용)
    BIBLE_BOOKS = [
        '창세기', '출애굽기', '레위기', '민수기', '신명기',
        '여호수아', '사사기', '룻기', '사무엘상', '사무엘하',
        '열왕기상', '열왕기하', '역대상', '역대하', '에스라',
        '느헤미야', '에스더', '욥기', '시편', '잠언', '전도서',
        '아가', '이사야', '예레미야', '예레미야애가', '에스겔',
        '다니엘', '호세아', '요엘', '아모스', '오바댜', '요나',
        '미가', '나훔', '하박국', '스바냐', '학개', '스가랴', '말라기',
        '마태복음', '마가복음', '누가복음', '요한복음', '사도행전',
        '로마서', '고린도전서', '고린도후서', '갈라디아서', '에베소서',
        '빌립보서', '골로새서', '데살로니가전서', '데살로니가후서',
        '디모데전서', '디모데후서', '디도서', '빌레몬서', '히브리서',
        '야고보서', '베드로전서', '베드로후서', '요한1서', '요한2서',
        '요한3서', '유다서', '요한계시록',
        # 약어
        '창', '출', '레', '민', '신', '수', '삿', '룻', '삼상', '삼하',
        '왕상', '왕하', '대상', '대하', '스', '느', '에', '욥', '시', '잠',
        '전', '아', '사', '렘', '애', '겔', '단', '호', '욜', '암', '옵',
        '욘', '미', '나', '합', '습', '학', '슥', '말', '마', '막', '눅',
        '요', '행', '롬', '고전', '고후', '갈', '엡', '빌', '골', '살전',
        '살후', '딤전', '딤후', '딛', '몬', '히', '약', '벧전', '벧후',
        '요일', '요이', '요삼', '유', '계'
    ]

    # ==================== 1. 예배 시간 추출 (1부~5부 형식) ====================
    # "1부 07:00 정정일목사" 형식 파싱 - 중복 제거 및 정렬
    service_pattern = r'(\d)부\s*(\d{1,2}:\d{2})\s*([가-힣]+(?:목사)?)?'
    service_matches = re.findall(service_pattern, full_text)

    seen_services = set()  # 중복 방지
    services_list = []

    for match in service_matches:
        part_num, time_str, leader = match

        # 중복 예배 스킵
        if part_num in seen_services:
            continue
        seen_services.add(part_num)

        hour = int(time_str.split(':')[0])
        time_prefix = "오전" if hour < 12 else "오후"

        services_list.append({
            "part": int(part_num),  # 정렬용
            "name": f"{part_num}부 예배",
            "time": f"{time_prefix} {time_str}",
            "leader": leader.replace("목사", " 목사") if leader else "",
            "items": []
        })

    # 예배 시간순 정렬 (1부, 2부, 3부, 4부, 5부)
    services_list.sort(key=lambda x: x["part"])

    # part 필드 제거 후 결과에 추가
    for service in services_list:
        del service["part"]
    result["worship_services"] = services_list

    # ==================== 2. 설교 제목 추출 (첫 번째 의미있는 제목) ====================
    # 설교 제목 패턴들
    sermon_title_patterns = [
        # "예수님 잘 믿는 기회를 반드시 성취하십시오" 같은 형식
        r'^([가-힣\s]{5,30}(?:하십시오|합니다|입니다|됩니다|시다|세요|하자|합시다))$',
        # "마태복음 11장 11-14절" 앞의 제목
        r'^(.{10,40})\n[가-힣]+\s*\d+장',
        # 설교: 또는 말씀: 뒤의 제목
        r'(?:설교|말씀)[:\s]+[「"\']*([^」"\'\\n]{5,50})[」"\']*',
    ]

    for pattern in sermon_title_patterns:
        match = re.search(pattern, full_text, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # 제목이 너무 길거나 목사 이름이 포함되면 스킵
            if len(title) < 50 and '목사' not in title and '전도사' not in title:
                result["sermon"]["title"] = title
                break

    # 제목을 못 찾으면 첫 줄에서 추출 시도
    if not result["sermon"]["title"]:
        for line in lines[:20]:
            # 한글로 된 적당한 길이의 문장 (제목 후보)
            if 10 <= len(line) <= 50 and re.match(r'^[가-힣\s]+$', line):
                # 목사 이름이나 스태프 리스트가 아닌지 확인
                if '목사' not in line and '전도사' not in line and '찬양대' not in line:
                    result["sermon"]["title"] = line
                    break

    # 설교 제목 정리 - 불필요한 접두사 제거
    if result["sermon"]["title"]:
        title = result["sermon"]["title"]
        # "지난주말씀", "금주말씀", "오늘말씀" 등 접두사 제거
        prefixes_to_remove = ['지난주말씀', '금주말씀', '오늘말씀', '이번주말씀', '말씀:', '설교:']
        for prefix in prefixes_to_remove:
            if title.startswith(prefix):
                title = title[len(prefix):].strip()
        # "「", "」", '"', "'" 제거
        title = re.sub(r'^[「"\']+|[」"\']+$', '', title).strip()
        result["sermon"]["title"] = title

    # ==================== 3. 성경 구절 추출 ====================
    # 성경 구절 패턴 매칭 후 유효성 검사
    scripture_patterns = [
        r'([가-힣]{2,6})\s*(\d{1,3})장?\s*(\d{1,3})[-~]?(\d{1,3})?\s*절?',
        r'본문[:\s]*([가-힣]+)\s*(\d+)[:\s장]*(\d+)[-~]?(\d+)?',
    ]

    for pattern in scripture_patterns:
        matches = re.findall(pattern, full_text)
        for match_groups in matches:
            if len(match_groups) >= 3 and match_groups[1]:
                book = match_groups[0]
                chapter = match_groups[1]
                verse_start = match_groups[2]
                verse_end = match_groups[3] if len(match_groups) > 3 and match_groups[3] else ""

                # 성경책 이름 유효성 검사 - "교회소식" 등 제외
                if book in BIBLE_BOOKS:
                    result["sermon"]["scripture"] = f"{book} {chapter}장 {verse_start}" + (f"-{verse_end}절" if verse_end else "절")
                    break
        if result["sermon"]["scripture"]:
            break

    # ==================== 4. 설교자/담임목사 추출 ====================
    # 더 정확한 패턴으로 목사님 이름 추출
    pastor_patterns = [
        # "김삼환 원로목사" 형식
        r'([가-힣]{2,4})\s*(원로목사|담임목사|위임목사|목사님)',
        # "원로목사 김삼환" 형식
        r'(원로목사|담임목사|위임목사)\s*:?\s*([가-힣]{2,4})',
        # "설교 김삼환 목사" 형식
        r'설교\s*[:\s]*([가-힣]{2,4})\s*목사',
        # "설교자 : 김삼환 목사" 형식
        r'설교자\s*[:\s]*([가-힣]{2,4})\s*목사',
    ]

    # 흔한 목사 이름 (검증용)
    common_pastor_names = ['김삼환', '이영훈', '조용기', '정성진', '정정일', '홍정길', '김장환', '옥한흠']

    for pattern in pastor_patterns:
        match = re.search(pattern, full_text)
        if match:
            groups = match.groups()
            # 이름 찾기 (2-4글자, 직책이 아닌 것)
            for g in groups:
                if g and 2 <= len(g) <= 4 and g not in ['원로목사', '담임목사', '위임목사', '목사님']:
                    # 이름으로 적합한지 검증 (성경이, 예수님 등 제외)
                    invalid_names = ['성경이', '예수님', '하나님', '교회가', '찬양이', '기도가', '말씀이', '예배가']
                    if g not in invalid_names:
                        result["sermon"]["pastor"] = g + " 목사"
                        break
            if result["sermon"]["pastor"]:
                break

    # 흔한 목사 이름으로 직접 검색 (패턴 매칭 실패 시)
    if not result["sermon"]["pastor"]:
        for name in common_pastor_names:
            if name in full_text:
                result["sermon"]["pastor"] = name + " 목사"
                break

    # ==================== 5. 오늘의 말씀 추출 ====================
    verse_patterns = [
        # "말씀" 형식 - 따옴표
        r'"([^"]{10,100})"\s*[(\[]?([가-힣]+\s*\d+[:\s]*\d+[~\-\d]*)[)\]]?',
        r"'([^']{10,100})'\s*[(\[]?([가-힣]+\s*\d+[:\s]*\d+[~\-\d]*)[)\]]?",
        # 「말씀」형식 - 낫표
        r'「([^」]{10,100})」\s*[(\[]?([가-힣]+\s*\d+[:\s]*\d+[~\-\d]*)[)\]]?',
        # 오늘의 말씀: 형식
        r'오늘의?\s*말씀[:\s]+([^가-힣]{0,3})([가-힣가-힣0-9\s,\.]{10,100})\s*[-–—]\s*([가-힣]+\s*\d+[:\s]*\d+[~\-\d]*)',
        # 표어/금주의 말씀 형식
        r'(?:금주의?|이번\s*주)\s*말씀[:\s]+([^가-힣]{0,3})([가-힣가-힣0-9\s,\.]{10,100})\s*[-–—]\s*([가-힣]+\s*\d+[:\s]*\d+[~\-\d]*)',
    ]

    for pattern in verse_patterns:
        match = re.search(pattern, full_text)
        if match:
            groups = match.groups()
            if len(groups) >= 2:
                # 마지막 그룹이 성경 참조인 경우
                if re.match(r'[가-힣]+\s*\d+', groups[-1]):
                    result["today_verse"]["reference"] = groups[-1].strip()
                    # 나머지 그룹을 연결하여 텍스트 생성
                    text_parts = [g.strip() for g in groups[:-1] if g and g.strip()]
                    result["today_verse"]["text"] = " ".join(text_parts).strip()
                else:
                    result["today_verse"]["text"] = groups[0].strip()
                    result["today_verse"]["reference"] = groups[1].strip()
            break

    # 말씀 텍스트가 없으면 설교 본문에서 추출 시도
    if not result["today_verse"]["text"] and result["sermon"]["scripture"]:
        # 성경 구절을 오늘의 말씀 참조로 사용
        result["today_verse"]["reference"] = result["sermon"]["scripture"]

    # ==================== 6. 예배 순서 항목 추출 (상세 내용 포함) ====================
    # 순서대로 정렬된 예배 순서 항목들
    order_items_ordered = [
        ('묵도', 'Silent Prayer', 1),
        ('예배의 부름', 'Call to Worship', 2),
        ('예배선포', 'Declaration', 3),
        ('찬송', 'Hymn', 4),
        ('기도', 'Prayer', 5),
        ('교독문', 'Responsive Reading', 6),
        ('신앙고백', 'Confession of Faith', 7),
        ('사도신경', "Apostles' Creed", 8),
        ('성경봉독', 'Scripture Reading', 9),
        ('찬양', 'Praise', 10),
        ('성가대', 'Choir', 11),
        ('설교', 'Sermon', 12),
        ('봉헌', 'Offering', 13),
        ('헌금', 'Offering', 14),
        ('봉헌기도', 'Offertory Prayer', 15),
        ('대표기도', 'Representative Prayer', 16),
        ('광고', 'Announcements', 17),
        ('축도', 'Benediction', 18),
        ('송영', 'Doxology', 19),
        ('파송', 'Dismissal', 20),
    ]

    found_items = []
    for item_name, item_en, order in order_items_ordered:
        if item_name in full_text:
            # 상세 내용 추출 패턴 (찬송 번호, 담당자 등)
            detail = ""

            # 찬송인 경우 번호 추출 (개선된 패턴)
            if item_name in ['찬송', '송영', '찬양']:
                # 다양한 형식 지원: "찬송 21장", "찬송가 21장", "찬송: 21", "찬 송 21", "*찬송 21장"
                hymn_patterns = [
                    rf'\*?{item_name}\s*[:\s·]*\s*(\d+)\s*장',  # 찬송 21장, *찬송 21장
                    rf'\*?{item_name}가?\s*[:\s·]*\s*(\d+)\s*장',  # 찬송가 21장
                    rf'\*?{item_name}\s*[:\s·]*\s*(\d+)(?!\d)',  # 찬송 21 (번호만)
                    rf'{item_name}\s+(\d+)(?:\s*장)?',  # 찬송 21, 찬송 21장
                    rf'(?:통일)?찬송가?\s*(\d+)\s*장',  # 통일찬송가 21장
                ]
                for hymn_pattern in hymn_patterns:
                    hymn_match = re.search(hymn_pattern, full_text)
                    if hymn_match:
                        detail = f"{hymn_match.group(1)}장"
                        break

            # 성경봉독인 경우 구절 추출
            elif item_name == '성경봉독':
                scripture_pattern = rf'{item_name}\s*[:\s·]*\s*([가-힣]+\s*\d+[:\s장]*\d+[-~\d]*절?)'
                scripture_match = re.search(scripture_pattern, full_text)
                if scripture_match:
                    detail = scripture_match.group(1)
                elif result["sermon"]["scripture"]:
                    detail = result["sermon"]["scripture"]

            # 교독문인 경우 번호 추출
            elif item_name == '교독문':
                responsive_pattern = rf'{item_name}\s*[:\s·]*\s*(\d+)\s*번?'
                responsive_match = re.search(responsive_pattern, full_text)
                if responsive_match:
                    detail = f"{responsive_match.group(1)}번"

            # 담당자 추출 (설교, 기도, 축도 등)
            if item_name in ['설교', '기도', '대표기도', '봉헌기도', '축도', '성경봉독']:
                person_pattern = rf'{item_name}\s*[:\s·]*\s*([가-힣]{{2,4}})\s*(목사|전도사|장로|권사|집사)?'
                person_match = re.search(person_pattern, full_text)
                if person_match:
                    person_name = person_match.group(1)
                    person_title = person_match.group(2) or ""
                    if person_name not in ['성경이', '예수님', '하나님']:
                        detail = f"{person_name} {person_title}".strip()

            # 설교인 경우 목사님 이름 사용
            if item_name == '설교' and not detail and result["sermon"]["pastor"]:
                detail = result["sermon"]["pastor"]

            found_items.append({
                "name": item_name,
                "name_en": item_en,
                "detail": detail,
                "order": order
            })

    # 순서대로 정렬
    found_items.sort(key=lambda x: x["order"])
    # order 필드 제거
    for item in found_items:
        del item["order"]

    # 예배 순서가 있으면 첫 번째 서비스에 추가
    if found_items and result["worship_services"]:
        result["worship_services"][0]["items"] = found_items
    elif found_items:
        result["worship_services"].append({
            "name": "주일예배",
            "time": "오전 11:00",
            "leader": "",
            "items": found_items
        })

    # ==================== 7. 교회 소식 추출 ====================
    news_markers = ['교회소식', '광고', '알림', '공지사항', '안내']
    stop_markers = ['섬기는이들', '목사', '전도사', 'TEL', 'FAX', 'www.', '.or.kr', '.com']

    news_section_started = False
    news_items = []
    current_news = None

    for line in lines:
        # 소식 섹션 시작
        if any(marker in line for marker in news_markers) and len(line) < 15:
            news_section_started = True
            continue

        # 소식 섹션 종료
        if news_section_started and any(marker in line for marker in stop_markers):
            break

        if news_section_started and len(line) > 3:
            # 번호나 기호로 시작하는 새 항목
            if re.match(r'^[0-9①②③④⑤⑥⑦⑧⑨⑩▶►◆●○★☆■□◎※·•\-\d+\.)]', line):
                if current_news:
                    news_items.append(current_news)
                current_news = {"title": line, "content": ""}
            elif current_news and len(line) > 5:
                current_news["content"] += " " + line

    if current_news:
        news_items.append(current_news)

    result["news"] = news_items[:10]

    # ==================== 8. 권/호 추출 ====================
    volume_match = re.search(r'(\d+)\s*권', full_text)
    issue_match = re.search(r'(\d+)\s*호', full_text)
    if volume_match:
        result["volume"] = volume_match.group(1)
    if issue_match:
        result["issue"] = issue_match.group(1)

    # ==================== 9. 지난주 말씀 추출 (개선) ====================
    result["last_week_sermon"] = {
        "title": "",
        "scripture": "",
        "preacher": "",
        "summary": ""
    }

    # 지난주 말씀 제목 추출 패턴
    last_week_title_patterns = [
        r'지난\s*주\s*말씀[:\s·]*["\']?([^"\'\n]{5,80})["\']?',
        r'지난\s*주\s*설교[:\s·]*["\']?([^"\'\n]{5,80})["\']?',
        r'전주\s*말씀[:\s·]*["\']?([^"\'\n]{5,80})["\']?',
        r'지\s*난\s*주[:\s·]*["\']?([^"\'\n]{10,80})["\']?',  # "지 난 주" (OCR 오류)
    ]

    for pattern in last_week_title_patterns:
        match = re.search(pattern, full_text)
        if match:
            title = match.group(1).strip()
            # 성경구절이 포함되어 있으면 분리
            scripture_in_title = re.search(r'[(\[]?([가-힣]+\s*\d+[:\s]*\d+[-~\d]*)[)\]]?', title)
            if scripture_in_title:
                result["last_week_sermon"]["scripture"] = scripture_in_title.group(1)
                title = title.replace(scripture_in_title.group(0), "").strip()
            result["last_week_sermon"]["title"] = title
            break

    # 지난주 말씀 성경구절 별도 추출
    if not result["last_week_sermon"]["scripture"]:
        last_week_scripture_patterns = [
            r'지난\s*주\s*말씀[^가-힣]*([가-힣]+\s*\d+[:\s]*\d+[-~\d]*)',
            r'지난\s*주\s*본문[:\s·]*([가-힣]+\s*\d+[:\s]*\d+[-~\d]*)',
        ]
        for pattern in last_week_scripture_patterns:
            match = re.search(pattern, full_text)
            if match:
                result["last_week_sermon"]["scripture"] = match.group(1).strip()
                break

    # 지난주 설교자 추출
    last_week_preacher_patterns = [
        r'지난\s*주\s*(?:말씀|설교)[^가-힣]*(?:설교[:\s·]*)?([가-힣]{2,4})\s*(?:목사|담임)',
        r'전주\s*설교[:\s·]*([가-힣]{2,4})\s*목사',
    ]
    for pattern in last_week_preacher_patterns:
        match = re.search(pattern, full_text)
        if match:
            result["last_week_sermon"]["preacher"] = match.group(1) + " 목사"
            break

    # 지난주 말씀이 없으면 이전 주일 설교 정보로 대체 시도 (선택적)
    if not result["last_week_sermon"]["title"]:
        # 주보에서 "지난 주일 설교 요약" 또는 유사한 섹션 찾기
        summary_patterns = [
            r'지난\s*주일\s*설교\s*요약[:\s]*([^\n]{20,200})',
            r'전주\s*설교\s*요약[:\s]*([^\n]{20,200})',
        ]
        for pattern in summary_patterns:
            match = re.search(pattern, full_text, re.DOTALL)
            if match:
                result["last_week_sermon"]["summary"] = match.group(1).strip()[:500]
                break

    # ==================== 10. 회차별 기도자/찬양 추출 ====================
    # 명성교회 형식: "기도  1부 임용섭  2부 홍길동  3부 ..."
    prayer_per_service = {}
    hymn_per_service = {}

    # 기도자 추출 패턴: "기도 1부 OOO 2부 OOO ..."
    prayer_line_match = re.search(r'기도\s*[:\s]*((?:[\d부\s]+[가-힣]{2,4}\s*)+)', full_text)
    if prayer_line_match:
        prayer_text = prayer_line_match.group(1)
        prayer_matches = re.findall(r'(\d)\s*부\s*([가-힣]{2,4})', prayer_text)
        for part, name in prayer_matches:
            prayer_per_service[int(part)] = name

    # 찬송 추출 패턴: "찬송 1부 123장 2부 456장 ..."
    hymn_line_match = re.search(r'찬송\s*[:\s]*((?:[\d부장\s]+)+)', full_text)
    if hymn_line_match:
        hymn_text = hymn_line_match.group(1)
        hymn_matches = re.findall(r'(\d)\s*부\s*(\d+)\s*장?', hymn_text)
        for part, hymn_num in hymn_matches:
            hymn_per_service[int(part)] = f"{hymn_num}장"

    # 각 예배에 회차별 기도자/찬양 정보 추가
    for i, service in enumerate(result["worship_services"]):
        part_num = i + 1
        if part_num in prayer_per_service:
            service["prayer_person"] = prayer_per_service[part_num]
        if part_num in hymn_per_service:
            service["hymn"] = hymn_per_service[part_num]

    # ==================== 11. OCR 오류 보정 ====================
    # 명성교회 특수 케이스: "정 일" -> "정정일" (목사 이름)
    ocr_corrections = {
        "정 일 목사": "정정일 목사",
        "정 일목사": "정정일 목사",
        "백재 용": "백재용",
        "김동 진": "김동진",
        "편경 호": "편경호",
        "김영 광": "김영광",
    }

    # 예배 리더 이름 보정
    for service in result["worship_services"]:
        leader = service.get("leader", "")
        for wrong, correct in ocr_corrections.items():
            if wrong in leader:
                service["leader"] = leader.replace(wrong, correct)

    # 설교자 이름 보정
    pastor = result["sermon"].get("pastor", "")
    for wrong, correct in ocr_corrections.items():
        if wrong in pastor:
            result["sermon"]["pastor"] = pastor.replace(wrong, correct)

    return result


@app.post("/api/church-convert")
async def convert_church_bulletin(
    file: UploadFile = File(...),
    church_name: str = Form(...),
    bulletin_date: str = Form(...),
    theme: Optional[str] = Form(default="default")
):
    """
    교회 주보 PDF를 모바일 최적화 HTML로 변환

    Parameters:
    - file: 주보 PDF 파일
    - church_name: 교회명
    - bulletin_date: 주보 날짜 (YYYY-MM-DD)
    - theme: 절기 테마 (default, advent, christmas, lent, easter, pentecost, harvest)

    Returns:
    - success: 성공 여부
    - url: 생성된 HTML 파일 URL
    - filename: 파일명
    - church_name: 교회명
    - bulletin_date: 주보 날짜
    - theme: 적용된 테마
    """
    import os

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 지원됩니다")

    try:
        # 교회 폴더 생성
        church_folder = OUTPUT_DIR / "Church" / church_name
        church_folder.mkdir(parents=True, exist_ok=True)

        # PDF 저장
        job_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_pdf_filename = f"{job_id}_{timestamp}.pdf"
        upload_path = UPLOAD_DIR / safe_pdf_filename

        content = await file.read()
        with open(upload_path, "wb") as f:
            f.write(content)

        # PDF 페이지 수 확인
        page_count = 0
        try:
            import fitz
            doc = fitz.open(str(upload_path))
            page_count = len(doc)
            doc.close()
        except:
            pass

        # 교회 HTML 생성기 사용
        try:
            from church_html_generator import ChurchBulletinGenerator, ChurchConfigManager

            # 교회 프리셋 가져오기 (여의도순복음교회, 명성교회 등 사전 정의된 설정)
            church_info = ChurchConfigManager.get_preset(church_name)
            # 기본값 보완
            if not church_info.get("name"):
                church_info["name"] = church_name

            generator = ChurchConfigManager.create_generator(church_name=church_name, church_info=church_info)

            # PDF에서 텍스트 추출
            extracted_text = ""
            page_texts = []
            try:
                import fitz
                doc = fitz.open(str(upload_path))
                for page in doc:
                    page_text = page.get_text()
                    page_texts.append(page_text)
                    extracted_text += page_text + "\n"
                doc.close()
            except Exception as text_err:
                logger.warning(f"PDF 텍스트 추출 실패: {text_err}")

            # 주보 텍스트 파싱하여 구조화된 데이터 추출
            parsed_data = parse_bulletin_text(extracted_text, church_name)

            # 추출된 데이터 구성
            extracted_data = {
                "date": bulletin_date,
                "volume": parsed_data.get("volume", ""),
                "issue": parsed_data.get("issue", ""),
                "theme": theme,
                "raw_text": extracted_text,
                "pages": [{"text": t} for t in page_texts],
                "structured_data": {
                    "today_verse": parsed_data.get("today_verse", {}),
                    "worship_services": parsed_data.get("worship_services", []),
                    "sermon": parsed_data.get("sermon", {}),
                    "choir": parsed_data.get("choir", []),
                    "news": parsed_data.get("news", [])
                },
                "services": parsed_data.get("worship_services", []),
                "news": parsed_data.get("news", []),
                "sermon": parsed_data.get("sermon", {})
            }

            # HTML 생성
            html_content = generator.generate(extracted_data, title=f"{church_name} 주보", theme=theme)

        except Exception as gen_err:
            logger.warning(f"ChurchBulletinGenerator 사용 실패: {gen_err}, 기본 템플릿 사용")
            # 기본 템플릿 사용
            html_content = generate_basic_church_html(church_name, bulletin_date, theme)

        # HTML 파일 저장
        output_filename = f"{bulletin_date}.html"
        output_path = church_folder / output_filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 자동 검증 시스템 실행
        verification_result = None
        try:
            logger.info(f"교회 주보 자동 검증 시작: {church_name}")
            verification_result = church_bulletin_verifier.verify_church_bulletin(
                original_pdf_path=str(upload_path),
                generated_html_path=str(output_path),
                extracted_data=extracted_data,
                church_name=church_name
            )
            logger.info(f"검증 완료: {verification_result['status']} "
                       f"(오류: {verification_result['statistics']['total_errors']}, "
                       f"경고: {verification_result['statistics']['total_warnings']}, "
                       f"유사도: {verification_result['statistics']['similarity_score']}%)")
        except Exception as verify_err:
            logger.warning(f"검증 실패 (변환은 완료): {verify_err}")
            verification_result = {"status": "error", "message": str(verify_err)}

        # 데이터베이스에 변환 기록 저장
        db_doc_id = None
        if doc_repo and bulletin_repo:
            try:
                import time
                start_time = time.time()

                # 문서 레코드 생성
                db_doc_id = doc_repo.create_document(
                    service_code='church',
                    filename=file.filename,
                    file_path=str(upload_path),
                    file_size=len(content),
                    page_count=page_count,
                    metadata={'church_name': church_name, 'bulletin_date': bulletin_date}
                )

                # 상태 업데이트 (완료)
                processing_time = int((time.time() - start_time) * 1000)
                doc_repo.update_document_status(
                    db_doc_id, 'completed',
                    output_path=str(output_path),
                    processing_time=processing_time
                )

                # 교회 주보 상세 데이터 저장
                bulletin_repo.save_bulletin(
                    doc_id=db_doc_id,
                    church_name=church_name,
                    bulletin_date=bulletin_date,
                    theme=theme,
                    sermon_data=parsed_data.get("sermon", {}),
                    services_data=parsed_data.get("worship_services", []),
                    news_data=parsed_data.get("news", [])
                )

                # 감사 로그
                if audit_logger:
                    audit_logger.log(
                        action='church.convert',
                        resource_type='church_bulletin',
                        resource_id=db_doc_id,
                        is_success=True,
                        response_time_ms=processing_time
                    )

                logger.info(f"주보 변환 DB 저장 완료: doc_id={db_doc_id}")
            except Exception as db_err:
                logger.warning(f"DB 저장 실패 (기능은 정상 동작): {db_err}")

        return JSONResponse({
            "success": True,
            "url": f"/outputs/Church/{church_name}/{output_filename}",
            "filename": output_filename,
            "church_name": church_name,
            "bulletin_date": bulletin_date,
            "theme": theme,
            "page_count": page_count,
            "doc_id": db_doc_id,
            "message": f"{church_name} 주보가 성공적으로 변환되었습니다.",
            "verification": {
                "status": verification_result.get("status", "unknown") if verification_result else "skipped",
                "similarity_score": verification_result.get("statistics", {}).get("similarity_score", 0) if verification_result else 0,
                "errors": verification_result.get("statistics", {}).get("total_errors", 0) if verification_result else 0,
                "warnings": verification_result.get("statistics", {}).get("total_warnings", 0) if verification_result else 0,
                "hallucinations": verification_result.get("statistics", {}).get("hallucination_count", 0) if verification_result else 0,
                "details": verification_result.get("errors", [])[:5] if verification_result else []  # 상위 5개 오류만
            }
        })

    except Exception as e:
        logger.error(f"교회 주보 변환 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"주보 변환 실패: {str(e)}")


# ========== AI 기반 변환 API (Claude Vision) ==========

@app.post("/api/church-convert-ai")
async def convert_church_bulletin_ai(
    file: UploadFile = File(...),
    church_name: str = Form(...),
    bulletin_date: str = Form(...),
    theme: str = Form("default"),
    license_key: Optional[str] = Form(None)
):
    """
    Claude Vision AI를 사용한 교회 주보 PDF 변환

    기존 regex 기반 변환 대신 Claude Vision API로 이미지 분석하여
    고품질 구조화된 데이터 추출 후 HTML 생성

    Args:
        license_key: 라이선스 키 (체험판 사용 시 필수)
    """
    import fitz
    from vision_ocr import VisionOCR

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 지원됩니다")

    # 라이선스 검증 비활성화 (개발 모드)
    # license_check = check_license_and_record_usage(license_key, "church_convert")
    # if license_key and not license_check["valid"]:
    #     raise HTTPException(
    #         status_code=403,
    #         detail=f"라이선스 오류: {license_check['message']}"
    #     )

    try:
        # Vision OCR 초기화
        vision_ocr = VisionOCR()
        if not vision_ocr.client:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY가 설정되지 않았습니다")

        # 교회 폴더 생성
        church_folder = OUTPUT_DIR / "Church" / church_name
        church_folder.mkdir(parents=True, exist_ok=True)

        # PDF 저장
        job_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        upload_path = UPLOAD_DIR / f"{job_id}_{timestamp}.pdf"

        content = await file.read()
        with open(upload_path, "wb") as f:
            f.write(content)

        # PDF 페이지를 이미지로 변환하고 Claude Vision으로 분석
        doc = fitz.open(str(upload_path))
        page_count = len(doc)

        all_extracted_data = []
        combined_text = ""

        logger.info(f"AI 변환 시작: {church_name}, {page_count}페이지")

        for page_num in range(page_count):
            page = doc[page_num]

            # 페이지를 이미지로 변환 (DPI 150)
            mat = fitz.Matrix(150/72, 150/72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("jpeg")

            # Base64 인코딩
            import base64
            image_base64 = base64.b64encode(img_data).decode('utf-8')

            # Claude Vision으로 분석
            logger.info(f"페이지 {page_num + 1}/{page_count} 분석 중...")
            result = vision_ocr.extract_church_bulletin_info(
                image_base64=image_base64,
                media_type="image/jpeg",
                page_number=page_num + 1
            )

            all_extracted_data.append({
                "page": page_num + 1,
                "text": result.get("text", ""),
                "structured": result.get("structured", {})
            })
            combined_text += result.get("text", "") + "\n\n"

        doc.close()

        # 추출된 데이터 통합
        merged_data = _merge_church_bulletin_data(all_extracted_data)

        # 다국어 번역 수행 (선택적 - API 호출 비용 고려)
        try:
            logger.info("다국어 번역 시작...")
            translations = vision_ocr.translate_church_bulletin_content(merged_data)
            merged_data['translations'] = translations
            logger.info(f"번역 완료: {len(translations)} 언어")
        except Exception as trans_error:
            logger.warning(f"번역 실패 (계속 진행): {str(trans_error)}")
            merged_data['translations'] = {}

        # 교회 HTML 생성기 사용
        from church_html_generator import ChurchBulletinGenerator, ChurchConfigManager

        church_info = ChurchConfigManager.get_preset(church_name)
        if not church_info.get("name"):
            church_info["name"] = church_name

        generator = ChurchConfigManager.create_generator(church_name=church_name, church_info=church_info)

        # 추출 데이터 구성
        extracted_data = {
            "date": bulletin_date,
            "volume": merged_data.get("church_info", {}).get("volume", ""),
            "issue": merged_data.get("church_info", {}).get("volume", ""),
            "theme": theme,
            "raw_text": combined_text,
            "ai_extracted": True,  # AI 추출 표시
            "multilingual": True,  # 다국어 지원 활성화
            "translations": merged_data.get("translations", {}),  # 다국어 번역 데이터
            "structured_data": {
                "today_verse": merged_data.get("today_verse", {}),
                "worship_services": merged_data.get("worship_services", []),
                "sermon": merged_data.get("sermon", {}),
                "choir": merged_data.get("choir", []),
                "news": merged_data.get("news", {}),
                "common_order": merged_data.get("common_order", {}),
                "devotional": merged_data.get("devotional", {}),
                "church_info": merged_data.get("church_info", {}),
                "pastors": merged_data.get("pastors", {})
            },
            "worship_services": merged_data.get("worship_services", []),
            "devotional": merged_data.get("devotional", {}),
            "slogan": merged_data.get("church_info", {}).get("slogan", ""),
            "goals": merged_data.get("church_info", {}).get("goals", []),
            "services": merged_data.get("worship_services", []),
            "news": merged_data.get("news", {}),
            "sermon": merged_data.get("sermon", {})
        }

        # HTML 생성
        html_content = generator.generate(extracted_data, title=f"{church_name} 주보", theme=theme)

        # HTML 파일 저장
        output_filename = f"{bulletin_date}.html"
        output_path = church_folder / output_filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"AI 변환 완료: {output_path}")

        # URL 경로 인코딩 (한글 지원)
        from urllib.parse import quote
        encoded_church_name = quote(church_name, safe='')
        encoded_url = f"/outputs/Church/{encoded_church_name}/{output_filename}"

        # 라이선스 정보 추가 (개발 모드: 무제한)
        license_info = {
            "daily_remaining": 9999,
            "message": "개발 모드 - 무제한"
        }

        return JSONResponse({
            "success": True,
            "url": encoded_url,
            "filename": output_filename,
            "church_name": church_name,
            "bulletin_date": bulletin_date,
            "theme": theme,
            "page_count": page_count,
            "ai_powered": True,
            "message": f"{church_name} 주보가 AI로 성공적으로 변환되었습니다.",
            "license": license_info
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI 교회 주보 변환 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI 주보 변환 실패: {str(e)}")


def _merge_church_bulletin_data(pages_data: list) -> dict:
    """여러 페이지의 교회 주보 데이터를 통합 - 상세 버전"""
    merged = {
        "church_info": {"name": "", "english_name": "", "date": "", "volume": "", "slogan": "", "goals": [], "address": "", "phone": ""},
        "pastors": {"senior": "", "associate": []},
        "today_verse": {"text": "", "reference": ""},
        "worship_services": [],
        "common_order": {"invocation": "", "first_hymn": "", "creed": "", "second_hymns": {}, "final_hymn": ""},
        "sermon": {"title": "", "english_title": "", "scripture": "", "pastor": "", "intro": "", "points": [], "author": ""},
        "choir": [],
        "raw_choir_table": {"headers": [], "rows": []},  # 원본 PDF 테이블 형식 보존
        "wednesday_service": {},
        "friday_service": {},
        "saturday_service": {},
        "news": {"worship": [], "recruit": [], "info": []},
        "next_week_prayers": [],
        "raw_prayer_table": {"headers": [], "rows": []},  # 대표기도 원본 테이블
        "devotional": {"title": "", "content": ""},
        "announcements": []
    }

    for page in pages_data:
        structured = page.get("structured", {})

        # 교회 정보 (첫 번째 발견된 것 사용)
        if structured.get("church_info"):
            church_info = structured["church_info"]
            for key in ["name", "english_name", "date", "volume", "slogan", "address", "phone"]:
                if not merged["church_info"].get(key) and church_info.get(key):
                    merged["church_info"][key] = church_info[key]
            if church_info.get("goals") and not merged["church_info"]["goals"]:
                merged["church_info"]["goals"] = church_info["goals"]

        # 목회자 정보
        if structured.get("pastors"):
            pastors = structured["pastors"]
            if not merged["pastors"]["senior"] and pastors.get("senior"):
                merged["pastors"]["senior"] = pastors["senior"]
            if pastors.get("associate") and not merged["pastors"]["associate"]:
                merged["pastors"]["associate"] = pastors["associate"]

        # 오늘의 말씀 (더 긴 텍스트 우선 사용 - 3페이지 본문이 1페이지 요약보다 정확함)
        new_verse = structured.get("today_verse", {})
        if new_verse.get("text"):
            current_text = merged["today_verse"].get("text", "")
            new_text = new_verse.get("text", "")
            # 새 텍스트가 더 길거나, 기존 텍스트가 없으면 교체
            if len(new_text) > len(current_text) or not current_text:
                merged["today_verse"]["text"] = new_text
            # 출처(reference)는 새 것이 있으면 항상 업데이트
            if new_verse.get("reference"):
                merged["today_verse"]["reference"] = new_verse["reference"]

        # 공통 순서
        if structured.get("common_order"):
            common = structured["common_order"]
            for key in ["invocation", "first_hymn", "creed", "final_hymn"]:
                if not merged["common_order"].get(key) and common.get(key):
                    merged["common_order"][key] = common[key]

        # 예배 순서 합치기 (중복 제거)
        if structured.get("worship_services"):
            for service in structured["worship_services"]:
                # 이름으로 중복 체크
                service_name = service.get("name", "")
                existing = [s for s in merged["worship_services"] if s.get("name") == service_name]
                if not existing:
                    merged["worship_services"].append(service)
                else:
                    # 기존 서비스에 누락된 정보 보완
                    existing_service = existing[0]
                    for key in service.keys():
                        if service.get(key) and not existing_service.get(key):
                            existing_service[key] = service[key]

        # 설교 (내용 합침)
        if structured.get("sermon"):
            sermon = structured["sermon"]
            for key in ["title", "english_title", "scripture", "author", "intro"]:
                if not merged["sermon"].get(key) and sermon.get(key):
                    merged["sermon"][key] = sermon[key]
            if sermon.get("points"):
                merged["sermon"]["points"].extend(sermon["points"])
            # 이전 형식 호환 (pastor -> author)
            if not merged["sermon"]["author"] and sermon.get("pastor"):
                merged["sermon"]["author"] = sermon["pastor"]

        # 찬양대 합치기 (중복 제거)
        if structured.get("choir"):
            for choir in structured["choir"]:
                service_name = choir.get("service", "")
                existing = [c for c in merged["choir"] if c.get("service") == service_name]
                if not existing:
                    merged["choir"].append(choir)

        # 원본 PDF 테이블 데이터 병합 (첫 번째 유효한 것 사용)
        if structured.get("raw_choir_table"):
            raw_table = structured["raw_choir_table"]
            if raw_table.get("headers") and not merged["raw_choir_table"]["headers"]:
                merged["raw_choir_table"]["headers"] = raw_table["headers"]
            if raw_table.get("rows") and not merged["raw_choir_table"]["rows"]:
                merged["raw_choir_table"]["rows"] = raw_table["rows"]

        # 소식 합치기 (카테고리별)
        if structured.get("news"):
            news = structured["news"]
            if isinstance(news, dict):
                for category in ["worship", "recruit", "info"]:
                    if news.get(category):
                        merged["news"][category].extend(news[category])
            elif isinstance(news, list):
                # 이전 형식 호환
                merged["news"]["info"].extend(news)

        # 대표기도 원본 테이블 병합
        if structured.get("raw_prayer_table"):
            raw_table = structured["raw_prayer_table"]
            if raw_table.get("headers") and not merged["raw_prayer_table"]["headers"]:
                merged["raw_prayer_table"]["headers"] = raw_table["headers"]
            if raw_table.get("rows") and not merged["raw_prayer_table"]["rows"]:
                merged["raw_prayer_table"]["rows"] = raw_table["rows"]

        # 오늘의 양식
        if structured.get("devotional"):
            devotional = structured["devotional"]
            if not merged["devotional"]["title"] and devotional.get("title"):
                merged["devotional"]["title"] = devotional["title"]
            if not merged["devotional"]["content"] and devotional.get("content"):
                merged["devotional"]["content"] = devotional["content"]

        # 광고 합치기
        if structured.get("announcements"):
            merged["announcements"].extend(structured["announcements"])

    return merged


@app.post("/api/lecture-convert-ai")
async def convert_lecture_ai(
    file: UploadFile = File(...),
    title: str = Form(""),
    instructor: str = Form(""),
    output_format: str = Form("html")
):
    """
    Claude Vision AI를 사용한 강의 자료 PDF 변환
    """
    import fitz
    from vision_ocr import VisionOCR

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 지원됩니다")

    try:
        vision_ocr = VisionOCR()
        if not vision_ocr.client:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY가 설정되지 않았습니다")

        # PDF 저장
        job_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        upload_path = UPLOAD_DIR / f"{job_id}_{timestamp}.pdf"

        content = await file.read()
        with open(upload_path, "wb") as f:
            f.write(content)

        # PDF 분석
        doc = fitz.open(str(upload_path))
        page_count = len(doc)

        all_pages = []

        logger.info(f"강의 AI 변환 시작: {page_count}페이지")

        for page_num in range(page_count):
            page = doc[page_num]
            mat = fitz.Matrix(150/72, 150/72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("jpeg")

            import base64
            image_base64 = base64.b64encode(img_data).decode('utf-8')

            logger.info(f"페이지 {page_num + 1}/{page_count} 분석 중...")
            result = vision_ocr.extract_lecture_info(
                image_base64=image_base64,
                media_type="image/jpeg",
                page_number=page_num + 1
            )

            all_pages.append({
                "page": page_num + 1,
                "text": result.get("text", ""),
                "structured": result.get("structured", {})
            })

        doc.close()

        # 강의 데이터 통합
        merged_data = _merge_lecture_data(all_pages)

        # 제목/강사 오버라이드
        if title:
            merged_data["title"] = title
        if instructor:
            merged_data["instructor"]["name"] = instructor

        # HTML 생성
        from lecture_generator import LectureGenerator

        generator = LectureGenerator()
        html_content = generator.generate({
            "title": merged_data.get("title", "강의 자료"),
            "subtitle": merged_data.get("subtitle", ""),
            "instructor": merged_data.get("instructor", {}),
            "learning_objectives": merged_data.get("learning_objectives", []),
            "sections": merged_data.get("sections", []),
            "key_terms": merged_data.get("key_terms", []),
            "questions": merged_data.get("questions", []),
            "ai_extracted": True
        })

        # 파일 저장
        output_filename = f"{job_id}_{timestamp}.html"
        output_path = OUTPUT_DIR / output_filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"강의 AI 변환 완료: {output_path}")

        return JSONResponse({
            "success": True,
            "url": f"/outputs/{output_filename}",
            "filename": output_filename,
            "page_count": page_count,
            "ai_powered": True,
            "extracted_data": merged_data,
            "message": "강의 자료가 AI로 성공적으로 변환되었습니다."
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"강의 AI 변환 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"강의 AI 변환 실패: {str(e)}")


def _merge_lecture_data(pages_data: list) -> dict:
    """여러 페이지의 강의 데이터를 통합"""
    merged = {
        "title": "",
        "subtitle": "",
        "instructor": {"name": "", "affiliation": "", "contact": ""},
        "learning_objectives": [],
        "sections": [],
        "tables": [],
        "key_terms": [],
        "questions": []
    }

    for page in pages_data:
        structured = page.get("structured", {})

        # 제목 (첫 번째 발견된 것)
        if not merged["title"] and structured.get("title"):
            merged["title"] = structured["title"]
        if not merged["subtitle"] and structured.get("subtitle"):
            merged["subtitle"] = structured["subtitle"]

        # 강사 정보
        if structured.get("instructor"):
            inst = structured["instructor"]
            if not merged["instructor"]["name"] and inst.get("name"):
                merged["instructor"]["name"] = inst["name"]
            if not merged["instructor"]["affiliation"] and inst.get("affiliation"):
                merged["instructor"]["affiliation"] = inst["affiliation"]

        # 학습 목표 합치기
        if structured.get("learning_objectives"):
            merged["learning_objectives"].extend(structured["learning_objectives"])

        # 섹션 합치기
        if structured.get("sections"):
            merged["sections"].extend(structured["sections"])

        # 표 합치기
        if structured.get("tables"):
            merged["tables"].extend(structured["tables"])

        # 핵심 용어 합치기
        if structured.get("key_terms"):
            merged["key_terms"].extend(structured["key_terms"])

        # 질문 합치기
        if structured.get("questions"):
            merged["questions"].extend(structured["questions"])

    return merged


@app.post("/api/newsletter-convert-ai")
async def convert_newsletter_ai(
    file: UploadFile = File(...),
    publisher: str = Form(""),
    issue: str = Form("")
):
    """
    Claude Vision AI를 사용한 뉴스레터 PDF 변환
    """
    import fitz
    from vision_ocr import VisionOCR

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 지원됩니다")

    try:
        vision_ocr = VisionOCR()
        if not vision_ocr.client:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY가 설정되지 않았습니다")

        job_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        upload_path = UPLOAD_DIR / f"{job_id}_{timestamp}.pdf"

        content = await file.read()
        with open(upload_path, "wb") as f:
            f.write(content)

        doc = fitz.open(str(upload_path))
        page_count = len(doc)

        all_pages = []

        logger.info(f"뉴스레터 AI 변환 시작: {page_count}페이지")

        for page_num in range(page_count):
            page = doc[page_num]
            mat = fitz.Matrix(150/72, 150/72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("jpeg")

            import base64
            image_base64 = base64.b64encode(img_data).decode('utf-8')

            logger.info(f"페이지 {page_num + 1}/{page_count} 분석 중...")
            result = vision_ocr.extract_newsletter_info(
                image_base64=image_base64,
                media_type="image/jpeg",
                page_number=page_num + 1
            )

            all_pages.append({
                "page": page_num + 1,
                "text": result.get("text", ""),
                "structured": result.get("structured", {})
            })

        doc.close()

        # 뉴스레터 데이터 통합
        merged_data = _merge_newsletter_data(all_pages)

        # 오버라이드
        if publisher:
            merged_data["publisher"] = publisher
        if issue:
            merged_data["issue"] = issue

        # HTML 생성
        html_content = _generate_newsletter_html(merged_data)

        output_filename = f"{job_id}_{timestamp}_newsletter.html"
        output_path = OUTPUT_DIR / output_filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"뉴스레터 AI 변환 완료: {output_path}")

        return JSONResponse({
            "success": True,
            "url": f"/outputs/{output_filename}",
            "filename": output_filename,
            "page_count": page_count,
            "ai_powered": True,
            "extracted_data": merged_data,
            "message": "뉴스레터가 AI로 성공적으로 변환되었습니다."
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"뉴스레터 AI 변환 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"뉴스레터 AI 변환 실패: {str(e)}")


def _merge_newsletter_data(pages_data: list) -> dict:
    """여러 페이지의 뉴스레터 데이터를 통합"""
    merged = {
        "publisher": "",
        "issue": "",
        "date": "",
        "headline": {"title": "", "subtitle": "", "content": ""},
        "articles": [],
        "events": [],
        "announcements": [],
        "ads": []
    }

    for page in pages_data:
        structured = page.get("structured", {})

        if not merged["publisher"] and structured.get("publisher"):
            merged["publisher"] = structured["publisher"]
        if not merged["issue"] and structured.get("issue"):
            merged["issue"] = structured["issue"]
        if not merged["date"] and structured.get("date"):
            merged["date"] = structured["date"]

        if not merged["headline"]["title"] and structured.get("headline", {}).get("title"):
            merged["headline"] = structured["headline"]

        if structured.get("articles"):
            merged["articles"].extend(structured["articles"])
        if structured.get("events"):
            merged["events"].extend(structured["events"])
        if structured.get("announcements"):
            merged["announcements"].extend(structured["announcements"])
        if structured.get("ads"):
            merged["ads"].extend(structured["ads"])

    return merged


def _generate_newsletter_html(data: dict) -> str:
    """뉴스레터 HTML 생성"""
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data.get('publisher', '뉴스레터')} - {data.get('issue', '')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Pretendard', -apple-system, sans-serif; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 20px; text-align: center; }}
        .header h1 {{ font-size: 2rem; margin-bottom: 10px; }}
        .header .issue {{ font-size: 1rem; opacity: 0.9; }}
        .headline {{ padding: 30px 20px; background: #f8f9fa; border-bottom: 3px solid #667eea; }}
        .headline h2 {{ font-size: 1.5rem; color: #333; margin-bottom: 10px; }}
        .headline .subtitle {{ color: #666; font-size: 1rem; margin-bottom: 15px; }}
        .headline .content {{ color: #444; line-height: 1.8; }}
        .articles {{ padding: 20px; }}
        .article {{ background: white; border: 1px solid #eee; border-radius: 8px; padding: 20px; margin-bottom: 15px; }}
        .article h3 {{ color: #333; font-size: 1.2rem; margin-bottom: 8px; }}
        .article .category {{ display: inline-block; background: #667eea; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8rem; margin-bottom: 10px; }}
        .article .summary {{ color: #666; margin-bottom: 10px; font-style: italic; }}
        .article .content {{ color: #444; line-height: 1.7; }}
        .events {{ background: #fff3cd; padding: 20px; }}
        .events h3 {{ color: #856404; margin-bottom: 15px; }}
        .events ul {{ list-style: none; }}
        .events li {{ padding: 8px 0; border-bottom: 1px solid #ffc107; }}
        .announcements {{ background: #e3f2fd; padding: 20px; }}
        .announcements h3 {{ color: #1565c0; margin-bottom: 15px; }}
        .announcements ul {{ list-style: disc; margin-left: 20px; }}
        .announcements li {{ padding: 5px 0; color: #333; }}
        .footer {{ background: #333; color: white; padding: 20px; text-align: center; }}
        .ai-badge {{ background: #10b981; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.75rem; display: inline-block; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>{data.get('publisher', '뉴스레터')}</h1>
            <div class="issue">{data.get('issue', '')} {data.get('date', '')}</div>
            <span class="ai-badge">🤖 AI Powered</span>
        </header>
"""

    # 헤드라인
    headline = data.get("headline", {})
    if headline.get("title"):
        html += f"""
        <section class="headline">
            <h2>{headline.get('title', '')}</h2>
            <p class="subtitle">{headline.get('subtitle', '')}</p>
            <p class="content">{headline.get('content', '')}</p>
        </section>
"""

    # 기사들
    articles = data.get("articles", [])
    if articles:
        html += '<section class="articles">'
        for article in articles:
            html += f"""
            <article class="article">
                <span class="category">{article.get('category', '기사')}</span>
                <h3>{article.get('title', '')}</h3>
                <p class="summary">{article.get('summary', '')}</p>
                <p class="content">{article.get('content', '')}</p>
            </article>
"""
        html += '</section>'

    # 이벤트
    events = data.get("events", [])
    if events:
        html += '<section class="events"><h3>📅 이벤트/일정</h3><ul>'
        for event in events:
            html += f'<li>{event}</li>'
        html += '</ul></section>'

    # 공지사항
    announcements = data.get("announcements", [])
    if announcements:
        html += '<section class="announcements"><h3>📢 공지사항</h3><ul>'
        for ann in announcements:
            html += f'<li>{ann}</li>'
        html += '</ul></section>'

    html += """
        <footer class="footer">
            <p>© 2024 All rights reserved</p>
            <p style="font-size: 0.8rem; margin-top: 5px;">Generated with Claude Vision AI</p>
        </footer>
    </div>
</body>
</html>"""

    return html


@app.post("/api/catalog-convert-ai")
async def convert_catalog_ai(
    file: UploadFile = File(...),
    company: str = Form(""),
    category: str = Form("")
):
    """
    Claude Vision AI를 사용한 카탈로그/브로셔 PDF 변환
    """
    import fitz
    from vision_ocr import VisionOCR

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 지원됩니다")

    try:
        vision_ocr = VisionOCR()
        if not vision_ocr.client:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY가 설정되지 않았습니다")

        job_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        upload_path = UPLOAD_DIR / f"{job_id}_{timestamp}.pdf"

        content = await file.read()
        with open(upload_path, "wb") as f:
            f.write(content)

        doc = fitz.open(str(upload_path))
        page_count = len(doc)

        all_pages = []

        logger.info(f"카탈로그 AI 변환 시작: {page_count}페이지")

        for page_num in range(page_count):
            page = doc[page_num]
            mat = fitz.Matrix(150/72, 150/72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("jpeg")

            import base64
            image_base64 = base64.b64encode(img_data).decode('utf-8')

            logger.info(f"페이지 {page_num + 1}/{page_count} 분석 중...")
            result = vision_ocr.extract_catalog_info(
                image_base64=image_base64,
                media_type="image/jpeg",
                page_number=page_num + 1
            )

            all_pages.append({
                "page": page_num + 1,
                "text": result.get("text", ""),
                "structured": result.get("structured", {})
            })

        doc.close()

        # 카탈로그 데이터 통합
        merged_data = _merge_catalog_data(all_pages)

        # 오버라이드
        if company:
            merged_data["company"] = company
        if category:
            merged_data["category"] = category

        # HTML 생성
        html_content = _generate_catalog_html(merged_data)

        output_filename = f"{job_id}_{timestamp}_catalog.html"
        output_path = OUTPUT_DIR / output_filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"카탈로그 AI 변환 완료: {output_path}")

        return JSONResponse({
            "success": True,
            "url": f"/outputs/{output_filename}",
            "filename": output_filename,
            "page_count": page_count,
            "ai_powered": True,
            "extracted_data": merged_data,
            "message": "카탈로그가 AI로 성공적으로 변환되었습니다."
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"카탈로그 AI 변환 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"카탈로그 AI 변환 실패: {str(e)}")


def _merge_catalog_data(pages_data: list) -> dict:
    """여러 페이지의 카탈로그 데이터를 통합"""
    merged = {
        "company": "",
        "catalog_title": "",
        "category": "",
        "products": [],
        "company_info": {"name": "", "description": "", "history": "", "vision": ""},
        "contact": {"address": "", "phone": "", "email": "", "website": "", "sns": ""},
        "other_info": {}
    }

    for page in pages_data:
        structured = page.get("structured", {})

        if not merged["company"] and structured.get("company"):
            merged["company"] = structured["company"]
        if not merged["catalog_title"] and structured.get("catalog_title"):
            merged["catalog_title"] = structured["catalog_title"]
        if not merged["category"] and structured.get("category"):
            merged["category"] = structured["category"]

        if structured.get("products"):
            merged["products"].extend(structured["products"])

        if structured.get("company_info"):
            ci = structured["company_info"]
            for key in ["name", "description", "history", "vision"]:
                if not merged["company_info"][key] and ci.get(key):
                    merged["company_info"][key] = ci[key]

        if structured.get("contact"):
            contact = structured["contact"]
            for key in ["address", "phone", "email", "website", "sns"]:
                if not merged["contact"][key] and contact.get(key):
                    merged["contact"][key] = contact[key]

    return merged


def _generate_catalog_html(data: dict) -> str:
    """카탈로그 HTML 생성"""
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data.get('company', '카탈로그')} - {data.get('catalog_title', '')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Pretendard', -apple-system, sans-serif; background: #f0f0f0; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; }}
        .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 50px 20px; text-align: center; }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
        .header .subtitle {{ font-size: 1.2rem; opacity: 0.9; }}
        .header .category {{ background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; display: inline-block; margin-top: 15px; }}
        .products {{ padding: 30px 20px; display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}
        .product {{ border: 1px solid #ddd; border-radius: 12px; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s; }}
        .product:hover {{ transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
        .product-img {{ height: 200px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; color: white; font-size: 3rem; }}
        .product-info {{ padding: 20px; }}
        .product h3 {{ color: #333; font-size: 1.2rem; margin-bottom: 8px; }}
        .product .price {{ color: #e53e3e; font-size: 1.3rem; font-weight: bold; margin-bottom: 10px; }}
        .product .description {{ color: #666; font-size: 0.9rem; margin-bottom: 15px; line-height: 1.6; }}
        .product .features {{ background: #f7fafc; padding: 12px; border-radius: 8px; }}
        .product .features ul {{ list-style: none; }}
        .product .features li {{ padding: 4px 0; color: #4a5568; font-size: 0.85rem; }}
        .product .features li:before {{ content: "✓ "; color: #48bb78; }}
        .company-info {{ background: #1a1a2e; color: white; padding: 40px 20px; }}
        .company-info h2 {{ margin-bottom: 20px; }}
        .company-info p {{ line-height: 1.8; opacity: 0.9; }}
        .contact {{ background: #f8f9fa; padding: 30px 20px; }}
        .contact h2 {{ color: #333; margin-bottom: 20px; }}
        .contact-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .contact-item {{ background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; }}
        .contact-item .label {{ color: #666; font-size: 0.85rem; }}
        .contact-item .value {{ color: #333; font-weight: 500; margin-top: 5px; }}
        .footer {{ background: #333; color: white; padding: 20px; text-align: center; }}
        .ai-badge {{ background: #10b981; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.75rem; }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>{data.get('company', '카탈로그')}</h1>
            <p class="subtitle">{data.get('catalog_title', '')}</p>
            <span class="category">{data.get('category', '')}</span>
            <br><span class="ai-badge" style="margin-top: 15px;">🤖 AI Powered</span>
        </header>
"""

    # 제품 목록
    products = data.get("products", [])
    if products:
        html += '<section class="products">'
        for i, product in enumerate(products):
            html += f"""
            <div class="product">
                <div class="product-img">📦</div>
                <div class="product-info">
                    <h3>{product.get('name', f'제품 {i+1}')}</h3>
                    <p class="price">{product.get('price', '')}</p>
                    <p class="description">{product.get('description', '')}</p>
"""
            if product.get("features"):
                html += '<div class="features"><ul>'
                for feat in product["features"]:
                    html += f'<li>{feat}</li>'
                html += '</ul></div>'
            html += '</div></div>'
        html += '</section>'

    # 회사 정보
    company_info = data.get("company_info", {})
    if company_info.get("description"):
        html += f"""
        <section class="company-info">
            <h2>회사 소개</h2>
            <p>{company_info.get('description', '')}</p>
            <p style="margin-top: 10px;">{company_info.get('vision', '')}</p>
        </section>
"""

    # 연락처
    contact = data.get("contact", {})
    if any(contact.values()):
        html += '<section class="contact"><h2>연락처</h2><div class="contact-grid">'
        if contact.get("address"):
            html += f'<div class="contact-item"><div class="label">📍 주소</div><div class="value">{contact["address"]}</div></div>'
        if contact.get("phone"):
            html += f'<div class="contact-item"><div class="label">📞 전화</div><div class="value">{contact["phone"]}</div></div>'
        if contact.get("email"):
            html += f'<div class="contact-item"><div class="label">📧 이메일</div><div class="value">{contact["email"]}</div></div>'
        if contact.get("website"):
            html += f'<div class="contact-item"><div class="label">🌐 웹사이트</div><div class="value">{contact["website"]}</div></div>'
        html += '</div></section>'

    html += """
        <footer class="footer">
            <p>© 2024 All rights reserved</p>
            <p style="font-size: 0.8rem; margin-top: 5px;">Generated with Claude Vision AI</p>
        </footer>
    </div>
</body>
</html>"""

    return html


@app.post("/api/election-convert-ai")
async def convert_election_ai(
    file: UploadFile = File(...),
    save_folder: str = Form(""),
    create_images_folder: bool = Form(False)
):
    """
    Claude Vision AI를 사용한 선거 공보물 PDF 변환
    """
    import fitz
    from vision_ocr import VisionOCR

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 지원됩니다")

    try:
        vision_ocr = VisionOCR()
        if not vision_ocr.client:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY가 설정되지 않았습니다")

        job_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        upload_path = UPLOAD_DIR / f"{job_id}_{timestamp}.pdf"

        content = await file.read()
        with open(upload_path, "wb") as f:
            f.write(content)

        doc = fitz.open(str(upload_path))
        page_count = len(doc)

        all_pages = []
        page_images = []

        logger.info(f"선거공보물 AI 변환 시작: {page_count}페이지")

        # 저장 경로 설정
        if save_folder:
            save_path = OUTPUT_DIR / save_folder
            save_path.mkdir(parents=True, exist_ok=True)
            if create_images_folder:
                images_path = save_path / "images"
                images_path.mkdir(exist_ok=True)
        else:
            save_path = OUTPUT_DIR
            images_path = None

        for page_num in range(page_count):
            page = doc[page_num]
            mat = fitz.Matrix(150/72, 150/72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("jpeg")

            import base64
            image_base64 = base64.b64encode(img_data).decode('utf-8')

            # 이미지 저장 (옵션)
            if images_path:
                img_filename = f"page_{page_num + 1}.jpg"
                with open(images_path / img_filename, "wb") as f:
                    f.write(img_data)
                page_images.append(f"images/{img_filename}")
            else:
                page_images.append(f"data:image/jpeg;base64,{image_base64[:50]}...")

            logger.info(f"페이지 {page_num + 1}/{page_count} 분석 중...")
            result = vision_ocr.extract_election_info(
                image_base64=image_base64,
                media_type="image/jpeg",
                page_number=page_num + 1
            )

            all_pages.append({
                "page": page_num + 1,
                "text": result.get("text", ""),
                "structured": result.get("structured", {})
            })

        doc.close()

        # 선거 공보물 데이터 통합
        merged_data = _merge_election_data(all_pages)
        merged_data["page_images"] = page_images

        # HTML 생성
        html_content = _generate_election_html(merged_data, page_count)

        output_filename = f"{job_id}_{timestamp}_election.html"
        output_path = save_path / output_filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"선거공보물 AI 변환 완료: {output_path}")

        # URL 경로 설정
        if save_folder:
            url = f"/outputs/{save_folder}/{output_filename}"
        else:
            url = f"/outputs/{output_filename}"

        return JSONResponse({
            "success": True,
            "result": {
                "url": url,
                "filename": output_filename,
                "candidate": {
                    "name": merged_data.get("candidate_name", ""),
                    "party": merged_data.get("party", "")
                },
                "statistics": {
                    "page_count": page_count,
                    "pledge_count": len(merged_data.get("pledges", []))
                }
            },
            "ai_powered": True,
            "message": "선거공보물이 AI로 성공적으로 변환되었습니다."
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"선거공보물 AI 변환 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"선거공보물 AI 변환 실패: {str(e)}")


def _merge_election_data(pages_data: list) -> dict:
    """여러 페이지의 선거공보물 데이터를 통합"""
    merged = {
        "candidate_name": "",
        "candidate_number": "",
        "party": "",
        "position": "",
        "district": "",
        "slogan": "",
        "pledges": [],
        "career": [],
        "education": [],
        "contact": {"phone": "", "email": "", "website": "", "sns": []},
        "photo_description": ""
    }

    for page in pages_data:
        structured = page.get("structured", {})

        # 기본 정보 (첫 번째로 발견된 값 사용)
        if not merged["candidate_name"] and structured.get("candidate_name"):
            merged["candidate_name"] = structured["candidate_name"]
        if not merged["candidate_number"] and structured.get("candidate_number"):
            merged["candidate_number"] = structured["candidate_number"]
        if not merged["party"] and structured.get("party"):
            merged["party"] = structured["party"]
        if not merged["position"] and structured.get("position"):
            merged["position"] = structured["position"]
        if not merged["district"] and structured.get("district"):
            merged["district"] = structured["district"]
        if not merged["slogan"] and structured.get("slogan"):
            merged["slogan"] = structured["slogan"]

        # 공약 (누적)
        if structured.get("pledges"):
            for pledge in structured["pledges"]:
                if pledge not in merged["pledges"]:
                    merged["pledges"].append(pledge)

        # 경력 (누적)
        if structured.get("career"):
            for item in structured["career"]:
                if item not in merged["career"]:
                    merged["career"].append(item)

        # 학력 (누적)
        if structured.get("education"):
            for item in structured["education"]:
                if item not in merged["education"]:
                    merged["education"].append(item)

        # 연락처
        if structured.get("contact"):
            contact = structured["contact"]
            if not merged["contact"]["phone"] and contact.get("phone"):
                merged["contact"]["phone"] = contact["phone"]
            if not merged["contact"]["email"] and contact.get("email"):
                merged["contact"]["email"] = contact["email"]
            if not merged["contact"]["website"] and contact.get("website"):
                merged["contact"]["website"] = contact["website"]
            if contact.get("sns"):
                for sns in contact["sns"]:
                    if sns not in merged["contact"]["sns"]:
                        merged["contact"]["sns"].append(sns)

    return merged


def _generate_election_html(data: dict, page_count: int) -> str:
    """선거 공보물 HTML 생성"""
    party = data.get("party", "")

    # 정당별 색상
    party_colors = {
        "더불어민주당": {"primary": "#004EA2", "secondary": "#0066CC", "bg": "#E6F0FF"},
        "민주당": {"primary": "#004EA2", "secondary": "#0066CC", "bg": "#E6F0FF"},
        "국민의힘": {"primary": "#E61E2B", "secondary": "#FF3344", "bg": "#FFE6E8"},
        "개혁신당": {"primary": "#FF6600", "secondary": "#FF8533", "bg": "#FFF0E6"},
        "조국혁신당": {"primary": "#003366", "secondary": "#004080", "bg": "#E6ECF2"},
        "진보당": {"primary": "#D6001C", "secondary": "#E6001F", "bg": "#FFE6E9"},
        "녹색정의당": {"primary": "#006400", "secondary": "#008000", "bg": "#E6F5E6"},
        "무소속": {"primary": "#666666", "secondary": "#888888", "bg": "#F5F5F5"}
    }

    colors = party_colors.get(party, {"primary": "#667eea", "secondary": "#764ba2", "bg": "#f0f4ff"})

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data.get('candidate_name', '후보자')} - {data.get('position', '선거공보')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Pretendard', -apple-system, 'Noto Sans KR', sans-serif; background: #f5f5f5; }}
        .container {{ max-width: 500px; margin: 0 auto; background: white; min-height: 100vh; }}

        .header {{
            background: linear-gradient(135deg, {colors['primary']} 0%, {colors['secondary']} 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .candidate-number {{
            display: inline-block;
            width: 60px;
            height: 60px;
            background: white;
            color: {colors['primary']};
            font-size: 2rem;
            font-weight: bold;
            border-radius: 50%;
            line-height: 60px;
            margin-bottom: 15px;
        }}
        .candidate-name {{ font-size: 2rem; font-weight: bold; margin-bottom: 8px; }}
        .party-badge {{
            background: rgba(255,255,255,0.2);
            padding: 5px 15px;
            border-radius: 20px;
            display: inline-block;
            margin-bottom: 10px;
        }}
        .position {{ font-size: 1.1rem; opacity: 0.9; }}
        .slogan {{
            background: {colors['bg']};
            color: {colors['primary']};
            padding: 20px;
            text-align: center;
            font-size: 1.2rem;
            font-weight: 600;
            border-left: 4px solid {colors['primary']};
        }}

        .section {{ padding: 25px 20px; border-bottom: 1px solid #eee; }}
        .section-title {{
            color: {colors['primary']};
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .pledge-list {{ list-style: none; }}
        .pledge-item {{
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            margin-bottom: 10px;
            border-left: 4px solid {colors['primary']};
        }}
        .pledge-item h4 {{ color: #333; margin-bottom: 5px; }}
        .pledge-item p {{ color: #666; font-size: 0.9rem; }}

        .career-item, .education-item {{
            padding: 10px 0;
            border-bottom: 1px dashed #eee;
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }}
        .career-item:last-child, .education-item:last-child {{ border-bottom: none; }}
        .career-item::before {{ content: "▪"; color: {colors['primary']}; }}
        .education-item::before {{ content: "🎓"; }}

        .contact-grid {{ display: grid; gap: 10px; }}
        .contact-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .contact-item a {{ color: {colors['primary']}; text-decoration: none; }}

        .footer {{
            background: #333;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 0.85rem;
        }}
        .ai-badge {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75rem;
            display: inline-block;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="candidate-number">{data.get('candidate_number', '?')}</div>
            <div class="party-badge">{data.get('party', '정당')}</div>
            <h1 class="candidate-name">{data.get('candidate_name', '후보자')}</h1>
            <p class="position">{data.get('position', '')} {data.get('district', '')}</p>
            <span class="ai-badge">🤖 AI 분석</span>
        </header>
"""

    if data.get("slogan"):
        html += f'<div class="slogan">"{data["slogan"]}"</div>'

    # 공약
    pledges = data.get("pledges", [])
    if pledges:
        html += '''
        <section class="section">
            <h2 class="section-title">📋 핵심 공약</h2>
            <ul class="pledge-list">
'''
        for i, pledge in enumerate(pledges, 1):
            if isinstance(pledge, dict):
                title = pledge.get("title", f"공약 {i}")
                desc = pledge.get("description", "")
                html += f'''
                <li class="pledge-item">
                    <h4>{i}. {title}</h4>
                    <p>{desc}</p>
                </li>
'''
            else:
                html += f'''
                <li class="pledge-item">
                    <h4>{i}. {pledge}</h4>
                </li>
'''
        html += '</ul></section>'

    # 경력
    career = data.get("career", [])
    if career:
        html += '''
        <section class="section">
            <h2 class="section-title">💼 주요 경력</h2>
'''
        for item in career:
            html += f'<div class="career-item">{item}</div>'
        html += '</section>'

    # 학력
    education = data.get("education", [])
    if education:
        html += '''
        <section class="section">
            <h2 class="section-title">📚 학력</h2>
'''
        for item in education:
            html += f'<div class="education-item">{item}</div>'
        html += '</section>'

    # 연락처
    contact = data.get("contact", {})
    if contact.get("phone") or contact.get("email") or contact.get("website"):
        html += '''
        <section class="section">
            <h2 class="section-title">📞 연락처</h2>
            <div class="contact-grid">
'''
        if contact.get("phone"):
            html += f'<div class="contact-item">📞 <a href="tel:{contact["phone"]}">{contact["phone"]}</a></div>'
        if contact.get("email"):
            html += f'<div class="contact-item">📧 <a href="mailto:{contact["email"]}">{contact["email"]}</a></div>'
        if contact.get("website"):
            html += f'<div class="contact-item">🌐 <a href="{contact["website"]}" target="_blank">{contact["website"]}</a></div>'
        html += '</div></section>'

    html += f'''
        <footer class="footer">
            <p>이 자료는 선거공보를 기반으로 AI가 자동 생성하였습니다.</p>
            <p style="margin-top: 8px; opacity: 0.7;">총 {page_count}페이지 분석 | Claude Vision AI</p>
        </footer>
    </div>
</body>
</html>'''

    return html


# ========== AI 변환 API 끝 ==========


@app.post("/api/church-verify")
async def verify_church_bulletin_endpoint(
    pdf_file: UploadFile = File(...),
    html_path: str = Form(...),
    church_name: str = Form(...)
):
    """
    교회 주보 변환 결과 수동 검증 API

    원본 PDF와 생성된 HTML을 비교하여 검증 결과 반환:
    - 오타/탈자 검사
    - 환각(hallucination) 검사 - 원본에 없는 내용이 추가되었는지
    - 누락 검사 - 원본 내용이 빠졌는지
    - 유사도 점수
    """
    try:
        # PDF 임시 저장
        temp_pdf = UPLOAD_DIR / f"verify_{uuid.uuid4().hex[:8]}.pdf"
        content = await pdf_file.read()
        with open(temp_pdf, "wb") as f:
            f.write(content)

        # HTML 경로 확인
        full_html_path = OUTPUT_DIR / html_path.lstrip("/outputs/")
        if not full_html_path.exists():
            raise HTTPException(status_code=404, detail=f"HTML 파일을 찾을 수 없습니다: {html_path}")

        # 검증 실행
        result = church_bulletin_verifier.verify_church_bulletin(
            original_pdf_path=str(temp_pdf),
            generated_html_path=str(full_html_path),
            extracted_data={},
            church_name=church_name
        )

        # 리포트 생성
        report = church_bulletin_verifier.generate_report(result)

        # 임시 파일 삭제
        temp_pdf.unlink(missing_ok=True)

        return JSONResponse({
            "success": True,
            "verification": result,
            "report": report
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"검증 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"검증 실패: {str(e)}")


@app.get("/api/church-verify/{church_name}/{date}")
async def verify_existing_bulletin(
    church_name: str,
    date: str,
    pdf_path: str = None
):
    """
    기존 변환된 주보 검증 (PDF 경로 지정 시)

    예: /api/church-verify/명성교회/2025-12-07?pdf_path=C:/Users/.../20251207.pdf
    """
    try:
        # HTML 파일 경로
        html_path = OUTPUT_DIR / "Church" / church_name / f"{date}.html"
        if not html_path.exists():
            raise HTTPException(status_code=404, detail=f"HTML 파일을 찾을 수 없습니다: {html_path}")

        if not pdf_path:
            return JSONResponse({
                "success": False,
                "message": "검증을 위해 원본 PDF 경로(pdf_path)를 지정해주세요.",
                "html_exists": True,
                "html_path": str(html_path)
            })

        # PDF 파일 확인
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise HTTPException(status_code=404, detail=f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

        # 검증 실행
        result = church_bulletin_verifier.verify_church_bulletin(
            original_pdf_path=str(pdf_file),
            generated_html_path=str(html_path),
            extracted_data={},
            church_name=church_name
        )

        # 리포트 생성
        report = church_bulletin_verifier.generate_report(result)

        return JSONResponse({
            "success": True,
            "verification": result,
            "report": report
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"검증 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"검증 실패: {str(e)}")


def generate_basic_church_html(church_name: str, bulletin_date: str, theme: str = "default") -> str:
    """교회별 프리셋을 적용한 풍부한 주보 HTML 템플릿 생성"""

    # 교회별 프리셋 정의
    CHURCH_PRESETS = {
        "명성교회": {
            "primary": "#1E3A5F",
            "primary_dark": "#152A45",
            "primary_light": "#E8EEF4",
            "accent": "#C9A857",
            "accent_light": "#F5EED8",
            "font_style": "serif",
            "letter_spacing": "8px",
            "name_en": "MYUNGSUNG CHURCH",
            "style": "elegant"
        },
        "여의도순복음교회": {
            "primary": "#5B4B9E",
            "primary_dark": "#4A3D82",
            "primary_light": "#E8E4F4",
            "accent": "#C9A857",
            "accent_light": "#F5EED8",
            "font_style": "sans-serif",
            "letter_spacing": "2px",
            "name_en": "YOIDO FULL GOSPEL CHURCH",
            "style": "modern"
        },
        "혈동교회": {
            "primary": "#8B4513",
            "primary_dark": "#5D3A1A",
            "primary_light": "#FDF8F0",
            "accent": "#C5A572",
            "accent_light": "#FAF5EB",
            "font_style": "serif",
            "letter_spacing": "4px",
            "name_en": "HYULDONG CHURCH",
            "style": "traditional"
        }
    }

    # 절기별 테마 색상
    THEME_COLORS = {
        "default": {"theme_color": None, "theme_light": None, "badge": None, "icon": "📖"},
        "advent": {"theme_color": "#4A0D67", "theme_light": "#E8D5F0", "badge": "대림절", "icon": "🕯️"},
        "christmas": {"theme_color": "#C41E3A", "theme_light": "#FFE4E1", "badge": "성탄절", "icon": "🎄"},
        "lent": {"theme_color": "#4B0082", "theme_light": "#E6E0F0", "badge": "사순절", "icon": "✝️"},
        "easter": {"theme_color": "#FFD700", "theme_light": "#FFFACD", "badge": "부활절", "icon": "🌸"},
        "pentecost": {"theme_color": "#DC143C", "theme_light": "#FFE4E1", "badge": "성령강림절", "icon": "🔥"},
        "harvest": {"theme_color": "#8B6914", "theme_light": "#FEF3C7", "badge": "추수감사절", "icon": "🌾"}
    }

    # 교회 프리셋 가져오기 (없으면 기본값)
    preset = CHURCH_PRESETS.get(church_name, {
        "primary": "#5B4B9E",
        "primary_dark": "#4A3D82",
        "primary_light": "#E8E4F4",
        "accent": "#C9A857",
        "accent_light": "#F5EED8",
        "font_style": "sans-serif",
        "letter_spacing": "2px",
        "name_en": "",
        "style": "modern"
    })

    theme_info = THEME_COLORS.get(theme, THEME_COLORS["default"])

    # 테마가 있으면 테마 색상 오버라이드
    primary = theme_info["theme_color"] if theme_info["theme_color"] else preset["primary"]
    primary_light = theme_info["theme_light"] if theme_info["theme_light"] else preset["primary_light"]

    # 폰트 스타일
    font_family = "'Noto Serif KR', serif" if preset["font_style"] == "serif" else "'Noto Sans KR', sans-serif"

    # 테마 배지
    theme_badge_html = ""
    if theme_info["badge"]:
        theme_badge_html = f'''
            <div class="theme-badge">
                <span>{theme_info["icon"]}</span> {theme_info["badge"]}
            </div>'''

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=5.0">
    <title>{church_name} 주보 - {bulletin_date}</title>
    <meta name="description" content="{church_name} {bulletin_date} 주보">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="{church_name}">
    <meta name="theme-color" content="{primary}">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700;800&family=Noto+Serif+KR:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: {primary};
            --primary-dark: {preset["primary_dark"]};
            --primary-light: {primary_light};
            --accent: {preset["accent"]};
            --accent-light: {preset["accent_light"]};
            --text-dark: #1a1a2e;
            --text-gray: #6B7280;
            --bg-gray: #F8F9FA;
            --border: #E5E7EB;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
        html {{ scroll-behavior: smooth; }}
        body {{
            font-family: {font_family};
            background: var(--bg-gray);
            color: var(--text-dark);
            line-height: 1.6;
            min-height: 100vh;
        }}
        .header {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 24px 20px;
            padding-top: calc(env(safe-area-inset-top, 20px) + 20px);
            text-align: center;
            position: relative;
        }}
        .theme-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(255,255,255,0.2);
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        .church-name {{
            font-family: 'Noto Serif KR', serif;
            font-size: 2em;
            font-weight: 700;
            letter-spacing: {preset["letter_spacing"]};
            margin-bottom: 6px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        .church-name-en {{
            font-size: 0.5em;
            font-weight: 400;
            letter-spacing: 2px;
            opacity: 0.85;
            display: block;
            margin-top: 4px;
        }}
        .jubo-date {{
            font-size: 1em;
            opacity: 0.9;
            margin-top: 8px;
        }}
        .nav-tabs {{
            background: white;
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            z-index: 999;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }}
        .nav-tabs::-webkit-scrollbar {{ display: none; }}
        .nav-tabs-inner {{
            display: flex;
            max-width: 600px;
            margin: 0 auto;
            padding: 0 8px;
            justify-content: space-around;
        }}
        .nav-tab {{
            flex: 1;
            padding: 12px 8px;
            font-size: 0.85em;
            font-weight: 600;
            color: var(--text-gray);
            text-decoration: none;
            border-bottom: 3px solid transparent;
            white-space: nowrap;
            transition: all 0.2s;
            text-align: center;
        }}
        .nav-tab.active, .nav-tab:hover {{
            color: var(--primary);
            border-bottom-color: var(--primary);
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 16px;
            padding-bottom: 100px;
        }}
        .verse-card {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 16px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        .verse-card::before {{
            content: '{theme_info["icon"]}';
            position: absolute;
            font-size: 4em;
            opacity: 0.15;
            top: -10px;
            right: -10px;
        }}
        .verse-label {{ font-size: 0.85em; opacity: 0.9; margin-bottom: 12px; }}
        .verse-text {{
            font-family: 'Noto Serif KR', serif;
            font-size: 1.1em;
            line-height: 1.9;
            font-weight: 500;
            margin-bottom: 16px;
            position: relative;
            z-index: 1;
        }}
        .verse-ref {{
            font-size: 0.9em;
            background: rgba(255,255,255,0.2);
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            cursor: pointer;
        }}
        .section {{
            background: white;
            border-radius: 16px;
            margin-bottom: 16px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.04);
            overflow: hidden;
        }}
        .section-header {{
            background: linear-gradient(135deg, var(--primary-light) 0%, white 100%);
            padding: 14px 18px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .section-icon {{ font-size: 1.3em; }}
        .section-title {{
            font-size: 1.05em;
            font-weight: 700;
            color: var(--primary);
        }}
        .section-body {{ padding: 18px; }}
        .worship-info {{ padding: 12px; background: var(--bg-gray); border-radius: 10px; margin-bottom: 12px; }}
        .worship-time {{ font-weight: 700; color: var(--primary); margin-bottom: 4px; }}
        .sermon-card {{
            background: linear-gradient(135deg, var(--accent-light) 0%, white 100%);
            border: 1px solid var(--accent);
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 16px;
        }}
        .sermon-title {{
            font-family: 'Noto Serif KR', serif;
            font-size: 1.2em;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 8px;
        }}
        .sermon-scripture {{ font-size: 0.9em; color: var(--text-gray); margin-bottom: 4px; }}
        .sermon-preacher {{ font-weight: 600; }}
        .btn-group {{
            display: flex;
            gap: 10px;
            margin-top: 16px;
        }}
        .btn {{
            flex: 1;
            padding: 12px;
            border: 1px solid var(--primary);
            background: white;
            color: var(--primary);
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.9em;
            cursor: pointer;
            text-decoration: none;
            text-align: center;
            transition: all 0.2s;
        }}
        .btn:hover {{ background: var(--primary); color: white; }}
        .btn.primary {{ background: var(--primary); color: white; }}
        .btn.primary:hover {{ background: var(--primary-dark); }}
        .offering-section {{
            background: linear-gradient(135deg, #E8F5E9 0%, white 100%);
            border: 2px dashed #4CAF50;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            margin-bottom: 16px;
        }}
        .offering-title {{ font-weight: 700; color: #2E7D32; margin-bottom: 8px; }}
        .share-section {{
            background: white;
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            margin-bottom: 16px;
        }}
        .share-buttons {{ display: flex; gap: 12px; justify-content: center; margin-top: 12px; }}
        .share-btn {{
            flex: 1;
            max-width: 140px;
            padding: 12px;
            border-radius: 10px;
            border: 1px solid var(--border);
            background: white;
            font-weight: 600;
            cursor: pointer;
        }}
        .share-btn.kakao {{ background: #FEE500; border-color: #FEE500; }}
        .dark-mode-toggle {{
            position: fixed;
            top: 80px;
            right: 16px;
            background: white;
            border: 1px solid var(--border);
            border-radius: 50%;
            width: 44px;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2em;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            z-index: 998;
        }}
        .footer {{
            background: var(--primary);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .footer-logo {{ font-size: 1.2em; font-weight: 700; margin-bottom: 8px; }}
        .footer-copyright {{ font-size: 0.75em; opacity: 0.7; margin-top: 12px; }}
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7);
            z-index: 2000;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .modal-overlay.active {{ display: flex; }}
        .modal-content {{
            background: white;
            border-radius: 16px;
            max-width: 500px;
            width: 100%;
            max-height: 80vh;
            overflow-y: auto;
        }}
        .modal-header {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 16px 20px;
            border-radius: 16px 16px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .modal-close {{
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            font-size: 1.2em;
            cursor: pointer;
        }}
        .modal-body {{ padding: 20px; line-height: 1.9; }}
        body.dark-mode {{
            --bg-gray: #1a1a2e;
            --text-dark: #ffffff;
            --text-gray: #a0a0b0;
            --border: #3a3a50;
            --primary-light: #3a3a50;
        }}
        body.dark-mode .section, body.dark-mode .share-section,
        body.dark-mode .nav-tabs, body.dark-mode .dark-mode-toggle {{
            background: #252540;
        }}
        @media (max-width: 375px) {{
            .church-name {{ font-size: 1.6em; letter-spacing: 4px; }}
            .nav-tab {{ padding: 10px 6px; font-size: 0.8em; }}
        }}
    </style>
</head>
<body>
    <header class="header">{theme_badge_html}
        <h1 class="church-name">
            {church_name}
            <span class="church-name-en">{preset["name_en"]}</span>
        </h1>
        <div class="jubo-date">{bulletin_date}</div>
    </header>

    <nav class="nav-tabs">
        <div class="nav-tabs-inner">
            <a href="#verse" class="nav-tab active">말씀</a>
            <a href="#worship" class="nav-tab">예배</a>
            <a href="#sermon" class="nav-tab">설교</a>
            <a href="#news" class="nav-tab">소식</a>
            <a href="#offering" class="nav-tab">헌금</a>
        </div>
    </nav>

    <button class="dark-mode-toggle" onclick="toggleDarkMode()">🌙</button>

    <main class="container">
        <section id="verse" class="verse-card">
            <div class="verse-label">오늘의 말씀</div>
            <p class="verse-text">"주의 말씀은 내 발에 등이요 내 길에 빛이니이다"</p>
            <span class="verse-ref" onclick="openBibleModal()">📖 시편 119:105</span>
        </section>

        <section class="sermon-card">
            <div style="font-size: 0.8em; color: var(--accent); font-weight: 600; margin-bottom: 6px;">📖 오늘의 설교</div>
            <div class="sermon-title">은혜의 말씀</div>
            <div class="sermon-scripture">본문: 말씀 준비 중</div>
            <div class="sermon-preacher">설교: 담임목사</div>
            <div class="btn-group">
                <button class="btn" onclick="openHymnModal()">🎵 찬송가</button>
                <a href="#" class="btn primary">🎧 설교 듣기</a>
            </div>
        </section>

        <section id="worship" class="section">
            <div class="section-header">
                <span class="section-icon">⛪</span>
                <h2 class="section-title">예배 안내</h2>
            </div>
            <div class="section-body">
                <div class="worship-info">
                    <div class="worship-time">주일 1부 예배 07:00</div>
                    <div>장소: 본당</div>
                </div>
                <div class="worship-info">
                    <div class="worship-time">주일 2부 예배 09:30</div>
                    <div>장소: 본당</div>
                </div>
                <div class="worship-info">
                    <div class="worship-time">주일 3부 예배 11:00</div>
                    <div>장소: 본당</div>
                </div>
            </div>
        </section>

        <section id="sermon" class="section">
            <div class="section-header">
                <span class="section-icon">📖</span>
                <h2 class="section-title">생명의 말씀</h2>
            </div>
            <div class="section-body">
                <p style="color: var(--text-gray); text-align: center;">설교 내용은 예배 후 업데이트됩니다.</p>
                <div class="btn-group" style="margin-top: 20px;">
                    <a href="#" class="btn">⬇️ 설교 다운로드</a>
                    <a href="#" class="btn primary">▶️ 설교 영상</a>
                </div>
            </div>
        </section>

        <section id="news" class="section">
            <div class="section-header">
                <span class="section-icon">📢</span>
                <h2 class="section-title">교회 소식</h2>
            </div>
            <div class="section-body">
                <p style="color: var(--text-gray); text-align: center;">교회 소식이 업데이트됩니다.</p>
            </div>
        </section>

        <section id="offering" class="offering-section">
            <div class="offering-title">💰 모바일 헌금 안내</div>
            <p style="font-size: 0.9em; color: var(--text-gray); margin-bottom: 12px;">
                온라인으로 편리하게 헌금하실 수 있습니다
            </p>
            <button class="btn primary" style="max-width: 200px;" onclick="alert('모바일 헌금 페이지로 이동합니다.')">
                💳 헌금하기
            </button>
        </section>

        <div class="share-section">
            <div style="font-weight: 600; margin-bottom: 4px;">주보를 공유해 보세요</div>
            <div class="share-buttons">
                <button class="share-btn kakao" onclick="shareKakao()">카카오톡</button>
                <button class="share-btn" onclick="shareLink()">링크 복사</button>
            </div>
        </div>
    </main>

    <footer class="footer">
        <div class="footer-logo">{church_name}</div>
        <div style="font-size: 0.85em; opacity: 0.9;">{preset["name_en"]}</div>
        <div class="footer-copyright">© 2025 {church_name}. All rights reserved.<br>StudySnap으로 생성됨</div>
    </footer>

    <div class="modal-overlay" id="bibleModal">
        <div class="modal-content">
            <div class="modal-header">
                <span>📖 성경 말씀</span>
                <button class="modal-close" onclick="closeModal('bibleModal')">✕</button>
            </div>
            <div class="modal-body">
                <p><strong>시편 119:105</strong></p>
                <p>주의 말씀은 내 발에 등이요 내 길에 빛이니이다</p>
            </div>
        </div>
    </div>

    <div class="modal-overlay" id="hymnModal">
        <div class="modal-content">
            <div class="modal-header" style="background: linear-gradient(135deg, #D97706 0%, #B45309 100%);">
                <span>🎵 찬송가</span>
                <button class="modal-close" onclick="closeModal('hymnModal')">✕</button>
            </div>
            <div class="modal-body" style="text-align: center;">
                <div style="font-size: 2em; font-weight: 800; color: #D97706;">1장</div>
                <div style="font-size: 1.2em; font-weight: 700; margin: 8px 0;">만복의 근원 하나님</div>
                <div style="text-align: left; white-space: pre-line; line-height: 1.8;">
1. 만복의 근원 하나님
   온 천하 만물 주관해
   천사와 모든 천군아
   다 찬송 높이 드리세

2. 인류를 구원하신 주
   천국 문 열어 주셨네
   성부와 성자 성령께
   영원토록 영광 돌리세
                </div>
            </div>
        </div>
    </div>

    <script>
        function toggleDarkMode() {{
            document.body.classList.toggle('dark-mode');
            const btn = document.querySelector('.dark-mode-toggle');
            btn.textContent = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
        }}
        function openBibleModal() {{ document.getElementById('bibleModal').classList.add('active'); }}
        function openHymnModal() {{ document.getElementById('hymnModal').classList.add('active'); }}
        function closeModal(id) {{ document.getElementById(id).classList.remove('active'); }}
        document.querySelectorAll('.modal-overlay').forEach(m => m.addEventListener('click', e => {{ if(e.target === m) m.classList.remove('active'); }}));
        function shareKakao() {{
            if(navigator.share) {{ navigator.share({{ title: '{church_name} 주보', text: '{bulletin_date} 주보', url: location.href }}); }}
            else {{ alert('카카오톡 공유는 모바일에서 이용 가능합니다.'); }}
        }}
        function shareLink() {{ navigator.clipboard.writeText(location.href).then(() => alert('링크가 복사되었습니다.')); }}
        document.querySelectorAll('a[href^="#"]').forEach(a => a.addEventListener('click', e => {{
            e.preventDefault();
            const t = document.querySelector(a.getAttribute('href'));
            if(t) window.scrollTo({{ top: t.offsetTop - 60, behavior: 'smooth' }});
        }}));
    </script>
</body>
</html>'''


@app.post("/api/batch-convert")
async def batch_convert_elections(
    files: List[UploadFile] = File(...)
):
    """
    다중 파일 일괄 자동 변환 API

    여러 PDF를 한번에 업로드하여 일괄 변환합니다.

    Parameters:
    - files: PDF 파일 목록 (최대 20개)

    Returns:
    - success: 성공 여부
    - results: 각 파일별 변환 결과
    """
    if auto_converter is None:
        raise HTTPException(
            status_code=500,
            detail="자동화 변환기가 초기화되지 않았습니다"
        )

    if len(files) > 20:
        raise HTTPException(status_code=400, detail="한번에 최대 20개 파일만 처리 가능합니다")

    results = []
    success_count = 0
    fail_count = 0

    for file in files:
        job_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            if not file.filename.lower().endswith('.pdf'):
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": "PDF 파일만 지원됩니다"
                })
                fail_count += 1
                continue

            content = await file.read()

            # 파일 저장
            safe_filename = f"{job_id}_{timestamp}.pdf"
            upload_path = UPLOAD_DIR / safe_filename

            with open(upload_path, "wb") as f:
                f.write(content)

            # 자동 변환
            brochure = auto_converter.convert(str(upload_path))
            html_content = auto_converter.generate_html(brochure)

            # 출력 저장
            if brochure.candidate.name:
                output_filename = f"{brochure.candidate.name}_{timestamp}.html"
            else:
                output_filename = f"AUTO_{job_id}_{timestamp}.html"

            output_path = OUTPUT_DIR / output_filename

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            # 임시 파일 정리
            cleanup_temp_files(job_id=job_id, keep_outputs=True)

            results.append({
                "filename": file.filename,
                "success": True,
                "output_url": f"/outputs/{output_filename}",
                "candidate_name": brochure.candidate.name,
                "party": brochure.candidate.party
            })
            success_count += 1

        except Exception as e:
            logger.error(f"일괄 변환 오류 ({file.filename}): {str(e)}")
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })
            fail_count += 1

    return JSONResponse({
        "success": True,
        "message": f"일괄 변환 완료: 성공 {success_count}개, 실패 {fail_count}개",
        "statistics": {
            "total": len(files),
            "success": success_count,
            "failed": fail_count
        },
        "results": results
    })


# ============================================
# AI 채팅 기반 HTML 편집 API
# ============================================

from pydantic import BaseModel
from typing import List, Optional

class ChatEditRequest(BaseModel):
    message: str
    html: str
    history: Optional[List[dict]] = []

class ChatEditResponse(BaseModel):
    success: bool
    response: str
    html: Optional[str] = None
    error: Optional[str] = None

# 대화 학습 데이터 저장 경로
CHAT_LEARNING_DIR = BASE_DIR / "learning_data" / "chat_history"
CHAT_LEARNING_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/api/chat/edit")
async def chat_edit_html(request: ChatEditRequest):
    """
    AI 대화 기반 HTML 편집 API

    사용자의 자연어 요청을 받아 HTML을 수정하고 결과를 반환합니다.
    대화 내용은 학습 데이터로 저장됩니다.
    """
    try:
        from anthropic import Anthropic

        client = Anthropic()

        # 시스템 프롬프트
        system_prompt = """당신은 교회 주보 HTML 편집 전문 AI입니다.

사용자의 요청에 따라 HTML을 수정합니다.

**규칙:**
1. 사용자가 수정을 요청하면, 수정된 전체 HTML을 <modified_html> 태그 안에 반환하세요.
2. 수정 내용을 간단히 설명하세요.
3. HTML 구조를 깨뜨리지 마세요.
4. 한국어 텍스트는 정확하게 유지하세요.
5. CSS 스타일은 기존 것을 최대한 유지하세요.

**응답 형식:**
수정 내용 설명

<modified_html>
(수정된 전체 HTML)
</modified_html>

또는 수정이 필요 없는 질문이면 그냥 답변만 하세요."""

        # 대화 히스토리 구성
        messages = []
        for h in request.history[-10:]:  # 최근 10개만
            messages.append({
                "role": h.get("role", "user"),
                "content": h.get("content", "")
            })

        # 현재 HTML과 사용자 메시지
        user_content = f"""**현재 HTML:**
```html
{request.html[:50000]}
```

**사용자 요청:**
{request.message}"""

        messages.append({
            "role": "user",
            "content": user_content
        })

        # Claude API 호출
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16384,
            system=system_prompt,
            messages=messages
        )

        ai_response = response.content[0].text

        # 수정된 HTML 추출
        modified_html = None
        if "<modified_html>" in ai_response and "</modified_html>" in ai_response:
            start = ai_response.find("<modified_html>") + len("<modified_html>")
            end = ai_response.find("</modified_html>")
            modified_html = ai_response[start:end].strip()
            # 응답에서 HTML 태그 제거
            clean_response = ai_response[:ai_response.find("<modified_html>")].strip()
        else:
            clean_response = ai_response

        # 학습 데이터 저장
        try:
            chat_log = {
                "timestamp": datetime.now().isoformat(),
                "user_message": request.message,
                "ai_response": clean_response,
                "html_modified": modified_html is not None,
                "html_length_before": len(request.html),
                "html_length_after": len(modified_html) if modified_html else len(request.html)
            }

            log_file = CHAT_LEARNING_DIR / f"chat_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(chat_log, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"채팅 로그 저장 실패: {e}")

        return JSONResponse({
            "success": True,
            "response": clean_response,
            "html": modified_html
        })

    except Exception as e:
        logger.error(f"AI 채팅 편집 오류: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e),
            "response": f"오류가 발생했습니다: {str(e)}"
        })


@app.get("/api/chat/history")
async def get_chat_history(date: str = None, limit: int = 100):
    """
    채팅 학습 히스토리 조회 API
    """
    try:
        if date:
            log_file = CHAT_LEARNING_DIR / f"chat_{date}.jsonl"
            if not log_file.exists():
                return JSONResponse({"success": True, "history": [], "count": 0})

            history = []
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        history.append(json.loads(line))

            return JSONResponse({
                "success": True,
                "history": history[-limit:],
                "count": len(history)
            })
        else:
            # 모든 날짜의 히스토리 파일 목록
            files = sorted(CHAT_LEARNING_DIR.glob("chat_*.jsonl"), reverse=True)
            dates = [f.stem.replace("chat_", "") for f in files]

            return JSONResponse({
                "success": True,
                "available_dates": dates,
                "total_files": len(dates)
            })

    except Exception as e:
        logger.error(f"채팅 히스토리 조회 오류: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@app.get("/api/chat/insights")
async def get_chat_insights():
    """
    채팅 학습 데이터 분석 - 자주 요청되는 수정 패턴 분석
    """
    try:
        all_history = []

        for log_file in CHAT_LEARNING_DIR.glob("chat_*.jsonl"):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        all_history.append(json.loads(line))

        if not all_history:
            return JSONResponse({
                "success": True,
                "total_conversations": 0,
                "insights": {}
            })

        # 통계 분석
        total = len(all_history)
        modified_count = sum(1 for h in all_history if h.get("html_modified"))

        # 자주 사용되는 키워드 분석
        keywords = {}
        for h in all_history:
            msg = h.get("user_message", "").lower()
            for word in ["바꿔", "변경", "수정", "추가", "삭제", "제목", "설교", "찬송", "예배", "목사", "시간"]:
                if word in msg:
                    keywords[word] = keywords.get(word, 0) + 1

        return JSONResponse({
            "success": True,
            "total_conversations": total,
            "html_modifications": modified_count,
            "modification_rate": round(modified_count / total * 100, 1) if total > 0 else 0,
            "common_keywords": dict(sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:10]),
            "insights": {
                "description": "사용자들이 자주 요청하는 수정 패턴을 분석한 결과입니다.",
                "recommendation": "자주 요청되는 패턴은 자동화 기능으로 추가할 수 있습니다."
            }
        })

    except Exception as e:
        logger.error(f"채팅 인사이트 분석 오류: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


# ============================================
# 데이터베이스 통계 및 조회 API
# ============================================

@app.get("/api/db/stats")
async def get_db_statistics(service: Optional[str] = None):
    """변환 통계 조회"""
    if not doc_repo:
        return JSONResponse({
            "success": False,
            "error": "데이터베이스가 초기화되지 않았습니다"
        })

    try:
        stats = doc_repo.get_statistics(service)
        return JSONResponse({
            "success": True,
            "service": service or "all",
            "statistics": stats
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@app.get("/api/db/documents")
async def get_recent_documents(service: Optional[str] = None, limit: int = 50):
    """최근 변환 문서 목록 조회"""
    if not doc_repo:
        return JSONResponse({
            "success": False,
            "error": "데이터베이스가 초기화되지 않았습니다"
        })

    try:
        documents = doc_repo.get_recent_documents(service, limit)
        return JSONResponse({
            "success": True,
            "count": len(documents),
            "documents": documents
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@app.get("/api/db/churches")
async def get_church_list():
    """등록된 교회 목록 조회"""
    if not bulletin_repo:
        return JSONResponse({
            "success": False,
            "error": "데이터베이스가 초기화되지 않았습니다"
        })

    try:
        churches = bulletin_repo.get_churches()
        return JSONResponse({
            "success": True,
            "count": len(churches),
            "churches": churches
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@app.get("/api/db/church/{church_name}/bulletins")
async def get_church_bulletins(church_name: str, limit: int = 20):
    """특정 교회의 주보 목록 조회"""
    if not bulletin_repo:
        return JSONResponse({
            "success": False,
            "error": "데이터베이스가 초기화되지 않았습니다"
        })

    try:
        bulletins = bulletin_repo.get_church_bulletins(church_name, limit)
        return JSONResponse({
            "success": True,
            "church_name": church_name,
            "count": len(bulletins),
            "bulletins": bulletins
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@app.get("/api/db/services")
async def get_services():
    """등록된 서비스 목록 조회"""
    if not db_manager:
        return JSONResponse({
            "success": False,
            "error": "데이터베이스가 초기화되지 않았습니다"
        })

    try:
        services = db_manager.execute("SELECT * FROM services WHERE is_active = 1")
        return JSONResponse({
            "success": True,
            "count": len(services),
            "services": services
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


# ========== FGFC 전용 검증 API ==========

@app.post("/api/fgfc/verify")
async def verify_fgfc_bulletin(
    ocr_data: dict = None,
    html_content: str = Form(None),
    html_path: str = Form(None)
):
    """
    여의도순복음교회 전용 주보 검증 API

    - OCR 추출 데이터 검증
    - HTML 출력물과 원본 비교
    - 자동 교정 제안
    """
    try:
        from church_bulletin_verifier import verify_bulletin, get_bulletin_verifier

        # HTML 파일에서 읽기 (경로 제공 시)
        html_text = html_content
        if html_path and not html_content:
            full_path = OUTPUT_DIR / html_path.lstrip("/outputs/")
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    html_text = f.read()

        # 검증 실행
        result = verify_bulletin(ocr_data or {}, html_text)

        return JSONResponse({
            "success": True,
            **result
        })

    except Exception as e:
        logger.error(f"FGFC 검증 실패: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/api/fgfc/template")
async def get_fgfc_template():
    """여의도순복음교회 전용 템플릿 조회"""
    try:
        template_path = Path(__file__).parent / "learning_data/church_bulletin/fgfc_template.json"

        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
            return JSONResponse({
                "success": True,
                "template": template
            })
        else:
            return JSONResponse({
                "success": False,
                "error": "템플릿 파일을 찾을 수 없습니다"
            }, status_code=404)

    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.post("/api/fgfc/auto-correct")
async def auto_correct_fgfc_data(ocr_data: dict):
    """
    FGFC 주보 데이터 자동 교정

    - 오타 수정
    - 형식 정규화
    - 누락 데이터 추정
    """
    try:
        from church_bulletin_verifier import get_bulletin_verifier

        verifier = get_bulletin_verifier()
        corrected_data, corrections = verifier.auto_correct(ocr_data)

        return JSONResponse({
            "success": True,
            "original": ocr_data,
            "corrected": corrected_data,
            "corrections": corrections,
            "correction_count": len(corrections)
        })

    except Exception as e:
        logger.error(f"자동 교정 실패: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


# 서버 실행 (개발용)
if __name__ == "__main__":
    import uvicorn

    print("=" * 50)
    print("StudySnap Backend Server")
    print("=" * 50)
    print(f"Upload Directory: {UPLOAD_DIR}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print("=" * 50)

    # 서버 시작 시 24시간 이상 된 임시 파일 자동 정리
    print("\n[INFO] Cleaning up temp files...")
    try:
        deleted_files = cleanup_temp_files(
            job_id=None,
            keep_outputs=True,
            cleanup_old_files=True,
            max_age_hours=24
        )
        if deleted_files:
            print(f"[OK] Deleted {len(deleted_files)} old temp files")
        else:
            print("[OK] No temp files to clean")
    except Exception as e:
        print(f"[WARNING] Cleanup failed: {str(e)}")

    print("=" * 50)
    print("[INFO] Starting server...")
    print("=" * 50)

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
