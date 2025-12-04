"""
StudySnap Backend - PDF to Mobile HTML Converter
FastAPI 기반 백엔드 서버
"""

import os
import uuid
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
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

app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

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

@app.get("/api/files/{folder}")
async def list_folder_files(folder: str):
    """
    폴더별 파일 목록 반환 (파일 브라우저용)

    - folder: outputs, uploads, static, templates
    """
    try:
        # 허용된 폴더만 접근 가능
        allowed_folders = {
            'outputs': OUTPUT_DIR,
            'uploads': UPLOAD_DIR,
            'static': STATIC_DIR,
            'templates': TEMPLATES_DIR
        }

        if folder not in allowed_folders:
            raise HTTPException(status_code=400, detail=f"허용되지 않은 폴더: {folder}")

        folder_path = allowed_folders[folder]

        if not folder_path.exists():
            return JSONResponse({
                "success": True,
                "files": [],
                "count": 0,
                "folder": folder,
                "total_size": 0
            })

        files = []
        total_size = 0

        for file_path in folder_path.iterdir():
            if file_path.is_file():
                try:
                    stat = file_path.stat()
                    total_size += stat.st_size
                    files.append({
                        "name": file_path.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "url": f"/{folder}/{file_path.name}"
                    })
                except Exception as e:
                    logger.warning(f"파일 정보 조회 실패: {file_path.name} - {str(e)}")

        # 최신 파일 우선 정렬
        files.sort(key=lambda x: x["modified"], reverse=True)

        return JSONResponse({
            "success": True,
            "files": files,
            "count": len(files),
            "folder": folder,
            "total_size": total_size
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"폴더 파일 목록 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 목록 조회 실패: {str(e)}")


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
            'templates': TEMPLATES_DIR
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


@app.post("/api/editor/save")
async def save_html_file(request: Request):
    """
    HTML 에디터에서 파일 저장

    - filename: 저장할 파일명
    - content: HTML 내용
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

        # 보안: 파일명 검증 (경로 조작 방지)
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="잘못된 파일명입니다")

        if not filename.endswith(".html"):
            raise HTTPException(status_code=400, detail="HTML 파일만 저장할 수 있습니다")

        # 파일 저장
        file_path = OUTPUT_DIR / filename

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"HTML 파일 저장 완료: {filename} ({len(content)} bytes)")

        return JSONResponse({
            "success": True,
            "message": "파일이 저장되었습니다",
            "filename": filename,
            "size": len(content)
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 저장 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {str(e)}")


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
