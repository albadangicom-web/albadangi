"""
MR Newsletter -- Web Scraper
각 소스별 크롤러 클래스 (전략 패턴)
"""
import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import traceback

# 프로젝트 루트
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "newsletter.db")
SCRAPED_DATA_DIR = os.path.join(PROJECT_ROOT, ".tmp", "scraped_data")

# 공통 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


def url_hash(url: str) -> str:
    """URL을 해시하여 고유 ID 생성"""
    return hashlib.md5(url.strip().encode("utf-8")).hexdigest()


def normalize_title(title: str) -> str:
    """공고 제목 정규화 (중복 비교용)"""
    title = re.sub(r"\[.*?\]", "", title)       # [재공지] 등 제거
    title = re.sub(r"\(.*?\)", "", title)       # (소괄호 내용) 제거
    title = re.sub(r"\s+", " ", title).strip()  # 공백 정규화
    return title


# =============================================================================
#  Base Scraper
# =============================================================================
class BaseScraper(ABC):
    """크롤러 기본 클래스"""

    name: str = "base"
    base_url: str = ""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.results = []

    @abstractmethod
    def scrape(self) -> list[dict]:
        """크롤링 실행. 공고 리스트 반환."""
        pass

    def fetch(self, url: str, **kwargs) -> BeautifulSoup | None:
        """URL에서 HTML을 가져와 BeautifulSoup 객체 반환"""
        try:
            resp = self.session.get(url, timeout=15, **kwargs)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            print(f"  [WARN] {self.name}: Failed to fetch {url} -- {e}")
            return None

    def make_posting(self, **kwargs) -> dict:
        """공고 딕셔너리 생성"""
        source_url = kwargs.get("source_url", "")
        return {
            "id": url_hash(source_url),
            "title": kwargs.get("title", "").strip(),
            "source": self.name,
            "source_url": source_url.strip(),
            "target_age": kwargs.get("target_age", ""),
            "target_gender": kwargs.get("target_gender", ""),
            "target_condition": kwargs.get("target_condition", ""),
            "date": kwargs.get("date", ""),
            "time": kwargs.get("time", ""),
            "duration": kwargs.get("duration", ""),
            "reward": kwargs.get("reward", ""),
            "location": kwargs.get("location", ""),
            "type": kwargs.get("type", ""),
            "raw_content": kwargs.get("raw_content", ""),
            "scraped_at": datetime.now().isoformat(),
            "is_active": True,
            "url_hash": url_hash(source_url),
        }


# =============================================================================
#  1. AlbabankScraper  (albabank.pe.kr)
# =============================================================================
class AlbabankScraper(BaseScraper):
    name = "albabank"
    base_url = "https://albabank.pe.kr/category/fgd/"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Scraping {self.base_url}")
        results = []

        # 메인 페이지 + 재공지 페이지
        urls = [
            self.base_url,
            "https://albabank.pe.kr/category/refgd/",
        ]

        for page_url in urls:
            soup = self.fetch(page_url)
            if not soup:
                continue

            articles = soup.select("article") or soup.select(".post")
            if not articles:
                # fallback: h4 태그로 찾기
                for h4 in soup.select("h4"):
                    link = h4.find("a")
                    if not link:
                        continue
                    title = link.get_text(strip=True)
                    href = link.get("href", "")
                    if not href or not title:
                        continue

                    # 상세 페이지에서 내용 가져오기
                    detail = self._parse_detail(href)
                    posting = self.make_posting(
                        title=title,
                        source_url=href,
                        raw_content=detail.get("raw_content", ""),
                        type=self._guess_type(title),
                        **{k: v for k, v in detail.items() if k != "raw_content"},
                    )
                    results.append(posting)
            else:
                for article in articles:
                    # 제목 링크를 h2/h3/h4에서 찾기 (첫 a는 카테고리 링크일 수 있음)
                    title_el = article.find(["h2", "h3", "h4"])
                    if not title_el:
                        continue
                    link = title_el.find("a")
                    if not link:
                        link = article.find("a")
                    if not link:
                        continue
                    title = title_el.get_text(strip=True)
                    href = link.get("href", "")
                    if not href or not title:
                        continue
                    # 카테고리 링크 필터링
                    if "/category/" in href:
                        continue

                    detail = self._parse_detail(href)
                    posting = self.make_posting(
                        title=title,
                        source_url=href,
                        raw_content=detail.get("raw_content", ""),
                        type=self._guess_type(title),
                        **{k: v for k, v in detail.items() if k != "raw_content"},
                    )
                    results.append(posting)

            time.sleep(1)  # 폴라이트 크롤링

        print(f"  [{self.name}] Found {len(results)} postings")
        return results

    def _parse_detail(self, url: str) -> dict:
        """상세 페이지에서 추가 정보 파싱"""
        soup = self.fetch(url)
        if not soup:
            return {}

        content_el = (
            soup.select_one("article.single") or
            soup.select_one(".entry-content") or 
            soup.select_one("article")
        )
        if not content_el:
            return {}

        raw = content_el.get_text(separator="\n", strip=True)
        info = {"raw_content": raw[:2000]}

        # *를 줄바꿈으로 치환하여 각 필드를 분리 (albabank 패턴)
        normalized = raw.replace("*", "\n")

        # 사례비 추출 (정확한 필드명 매칭 우선)
        reward_match = re.search(r"(사례비|참석비|참여비|보상)\s*[:：]\s*(.+)", normalized)
        if reward_match:
            info["reward"] = reward_match.group(2).strip()

        # 소요시간 추출
        duration_match = re.search(r"소요\s*시간\s*[:：]\s*(.+)", normalized)
        if duration_match:
            info["duration"] = duration_match.group(1).strip()

        # 장소 추출
        loc_match = re.search(r"(장소|위치)\s*[:：]\s*(.+)", normalized)
        if loc_match:
            info["location"] = loc_match.group(2).strip()

        # 대상 추출
        target_match = re.search(r"(대상\s*조건|대상|조건)\s*[:：\-]\s*(.+)", normalized)
        if target_match:
            target_text = target_match.group(2).strip()
            info["target_condition"] = target_text
            # 성별
            if "여성" in target_text and "남" not in target_text:
                info["target_gender"] = "여성"
            elif "남성" in target_text and "여" not in target_text:
                info["target_gender"] = "남성"
            elif "남녀" in target_text or "남여" in target_text:
                info["target_gender"] = "남녀"
            # 연령
            age_match = re.search(r"(만?\s*\d+[~\-]\s*\d+세)", target_text)
            if age_match:
                info["target_age"] = age_match.group(1)
            else:
                age_match2 = re.search(r"(\d+세)", target_text)
                if age_match2:
                    info["target_age"] = age_match2.group(1)

        # 일정 추출
        date_match = re.search(r"(일정|날짜|일시|조사\s*기간|조사\s*일자)\s*[:：]\s*(.+)", normalized)
        if date_match:
            info["date"] = date_match.group(2).strip()

        # 시간 추출
        time_match = re.search(r"(시간|진행\s*시간)\s*[:：]\s*(.+)", normalized)
        if time_match and "소요" not in time_match.group(0):
            info["time"] = time_match.group(2).strip()

        time.sleep(0.5)
        return info

    def _guess_type(self, title: str) -> str:
        """제목에서 공고 유형 추측"""
        title_lower = title.lower()
        if "좌담회" in title_lower or "fgd" in title_lower:
            return "좌담회"
        if "맛테스트" in title_lower or "맛 테스트" in title_lower or "갱조사" in title_lower:
            return "맛테스트"
        if "인터뷰" in title_lower:
            return "인터뷰"
        if "설문" in title_lower or "온라인" in title_lower or "다이어리" in title_lower:
            return "온라인"
        if "유치" in title_lower:
            return "유치조사"
        if "패널" in title_lower:
            return "패널모집"
        return "기타"


# =============================================================================
#  2. PanelPowerScraper  (panel.co.kr) -- 엠브레인
# =============================================================================
class PanelPowerScraper(BaseScraper):
    name = "panelpower"
    base_url = "https://www.panel.co.kr"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Scraping {self.base_url}")
        results = []

        # 엠브레인 패널파워는 SPA 방식, API 엔드포인트 직접 호출 시도
        api_urls = [
            f"{self.base_url}/api/user/survey/offline/list",
            f"{self.base_url}/user/api/survey/offline",
        ]

        for api_url in api_urls:
            try:
                resp = self.session.get(api_url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        for item in data:
                            posting = self.make_posting(
                                title=item.get("title", ""),
                                source_url=f"{self.base_url}/user/survey/offline/detail/{item.get('id', '')}",
                                reward=item.get("reward", ""),
                                date=item.get("date", ""),
                                type="좌담회",
                            )
                            results.append(posting)
                    break
            except Exception:
                continue

        if not results:
            print(f"  [{self.name}] API not accessible, trying HTML fallback")
            # 대체 방식: 공지사항 페이지
            soup = self.fetch(f"{self.base_url}/user/main")
            if soup:
                # SPA이므로 자바스크립트 렌더링 필요 → Selenium 필요
                print(f"  [{self.name}] SPA detected - requires Selenium (skipping for now)")

        print(f"  [{self.name}] Found {len(results)} postings")
        return results


# =============================================================================
#  3. SurveylinkScraper  (surveylink.co.kr)
# =============================================================================
class SurveylinkScraper(BaseScraper):
    name = "surveylink"
    base_url = "https://www.surveylink.co.kr"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Scraping {self.base_url}")
        results = []

        # 설문 목록 페이지
        survey_urls = [
            f"{self.base_url}/survey/list",
            f"{self.base_url}/survey/",
        ]

        for survey_url in survey_urls:
            soup = self.fetch(survey_url)
            if not soup:
                continue

            # 설문 목록 파싱
            items = soup.select(".survey-item, .list-item, .board-item, tr")
            for item in items:
                link = item.find("a")
                if not link:
                    continue
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if not href or not title or len(title) < 5:
                    continue

                if not href.startswith("http"):
                    href = self.base_url + href

                posting = self.make_posting(
                    title=title,
                    source_url=href,
                    type="온라인",
                )
                results.append(posting)
            if results:
                break

        print(f"  [{self.name}] Found {len(results)} postings")
        return results


# =============================================================================
#  4. PanelNowScraper  (panelnow.co.kr)
# =============================================================================
class PanelNowScraper(BaseScraper):
    name = "panelnow"
    base_url = "https://www.panelnow.co.kr"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Scraping {self.base_url}")
        results = []

        soup = self.fetch(self.base_url)
        if not soup:
            return results

        # 진행 중인 설문 목록 파싱
        items = soup.select(".survey-list a, .survey-item a, .list-group-item a")
        for item in items:
            title = item.get_text(strip=True)
            href = item.get("href", "")
            if not href or not title or len(title) < 5:
                continue
            if not href.startswith("http"):
                href = self.base_url + href

            posting = self.make_posting(
                title=title,
                source_url=href,
                type="온라인",
            )
            results.append(posting)

        print(f"  [{self.name}] Found {len(results)} postings")
        return results


# =============================================================================
#  5. ResearchiScraper  (researchi.co.kr)
# =============================================================================
class ResearchiScraper(BaseScraper):
    name = "researchi"
    base_url = "https://researchi.co.kr"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Scraping {self.base_url}")
        results = []

        # HTTP로 시도 (TLS 문제 우회)
        for scheme in ["https", "http"]:
            try:
                url = f"{scheme}://researchi.co.kr"
                soup = self.fetch(url, verify=False)
                if not soup:
                    continue

                items = soup.select("article, .post, .board-item, tr")
                for item in items:
                    link = item.find("a")
                    if not link:
                        continue
                    title = link.get_text(strip=True)
                    href = link.get("href", "")
                    if not href or not title or len(title) < 5:
                        continue
                    if not href.startswith("http"):
                        href = url + href

                    posting = self.make_posting(
                        title=title,
                        source_url=href,
                        type=self._guess_type(title),
                    )
                    results.append(posting)
                if results:
                    break
            except Exception as e:
                print(f"  [{self.name}] {scheme} failed: {e}")
                continue

        print(f"  [{self.name}] Found {len(results)} postings")
        return results

    def _guess_type(self, title: str) -> str:
        if "좌담회" in title:
            return "좌담회"
        if "맛테스트" in title or "갱조사" in title:
            return "맛테스트"
        if "인터뷰" in title:
            return "인터뷰"
        return "기타"


# =============================================================================
#  6. NaverCafeScraper  (로그인 필요 → Selenium)
# =============================================================================
class NaverCafeScraper(BaseScraper):
    name = "naver_cafe"
    base_url = "https://cafe.naver.com/togetheralba"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Naver Cafe requires Selenium + login")
        print(f"  [{self.name}] Skipping for now (Phase 2 extension)")
        return []


# =============================================================================
#  7. HankookResearchScraper  (한국리서치 패널 모집)
# =============================================================================
class HankookResearchScraper(BaseScraper):
    name = "hankook_research"
    base_url = "https://www.hrc.co.kr"

    def scrape(self) -> list[dict]:
        print(f"[{self.name}] Scraping {self.base_url}")
        results = []

        # 공지사항/모집 페이지
        urls_to_try = [
            f"{self.base_url}/Notice/List",
            f"{self.base_url}/notice",
            f"{self.base_url}/board",
        ]

        for page_url in urls_to_try:
            soup = self.fetch(page_url)
            if not soup:
                continue

            items = soup.select("tr, .board-item, .list-item, article")
            for item in items:
                link = item.find("a")
                if not link:
                    continue
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if not title or len(title) < 5:
                    continue
                if not href.startswith("http"):
                    href = self.base_url + href

                posting = self.make_posting(
                    title=title,
                    source_url=href,
                    type="기타",
                )
                results.append(posting)
            if results:
                break

        print(f"  [{self.name}] Found {len(results)} postings")
        return results


# =============================================================================
#  DB 저장 · 중복 제거 · 실행
# =============================================================================
def save_to_db(postings: list[dict]) -> tuple[int, int]:
    """크롤링 결과를 DB에 저장. (새로 추가된 건수, 전체 건수) 반환."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_count = 0

    for p in postings:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO postings 
                (id, title, source, source_url, target_age, target_gender,
                 target_condition, date, time, duration, reward, location,
                 type, raw_content, scraped_at, is_active, url_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["id"], p["title"], p["source"], p["source_url"],
                p.get("target_age", ""), p.get("target_gender", ""),
                p.get("target_condition", ""), p.get("date", ""),
                p.get("time", ""), p.get("duration", ""),
                p.get("reward", ""), p.get("location", ""),
                p.get("type", ""), p.get("raw_content", ""),
                p["scraped_at"], 1, p["url_hash"],
            ))
            if cursor.rowcount > 0:
                new_count += 1
        except Exception as e:
            print(f"  [DB ERROR] {p.get('title', '?')}: {e}")

    conn.commit()
    conn.close()
    return new_count, len(postings)


def save_to_json(postings: list[dict], date_str: str = None):
    """크롤링 결과를 JSON 파일로 저장"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(SCRAPED_DATA_DIR, exist_ok=True)
    filepath = os.path.join(SCRAPED_DATA_DIR, f"{date_str}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(postings, f, ensure_ascii=False, indent=2)
    print(f"[JSON] Saved {len(postings)} postings to {filepath}")
    return filepath


def deduplicate_postings(postings: list[dict]) -> list[dict]:
    """제목 유사도 기반 중복 제거 (albabank ↔ fgdalba 등)"""
    seen_titles = {}
    unique = []
    for p in postings:
        norm_title = normalize_title(p["title"])
        if norm_title in seen_titles:
            # 중복 발견: 더 정보가 많은 쪽 유지
            existing = seen_titles[norm_title]
            if len(p.get("raw_content", "")) > len(existing.get("raw_content", "")):
                unique.remove(existing)
                unique.append(p)
                seen_titles[norm_title] = p
        else:
            seen_titles[norm_title] = p
            unique.append(p)
    return unique


def log_scrape(source: str, status: str, new_count: int, total: int, error: str = ""):
    """크롤링 로그 DB에 기록"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scrape_logs (source, finished_at, new_postings, total_scraped, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (source, datetime.now().isoformat(), new_count, total, status, error))
        conn.commit()
        conn.close()
    except Exception:
        pass


# =============================================================================
#  메인 실행
# =============================================================================
ALL_SCRAPERS = [
    AlbabankScraper,
    PanelPowerScraper,
    SurveylinkScraper,
    PanelNowScraper,
    ResearchiScraper,
    HankookResearchScraper,
    NaverCafeScraper,
]


def run_all_scrapers(test_mode: bool = False) -> list[dict]:
    """모든 크롤러 실행"""
    print("=" * 60)
    print(f"[MR Newsletter Scraper] Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    all_postings = []
    for scraper_cls in ALL_SCRAPERS:
        scraper = scraper_cls()
        try:
            postings = scraper.scrape()
            all_postings.extend(postings)
            log_scrape(scraper.name, "success", len(postings), len(postings))
        except Exception as e:
            print(f"  [ERROR] {scraper.name}: {e}")
            traceback.print_exc()
            log_scrape(scraper.name, "failed", 0, 0, str(e))

        if test_mode:
            break  # 테스트 모드에서는 첫 번째 크롤러만

    # 중복 제거
    before = len(all_postings)
    all_postings = deduplicate_postings(all_postings)
    after = len(all_postings)
    if before != after:
        print(f"\n[Dedup] {before} -> {after} postings (removed {before - after} duplicates)")

    # 저장
    if all_postings:
        new_count, total = save_to_db(all_postings)
        save_to_json(all_postings)
        print(f"\n[Result] {new_count} new / {total} total postings saved to DB")
    else:
        print("\n[Result] No postings found")

    print("=" * 60)
    return all_postings


if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    run_all_scrapers(test_mode=test_mode)
