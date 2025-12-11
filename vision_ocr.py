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
        """교회 주보에서 구조화된 정보 추출"""
        if not self.client:
            return {"text": "", "structured": {}}

        try:
            if "base64," in image_base64:
                image_base64 = image_base64.split("base64,")[1]

            # 페이지 번호에 따라 프롬프트 조정
            page_context = ""
            if page_number == 1:
                page_context = "이것은 주보 앞면입니다. 오늘의 말씀, 예배 시간, 예배 순서를 추출하세요."
            elif page_number == 2:
                page_context = "이것은 주보 뒷면입니다. 설교 본문, 찬양대 순서, 교회 소식을 추출하세요."

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
                                "text": f"""{page_context}

이 교회 주보 이미지를 정확하게 분석하여 정보를 추출해주세요.

**중요 원칙:**
1. 이미지에 보이는 모든 텍스트를 빠짐없이 추출하세요
2. 예배 순서의 모든 항목(사회, 성경봉독, 대표기도, 찬송, 설교)을 추출하세요
3. 찬송가 번호, 성경 구절 참조(예: 요한복음 3:16)를 정확히 추출하세요
4. 설교 전문 내용을 모두 추출하세요

**추출 형식:**

[오늘의 말씀]
본문: (성경 구절 텍스트)
출처: (예: 요한복음 3:16)

[예배 순서]
예배명: (1부예배/2·3·4부예배/5부예배/저녁예배)
사회: (담당자 이름)
성경봉독: (성경 구절 - 예: 요한복음 1:1-14)
대표기도: (담당자 이름)
찬송: (찬송가 번호 - 예: 94장)
설교: (설교 제목) / (담당 목사님)
(위 형식으로 모든 예배 순서 추출)

[설교]
제목: (설교 제목)
본문: (성경 구절)
목사: (설교자 이름)
내용:
(설교 전문 - 문단별로 구분하여 전체 내용 추출)

[찬양대]
예배: (몇 부 예배)
찬양대: (찬양대 이름)
곡명: (찬양 제목)
(각 예배별로 모든 찬양대 순서 추출)

[교회 소식]
- (소식1 - 제목과 내용 모두)
- (소식2)
...

[광고]
- (광고1)
- (광고2)
...

**주의:**
- 모든 텍스트를 순서대로 추출하세요
- 성경 구절 형식을 정확히 유지하세요 (예: 요한복음 3:16, 시편 23:1-6)
- 찬송가 번호를 정확히 추출하세요 (예: 94장, 새찬송가 94장)
- 설교 내용은 전체를 문단별로 추출하세요"""
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
        """교회 주보 응답을 구조화된 데이터로 파싱"""
        result = {
            "today_verse": {"text": "", "reference": ""},
            "worship_services": [],  # 예배 순서들
            "sermon": {"title": "", "scripture": "", "pastor": "", "content": []},
            "choir": [],  # 찬양대 순서
            "news": [],  # 교회 소식
            "announcements": [],  # 광고
            "other_text": ""
        }

        current_section = None
        current_service = None
        current_choir = None
        lines = text.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            i += 1

            if not line:
                continue

            # 섹션 헤더 감지
            if "[오늘의 말씀]" in line or "[금주의 말씀]" in line:
                current_section = "verse"
                continue
            elif "[예배 순서]" in line or "[예배순서]" in line:
                current_section = "worship"
                continue
            elif "[설교]" in line:
                current_section = "sermon"
                continue
            elif "[찬양대]" in line:
                current_section = "choir"
                continue
            elif "[교회 소식]" in line or "[소식]" in line:
                current_section = "news"
                continue
            elif "[광고]" in line:
                current_section = "announcements"
                continue

            # 섹션별 파싱
            if current_section == "verse":
                if line.startswith("본문:"):
                    result["today_verse"]["text"] = line.replace("본문:", "").strip()
                elif line.startswith("출처:"):
                    result["today_verse"]["reference"] = line.replace("출처:", "").strip()
                elif not result["today_verse"]["text"] and len(line) > 10:
                    result["today_verse"]["text"] = line

            elif current_section == "worship":
                if line.startswith("예배명:") or line.startswith("예배:"):
                    # 이전 예배 저장
                    if current_service:
                        result["worship_services"].append(current_service)
                    service_name = line.replace("예배명:", "").replace("예배:", "").strip()
                    current_service = {
                        "name": service_name,
                        "司會": "",  # 사회
                        "scripture": "",  # 성경봉독
                        "prayer": "",  # 대표기도
                        "hymn": "",  # 찬송
                        "sermon_title": "",
                        "sermon_pastor": ""
                    }
                elif current_service:
                    if line.startswith("사회:"):
                        current_service["司會"] = line.replace("사회:", "").strip()
                    elif line.startswith("성경봉독:"):
                        current_service["scripture"] = line.replace("성경봉독:", "").strip()
                    elif line.startswith("대표기도:"):
                        current_service["prayer"] = line.replace("대표기도:", "").strip()
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

            elif current_section == "sermon":
                if line.startswith("제목:"):
                    result["sermon"]["title"] = line.replace("제목:", "").strip()
                elif line.startswith("본문:"):
                    result["sermon"]["scripture"] = line.replace("본문:", "").strip()
                elif line.startswith("목사:") or line.startswith("설교자:"):
                    result["sermon"]["pastor"] = line.replace("목사:", "").replace("설교자:", "").strip()
                elif line.startswith("내용:"):
                    # 다음 줄들을 설교 내용으로 수집
                    continue
                elif line.startswith("-") or line.startswith("•"):
                    continue
                elif len(line) > 20:  # 긴 텍스트는 설교 내용
                    result["sermon"]["content"].append(line)

            elif current_section == "choir":
                if line.startswith("예배:"):
                    if current_choir:
                        result["choir"].append(current_choir)
                    current_choir = {
                        "service": line.replace("예배:", "").strip(),
                        "name": "",
                        "song": ""
                    }
                elif current_choir:
                    if line.startswith("찬양대:"):
                        current_choir["name"] = line.replace("찬양대:", "").strip()
                    elif line.startswith("곡명:"):
                        current_choir["song"] = line.replace("곡명:", "").strip()

            elif current_section == "news":
                if line.startswith("-") or line.startswith("•"):
                    news_item = line.lstrip("-•").strip()
                    if len(news_item) > 3:
                        result["news"].append(news_item)
                elif len(line) > 5:
                    result["news"].append(line)

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


# 테스트
if __name__ == "__main__":
    ocr = VisionOCR()
    print(f"Client initialized: {ocr.client is not None}")
