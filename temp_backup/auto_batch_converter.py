"""
자동화 일괄 변환 및 학습 스크립트
test_pdfs 폴더의 모든 PDF를 변환하고 학습 시스템에 피드백
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent
TEST_PDF_DIR = BASE_DIR / "test_pdfs"
OUTPUT_DIR = BASE_DIR / "outputs"
REPORT_DIR = BASE_DIR / "reports"

# 디렉토리 생성
OUTPUT_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

# 모듈 임포트
try:
    from auto_election_converter import AutoElectionConverter
    from learning_system import get_learning_system
    AUTO_CONVERTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"자동 변환기 모듈 로드 실패: {e}")
    AUTO_CONVERTER_AVAILABLE = False

try:
    from pdf_converter import PDFConverter
    from html_generator import HTMLGenerator
    BASIC_CONVERTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"기본 변환기 모듈 로드 실패: {e}")
    BASIC_CONVERTER_AVAILABLE = False


class BatchConverter:
    """일괄 변환 클래스"""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.start_time = None
        self.end_time = None

        # 자동 변환기 초기화
        if AUTO_CONVERTER_AVAILABLE:
            try:
                self.auto_converter = AutoElectionConverter()
                self.learning_system = get_learning_system()
                logger.info("자동 변환기 초기화 완료")
            except Exception as e:
                logger.error(f"자동 변환기 초기화 실패: {e}")
                self.auto_converter = None
                self.learning_system = None
        else:
            self.auto_converter = None
            self.learning_system = None

        # 기본 변환기 초기화
        if BASIC_CONVERTER_AVAILABLE:
            try:
                self.pdf_converter = PDFConverter()
                self.html_generator = HTMLGenerator()
                logger.info("기본 변환기 초기화 완료")
            except Exception as e:
                logger.error(f"기본 변환기 초기화 실패: {e}")
                self.pdf_converter = None
                self.html_generator = None
        else:
            self.pdf_converter = None
            self.html_generator = None

    def get_pdf_files(self) -> List[Path]:
        """test_pdfs 폴더의 PDF 파일 목록 반환"""
        if not TEST_PDF_DIR.exists():
            logger.error(f"test_pdfs 폴더가 없습니다: {TEST_PDF_DIR}")
            return []

        pdf_files = list(TEST_PDF_DIR.glob("*.pdf"))
        pdf_files.extend(TEST_PDF_DIR.glob("*.PDF"))

        # 중복 제거 및 정렬
        pdf_files = list(set(pdf_files))
        pdf_files.sort(key=lambda x: x.name)

        return pdf_files

    def convert_single(self, pdf_path: Path, index: int, total: int) -> Dict[str, Any]:
        """단일 PDF 변환"""
        result = {
            "index": index,
            "filename": pdf_path.name,
            "success": False,
            "output_url": None,
            "candidate_name": None,
            "party": None,
            "error": None,
            "conversion_time": 0,
            "method": None
        }

        start = time.time()
        logger.info(f"[{index}/{total}] 변환 시작: {pdf_path.name}")

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 방법 1: 자동 변환기 사용
            if self.auto_converter:
                try:
                    brochure = self.auto_converter.convert(str(pdf_path))
                    html_content = self.auto_converter.generate_html(brochure)

                    # 출력 파일명 생성
                    if brochure.candidate.name:
                        output_filename = f"{brochure.candidate.name}_자동생성_{timestamp}.html"
                        result["candidate_name"] = brochure.candidate.name
                        result["party"] = brochure.candidate.party
                    else:
                        output_filename = f"AUTO_{pdf_path.stem}_{timestamp}.html"

                    output_path = OUTPUT_DIR / output_filename

                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(html_content)

                    result["success"] = True
                    result["output_url"] = f"/outputs/{output_filename}"
                    result["method"] = "auto_converter"

                    logger.info(f"  ✓ 자동 변환 성공: {output_filename}")

                except Exception as e:
                    logger.warning(f"  자동 변환 실패, 기본 변환기 시도: {e}")
                    raise e

            # 방법 2: 기본 변환기 사용 (자동 변환 실패 시)
            elif self.pdf_converter and self.html_generator:
                # PDF 텍스트 추출
                extracted = self.pdf_converter.extract_text_and_images(str(pdf_path))

                # HTML 생성
                html_content = self.html_generator.generate(
                    extracted.get("text", ""),
                    extracted.get("images", []),
                    template="default"
                )

                output_filename = f"BASIC_{pdf_path.stem}_{timestamp}.html"
                output_path = OUTPUT_DIR / output_filename

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)

                result["success"] = True
                result["output_url"] = f"/outputs/{output_filename}"
                result["method"] = "basic_converter"

                logger.info(f"  ✓ 기본 변환 성공: {output_filename}")

            else:
                raise Exception("사용 가능한 변환기가 없습니다")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"  ✗ 변환 실패: {e}")

        result["conversion_time"] = round(time.time() - start, 2)
        return result

    def run_batch(self) -> Dict[str, Any]:
        """일괄 변환 실행"""
        self.start_time = datetime.now()
        self.results = []

        pdf_files = self.get_pdf_files()
        total = len(pdf_files)

        if total == 0:
            logger.error("변환할 PDF 파일이 없습니다")
            return {"success": False, "error": "변환할 PDF 파일이 없습니다"}

        logger.info(f"=" * 50)
        logger.info(f"일괄 변환 시작: {total}개 파일")
        logger.info(f"=" * 50)

        for i, pdf_path in enumerate(pdf_files, 1):
            result = self.convert_single(pdf_path, i, total)
            self.results.append(result)

            # 진행률 표시
            success_count = sum(1 for r in self.results if r["success"])
            fail_count = sum(1 for r in self.results if not r["success"])
            logger.info(f"  진행: {i}/{total} (성공: {success_count}, 실패: {fail_count})")

        self.end_time = datetime.now()

        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """결과 리포트 생성"""
        total = len(self.results)
        success_count = sum(1 for r in self.results if r["success"])
        fail_count = total - success_count

        total_time = (self.end_time - self.start_time).total_seconds()
        avg_time = total_time / total if total > 0 else 0

        report = {
            "summary": {
                "total_files": total,
                "success_count": success_count,
                "fail_count": fail_count,
                "success_rate": round(success_count / total * 100, 1) if total > 0 else 0,
                "total_time_seconds": round(total_time, 2),
                "average_time_seconds": round(avg_time, 2),
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat()
            },
            "results": self.results,
            "failed_files": [r for r in self.results if not r["success"]],
            "successful_files": [r for r in self.results if r["success"]]
        }

        # 리포트 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"batch_report_{timestamp}.json"
        report_path = REPORT_DIR / report_filename

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"\n" + "=" * 50)
        logger.info(f"일괄 변환 완료!")
        logger.info(f"=" * 50)
        logger.info(f"총 파일: {total}개")
        logger.info(f"성공: {success_count}개 ({report['summary']['success_rate']}%)")
        logger.info(f"실패: {fail_count}개")
        logger.info(f"총 소요시간: {round(total_time, 1)}초")
        logger.info(f"평균 소요시간: {round(avg_time, 1)}초/파일")
        logger.info(f"리포트 저장: {report_path}")
        logger.info(f"=" * 50)

        return report

    def learn_from_results(self):
        """학습 시스템에 결과 피드백"""
        if not self.learning_system:
            logger.warning("학습 시스템을 사용할 수 없습니다")
            return

        success_results = [r for r in self.results if r["success"]]

        logger.info(f"\n학습 데이터 생성 중... ({len(success_results)}개 성공 결과)")

        # 성공한 변환 결과를 학습 데이터로 활용
        for result in success_results:
            try:
                job_id = f"batch_{result.get('index', 0)}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

                # log_feedback 메서드 사용
                self.learning_system.log_feedback(
                    job_id=job_id,
                    feedback_data={
                        "rating": 5,  # 자동 변환 성공 = 최고 평점
                        "accuracy": 5,
                        "completeness": 5,
                        "issues": [],
                        "comment": f"자동 일괄 변환 성공: {result.get('candidate_name', 'Unknown')}",
                        "corrections": {}
                    }
                )

                # log_conversion 메서드도 호출
                self.learning_system.log_conversion(
                    job_id=job_id,
                    conversion_data={
                        "filename": result.get("filename"),
                        "candidate_name": result.get("candidate_name"),
                        "party": result.get("party"),
                        "method": result.get("method"),
                        "conversion_time": result.get("conversion_time"),
                        "success": True
                    }
                )

            except Exception as e:
                logger.warning(f"학습 피드백 실패: {e}")

        logger.info("학습 데이터 생성 완료")


def main():
    """메인 실행"""
    print("\n" + "=" * 60)
    print("  StudySnap 자동화 일괄 변환 시스템")
    print("=" * 60)

    # PDF 파일 확인
    if not TEST_PDF_DIR.exists():
        print(f"\n❌ 오류: test_pdfs 폴더가 없습니다")
        print(f"   경로: {TEST_PDF_DIR}")
        print(f"\n   폴더를 생성하고 PDF 파일을 추가해주세요.")
        return

    pdf_files = list(TEST_PDF_DIR.glob("*.pdf")) + list(TEST_PDF_DIR.glob("*.PDF"))
    pdf_files = list(set(pdf_files))

    if not pdf_files:
        print(f"\n❌ 오류: test_pdfs 폴더에 PDF 파일이 없습니다")
        print(f"   경로: {TEST_PDF_DIR}")
        return

    print(f"\n📁 발견된 PDF 파일: {len(pdf_files)}개")
    for i, f in enumerate(pdf_files[:10], 1):
        print(f"   {i}. {f.name}")
    if len(pdf_files) > 10:
        print(f"   ... 외 {len(pdf_files) - 10}개")

    # 사용자 확인
    print(f"\n⚡ 일괄 변환을 시작하시겠습니까? (y/n): ", end="")

    # 자동 실행 모드 (인자로 --auto 전달 시)
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        print("y (자동 실행)")
        confirm = "y"
    else:
        confirm = input().strip().lower()

    if confirm != "y":
        print("취소되었습니다.")
        return

    # 일괄 변환 실행
    converter = BatchConverter()
    report = converter.run_batch()

    # 학습 시스템 피드백
    if report.get("summary", {}).get("success_count", 0) > 0:
        print("\n📚 학습 시스템에 결과 피드백 중...")
        converter.learn_from_results()

    print("\n✅ 모든 작업이 완료되었습니다!")
    print(f"   결과 확인: http://localhost:8000/static/editor.html")


if __name__ == "__main__":
    main()
