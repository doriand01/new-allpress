import regex
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup as Soup
from concurrent.futures import ThreadPoolExecutor

from allpress.util import logger
from allpress.nlp.processors import Article, ArticleBatch


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
        self.url = url
        self.soup = soup

        confidence_score = 0.0
        confidence_score += self._check_year_heuristic()
        confidence_score += self._check_article_in_url_heuristic()
        confidence_score += self._check_has_article_tags()
        confidence_score += self._check_text_density()
        confidence_score += self._check_metadata_tags()
        confidence_score += self._check_headline_structure()
        confidence_score += self._check_blacklist_url()

        return confidence_score >= self.confidence_threshold, confidence_score

    def _check_year_heuristic(self):
        for regex_pattern in self.year_url_regexes:
            if regex.search(regex_pattern, self.url):
                return 0.25
        return 0.0

    def _check_article_in_url_heuristic(self):
        if 'article' in self.url or 'post' in self.url:
            return 0.1
        return 0.0

    def _check_blacklist_url(self):
        blacklist = ['category', 'tag', 'search', 'archive', 'feed', 'page']
        if any(term in self.url.lower() for term in blacklist):
            return -0.4
        return 0.0

    def _check_headline_structure(self):
        if self.soup.find('h1') or self.soup.find('h2'):
            return 0.1
        return 0.0

    def _check_metadata_tags(self):
        score = 0.0
        for tag in self.soup.find_all('meta'):
            if tag.get('property') == 'og:type' and tag.get('content') == 'article':
                score += 0.3
            if tag.get('name') == 'article:published_time':
                score += 0.2
        return score

    def _check_has_article_tags(self):
        score = 0.0
        if self.soup.find_all('article'):
            score += 0.2
        for tag in self.soup.find_all(['main', 'section']):
            if tag.get('role') == 'article':
                score += 0.2
            elif tag.get('class') and 'article' in tag.get('class'):
                score += 0.2
        return score

    def _check_text_density(self):
        paragraphs = self.soup.find_all('p')
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
        self.detector = ArticleDetector(confidence_threshold=0.7)

    def on_site(self, url: str) -> bool:
        if not self.starting_url:
            return False
        base_domain = urlparse(self.starting_url).netloc
        target_domain = urlparse(urljoin(self.starting_url, url)).netloc
        return base_domain == target_domain

    def _fetch_url(self, url: str):
        try:
            resp = requests.get(url, headers={'Accept-Encoding': 'gzip'}, timeout=10)
            logger.info(f'Response from {url} received. Status code {resp.status_code}')
            return resp
        except Exception as e:
            logger.error(f'Request to {url} failed: {e}')
            return None

    def scrape(self, domain: str, iterations: int = 2):
        iteration = 0
        self.starting_url = domain
        start_page = requests.get(domain)
        parser = Soup(start_page.text, 'html.parser')
        initial_links = {urljoin(domain, a['href']) for a in parser.find_all('a', href=True) if self.on_site(a['href'])}
        to_scrape = list(initial_links)

        while iteration < iterations:
            iteration += 1
            logger.info(f'Scraping iteration {iteration}...')

            with ThreadPoolExecutor(max_workers=64) as executor:
                responses = list(executor.map(self._fetch_url, to_scrape))

            articles = []
            new_found_urls = set()

            for response in responses:
                if not response or response.url in self.scraped_urls or response.status_code != 200:
                    continue

                if 'text/html' not in response.headers.get('Content-Type', ''):
                    continue

                soup = Soup(response.content, 'html.parser')
                self.scraped_urls.add(response.url)

                is_article, confidence_score = self.detector.detect_article(response.url, soup)
                if is_article:
                    logger.debug(f'[ARTICLE] {response.url} ({confidence_score})')
                    self.cached_urls.add(response.url)
                    articles.append(Article(response.url, soup))
                else:
                    logger.debug(f'[SKIP] {response.url} ({confidence_score})')

                found_links = {urljoin(response.url, a['href']) for a in soup.find_all('a', href=True) if self.on_site(a['href'])}
                new_found_urls.update(found_links)

            to_scrape = list(new_found_urls - self.scraped_urls)
            yield ArticleBatch(articles)
            logger.info(f'Iteration {iteration} done. Scraped {len(self.scraped_urls)} URLs.')
