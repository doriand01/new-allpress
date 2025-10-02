import asyncio
import aiohttp
import requests
import regex
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup as Soup

from allpress.util import logger
from allpress.services.nlp.processors import Article, ArticleBatch

# This module contains classes and tools for scraping news sources for articles, and runs heuristics
# on whether to skip saving articles or to keep scraped pages.


class ArticleDetector:
    def __init__(self, confidence_threshold: float = 0.7):
        self.year_url_regexes = [
            r'\d{4}/\d{2}/\d{2}',
            r'\d{4}-\d{2}-\d{2}',
            r'\d{4}/\d{2}',
            r'\d{4}-\d{2}',
            r'\d{4}'
        ]
        self.confidence_threshold = confidence_threshold

    def detect_article(self, url: str, soup: Soup) -> tuple[bool, float]:
        # Runs several heuristic tests to determine the confidence score of a web page. If the confidence threshold is
        # not reached,  the page is discarded. Increase the confidence threshold for stricter scraping.
        confidence_score = 0.0
        confidence_score += self._check_year_heuristic(url)
        confidence_score += self._check_article_in_url_heuristic(url)
        confidence_score += self._check_has_article_tags(soup)
        confidence_score += self._check_text_density(soup)
        confidence_score += self._check_metadata_tags(soup)
        confidence_score += self._check_headline_structure(soup)
        confidence_score += self._check_blacklist_url(url)
        logger.log(f"Detected {confidence_score:.2f}% of {url}", level="debug")
        return confidence_score >= self.confidence_threshold, confidence_score

    def _check_year_heuristic(self, url): return 0.25 if any(regex.search(p, url) for p in self.year_url_regexes) else 0.0
    def _check_article_in_url_heuristic(self, url): return 0.1 if 'article' in url or 'post' in url else 0.0
    def _check_blacklist_url(self, url): return -0.4 if any(term in url.lower() for term in ['category', 'tag', 'search', 'archive', 'feed', 'page']) else 0.0
    def _check_headline_structure(self, soup): return 0.1 if soup.find('h1') or soup.find('h2') else 0.0

    def _check_metadata_tags(self, soup):
        score = 0.0
        for tag in soup.find_all('meta'):
            if tag.get('property') == 'og:type' and tag.get('content') == 'article':
                score += 0.3
            if tag.get('name') == 'article:published_time':
                score += 0.2
        return score

    def _check_has_article_tags(self, soup):
        score = 0.0
        if soup.find_all('article'):
            score += 0.2
        for tag in soup.find_all(['main', 'section']):
            if tag.get('role') == 'article':
                score += 0.2
            elif tag.get('class') and 'article' in tag.get('class'):
                score += 0.2
        return score

    def _check_text_density(self, soup):
        paragraphs = soup.find_all('p')
        total_text = ' '.join(p.get_text() for p in paragraphs).strip()
        if len(paragraphs) >= 5:
            return 0.2
        if len(total_text.split()) > 300:
            return 0.2
        return 0.0


class Scraper:
    def __init__(self):
        self.starting_url = None
        self.cached_urls = set()
        self.found_urls = set()
        self.scraped_urls = set()
        self.detector = ArticleDetector()

    def on_site(self, url: str) -> bool:
        if not self.starting_url:
            return False
        base_domain = urlparse(self.starting_url).netloc
        target_domain = urlparse(urljoin(self.starting_url, url)).netloc

        # Boolean that checks if a scraped link redirects away from the website. If the base domain of the link
        # does not match the target domain, the function returns false.
        return base_domain == target_domain

    async def _fetch(self, session, url):
        try:
            async with session.get(url, timeout=5) as resp:
                if resp.status != 200 or 'text/html' not in resp.headers.get('Content-Type', ''):
                    return None
                text = await resp.text()
                return {'url': str(resp.url), 'html': text}
        except Exception as e:
            logger.log(f"[FAIL] {url}: {e}",)
            return None

    async def _fetch_all(self, urls: list[str]) -> list[dict]:
        headers = {'Accept-Encoding': 'gzip'}
        async with aiohttp.ClientSession(headers=headers) as session:
            tasks = [self._fetch(session, url) for url in urls]
            return await asyncio.gather(*tasks)

    def scrape(self, domain: str, iterations: int = 2):
        self.starting_url = domain
        loop = asyncio.get_event_loop()

        # Get initial links
        initial_html = requests.get(domain).text
        soup = Soup(initial_html, 'lxml')
        to_scrape = list({
            urljoin(domain, a['href'])
            for a in soup.find_all('a', href=True)
            if self.on_site(a['href'])
        })

        for iteration in range(iterations):
            logger.log(f"[ITER {iteration+1}] Scraping {len(to_scrape)} URLs", level="debug")
            raw_responses = loop.run_until_complete(self._fetch_all(to_scrape))
            articles = []
            new_found_urls = set()

            for res in raw_responses:
                if not res or res['url'] in self.scraped_urls:
                    continue

                soup = Soup(res['html'], 'lxml')
                url = res['url']
                self.scraped_urls.add(url)

                is_article, score = self.detector.detect_article(url, soup)
                if is_article:
                    logger.log(f"[ARTICLE] {url} ({score})", level="debug")
                    self.cached_urls.add(url)
                    articles.append(Article(url, soup))
                else:
                    logger.log(f"[SKIP] {url} ({score})", level="debug")

                links = {
                    urljoin(url, a['href'])
                    for a in soup.find_all('a', href=True)
                    if self.on_site(a['href'])
                }
                new_found_urls.update(links)

            to_scrape = list(new_found_urls - self.scraped_urls)
            logger.log(f"[DONE] Found {len(to_scrape)} new URLs.", level="debug")
            if len(articles) > 0:
                yield ArticleBatch(articles)
