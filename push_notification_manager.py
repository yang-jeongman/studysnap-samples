"""
푸시 알림 관리자 (Push Notification Manager)

Firebase Cloud Messaging (FCM)을 사용한 푸시 알림 시스템
여의도순복음교회 모바일 주보 사용자에게 실시간 알림 발송

사용 예시:
    push_manager = PushNotificationManager()

    # 전체 사용자에게 발송
    push_manager.send_to_topic(
        topic='fgfc-all',
        title='새 주보 업데이트',
        body='2025-12-29 주보가 업데이트되었습니다'
    )

    # 특정 언어 사용자에게 발송
    push_manager.send_to_topic(
        topic='fgfc-english',
        title='New Bulletin Available',
        body='Check out the latest bulletin for 2025-12-29'
    )
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

# Firebase Admin SDK (설치 필요: pip install firebase-admin)
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logging.warning("⚠️ Firebase Admin SDK가 설치되지 않았습니다. 'pip install firebase-admin' 실행 필요")

logger = logging.getLogger(__name__)


class PushNotificationManager:
    """
    푸시 알림 관리자

    Firebase Cloud Messaging을 통해 모바일 주보 사용자에게 푸시 알림 발송
    """

    def __init__(self, credentials_path: str = None):
        """
        푸시 알림 관리자 초기화

        Args:
            credentials_path: Firebase 서비스 계정 JSON 키 파일 경로
                             None일 경우 환경변수 FIREBASE_CREDENTIALS_PATH 사용
        """
        self.initialized = False

        if not FIREBASE_AVAILABLE:
            logger.error("❌ Firebase Admin SDK가 설치되지 않음")
            return

        # Firebase 서비스 계정 키 경로
        if credentials_path is None:
            credentials_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-service-account.json')

        self.credentials_path = credentials_path

        # Firebase 초기화
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred)
                self.initialized = True
                logger.info("✅ Firebase Cloud Messaging 초기화 완료")
            else:
                self.initialized = True
                logger.info("✅ Firebase 이미 초기화됨")
        except FileNotFoundError:
            logger.error(f"❌ Firebase 서비스 계정 키 파일 없음: {credentials_path}")
            logger.info("""
            Firebase 서비스 계정 키 설정 방법:
            1. https://console.firebase.google.com 접속
            2. 프로젝트 설정 → 서비스 계정
            3. '새 비공개 키 생성' 클릭
            4. 다운로드한 JSON 파일을 'firebase-service-account.json'으로 저장
            """)
        except Exception as e:
            logger.error(f"❌ Firebase 초기화 실패: {str(e)}")

    def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict] = None,
        image_url: Optional[str] = None
    ) -> Optional[str]:
        """
        특정 토픽 구독자들에게 푸시 알림 발송

        Args:
            topic: 토픽 이름 (예: 'fgfc-all', 'fgfc-korean', 'fgfc-english')
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터 (딕셔너리)
            image_url: 알림에 표시할 이미지 URL (선택)

        Returns:
            성공 시 메시지 ID, 실패 시 None

        Example:
            >>> push_manager.send_to_topic(
            ...     topic='fgfc-all',
            ...     title='📖 새 주보 업데이트',
            ...     body='여의도순복음교회 2025-12-29 주보가 업데이트되었습니다',
            ...     data={'url': '/bulletins/2025-12-29.html'}
            ... )
        """
        if not self.initialized:
            logger.error("❌ Firebase가 초기화되지 않음")
            return None

        try:
            # 알림 메시지 구성
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )

            # 메시지 생성
            message = messaging.Message(
                notification=notification,
                data=data or {},
                topic=topic,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        icon='ic_notification',
                        color='#5B4B9E',  # 여의도순복음교회 메인 컬러
                        sound='default'
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            badge=1,
                            sound='default'
                        )
                    )
                ),
                webpush=messaging.WebpushConfig(
                    notification=messaging.WebpushNotification(
                        icon='/static/icon-192x192.png',
                        badge='/static/badge-72x72.png',
                        vibrate=[200, 100, 200]
                    )
                )
            )

            # 메시지 발송
            response = messaging.send(message)
            logger.info(f"✅ 푸시 발송 성공 (topic: {topic}): {response}")
            return response

        except Exception as e:
            logger.error(f"❌ 푸시 발송 실패 (topic: {topic}): {str(e)}")
            return None

    def send_to_device(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict] = None,
        image_url: Optional[str] = None
    ) -> Optional[str]:
        """
        특정 디바이스에 푸시 알림 발송

        Args:
            token: FCM 디바이스 토큰
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터
            image_url: 이미지 URL

        Returns:
            성공 시 메시지 ID, 실패 시 None
        """
        if not self.initialized:
            logger.error("❌ Firebase가 초기화되지 않음")
            return None

        try:
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )

            message = messaging.Message(
                notification=notification,
                data=data or {},
                token=token
            )

            response = messaging.send(message)
            logger.info(f"✅ 푸시 발송 성공 (device): {response}")
            return response

        except Exception as e:
            logger.error(f"❌ 푸시 발송 실패 (device): {str(e)}")
            return None

    def send_multicast(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict] = None
    ) -> Optional[messaging.BatchResponse]:
        """
        여러 디바이스에 동시 푸시 발송 (최대 500개)

        Args:
            tokens: FCM 디바이스 토큰 리스트 (최대 500개)
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터

        Returns:
            BatchResponse 객체 (성공/실패 통계 포함)
        """
        if not self.initialized:
            logger.error("❌ Firebase가 초기화되지 않음")
            return None

        if len(tokens) > 500:
            logger.warning(f"⚠️ 토큰 개수가 500개를 초과함 ({len(tokens)}개). 처음 500개만 발송")
            tokens = tokens[:500]

        try:
            notification = messaging.Notification(title=title, body=body)
            message = messaging.MulticastMessage(
                notification=notification,
                data=data or {},
                tokens=tokens
            )

            response = messaging.send_multicast(message)
            logger.info(f"✅ 멀티캐스트 발송: {response.success_count}/{len(tokens)} 성공")

            # 실패한 토큰 로그
            if response.failure_count > 0:
                failed_tokens = [
                    tokens[idx] for idx, resp in enumerate(response.responses) if not resp.success
                ]
                logger.warning(f"⚠️ 실패한 토큰: {failed_tokens[:5]}...")  # 처음 5개만 표시

            return response

        except Exception as e:
            logger.error(f"❌ 멀티캐스트 발송 실패: {str(e)}")
            return None

    def subscribe_to_topic(self, tokens: List[str], topic: str) -> Optional[messaging.TopicManagementResponse]:
        """
        디바이스를 토픽에 구독

        Args:
            tokens: FCM 디바이스 토큰 리스트
            topic: 토픽 이름

        Returns:
            TopicManagementResponse 객체

        Example:
            >>> push_manager.subscribe_to_topic(
            ...     tokens=['token1', 'token2'],
            ...     topic='fgfc-korean'
            ... )
        """
        if not self.initialized:
            logger.error("❌ Firebase가 초기화되지 않음")
            return None

        try:
            response = messaging.subscribe_to_topic(tokens, topic)
            logger.info(f"✅ 토픽 구독 성공 ({topic}): {response.success_count}/{len(tokens)}")
            return response
        except Exception as e:
            logger.error(f"❌ 토픽 구독 실패 ({topic}): {str(e)}")
            return None

    def unsubscribe_from_topic(self, tokens: List[str], topic: str) -> Optional[messaging.TopicManagementResponse]:
        """
        디바이스를 토픽에서 구독 해지

        Args:
            tokens: FCM 디바이스 토큰 리스트
            topic: 토픽 이름

        Returns:
            TopicManagementResponse 객체
        """
        if not self.initialized:
            logger.error("❌ Firebase가 초기화되지 않음")
            return None

        try:
            response = messaging.unsubscribe_from_topic(tokens, topic)
            logger.info(f"✅ 토픽 구독 해지 성공 ({topic}): {response.success_count}/{len(tokens)}")
            return response
        except Exception as e:
            logger.error(f"❌ 토픽 구독 해지 실패 ({topic}): {str(e)}")
            return None

    def send_bulletin_update_notification(
        self,
        church_name: str,
        bulletin_date: str,
        bulletin_url: str,
        language: str = 'ko'
    ) -> Optional[str]:
        """
        주보 업데이트 알림 발송 (편의 메서드)

        Args:
            church_name: 교회 이름
            bulletin_date: 주보 날짜
            bulletin_url: 주보 URL
            language: 언어 코드 ('ko', 'en', 'zh' 등)

        Returns:
            메시지 ID
        """
        # 언어별 메시지
        messages = {
            'ko': {
                'title': f'📖 새 주보가 업데이트되었습니다',
                'body': f'{church_name} {bulletin_date} 주보를 확인하세요'
            },
            'en': {
                'title': '📖 New Bulletin Available',
                'body': f'Check out {church_name} bulletin for {bulletin_date}'
            },
            'zh': {
                'title': '📖 新周报已更新',
                'body': f'查看 {church_name} {bulletin_date} 周报'
            },
            'ja': {
                'title': '📖 新しい週報が更新されました',
                'body': f'{church_name} {bulletin_date} の週報をご確認ください'
            }
        }

        msg = messages.get(language, messages['ko'])

        return self.send_to_topic(
            topic=f'fgfc-{language}',
            title=msg['title'],
            body=msg['body'],
            data={'url': bulletin_url, 'type': 'bulletin_update'}
        )


# 테스트 코드
if __name__ == "__main__":
    import sys

    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print("푸시 알림 관리자 테스트")
    print("=" * 60)

    # 푸시 관리자 초기화
    push_manager = PushNotificationManager()

    if not push_manager.initialized:
        print("\n❌ Firebase 초기화 실패")
        print("\n다음 단계:")
        print("1. Firebase Console에서 서비스 계정 키 다운로드")
        print("2. 'firebase-service-account.json'으로 저장")
        print("3. 다시 실행")
        sys.exit(1)

    print("\n✅ Firebase 초기화 성공!")
    print("\n사용 가능한 메서드:")
    print("- send_to_topic(): 토픽 구독자에게 발송")
    print("- send_to_device(): 특정 디바이스에 발송")
    print("- send_multicast(): 여러 디바이스에 동시 발송")
    print("- subscribe_to_topic(): 토픽 구독")
    print("- send_bulletin_update_notification(): 주보 업데이트 알림")

    # 테스트 발송 (주석 처리됨 - 실제 사용 시 주석 해제)
    # response = push_manager.send_to_topic(
    #     topic='fgfc-test',
    #     title='테스트 푸시 알림',
    #     body='푸시 알림 시스템이 정상 작동합니다',
    #     data={'test': 'true'}
    # )
    #
    # if response:
    #     print(f"\n✅ 테스트 푸시 발송 완료: {response}")
    # else:
    #     print("\n❌ 테스트 푸시 발송 실패")
