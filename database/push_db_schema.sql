-- ============================================================
-- 푸시 알림 시스템 데이터베이스 스키마
-- ============================================================
-- 생성일: 2025-12-25
-- 목적: 여의도순복음교회 모바일 주보 푸시 알림 관리
-- ============================================================

-- 1. 디바이스 토큰 테이블
-- FCM 토큰 및 사용자 디바이스 정보 저장
CREATE TABLE IF NOT EXISTS device_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token VARCHAR(255) UNIQUE NOT NULL,          -- FCM 디바이스 토큰
    device_type VARCHAR(10) DEFAULT 'web',       -- 'ios', 'android', 'web'
    device_id VARCHAR(100),                      -- 디바이스 고유 ID (선택)
    user_id VARCHAR(100),                        -- 사용자 식별자 (선택, 익명 가능)
    language VARCHAR(5) DEFAULT 'ko',            -- 사용자 언어 ('ko', 'en', 'zh', 'ja', 'id', 'es', 'ru', 'fr')
    topics TEXT,                                 -- 구독 토픽 (JSON 배열, 예: ["fgfc-all", "fgfc-korean"])
    browser_info TEXT,                           -- 브라우저 정보 (JSON)
    os_info TEXT,                                -- OS 정보 (JSON)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1                  -- 활성 여부 (0: 비활성, 1: 활성)
);

-- 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_token ON device_tokens(token);
CREATE INDEX IF NOT EXISTS idx_language ON device_tokens(language);
CREATE INDEX IF NOT EXISTS idx_device_type ON device_tokens(device_type);
CREATE INDEX IF NOT EXISTS idx_is_active ON device_tokens(is_active);
CREATE INDEX IF NOT EXISTS idx_last_active ON device_tokens(last_active);


-- 2. 푸시 알림 발송 기록 테이블
-- 발송한 모든 푸시 알림 이력 저장
CREATE TABLE IF NOT EXISTS push_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,                 -- 알림 제목
    message TEXT NOT NULL,                       -- 알림 내용
    topic VARCHAR(100),                          -- 발송 토픽 (예: 'fgfc-all', 'fgfc-korean')
    target_type VARCHAR(20) DEFAULT 'topic',     -- 'topic', 'device', 'multicast'
    target_count INTEGER DEFAULT 0,              -- 발송 대상 수
    success_count INTEGER DEFAULT 0,             -- 성공 수
    failure_count INTEGER DEFAULT 0,             -- 실패 수
    data TEXT,                                   -- 추가 데이터 (JSON)
    image_url TEXT,                              -- 이미지 URL (선택)
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_by VARCHAR(100),                        -- 발송자 (관리자 ID)
    response_id VARCHAR(100),                    -- FCM 응답 ID
    status VARCHAR(20) DEFAULT 'pending'         -- 'pending', 'sent', 'failed'
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_topic ON push_notifications(topic);
CREATE INDEX IF NOT EXISTS idx_sent_at ON push_notifications(sent_at);
CREATE INDEX IF NOT EXISTS idx_status ON push_notifications(status);


-- 3. 토픽 관리 테이블
-- 사용 가능한 토픽 목록 및 설명
CREATE TABLE IF NOT EXISTS push_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_name VARCHAR(100) UNIQUE NOT NULL,     -- 토픽 이름 (예: 'fgfc-all')
    display_name VARCHAR(200),                   -- 표시 이름 (예: '전체 알림')
    description TEXT,                            -- 토픽 설명
    language VARCHAR(5),                         -- 언어 코드 (NULL이면 전체)
    subscriber_count INTEGER DEFAULT 0,          -- 구독자 수
    is_active BOOLEAN DEFAULT 1,                 -- 활성 여부
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 기본 토픽 데이터 삽입
INSERT OR IGNORE INTO push_topics (topic_name, display_name, description, language) VALUES
('fgfc-all', '전체 알림', '모든 사용자에게 발송', NULL),
('fgfc-korean', '한국어 알림', '한국어 사용자 대상', 'ko'),
('fgfc-english', 'English Notifications', 'For English speakers', 'en'),
('fgfc-chinese', '中文通知', '中文用户', 'zh'),
('fgfc-japanese', '日本語通知', '日本語ユーザー', 'ja'),
('fgfc-indonesian', 'Notifikasi Indonesia', 'Untuk pengguna Indonesia', 'id'),
('fgfc-spanish', 'Notificaciones en Español', 'Para usuarios de español', 'es'),
('fgfc-russian', 'Русские уведомления', 'Для русскоязычных пользователей', 'ru'),
('fgfc-french', 'Notifications Françaises', 'Pour les francophones', 'fr');


-- 4. 푸시 알림 템플릿 테이블
-- 자주 사용하는 푸시 알림 템플릿 저장
CREATE TABLE IF NOT EXISTS push_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_name VARCHAR(100) UNIQUE NOT NULL,  -- 템플릿 이름 (예: 'bulletin_update')
    title_ko VARCHAR(200),                       -- 제목 (한국어)
    title_en VARCHAR(200),                       -- 제목 (영어)
    title_zh VARCHAR(200),                       -- 제목 (중국어)
    title_ja VARCHAR(200),                       -- 제목 (일본어)
    message_ko TEXT,                             -- 메시지 (한국어)
    message_en TEXT,                             -- 메시지 (영어)
    message_zh TEXT,                             -- 메시지 (중국어)
    message_ja TEXT,                             -- 메시지 (일본어)
    variables TEXT,                              -- 변수 (JSON 배열, 예: ["church_name", "date"])
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 기본 템플릿 삽입
INSERT OR IGNORE INTO push_templates (
    template_name,
    title_ko, title_en, title_zh, title_ja,
    message_ko, message_en, message_zh, message_ja,
    variables
) VALUES
(
    'bulletin_update',
    '📖 새 주보가 업데이트되었습니다',
    '📖 New Bulletin Available',
    '📖 新周报已更新',
    '📖 新しい週報が更新されました',
    '{church_name} {date} 주보를 확인하세요',
    'Check out {church_name} bulletin for {date}',
    '查看 {church_name} {date} 周报',
    '{church_name} {date} の週報をご確認ください',
    '["church_name", "date"]'
),
(
    'emergency_notice',
    '🚨 긴급 공지',
    '🚨 Urgent Notice',
    '🚨 紧急通知',
    '🚨 緊急のお知らせ',
    '{message}',
    '{message}',
    '{message}',
    '{message}',
    '["message"]'
),
(
    'event_reminder',
    '📅 행사 안내',
    '📅 Event Reminder',
    '📅 活动提醒',
    '📅 イベントのお知らせ',
    '{event_name} - {date}에 진행됩니다',
    '{event_name} will be held on {date}',
    '{event_name} 将于 {date} 举行',
    '{event_name} は {date} に開催されます',
    '["event_name", "date"]'
);


-- 5. 푸시 알림 스케줄 테이블
-- 예약 발송 관리
CREATE TABLE IF NOT EXISTS push_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    topic VARCHAR(100),
    scheduled_at TIMESTAMP NOT NULL,             -- 예약 시간
    status VARCHAR(20) DEFAULT 'scheduled',      -- 'scheduled', 'sent', 'cancelled', 'failed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    created_by VARCHAR(100)                      -- 생성자
);

CREATE INDEX IF NOT EXISTS idx_scheduled_at ON push_schedules(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_schedule_status ON push_schedules(status);


-- 6. 푸시 알림 통계 뷰 (읽기 전용)
-- 발송 통계 조회용 뷰
CREATE VIEW IF NOT EXISTS push_stats AS
SELECT
    DATE(sent_at) as send_date,
    COUNT(*) as total_pushes,
    SUM(target_count) as total_targets,
    SUM(success_count) as total_success,
    SUM(failure_count) as total_failures,
    ROUND(CAST(SUM(success_count) AS FLOAT) / SUM(target_count) * 100, 2) as success_rate
FROM push_notifications
WHERE status = 'sent'
GROUP BY DATE(sent_at)
ORDER BY send_date DESC;


-- 7. 활성 디바이스 통계 뷰
CREATE VIEW IF NOT EXISTS active_devices_stats AS
SELECT
    device_type,
    language,
    COUNT(*) as device_count,
    COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_count,
    COUNT(CASE WHEN DATE(last_active) = DATE('now') THEN 1 END) as today_active
FROM device_tokens
GROUP BY device_type, language;


-- ============================================================
-- 샘플 쿼리 예시
-- ============================================================

-- 1. 전체 활성 디바이스 수 조회
-- SELECT COUNT(*) FROM device_tokens WHERE is_active = 1;

-- 2. 언어별 디바이스 수
-- SELECT language, COUNT(*) as count FROM device_tokens WHERE is_active = 1 GROUP BY language;

-- 3. 최근 7일간 발송 통계
-- SELECT * FROM push_stats WHERE send_date >= DATE('now', '-7 days');

-- 4. 특정 토픽 구독자 수
-- SELECT COUNT(*) FROM device_tokens WHERE topics LIKE '%"fgfc-korean"%' AND is_active = 1;

-- 5. 오늘 발송한 푸시 알림 목록
-- SELECT * FROM push_notifications WHERE DATE(sent_at) = DATE('now') ORDER BY sent_at DESC;

-- 6. 실패율 높은 푸시 조회 (성공률 80% 이하)
-- SELECT * FROM push_notifications
-- WHERE success_count > 0 AND (CAST(success_count AS FLOAT) / target_count) < 0.8
-- ORDER BY sent_at DESC LIMIT 10;
