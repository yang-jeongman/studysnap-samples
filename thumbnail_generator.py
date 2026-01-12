"""
교회 주보 및 선거 공보물 썸네일 이미지 자동 생성기
SMS/카카오톡 링크 공유 시 노출되는 OG 이미지 생성
"""

from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime

class ThumbnailGenerator:
    """소셜 미디어 썸네일 이미지 생성기"""

    def __init__(self):
        # OG 이미지 표준 크기 (1200x630px)
        self.og_width = 1200
        self.og_height = 630

        # 한글 폰트 경로 (Windows 기본 폰트)
        self.font_paths = {
            "bold": "C:/Windows/Fonts/malgunbd.ttf",  # 맑은 고딕 Bold
            "regular": "C:/Windows/Fonts/malgun.ttf"   # 맑은 고딕
        }

    def create_church_bulletin_thumbnail(
        self,
        church_name: str,
        bulletin_date: str,
        sermon_title: str = "",
        verse_ref: str = "",
        output_path: str = None
    ) -> str:
        """
        교회 주보 썸네일 생성

        Args:
            church_name: 교회명 (예: "여의도순복음교회")
            bulletin_date: 주보 날짜 (예: "2025-12-29")
            sermon_title: 설교 제목 (선택)
            verse_ref: 성경 구절 (예: "누가복음 3:4-6")
            output_path: 저장 경로 (None이면 자동 생성)

        Returns:
            생성된 이미지 파일 경로
        """
        # 이미지 생성 (보라색 그라디언트 배경)
        img = Image.new('RGB', (self.og_width, self.og_height), color='#4A3D82')
        draw = ImageDraw.Draw(img)

        # 그라디언트 효과 (상단: 진한 보라, 하단: 밝은 보라)
        for y in range(self.og_height):
            ratio = y / self.og_height
            r = int(90 + (91 * ratio))   # 5A → 5B
            g = int(61 + (14 * ratio))   # 3D → 4B
            b = int(130 + (28 * ratio))  # 82 → 9E
            color = (r, g, b)
            draw.rectangle([(0, y), (self.og_width, y + 1)], fill=color)

        # 상단 흰색 반투명 박스
        top_box_height = 200
        overlay = Image.new('RGBA', (self.og_width, self.og_height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            [(0, 0), (self.og_width, top_box_height)],
            fill=(255, 255, 255, 60)
        )
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)

        # 중앙 콘텐츠 박스 (둥근 모서리)
        content_box = [100, 250, 1100, 550]
        draw.rounded_rectangle(content_box, radius=20, fill=(255, 255, 255))

        try:
            # 폰트 로드
            font_title = ImageFont.truetype(self.font_paths["bold"], 80)
            font_church = ImageFont.truetype(self.font_paths["bold"], 100)
            font_date = ImageFont.truetype(self.font_paths["regular"], 50)
            font_subtitle = ImageFont.truetype(self.font_paths["regular"], 40)
        except:
            # 폰트 로드 실패 시 기본 폰트
            font_title = ImageFont.load_default()
            font_church = ImageFont.load_default()
            font_date = ImageFont.load_default()
            font_subtitle = ImageFont.load_default()

        # 날짜 파싱 (YYYY-MM-DD → YYYY년 M월 D일)
        try:
            date_obj = datetime.strptime(bulletin_date, "%Y-%m-%d")
            date_text = f"{date_obj.year}년 {date_obj.month}월 {date_obj.day}일"
        except:
            date_text = bulletin_date

        # 텍스트 그리기
        # 1. 상단: "주보" 타이틀
        title_text = "주보"
        title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
        title_x = (self.og_width - (title_bbox[2] - title_bbox[0])) // 2
        draw.text((title_x, 50), title_text, fill=(255, 255, 255), font=font_title)

        # 2. 교회명 (중앙 박스)
        church_bbox = draw.textbbox((0, 0), church_name, font=font_church)
        church_x = (self.og_width - (church_bbox[2] - church_bbox[0])) // 2
        draw.text((church_x, 300), church_name, fill=(90, 61, 130), font=font_church)

        # 3. 날짜 (교회명 아래)
        date_bbox = draw.textbbox((0, 0), date_text, font=font_date)
        date_x = (self.og_width - (date_bbox[2] - date_bbox[0])) // 2
        draw.text((date_x, 420), date_text, fill=(107, 114, 128), font=font_date)

        # 4. 성경 구절 (하단)
        if verse_ref:
            verse_bbox = draw.textbbox((0, 0), verse_ref, font=font_subtitle)
            verse_x = (self.og_width - (verse_bbox[2] - verse_bbox[0])) // 2
            draw.text((verse_x, 490), verse_ref, fill=(107, 114, 128), font=font_subtitle)

        # 하단 워터마크
        watermark = "StudySnap Mobile 주보"
        watermark_bbox = draw.textbbox((0, 0), watermark, font=font_subtitle)
        watermark_x = (self.og_width - (watermark_bbox[2] - watermark_bbox[0])) // 2
        draw.text((watermark_x, 570), watermark, fill=(255, 255, 255), font=font_subtitle)

        # 파일 저장
        if not output_path:
            output_dir = f"outputs/Church/{church_name}"
            os.makedirs(output_dir, exist_ok=True)
            output_path = f"{output_dir}/{bulletin_date}_thumbnail.jpg"

        img.save(output_path, "JPEG", quality=95, optimize=True)
        return output_path

    def create_election_thumbnail(
        self,
        candidate_name: str,
        party: str,
        district: str,
        slogan: str = "",
        output_path: str = None
    ) -> str:
        """선거 공보물 썸네일 생성"""
        # 정당별 색상
        party_colors = {
            "더불어민주당": {"primary": (0, 112, 192), "accent": (0, 176, 240)},
            "국민의힘": {"primary": (227, 33, 46), "accent": (237, 125, 49)},
            "진보당": {"primary": (255, 192, 0), "accent": (146, 208, 80)}
        }

        colors = party_colors.get(party, {"primary": (0, 112, 192), "accent": (0, 176, 240)})

        # 이미지 생성
        img = Image.new('RGB', (self.og_width, self.og_height), color=colors["primary"])
        draw = ImageDraw.Draw(img)

        # 그라디언트
        for y in range(200):
            ratio = y / 200
            r = int(colors["primary"][0] + ((colors["accent"][0] - colors["primary"][0]) * ratio))
            g = int(colors["primary"][1] + ((colors["accent"][1] - colors["primary"][1]) * ratio))
            b = int(colors["primary"][2] + ((colors["accent"][2] - colors["primary"][2]) * ratio))
            draw.rectangle([(0, y), (self.og_width, y + 1)], fill=(r, g, b))

        # 하단 박스
        draw.rectangle([(0, 200), (self.og_width, self.og_height)], fill=(245, 245, 245))

        try:
            font_badge = ImageFont.truetype(self.font_paths["regular"], 40)
            font_name = ImageFont.truetype(self.font_paths["bold"], 120)
            font_slogan = ImageFont.truetype(self.font_paths["bold"], 60)
            font_number = ImageFont.truetype(self.font_paths["bold"], 200)
        except:
            font_badge = font_name = font_slogan = font_number = ImageFont.load_default()

        # 배지
        draw.rounded_rectangle([(50, 30), (250, 90)], radius=30, fill=(0, 176, 240))
        badge_bbox = draw.textbbox((0, 0), "기호 1번", font=font_badge)
        badge_x = 150 - (badge_bbox[2] - badge_bbox[0]) // 2
        draw.text((badge_x, 45), "기호 1번", fill=(255, 255, 255), font=font_badge)

        # 후보자명
        name_bbox = draw.textbbox((0, 0), candidate_name, font=font_name)
        name_x = (self.og_width - (name_bbox[2] - name_bbox[0])) // 2
        draw.text((name_x, 100), candidate_name, fill=(255, 255, 255), font=font_name)

        # 슬로건
        if slogan:
            slogan_bbox = draw.textbbox((0, 0), slogan, font=font_slogan)
            slogan_x = (self.og_width - (slogan_bbox[2] - slogan_bbox[0])) // 2
            draw.text((slogan_x, 240), slogan, fill=(0, 112, 192), font=font_slogan)

        # 번호 1
        number_bbox = draw.textbbox((0, 0), "1", font=font_number)
        number_x = (self.og_width - (number_bbox[2] - number_bbox[0])) // 2
        draw.text((number_x, 350), "1", fill=(255, 192, 0), font=font_number)

        # 파일 저장
        if not output_path:
            output_dir = f"outputs/Election/{party}/{candidate_name}"
            os.makedirs(output_dir, exist_ok=True)
            output_path = f"{output_dir}/{candidate_name}_thumbnail.jpg"

        img.save(output_path, "JPEG", quality=95, optimize=True)
        return output_path


if __name__ == "__main__":
    generator = ThumbnailGenerator()

    # 교회 주보 테스트
    church_thumb = generator.create_church_bulletin_thumbnail(
        church_name="여의도순복음교회",
        bulletin_date="2025-12-29",
        verse_ref="누가복음 3:4-6"
    )
    print(f"교회 주보 썸네일: {church_thumb}")

    # 선거 공보물 테스트
    election_thumb = generator.create_election_thumbnail(
        candidate_name="김병욱",
        party="더불어민주당",
        district="31선 국토교통위원장",
        slogan="말끔이 아닌 진짜일꾼!"
    )
    print(f"선거 공보물 썸네일: {election_thumb}")
