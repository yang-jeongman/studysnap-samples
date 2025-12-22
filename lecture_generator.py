"""
대학 강의자료 HTML 생성 모듈 - 완전 자동화 버전
================================================

주요 기능:
- Claude Vision OCR 연동으로 PDF 자동 분석
- 슬라이드/페이지별 구조화
- 수학 공식 (MathJax) 자동 인식 및 렌더링
- 코드 블록 (Highlight.js) 구문 강조
- 이미지 자동 추출 및 최적 배치
- 표 자동 인식 및 반응형 변환
- 목차 자동 생성 (접을 수 있는 네비게이션)
- 핵심 개념/키워드 자동 추출
- 플래시카드 자동 생성 (학습용)
- 퀴즈 자동 생성
- 진행률 표시 및 북마크
- 다크 모드 지원
- 모바일 최적화

사용법:
    from lecture_generator import LectureHTMLGenerator

    generator = LectureHTMLGenerator()
    html = generator.generate(extracted_data, title="미적분학 개론")
"""

import json
import logging
import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class LectureHTMLGenerator:
    """대학 강의자료 전용 HTML 생성기 - 완전 자동화 버전"""

    # 과목별 테마 색상
    SUBJECT_THEMES = {
        "math": {
            "name": "수학",
            "icon": "📐",
            "primary": "#4F46E5",
            "secondary": "#818CF8",
            "accent": "#C7D2FE",
            "gradient": "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)"
        },
        "physics": {
            "name": "물리학",
            "icon": "⚛️",
            "primary": "#0EA5E9",
            "secondary": "#38BDF8",
            "accent": "#BAE6FD",
            "gradient": "linear-gradient(135deg, #0EA5E9 0%, #06B6D4 100%)"
        },
        "chemistry": {
            "name": "화학",
            "icon": "🧪",
            "primary": "#8B5CF6",
            "secondary": "#A78BFA",
            "accent": "#DDD6FE",
            "gradient": "linear-gradient(135deg, #8B5CF6 0%, #A855F7 100%)"
        },
        "biology": {
            "name": "생물학",
            "icon": "🧬",
            "primary": "#10B981",
            "secondary": "#34D399",
            "accent": "#A7F3D0",
            "gradient": "linear-gradient(135deg, #10B981 0%, #059669 100%)"
        },
        "computer": {
            "name": "컴퓨터공학",
            "icon": "💻",
            "primary": "#EF4444",
            "secondary": "#F87171",
            "accent": "#FECACA",
            "gradient": "linear-gradient(135deg, #EF4444 0%, #F97316 100%)"
        },
        "economics": {
            "name": "경제학",
            "icon": "📊",
            "primary": "#F59E0B",
            "secondary": "#FBBF24",
            "accent": "#FDE68A",
            "gradient": "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)"
        },
        "engineering": {
            "name": "공학",
            "icon": "⚙️",
            "primary": "#6366F1",
            "secondary": "#818CF8",
            "accent": "#C7D2FE",
            "gradient": "linear-gradient(135deg, #6366F1 0%, #4F46E5 100%)"
        },
        "medicine": {
            "name": "의학",
            "icon": "🏥",
            "primary": "#EC4899",
            "secondary": "#F472B6",
            "accent": "#FBCFE8",
            "gradient": "linear-gradient(135deg, #EC4899 0%, #DB2777 100%)"
        },
        "law": {
            "name": "법학",
            "icon": "⚖️",
            "primary": "#78716C",
            "secondary": "#A8A29E",
            "accent": "#E7E5E4",
            "gradient": "linear-gradient(135deg, #78716C 0%, #57534E 100%)"
        },
        "general": {
            "name": "일반",
            "icon": "📚",
            "primary": "#4F46E5",
            "secondary": "#818CF8",
            "accent": "#C7D2FE",
            "gradient": "linear-gradient(135deg, #4F46E5 0%, #6366F1 100%)"
        }
    }

    # 과목 감지 키워드
    SUBJECT_KEYWORDS = {
        "math": ["미분", "적분", "방정식", "함수", "정리", "증명", "theorem", "calculus",
                 "derivative", "integral", "limit", "matrix", "벡터", "행렬", "선형대수"],
        "physics": ["물리", "운동", "에너지", "힘", "전자기", "양자", "physics", "force",
                    "velocity", "acceleration", "momentum", "thermodynamics", "파동"],
        "chemistry": ["화학", "분자", "원소", "반응", "결합", "chemistry", "molecule",
                      "atom", "compound", "organic", "원자", "화합물", "이온"],
        "biology": ["생물", "세포", "유전", "DNA", "단백질", "biology", "cell", "gene",
                    "protein", "enzyme", "진화", "생태계", "대사"],
        "computer": ["프로그래밍", "코드", "알고리즘", "자료구조", "python", "java",
                     "programming", "algorithm", "database", "네트워크", "운영체제"],
        "economics": ["경제", "수요", "공급", "시장", "가격", "economics", "market",
                      "GDP", "inflation", "금융", "투자", "무역"],
        "engineering": ["설계", "회로", "시스템", "제어", "engineering", "design",
                        "circuit", "signal", "control", "CAD"],
        "medicine": ["의학", "질병", "치료", "해부", "약리", "medicine", "disease",
                     "diagnosis", "anatomy", "pharmacology", "임상"],
        "law": ["법률", "헌법", "민법", "형법", "판례", "법원", "law", "legal",
                "constitution", "contract", "소송"]
    }

    def __init__(self):
        self.extracted_concepts = []
        self.generated_flashcards = []
        self.generated_quiz = []

    def detect_subject(self, text: str) -> str:
        """텍스트에서 과목 자동 감지"""
        text_lower = text.lower()
        scores = {}

        for subject, keywords in self.SUBJECT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                scores[subject] = score

        if scores:
            return max(scores, key=scores.get)
        return "general"

    def extract_structure(self, pages: List[Dict]) -> Dict:
        """페이지에서 구조 추출 (제목, 섹션, 이미지 등)"""
        structure = {
            "title": "",
            "subtitle": "",
            "author": "",
            "date": "",
            "sections": [],
            "images": [],
            "tables": [],
            "equations": [],
            "code_blocks": [],
            "key_concepts": [],
            "page_count": len(pages)
        }

        all_text = ""
        for i, page in enumerate(pages):
            page_text = page.get("text", "")
            page_images = page.get("images", [])
            all_text += page_text + "\n"

            # 이미지 수집
            for img in page_images:
                structure["images"].append({
                    "page": i + 1,
                    "path": img.get("path", ""),
                    "caption": img.get("caption", ""),
                    "base64": img.get("base64", "")
                })

        # 제목 추출 (첫 번째 큰 텍스트 또는 # 헤딩)
        title_match = re.search(r'^#\s+(.+)$', all_text, re.MULTILINE)
        if title_match:
            structure["title"] = title_match.group(1).strip()

        # 섹션 추출
        sections = self._extract_sections(all_text)
        structure["sections"] = sections

        # 표 추출
        tables = self._extract_tables(all_text)
        structure["tables"] = tables

        # 수식 추출
        equations = self._extract_equations(all_text)
        structure["equations"] = equations

        # 코드 블록 추출
        code_blocks = self._extract_code_blocks(all_text)
        structure["code_blocks"] = code_blocks

        # 핵심 개념 추출
        key_concepts = self._extract_key_concepts(all_text)
        structure["key_concepts"] = key_concepts

        return structure

    def _extract_sections(self, text: str) -> List[Dict]:
        """섹션/챕터 추출"""
        sections = []

        # Markdown 헤딩 패턴
        heading_pattern = r'^(#{1,3})\s+(.+)$'

        # 숫자 기반 제목 패턴 (1. 제목, 1.1 소제목)
        number_pattern = r'^(\d+(?:\.\d+)*)\s*[\.)\s]\s*(.+)$'

        lines = text.split('\n')
        current_section = None
        current_content = []

        for line in lines:
            # Markdown 헤딩
            md_match = re.match(heading_pattern, line)
            if md_match:
                if current_section:
                    current_section["content"] = "\n".join(current_content).strip()
                    sections.append(current_section)

                level = len(md_match.group(1))
                current_section = {
                    "level": level,
                    "title": md_match.group(2).strip(),
                    "content": ""
                }
                current_content = []
                continue

            # 숫자 기반 제목
            num_match = re.match(number_pattern, line)
            if num_match:
                number = num_match.group(1)
                level = len(number.split('.'))

                if current_section:
                    current_section["content"] = "\n".join(current_content).strip()
                    sections.append(current_section)

                current_section = {
                    "level": level,
                    "number": number,
                    "title": num_match.group(2).strip(),
                    "content": ""
                }
                current_content = []
                continue

            if current_section:
                current_content.append(line)

        # 마지막 섹션 추가
        if current_section:
            current_section["content"] = "\n".join(current_content).strip()
            sections.append(current_section)

        return sections

    def _extract_tables(self, text: str) -> List[Dict]:
        """표 추출 및 파싱"""
        tables = []

        # Markdown 표 패턴
        table_pattern = r'(\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)+)'

        matches = re.findall(table_pattern, text)
        for match in matches:
            lines = match.strip().split('\n')
            if len(lines) >= 2:
                # 헤더 파싱
                header = [cell.strip() for cell in lines[0].split('|')[1:-1]]

                # 데이터 파싱 (구분자 라인 건너뜀)
                data = []
                for line in lines[2:]:
                    if '|' in line:
                        row = [cell.strip() for cell in line.split('|')[1:-1]]
                        if row:
                            data.append(row)

                tables.append({
                    "header": header,
                    "data": data,
                    "original": match
                })

        return tables

    def _extract_equations(self, text: str) -> List[Dict]:
        """수학 수식 추출"""
        equations = []

        # Display math: $$...$$ 또는 \[...\]
        display_pattern = r'\$\$(.+?)\$\$|\\\[(.+?)\\\]'
        for match in re.finditer(display_pattern, text, re.DOTALL):
            eq = match.group(1) or match.group(2)
            equations.append({
                "type": "display",
                "latex": eq.strip(),
                "original": match.group(0)
            })

        # Inline math: $...$ 또는 \(...\)
        inline_pattern = r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)|\\(\(.+?\\\))'
        for match in re.finditer(inline_pattern, text):
            eq = match.group(1) or match.group(2)
            if eq:
                equations.append({
                    "type": "inline",
                    "latex": eq.strip(),
                    "original": match.group(0)
                })

        return equations

    def _extract_code_blocks(self, text: str) -> List[Dict]:
        """코드 블록 추출"""
        code_blocks = []

        # Markdown 코드 블록: ```language ... ```
        pattern = r'```(\w*)\n(.*?)```'
        for match in re.finditer(pattern, text, re.DOTALL):
            lang = match.group(1) or "plaintext"
            code = match.group(2).strip()
            code_blocks.append({
                "language": lang,
                "code": code,
                "original": match.group(0)
            })

        return code_blocks

    def _extract_key_concepts(self, text: str) -> List[Dict]:
        """핵심 개념 및 정의 추출 - 실제 내용 기반"""
        concepts = []
        seen = set()

        # 1. **용어**: 설명 패턴 (가장 유용한 패턴)
        # 예: **힘의 정의**: 물체의 운동 상태를 변화시키는 원인
        term_def_pattern = r'\*\*([^*:]+)\*\*\s*[:\-]\s*([^\n]+)'
        for match in re.finditer(term_def_pattern, text):
            term = match.group(1).strip()
            definition = match.group(2).strip()
            # 라벨성 용어 제외
            if self._is_label_text(term):
                continue
            # 정의가 있고 의미있는 길이인 경우
            if definition and len(definition) > 10 and term not in seen:
                seen.add(term)
                concepts.append({
                    "text": term,
                    "definition": definition,
                    "type": "definition"
                })

        # 2. 리스트 항목에서 개념 추출
        # 예: - 관성: 물체가 현재 운동 상태를 유지하려는 성질
        list_concept_pattern = r'[-•]\s*([^:\n]+):\s*([^\n]+)'
        for match in re.finditer(list_concept_pattern, text):
            term = match.group(1).strip()
            definition = match.group(2).strip()
            if len(term) > 1 and len(term) < 30 and len(definition) > 5:
                if not self._is_label_text(term) and term not in seen:
                    seen.add(term)
                    concepts.append({
                        "text": term,
                        "definition": definition,
                        "type": "term"
                    })

        # 3. 수식 정의 추출
        # 예: $F = ma$ 앞뒤 문맥에서 의미 추출
        equation_pattern = r'([^\n]*?)\$([^$]+)\$([^\n]*)'
        for match in re.finditer(equation_pattern, text):
            before = match.group(1).strip()
            equation = match.group(2).strip()
            after = match.group(3).strip()

            # 수식이 의미있는 것인지 확인 (단순 변수가 아닌)
            if len(equation) > 3 and '=' in equation:
                context = (before + ' ' + after).strip()
                if len(context) > 5:
                    eq_key = equation[:20]
                    if eq_key not in seen:
                        seen.add(eq_key)
                        concepts.append({
                            "text": f"${equation}$",
                            "definition": context if context else "수식의 의미를 이해하세요",
                            "type": "equation"
                        })

        # 4. 섹션 콘텐츠에서 첫 문장 추출 (정의 성격)
        # 예: "물체의 가속도는 작용하는 알짜힘에 비례하고..."
        sentence_pattern = r'(?:^|\n)([가-힣][^.\n]{20,100}[다니요]\.)'
        for match in re.finditer(sentence_pattern, text):
            sentence = match.group(1).strip()
            # 이미 추출된 개념과 중복 체크
            if sentence not in seen and not self._is_label_text(sentence):
                # 문장의 핵심 키워드 추출
                keywords = re.findall(r'([가-힣]+(?:도|력|량|법칙|에너지|운동))', sentence)
                if keywords:
                    key = keywords[0]
                    if key not in seen:
                        seen.add(key)
                        concepts.append({
                            "text": key,
                            "definition": sentence,
                            "type": "concept"
                        })

        return concepts[:15]  # 최대 15개

    def _is_label_text(self, text: str) -> bool:
        """라벨성 텍스트인지 확인"""
        if not text:
            return True
        text = text.strip().rstrip(':').rstrip('-')

        # 라벨 키워드
        label_keywords = {
            '핵심', '개념', '정의', '예시', '예제', '중요', '참고', '주의', '요약',
            '실생활', '단위', '팁', '기둥', '법칙', 'Note', 'Key', 'Example',
            'Important', 'Definition', 'Tip'
        }

        # 정확히 일치하거나 콜론으로 끝나는 경우
        if text in label_keywords or text.endswith(':') or text.endswith('-'):
            return True

        # 라벨 키워드로 시작하는 경우
        for kw in label_keywords:
            if text.startswith(kw) and len(text) < len(kw) + 10:
                return True

        return False

    def generate_flashcards(self, structure: Dict) -> List[Dict]:
        """핵심 개념으로 플래시카드 자동 생성 - 실제 정의 기반"""
        flashcards = []
        seen_texts = set()  # 중복 방지

        # 1. 핵심 개념에서 생성 (정의가 있는 것 우선)
        for concept in structure.get("key_concepts", []):
            term = concept.get("text", "").strip()
            definition = concept.get("definition", "").strip()
            concept_type = concept.get("type", "term")

            # 중복 체크
            if term in seen_texts or len(term) < 2:
                continue
            seen_texts.add(term)

            # 정의가 있는 경우 - 고품질 플래시카드
            if definition and len(definition) > 10:
                if concept_type == "equation":
                    # 수식 카드
                    flashcards.append({
                        "front": f"다음 수식의 의미는?\n{term}",
                        "back": definition,
                        "type": "equation"
                    })
                else:
                    # 용어/개념 카드
                    flashcards.append({
                        "front": f"'{term}'이란?",
                        "back": definition,
                        "type": concept_type
                    })

        # 2. 섹션 내용에서 추가 카드 생성 (정의 기반 카드가 부족할 때)
        if len(flashcards) < 5:
            for section in structure.get("sections", []):
                if len(flashcards) >= 10:
                    break

                title = section.get("title", "").strip()
                content = section.get("content", "").strip()

                if not title or title in seen_texts:
                    continue

                # 섹션 내용에서 첫 문장 추출
                if content and len(content) > 30:
                    # 첫 문장 추출 시도
                    first_sentence = content.split('.')[0].strip() if '.' in content else content[:100]
                    if len(first_sentence) > 20:
                        seen_texts.add(title)
                        flashcards.append({
                            "front": f"'{title}'에 대해 설명하시오.",
                            "back": first_sentence + ".",
                            "type": "section"
                        })

        # 3. 수식에서 추가 생성 (아직 포함되지 않은 것)
        for eq in structure.get("equations", [])[:5]:
            if len(flashcards) >= 10:
                break
            if eq.get("type") == "display":
                latex = eq.get("latex", "").strip()
                eq_key = latex[:30]
                if eq_key not in seen_texts and len(latex) > 5:
                    seen_texts.add(eq_key)
                    flashcards.append({
                        "front": f"다음 수식을 설명하시오:\n$${latex}$$",
                        "back": "수식의 각 기호(변수)와 물리적 의미를 설명하세요.",
                        "type": "equation"
                    })

        # 최대 10개로 제한
        self.generated_flashcards = flashcards[:10]
        return self.generated_flashcards

    def generate_quiz(self, structure: Dict, text: str) -> List[Dict]:
        """향상된 퀴즈 자동 생성 - 핵심 개념 정의 기반"""
        quiz = []
        seen_questions = set()

        # 1. 핵심 개념(정의 있는 것)에서 퀴즈 생성 - 최우선
        for concept in structure.get("key_concepts", []):
            if len(quiz) >= 5:
                break

            term = concept.get("text", "").strip()
            definition = concept.get("definition", "").strip()
            concept_type = concept.get("type", "term")

            if not term or term in seen_questions:
                continue
            if not definition or len(definition) < 15:
                continue

            seen_questions.add(term)

            if concept_type == "equation":
                # 수식 퀴즈
                quiz.append({
                    "id": len(quiz) + 1,
                    "type": "equation",
                    "question": f"다음 수식이 나타내는 의미는?\n{term}",
                    "answer": definition,
                    "hint": "수식의 각 기호와 물리적 의미를 생각해보세요."
                })
            else:
                # 용어/개념 퀴즈
                quiz.append({
                    "id": len(quiz) + 1,
                    "type": "definition",
                    "question": f"'{term}'을(를) 정의하시오.",
                    "answer": definition,
                    "hint": f"'{term}'의 핵심적인 의미를 떠올려보세요."
                })

        # 2. 섹션 내용에서 추가 퀴즈 생성
        if len(quiz) < 5:
            sections = structure.get("sections", [])
            for section in sections:
                if len(quiz) >= 5:
                    break

                title = section.get("title", "").strip()
                content = section.get("content", "").strip()

                # 중복 방지 및 유효성 검사
                if not title or title in seen_questions:
                    continue
                if not content or len(content) < 50:
                    continue

                seen_questions.add(title)

                # 섹션 내용에서 첫 문장 추출
                first_sentence = content.split('.')[0].strip() if '.' in content else content[:100].strip()
                if len(first_sentence) > 20:
                    quiz.append({
                        "id": len(quiz) + 1,
                        "type": "short_answer",
                        "question": f"'{title}'에 대해 설명하시오.",
                        "answer": first_sentence + ".",
                        "hint": f"이 섹션의 핵심 내용을 정리해보세요."
                    })

        # 3. 수식이 있으면 수식 관련 퀴즈 추가
        if len(quiz) < 5:
            equations = structure.get("equations", [])
            for eq in equations[:3]:
                if len(quiz) >= 5:
                    break
                if eq.get("type") == "display":
                    latex = eq.get("latex", "").strip()
                    eq_key = latex[:30]
                    if latex and eq_key not in seen_questions:
                        seen_questions.add(eq_key)
                        quiz.append({
                            "id": len(quiz) + 1,
                            "type": "equation",
                            "question": f"다음 수식의 물리적 의미를 설명하시오.\n$${latex}$$",
                            "answer": "수식의 각 변수와 법칙/원리를 설명해보세요.",
                            "hint": "F, m, a 등 각 기호의 의미를 생각해보세요."
                        })

        # 4. 퀴즈가 여전히 부족하면 일반 복습 질문
        if len(quiz) < 3:
            general_questions = [
                ("이 강의에서 배운 핵심 개념 3가지를 나열하시오.",
                 "각 섹션에서 강조된 내용을 떠올려보세요."),
                ("오늘 배운 내용을 실생활 예시로 설명하시오.",
                 "일상에서 볼 수 있는 현상과 연결해보세요."),
            ]
            for q, hint in general_questions:
                if len(quiz) >= 5:
                    break
                if q not in seen_questions:
                    quiz.append({
                        "id": len(quiz) + 1,
                        "type": "open_ended",
                        "question": q,
                        "answer": "배운 내용을 바탕으로 자유롭게 답변하세요.",
                        "hint": hint
                    })

        self.generated_quiz = quiz[:5]
        return self.generated_quiz

    def generate(
        self,
        extracted_data: Dict[str, Any],
        title: str = "",
        subject: str = None,
        options: Dict = None
    ) -> str:
        """
        강의자료 HTML 생성 (메인 진입점)

        Args:
            extracted_data: OCR로 추출된 데이터 {"pages": [...], "metadata": {...}}
            title: 문서 제목 (없으면 자동 추출)
            subject: 과목 (없으면 자동 감지)
            options: 추가 옵션
                - show_flashcards: 플래시카드 표시 (default: True)
                - show_quiz: 퀴즈 표시 (default: True)
                - show_toc: 목차 표시 (default: True)
                - show_progress: 진행률 표시 (default: True)

        Returns:
            완성된 HTML 문자열
        """
        options = options or {}
        show_flashcards = options.get("show_flashcards", True)
        show_quiz = options.get("show_quiz", True)
        show_toc = options.get("show_toc", True)
        show_progress = options.get("show_progress", True)

        pages = extracted_data.get("pages", [])
        metadata = extracted_data.get("metadata", {})

        # 전체 텍스트 합치기
        all_text = "\n".join([p.get("text", "") for p in pages])

        # 구조 추출
        structure = self.extract_structure(pages)

        # 제목 결정
        final_title = title or structure.get("title") or metadata.get("title", "강의자료")

        # 과목 자동 감지
        detected_subject = subject or self.detect_subject(all_text)
        theme = self.SUBJECT_THEMES.get(detected_subject, self.SUBJECT_THEMES["general"])

        # 플래시카드 생성
        flashcards = self.generate_flashcards(structure) if show_flashcards else []

        # 퀴즈 생성
        quiz = self.generate_quiz(structure, all_text) if show_quiz else []

        # HTML 빌드
        html = self._build_html(
            title=final_title,
            structure=structure,
            theme=theme,
            subject=detected_subject,
            all_text=all_text,
            flashcards=flashcards,
            quiz=quiz,
            options={
                "show_toc": show_toc,
                "show_progress": show_progress,
                "show_flashcards": show_flashcards,
                "show_quiz": show_quiz
            },
            metadata=metadata
        )

        return html

    def _build_toc_html(self, sections: List[Dict]) -> str:
        """목차 HTML 생성 (기존 호환용)"""
        return self._build_toc_items_html(sections)

    def _build_toc_items_html(self, sections: List[Dict]) -> str:
        """새 스타일 목차 아이템 HTML 생성"""
        if not sections:
            return ""

        toc_items = []
        for i, section in enumerate(sections):
            level = section.get("level", 1)
            title = section.get("title", "")
            number = section.get("number", str(i + 1))

            # 레벨 1, 2만 목차에 표시
            if level <= 2:
                toc_items.append(f'''
                    <a href="#chapter-{i}" class="toc-item">
                        <div class="toc-item-number">{number if number else i + 1}</div>
                        <div class="toc-item-title">{title}</div>
                    </a>
                ''')

        return "\n".join(toc_items)

    def _build_sections_html(self, sections: List[Dict], theme: Dict) -> str:
        """섹션 콘텐츠 HTML 생성 (기존 호환용)"""
        return self._build_chapters_html(sections, theme)

    def _build_chapters_html(self, sections: List[Dict], theme: Dict) -> str:
        """새 스타일 챕터 섹션 HTML 생성"""
        if not sections:
            return ""

        html_parts = []
        chapter_num = 0

        for i, section in enumerate(sections):
            level = section.get("level", 1)
            title = section.get("title", "")
            number = section.get("number", "")
            content = section.get("content", "")

            # 콘텐츠 처리 (코드 블록, 수식, 특별 박스 등)
            processed_content = self._process_content_enhanced(content)

            # 레벨 1은 메인 챕터, 레벨 2 이상은 서브섹션
            if level == 1:
                chapter_num += 1
                display_number = number if number else str(chapter_num)

                html_parts.append(f'''
                <section class="chapter-section" id="chapter-{i}" data-chapter="{i}">
                    <div class="chapter-header">
                        <div class="chapter-header-left">
                            <div class="chapter-number">{display_number}</div>
                            <div class="chapter-title">{title}</div>
                        </div>
                        <button class="bookmark-btn" onclick="toggleBookmark(this, {i})" title="북마크">🔖</button>
                    </div>
                    <div class="chapter-content">
                        <div class="content-text">
                            {processed_content}
                        </div>
                    </div>
                </section>
                ''')
            else:
                # 서브섹션은 이전 챕터 내에 포함
                display_number = number if number else f"{chapter_num}.{level - 1}"
                html_parts.append(f'''
                <section class="chapter-section sub-chapter" id="chapter-{i}" data-chapter="{i}">
                    <div class="chapter-header">
                        <div class="chapter-header-left">
                            <div class="chapter-number" style="font-size: 1em; width: 40px; height: 40px;">{display_number}</div>
                            <div class="chapter-title" style="font-size: 1.1em;">{title}</div>
                        </div>
                    </div>
                    <div class="chapter-content">
                        <div class="content-text">
                            {processed_content}
                        </div>
                    </div>
                </section>
                ''')

        return "\n".join(html_parts)

    def _process_content_enhanced(self, content: str) -> str:
        """향상된 콘텐츠 처리 (특별 박스 포함)"""
        if not content:
            return ""

        # 코드 블록 변환
        def replace_code_block(match):
            lang = match.group(1) or "plaintext"
            code = match.group(2).strip()
            # HTML 이스케이프
            code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            return f'''
<div class="code-block">
    <div class="code-header">
        <span class="code-lang">{lang}</span>
        <button class="copy-btn" onclick="copyCode(this)">복사</button>
    </div>
    <pre><code class="language-{lang}">{code}</code></pre>
</div>'''

        content = re.sub(r'```(\w*)\n(.*?)```', replace_code_block, content, flags=re.DOTALL)

        # 핵심 개념 박스 (Key:, 핵심:, Definition: 등)
        def replace_key_concept(match):
            text = match.group(1).strip()
            return f'''
<div class="info-box key-concept-box">
    <div class="box-title">💡 핵심 개념</div>
    <p>{text}</p>
</div>'''

        content = re.sub(r'(?:핵심|Key|Definition|정의)\s*[:\-]\s*(.+?)(?=\n\n|\n[#\d]|$)', replace_key_concept, content, flags=re.IGNORECASE | re.DOTALL)

        # 예제 박스 (Example:, 예제: 등) - **bold**로 시작하는 것 제외
        def replace_example(match):
            text = match.group(1).strip()
            # 빈 텍스트나 **로 끝나는 경우 스킵 (실생활 예시:** 같은 경우)
            if not text or text.endswith('**') or len(text) < 5:
                return match.group(0)  # 원본 반환
            return f'''
<div class="info-box example-box">
    <div class="box-title">📝 예제</div>
    <p>{text}</p>
</div>'''

        # **실생활 예시:** 같은 패턴은 제외 (앞에 **가 있으면 매칭 안함)
        content = re.sub(r'(?<!\*\*)(?:예제|Example)\s*[:\-]\s*(.+?)(?=\n\n|\n[#\d]|$)', replace_example, content, flags=re.IGNORECASE | re.DOTALL)

        # 중요 박스 (Important:, 중요: 등)
        def replace_important(match):
            text = match.group(1).strip()
            return f'''
<div class="info-box important-box">
    <div class="box-title">⚠️ 중요</div>
    <p>{text}</p>
</div>'''

        content = re.sub(r'(?:중요|Important|Note|참고)\s*[:\-]\s*(.+?)(?=\n\n|\n[#\d]|$)', replace_important, content, flags=re.IGNORECASE | re.DOTALL)

        # 수식 블록 ($$...$$)을 특별 스타일로
        def replace_display_math(match):
            eq = match.group(1).strip()
            return f'''
<div class="equation-block">
$${eq}$$
</div>'''

        content = re.sub(r'\$\$(.+?)\$\$', replace_display_math, content, flags=re.DOTALL)

        # 블록 인용문 (> 로 시작하는 라인)
        def replace_blockquote(match):
            quote_text = match.group(1).strip()
            # 여러 줄의 인용문 처리
            lines = quote_text.split('\n')
            cleaned_lines = [re.sub(r'^>\s*', '', line).strip() for line in lines]
            return f'''
<blockquote class="quote-box">
    <p>{'<br>'.join(cleaned_lines)}</p>
</blockquote>'''

        content = re.sub(r'^((?:>.*\n?)+)', replace_blockquote, content, flags=re.MULTILINE)

        # 리스트 변환 (- 또는 * 로 시작)
        def replace_list(match):
            list_text = match.group(0)
            items = re.findall(r'^[\-\*]\s*(.+)$', list_text, re.MULTILINE)
            if items:
                list_items = ''.join([f'<li>{item.strip()}</li>' for item in items])
                return f'<ul class="content-list">{list_items}</ul>'
            return list_text

        content = re.sub(r'((?:^[\-\*]\s+.+$\n?)+)', replace_list, content, flags=re.MULTILINE)

        # 숫자 리스트 변환 (1. 2. 3. 등)
        def replace_ordered_list(match):
            list_text = match.group(0)
            items = re.findall(r'^\d+\.\s*(.+)$', list_text, re.MULTILINE)
            if items:
                list_items = ''.join([f'<li>{item.strip()}</li>' for item in items])
                return f'<ol class="content-list">{list_items}</ol>'
            return list_text

        content = re.sub(r'((?:^\d+\.\s+.+$\n?)+)', replace_ordered_list, content, flags=re.MULTILINE)

        # 마크다운 테이블 변환
        def replace_markdown_table(match):
            table_text = match.group(0).strip()
            lines = [l.strip() for l in table_text.split('\n') if l.strip()]

            if len(lines) < 2:
                return table_text

            # 헤더 행
            header_line = lines[0]
            # 구분자 행 (|---|---|) 건너뛰기
            data_lines = [l for l in lines[1:] if not re.match(r'^\|[\s\-:]+\|$', l.replace('|', '| |'))]

            # 셀 파싱
            def parse_row(line):
                cells = [c.strip() for c in line.split('|')]
                # 앞뒤 빈 셀 제거
                cells = [c for c in cells if c]
                return cells

            headers = parse_row(header_line)
            if not headers:
                return table_text

            # HTML 테이블 생성
            html = '<div class="table-container"><table class="data-table">'

            # 헤더
            html += '<thead><tr>'
            for h in headers:
                html += f'<th>{h}</th>'
            html += '</tr></thead>'

            # 데이터 행
            html += '<tbody>'
            for line in data_lines:
                if '---' in line:
                    continue
                cells = parse_row(line)
                if cells:
                    html += '<tr>'
                    for c in cells:
                        html += f'<td>{c}</td>'
                    html += '</tr>'
            html += '</tbody></table></div>'

            return html

        # 마크다운 테이블 패턴: | ... | 로 시작하는 연속된 줄
        content = re.sub(r'((?:^\|.+\|\s*\n?)+)', replace_markdown_table, content, flags=re.MULTILINE)

        # 줄바꿈 처리
        lines = content.split('\n')
        processed_lines = []
        in_special = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # HTML 태그로 시작하면 그대로 유지
            if stripped.startswith('<') or stripped.startswith('</'):
                processed_lines.append(line)
                if '<div' in stripped or '<ul' in stripped or '<ol' in stripped or '<blockquote' in stripped:
                    in_special = '</div>' not in stripped and '</ul>' not in stripped and '</ol>' not in stripped and '</blockquote>' not in stripped
                elif '</div>' in stripped or '</ul>' in stripped or '</ol>' in stripped or '</blockquote>' in stripped:
                    in_special = False
            elif in_special:
                processed_lines.append(line)
            else:
                processed_lines.append(f'<p>{stripped}</p>')

        return "\n".join(processed_lines) if processed_lines else f'<p>{content}</p>'

    def _process_content(self, content: str) -> str:
        """콘텐츠 처리 (코드 블록, 수식 변환)"""
        if not content:
            return ""

        # 코드 블록 변환
        def replace_code_block(match):
            lang = match.group(1) or "plaintext"
            code = match.group(2).strip()
            # HTML 이스케이프
            code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            return f'''
<div class="code-block">
    <div class="code-header">
        <span class="code-lang">{lang}</span>
        <button class="copy-btn" onclick="copyCode(this)">📋 복사</button>
    </div>
    <pre><code class="language-{lang}">{code}</code></pre>
</div>'''

        content = re.sub(r'```(\w*)\n(.*?)```', replace_code_block, content, flags=re.DOTALL)

        # 줄바꿈을 <br>로 (단, 코드 블록 내부 제외)
        lines = content.split('\n')
        processed_lines = []
        for line in lines:
            if line.strip():
                processed_lines.append(f'<p>{line}</p>')

        return "\n".join(processed_lines) if processed_lines else f'<p>{content}</p>'

    def _build_flashcards_html(self, flashcards: List[Dict]) -> str:
        """플래시카드 HTML 생성"""
        if not flashcards:
            return ""

        cards_html = []
        for i, card in enumerate(flashcards):
            cards_html.append(f'''
                <div class="flashcard" data-index="{i}" onclick="flipCard(this)">
                    <div class="flashcard-inner">
                        <div class="flashcard-front">
                            <div class="card-content">{card["front"]}</div>
                            <div class="card-hint">클릭하여 뒤집기</div>
                        </div>
                        <div class="flashcard-back">
                            <div class="card-content">{card["back"]}</div>
                        </div>
                    </div>
                </div>
            ''')

        return f'''
        <div class="flashcards-section">
            <h3 class="section-header">📇 플래시카드 ({len(flashcards)}개)</h3>
            <div class="flashcards-container">
                {" ".join(cards_html)}
            </div>
            <div class="flashcard-controls">
                <button onclick="prevCard()" class="nav-btn">◀ 이전</button>
                <span class="card-counter">1 / {len(flashcards)}</span>
                <button onclick="nextCard()" class="nav-btn">다음 ▶</button>
            </div>
        </div>
        '''

    def _build_quiz_html(self, quiz: List[Dict]) -> str:
        """퀴즈 HTML 생성"""
        if not quiz:
            return ""

        questions_html = []
        for q in quiz:
            questions_html.append(f'''
                <div class="quiz-question" data-id="{q["id"]}" data-answer="{q["answer"]}">
                    <div class="question-text">
                        <span class="q-number">Q{q["id"]}.</span>
                        {q["question"]}
                    </div>
                    <div class="answer-input">
                        <input type="text" placeholder="답을 입력하세요" class="quiz-input">
                        <button onclick="checkAnswer(this)" class="check-btn">확인</button>
                    </div>
                    <div class="hint-text" style="display: none;">힌트: {q.get("hint", "")}</div>
                    <div class="result-text"></div>
                </div>
            ''')

        return f'''
        <div class="quiz-section">
            <h3 class="section-header">📝 퀴즈 ({len(quiz)}문제)</h3>
            <div class="quiz-container">
                {" ".join(questions_html)}
            </div>
            <div class="quiz-summary" style="display: none;">
                <div class="score">점수: <span id="quiz-score">0</span> / {len(quiz)}</div>
            </div>
        </div>
        '''

    def _build_key_concepts_html(self, concepts: List[Dict]) -> str:
        """핵심 개념 HTML 생성 - 정의 포함"""
        if not concepts:
            return ""

        items = []
        for concept in concepts:
            term = concept.get("text", "").strip()
            definition = concept.get("definition", "").strip()
            concept_type = concept.get("type", "term")

            # 아이콘 선택: 정의형은 📌, 용어는 🔑, 수식은 📐
            if concept_type == "definition":
                icon = "📌"
            elif concept_type == "equation":
                icon = "📐"
            else:
                icon = "🔑"

            # 정의가 있으면 툴팁으로 표시
            if definition and len(definition) > 5:
                # 정의가 길면 잘라서 표시
                short_def = definition[:80] + "..." if len(definition) > 80 else definition
                items.append(f'<span class="concept-tag" title="{definition}">{icon} <strong>{term}</strong>: {short_def}</span>')
            else:
                items.append(f'<span class="concept-tag">{icon} {term}</span>')

        return f'''
        <div class="key-concepts-section">
            <h3 class="section-header">💡 핵심 개념 ({len(concepts)}개)</h3>
            <div class="concepts-container">
                {" ".join(items)}
            </div>
        </div>
        '''

    def _build_html(
        self,
        title: str,
        structure: Dict,
        theme: Dict,
        subject: str,
        all_text: str,
        flashcards: List[Dict],
        quiz: List[Dict],
        options: Dict,
        metadata: Dict
    ) -> str:
        """최종 HTML 문서 생성 - 고품질 템플릿 적용"""

        # 수학 수식 포함 여부
        has_math = bool(structure.get("equations")) or '$' in all_text or '\\[' in all_text
        # 코드 블록 포함 여부
        has_code = bool(structure.get("code_blocks")) or '```' in all_text

        # 목차 아이템 (챕터 네비게이션용)
        sections = structure.get("sections", [])
        toc_items = self._build_toc_items_html(sections) if options.get("show_toc") else ""

        # 챕터 섹션 HTML (고급 스타일)
        chapters_html = self._build_chapters_html(sections, theme)

        # 핵심 개념 HTML
        concepts_html = self._build_key_concepts_html(structure.get("key_concepts", []))

        # 플래시카드 HTML
        flashcards_html = self._build_flashcards_html(flashcards) if options.get("show_flashcards") else ""

        # 퀴즈 HTML
        quiz_html = self._build_quiz_html(quiz) if options.get("show_quiz") else ""

        # 표 HTML (섹션 내부로 통합)
        tables_html = ""
        for table in structure.get("tables", []):
            tables_html += self._build_table_html(table)

        # 이미지 HTML (섹션 내부로 통합)
        images_html = ""
        for img in structure.get("images", []):
            if img.get("base64"):
                images_html += f'''
                <div class="image-container">
                    <img src="data:image/png;base64,{img["base64"]}" alt="{img.get("caption", "")}">
                    {f'<p class="image-caption">{img["caption"]}</p>' if img.get("caption") else ''}
                </div>
                '''
            elif img.get("path"):
                images_html += f'''
                <div class="image-container">
                    <img src="{img["path"]}" alt="{img.get("caption", "")}">
                    {f'<p class="image-caption">{img["caption"]}</p>' if img.get("caption") else ''}
                </div>
                '''

        # 메인 콘텐츠 (섹션이 없으면 전체 텍스트)
        main_content = chapters_html if chapters_html else f'''
        <div class="chapter-section" id="chapter-1">
            <div class="chapter-title">
                <div class="chapter-number">1</div>
                강의 내용
            </div>
            <div class="content-text">
                {self._process_content(all_text)}
            </div>
        </div>
        '''

        # 페이지 수
        page_count = structure.get("page_count", 0)
        section_count = len(sections)

        # 작성자/날짜 정보
        author = metadata.get("author", "") or structure.get("author", "")
        date_info = metadata.get("date", "") or structure.get("date", "")

        # MathJax 스크립트
        mathjax_script = '''
    <script>
        MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
                processEscapes: true
            },
            options: {
                skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
            }
        };
    </script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.min.js" async></script>
''' if has_math else ""

        # Highlight.js 스크립트
        highlight_script = '''
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css" id="hljs-light">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css" id="hljs-dark" disabled>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script>hljs.highlightAll();</script>
''' if has_code else ""

        return f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <meta name="theme-color" content="{theme['primary']}">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <title>{title} | StudySnap</title>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

    {mathjax_script}
    {highlight_script}

    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --primary: {theme['primary']};
            --secondary: {theme['secondary']};
            --accent: {theme['accent']};
            --gradient: {theme['gradient']};
            --bg-color: #FFFFFF;
            --bg-secondary: #F8FAFC;
            --text-primary: #1E293B;
            --text-secondary: #64748B;
            --border-color: #E2E8F0;
            --shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
        }}

        .dark-mode {{
            --bg-color: #0F172A;
            --bg-secondary: #1E293B;
            --text-primary: #F1F5F9;
            --text-secondary: #94A3B8;
            --border-color: #334155;
        }}

        html {{
            scroll-behavior: smooth;
            overflow-x: hidden;
        }}
        body {{
            font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.8;
            padding-bottom: 80px;
            overflow-x: hidden;
            width: 100%;
            max-width: 100vw;
        }}

        /* ========== 진행률 바 ========== */
        .progress-bar {{
            position: fixed;
            top: 0;
            left: 0;
            height: 4px;
            background: var(--gradient);
            width: 0%;
            z-index: 1001;
            transition: width 0.15s ease-out;
        }}

        /* ========== 고정 네비게이션 바 ========== */
        .top-nav {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 56px;
            background: var(--bg-color);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 16px;
            z-index: 1000;
            box-shadow: var(--shadow);
        }}

        .nav-logo {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 700;
            font-size: 1.1em;
            color: var(--primary);
        }}

        .nav-logo-icon {{
            width: 32px;
            height: 32px;
            background: var(--gradient);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.2em;
        }}

        .nav-actions {{
            display: flex;
            gap: 8px;
        }}

        .nav-btn {{
            width: 40px;
            height: 40px;
            border-radius: 10px;
            border: none;
            background: var(--bg-secondary);
            color: var(--text-secondary);
            font-size: 1.1em;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }}

        .nav-btn:hover {{
            background: var(--accent);
            color: var(--primary);
        }}

        .nav-btn.active {{
            background: var(--primary);
            color: white;
        }}

        /* 언어 선택 */
        .language-selector {{
            background: var(--bg-secondary);
            border: none;
            border-radius: 10px;
            padding: 8px 12px;
            font-size: 0.85em;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
            outline: none;
        }}

        .language-selector:hover {{
            background: var(--accent);
            color: var(--primary);
        }}

        /* ========== 그라디언트 헤더 ========== */
        .hero-header {{
            background: var(--gradient);
            padding: 80px 20px 40px;
            color: white;
            position: relative;
            overflow: hidden;
        }}

        .hero-header::before {{
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            width: 300px;
            height: 300px;
            background: rgba(255,255,255,0.1);
            border-radius: 50%;
            transform: translate(50%, -50%);
        }}

        .hero-content {{
            max-width: 800px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }}

        .hero-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(255,255,255,0.2);
            backdrop-filter: blur(10px);
            padding: 8px 16px;
            border-radius: 25px;
            font-size: 0.9em;
            margin-bottom: 16px;
        }}

        .hero-title {{
            font-size: 1.8em;
            font-weight: 800;
            margin-bottom: 12px;
            line-height: 1.3;
        }}

        .hero-meta {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            font-size: 0.95em;
            opacity: 0.95;
        }}

        .hero-meta-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        /* ========== 퀵 액션 버튼 ========== */
        .quick-actions {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            padding: 20px;
            max-width: 800px;
            margin: -30px auto 0;
            position: relative;
            z-index: 10;
        }}

        .action-btn {{
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 16px 12px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: var(--shadow);
        }}

        .action-btn:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
            border-color: var(--primary);
        }}

        .action-icon {{
            width: 44px;
            height: 44px;
            background: var(--accent);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 10px;
            font-size: 1.3em;
        }}

        .action-label {{
            font-size: 0.85em;
            font-weight: 600;
            color: var(--text-primary);
        }}

        /* ========== 메인 컨테이너 ========== */
        .main-container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}

        /* ========== 접이식 목차 ========== */
        .toc-section {{
            background: var(--bg-secondary);
            border-radius: 16px;
            margin-bottom: 24px;
            border: 1px solid var(--border-color);
            overflow: hidden;
        }}

        .toc-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 18px 20px;
            cursor: pointer;
            transition: background 0.2s;
        }}

        .toc-header:hover {{
            background: rgba(0,0,0,0.02);
        }}

        .toc-header-left {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .toc-icon {{
            width: 40px;
            height: 40px;
            background: var(--accent);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2em;
        }}

        .toc-title {{
            font-weight: 700;
            font-size: 1.05em;
        }}

        .toc-count {{
            font-size: 0.85em;
            color: var(--text-secondary);
        }}

        .toc-toggle {{
            width: 32px;
            height: 32px;
            background: var(--bg-color);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.3s;
        }}

        .toc-section.collapsed .toc-toggle {{
            transform: rotate(-90deg);
        }}

        .toc-content {{
            max-height: 400px;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }}

        .toc-section.collapsed .toc-content {{
            max-height: 0;
        }}

        .toc-list {{
            padding: 0 20px 20px;
        }}

        .toc-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px 16px;
            margin-bottom: 8px;
            background: var(--bg-color);
            border-radius: 12px;
            text-decoration: none;
            color: var(--text-primary);
            transition: all 0.2s;
            border: 1px solid transparent;
        }}

        .toc-item:hover {{
            border-color: var(--primary);
            transform: translateX(4px);
        }}

        .toc-item-number {{
            width: 28px;
            height: 28px;
            background: var(--gradient);
            color: white;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.85em;
            font-weight: 700;
            flex-shrink: 0;
        }}

        .toc-item-title {{
            flex: 1;
            font-weight: 500;
        }}

        /* ========== 챕터 섹션 ========== */
        .chapter-section {{
            background: var(--bg-color);
            border-radius: 16px;
            margin-bottom: 16px;
            border: 1px solid var(--border-color);
            overflow: hidden;
            box-shadow: var(--shadow);
        }}

        .chapter-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 20px;
            border-bottom: 1px solid var(--border-color);
            background: var(--bg-secondary);
        }}

        .chapter-header-left {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .chapter-number {{
            width: 36px;
            height: 36px;
            background: var(--gradient);
            color: white;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1em;
            font-weight: 800;
            flex-shrink: 0;
        }}

        .chapter-title {{
            font-size: 1.1em;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.3;
        }}

        .bookmark-btn {{
            width: 36px;
            height: 36px;
            border-radius: 10px;
            border: 1px solid var(--border-color);
            background: var(--bg-color);
            color: var(--text-secondary);
            font-size: 1em;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .bookmark-btn:hover, .bookmark-btn.active {{
            background: #FEF3C7;
            border-color: #F59E0B;
            color: #F59E0B;
        }}

        .chapter-content {{
            padding: 16px 20px;
            overflow-x: hidden;
            max-width: 100%;
        }}

        .content-text {{
            line-height: 1.9;
            overflow-wrap: break-word;
            word-wrap: break-word;
            word-break: keep-all;
            color: var(--text-primary);
        }}

        .content-text p {{
            margin-bottom: 16px;
        }}

        /* ========== 리스트 스타일 ========== */
        .content-list {{
            margin: 16px 0;
            padding-left: 24px;
        }}

        .content-list li {{
            margin-bottom: 8px;
            line-height: 1.7;
            position: relative;
        }}

        ul.content-list {{
            list-style: none;
        }}

        ul.content-list li::before {{
            content: '•';
            color: var(--primary);
            font-weight: bold;
            position: absolute;
            left: -18px;
        }}

        ol.content-list {{
            list-style: decimal;
        }}

        ol.content-list li::marker {{
            color: var(--primary);
            font-weight: 700;
        }}

        /* ========== 블록 인용문 스타일 ========== */
        .quote-box {{
            background: var(--bg-secondary);
            border-left: 4px solid var(--primary);
            border-radius: 0 12px 12px 0;
            padding: 16px 20px;
            margin: 16px 0;
            font-style: italic;
            color: var(--text-secondary);
        }}

        .quote-box p {{
            margin: 0;
        }}

        /* ========== 특별 박스 스타일 ========== */
        .info-box {{
            border-radius: 14px;
            padding: 20px;
            margin: 20px 0;
        }}

        .key-concept-box {{
            background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
            border-left: 4px solid #6366F1;
        }}

        .example-box {{
            background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%);
            border-left: 4px solid #10B981;
        }}

        .important-box {{
            background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%);
            border-left: 4px solid #F59E0B;
        }}

        .warning-box {{
            background: linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%);
            border-left: 4px solid #EF4444;
        }}

        .box-title {{
            font-weight: 700;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        /* ========== 수식 스타일 ========== */
        .equation-block {{
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            text-align: center;
            border: 1px solid var(--border-color);
            overflow-x: auto;
            max-width: 100%;
            -webkit-overflow-scrolling: touch;
        }}

        /* MathJax 수식 오버플로우 방지 */
        .MathJax {{
            overflow-x: auto !important;
            overflow-y: hidden !important;
            max-width: 100% !important;
        }}

        mjx-container {{
            overflow-x: auto !important;
            max-width: 100% !important;
            padding: 4px 0;
        }}

        /* ========== 코드 블록 ========== */
        .code-block {{
            margin: 20px 0;
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            background: #1E293B;
        }}

        .code-header {{
            background: #334155;
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .code-lang {{
            color: #94A3B8;
            font-size: 0.85em;
            font-weight: 600;
        }}

        .copy-btn {{
            background: rgba(255,255,255,0.1);
            color: #E2E8F0;
            border: none;
            padding: 6px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.85em;
            transition: all 0.2s;
        }}

        .copy-btn:hover {{
            background: rgba(255,255,255,0.2);
        }}

        .code-block pre {{
            margin: 0;
            padding: 20px;
            overflow-x: auto;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 0.9em;
            line-height: 1.6;
            color: #E2E8F0;
        }}

        /* ========== 표 스타일 ========== */
        .table-container {{
            margin: 24px 0;
            overflow-x: auto;
            border-radius: 14px;
            border: 1px solid var(--border-color);
            max-width: 100%;
            -webkit-overflow-scrolling: touch;
        }}

        .data-table {{
            width: 100%;
            border-collapse: collapse;
            table-layout: auto;
        }}

        .data-table th {{
            background: var(--gradient);
            color: white;
            padding: 14px 18px;
            text-align: left;
            font-weight: 600;
        }}

        .data-table td {{
            padding: 14px 18px;
            border-bottom: 1px solid var(--border-color);
            background: var(--bg-color);
        }}

        .data-table tr:hover td {{
            background: var(--bg-secondary);
        }}

        /* ========== 이미지 ========== */
        .image-container {{
            margin: 24px 0;
            text-align: center;
        }}

        .image-container img {{
            max-width: 100%;
            border-radius: 14px;
            box-shadow: var(--shadow-lg);
        }}

        .image-caption {{
            margin-top: 12px;
            font-size: 0.9em;
            color: var(--text-secondary);
            font-style: italic;
        }}

        /* ========== 핵심 개념 태그 ========== */
        .key-concepts-section {{
            background: var(--bg-secondary);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 24px;
            border: 1px solid var(--border-color);
        }}

        .section-header {{
            font-size: 1.1em;
            font-weight: 700;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .concepts-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .concept-tag {{
            background: var(--bg-color);
            color: var(--primary);
            padding: 10px 16px;
            border-radius: 25px;
            font-size: 0.9em;
            font-weight: 600;
            border: 1px solid var(--border-color);
            transition: all 0.2s;
        }}

        .concept-tag:hover {{
            background: var(--accent);
            border-color: var(--primary);
        }}

        /* ========== 플래시카드 ========== */
        .flashcards-section {{
            background: var(--bg-secondary);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 24px;
            border: 1px solid var(--border-color);
        }}

        .flashcards-container {{
            display: flex;
            gap: 16px;
            overflow-x: auto;
            padding: 10px 0;
            scroll-snap-type: x mandatory;
        }}

        .flashcard {{
            min-width: 300px;
            height: 200px;
            perspective: 1000px;
            cursor: pointer;
            scroll-snap-align: center;
        }}

        .flashcard-inner {{
            width: 100%;
            height: 100%;
            transition: transform 0.6s;
            transform-style: preserve-3d;
            position: relative;
        }}

        .flashcard.flipped .flashcard-inner {{
            transform: rotateY(180deg);
        }}

        .flashcard-front, .flashcard-back {{
            position: absolute;
            width: 100%;
            height: 100%;
            backface-visibility: hidden;
            border-radius: 16px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
        }}

        .flashcard-front {{
            background: var(--gradient);
            color: white;
        }}

        .flashcard-back {{
            background: var(--bg-color);
            border: 2px solid var(--primary);
            color: var(--text-primary);
            transform: rotateY(180deg);
        }}

        .card-content {{
            font-size: 1.1em;
            font-weight: 600;
        }}

        .card-hint {{
            font-size: 0.85em;
            opacity: 0.8;
            margin-top: 12px;
        }}

        .flashcard-controls {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 16px;
            margin-top: 12px;
            flex-wrap: wrap;
        }}

        .control-btn {{
            background: var(--primary);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.95em;
            transition: all 0.2s;
            min-width: 60px;
            white-space: nowrap;
        }}

        .control-btn:hover {{
            transform: scale(1.05);
        }}

        .card-counter {{
            font-weight: 700;
            font-size: 1em;
            color: var(--text-secondary);
            min-width: 50px;
            text-align: center;
        }}

        /* ========== 퀴즈 ========== */
        .quiz-section {{
            background: var(--bg-secondary);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 24px;
            border: 1px solid var(--border-color);
        }}

        .quiz-question {{
            background: var(--bg-color);
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 16px;
            border: 1px solid var(--border-color);
        }}

        .question-text {{
            font-size: 1.05em;
            margin-bottom: 16px;
            font-weight: 500;
        }}

        .q-number {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            background: var(--primary);
            color: white;
            border-radius: 8px;
            font-size: 0.85em;
            font-weight: 700;
            margin-right: 10px;
        }}

        .answer-input {{
            display: flex;
            gap: 12px;
        }}

        .quiz-input {{
            flex: 1;
            padding: 14px 18px;
            border: 2px solid var(--border-color);
            border-radius: 12px;
            font-size: 1em;
            background: var(--bg-color);
            color: var(--text-primary);
            transition: border-color 0.2s;
        }}

        .quiz-input:focus {{
            outline: none;
            border-color: var(--primary);
        }}

        .check-btn {{
            background: var(--primary);
            color: white;
            border: none;
            padding: 14px 24px;
            border-radius: 12px;
            cursor: pointer;
            font-weight: 700;
            transition: all 0.2s;
        }}

        .check-btn:hover {{
            transform: scale(1.02);
        }}

        .result-text {{
            margin-top: 12px;
            padding: 12px 16px;
            border-radius: 10px;
            font-weight: 600;
        }}

        .result-text.correct {{
            background: #ECFDF5;
            color: #059669;
        }}

        .result-text.incorrect {{
            background: #FEE2E2;
            color: #DC2626;
        }}

        /* ========== 하단 고정 네비게이션 ========== */
        .bottom-nav {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 64px;
            background: var(--bg-color);
            border-top: 1px solid var(--border-color);
            display: flex;
            justify-content: space-around;
            align-items: center;
            padding: 0 20px;
            z-index: 1000;
            box-shadow: 0 -4px 6px -1px rgba(0,0,0,0.05);
        }}

        .bottom-nav-btn {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 0.75em;
            cursor: pointer;
            padding: 8px 16px;
            border-radius: 10px;
            transition: all 0.2s;
        }}

        .bottom-nav-btn:hover {{
            background: var(--bg-secondary);
            color: var(--primary);
        }}

        .bottom-nav-btn .icon {{
            font-size: 1.5em;
        }}

        /* ========== 푸터 ========== */
        .lecture-footer {{
            text-align: center;
            padding: 40px 20px 100px;
            color: var(--text-secondary);
        }}

        .footer-logo {{
            font-size: 1.4em;
            font-weight: 800;
            background: var(--gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }}

        .footer-tagline {{
            font-size: 0.9em;
            margin-bottom: 16px;
        }}

        .footer-meta {{
            font-size: 0.8em;
            opacity: 0.7;
        }}

        /* ========== PC 최적화 (1024px 이상) ========== */
        @media (min-width: 1024px) {{
            .main-container {{
                max-width: 900px;
                margin: 0 auto;
                padding: 24px 40px;
            }}

            .chapter-section {{
                margin-bottom: 20px;
            }}

            .chapter-header {{
                padding: 14px 24px;
            }}

            .chapter-number {{
                width: 40px;
                height: 40px;
                font-size: 1.15em;
            }}

            .chapter-title {{
                font-size: 1.15em;
            }}

            .flashcard-container {{
                gap: 20px;
            }}

            .flashcard {{
                min-width: 320px;
                height: 220px;
            }}

            .flashcard-controls {{
                gap: 24px;
                margin-top: 16px;
            }}

            .control-btn {{
                padding: 12px 28px;
                font-size: 1em;
            }}

            .quiz-question {{
                padding: 24px;
            }}
        }}

        /* ========== 태블릿 (768px ~ 1023px) ========== */
        @media (min-width: 768px) and (max-width: 1023px) {{
            .main-container {{
                padding: 20px 24px;
            }}

            .flashcard {{
                min-width: 280px;
                height: 200px;
            }}
        }}

        /* ========== 모바일 (768px 미만) ========== */
        @media (max-width: 767px) {{
            .hero-header {{
                padding: 60px 16px 24px;
            }}

            .hero-title {{
                font-size: 1.4em;
            }}

            .hero-meta {{
                font-size: 0.85em;
            }}

            .quick-actions {{
                grid-template-columns: repeat(2, 1fr);
                padding: 12px;
                margin-top: -16px;
                gap: 8px;
            }}

            .action-btn {{
                padding: 12px 8px;
            }}

            .action-icon {{
                font-size: 1.3em;
            }}

            .action-label {{
                font-size: 0.8em;
            }}

            .main-container {{
                padding: 12px;
            }}

            .chapter-section {{
                border-radius: 12px;
                margin-bottom: 12px;
            }}

            .chapter-header {{
                padding: 10px 14px;
            }}

            .chapter-header-left {{
                gap: 10px;
            }}

            .chapter-number {{
                width: 32px;
                height: 32px;
                font-size: 1em;
                border-radius: 8px;
            }}

            .chapter-title {{
                font-size: 1em;
            }}

            .bookmark-btn {{
                width: 32px;
                height: 32px;
                font-size: 0.9em;
            }}

            .chapter-content {{
                padding: 14px;
            }}

            .content-text {{
                font-size: 0.95em;
                line-height: 1.8;
            }}

            .flashcard-container {{
                gap: 12px;
            }}

            .flashcard {{
                min-width: 240px;
                height: 160px;
            }}

            .card-content {{
                font-size: 1em;
            }}

            .flashcard-controls {{
                gap: 12px;
                margin-top: 10px;
            }}

            .control-btn {{
                padding: 8px 16px;
                font-size: 0.9em;
                min-width: 50px;
            }}

            .card-counter {{
                font-size: 0.9em;
            }}

            .quiz-section {{
                padding: 14px;
                border-radius: 12px;
            }}

            .quiz-question {{
                padding: 14px;
                border-radius: 10px;
            }}

            .question-text {{
                font-size: 0.95em;
            }}

            .quiz-input {{
                padding: 12px 14px;
                font-size: 0.95em;
            }}

            .answer-input {{
                flex-direction: column;
                gap: 10px;
            }}

            .info-box {{
                padding: 14px;
                margin: 14px 0;
            }}

            .equation-block {{
                padding: 14px;
                margin: 14px 0;
            }}

            .code-block {{
                margin: 14px 0;
                border-radius: 10px;
            }}

            .toc-section {{
                border-radius: 12px;
            }}

            .toc-header {{
                padding: 14px 16px;
            }}

            .toc-content {{
                padding: 12px;
            }}

            /* 테이블 반응형 - 모바일 */
            .table-container {{
                margin: 12px 0;
                border-radius: 10px;
                -webkit-overflow-scrolling: touch;
            }}

            .data-table {{
                min-width: 100%;
                font-size: 0.85em;
            }}

            .data-table th,
            .data-table td {{
                padding: 10px 12px;
                white-space: nowrap;
            }}

            /* 작은 화면에서 테이블 세로 배치 옵션 */
            .table-responsive-stack .data-table,
            .table-responsive-stack .data-table thead,
            .table-responsive-stack .data-table tbody,
            .table-responsive-stack .data-table th,
            .table-responsive-stack .data-table td,
            .table-responsive-stack .data-table tr {{
                display: block;
            }}

            .table-responsive-stack .data-table thead {{
                display: none;
            }}

            .table-responsive-stack .data-table tr {{
                margin-bottom: 12px;
                border: 1px solid var(--border-color);
                border-radius: 10px;
                overflow: hidden;
            }}

            .table-responsive-stack .data-table td {{
                text-align: left;
                padding: 10px 14px;
                border-bottom: 1px solid var(--border-color);
                position: relative;
            }}

            .table-responsive-stack .data-table td:before {{
                content: attr(data-label);
                font-weight: 700;
                color: var(--primary);
                display: block;
                margin-bottom: 4px;
                font-size: 0.85em;
            }}

            .table-responsive-stack .data-table td:last-child {{
                border-bottom: none;
            }}
        }}

        /* ========== 작은 모바일 (480px 미만) ========== */
        @media (max-width: 479px) {{
            .hero-header {{
                padding: 55px 12px 20px;
            }}

            .hero-title {{
                font-size: 1.25em;
            }}

            .quick-actions {{
                padding: 10px;
            }}

            .main-container {{
                padding: 10px;
            }}

            .chapter-header {{
                padding: 8px 12px;
            }}

            .chapter-number {{
                width: 28px;
                height: 28px;
                font-size: 0.9em;
            }}

            .chapter-title {{
                font-size: 0.95em;
            }}

            .chapter-content {{
                padding: 12px;
            }}

            .flashcard {{
                min-width: 200px;
                height: 140px;
            }}

            .control-btn {{
                padding: 7px 14px;
                font-size: 0.85em;
            }}
        }}
    </style>
</head>
<body>
    <!-- 진행률 바 -->
    {'<div class="progress-bar" id="progressBar"></div>' if options.get("show_progress") else ''}

    <!-- 상단 고정 네비게이션 -->
    <nav class="top-nav">
        <div class="nav-logo">
            <div class="nav-logo-icon">{theme['icon']}</div>
            <span>StudySnap</span>
        </div>
        <div class="nav-actions">
            <select class="language-selector" onchange="changeLanguage(this.value)" title="언어 선택">
                <option value="ko" selected>한국어</option>
                <option value="en">English</option>
                <option value="zh">中文</option>
                <option value="ja">日本語</option>
                <option value="id">Bahasa Indonesia</option>
                <option value="es">Español</option>
                <option value="ru">Русский</option>
                <option value="fr">Français</option>
            </select>
            <button class="nav-btn" onclick="changeFontSize(-1)" title="글자 작게" data-i18n-title="btn_font_smaller">A-</button>
            <button class="nav-btn" onclick="changeFontSize(1)" title="글자 크게" data-i18n-title="btn_font_larger">A+</button>
            <button class="nav-btn" onclick="toggleDarkMode()" title="다크모드" id="darkModeBtn" data-i18n-title="btn_dark_mode">🌙</button>
            <button class="nav-btn" onclick="sharePage()" title="공유" data-i18n-title="btn_share">📤</button>
        </div>
    </nav>

    <!-- 그라디언트 헤더 -->
    <header class="hero-header">
        <div class="hero-content">
            <div class="hero-badge">
                <span>{theme['icon']}</span>
                <span>{theme['name']}</span>
            </div>
            <h1 class="hero-title">{title}</h1>
            <div class="hero-meta">
                <span class="hero-meta-item">📄 {page_count}페이지</span>
                <span class="hero-meta-item">📚 {section_count}섹션</span>
                {f'<span class="hero-meta-item">📐 수식 포함</span>' if has_math else ''}
                {f'<span class="hero-meta-item">💻 코드 포함</span>' if has_code else ''}
            </div>
        </div>
    </header>

    <!-- 퀵 액션 버튼 -->
    <div class="quick-actions">
        <div class="action-btn" onclick="scrollToTOC()">
            <div class="action-icon">📋</div>
            <div class="action-label" data-i18n="action_toc">목차</div>
        </div>
        <div class="action-btn" onclick="scrollToFlashcards()">
            <div class="action-icon">📇</div>
            <div class="action-label" data-i18n="action_flashcards">플래시카드</div>
        </div>
        <div class="action-btn" onclick="scrollToQuiz()">
            <div class="action-icon">📝</div>
            <div class="action-label" data-i18n="action_quiz">퀴즈</div>
        </div>
        <div class="action-btn" onclick="printPage()">
            <div class="action-icon">🖨️</div>
            <div class="action-label" data-i18n="action_print">인쇄</div>
        </div>
    </div>

    <!-- 메인 컨테이너 -->
    <main class="main-container">
        <!-- 접이식 목차 -->
        {f'''
        <div class="toc-section" id="tocSection">
            <div class="toc-header" onclick="toggleTOCContent()">
                <div class="toc-header-left">
                    <div class="toc-icon">📋</div>
                    <div>
                        <div class="toc-title" data-i18n="toc_title">목차</div>
                        <div class="toc-count"><span id="sectionCountNum">{section_count}</span><span data-i18n="toc_sections">개 섹션</span></div>
                    </div>
                </div>
                <div class="toc-toggle" id="tocToggle">▼</div>
            </div>
            <div class="toc-content" id="tocContent">
                <div class="toc-list">
                    {toc_items}
                </div>
            </div>
        </div>
        ''' if toc_items else ''}

        <!-- 핵심 개념 -->
        {concepts_html}

        <!-- 메인 콘텐츠 (챕터들) -->
        {main_content}

        <!-- 표 -->
        {tables_html}

        <!-- 이미지 -->
        {images_html}

        <!-- 플래시카드 -->
        {flashcards_html}

        <!-- 퀴즈 -->
        {quiz_html}
    </main>

    <!-- 푸터 -->
    <footer class="lecture-footer">
        <div class="footer-logo">📖 StudySnap</div>
        <p class="footer-tagline">AI 기반 스마트 학습 문서 변환</p>
        <p class="footer-meta">Generated at {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
    </footer>

    <!-- 하단 고정 네비게이션 -->
    <nav class="bottom-nav">
        <button class="bottom-nav-btn" onclick="navigateChapter(-1)">
            <span class="icon">◀</span>
            <span>이전</span>
        </button>
        <button class="bottom-nav-btn" onclick="scrollToTOC()">
            <span class="icon">📋</span>
            <span>목차</span>
        </button>
        <button class="bottom-nav-btn" onclick="scrollToTop()">
            <span class="icon">⬆️</span>
            <span>맨위</span>
        </button>
        <button class="bottom-nav-btn" onclick="navigateChapter(1)">
            <span class="icon">▶</span>
            <span>다음</span>
        </button>
    </nav>

    <script>
        // ========== 다국어 번역 시스템 ==========
        const translations = {{
            ko: {{
                action_toc: "목차",
                action_flashcards: "플래시카드",
                action_quiz: "퀴즈",
                action_print: "인쇄",
                toc_title: "목차",
                toc_sections: "개 섹션",
                flashcard_title: "플래시카드",
                flashcard_prev: "이전",
                flashcard_next: "다음",
                flashcard_flip: "뒤집기",
                quiz_title: "퀴즈",
                quiz_submit: "제출",
                quiz_retry: "다시 풀기",
                btn_font_smaller: "글자 작게",
                btn_font_larger: "글자 크게",
                btn_dark_mode: "다크모드",
                btn_share: "공유"
            }},
            en: {{
                action_toc: "Contents",
                action_flashcards: "Flashcards",
                action_quiz: "Quiz",
                action_print: "Print",
                toc_title: "Table of Contents",
                toc_sections: " sections",
                flashcard_title: "Flashcards",
                flashcard_prev: "Previous",
                flashcard_next: "Next",
                flashcard_flip: "Flip",
                quiz_title: "Quiz",
                quiz_submit: "Submit",
                quiz_retry: "Retry",
                btn_font_smaller: "Smaller text",
                btn_font_larger: "Larger text",
                btn_dark_mode: "Dark mode",
                btn_share: "Share"
            }},
            zh: {{
                action_toc: "目录",
                action_flashcards: "闪卡",
                action_quiz: "测验",
                action_print: "打印",
                toc_title: "目录",
                toc_sections: "个章节",
                flashcard_title: "闪卡",
                flashcard_prev: "上一个",
                flashcard_next: "下一个",
                flashcard_flip: "翻转",
                quiz_title: "测验",
                quiz_submit: "提交",
                quiz_retry: "重试",
                btn_font_smaller: "缩小字体",
                btn_font_larger: "放大字体",
                btn_dark_mode: "深色模式",
                btn_share: "分享"
            }},
            ja: {{
                action_toc: "目次",
                action_flashcards: "フラッシュカード",
                action_quiz: "クイズ",
                action_print: "印刷",
                toc_title: "目次",
                toc_sections: "セクション",
                flashcard_title: "フラッシュカード",
                flashcard_prev: "前へ",
                flashcard_next: "次へ",
                flashcard_flip: "裏返す",
                quiz_title: "クイズ",
                quiz_submit: "提出",
                quiz_retry: "やり直し",
                btn_font_smaller: "文字を小さく",
                btn_font_larger: "文字を大きく",
                btn_dark_mode: "ダークモード",
                btn_share: "共有"
            }},
            id: {{
                action_toc: "Daftar Isi",
                action_flashcards: "Kartu Flash",
                action_quiz: "Kuis",
                action_print: "Cetak",
                toc_title: "Daftar Isi",
                toc_sections: " bagian",
                flashcard_title: "Kartu Flash",
                flashcard_prev: "Sebelumnya",
                flashcard_next: "Selanjutnya",
                flashcard_flip: "Balik",
                quiz_title: "Kuis",
                quiz_submit: "Kirim",
                quiz_retry: "Coba lagi",
                btn_font_smaller: "Perkecil teks",
                btn_font_larger: "Perbesar teks",
                btn_dark_mode: "Mode gelap",
                btn_share: "Bagikan"
            }},
            es: {{
                action_toc: "Índice",
                action_flashcards: "Tarjetas",
                action_quiz: "Cuestionario",
                action_print: "Imprimir",
                toc_title: "Índice",
                toc_sections: " secciones",
                flashcard_title: "Tarjetas didácticas",
                flashcard_prev: "Anterior",
                flashcard_next: "Siguiente",
                flashcard_flip: "Voltear",
                quiz_title: "Cuestionario",
                quiz_submit: "Enviar",
                quiz_retry: "Reintentar",
                btn_font_smaller: "Texto más pequeño",
                btn_font_larger: "Texto más grande",
                btn_dark_mode: "Modo oscuro",
                btn_share: "Compartir"
            }},
            ru: {{
                action_toc: "Содержание",
                action_flashcards: "Карточки",
                action_quiz: "Тест",
                action_print: "Печать",
                toc_title: "Содержание",
                toc_sections: " разделов",
                flashcard_title: "Карточки",
                flashcard_prev: "Назад",
                flashcard_next: "Далее",
                flashcard_flip: "Перевернуть",
                quiz_title: "Тест",
                quiz_submit: "Отправить",
                quiz_retry: "Повторить",
                btn_font_smaller: "Уменьшить шрифт",
                btn_font_larger: "Увеличить шрифт",
                btn_dark_mode: "Тёмный режим",
                btn_share: "Поделиться"
            }},
            fr: {{
                action_toc: "Sommaire",
                action_flashcards: "Cartes mémoire",
                action_quiz: "Quiz",
                action_print: "Imprimer",
                toc_title: "Sommaire",
                toc_sections: " sections",
                flashcard_title: "Cartes mémoire",
                flashcard_prev: "Précédent",
                flashcard_next: "Suivant",
                flashcard_flip: "Retourner",
                quiz_title: "Quiz",
                quiz_submit: "Soumettre",
                quiz_retry: "Réessayer",
                btn_font_smaller: "Réduire le texte",
                btn_font_larger: "Agrandir le texte",
                btn_dark_mode: "Mode sombre",
                btn_share: "Partager"
            }}
        }};

        let currentLanguage = 'ko';

        function changeLanguage(lang) {{
            currentLanguage = lang;
            // 텍스트 번역
            document.querySelectorAll('[data-i18n]').forEach(el => {{
                const key = el.getAttribute('data-i18n');
                if (translations[lang] && translations[lang][key]) {{
                    el.textContent = translations[lang][key];
                }}
            }});
            // title 속성 번역
            document.querySelectorAll('[data-i18n-title]').forEach(el => {{
                const key = el.getAttribute('data-i18n-title');
                if (translations[lang] && translations[lang][key]) {{
                    el.setAttribute('title', translations[lang][key]);
                }}
            }});
            localStorage.setItem('lecture_lang', lang);
        }}

        // 페이지 로드 시 저장된 언어 복원
        document.addEventListener('DOMContentLoaded', function() {{
            const savedLang = localStorage.getItem('lecture_lang');
            if (savedLang && translations[savedLang]) {{
                const selector = document.querySelector('.language-selector');
                if (selector) {{
                    selector.value = savedLang;
                    changeLanguage(savedLang);
                }}
            }}
        }});

        // ========== 진행률 바 ==========
        function updateProgressBar() {{
            const scrollTop = window.scrollY;
            const docHeight = document.body.scrollHeight - window.innerHeight;
            const progress = Math.min((scrollTop / docHeight) * 100, 100);
            const progressBar = document.getElementById('progressBar');
            if (progressBar) progressBar.style.width = progress + '%';
        }}
        window.addEventListener('scroll', updateProgressBar);

        // ========== 스크롤 함수들 ==========
        function scrollToTop() {{
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        function scrollToTOC() {{
            const toc = document.getElementById('tocSection');
            if (toc) {{
                toc.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            }}
        }}

        function scrollToFlashcards() {{
            const section = document.querySelector('.flashcards-section');
            if (section) {{
                section.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            }}
        }}

        function scrollToQuiz() {{
            const section = document.querySelector('.quiz-section');
            if (section) {{
                section.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            }}
        }}

        // ========== 목차 토글 ==========
        function toggleTOCContent() {{
            const section = document.getElementById('tocSection');
            const toggle = document.getElementById('tocToggle');
            if (section.classList.contains('collapsed')) {{
                section.classList.remove('collapsed');
                toggle.textContent = '▼';
            }} else {{
                section.classList.add('collapsed');
                toggle.textContent = '▶';
            }}
        }}

        // ========== 글자 크기 조절 ==========
        let currentFontSize = 100;
        function changeFontSize(delta) {{
            currentFontSize = Math.max(80, Math.min(140, currentFontSize + delta * 10));
            document.body.style.fontSize = currentFontSize + '%';
            localStorage.setItem('fontSize', currentFontSize);
        }}

        // ========== 다크 모드 ==========
        function toggleDarkMode() {{
            document.body.classList.toggle('dark-mode');
            const isDark = document.body.classList.contains('dark-mode');
            localStorage.setItem('darkMode', isDark);

            const btn = document.getElementById('darkModeBtn');
            if (btn) btn.textContent = isDark ? '☀️' : '🌙';

            // Highlight.js 스타일 토글
            const lightStyle = document.getElementById('hljs-light');
            const darkStyle = document.getElementById('hljs-dark');
            if (lightStyle && darkStyle) {{
                lightStyle.disabled = isDark;
                darkStyle.disabled = !isDark;
            }}
        }}

        // ========== 공유 ==========
        function sharePage() {{
            if (navigator.share) {{
                navigator.share({{
                    title: document.title,
                    url: window.location.href
                }});
            }} else {{
                navigator.clipboard.writeText(window.location.href).then(() => {{
                    alert('링크가 복사되었습니다!');
                }});
            }}
        }}

        // ========== 인쇄 ==========
        function printPage() {{
            window.print();
        }}

        // ========== 챕터 네비게이션 ==========
        let currentChapter = 0;
        const chapters = document.querySelectorAll('.chapter-section');

        function navigateChapter(delta) {{
            if (chapters.length === 0) return;

            // 현재 위치 기준으로 정확한 챕터 찾기
            updateCurrentChapter();

            // 새 챕터 인덱스 계산 (범위 제한)
            const newChapter = Math.max(0, Math.min(chapters.length - 1, currentChapter + delta));

            // 같은 챕터면 이동하지 않음 (경계에서)
            if (newChapter === currentChapter && delta !== 0) {{
                // 경계에서 시각적 피드백 (옵션)
                return;
            }}

            currentChapter = newChapter;

            // 네비게이션 바 높이(64px) + 여백 고려하여 스크롤
            const navHeight = 70;
            const targetElement = chapters[currentChapter];
            const targetPosition = targetElement.getBoundingClientRect().top + window.scrollY - navHeight;

            window.scrollTo({{
                top: targetPosition,
                behavior: 'smooth'
            }});
        }}

        // 현재 보이는 챕터 감지 (화면 중앙 기준)
        function updateCurrentChapter() {{
            const viewportCenter = window.scrollY + window.innerHeight / 3;
            let closestChapter = 0;
            let closestDistance = Infinity;

            chapters.forEach((chapter, index) => {{
                const chapterTop = chapter.getBoundingClientRect().top + window.scrollY;
                const distance = Math.abs(chapterTop - viewportCenter);

                if (distance < closestDistance) {{
                    closestDistance = distance;
                    closestChapter = index;
                }}
            }});

            currentChapter = closestChapter;
        }}
        window.addEventListener('scroll', updateCurrentChapter);

        // ========== 북마크 ==========
        function toggleBookmark(btn, chapterId) {{
            btn.classList.toggle('active');
            const bookmarks = JSON.parse(localStorage.getItem('bookmarks') || '[]');
            if (btn.classList.contains('active')) {{
                if (!bookmarks.includes(chapterId)) bookmarks.push(chapterId);
            }} else {{
                const idx = bookmarks.indexOf(chapterId);
                if (idx > -1) bookmarks.splice(idx, 1);
            }}
            localStorage.setItem('bookmarks', JSON.stringify(bookmarks));
        }}

        // ========== 코드 복사 ==========
        function copyCode(btn) {{
            const codeBlock = btn.closest('.code-block').querySelector('code');
            navigator.clipboard.writeText(codeBlock.textContent).then(() => {{
                const originalText = btn.textContent;
                btn.textContent = '✅ 복사됨!';
                setTimeout(() => {{ btn.textContent = originalText; }}, 2000);
            }});
        }}

        // ========== 플래시카드 ==========
        let currentCard = 0;
        const flashcards = document.querySelectorAll('.flashcard');

        function flipCard(card) {{
            card.classList.toggle('flipped');
        }}

        function showCard(index) {{
            flashcards.forEach((card, i) => {{
                card.style.display = i === index ? 'block' : 'none';
                card.classList.remove('flipped');
            }});
            const counter = document.querySelector('.card-counter');
            if (counter) counter.textContent = `${{index + 1}} / ${{flashcards.length}}`;
        }}

        function nextCard() {{
            if (flashcards.length > 0) {{
                currentCard = (currentCard + 1) % flashcards.length;
                showCard(currentCard);
            }}
        }}

        function prevCard() {{
            if (flashcards.length > 0) {{
                currentCard = (currentCard - 1 + flashcards.length) % flashcards.length;
                showCard(currentCard);
            }}
        }}

        // ========== 퀴즈 ==========
        let quizScore = 0;
        const totalQuestions = document.querySelectorAll('.quiz-question').length;

        function checkAnswer(btn) {{
            const question = btn.closest('.quiz-question');
            const input = question.querySelector('.quiz-input');
            const answer = question.dataset.answer;
            const result = question.querySelector('.result-text');

            const isCorrect = input.value.trim().toLowerCase() === answer.toLowerCase();

            if (isCorrect) {{
                result.textContent = '✅ 정답입니다!';
                result.className = 'result-text correct';
                quizScore++;
            }} else {{
                result.textContent = `❌ 오답입니다. 정답: ${{answer}}`;
                result.className = 'result-text incorrect';
            }}
            result.style.display = 'block';

            input.disabled = true;
            btn.disabled = true;

            // 점수 업데이트
            const scoreEl = document.getElementById('quiz-score');
            if (scoreEl) scoreEl.textContent = `${{quizScore}} / ${{totalQuestions}}`;
        }}

        // ========== 초기화 ==========
        document.addEventListener('DOMContentLoaded', function() {{
            // 저장된 설정 복원
            const savedFontSize = localStorage.getItem('fontSize');
            if (savedFontSize) {{
                currentFontSize = parseInt(savedFontSize);
                document.body.style.fontSize = currentFontSize + '%';
            }}

            const savedDarkMode = localStorage.getItem('darkMode');
            if (savedDarkMode === 'true') {{
                document.body.classList.add('dark-mode');
                const btn = document.getElementById('darkModeBtn');
                if (btn) btn.textContent = '☀️';
            }}

            // 저장된 북마크 복원
            const bookmarks = JSON.parse(localStorage.getItem('bookmarks') || '[]');
            bookmarks.forEach(id => {{
                const btn = document.querySelector(`[data-chapter="${{id}}"] .bookmark-btn`);
                if (btn) btn.classList.add('active');
            }});

            // 플래시카드 초기화
            if (flashcards.length > 0) {{
                showCard(0);
            }}

            // 진행률 바 초기화
            updateProgressBar();
        }});
    </script>
</body>
</html>'''

    def _build_table_html(self, table: Dict) -> str:
        """표 HTML 생성"""
        html = '<div class="table-container"><table class="data-table">'

        # 헤더
        if table.get("header"):
            html += '<thead><tr>'
            for cell in table["header"]:
                html += f'<th>{cell}</th>'
            html += '</tr></thead>'

        # 데이터
        if table.get("data"):
            html += '<tbody>'
            for row in table["data"]:
                html += '<tr>'
                for cell in row:
                    html += f'<td>{cell}</td>'
                html += '</tr>'
            html += '</tbody>'

        html += '</table></div>'
        return html


# 편의 함수
def get_lecture_generator() -> LectureHTMLGenerator:
    """강의자료 생성기 인스턴스 반환"""
    return LectureHTMLGenerator()


# 기존 호환성을 위한 alias
LectureGenerator = LectureHTMLGenerator


# 테스트
if __name__ == "__main__":
    generator = LectureHTMLGenerator()

    # 테스트 데이터
    test_data = {
        "pages": [
            {
                "text": """# 미적분학 개론

## 1. 극한과 연속

### 1.1 극한의 정의

**정의**: 함수 f(x)의 x -> a에서의 극한

수열 {an}에서 n이 무한히 커질 때, an이 어떤 값 L에 한없이 가까워지면
$$\\lim_{n \\to \\infty} a_n = L$$
이라고 표현합니다.

### 1.2 극한의 성질

| 성질 | 수식 |
|------|------|
| 덧셈 | lim(f+g) = lim f + lim g |
| 곱셈 | lim(f*g) = lim f * lim g |
| 나눗셈 | lim(f/g) = lim f / lim g |

## 2. 미분

**핵심**: 미분은 순간변화율을 나타냅니다.

```python
def derivative(f, x, h=1e-10):
    return (f(x + h) - f(x)) / h
```
"""
            }
        ],
        "metadata": {
            "title": "미적분학 개론",
            "author": "홍길동"
        }
    }

    html = generator.generate(test_data, title="미적분학 개론")

    # 파일로 저장
    with open("test_lecture.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("[OK] Lecture HTML generator ready!")
    print(f"   - Detected subject: {generator.detect_subject(test_data['pages'][0]['text'])}")
    print(f"   - Generated flashcards: {len(generator.generated_flashcards)}")
    print(f"   - Generated quiz: {len(generator.generated_quiz)}")
