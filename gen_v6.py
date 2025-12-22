from lecture_generator import LectureHTMLGenerator
import os

test_data = {
    'pages': [
        {'text': '''# 제1장: 뉴턴의 운동법칙

## 1.1 제1법칙 (관성의 법칙)

외부의 힘이 작용하지 않으면 정지한 물체는 계속 정지해 있고, 운동하는 물체는 등속 직선 운동을 계속한다.

**핵심 개념:**
- 관성: 물체가 현재 운동 상태를 유지하려는 성질
- 관성 기준계: 뉴턴의 법칙이 성립하는 좌표계

$$F_{net} = 0 \\Rightarrow \\vec{v} = \\text{constant}$$

## 1.2 제2법칙 (가속도의 법칙)

물체의 가속도는 작용하는 알짜힘에 비례하고, 질량에 반비례한다.

$$\\vec{F} = m\\vec{a}$$
''', 'images': []},
        {'text': '''## 1.3 제3법칙 (작용-반작용의 법칙)

두 물체 사이의 상호작용에서, 한 물체가 다른 물체에 힘을 가하면 동시에 같은 크기의 반대 방향 힘을 받는다.

$$\\vec{F}_{12} = -\\vec{F}_{21}$$

**실생활 예시:**
1. 로켓 추진: 연료가 분출되면서 로켓을 밀어올림
2. 걷기: 발이 땅을 미는 힘 = 땅이 발을 미는 힘

| 작용 | 반작용 | 적용 대상 |
|------|--------|-----------|
| 지구가 사과를 당김 | 사과가 지구를 당김 | 중력 |
| 책상이 책을 밂 | 책이 책상을 누름 | 수직항력 |
''', 'images': []},
        {'text': '''# 제2장: 에너지와 일

## 2.1 일(Work)의 정의

일은 힘이 물체를 이동시킬 때 전달되는 에너지입니다.

$$W = \\vec{F} \\cdot \\vec{d} = Fd\\cos\\theta$$

**일의 단위:** 줄(J) = N·m = kg·m²/s²

## 2.2 역학적 에너지 보존

비보존력이 작용하지 않을 때:
$$E = K + U = \\text{constant}$$

| 구분 | 예시 | 특징 |
|------|------|------|
| 보존력 | 중력, 탄성력 | 에너지 보존 |
| 비보존력 | 마찰력 | 에너지 손실 |
''', 'images': []}
    ],
    'metadata': {'subject': 'physics', 'title': '일반물리학 v6'}
}

generator = LectureHTMLGenerator()
html = generator.generate(test_data, title='일반물리학 - 퀴즈/플래시카드 개선 v6')

os.makedirs('C:/StudySnap-Backend/test/lectures', exist_ok=True)
with open('C:/StudySnap-Backend/test/lectures/physics_responsive_v6.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('생성 완료: physics_responsive_v6.html')
print(f'플래시카드 수: {len(generator.generated_flashcards)}')
print(f'퀴즈 수: {len(generator.generated_quiz)}')

# 플래시카드 내용 출력
print('\n=== 플래시카드 ===')
for i, fc in enumerate(generator.generated_flashcards):
    print(f"{i+1}. 문제: {fc['front'][:50]}...")
    print(f"   답: {fc['back'][:50]}...")

# 퀴즈 내용 출력
print('\n=== 퀴즈 ===')
for q in generator.generated_quiz:
    print(f"{q['id']}. {q['question'][:60]}...")
    print(f"   답: {q['answer'][:50]}...")
