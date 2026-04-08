import os
import smtplib
import json
import urllib.request
from email.message import EmailMessage
from datetime import datetime
import time

def load_env():
    env = {}
    try:
        # Load from the ROOT directory (where run_daily is usually invoked)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(project_root, '.env')
        if not os.path.exists(env_path):
            env_path = '.env'
            
        lines = []
        # Try UTF-16 first (common on Windows PowerShell outputs)
        try:
            with open(env_path, 'r', encoding='utf-16') as f:
                lines = f.readlines()
        except:
            # Fallback to UTF-8
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.strip().split('=', 1)
                env[k.strip()] = v.strip().strip('"\'')
    except Exception as e:
        print(f"  [환경 설정 로드 실패] {e}")
    return env

def get_subscribers(web_app_url):
    try:
        print("  [1/4] 구글 시트에서 구독자 명단을 조회합니다...")
        url = f"{web_app_url}?action=get_subscribers"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            if res.get('status') == 'success':
                return res.get('data', [])
    except Exception as e:
        print(f"  [명단 조회 에러] {e}")
    return []

def send_newsletters(dry_run=False):
    print("============================================================")
    print("                 [알바단지 이메일 자동 발송 시작]                  ")
    print("============================================================")
    
    # 1. 환경 변수 로드
    env = load_env()
    WEB_APP_URL = env.get('WEB_APP_URL')
    GMAIL_USER = env.get('GMAIL_USER')
    GMAIL_APP_PASSWORD = env.get('GMAIL_APP_PASSWORD')
    
    if not all([WEB_APP_URL, GMAIL_USER, GMAIL_APP_PASSWORD]):
        print("  [오류] .env 파일에 필요한 계정 정보(WEB_APP_URL, GMAIL_USER, GMAIL_APP_PASSWORD)가 누락되었습니다.")
        return
        
    # 2. 이번에 보낼 HTML 파일 확인
    today_str = datetime.now().strftime('%Y-%m-%d')
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_html_path = os.path.join(project_root, 'output', 'email', f"{today_str}.html")
    
    if not os.path.exists(output_html_path):
        print(f"  [오류] 오늘의 이메일 파일({output_html_path})이 없습니다. 봇 빌더를 먼저 실행해주세요.")
        return
        
    with open(output_html_path, 'r', encoding='utf-8') as f:
        base_html = f.read()
        
    # 3. 구독자 명단 확인
    subscribers = get_subscribers(WEB_APP_URL)
    
    if not subscribers:
        print("  [2/4] 구독중인 회원이 0명이거나 리스트를 가져오지 못했습니다. 발송을 취소합니다.")
        return
        
    print(f"  [2/4] 총 {len(subscribers)}명의 활성 구독자를 찾았습니다.")
    
    # 4. 발송 진행 (SMTP)
    print("  [3/4] 구글 SMTP 서버에 접속합니다...")
    success_count = 0
    fail_count = 0
    
    try:
        if not dry_run:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    except Exception as e:
        print(f"  [접속 오류] 구글 서버 로그인에 실패했습니다. (앱 비밀번호 확인)\n  - 에러: {e}")
        return
        
    print("  [4/4] 개별 이메일 발송을 시작합니다!")
    for idx, email in enumerate(subscribers):
        # 개별 사용자용 커스텀 취소 링크 삽입
        unsub_link = f"{WEB_APP_URL}?action=unsubscribe&email={email}"
        personal_html = base_html.replace('{UNSUBSCRIBE_LINK}', unsub_link)
        
        msg = EmailMessage()
        msg['Subject'] = f"[알바단지] {today_str} 최신 지원 공고가 도착했습니다!"
        msg['From'] = f"알바단지 <{GMAIL_USER}>"
        msg['To'] = email
        msg.set_content("HTML 형식을 지원하는 메일 클라이언트에서 열어주세요.")
        msg.add_alternative(personal_html, subtype='html')
        
        try:
            if not dry_run:
                server.send_message(msg)
            print(f"      - [{idx+1}/{len(subscribers)}] 전송 완료: {email}")
            success_count += 1
            time.sleep(1) # 부하 방지용 딜레이
        except Exception as e:
            print(f"      - [{idx+1}/{len(subscribers)}] 전송 실패: {email} ({e})")
            fail_count += 1
            
    if not dry_run:
        server.quit()
        
    print("============================================================")
    print(f"[발송 완료] 성공: {success_count}건, 실패: {fail_count}건")
    print("============================================================")

if __name__ == '__main__':
    send_newsletters(dry_run=False)
