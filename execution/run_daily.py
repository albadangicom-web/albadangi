"""
MR Newsletter -- Daily Runner
매일 자동 실행 메인 스크립트

Usage:
    py -3 execution/run_daily.py          # 전체 실행
    py -3 execution/run_daily.py --scrape  # 크롤링만
    py -3 execution/run_daily.py --build   # 빌드만
"""
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "execution"))

from scraper import run_all_scrapers
from newsletter_builder import build_all


def run_daily():
    """매일 실행 전체 파이프라인"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    print("=" * 60)
    print(f"  MR Newsletter Daily Run")
    print(f"  Date: {date_str}")
    print(f"  Time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    # Step 1: 크롤링
    print("\n[Step 1/3] Scraping...")
    postings = run_all_scrapers()
    
    # Step 2: 뉴스레터 빌드
    print("\n[Step 2/3] Building newsletter...")
    build_all(date_str)
    
    # Step 3: 이메일 발송 안내
    email_path = os.path.join(PROJECT_ROOT, "output", "email", f"{date_str}.html")
    subscribers_path = os.path.join(PROJECT_ROOT, "output", "subscribers_emails.txt")
    
    print("\n" + "=" * 60)
    print("  DAILY RUN COMPLETE!")
    print("=" * 60)
    print(f"\n  Postings collected: {len(postings)}")
    print(f"  Email HTML: {email_path}")
    print(f"\n  --- Manual Sending Steps ---")
    print(f"  1. Open the email HTML file in browser to preview")
    print(f"  2. Run: py -3 execution/subscriber_manager.py export")
    print(f"     This creates a BCC email list at: {subscribers_path}")
    print(f"  3. Open Gmail composer")
    print(f"  4. Paste BCC list from subscribers_emails.txt")
    print(f"  5. Copy email HTML content and paste into Gmail body")
    print(f"  6. Send!")
    print("=" * 60)


if __name__ == "__main__":
    args = sys.argv[1:]
    
    if "--scrape" in args:
        run_all_scrapers()
    elif "--build" in args:
        build_all()
    else:
        run_daily()
