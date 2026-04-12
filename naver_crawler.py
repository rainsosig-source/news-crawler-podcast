# ===== 최우선 로깅 설정 (import 오류도 캐치) =====
import os
import sys
import logging

# 스크립트 위치 기준으로 로그 파일 경로 설정
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LOG_FILE = os.path.join(_SCRIPT_DIR, "crawler_log.txt")

# 기본 로깅 설정 (import 전에 설정)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
_logger = logging.getLogger("startup")
_logger.info("=" * 60)
_logger.info("스크립트 로드 시작")
_logger.info(f"작업 디렉토리: {os.getcwd()}")
_logger.info(f"스크립트 경로: {_SCRIPT_DIR}")

# ===== 모듈 Import (오류 시 로그에 기록) =====
try:
    import requests
    from bs4 import BeautifulSoup
    import urllib.parse
    import time
    import random
    import re
    import signal
    from datetime import datetime, timedelta
    
    from podcast_generator import generate_podcast_script
    from podcast_audio import run_audio_generation
    from sftp_uploader import upload_file
    import db_manager
    _logger.info("모든 모듈 import 성공")
except Exception as e:
    _logger.error(f"모듈 import 실패: {e}")
    import traceback
    _logger.error(traceback.format_exc())
    sys.exit(1)

logger = _logger  # 기존 코드 호환성

# User-Agent 목록 (랜덤 선택으로 차단 방지)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

def get_random_headers():
    """랜덤 User-Agent를 포함한 헤더 반환"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

# Graceful Shutdown 플래그
_shutdown_requested = False

def signal_handler(signum, frame):
    """Ctrl+C 등 시그널 처리"""
    global _shutdown_requested
    print("\n⚠️ 종료 요청 감지. 현재 작업 완료 후 종료합니다...")
    _shutdown_requested = True

def crawl_naver_news(query, keyword_id=None, requirements=None, use_ai=True, make_audio=True, max_articles=3):
    # Encode the query for the URL
    encoded_query = urllib.parse.quote(query)
    
    # Base URL provided by the user
    # Note: query parameter is replaced with the user input
    url = f"https://search.naver.com/search.naver?ssc=tab.news.all&query={encoded_query}&sm=tab_opt&sort=1&nso=so%3Add"
    
    headers = get_random_headers()
    
    # Statistics tracking
    stats = {
        'total': 0,
        'success': 0,
        'duplicate': 0,
        'failed': 0
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Naver News search results list
        news_list_ul = soup.select_one("ul.list_news")
        
        print(f"검색어 '{query}'에 대한 뉴스 검색 결과입니다.\n")
        
        if not news_list_ul:                        
            print("뉴스 기사 리스트를 찾을 수 없습니다.")
            return stats


        # Find headlines with fallback strategies (내구성 향상)
        headline_selectors = [
            lambda c: c and 'sds-comps-text-type-headline1' in c,  # Current selector
            lambda c: c and 'news_tit' in c,  # Legacy selector
            lambda c: c and 'title' in c.lower() and 'news' in c.lower(),  # Generic
        ]
        
        headlines = []
        for selector in headline_selectors:
            headlines = news_list_ul.find_all(class_=selector)
            if headlines:
                print(f"✓ 헤드라인 발견 (셀렉터 전략 사용)")
                break

        if not headlines:
             print("뉴스 기사를 찾을 수 없습니다.")
             return stats

        # Limit to top N articles per keyword to avoid spamming
        for i, headline in enumerate(headlines[:max_articles]):
            stats['total'] += 1
            
            try:
                # Title
                title = headline.get_text(strip=True)
                
                # Link (parent a tag)
                link_el = headline.find_parent("a")
                link = link_el['href'] if link_el else ""
                
                # Check for duplicates
                if link and db_manager.is_duplicate_news(link):
                    print(f"[중복 건너뛰기] {title}")
                    stats['duplicate'] += 1
                    continue
                
                
                # Press (closest preceding press element) with fallback
                press_selectors = [
                    lambda c: c and 'sds-comps-profile-info-title-text' in c,
                    lambda c: c and 'press' in c.lower(),
                    lambda c: c and 'info_group' in c,
                ]
                
                press = "언론사 정보 없음"
                for press_selector in press_selectors:
                    press_el = headline.find_previous(class_=press_selector)
                    if press_el:
                        press = press_el.get_text(strip=True)
                        break

                print(f"언론사: {press}")
                print(f"제목: {title}")
                print(f"링크: {link}")
                
                
                content = ""
                if link:
                    # Rate limiting: Random delay to avoid IP blocking
                    delay = random.uniform(1.0, 3.0)
                    print(f"본문 내용 추출 중... (대기: {delay:.1f}초)")
                    time.sleep(delay)
                    content = get_news_content(link)
                    # print(f"본문:\n{content}") # Too verbose
                
                if use_ai and content and "본문 내용을 추출할 수 없습니다" not in content:
                    print("\n[AI 팟캐스트 대본 생성 중...]")
                    script = generate_podcast_script(title, content, requirements=requirements)
                    print(f"--- 팟캐스트 대본 ---\n{script[:200]}...\n---------------------")
                    
                    if make_audio:
                        print("[오디오 파일 생성 중...]")
                        
                        # Ensure MP3 directory exists
                        if not os.path.exists("MP3"):
                            os.makedirs("MP3")
                            
                        # Create a safe filename
                        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()[:30]
                        filename = os.path.join("MP3", f"podcast_{safe_title}_{i}.mp3")
                        
                        # Pass title to audio generator for announcement
                        audio_result = run_audio_generation(script, filename, title=title)
                        
                        # Check if audio was successfully generated
                        if not audio_result:
                            print("❌ 오디오 생성 실패 - 유효한 대본이 없습니다. 업로드 및 DB 저장 건너뜀.")
                            stats['failed'] += 1
                        else:
                            # ✅ 파일 크기 이중 검증 (안전장치)
                            try:
                                file_size = os.path.getsize(filename)
                                file_size_mb = file_size / (1024 * 1024)
                                
                                if file_size < 1048576:  # 1MB = 1048576 bytes
                                    print(f"❌ 파일 크기 부족: {file_size_mb:.2f}MB (최소 1MB 필요)")
                                    print(f"   업로드 및 DB 등록 건너뜀")
                                    if os.path.exists(filename):
                                        os.remove(filename)
                                        print(f"   로컬 파일 삭제: {filename}")
                                    stats['failed'] += 1
                                    continue
                                
                                print(f"✅ 파일 크기 검증 통과: {file_size_mb:.2f}MB")
                            except Exception as e:
                                print(f"❌ 파일 크기 확인 중 오류: {e}")
                                stats['failed'] += 1
                                continue
                            
                            print("[서버로 업로드 중...]")
                            remote_path = upload_file(filename)
                            
                            if remote_path:
                                print(f"[DB 저장 중...] {title}")
                                db_manager.insert_episode(press, title, link, remote_path, keyword_id=keyword_id)
                                
                                # Clean up local file after successful upload
                                try:
                                    os.remove(filename)
                                    print(f"[로컬 파일 삭제] {filename}")
                                except Exception as e:
                                    print(f"[로컬 파일 삭제 실패] {e}")
                                
                                stats['success'] += 1
                            else:
                                print("[업로드 실패] 로컬 파일 유지")
                                stats['failed'] += 1
                else:
                    print("[본문 추출 실패 또는 AI 처리 건너뛰기]")
                    stats['failed'] += 1

                print("-" * 50)
                
            except Exception as e:
                print(f"[기사 처리 중 오류] {e}")
                stats['failed'] += 1
                print("-" * 50)
                continue  # Move to next article
            
    except requests.exceptions.RequestException as e:
        print(f"에러가 발생했습니다: {e}")
    
    # Print statistics
    print(f"\n📊 크롤링 통계 - 총: {stats['total']}, 성공: {stats['success']}, 중복: {stats['duplicate']}, 실패: {stats['failed']}\n")
    return stats

def validate_content(content):
    """Validate article content quality."""
    if not content or len(content) < 200:
        return False
    
    # Check Korean character ratio
    korean_chars = len([c for c in content if '가' <= c <= '힣'])
    total_chars = len(content.replace('\n', '').replace(' ', ''))
    
    if total_chars == 0:
        return False
    
    if korean_chars / total_chars < 0.3:  # At least 30% Korean
        return False
    
    return True


def clean_article_text(text):
    """Remove reporter info, copyright, and other unwanted patterns from article text."""
    if not text:
        return text
    
    # 기자 이메일 제거
    text = re.sub(r'\w+@\w+\.\w+', '', text)
    
    # 기자 서명 패턴 제거
    reporter_patterns = [
        r'.*?기자\s*=\s*',
        r'.*?특파원\s*=\s*', 
        r'\[.*?기자\]',
        r'기자\s+\w+',
    ]
    for pattern in reporter_patterns:
        text = re.sub(pattern, '', text)
    
    # 저작권/출처 관련 제거
    copyright_patterns = [
        r'Copyright\s*©.*',
        r'저작권자.*',
        r'무단\s*전재.*',
        r'배포\s*금지.*',
        r'ⓒ.*',
    ]
    for pattern in copyright_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # SNS 공유 관련 제거
    text = re.sub(r'(카카오톡|페이스북|트위터|공유하기).*', '', text)
    
    # ===== 네이버 뉴스 특유 불필요 텍스트 제거 =====
    naver_noise_patterns = [
        r'기사 섹션 분류 안내.*?있습니다\.',  # 섹션 분류 안내
        r'이 기사는 언론사에서.*?분류했습니다\.',  # 언론사 분류 안내
        r'섹션으로 분류했습니다',
        r'.*?바로가기\n?',  # 바로가기 링크
        r'기사의 섹션 정보는.*',  # 섹션 정보 안내
        r'언론사는 개별 기사를.*',  # 언론사 안내
        r'\[.*?뉴스\]',  # [OO뉴스] 패턴
        r'【.*?】',  # 【기사】 패턴
        r'▶.*?\n?',  # ▶ 관련기사 등
        r'◆.*?\n?',  # ◆ 관련기사 등
        r'■.*?\n?',  # ■ 관련기사 등
        r'☞.*?\n?',  # ☞ 관련기사 등
        r'▷.*?\n?',  # ▷ 관련기사 등
        r'사진=.*?\n?',  # 사진 출처
        r'\(사진.*?\)',  # (사진 설명)
        r'영상=.*?\n?',  # 영상 출처
    ]
    for pattern in naver_noise_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL)
    
    # 여러 줄바꿈을 2개로 정리
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    return text

def get_news_content(url):
    """
    Extract news article content with multi-layer fallback strategies.
    
    전략 순서:
    1. 네이버 뉴스 전용 셀렉터 (최신 구조 반영)
    2. 주요 언론사별 맞춤 셀렉터
    3. 공통 뉴스 셀렉터
    4. <article> 태그
    5. <p> 태그 휴리스틱
    6. meta description 폴백
    """
    extraction_log = []  # 디버깅용 로그
    
    try:
        headers = get_random_headers()
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        # Detect encoding
        response.encoding = response.apparent_encoding
        final_url = response.url  # 리다이렉트 후 최종 URL
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ===== 불필요 요소 제거 (강화) =====
        for unwanted in soup([
            "script", "style", "header", "footer", "nav", 
            "iframe", "noscript", "aside", "figure", "figcaption"
        ]):
            unwanted.decompose()
        
        # 광고, 배너, 관련기사 제거
        unwanted_patterns = [
            'ad', 'banner', 'sidebar', 'related', 'recommend',
            'comment', 'sns', 'share', 'copyright', 'journalist',
            'byline', 'photo_org', 'sponsor', 'modal', 'popup'
        ]
        for pattern in unwanted_patterns:
            for element in soup.find_all(class_=lambda c: c and pattern in c.lower()):
                element.decompose()
            for element in soup.find_all(id=lambda i: i and pattern in i.lower()):
                element.decompose()
        
        # 관련기사 텍스트 기반 제거
        related_keywords = ['관련기사', '함께 보면', '이전 기사', '다음 기사', '추천 기사', '인기기사', '많이 본']
        for element in soup.find_all(['div', 'section', 'aside', 'ul']):
            if element.get_text():
                text_sample = element.get_text()[:100]
                if any(keyword in text_sample for keyword in related_keywords):
                    element.decompose()
        
        # ===== Strategy 1: 네이버 뉴스 전용 (최신 구조) =====
        if 'naver.com' in final_url:
            naver_selectors = [
                '#dic_area',              # 네이버 뉴스 본문 (최신)
                '#newsct_article',        # 네이버 뉴스 본문 (구버전)
                '#articeBody',            # 네이버 뉴스 본문 (구버전2)
                '#articleBodyContents',   # 네이버 뉴스 본문 (구버전3)
                '.newsct_article',        # 클래스 버전
                '._article_body',         # 모바일 버전
                '#content',               # 일반적 컨텐츠 영역
            ]
            for selector in naver_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator='\n', strip=True)
                    text = clean_article_text(text)
                    if validate_content(text):
                        extraction_log.append(f"✓ 네이버 셀렉터 성공: {selector}")
                        print(f"  [추출] 네이버 뉴스 ({selector})")
                        return text
                    extraction_log.append(f"✗ 네이버 셀렉터 검증 실패: {selector}")
        
        # ===== Strategy 2: 주요 언론사별 맞춤 셀렉터 =====
        press_selectors = {
            # 조선일보
            'chosun.com': ['#article-view-content-div', '.article-body', '#articleBody'],
            # 중앙일보
            'joongang.co.kr': ['#article_body', '.article_body', '#article-content'],
            # 동아일보
            'donga.com': ['#article_body', '.article_body', '.article_txt'],
            # 한겨레
            'hani.co.kr': ['.article-body', '.article-text', '#article-body'],
            # 경향신문
            'khan.co.kr': ['.art_body', '.article_body', '#articleBody'],
            # 한국경제
            'hankyung.com': ['#articletxt', '.article-body', '#article-body-view'],
            # 매일경제
            'mk.co.kr': ['#article_body', '.art_txt', '.article_body'],
            # 연합뉴스
            'yna.co.kr': ['.article-txt', '.story-news', '#articleWrap'],
            # SBS
            'sbs.co.kr': ['.article_cont_area', '.text_area', '#news_content'],
            # KBS
            'kbs.co.kr': ['.detail-body', '.article-body', '#cont_newstext'],
            # MBC
            'mbc.co.kr': ['.news_txt', '.article_body', '.article-body'],
            # JTBC
            'jtbc.co.kr': ['.article_content', '.article-content', '#article-body'],
            # YTN
            'ytn.co.kr': ['.paragraph', '.article-body', '#CmAdContent'],
            # 뉴시스
            'newsis.com': ['.article_body', '.viewer', '#articleBody'],
            # 뉴스1
            'news1.kr': ['.article', '.article_body', '#news-body'],
            # 이데일리
            'edaily.co.kr': ['.news_body', '.article_body', '#articleBody'],
            # 머니투데이
            'mt.co.kr': ['#textBody', '.article-body', '.textBody'],
            # 서울경제
            'sedaily.com': ['#v-article-content', '.article_view', '.article_body'],
            # 오마이뉴스
            'ohmynews.com': ['.article_body', '.at_contents', '#articleBody'],
            # 프레시안
            'pressian.com': ['.article_body', '.article-body', '#news_body'],
        }
        
        for domain, selectors in press_selectors.items():
            if domain in final_url:
                for selector in selectors:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(separator='\n', strip=True)
                        text = clean_article_text(text)
                        if validate_content(text):
                            extraction_log.append(f"✓ 언론사 셀렉터 성공: {domain} - {selector}")
                            print(f"  [추출] {domain} ({selector})")
                            return text
                        extraction_log.append(f"✗ 언론사 셀렉터 검증 실패: {domain} - {selector}")
                break  # 해당 언론사 셀렉터 시도 후 다음 전략으로
        
        # ===== Strategy 3: 공통 뉴스 셀렉터 =====
        common_selectors = [
            'article',
            '[itemprop="articleBody"]',
            '.article-body',
            '.article_body', 
            '.article-content',
            '.article_content',
            '.news-body',
            '.news_body',
            '.post-content',
            '.entry-content',
            '#article-body',
            '#article_body',
            '#articleBody',
            '#content-body',
            '.story-body',
            '.text-body',
        ]
        
        for selector in common_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(separator='\n', strip=True)
                text = clean_article_text(text)
                if validate_content(text):
                    extraction_log.append(f"✓ 공통 셀렉터 성공: {selector}")
                    print(f"  [추출] 공통 셀렉터 ({selector})")
                    return text
                extraction_log.append(f"✗ 공통 셀렉터 검증 실패: {selector}")
        
        # ===== Strategy 4: <p> 태그 휴리스틱 (강화) =====
        paragraphs = soup.find_all('p')
        content = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            # 본문 가능성 높은 문단만 수집 (최소 50자, 문장 형태)
            if len(text) > 50 and ('다.' in text or '요.' in text or '죠.' in text):
                content.append(text)
        
        if content:
            combined = "\n".join(content)
            combined = clean_article_text(combined)
            if validate_content(combined):
                extraction_log.append(f"✓ <p> 태그 휴리스틱 성공 ({len(content)}개 문단)")
                print(f"  [추출] <p> 태그 휴리스틱 ({len(content)}개 문단)")
                return combined
            extraction_log.append(f"✗ <p> 태그 휴리스틱 검증 실패")
        
        # ===== Strategy 5: 가장 긴 텍스트 블록 찾기 (최후 휴리스틱) =====
        all_divs = soup.find_all('div')
        best_text = ""
        best_score = 0
        
        for div in all_divs:
            text = div.get_text(separator='\n', strip=True)
            # 점수 계산: 길이 + 한글 비율 + 마침표 빈도
            if len(text) > 200:
                korean_chars = len([c for c in text if '가' <= c <= '힣'])
                period_count = text.count('.') + text.count('다.')
                score = len(text) * 0.3 + korean_chars * 0.5 + period_count * 10
                
                if score > best_score:
                    best_score = score
                    best_text = text
        
        if best_text:
            best_text = clean_article_text(best_text)
            if validate_content(best_text):
                extraction_log.append(f"✓ 최대 텍스트 블록 성공 (점수: {best_score:.0f})")
                print(f"  [추출] 최대 텍스트 블록 (점수: {best_score:.0f})")
                return best_text
        
        # ===== Strategy 6: Meta Description 폴백 =====
        meta_selectors = [
            ('meta[property="og:description"]', 'content'),
            ('meta[name="description"]', 'content'),
            ('meta[name="twitter:description"]', 'content'),
        ]
        
        for selector, attr in meta_selectors:
            meta = soup.select_one(selector)
            if meta and meta.get(attr):
                meta_content = meta.get(attr).strip()
                if len(meta_content) > 50:
                    extraction_log.append(f"⚠ Meta fallback 사용: {selector}")
                    print(f"  [추출] Meta description 폴백 (본문 추출 실패, 요약만 사용)")
                    return f"[요약] {meta_content}"
        
        # ===== 모든 전략 실패 =====
        extraction_log.append("✗ 모든 전략 실패")
        print(f"  [실패] 모든 추출 전략 실패")
        print(f"  URL: {final_url}")
        if extraction_log:
            print(f"  시도된 전략: {len(extraction_log)}개")
        
        return "본문 내용을 추출할 수 없습니다."

    except requests.exceptions.Timeout:
        print(f"  [오류] 타임아웃: {url}")
        return "본문 추출 중 오류 발생: 요청 시간 초과"
    except requests.exceptions.RequestException as e:
        print(f"  [오류] 요청 실패: {e}")
        return f"본문 추출 중 오류 발생: {e}"
    except Exception as e:
        print(f"  [오류] 예외 발생: {e}")
        return f"본문 추출 중 오류 발생: {e}"


def run_crawling_job():
    keywords = db_manager.get_active_keywords()
    
    if not keywords:
        print("활성화된 검색어가 없습니다. 기본값 '인공지능'으로 실행합니다.")
        crawl_naver_news("인공지능", use_ai=True, make_audio=True)
        return

    for k in keywords:
        print(f"\n>>> 검색어 '{k['keyword']}' (우선순위: {k.get('priority', 0)}) 크롤링 시작...")
        crawl_naver_news(
            query=k['keyword'],
            keyword_id=k['id'],
            requirements=k['requirements'],
            use_ai=True,
            make_audio=True
        )

if __name__ == "__main__":
    import traceback
    
    logger.info("=" * 60)
    logger.info("크롤러 프로세스 시작")
    logger.info(f"작업 디렉토리: {os.getcwd()}")
    logger.info(f"Python 경로: {sys.executable}")
    logger.info(f"스크립트 경로: {os.path.abspath(__file__)}")
    
    # Graceful Shutdown 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    
    # Windows에서는 SIGTERM을 지원하지 않음 - 스케줄러 호환성을 위해 try-except 처리
    try:
        signal.signal(signal.SIGTERM, signal_handler)
    except (OSError, AttributeError):
        pass  # Windows에서는 무시
    
    exit_code = 0
    try:
        # Initialize DB
        logger.info("DB 초기화 중...")
        db_manager.init_db()
        logger.info("DB 초기화 완료")
        
        logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] 크롤러 시작")
        
        # 한 번 실행 후 종료
        run_crawling_job()
        
        logger.info(f"✅ 크롤링 완료! [{datetime.now().strftime('%H:%M:%S')}]")
    except Exception as e:
        logger.error(f"❌ 크롤링 중 치명적 오류 발생: {e}")
        logger.error(f"상세 오류:\n{traceback.format_exc()}")
        exit_code = 1
    finally:
        logger.info(f"프로세스 종료 (exit_code: {exit_code})")
        logger.info("=" * 60)
        # 명시적 종료 코드 반환 (스케줄러 호환성)
        sys.exit(exit_code)

