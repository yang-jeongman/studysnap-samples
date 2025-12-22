"""
성경 및 찬송가 조회 유틸리티
교회 주보 시스템에서 사용하는 성경 구절 및 찬송가 데이터 관리
"""

import re
from typing import Dict, List, Optional, Tuple


class BibleVerseLookup:
    """성경 구절 조회 및 관리"""

    # 성경 책 이름 매핑 (한글 -> 영문 약어)
    BOOK_MAPPING = {
        # 구약
        "창세기": "gen", "창": "gen",
        "출애굽기": "exo", "출": "exo",
        "레위기": "lev", "레": "lev",
        "민수기": "num", "민": "num",
        "신명기": "deu", "신": "deu",
        "여호수아": "jos", "수": "jos",
        "사사기": "jdg", "삿": "jdg",
        "룻기": "rut", "룻": "rut",
        "사무엘상": "1sa", "삼상": "1sa",
        "사무엘하": "2sa", "삼하": "2sa",
        "열왕기상": "1ki", "왕상": "1ki",
        "열왕기하": "2ki", "왕하": "2ki",
        "역대상": "1ch", "대상": "1ch",
        "역대하": "2ch", "대하": "2ch",
        "에스라": "ezr", "스": "ezr",
        "느헤미야": "neh", "느": "neh",
        "에스더": "est", "에": "est",
        "욥기": "job", "욥": "job",
        "시편": "psa", "시": "psa",
        "잠언": "pro", "잠": "pro",
        "전도서": "ecc", "전": "ecc",
        "아가": "sng", "아": "sng",
        "이사야": "isa", "사": "isa",
        "예레미야": "jer", "렘": "jer",
        "예레미야애가": "lam", "애": "lam",
        "에스겔": "ezk", "겔": "ezk",
        "다니엘": "dan", "단": "dan",
        "호세아": "hos", "호": "hos",
        "요엘": "jol", "욜": "jol",
        "아모스": "amo", "암": "amo",
        "오바댜": "oba", "옵": "oba",
        "요나": "jon", "욘": "jon",
        "미가": "mic", "미": "mic",
        "나훔": "nam", "나": "nam",
        "하박국": "hab", "합": "hab",
        "스바냐": "zep", "습": "zep",
        "학개": "hag", "학": "hag",
        "스가랴": "zec", "슥": "zec",
        "말라기": "mal", "말": "mal",
        # 신약
        "마태복음": "mat", "마": "mat",
        "마가복음": "mrk", "막": "mrk",
        "누가복음": "luk", "눅": "luk",
        "요한복음": "jhn", "요": "jhn",
        "사도행전": "act", "행": "act",
        "로마서": "rom", "롬": "rom",
        "고린도전서": "1co", "고전": "1co",
        "고린도후서": "2co", "고후": "2co",
        "갈라디아서": "gal", "갈": "gal",
        "에베소서": "eph", "엡": "eph",
        "빌립보서": "php", "빌": "php",
        "골로새서": "col", "골": "col",
        "데살로니가전서": "1th", "살전": "1th",
        "데살로니가후서": "2th", "살후": "2th",
        "디모데전서": "1ti", "딤전": "1ti",
        "디모데후서": "2ti", "딤후": "2ti",
        "디도서": "tit", "딛": "tit",
        "빌레몬서": "phm", "몬": "phm",
        "히브리서": "heb", "히": "heb",
        "야고보서": "jas", "약": "jas",
        "베드로전서": "1pe", "벧전": "1pe",
        "베드로후서": "2pe", "벧후": "2pe",
        "요한일서": "1jn", "요일": "1jn",
        "요한이서": "2jn", "요이": "2jn",
        "요한삼서": "3jn", "요삼": "3jn",
        "유다서": "jud", "유": "jud",
        "요한계시록": "rev", "계": "rev"
    }

    # 성경 읽기 URL 템플릿
    BIBLE_URL_TEMPLATES = {
        "대한성서공회": "https://www.bskorea.or.kr/bible/korbibReadpage.php?version=GAE&book={book}&chap={chapter}",
        "두란노": "https://www.duranno.com/bible/main/bible_read.asp?book={book}&chap={chapter}",
        "마이바이블": "https://mybible.kr/bible/{book}/{chapter}"
    }

    @classmethod
    def parse_reference(cls, reference: str) -> Optional[Dict]:
        """
        성경 구절 참조 파싱

        Args:
            reference: "요한복음 3:16", "시편 23:1-6", "로마서 8:28~30"

        Returns:
            {"book": "jhn", "book_kr": "요한복음", "chapter": 3, "verses": "16", "start": 16, "end": 16}
        """
        # 패턴: 책이름 장:절(-절)
        pattern = r'([가-힣]+)\s*(\d+)[:\s]*(\d+)(?:[-~](\d+))?'
        match = re.search(pattern, reference)

        if not match:
            return None

        book_kr = match.group(1)
        chapter = int(match.group(2))
        start_verse = int(match.group(3))
        end_verse = int(match.group(4)) if match.group(4) else start_verse

        book_code = cls.BOOK_MAPPING.get(book_kr)
        if not book_code:
            return None

        return {
            "book": book_code,
            "book_kr": book_kr,
            "chapter": chapter,
            "verses": f"{start_verse}" if start_verse == end_verse else f"{start_verse}-{end_verse}",
            "start": start_verse,
            "end": end_verse
        }

    @classmethod
    def get_bible_url(cls, reference: str, source: str = "대한성서공회") -> Optional[str]:
        """
        성경 읽기 URL 생성

        Args:
            reference: 성경 구절 참조
            source: URL 출처 ("대한성서공회", "두란노", "마이바이블")

        Returns:
            URL 문자열
        """
        parsed = cls.parse_reference(reference)
        if not parsed:
            return None

        template = cls.BIBLE_URL_TEMPLATES.get(source)
        if not template:
            return None

        return template.format(book=parsed["book"], chapter=parsed["chapter"])

    @classmethod
    def generate_modal_data(cls, reference: str, content: str = "") -> Dict:
        """
        모달 팝업용 데이터 생성

        Args:
            reference: 성경 구절 참조
            content: 구절 내용 (HTML 형식)

        Returns:
            모달 데이터 딕셔너리
        """
        parsed = cls.parse_reference(reference)
        key = reference.replace(" ", "_").replace(":", "_").replace("-", "_")

        return {
            "key": key,
            "title": reference,
            "content": content,
            "url": cls.get_bible_url(reference),
            "parsed": parsed
        }


class HymnLookup:
    """찬송가 조회 및 관리"""

    # 찬송가 카테고리
    HYMN_CATEGORIES = {
        "예배": list(range(1, 51)),
        "찬양": list(range(51, 101)),
        "성부하나님": list(range(101, 151)),
        "성자예수": list(range(151, 251)),
        "성령": list(range(251, 301)),
        "성경": list(range(301, 351)),
        "복음": list(range(351, 401)),
        "구원": list(range(401, 451)),
        "신앙": list(range(451, 501)),
        "기도": list(range(501, 551)),
        "헌신": list(range(551, 601)),
        "송영": list(range(601, 651))
    }

    # 주요 찬송가 정보 (자주 사용되는 것들)
    COMMON_HYMNS = {
        1: {"title": "만복의 근원 하나님", "english": "Praise God From Whom All Blessings Flow"},
        21: {"title": "다 찬양하여라", "english": "O for a Thousand Tongues to Sing"},
        26: {"title": "거룩하신 하나님", "english": "Holy God, We Praise Thy Name"},
        28: {"title": "주 달려 죽은 십자가", "english": "When I Survey the Wondrous Cross"},
        30: {"title": "내 맘을 드리오니", "english": "Take My Life and Let It Be"},
        40: {"title": "주 예수 이름 높이어", "english": "All Hail the Power of Jesus' Name"},
        78: {"title": "내 주 하나님 넓고 큰 은혜는", "english": "O Love That Wilt Not Let Me Go"},
        79: {"title": "주 하나님 지으신 모든 세계", "english": "How Great Thou Art"},
        87: {"title": "주여 우리 무리를", "english": "Savior, Like a Shepherd Lead Us"},
        93: {"title": "주 품에 품으소서", "english": "Safe in the Arms of Jesus"},
        94: {"title": "만세 반석 열리니", "english": "Rock of Ages, Cleft for Me"},
        95: {"title": "어지러운 세상 중에", "english": "In the Hour of Trial"},
        100: {"title": "복 있는 사람은", "english": "Blessed Is the Man"},
        130: {"title": "내 구주 예수를 더욱 사랑", "english": "More Love to Thee, O Christ"},
        165: {"title": "높이 계신 주님", "english": "How Great Is Our God"},
        205: {"title": "큰 죄에 빠진 날 위해", "english": "What a Friend We Have in Jesus"},
        218: {"title": "네 맘과 정성을 다하여서", "english": "Take My Life and Let It Be"},
        221: {"title": "내 영혼이 은총 입어", "english": "Amazing Grace"},
        250: {"title": "나의 갈 길 다 가도록", "english": "All the Way My Savior Leads Me"},
        251: {"title": "예수 따라가며", "english": "Where He Leads Me"},
        288: {"title": "오 놀라운 구세주", "english": "He Hideth My Soul"},
        293: {"title": "내 주여 뜻대로", "english": "Have Thine Own Way, Lord"},
        305: {"title": "너 하나님께 이끌리어", "english": "Just As I Am"},
        310: {"title": "예수로 나의 구주 삼고", "english": "Blessed Assurance"},
        320: {"title": "주와 같이 길 가는 것", "english": "Walking with Jesus"},
        338: {"title": "주님께 감사하세", "english": "Give Thanks"},
        339: {"title": "이 세상 끝날까지", "english": "Stand Up, Stand Up for Jesus"},
        370: {"title": "예수 사랑하심은", "english": "Jesus Loves Me"},
        405: {"title": "나 같은 죄인 살리신", "english": "Amazing Grace"},
        430: {"title": "내 영혼이 평안하네", "english": "It Is Well with My Soul"},
        453: {"title": "큰 믿음 주옵소서", "english": "O for a Faith That Will Not Shrink"},
        461: {"title": "내 갈길 멀고 밤은 깊은데", "english": "Lead, Kindly Light"},
        488: {"title": "십자가 군병 되어서", "english": "Onward Christian Soldiers"},
        540: {"title": "주 예수 내 맘에 들어와 계신 후", "english": "Since Jesus Came into My Heart"},
        545: {"title": "예수가 우리를 부르는 소리", "english": "Jesus Calls Us"},
        559: {"title": "내 주 하나님 넓고 큰 은혜는", "english": "O Love That Wilt Not Let Me Go"},
        580: {"title": "예수 나의 예수 이름 찬양", "english": "Jesus, Name Above All Names"},
        600: {"title": "주 하나님 우리를", "english": "For the Beauty of the Earth"},
        635: {"title": "하늘에 계신 (주기도문)", "english": "Our Father Which Art in Heaven"}
    }

    @classmethod
    def get_hymn_info(cls, number: int) -> Optional[Dict]:
        """찬송가 정보 조회"""
        if number in cls.COMMON_HYMNS:
            info = cls.COMMON_HYMNS[number]
            return {
                "number": number,
                "title": info["title"],
                "english": info.get("english", ""),
                "category": cls.get_category(number)
            }
        return {
            "number": number,
            "title": f"찬송가 {number}장",
            "english": "",
            "category": cls.get_category(number)
        }

    @classmethod
    def get_category(cls, number: int) -> str:
        """찬송가 카테고리 조회"""
        for category, numbers in cls.HYMN_CATEGORIES.items():
            if number in numbers:
                return category
        return "기타"

    @classmethod
    def get_youtube_search_url(cls, number: int) -> str:
        """유튜브 검색 URL 생성"""
        hymn_info = cls.get_hymn_info(number)
        title = hymn_info.get("title", f"찬송가 {number}장")
        query = f"새찬송가 {number}장 {title}".replace(" ", "+")
        return f"https://www.youtube.com/results?search_query={query}"

    @classmethod
    def generate_hymn_link_html(cls, hymn_text: str) -> str:
        """
        찬송가 텍스트에서 링크 생성

        Args:
            hymn_text: "21장 다 찬양하여라" 또는 "찬송가 79장"

        Returns:
            HTML 링크 문자열
        """
        # 찬송가 번호 추출
        match = re.search(r'(\d+)장', hymn_text)
        if not match:
            return hymn_text

        number = int(match.group(1))
        url = cls.get_youtube_search_url(number)

        return f'<a href="{url}" target="_blank" class="hymn-link" title="찬송가 {number}장 듣기">{hymn_text}</a>'


class ChurchCalendar:
    """교회력 계산"""

    # 2025년 기준 주요 절기
    LITURGICAL_SEASONS_2025 = {
        "대림절": {"start": "2024-12-01", "end": "2024-12-24", "theme": "advent"},
        "성탄절": {"start": "2024-12-25", "end": "2025-01-05", "theme": "christmas"},
        "주현절": {"start": "2025-01-06", "end": "2025-03-04", "theme": "default"},
        "사순절": {"start": "2025-03-05", "end": "2025-04-19", "theme": "lent"},
        "부활절": {"start": "2025-04-20", "end": "2025-06-07", "theme": "easter"},
        "성령강림절": {"start": "2025-06-08", "end": "2025-11-29", "theme": "pentecost"},
    }

    # 2025년 특별 주일
    SPECIAL_SUNDAYS_2025 = {
        "2025-01-01": {"name": "신년주일", "theme": "default"},
        "2025-02-09": {"name": "성서주일", "theme": "default"},
        "2025-03-02": {"name": "삼일절주일", "theme": "default"},
        "2025-04-13": {"name": "종려주일", "theme": "lent"},
        "2025-04-20": {"name": "부활절", "theme": "easter"},
        "2025-05-04": {"name": "어린이주일", "theme": "default"},
        "2025-05-11": {"name": "어버이주일", "theme": "default"},
        "2025-05-18": {"name": "유아세례주일", "theme": "default"},
        "2025-06-08": {"name": "성령강림절", "theme": "pentecost"},
        "2025-06-15": {"name": "삼위일체주일", "theme": "default"},
        "2025-07-20": {"name": "맥추감사절", "theme": "harvest"},
        "2025-08-17": {"name": "광복절주일", "theme": "default"},
        "2025-09-14": {"name": "교회창립기념주일", "theme": "default"},
        "2025-10-05": {"name": "세계성찬주일", "theme": "default"},
        "2025-10-12": {"name": "전도주일", "theme": "default"},
        "2025-10-26": {"name": "종교개혁주일", "theme": "default"},
        "2025-11-02": {"name": "세계선교주일", "theme": "default"},
        "2025-11-23": {"name": "추수감사절", "theme": "harvest"},
        "2025-11-30": {"name": "대림절 첫째주일", "theme": "advent"},
        "2025-12-07": {"name": "대림절 둘째주일", "theme": "advent"},
        "2025-12-14": {"name": "대림절 셋째주일", "theme": "advent"},
        "2025-12-21": {"name": "대림절 넷째주일", "theme": "advent"},
        "2025-12-25": {"name": "성탄절", "theme": "christmas"},
    }

    @classmethod
    def get_sunday_info(cls, date_str: str) -> Dict:
        """
        특정 날짜의 주일 정보 조회

        Args:
            date_str: "2025-12-07" 형식

        Returns:
            {"name": "대림절 둘째주일", "theme": "advent", "is_special": True}
        """
        # 특별 주일 확인
        if date_str in cls.SPECIAL_SUNDAYS_2025:
            info = cls.SPECIAL_SUNDAYS_2025[date_str]
            return {
                "name": info["name"],
                "theme": info["theme"],
                "is_special": True
            }

        # 일반 주일
        return {
            "name": "주일예배",
            "theme": "default",
            "is_special": False
        }

    @classmethod
    def get_theme_for_date(cls, date_str: str) -> str:
        """날짜에 맞는 테마 반환"""
        info = cls.get_sunday_info(date_str)
        return info.get("theme", "default")


# 편의 함수들
def parse_bible_reference(reference: str) -> Optional[Dict]:
    """성경 구절 참조 파싱"""
    return BibleVerseLookup.parse_reference(reference)


def get_bible_url(reference: str) -> Optional[str]:
    """성경 읽기 URL 생성"""
    return BibleVerseLookup.get_bible_url(reference)


def get_hymn_url(number: int) -> str:
    """찬송가 유튜브 URL 생성"""
    return HymnLookup.get_youtube_search_url(number)


def get_hymn_info(number: int) -> Optional[Dict]:
    """찬송가 정보 조회"""
    return HymnLookup.get_hymn_info(number)


def get_sunday_theme(date_str: str) -> str:
    """주일 테마 조회"""
    return ChurchCalendar.get_theme_for_date(date_str)


def get_sunday_name(date_str: str) -> str:
    """주일 이름 조회"""
    return ChurchCalendar.get_sunday_info(date_str).get("name", "주일예배")
