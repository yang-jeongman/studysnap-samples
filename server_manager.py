#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 서버 관리 시스템
여러 프로젝트의 서버를 통합 관리
"""

import json
import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path
from typing import List, Dict, Optional

# Windows 콘솔 UTF-8 설정
if os.name == 'nt':
    try:
        os.system('chcp 65001 >nul 2>&1')
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

class ServerManager:
    def __init__(self):
        self.config_file = Path(__file__).parent / "servers.json"
        self.servers = []
        self.settings = {}
        self.load_config()

    def load_config(self):
        """서버 설정 파일 로드"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.servers = data.get('servers', [])
                self.settings = data.get('settings', {})
        except FileNotFoundError:
            print("⚠️ servers.json 파일을 찾을 수 없습니다.")
            self.servers = []
            self.settings = {}
        except json.JSONDecodeError:
            print("⚠️ servers.json 파일 형식이 올바르지 않습니다.")
            self.servers = []
            self.settings = {}

    def save_config(self):
        """서버 설정 파일 저장"""
        data = {
            'servers': self.servers,
            'settings': self.settings
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("✅ 설정이 저장되었습니다.")

    def get_server_status(self, server: Dict) -> bool:
        """서버 실행 상태 확인"""
        try:
            # 포트 확인
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', server['port']))
            sock.close()
            return result == 0
        except:
            return False

    def kill_process_on_port(self, port: int):
        """특정 포트를 사용하는 프로세스 종료"""
        try:
            if os.name == 'nt':  # Windows
                cmd = f'netstat -ano | findstr :{port}'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            subprocess.run(f'taskkill /F /PID {pid}', shell=True,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
            else:  # Unix/Linux
                cmd = f'lsof -ti:{port} | xargs kill -9'
                subprocess.run(cmd, shell=True)
                return True
        except:
            return False

    def start_server(self, server: Dict):
        """서버 시작"""
        print(f"\n🟢 {server['name']} 시작 중...")

        # 포트 충돌 확인
        if self.get_server_status(server):
            if self.settings.get('kill_on_port_conflict', True):
                print(f"⚠️ 포트 {server['port']} 사용 중 - 기존 프로세스 종료...")
                self.kill_process_on_port(server['port'])
                time.sleep(1)
            else:
                print(f"❌ 포트 {server['port']}가 이미 사용 중입니다.")
                return False

        # 디렉토리 확인
        if not os.path.exists(server['path']):
            print(f"❌ 경로를 찾을 수 없습니다: {server['path']}")
            return False

        # 서버 시작
        try:
            os.chdir(server['path'])

            # 가상환경 활성화 (있는 경우)
            venv_path = Path(server['path']) / 'venv' / 'Scripts' / 'activate.bat'
            if venv_path.exists():
                print("  ✓ 가상환경 활성화")

            # 새 콘솔 창에서 서버 시작
            if os.name == 'nt':  # Windows
                cmd = f'start "서버: {server["name"]}" cmd /k "{server["start_command"]}"'
                subprocess.Popen(cmd, shell=True)
            else:  # Unix/Linux
                subprocess.Popen(server['start_command'], shell=True)

            print(f"✅ {server['name']} 시작됨 (포트: {server['port']})")

            # 브라우저 자동 열기
            if self.settings.get('auto_open_browser', True):
                time.sleep(2)
                webbrowser.open(server['url'])
                print(f"  🌐 브라우저 열림: {server['url']}")

            return True
        except Exception as e:
            print(f"❌ 시작 실패: {e}")
            return False

    def stop_server(self, server: Dict):
        """서버 종료"""
        print(f"\n🔴 {server['name']} 종료 중...")

        if not self.get_server_status(server):
            print(f"⚪ {server['name']}가 실행 중이지 않습니다.")
            return False

        # 포트 기반으로 프로세스 종료
        if self.kill_process_on_port(server['port']):
            print(f"✅ {server['name']} 종료됨")
            return True
        else:
            print(f"❌ 종료 실패")
            return False

    def restart_server(self, server: Dict):
        """서버 재시작"""
        print(f"\n🔄 {server['name']} 재시작 중...")
        self.stop_server(server)
        time.sleep(2)
        self.start_server(server)

    def show_status(self):
        """모든 서버 상태 표시"""
        print("\n" + "="*60)
        print("  📊 서버 상태")
        print("="*60)

        if not self.servers:
            print("⚪ 등록된 서버가 없습니다.")
            return

        for idx, server in enumerate(self.servers, 1):
            status = "✅ 실행 중" if self.get_server_status(server) else "⚪ 중지됨"
            enabled = "🟢" if server.get('enabled', True) else "⚫"

            print(f"\n[{idx}] {enabled} {server['name']}")
            print(f"    상태: {status}")
            print(f"    포트: {server['port']}")
            print(f"    경로: {server['path']}")
            print(f"    URL:  {server['url']}")

    def add_server(self):
        """새 서버 등록"""
        print("\n" + "="*60)
        print("  ➕ 새 서버 등록")
        print("="*60)

        server = {}
        server['id'] = input("\n서버 ID (영문): ").strip()
        server['name'] = input("서버 이름: ").strip()
        server['description'] = input("설명: ").strip()
        server['path'] = input("프로젝트 경로: ").strip()
        server['port'] = int(input("포트 번호: ").strip())

        print("\n서버 타입 선택:")
        print("  [1] FastAPI")
        print("  [2] Flask")
        print("  [3] Django")
        print("  [4] Node.js")
        print("  [5] 기타")

        type_choice = input("\n선택 (1-5): ").strip()
        type_map = {'1': 'fastapi', '2': 'flask', '3': 'django', '4': 'nodejs', '5': 'other'}
        server['type'] = type_map.get(type_choice, 'other')

        server['start_command'] = input("시작 명령어: ").strip()
        server['process_name'] = input("프로세스 이름 (예: python.exe): ").strip()
        server['url'] = input("기본 URL: ").strip()
        server['enabled'] = True
        server['auto_start'] = False
        server['pages'] = []

        self.servers.append(server)
        self.save_config()

        print(f"\n✅ {server['name']} 서버가 등록되었습니다!")

    def remove_server(self):
        """서버 삭제"""
        if not self.servers:
            print("\n⚪ 등록된 서버가 없습니다.")
            return

        self.list_servers()

        try:
            idx = int(input("\n삭제할 서버 번호: ").strip()) - 1
            if 0 <= idx < len(self.servers):
                server = self.servers[idx]
                confirm = input(f"\n정말 '{server['name']}'를 삭제하시겠습니까? (y/N): ").strip().lower()

                if confirm == 'y':
                    self.servers.pop(idx)
                    self.save_config()
                    print(f"\n✅ {server['name']} 서버가 삭제되었습니다.")
                else:
                    print("\n❌ 취소되었습니다.")
            else:
                print("\n❌ 잘못된 번호입니다.")
        except ValueError:
            print("\n❌ 숫자를 입력하세요.")

    def list_servers(self):
        """서버 목록 표시"""
        print("\n" + "="*60)
        print("  📋 등록된 서버 목록")
        print("="*60)

        if not self.servers:
            print("⚪ 등록된 서버가 없습니다.")
            return

        for idx, server in enumerate(self.servers, 1):
            enabled = "🟢" if server.get('enabled', True) else "⚫"
            print(f"\n[{idx}] {enabled} {server['name']}")
            print(f"    {server['description']}")
            print(f"    포트: {server['port']} | 타입: {server['type']}")

    def start_all(self):
        """모든 활성화된 서버 시작"""
        print("\n🚀 모든 서버 시작 중...")

        for server in self.servers:
            if server.get('enabled', True):
                self.start_server(server)
                time.sleep(1)

    def stop_all(self):
        """모든 서버 종료"""
        print("\n🛑 모든 서버 종료 중...")

        for server in self.servers:
            if self.get_server_status(server):
                self.stop_server(server)

    def open_pages(self, server: Dict):
        """서버 페이지 열기"""
        if not server.get('pages'):
            webbrowser.open(server['url'])
            return

        print(f"\n🌐 {server['name']} 페이지:")
        for idx, page in enumerate(server['pages'], 1):
            print(f"  [{idx}] {page['name']}: {page['url']}")

        print("  [0] 뒤로가기")

        choice = input("\n선택: ").strip()

        if choice == '0':
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(server['pages']):
                webbrowser.open(server['pages'][idx]['url'])
                print(f"✅ {server['pages'][idx]['name']} 열림")
        except ValueError:
            print("❌ 잘못된 입력입니다.")

    def main_menu(self):
        """메인 메뉴"""
        while True:
            print("\n" + "="*60)
            print("  🎛️  통합 서버 관리 시스템")
            print("="*60)
            print("\n  [1] 📊 서버 상태")
            print("  [2] 🟢 서버 시작")
            print("  [3] 🔴 서버 종료")
            print("  [4] 🔄 서버 재시작")
            print("  [5] 🌐 브라우저 열기")
            print("\n  [6] ➕ 서버 추가")
            print("  [7] ➖ 서버 삭제")
            print("  [8] 📋 서버 목록")
            print("\n  [9] 🚀 모든 서버 시작")
            print("  [0] 🛑 모든 서버 종료")
            print("\n  [q] ❌ 종료")

            choice = input("\n선택: ").strip().lower()

            if choice == '1':
                self.show_status()

            elif choice == '2':
                self.list_servers()
                try:
                    idx = int(input("\n시작할 서버 번호: ").strip()) - 1
                    if 0 <= idx < len(self.servers):
                        self.start_server(self.servers[idx])
                except ValueError:
                    print("❌ 숫자를 입력하세요.")

            elif choice == '3':
                self.list_servers()
                try:
                    idx = int(input("\n종료할 서버 번호: ").strip()) - 1
                    if 0 <= idx < len(self.servers):
                        self.stop_server(self.servers[idx])
                except ValueError:
                    print("❌ 숫자를 입력하세요.")

            elif choice == '4':
                self.list_servers()
                try:
                    idx = int(input("\n재시작할 서버 번호: ").strip()) - 1
                    if 0 <= idx < len(self.servers):
                        self.restart_server(self.servers[idx])
                except ValueError:
                    print("❌ 숫자를 입력하세요.")

            elif choice == '5':
                self.list_servers()
                try:
                    idx = int(input("\n브라우저를 열 서버 번호: ").strip()) - 1
                    if 0 <= idx < len(self.servers):
                        self.open_pages(self.servers[idx])
                except ValueError:
                    print("❌ 숫자를 입력하세요.")

            elif choice == '6':
                self.add_server()

            elif choice == '7':
                self.remove_server()

            elif choice == '8':
                self.list_servers()

            elif choice == '9':
                self.start_all()

            elif choice == '0':
                self.stop_all()

            elif choice == 'q':
                print("\n👋 종료합니다.")
                break

            else:
                print("\n❌ 잘못된 선택입니다.")

            input("\n계속하려면 Enter를 누르세요...")

def main():
    """메인 함수"""
    manager = ServerManager()

    # 명령행 인자 처리
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'start':
            if len(sys.argv) > 2:
                server_id = sys.argv[2]
                server = next((s for s in manager.servers if s['id'] == server_id), None)
                if server:
                    manager.start_server(server)
                else:
                    print(f"❌ 서버를 찾을 수 없습니다: {server_id}")
            else:
                manager.start_all()

        elif command == 'stop':
            if len(sys.argv) > 2:
                server_id = sys.argv[2]
                server = next((s for s in manager.servers if s['id'] == server_id), None)
                if server:
                    manager.stop_server(server)
                else:
                    print(f"❌ 서버를 찾을 수 없습니다: {server_id}")
            else:
                manager.stop_all()

        elif command == 'restart':
            if len(sys.argv) > 2:
                server_id = sys.argv[2]
                server = next((s for s in manager.servers if s['id'] == server_id), None)
                if server:
                    manager.restart_server(server)
                else:
                    print(f"❌ 서버를 찾을 수 없습니다: {server_id}")

        elif command == 'status':
            manager.show_status()

        elif command == 'list':
            manager.list_servers()

        else:
            print(f"❌ 알 수 없는 명령어: {command}")
            print("\n사용법:")
            print("  server-manager.bat              (메뉴)")
            print("  server-manager.bat start [id]   (서버 시작)")
            print("  server-manager.bat stop [id]    (서버 종료)")
            print("  server-manager.bat restart [id] (서버 재시작)")
            print("  server-manager.bat status       (서버 상태)")
            print("  server-manager.bat list         (서버 목록)")
    else:
        # 메뉴 모드
        manager.main_menu()

if __name__ == '__main__':
    main()
