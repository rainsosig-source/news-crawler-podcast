import requests
from bs4 import BeautifulSoup
import urllib.parse
import os
import time
import random

def crawl_naver_news(query, keyword_id=None, requirements=None, use_ai=True, make_audio=True, max_articles=3):
    # Encode the query for the URL
    encoded_query = urllib.parse.quote(query)
    
    # Base URL provided by the user
    # Note: query parameter is replaced with the user input
    url = f"https://search.naver.com/search.naver?ssc=tab.news.all&query={encoded_query}&sm=tab_opt&sort=1&nso=so%3Add"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    
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
                
                # Link - 네이버 뉴스 링크 우선 사용 (본문 추출 성공률 향상)
                link = ""
                original_link = ""
                
                # 1. 먼저 원본 링크 저장
                link_el = headline.find_parent("a")
                if link_el:
                    original_link = link_el['href']
                
                # 2. 상위 li.bx 컨테이너에서 네이버 뉴스 링크 탐색
                news_item = headline.find_parent("li")
                if news_item:
                    # news.naver.com 링크 찾기
                    naver_news_link = news_item.find("a", href=lambda h: h and "news.naver.com" in h)
                    if naver_news_link:
                        link = naver_news_link['href']
                        print(f"✅ 네이버뉴스 링크 발견")
                
                # 3. 네이버 뉴스 링크가 없으면 원본 사용
                if not link:
                    link = original_link
                    if link:
                        print(f"⚠️ 원본 링크 사용 (네이버뉴스 없음)")
                
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

import re

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
    
    # 여러 줄바꿈을 2개로 정리
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 앞뒤 공백 제거
    text = text.strip()
    
    return text

def get_news_content(url):
    """Extract news article content with improved strategies."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Detect encoding
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements (enhanced)
        for unwanted in soup([
            "script", "style", "header", "footer", "nav", 
            "iframe", "noscript", "aside"  # Added aside for sidebars
        ]):
            unwanted.decompose()
        
        # Remove ads and banners
        for ad in soup.find_all(class_=lambda c: c and ('ad' in c.lower() or 'banner' in c.lower())):
            ad.decompose()
        
        # Remove Naver news specific unwanted elements
        naver_unwanted_classes = [
            'end_photo_org',  # 사진 저작권
            'journalist',  # 기자 정보
            'byline',  # 출처
            'copyright',  # 저작권
            'article_sponsor',  # 광고
            'relation_lst',  # 관련기사
            'categorize',  # 카테고리
        ]
        
        for class_name in naver_unwanted_classes:
            for element in soup.find_all(class_=lambda c: c and class_name in c.lower()):
                element.decompose()
        
        # Remove related articles sections
        related_keywords = ['관련기사', '함께 보면', '이전 기사', '다음 기사', '추천 기사', '인기기사']
        for element in soup.find_all(['div', 'section', 'aside']):
            if element.get_text():
                text_sample = element.get_text()[:50]
                if any(keyword in text_sample for keyword in related_keywords):
                    element.decompose()
        
        content = []
        
        # Strategy 1: Try to find article tag first (common in modern news sites)
        article = soup.find('article')
        if article:
            text = article.get_text(separator='\n', strip=True)
            text = clean_article_text(text)
            if validate_content(text):
                return text
        
        # Strategy 2: Try common news content classes/ids
        content_selectors = [
            {'id': 'articleBodyContents'},  # Naver news
            {'id': 'articeBody'},
            {'class_': 'article_body'},
            {'class_': 'article-body'},
            {'id': 'newsct_article'},
        ]
        
        for selector in content_selectors:
            element = soup.find('div', selector)
            if element:
                text = element.get_text(separator='\n', strip=True)
                text = clean_article_text(text)
                if validate_content(text):
                    return text
            
        # Strategy 3: Extract all p tags (fallback)
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 30:  # Filter out short texts (menus, copyrights, etc.)
                content.append(text)
        
        if content:
            combined = "\n".join(content)
            combined = clean_article_text(combined)
            if validate_content(combined):
                return combined
            
        return "본문 내용을 추출할 수 없습니다."

    except Exception as e:
        return f"본문 추출 중 오류 발생: {e}"

from datetime import datetime, timedelta 

from podcast_generator import generate_podcast_script
from podcast_audio import run_audio_generation
from sftp_uploader import upload_file
import db_manager

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
    # Initialize DB
    db_manager.init_db()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 크롤러 시작.")
    
    # Run once and exit (Windows Task Scheduler will re-run every hour)
    run_crawling_job()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 크롤링 완료.")

