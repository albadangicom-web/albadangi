"""
MR Newsletter -- Newsletter Builder
크롤링 데이터 -> 웹사이트 HTML + 이메일 HTML 생성
"""
import json
import os
import sqlite3
import sys
from datetime import datetime

# 프로젝트 루트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "newsletter.db")
WEBSITE_DIR = os.path.join(PROJECT_ROOT, "newsletter-website")
OUTPUT_EMAIL_DIR = os.path.join(PROJECT_ROOT, "output", "email")
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "templates")
SCRAPED_DATA_DIR = os.path.join(PROJECT_ROOT, ".tmp", "scraped_data")


# Type -> badge class mapping for email
TYPE_BADGE = {
    "fgd": ("type-fgd", "FGD"),
    "online": ("type-online", "Online"),
    "taste": ("type-taste", "Taste"),
    "interview": ("type-interview", "Interview"),
    "other": ("type-other", "Other"),
}

TYPE_MAP = {
    "좌담회": "fgd",
    "설문조사": "online",
    "온라인": "online",
    "맛테스트": "taste",
    "인터뷰": "interview",
    "유치조사": "other",
    "패널모집": "other",
    "기타": "other",
}

TYPE_COLOR = {
    "fgd": "#3b82f6",
    "online": "#22c55e",
    "taste": "#f59e0b",
    "interview": "#a855f7",
    "other": "#a0a0a0",
}


def get_today_postings(date_str: str = None) -> list[dict]:
    """DB에서 오늘의 공고 가져오기"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 먼저 JSON에서 시도
    json_path = os.path.join(SCRAPED_DATA_DIR, f"{date_str}.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # DB에서 가져오기
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM postings 
        WHERE date(scraped_at) = ? AND is_active = 1
        ORDER BY scraped_at DESC
    """, (date_str,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def build_website_data(postings: list[dict], date_str: str = None):
    """웹사이트용 data.json 생성"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    output = {
        "date": date_str,
        "generated_at": datetime.now().isoformat(),
        "count": len(postings),
        "postings": postings,
    }

    data_path = os.path.join(WEBSITE_DIR, "data.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[Website] data.json generated: {len(postings)} postings")
    return data_path


def build_email_posting_html(posting: dict) -> str:
    """이메일용 개별 공고 HTML 생성"""
    p_type = TYPE_MAP.get(posting.get("type", ""), "other")
    color = TYPE_COLOR.get(p_type, "#a0a0a0")
    type_label = posting.get("type", "Other")

    meta_parts = []
    if posting.get("location"):
        meta_parts.append(f"&#128205; {posting['location']}")
    if posting.get("reward"):
        meta_parts.append(f"&#128176; {posting['reward']}")
    if posting.get("date"):
        meta_parts.append(f"&#128197; {posting['date']}")
    if posting.get("target_age"):
        meta_parts.append(f"&#128100; {posting['target_age']}")
    if posting.get("target_gender"):
        meta_parts.append(f"&#128101; {posting['target_gender']}")

    meta_html = ""
    if meta_parts:
        meta_items = " &nbsp;&middot;&nbsp; ".join(meta_parts)
        meta_html = f'<p style="font-size: 13px; color: #a0a0a0; margin: 8px 0 0 0;">{meta_items}</p>'

    return f"""
          <tr>
            <td class="posting-item" style="padding: 20px 24px; border-bottom: 1px solid #2a2a2a;">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                <tr>
                  <td>
                    <span class="type-badge" style="display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; background: rgba({_hex_to_rgb(color)}, 0.15); color: {color};">
                      {type_label}
                    </span>
                    <h3 style="font-size: 16px; font-weight: 600; color: #f5f5f5; margin: 8px 0 0 0; line-height: 1.4;">
                      {posting.get('title', '')}
                    </h3>
                    {meta_html}
                    <a href="{posting.get('source_url', '#')}" class="view-link" style="display: inline-block; margin-top: 12px; padding: 6px 14px; background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.2); border-radius: 6px; color: #3b82f6; text-decoration: none; font-size: 13px; font-weight: 500;">
                      View Original &rarr;
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>"""


def _hex_to_rgb(hex_color: str) -> str:
    """#3b82f6 -> 59,130,246"""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


def build_email_html(postings: list[dict], date_str: str = None) -> str:
    """이메일 HTML 전체 생성"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 날짜 표시 형식
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    days_ko = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    date_display = f"{dt.year}.{dt.month:02d}.{dt.day:02d} ({days_ko[dt.weekday()]})"

    # 공고별 HTML 생성
    postings_html = "\n".join([build_email_posting_html(p) for p in postings])

    # 템플릿 로드
    template_path = os.path.join(TEMPLATE_DIR, "email_template.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # 변수 치환
    html = template.replace("{{ title }}", f"MR Newsletter - {date_display}")
    html = html.replace("{{ date_display }}", date_display)
    html = html.replace("{{ posting_count }}", str(len(postings)))
    html = html.replace("{{ postings_html }}", postings_html)
    html = html.replace("{{ site_url }}", "https://yourdomain.com")
    html = html.replace("{{ unsubscribe_url }}", "#unsubscribe")

    return html


def save_email_html(html: str, date_str: str = None) -> str:
    """이메일 HTML 파일 저장"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    os.makedirs(OUTPUT_EMAIL_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_EMAIL_DIR, f"{date_str}.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[Email] HTML saved: {filepath}")
    return filepath


def log_newsletter(date_str: str, total: int, web_path: str, email_path: str):
    """뉴스레터 발행 로그 기록"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO newsletters 
            (publish_date, total_postings, web_html_path, email_html_path)
            VALUES (?, ?, ?, ?)
        """, (date_str, total, web_path, email_path))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB WARN] Newsletter log failed: {e}")


def build_all(date_str: str = None):
    """전체 빌드 실행"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    print("=" * 60)
    print(f"[Newsletter Builder] Building for {date_str}")
    print("=" * 60)

    # 1. 데이터 로드
    postings = get_today_postings(date_str)
    if not postings:
        print("[WARN] No postings found for today!")
        return

    print(f"[Data] {len(postings)} postings loaded")

    # 2. 웹사이트 data.json 생성
    web_path = build_website_data(postings, date_str)

    # 3. 이메일 HTML 생성
    email_html = build_email_html(postings, date_str)
    email_path = save_email_html(email_html, date_str)

    # 4. 로그
    log_newsletter(date_str, len(postings), web_path, email_path)

    print(f"\n[DONE] Newsletter built successfully!")
    print(f"  Website data: {web_path}")
    print(f"  Email HTML:   {email_path}")
    print(f"  (Open the email HTML in browser to preview)")
    print("=" * 60)


if __name__ == "__main__":
    date_arg = None
    if len(sys.argv) > 1 and sys.argv[1] != "--test":
        date_arg = sys.argv[1]
    build_all(date_str=date_arg)
