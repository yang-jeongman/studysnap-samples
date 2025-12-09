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
from verification_system import get_verification_system
from intelligent_layout_engine import get_layout_engine

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
layout_engine = get_layout_engine()

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
    """헬스체크 엔드포인트"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


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
