"""
다국어 지원 시스템
여러 언어로 OCR 및 출력 생성 지원
"""

import logging
from typing import Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """지원 언어"""
    KOREAN = "ko"
    ENGLISH = "en"
    JAPANESE = "ja"
    CHINESE = "zh"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"


class LocalizationManager:
    """다국어 지원 관리자"""

    def __init__(self):
        # OCR 프롬프트 언어별 설정
        self.ocr_prompts = self._init_ocr_prompts()

        # UI 라벨 번역
        self.ui_labels = self._init_ui_labels()

        # 날짜/시간 형식
        self.datetime_formats = self._init_datetime_formats()

        logger.info("다국어 지원 시스템 초기화 완료")

    def _init_ocr_prompts(self) -> Dict[str, Dict[str, str]]:
        """OCR 프롬프트 초기화"""
        return {
            Language.KOREAN: {
                "general": """이 이미지에서 모든 텍스트를 추출해주세요.

규칙:
1. 이미지에 보이는 텍스트를 그대로 추출
2. 레이아웃과 구조를 최대한 유지
3. 제목, 부제, 본문 등의 구조 파악
4. 한국어 텍스트 우선
5. 불필요한 설명 없이 텍스트만 반환

추출된 텍스트:""",
                "election": "선거 공보물 이미지를 분석하여 정보를 추출해주세요.",
                "lecture": "강의 자료 이미지를 분석하여 내용을 추출해주세요.",
                "church": "교회 자료 이미지를 분석하여 내용을 추출해주세요.",
            },
            Language.ENGLISH: {
                "general": """Extract all text from this image.

Rules:
1. Extract text exactly as shown in the image
2. Preserve layout and structure
3. Identify structure: titles, subtitles, body text
4. Prioritize English text
5. Return text only, no explanations

Extracted text:""",
                "election": "Analyze this election campaign material and extract information.",
                "lecture": "Analyze this lecture material and extract the content.",
                "church": "Analyze this church material and extract the content.",
            },
            Language.JAPANESE: {
                "general": """この画像からすべてのテキストを抽出してください。

ルール:
1. 画像に表示されているテキストをそのまま抽出
2. レイアウトと構造を最大限維持
3. タイトル、サブタイトル、本文などの構造を把握
4. 日本語テキストを優先
5. 不要な説明なしでテキストのみを返す

抽出されたテキスト:""",
                "election": "この選挙資料の画像を分析して情報を抽出してください。",
                "lecture": "この講義資料の画像を分析して内容を抽出してください。",
                "church": "この教会資料の画像を分析して内容を抽出してください。",
            },
            Language.CHINESE: {
                "general": """从此图像中提取所有文本。

规则：
1. 按原样提取图像中显示的文本
2. 最大限度地保留布局和结构
3. 识别结构：标题、副标题、正文
4. 优先提取中文文本
5. 仅返回文本，无需说明

提取的文本：""",
                "election": "分析此选举宣传材料并提取信息。",
                "lecture": "分析此讲义材料并提取内容。",
                "church": "分析此教会材料并提取内容。",
            },
            Language.SPANISH: {
                "general": """Extrae todo el texto de esta imagen.

Reglas:
1. Extrae el texto exactamente como se muestra en la imagen
2. Conserva el diseño y la estructura
3. Identifica la estructura: títulos, subtítulos, texto del cuerpo
4. Prioriza el texto en español
5. Devuelve solo texto, sin explicaciones

Texto extraído:""",
                "election": "Analiza este material de campaña electoral y extrae la información.",
                "lecture": "Analiza este material de conferencia y extrae el contenido.",
                "church": "Analiza este material de la iglesia y extrae el contenido.",
            },
            Language.FRENCH: {
                "general": """Extrayez tout le texte de cette image.

Règles:
1. Extrayez le texte exactement tel qu'il apparaît dans l'image
2. Préservez la mise en page et la structure
3. Identifiez la structure : titres, sous-titres, corps du texte
4. Privilégiez le texte en français
5. Retournez uniquement le texte, sans explications

Texte extrait:""",
                "election": "Analysez ce matériel de campagne électorale et extrayez les informations.",
                "lecture": "Analysez ce matériel de conférence et extrayez le contenu.",
                "church": "Analysez ce matériel d'église et extrayez le contenu.",
            },
            Language.GERMAN: {
                "general": """Extrahieren Sie den gesamten Text aus diesem Bild.

Regeln:
1. Extrahieren Sie den Text genau so, wie er im Bild angezeigt wird
2. Bewahren Sie Layout und Struktur
3. Identifizieren Sie die Struktur: Titel, Untertitel, Fließtext
4. Priorisieren Sie deutschen Text
5. Geben Sie nur Text zurück, keine Erklärungen

Extrahierter Text:""",
                "election": "Analysieren Sie dieses Wahlkampfmaterial und extrahieren Sie die Informationen.",
                "lecture": "Analysieren Sie dieses Vorlesungsmaterial und extrahieren Sie den Inhalt.",
                "church": "Analysieren Sie dieses Kirchenmaterial und extrahieren Sie den Inhalt.",
            },
        }

    def _init_ui_labels(self) -> Dict[str, Dict[str, str]]:
        """UI 라벨 초기화"""
        return {
            Language.KOREAN: {
                "title": "제목",
                "content": "내용",
                "page": "페이지",
                "candidate": "후보자",
                "party": "정당",
                "pledges": "공약",
                "contact": "연락처",
                "career": "경력",
                "generated_by": "생성: StudySnap",
                "page_of": "{current} / {total}",
            },
            Language.ENGLISH: {
                "title": "Title",
                "content": "Content",
                "page": "Page",
                "candidate": "Candidate",
                "party": "Party",
                "pledges": "Pledges",
                "contact": "Contact",
                "career": "Career",
                "generated_by": "Generated by StudySnap",
                "page_of": "{current} of {total}",
            },
            Language.JAPANESE: {
                "title": "タイトル",
                "content": "内容",
                "page": "ページ",
                "candidate": "候補者",
                "party": "政党",
                "pledges": "公約",
                "contact": "連絡先",
                "career": "経歴",
                "generated_by": "生成: StudySnap",
                "page_of": "{current} / {total}",
            },
            Language.CHINESE: {
                "title": "标题",
                "content": "内容",
                "page": "页面",
                "candidate": "候选人",
                "party": "政党",
                "pledges": "承诺",
                "contact": "联系方式",
                "career": "经历",
                "generated_by": "生成：StudySnap",
                "page_of": "{current} / {total}",
            },
            Language.SPANISH: {
                "title": "Título",
                "content": "Contenido",
                "page": "Página",
                "candidate": "Candidato",
                "party": "Partido",
                "pledges": "Promesas",
                "contact": "Contacto",
                "career": "Carrera",
                "generated_by": "Generado por StudySnap",
                "page_of": "{current} de {total}",
            },
            Language.FRENCH: {
                "title": "Titre",
                "content": "Contenu",
                "page": "Page",
                "candidate": "Candidat",
                "party": "Parti",
                "pledges": "Promesses",
                "contact": "Contact",
                "career": "Carrière",
                "generated_by": "Généré par StudySnap",
                "page_of": "{current} sur {total}",
            },
            Language.GERMAN: {
                "title": "Titel",
                "content": "Inhalt",
                "page": "Seite",
                "candidate": "Kandidat",
                "party": "Partei",
                "pledges": "Versprechen",
                "contact": "Kontakt",
                "career": "Karriere",
                "generated_by": "Erstellt von StudySnap",
                "page_of": "{current} von {total}",
            },
        }

    def _init_datetime_formats(self) -> Dict[str, str]:
        """날짜/시간 형식 초기화"""
        return {
            Language.KOREAN: "%Y년 %m월 %d일",
            Language.ENGLISH: "%B %d, %Y",
            Language.JAPANESE: "%Y年%m月%d日",
            Language.CHINESE: "%Y年%m月%d日",
            Language.SPANISH: "%d de %B de %Y",
            Language.FRENCH: "%d %B %Y",
            Language.GERMAN: "%d. %B %Y",
        }

    def get_ocr_prompt(self, language: str, content_type: str = "general") -> str:
        """OCR 프롬프트 가져오기"""
        lang = language if language in self.ocr_prompts else Language.KOREAN
        prompts = self.ocr_prompts.get(lang, self.ocr_prompts[Language.KOREAN])
        return prompts.get(content_type, prompts["general"])

    def get_label(self, language: str, label_key: str, **kwargs) -> str:
        """UI 라벨 가져오기"""
        lang = language if language in self.ui_labels else Language.KOREAN
        labels = self.ui_labels.get(lang, self.ui_labels[Language.KOREAN])
        label = labels.get(label_key, label_key)

        # 템플릿 변수 처리
        if kwargs:
            try:
                label = label.format(**kwargs)
            except KeyError:
                pass

        return label

    def get_datetime_format(self, language: str) -> str:
        """날짜/시간 형식 가져오기"""
        return self.datetime_formats.get(language, self.datetime_formats[Language.KOREAN])

    def get_supported_languages(self) -> list:
        """지원 언어 목록"""
        return [
            {"code": Language.KOREAN, "name": "한국어", "native": "한국어"},
            {"code": Language.ENGLISH, "name": "English", "native": "English"},
            {"code": Language.JAPANESE, "name": "Japanese", "native": "日本語"},
            {"code": Language.CHINESE, "name": "Chinese", "native": "中文"},
            {"code": Language.SPANISH, "name": "Spanish", "native": "Español"},
            {"code": Language.FRENCH, "name": "French", "native": "Français"},
            {"code": Language.GERMAN, "name": "German", "native": "Deutsch"},
        ]

    def detect_language(self, text: str) -> str:
        """텍스트에서 언어 자동 감지 (간단한 휴리스틱)"""
        if not text:
            return Language.KOREAN

        # 한글
        korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7a3')
        # 일본어 (히라가나, 가타카나)
        japanese_chars = sum(1 for c in text if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff')
        # 중국어 (한자)
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        # 영어
        english_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')

        total = len(text)
        if total == 0:
            return Language.KOREAN

        # 비율 계산
        ratios = {
            Language.KOREAN: korean_chars / total,
            Language.JAPANESE: japanese_chars / total,
            Language.CHINESE: chinese_chars / total,
            Language.ENGLISH: english_chars / total,
        }

        # 가장 높은 비율의 언어 반환
        detected = max(ratios, key=ratios.get)
        logger.info(f"언어 감지: {detected} (한글: {ratios[Language.KOREAN]:.2%}, "
                   f"일본어: {ratios[Language.JAPANESE]:.2%}, "
                   f"중국어: {ratios[Language.CHINESE]:.2%}, "
                   f"영어: {ratios[Language.ENGLISH]:.2%})")

        return detected


# 싱글톤 인스턴스
_localization_manager = None

def get_localization_manager() -> LocalizationManager:
    """다국어 지원 관리자 싱글톤 인스턴스"""
    global _localization_manager
    if _localization_manager is None:
        _localization_manager = LocalizationManager()
    return _localization_manager
