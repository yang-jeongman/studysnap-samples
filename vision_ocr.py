"""
Claude Vision OCR 모듈
이미지 기반 PDF에서 텍스트를 추출하기 위해 Claude Vision API 활용
"""

import os
import base64
import logging
import anthropic
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# 로거 설정
logger = logging.getLogger(__name__)


class VisionOCR:
    """Claude Vision API를 사용한 OCR"""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY가 설정되지 않았습니다. Vision OCR 기능을 사용할 수 없습니다.")
            self.client = None
        else:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                logger.info("Claude Vision OCR 클라이언트 초기화 완료")
            except Exception as e:
                logger.error(f"Claude Vision OCR 클라이언트 초기화 실패: {str(e)}")
                self.client = None

    def extract_text_from_image(self, image_base64: str, media_type: str = "image/jpeg") -> str:
        """이미지에서 텍스트 추출"""
        if not self.client:
            return ""

        try:
            # base64 데이터만 추출 (data:image/jpeg;base64, 제거)
            if "base64," in image_base64:
                image_base64 = image_base64.split("base64,")[1]

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": """이 이미지에서 모든 텍스트를 추출해주세요.

규칙:
1. 이미지에 보이는 텍스트를 그대로 추출
2. 레이아웃과 구조를 최대한 유지
3. 제목, 부제, 본문 등의 구조 파악
4. 한국어 텍스트 우선
5. 불필요한 설명 없이 텍스트만 반환

추출된 텍스트:"""
                            }
                        ],
                    }
                ],
            )

            return message.content[0].text.strip()

        except Exception as e:
            logger.error(f"Vision OCR 텍스트 추출 오류: {str(e)}", exc_info=True)
            return ""

    def extract_election_info(self, image_base64: str, media_type: str = "image/jpeg", page_number: int = 1) -> dict:
        """선거 공보물에서 구조화된 정보 추출"""
        if not self.client:
            return {"text": "", "structured": {}}

        try:
            if "base64," in image_base64:
                image_base64 = image_base64.split("base64,")[1]

            # 페이지 번호에 따라 프롬프트 조정
            page_context = ""
            if page_number == 1:
                page_context = "이것은 1페이지입니다. 후보자 기본 정보(이름, 기호, 정당, 슬로건)를 추출하세요."
            elif page_number == 2:
                page_context = "이것은 2페이지입니다. 출사표 내용을 추출하세요."
            elif 3 <= page_number <= 4:
                page_context = "이것은 성과 페이지입니다. '나경원이 바꾼 동작' 또는 '나경원이 바꾼 대한민국' 성과를 추출하세요."
            elif 5 <= page_number <= 9:
                page_context = f"이것은 핵심공약 페이지({page_number}/9)입니다. 6개 핵심공약 중 일부를 추출하세요. 각 공약마다 제목과 모든 세부 항목(bullet points)을 빠짐없이 추출하세요. 반드시 [핵심공약] 섹션으로 표시하세요."
            elif page_number == 10:
                page_context = "이것은 주민밀착공약 페이지입니다. [주민밀착공약] 섹션으로 표시하세요."
            elif page_number >= 11:
                page_context = "이것은 경력 및 연락처 페이지입니다. 경력, 마무리 문구, 선거사무소, SNS 정보를 추출하세요."

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": f"""{page_context}

이 선거 공보물 이미지를 **페이지별로** 정확하게 분석하여 정보를 추출해주세요.

**중요 원칙:**
1. 이미지에 보이는 모든 텍스트를 빠짐없이 추출하세요
2. 제목, 소제목, 본문을 구분하여 추출하세요
3. 순서와 구조를 정확히 유지하세요
4. OCR 오류는 수정하되 원본 의미를 변경하지 마세요

**추출 형식:**

[페이지 정보]
페이지 유형: (메인/출사표/성과/공약/주민밀착공약/경력 등)

[후보자 기본 정보] (1페이지에만)
이름: (후보자 이름)
기호: (숫자만)
정당: (정당명)
슬로건: (캐치프레이즈)
부제: (추가 설명)

[출사표] (2페이지)
제목: (출사표 제목)
내용: (출사표 전문)
마무리: (맺음말)

[성과] (3-4페이지)
대제목: (나경원이 바꾼 ○○)
소제목1: 제목
- 항목1
- 항목2
...

[핵심공약] (5-7페이지 - 6개 공약)
공약1: 제목
- 세부내용1
- 세부내용2
공약2: 제목
...

[주민밀착공약] (8-10페이지)
- 공약1
- 공약2
...

[경력 및 연락처] (11페이지)
경력:
- 경력1
- 경력2
...
마무리 문구: (있으면)
선거사무소: (주소 및 연락처)

**주의:**
- 모든 텍스트를 순서대로 추출하세요
- 제목과 내용을 명확히 구분하세요
- 숫자, 기호, 특수문자도 정확히 추출하세요"""
                            }
                        ],
                    }
                ],
            )

            raw_text = message.content[0].text.strip()
            return {
                "text": raw_text,
                "structured": self._parse_election_response(raw_text)
            }

        except Exception as e:
            logger.error(f"선거 정보 추출 오류: {str(e)}", exc_info=True)
            return {"text": "", "structured": {}}

    def _parse_election_response(self, text: str) -> dict:
        """Claude 응답을 구조화된 데이터로 파싱 - 페이지별 상세 파싱"""
        result = {
            "candidate_name": "",
            "party": "",
            "symbol": "",
            "slogan": "",
            "subtitle": "",  # 부제
            "manifesto": {"title": "", "content": "", "closing": ""},  # 출사표
            "achievements": [],  # 성과 (나경원이 바꾼 동작/대한민국)
            "core_pledges": [],  # 6개 핵심공약
            "pledges": [],  # 기존 호환성 유지
            "public_pledges": [],  # 국민밀착공약
            "career": [],
            "closing_message": "",  # 마무리 문구
            "contact_info": "",
            "other_text": ""
        }

        current_section = None
        current_subsection = None
        lines = text.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            i += 1

            if not line:
                continue

            # 섹션 헤더 감지
            if "[페이지 정보]" in line or "페이지 유형:" in line:
                continue
            elif "[후보자 기본 정보]" in line or "[후보자 정보]" in line:
                current_section = "candidate"
                continue
            elif "[출사표]" in line:
                current_section = "manifesto"
                continue
            elif "[성과]" in line:
                current_section = "achievements"
                current_subsection = {"title": "", "items": []}
                continue
            elif "[핵심공약]" in line or "[공약]" in line:
                current_section = "core_pledges"
                continue
            elif "[주민밀착공약]" in line or "[국민밀착공약]" in line:
                current_section = "public_pledges"
                continue
            elif "[경력 및 연락처]" in line or "[경력]" in line:
                current_section = "career"
                continue
            elif "[연락처 및 SNS]" in line or "[연락처]" in line:
                current_section = "contact"
                continue
            elif "[기타" in line:
                current_section = "other"
                continue

            # 섹션별 파싱
            if current_section == "candidate":
                if line.startswith("이름:"):
                    result["candidate_name"] = line.replace("이름:", "").strip()
                elif line.startswith("기호:"):
                    result["symbol"] = line.replace("기호:", "").strip()
                elif line.startswith("정당:"):
                    result["party"] = line.replace("정당:", "").strip()
                elif line.startswith("슬로건:"):
                    result["slogan"] = line.replace("슬로건:", "").strip()
                elif line.startswith("부제:"):
                    result["subtitle"] = line.replace("부제:", "").strip()

            elif current_section == "manifesto":
                if line.startswith("제목:"):
                    result["manifesto"]["title"] = line.replace("제목:", "").strip()
                elif line.startswith("내용:"):
                    content = line.replace("내용:", "").strip()
                    # 다음 줄들도 내용에 포함
                    while i < len(lines) and not lines[i].strip().startswith("마무리:"):
                        content += "\n" + lines[i].strip()
                        i += 1
                    result["manifesto"]["content"] = content
                elif line.startswith("마무리:"):
                    result["manifesto"]["closing"] = line.replace("마무리:", "").strip()

            elif current_section == "achievements":
                if line.startswith("대제목:"):
                    if current_subsection and current_subsection["title"]:
                        result["achievements"].append(current_subsection)
                    current_subsection = {
                        "title": line.replace("대제목:", "").strip(),
                        "sections": []
                    }
                elif line.startswith("소제목") or ":" in line and not line.startswith("-"):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        current_subsection.setdefault("sections", []).append({
                            "title": parts[1].strip(),
                            "items": []
                        })
                elif line.startswith("-"):
                    item = line.lstrip("-•").strip()
                    if current_subsection and "sections" in current_subsection and current_subsection["sections"]:
                        current_subsection["sections"][-1]["items"].append(item)

            elif current_section == "core_pledges":
                if line.startswith("공약") and ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        pledge = {"title": parts[1].strip(), "details": []}
                        # 다음 줄들이 세부내용
                        while i < len(lines) and lines[i].strip().startswith("-"):
                            pledge["details"].append(lines[i].strip().lstrip("-•").strip())
                            i += 1
                        result["core_pledges"].append(pledge)
                        result["pledges"].append(pledge["title"])  # 호환성

            elif current_section == "public_pledges":
                if line.startswith("-") or line.startswith("•"):
                    pledge = line.lstrip("-•").strip()
                    if len(pledge) > 3:
                        result["public_pledges"].append(pledge)

            elif current_section == "career":
                if line.startswith("경력:"):
                    continue
                elif line.startswith("마무리 문구:"):
                    result["closing_message"] = line.replace("마무리 문구:", "").strip()
                elif line.startswith("선거사무소:") or line.startswith("선거사무소 :"):
                    # 선거사무소 정보 시작 - 이후 모든 줄을 contact_info에 추가
                    contact_line = line.replace("선거사무소:", "").replace("선거사무소 :", "").strip()
                    if contact_line:
                        result["contact_info"] += contact_line + "\n"
                    # 다음 줄들도 contact_info에 포함 (SNS 링크 등)
                    current_section = "contact"
                elif line.startswith("-") or line.startswith("•"):
                    career = line.lstrip("-•").strip()
                    if len(career) > 5:
                        result["career"].append(career)
                elif line and len(line) > 5 and not result["closing_message"]:
                    result["career"].append(line)

            elif current_section == "contact":
                # SNS, 연락처 등 모든 정보 포함
                if line and not line.startswith("["):  # 새 섹션 시작 아니면 추가
                    result["contact_info"] += line + "\n"

            elif current_section == "other":
                result["other_text"] += line + "\n"

        # 마지막 성과 추가
        if current_subsection and current_subsection.get("title"):
            result["achievements"].append(current_subsection)

        result["contact_info"] = result["contact_info"].strip()
        result["other_text"] = result["other_text"].strip()
        return result


    def extract_church_bulletin_info(self, image_base64: str, media_type: str = "image/jpeg", page_number: int = 1) -> dict:
        """교회 주보에서 구조화된 정보 추출 - 페이지별 상세 추출"""
        if not self.client:
            return {"text": "", "structured": {}}

        try:
            if "base64," in image_base64:
                image_base64 = image_base64.split("base64,")[1]

            # 페이지별 맞춤형 상세 프롬프트
            if page_number == 1:
                prompt = """이 교회 주보 표지를 분석하세요.

**반드시 추출할 항목:**

[교회정보]
교회명: (교회 이름)
영문명: (영문 이름 있으면)
날짜: (예: 2025년 12월 14일)
통권: (예: 통권 제68권 50호)
표어: (2025 표어: 오직 말씀으로 - 정확히 추출)
교회목표: (목표 항목들)
주소: (주소)
대표전화: (전화번호)

[목회자]
위임목사: (이름)
부목사: (목회/교무/국제 등 역할별로)

**주의: 1페이지의 짧은 성경 구절은 추출하지 마세요. 오늘의 말씀은 3페이지에서 추출합니다.**"""

            elif page_number == 2:
                prompt = """이 주일예배순서 페이지를 분석하세요.

**반드시 모든 예배 정보를 추출하세요:**

[주일예배순서]
공통순서:
- 예배로 부르심: (성경구절)
- 첫 찬송: (찬송가 번호)
- 신앙고백: (사도신경 등)
- 마지막 찬송: (주기도문 등)

예배별 담당자 (마크다운 테이블 형식으로 출력):
**중요: PDF에 있는 예배 정보를 그대로 추출하세요. 가상 데이터를 생성하지 마세요.**

테이블 형식:
| 구분 | 시간 | 사회 | 성경봉독 | 대표기도 | 헌금기도 | 찬송 | 설교제목 | 설교자 |
|------|------|------|----------|----------|----------|------|----------|--------|
| (PDF의 실제 예배 정보를 각 행에 추출) |

**절대 규칙:
1. 모든 예배의 모든 담당자를 PDF에서 빠짐없이 추출
2. PDF에 없는 정보는 절대 추측하거나 생성하지 않음
3. 성경봉독은 PDF에 표시된 전체 구절 그대로 추출
4. 찬송은 PDF에 있는 번호 그대로 추출
5. 테이블 형식을 정확히 유지**"""

            elif page_number == 3:
                prompt = """**중요: 이 페이지에서 '오늘의 말씀' 또는 '금주의 말씀' 섹션을 찾아 정확히 추출하세요.**

[오늘의 말씀]
**절대 규칙: 이 PDF 페이지에 표시된 성경 말씀을 그대로 추출하세요.**
**가상 예시나 다른 문서의 내용을 절대 사용하지 마세요!**

본문: (이 페이지에 보이는 말씀 전체 텍스트 - 한 글자도 빠뜨리지 말고 그대로 추출)
출처: (PDF에 표시된 성경 구절 참조 그대로)

[수요예배순]
날짜: (날짜)
1부: 시간, 사회, 기도, 성경봉독, 찬양, 설교, 헌금기도
2부: 시간, 사회, 기도, 성경봉독, 찬양, 설교, 헌금기도
3부: 시간, 사회, 기도, 성경봉독, 찬양, 설교, 헌금기도

[금요성령대망회순]
날짜: (날짜)
시간: (시간)
사회: (이름)
기도: (이름)
성경봉독: (구절)
찬양: (찬양대)
설교: (제목) / (목사)

[토요예배순]
날짜: (날짜)
시간: (시간)
사회: (이름)
기도: (이름)
성경봉독: (구절)
찬양: (찬양대)
설교: (제목) / (목사)
헌금기도: (이름)

[금주의 찬양]
**중요: PDF에 있는 금주의 찬양 표를 마크다운 테이블 형식으로 그대로 추출하세요.**
**가상 데이터나 예시를 생성하지 마세요. 오직 PDF 원본에 있는 내용만 추출하세요.**

마크다운 테이블 형식 (파이프 | 문자 사용):
- 첫 줄: 헤더 (열 제목) - PDF에 있는 그대로
- 둘째 줄: 구분선 |------|
- 셋째 줄부터: PDF에서 추출한 실제 데이터

**절대 지켜야 할 규칙:**
1. PDF에 있는 찬양대 이름, 지휘자, 반주자, 곡명을 그대로 추출
2. 실제로 PDF에 없는 내용은 절대 생성하지 않음
3. 추측이나 가상의 데이터를 만들지 않음
4. 헤더와 데이터의 열 개수가 일치해야 함
5. PDF에 찬양대 정보가 없으면 "[금주의 찬양]" 섹션을 완전히 생략

**PDF에 금주의 찬양 정보가 없으면 이 섹션을 출력하지 마세요.**"""

            elif page_number == 4:
                prompt = """이 설교 말씀(생명의 말씀) 페이지를 분석하세요.

[생명의 말씀]
제목: (설교 제목 - 한글)
영문제목: (영문 제목)
본문: (성경 구절)
날짜: (날짜)

[설교 내용]
서론: (설교 서론 문단 전체를 그대로 추출)

소제목1: (첫 번째 포인트 제목)
영문1: (영문 제목)
내용1: (첫 번째 포인트 내용 전체를 그대로 추출 - 문단 유지)

소제목2: (두 번째 포인트 제목)
영문2: (영문 제목)
내용2: (두 번째 포인트 내용 전체를 그대로 추출)

소제목3: (세 번째 포인트 제목)
영문3: (영문 제목)
내용3: (세 번째 포인트 내용 전체를 그대로 추출)

설교자: (교회명 + 목사 이름 + 직분)

**중요: 설교 내용을 축약하지 말고 전체를 그대로 추출하세요.**"""

            elif page_number == 5:
                prompt = """이 교회소식(News Board/Church News) 페이지의 모든 내용을 완전히 추출하세요.

**매우 중요: 이 페이지에 있는 모든 공지사항, 안내, 광고를 빠짐없이 추출해야 합니다!**

**반드시 아래 형식을 정확히 따르세요:**

[예배]
1. (예배 관련 공지 제목)
   상세내용: (일시, 장소, 설교자, 말씀 등 모든 세부 정보)
2. (다음 예배 공지 제목)
   상세내용: (세부 정보)

[모집]
1. (모집 관련 공지 제목)
   상세내용: (일자, 대상, 과정, 문의처 등)

[안내]
1. (일반 안내 제목)
   상세내용: (세부 정보 전체)
2. (다음 안내 제목)
   상세내용: (세부 정보 전체)

**중요 규칙:**
1. PDF에 보이는 모든 공지/안내를 빠짐없이 추출
2. 각 항목은 반드시 "1. 제목" 형식으로 시작
3. 상세내용은 반드시 "   상세내용: " 으로 시작 (들여쓰기 3칸)
4. 예배 관련 소식은 [예배], 모집 관련은 [모집], 나머지는 [안내]로 분류
5. 절대 요약하지 말고 원문 그대로 추출

**교회 소식이 없으면 "[예배]", "[모집]", "[안내]" 섹션 자체를 생략하세요.**

[다음 주간 대표기도]
| 구분 | 1부 | 2부 | 3부 | 4부 |
|------|-----|-----|-----|-----|
| (요일) | (이름) | (이름) | (이름) | (이름) |

**대표기도 표가 없으면 이 섹션을 생략하세요.**"""

            elif page_number == 6:
                prompt = """이 오늘의 양식(묵상) 페이지를 분석하세요.

[오늘의 양식]
제목: (양식 제목 - 예: "마카롱의 미학")
내용: (전체 내용을 문단별로 그대로 추출)

문단1: (첫 번째 문단 전체)
문단2: (두 번째 문단 전체)
문단3: (세 번째 문단 전체)
...

**매우 중요: 내용을 절대 요약하거나 축약하지 마세요!**
**모든 문단의 전체 텍스트를 빠짐없이 추출하세요!**
**글의 처음부터 끝까지 모두 포함해야 합니다!**"""

            else:
                prompt = """이 주보 페이지의 모든 텍스트를 추출하세요.

[페이지 내용]
(보이는 모든 텍스트를 순서대로 추출)"""

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )

            raw_text = message.content[0].text.strip()
            return {
                "text": raw_text,
                "structured": self._parse_church_bulletin_response(raw_text)
            }

        except Exception as e:
            logger.error(f"교회 주보 정보 추출 오류: {str(e)}", exc_info=True)
            return {"text": "", "structured": {}}

    def _parse_church_bulletin_response(self, text: str) -> dict:
        """교회 주보 응답을 구조화된 데이터로 파싱 - 상세 버전"""
        result = {
            "church_info": {"name": "", "english_name": "", "date": "", "volume": "", "slogan": "", "goals": [], "address": "", "phone": ""},
            "pastors": {"senior": "", "associate": []},
            "today_verse": {"text": "", "reference": ""},
            "worship_services": [],  # 예배 순서들
            "common_order": {"invocation": "", "first_hymn": "", "creed": "", "second_hymns": {}, "final_hymn": ""},
            "sermon": {"title": "", "english_title": "", "scripture": "", "pastor": "", "intro": "", "points": [], "author": ""},
            "choir": [],  # 찬양대 순서
            "raw_choir_table": {"headers": [], "rows": []},  # 원본 PDF 테이블 형식 보존
            "wednesday_service": {},
            "friday_service": {},
            "saturday_service": {},
            "news": {"worship": [], "recruit": [], "info": []},  # 카테고리별 교회 소식 (제목+상세내용)
            "next_week_prayers": [],  # 다음 주간 대표기도
            "raw_prayer_table": {"headers": [], "rows": []},  # 대표기도 원본 테이블
            "devotional": {"title": "", "content": ""},  # 오늘의 양식
            "announcements": [],  # 광고
            "other_text": ""
        }

        current_section = None
        current_service = None
        current_choir = None
        current_news_category = None
        lines = text.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            i += 1

            if not line:
                continue

            # 섹션 헤더 감지
            if "[교회정보]" in line:
                current_section = "church_info"
                continue
            elif "[목회자]" in line:
                current_section = "pastors"
                continue
            elif "[오늘의 말씀]" in line or "[금주의 말씀]" in line:
                current_section = "verse"
                continue
            elif "[주일예배순서]" in line or "[예배 순서]" in line or "[예배순서]" in line:
                current_section = "worship"
                continue
            elif "[생명의 말씀]" in line or "[설교]" in line:
                current_section = "sermon"
                continue
            elif "[설교 내용]" in line:
                current_section = "sermon_content"
                continue
            elif "[금주의 찬양]" in line or "[찬양대]" in line:
                current_section = "choir"
                continue
            elif "[수요예배순]" in line:
                current_section = "wednesday"
                continue
            elif "[금요성령대망회순]" in line:
                current_section = "friday"
                continue
            elif "[토요예배순]" in line:
                current_section = "saturday"
                continue
            elif "[예배 안내]" in line or "[예배]" in line:
                current_section = "news"
                current_news_category = "worship"
                continue
            elif "[모집]" in line:
                current_section = "news"
                current_news_category = "recruit"
                continue
            elif "[안내]" in line:
                current_section = "news"
                current_news_category = "info"
                continue
            elif "[교회 소식]" in line or "[소식]" in line:
                current_section = "news"
                current_news_category = "info"
                continue
            elif "[예배]" in line and "예배순" not in line:
                current_section = "news"
                current_news_category = "worship"
                continue
            elif "[모집]" in line:
                current_section = "news"
                current_news_category = "recruit"
                continue
            elif "[안내]" in line:
                current_section = "news"
                current_news_category = "info"
                continue
            elif "[다음 주간 대표기도]" in line or "대표기도" in line and "주간" in line:
                current_section = "next_prayers"
                continue
            elif "[오늘의 양식]" in line:
                current_section = "devotional"
                continue
            elif "[광고]" in line:
                current_section = "announcements"
                continue

            # 섹션별 파싱
            if current_section == "church_info":
                if line.startswith("교회명:"):
                    result["church_info"]["name"] = line.replace("교회명:", "").strip()
                elif line.startswith("영문명:"):
                    result["church_info"]["english_name"] = line.replace("영문명:", "").strip()
                elif line.startswith("날짜:"):
                    result["church_info"]["date"] = line.replace("날짜:", "").strip()
                elif line.startswith("통권:"):
                    result["church_info"]["volume"] = line.replace("통권:", "").strip()
                elif line.startswith("표어:"):
                    result["church_info"]["slogan"] = line.replace("표어:", "").strip()
                elif line.startswith("교회목표:"):
                    goals_text = line.replace("교회목표:", "").strip()
                    result["church_info"]["goals"] = [g.strip() for g in goals_text.split(",") if g.strip()]
                elif line.startswith("주소:"):
                    result["church_info"]["address"] = line.replace("주소:", "").strip()
                elif line.startswith("대표전화:"):
                    result["church_info"]["phone"] = line.replace("대표전화:", "").strip()

            elif current_section == "pastors":
                if line.startswith("위임목사:"):
                    result["pastors"]["senior"] = line.replace("위임목사:", "").strip()
                elif line.startswith("부목사:"):
                    associate = line.replace("부목사:", "").strip()
                    result["pastors"]["associate"] = [a.strip() for a in associate.split(",") if a.strip()]

            elif current_section == "verse":
                if line.startswith("본문:"):
                    result["today_verse"]["text"] = line.replace("본문:", "").strip()
                elif line.startswith("출처:"):
                    result["today_verse"]["reference"] = line.replace("출처:", "").strip()
                elif not result["today_verse"]["text"] and len(line) > 10:
                    result["today_verse"]["text"] = line

            elif current_section == "worship":
                # 테이블 형식 파싱 (| 구분 | 시간 | 사회 | 성경봉독 | 대표기도 | 헌금기도 | 찬송 | 설교제목 | 설교자 |)
                if line.startswith("|") and "구분" not in line and "---" not in line:
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if len(parts) >= 6:  # 최소 6개 컬럼
                        # 9컬럼 (찬송 포함): 구분|시간|사회|성경봉독|대표기도|헌금기도|찬송|설교제목|설교자
                        # 8컬럼 (찬송 미포함): 구분|시간|사회|성경봉독|대표기도|헌금기도|설교제목|설교자
                        if len(parts) >= 9:
                            service = {
                                "name": parts[0],
                                "time": parts[1] if len(parts) > 1 else "",
                                "presider": parts[2] if len(parts) > 2 else "",
                                "scripture": parts[3] if len(parts) > 3 else "",
                                "prayer": parts[4] if len(parts) > 4 else "",
                                "offering_prayer": parts[5] if len(parts) > 5 else "",
                                "hymn": parts[6] if len(parts) > 6 else "",
                                "sermon_title": parts[7] if len(parts) > 7 else "",
                                "sermon_pastor": parts[8] if len(parts) > 8 else ""
                            }
                        else:
                            # 이전 형식 (찬송 컬럼 없음)
                            service = {
                                "name": parts[0],
                                "time": parts[1] if len(parts) > 1 else "",
                                "presider": parts[2] if len(parts) > 2 else "",
                                "scripture": parts[3] if len(parts) > 3 else "",
                                "prayer": parts[4] if len(parts) > 4 else "",
                                "offering_prayer": parts[5] if len(parts) > 5 else "",
                                "hymn": "",
                                "sermon_title": parts[6] if len(parts) > 6 else "",
                                "sermon_pastor": parts[7] if len(parts) > 7 else ""
                            }
                        result["worship_services"].append(service)
                # 기존 형식도 지원
                elif line.startswith("예배명:") or line.startswith("예배:"):
                    if current_service:
                        result["worship_services"].append(current_service)
                    service_name = line.replace("예배명:", "").replace("예배:", "").strip()
                    current_service = {
                        "name": service_name,
                        "presider": "",
                        "scripture": "",
                        "prayer": "",
                        "offering_prayer": "",
                        "hymn": "",
                        "sermon_title": "",
                        "sermon_pastor": ""
                    }
                elif current_service:
                    if line.startswith("사회:"):
                        current_service["presider"] = line.replace("사회:", "").strip()
                    elif line.startswith("시간:"):
                        current_service["time"] = line.replace("시간:", "").strip()
                    elif line.startswith("성경봉독:"):
                        current_service["scripture"] = line.replace("성경봉독:", "").strip()
                    elif line.startswith("대표기도:"):
                        current_service["prayer"] = line.replace("대표기도:", "").strip()
                    elif line.startswith("헌금기도:"):
                        current_service["offering_prayer"] = line.replace("헌금기도:", "").strip()
                    elif line.startswith("찬송:"):
                        current_service["hymn"] = line.replace("찬송:", "").strip()
                    elif line.startswith("설교:"):
                        sermon_info = line.replace("설교:", "").strip()
                        if "/" in sermon_info:
                            parts = sermon_info.split("/")
                            current_service["sermon_title"] = parts[0].strip()
                            current_service["sermon_pastor"] = parts[1].strip() if len(parts) > 1 else ""
                        else:
                            current_service["sermon_title"] = sermon_info
                # 공통 순서 파싱
                elif line.startswith("- 예배로 부르심:"):
                    result["common_order"]["invocation"] = line.replace("- 예배로 부르심:", "").strip()
                elif line.startswith("- 첫 찬송:"):
                    result["common_order"]["first_hymn"] = line.replace("- 첫 찬송:", "").strip()
                elif line.startswith("- 신앙고백:"):
                    result["common_order"]["creed"] = line.replace("- 신앙고백:", "").strip()
                elif line.startswith("- 마지막 찬송:"):
                    result["common_order"]["final_hymn"] = line.replace("- 마지막 찬송:", "").strip()

            elif current_section == "sermon":
                if line.startswith("제목:"):
                    result["sermon"]["title"] = line.replace("제목:", "").strip()
                elif line.startswith("영문제목:"):
                    result["sermon"]["english_title"] = line.replace("영문제목:", "").strip()
                elif line.startswith("본문:"):
                    result["sermon"]["scripture"] = line.replace("본문:", "").strip()
                elif line.startswith("날짜:"):
                    pass  # 날짜는 church_info에서 처리
                elif line.startswith("설교자:"):
                    result["sermon"]["author"] = line.replace("설교자:", "").strip()

            elif current_section == "sermon_content":
                if line.startswith("서론:"):
                    result["sermon"]["intro"] = line.replace("서론:", "").strip()
                elif line.startswith("소제목") and ":" in line:
                    point_num = line.split(":")[0].replace("소제목", "").strip()
                    point_title = line.split(":", 1)[1].strip() if ":" in line else ""
                    result["sermon"]["points"].append({
                        "number": point_num,
                        "title": point_title,
                        "english": "",
                        "content": ""
                    })
                elif line.startswith("영문") and ":" in line and result["sermon"]["points"]:
                    result["sermon"]["points"][-1]["english"] = line.split(":", 1)[1].strip()
                elif line.startswith("내용") and ":" in line and result["sermon"]["points"]:
                    content = line.split(":", 1)[1].strip() if ":" in line else ""
                    # 다음 줄들도 내용에 포함
                    while i < len(lines) and not lines[i].strip().startswith("소제목") and not lines[i].strip().startswith("[") and lines[i].strip():
                        content += "\n" + lines[i].strip()
                        i += 1
                    result["sermon"]["points"][-1]["content"] = content
                elif line.startswith("설교자:"):
                    result["sermon"]["author"] = line.replace("설교자:", "").strip()
                elif len(line) > 30 and not result["sermon"]["intro"]:
                    result["sermon"]["intro"] = line

            elif current_section == "choir":
                # 테이블 형식 파싱 - 원본 PDF 형식 그대로 보존
                if line.startswith("|"):
                    parts = [p.strip() for p in line.split("|") if p.strip()]

                    # 헤더 행 감지 (구분, 찬양대 등 포함)
                    if any(h in line for h in ["구분", "찬양대", "지휘", "반주", "찬양곡"]):
                        result["raw_choir_table"]["headers"] = parts
                    # 구분선 무시
                    elif "---" in line or "–––" in line:
                        pass
                    # 데이터 행
                    elif len(parts) >= 2:
                        result["raw_choir_table"]["rows"].append(parts)
                        # 기존 choir 배열도 함께 채움 (하위 호환)
                        choir = {
                            "service": parts[0] if len(parts) > 0 else "",
                            "name": parts[1] if len(parts) > 1 else "",
                            "conductor": parts[2] if len(parts) > 2 else "",
                            "song": parts[3] if len(parts) > 3 else "",
                            "accompanist": parts[4] if len(parts) > 4 else ""
                        }
                        result["choir"].append(choir)
                # 기존 형식도 지원
                elif line.startswith("예배:"):
                    if current_choir:
                        result["choir"].append(current_choir)
                    current_choir = {
                        "service": line.replace("예배:", "").strip(),
                        "name": "",
                        "conductor": "",
                        "song": ""
                    }
                elif current_choir:
                    if line.startswith("찬양대:"):
                        current_choir["name"] = line.replace("찬양대:", "").strip()
                    elif line.startswith("지휘자:"):
                        current_choir["conductor"] = line.replace("지휘자:", "").strip()
                    elif line.startswith("곡명:"):
                        current_choir["song"] = line.replace("곡명:", "").strip()

            elif current_section == "news":
                # 번호가 있는 항목 (1. 2. 등) - 제목과 상세내용 분리
                import re
                if re.match(r'^\d+\.', line):
                    title = re.sub(r'^\d+\.\s*', '', line)
                    # 다음 줄에서 상세내용 가져오기
                    detail = ""
                    while i < len(lines):
                        next_line = lines[i].strip()
                        # 다음 번호 항목이나 섹션 시작이면 중단
                        if re.match(r'^\d+\.', next_line) or next_line.startswith("["):
                            break
                        # 상세내용: 으로 시작하면
                        if next_line.startswith("상세내용:"):
                            detail = next_line.replace("상세내용:", "").strip()
                            i += 1
                            # 다음 줄들도 상세내용에 포함
                            while i < len(lines):
                                cont_line = lines[i].strip()
                                if re.match(r'^\d+\.', cont_line) or cont_line.startswith("["):
                                    break
                                if cont_line:
                                    detail += "\n" + cont_line
                                i += 1
                            break
                        elif next_line and not next_line.startswith("["):
                            detail += ("\n" if detail else "") + next_line
                            i += 1
                        else:
                            i += 1
                            break

                    if current_news_category and title:
                        result["news"][current_news_category].append({
                            "title": title,
                            "detail": detail.strip()
                        })
                elif line.startswith("-") or line.startswith("•"):
                    news_item = line.lstrip("-•").strip()
                    if len(news_item) > 3:
                        if current_news_category:
                            result["news"][current_news_category].append({
                                "title": news_item,
                                "detail": ""
                            })
                        else:
                            result["news"]["info"].append({
                                "title": news_item,
                                "detail": ""
                            })

            elif current_section == "next_prayers":
                # 대표기도 테이블 파싱 - 원본 그대로
                if line.startswith("|"):
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    # 헤더 행 감지
                    if any(h in line for h in ["구분", "1부", "2부", "3부", "4부"]):
                        result["raw_prayer_table"]["headers"] = parts
                    # 구분선 무시
                    elif "---" in line or "–––" in line:
                        pass
                    # 데이터 행
                    elif len(parts) >= 2:
                        result["raw_prayer_table"]["rows"].append(parts)

            elif current_section == "devotional":
                if line.startswith("제목:"):
                    result["devotional"]["title"] = line.replace("제목:", "").strip()
                elif line.startswith("내용:"):
                    content = line.replace("내용:", "").strip()
                    # 다음 줄들도 내용에 포함
                    while i < len(lines) and not lines[i].strip().startswith("["):
                        content += "\n" + lines[i].strip()
                        i += 1
                    result["devotional"]["content"] = content
                elif line.startswith("문단") and ":" in line:
                    # 문단1:, 문단2: 등의 형식
                    paragraph = line.split(":", 1)[1].strip() if ":" in line else ""
                    if paragraph:
                        if result["devotional"]["content"]:
                            result["devotional"]["content"] += "\n\n" + paragraph
                        else:
                            result["devotional"]["content"] = paragraph
                elif not result["devotional"]["title"] and len(line) > 5:
                    result["devotional"]["title"] = line
                elif result["devotional"]["title"] and len(line) > 20:
                    # 제목이 있고 긴 줄이면 내용에 추가
                    if result["devotional"]["content"]:
                        result["devotional"]["content"] += "\n\n" + line
                    else:
                        result["devotional"]["content"] = line

            elif current_section == "announcements":
                if line.startswith("-") or line.startswith("•"):
                    announcement = line.lstrip("-•").strip()
                    if len(announcement) > 3:
                        result["announcements"].append(announcement)

        # 마지막 항목 추가
        if current_service:
            result["worship_services"].append(current_service)
        if current_choir:
            result["choir"].append(current_choir)

        return result


    def extract_lecture_info(self, image_base64: str, media_type: str = "image/jpeg", page_number: int = 1) -> dict:
        """강의 자료에서 구조화된 정보 추출"""
        if not self.client:
            return {"text": "", "structured": {}}

        try:
            if "base64," in image_base64:
                image_base64 = image_base64.split("base64,")[1]

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": f"""이 강의 자료 이미지(페이지 {page_number})를 분석하여 구조화된 정보를 추출해주세요.

**추출 형식:**

[페이지 정보]
페이지 번호: {page_number}
페이지 유형: (표지/목차/본문/요약/참고자료)

[제목]
메인 제목: (강의 제목)
부제목: (있는 경우)

[강사 정보] (표지에만)
강사명:
소속:
연락처:

[학습 목표] (있는 경우)
- 목표1
- 목표2

[본문 내용]
섹션1: 제목
- 핵심 포인트1
- 핵심 포인트2

섹션2: 제목
- 내용1
- 내용2

[표/차트] (있는 경우)
표 제목:
표 내용 요약:

[이미지/다이어그램 설명] (있는 경우)
- 이미지1: 설명
- 이미지2: 설명

[핵심 용어] (있는 경우)
- 용어1: 정의
- 용어2: 정의

[질문/토론 주제] (있는 경우)
- 질문1
- 질문2

**주의:**
- 모든 텍스트를 순서대로 추출하세요
- 수식이나 코드가 있으면 그대로 추출하세요
- 표와 차트의 데이터도 추출하세요"""
                            }
                        ],
                    }
                ],
            )

            raw_text = message.content[0].text.strip()
            return {
                "text": raw_text,
                "structured": self._parse_lecture_response(raw_text),
                "page_number": page_number
            }

        except Exception as e:
            logger.error(f"강의 정보 추출 오류: {str(e)}", exc_info=True)
            return {"text": "", "structured": {}, "page_number": page_number}

    def _parse_lecture_response(self, text: str) -> dict:
        """강의 자료 응답을 구조화된 데이터로 파싱"""
        result = {
            "page_type": "",
            "title": "",
            "subtitle": "",
            "instructor": {"name": "", "affiliation": "", "contact": ""},
            "learning_objectives": [],
            "sections": [],
            "tables": [],
            "images": [],
            "key_terms": [],
            "questions": []
        }

        current_section = None
        current_content = None
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 섹션 헤더 감지
            if "[페이지 정보]" in line:
                current_section = "page_info"
            elif "[제목]" in line:
                current_section = "title"
            elif "[강사 정보]" in line:
                current_section = "instructor"
            elif "[학습 목표]" in line:
                current_section = "objectives"
            elif "[본문 내용]" in line:
                current_section = "content"
            elif "[표/차트]" in line:
                current_section = "tables"
            elif "[이미지" in line or "[다이어그램" in line:
                current_section = "images"
            elif "[핵심 용어]" in line:
                current_section = "terms"
            elif "[질문" in line or "[토론" in line:
                current_section = "questions"
            else:
                # 섹션별 파싱
                if current_section == "page_info":
                    if "페이지 유형:" in line:
                        result["page_type"] = line.split(":", 1)[1].strip()
                elif current_section == "title":
                    if "메인 제목:" in line:
                        result["title"] = line.split(":", 1)[1].strip()
                    elif "부제목:" in line:
                        result["subtitle"] = line.split(":", 1)[1].strip()
                elif current_section == "instructor":
                    if "강사명:" in line:
                        result["instructor"]["name"] = line.split(":", 1)[1].strip()
                    elif "소속:" in line:
                        result["instructor"]["affiliation"] = line.split(":", 1)[1].strip()
                    elif "연락처:" in line:
                        result["instructor"]["contact"] = line.split(":", 1)[1].strip()
                elif current_section == "objectives":
                    if line.startswith("-") or line.startswith("•"):
                        result["learning_objectives"].append(line.lstrip("-•").strip())
                elif current_section == "content":
                    if line.startswith("섹션") and ":" in line:
                        section_title = line.split(":", 1)[1].strip()
                        current_content = {"title": section_title, "points": []}
                        result["sections"].append(current_content)
                    elif (line.startswith("-") or line.startswith("•")) and current_content:
                        current_content["points"].append(line.lstrip("-•").strip())
                elif current_section == "tables":
                    if "표 제목:" in line:
                        result["tables"].append({"title": line.split(":", 1)[1].strip(), "summary": ""})
                    elif "표 내용 요약:" in line and result["tables"]:
                        result["tables"][-1]["summary"] = line.split(":", 1)[1].strip()
                elif current_section == "images":
                    if line.startswith("-"):
                        result["images"].append(line.lstrip("-•").strip())
                elif current_section == "terms":
                    if line.startswith("-") and ":" in line:
                        parts = line.lstrip("-•").split(":", 1)
                        if len(parts) == 2:
                            result["key_terms"].append({"term": parts[0].strip(), "definition": parts[1].strip()})
                elif current_section == "questions":
                    if line.startswith("-") or line.startswith("•"):
                        result["questions"].append(line.lstrip("-•").strip())

        return result

    def extract_newsletter_info(self, image_base64: str, media_type: str = "image/jpeg", page_number: int = 1) -> dict:
        """뉴스레터에서 구조화된 정보 추출"""
        if not self.client:
            return {"text": "", "structured": {}}

        try:
            if "base64," in image_base64:
                image_base64 = image_base64.split("base64,")[1]

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": f"""이 뉴스레터/소식지 이미지(페이지 {page_number})를 분석하여 구조화된 정보를 추출해주세요.

**추출 형식:**

[뉴스레터 정보]
발행처: (조직/회사명)
발행호: (예: 2024년 12월호, Vol.5)
발행일: (날짜)

[헤드라인 기사]
제목: (메인 기사 제목)
부제: (있는 경우)
내용: (기사 전문)

[서브 기사들]
기사1:
- 제목:
- 카테고리: (사내소식/업계동향/인사/행사 등)
- 요약:
- 내용:

기사2:
- 제목:
- 카테고리:
- 요약:
- 내용:

[인터뷰/인물 소개] (있는 경우)
대상:
직위:
내용:

[이벤트/일정] (있는 경우)
- 이벤트1: 날짜, 장소, 내용
- 이벤트2: 날짜, 장소, 내용

[공지사항] (있는 경우)
- 공지1
- 공지2

[광고/배너] (있는 경우)
- 광고1: 내용 설명
- 광고2: 내용 설명

**주의:**
- 모든 텍스트를 순서대로 추출하세요
- 기사별로 명확히 구분하세요
- 이미지 캡션도 추출하세요"""
                            }
                        ],
                    }
                ],
            )

            raw_text = message.content[0].text.strip()
            return {
                "text": raw_text,
                "structured": self._parse_newsletter_response(raw_text),
                "page_number": page_number
            }

        except Exception as e:
            logger.error(f"뉴스레터 정보 추출 오류: {str(e)}", exc_info=True)
            return {"text": "", "structured": {}, "page_number": page_number}

    def _parse_newsletter_response(self, text: str) -> dict:
        """뉴스레터 응답을 구조화된 데이터로 파싱"""
        result = {
            "publisher": "",
            "issue": "",
            "date": "",
            "headline": {"title": "", "subtitle": "", "content": ""},
            "articles": [],
            "interviews": [],
            "events": [],
            "announcements": [],
            "ads": []
        }

        current_section = None
        current_article = None
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 섹션 헤더
            if "[뉴스레터 정보]" in line:
                current_section = "info"
            elif "[헤드라인" in line:
                current_section = "headline"
            elif "[서브 기사" in line:
                current_section = "articles"
            elif "[인터뷰" in line or "[인물" in line:
                current_section = "interviews"
            elif "[이벤트" in line or "[일정" in line:
                current_section = "events"
            elif "[공지" in line:
                current_section = "announcements"
            elif "[광고" in line or "[배너" in line:
                current_section = "ads"
            else:
                if current_section == "info":
                    if "발행처:" in line:
                        result["publisher"] = line.split(":", 1)[1].strip()
                    elif "발행호:" in line:
                        result["issue"] = line.split(":", 1)[1].strip()
                    elif "발행일:" in line:
                        result["date"] = line.split(":", 1)[1].strip()
                elif current_section == "headline":
                    if "제목:" in line:
                        result["headline"]["title"] = line.split(":", 1)[1].strip()
                    elif "부제:" in line:
                        result["headline"]["subtitle"] = line.split(":", 1)[1].strip()
                    elif "내용:" in line:
                        result["headline"]["content"] = line.split(":", 1)[1].strip()
                elif current_section == "articles":
                    if line.startswith("기사") and ":" in line:
                        if current_article:
                            result["articles"].append(current_article)
                        current_article = {"title": "", "category": "", "summary": "", "content": ""}
                    elif current_article:
                        if "- 제목:" in line:
                            current_article["title"] = line.split(":", 1)[1].strip()
                        elif "- 카테고리:" in line:
                            current_article["category"] = line.split(":", 1)[1].strip()
                        elif "- 요약:" in line:
                            current_article["summary"] = line.split(":", 1)[1].strip()
                        elif "- 내용:" in line:
                            current_article["content"] = line.split(":", 1)[1].strip()
                elif current_section == "events":
                    if line.startswith("-"):
                        result["events"].append(line.lstrip("-•").strip())
                elif current_section == "announcements":
                    if line.startswith("-"):
                        result["announcements"].append(line.lstrip("-•").strip())
                elif current_section == "ads":
                    if line.startswith("-"):
                        result["ads"].append(line.lstrip("-•").strip())

        # 마지막 기사 추가
        if current_article and current_article.get("title"):
            result["articles"].append(current_article)

        return result

    def extract_catalog_info(self, image_base64: str, media_type: str = "image/jpeg", page_number: int = 1) -> dict:
        """카탈로그에서 구조화된 정보 추출"""
        if not self.client:
            return {"text": "", "structured": {}}

        try:
            if "base64," in image_base64:
                image_base64 = image_base64.split("base64,")[1]

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": f"""이 카탈로그/브로셔 이미지(페이지 {page_number})를 분석하여 구조화된 정보를 추출해주세요.

**추출 형식:**

[카탈로그 정보]
회사/브랜드명:
카탈로그 제목:
카테고리: (제품/서비스/회사소개 등)

[제품/서비스 목록]
항목1:
- 제품명:
- 가격: (있는 경우)
- 설명:
- 특징:
  - 특징1
  - 특징2
- 사양/스펙: (있는 경우)

항목2:
- 제품명:
- 가격:
- 설명:
- 특징:
- 사양/스펙:

[회사 소개] (있는 경우)
회사명:
설명:
연혁:
비전/미션:

[연락처/문의]
주소:
전화:
이메일:
웹사이트:
SNS:

[기타 정보]
- 배송정보:
- 보증/A/S:
- 주의사항:

**주의:**
- 모든 제품/서비스 정보를 빠짐없이 추출하세요
- 가격, 할인 정보를 정확히 추출하세요
- 제품 사양/스펙을 상세히 추출하세요"""
                            }
                        ],
                    }
                ],
            )

            raw_text = message.content[0].text.strip()
            return {
                "text": raw_text,
                "structured": self._parse_catalog_response(raw_text),
                "page_number": page_number
            }

        except Exception as e:
            logger.error(f"카탈로그 정보 추출 오류: {str(e)}", exc_info=True)
            return {"text": "", "structured": {}, "page_number": page_number}

    def _parse_catalog_response(self, text: str) -> dict:
        """카탈로그 응답을 구조화된 데이터로 파싱"""
        result = {
            "company": "",
            "catalog_title": "",
            "category": "",
            "products": [],
            "company_info": {"name": "", "description": "", "history": "", "vision": ""},
            "contact": {"address": "", "phone": "", "email": "", "website": "", "sns": ""},
            "other_info": {"shipping": "", "warranty": "", "notes": ""}
        }

        current_section = None
        current_product = None
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 섹션 헤더
            if "[카탈로그 정보]" in line:
                current_section = "info"
            elif "[제품" in line or "[서비스" in line:
                current_section = "products"
            elif "[회사 소개]" in line:
                current_section = "company"
            elif "[연락처" in line or "[문의" in line:
                current_section = "contact"
            elif "[기타 정보]" in line:
                current_section = "other"
            else:
                if current_section == "info":
                    if "회사/브랜드명:" in line or "회사명:" in line:
                        result["company"] = line.split(":", 1)[1].strip()
                    elif "카탈로그 제목:" in line:
                        result["catalog_title"] = line.split(":", 1)[1].strip()
                    elif "카테고리:" in line:
                        result["category"] = line.split(":", 1)[1].strip()
                elif current_section == "products":
                    if line.startswith("항목") and ":" in line:
                        if current_product:
                            result["products"].append(current_product)
                        current_product = {"name": "", "price": "", "description": "", "features": [], "specs": ""}
                    elif current_product:
                        if "- 제품명:" in line:
                            current_product["name"] = line.split(":", 1)[1].strip()
                        elif "- 가격:" in line:
                            current_product["price"] = line.split(":", 1)[1].strip()
                        elif "- 설명:" in line:
                            current_product["description"] = line.split(":", 1)[1].strip()
                        elif "- 특징:" in line:
                            continue  # 다음 줄들이 특징
                        elif line.startswith("  - "):
                            current_product["features"].append(line.lstrip(" -•").strip())
                        elif "- 사양" in line or "- 스펙" in line:
                            current_product["specs"] = line.split(":", 1)[1].strip() if ":" in line else ""
                elif current_section == "company":
                    if "회사명:" in line:
                        result["company_info"]["name"] = line.split(":", 1)[1].strip()
                    elif "설명:" in line:
                        result["company_info"]["description"] = line.split(":", 1)[1].strip()
                    elif "연혁:" in line:
                        result["company_info"]["history"] = line.split(":", 1)[1].strip()
                    elif "비전" in line or "미션" in line:
                        result["company_info"]["vision"] = line.split(":", 1)[1].strip()
                elif current_section == "contact":
                    if "주소:" in line:
                        result["contact"]["address"] = line.split(":", 1)[1].strip()
                    elif "전화:" in line:
                        result["contact"]["phone"] = line.split(":", 1)[1].strip()
                    elif "이메일:" in line:
                        result["contact"]["email"] = line.split(":", 1)[1].strip()
                    elif "웹사이트:" in line:
                        result["contact"]["website"] = line.split(":", 1)[1].strip()
                    elif "SNS:" in line:
                        result["contact"]["sns"] = line.split(":", 1)[1].strip()
                elif current_section == "other":
                    if "배송" in line:
                        result["other_info"]["shipping"] = line.split(":", 1)[1].strip() if ":" in line else ""
                    elif "보증" in line or "A/S" in line:
                        result["other_info"]["warranty"] = line.split(":", 1)[1].strip() if ":" in line else ""
                    elif "주의" in line:
                        result["other_info"]["notes"] = line.split(":", 1)[1].strip() if ":" in line else ""

        # 마지막 제품 추가
        if current_product and current_product.get("name"):
            result["products"].append(current_product)

        return result

    # ========== 다국어 번역 기능 ==========
    def translate_content(self, text: str, target_languages: list = None) -> dict:
        """
        Claude AI를 사용하여 텍스트를 여러 언어로 번역

        Args:
            text: 번역할 한국어 텍스트
            target_languages: 대상 언어 코드 목록 (기본: ['en', 'zh', 'ja', 'id', 'es', 'ru', 'fr'])

        Returns:
            {lang_code: translated_text} 형태의 딕셔너리
        """
        if not self.client or not text:
            return {}

        if target_languages is None:
            target_languages = ['en', 'zh', 'ja', 'id', 'es', 'ru', 'fr']

        lang_names = {
            'en': 'English',
            'zh': 'Chinese (Simplified)',
            'ja': 'Japanese',
            'id': 'Indonesian (Bahasa Indonesia)',
            'es': 'Spanish',
            'ru': 'Russian',
            'fr': 'French'
        }

        try:
            prompt = f"""아래 한국어 텍스트를 다음 언어로 번역해주세요.
번역 시 원문의 의미와 뉘앙스를 정확히 전달하세요.
성경 구절이나 종교적 내용의 경우 해당 언어의 공인된 번역을 참고하세요.

원문:
{text}

**출력 형식 (JSON):**
{{
{', '.join([f'    "{lang}": "번역된 텍스트"' for lang in target_languages])}
}}

각 언어 번역만 출력하세요. 설명이나 주석은 포함하지 마세요."""

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text.strip()

            # JSON 파싱 시도
            import json
            import re
            try:
                # JSON 블록 추출
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                # JSON 객체 찾기 (첫 번째 { 부터 마지막 } 까지)
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    response_text = json_match.group()

                translations = json.loads(response_text)
                return translations
            except json.JSONDecodeError as e:
                logger.warning(f"번역 응답 JSON 파싱 실패: {str(e)}, 응답: {response_text[:300]}")
                # 부분 파싱 시도: 각 언어별로 추출
                partial_translations = {}
                for lang in target_languages:
                    pattern = rf'"{lang}"\s*:\s*"([^"]*(?:\\.[^"]*)*)"'
                    match = re.search(pattern, response_text)
                    if match:
                        partial_translations[lang] = match.group(1).replace('\\"', '"').replace('\\n', '\n')
                if partial_translations:
                    logger.info(f"부분 번역 추출 성공: {list(partial_translations.keys())}")
                    return partial_translations
                return {}

        except Exception as e:
            logger.error(f"번역 오류: {str(e)}")
            return {}

    def translate_church_bulletin_content(self, data: dict) -> dict:
        """
        교회 주보 전체 콘텐츠를 다국어로 번역

        Args:
            data: 추출된 주보 데이터 (today_verse, sermon, devotional 등)

        Returns:
            translations 키가 추가된 데이터
        """
        translations = {
            'ko': {},  # 원본 한국어
            'en': {},
            'zh': {},
            'ja': {},
            'id': {},
            'es': {},
            'ru': {},
            'fr': {}
        }

        # 오늘의 말씀 번역
        verse_text = data.get('today_verse', {}).get('text', '')
        if verse_text:
            verse_translations = self.translate_content(verse_text)
            translations['ko']['verse_text'] = verse_text
            for lang, translated in verse_translations.items():
                translations[lang]['verse_text'] = translated

        # 설교 제목 번역
        sermon_title = data.get('sermon', {}).get('title', '')
        if sermon_title:
            title_translations = self.translate_content(sermon_title)
            translations['ko']['sermon_title'] = sermon_title
            for lang, translated in title_translations.items():
                translations[lang]['sermon_title'] = translated

        # 설교 서론 번역
        sermon_intro = data.get('sermon', {}).get('intro', '')
        if sermon_intro:
            intro_translations = self.translate_content(sermon_intro)
            translations['ko']['sermon_intro'] = sermon_intro
            for lang, translated in intro_translations.items():
                translations[lang]['sermon_intro'] = translated

        # 설교 포인트 번역
        points = data.get('sermon', {}).get('points', [])
        for i, point in enumerate(points):
            point_title = point.get('title', '')
            point_content = point.get('content', '')

            if point_title:
                pt_trans = self.translate_content(point_title)
                translations['ko'][f'sermon_point{i+1}_title'] = point_title
                for lang, translated in pt_trans.items():
                    translations[lang][f'sermon_point{i+1}_title'] = translated

            if point_content:
                pc_trans = self.translate_content(point_content)
                translations['ko'][f'sermon_point{i+1}_content'] = point_content
                for lang, translated in pc_trans.items():
                    translations[lang][f'sermon_point{i+1}_content'] = translated

        # 오늘의 양식 번역
        devotional_title = data.get('devotional', {}).get('title', '')
        devotional_content = data.get('devotional', {}).get('content', '')

        if devotional_title:
            dt_trans = self.translate_content(devotional_title)
            translations['ko']['devotional_title'] = devotional_title
            for lang, translated in dt_trans.items():
                translations[lang]['devotional_title'] = translated

        if devotional_content:
            dc_trans = self.translate_content(devotional_content)
            translations['ko']['devotional_content'] = devotional_content
            for lang, translated in dc_trans.items():
                translations[lang]['devotional_content'] = translated

        return translations


# 테스트
if __name__ == "__main__":
    ocr = VisionOCR()
    print(f"Client initialized: {ocr.client is not None}")
