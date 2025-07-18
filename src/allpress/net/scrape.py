import regex
import requests
from urllib.parse import urljoin

from bs4 import BeautifulSoup as Soup

from allpress.util import logger
from allpress.nlp.processors import Article, ArticleBatch
from allpress.net.request_managers import HTTPRequestPoolManager

manager = HTTPRequestPoolManager()


class ArticleDetector:

    def __init__(self, confidence_threshold: float = 0.7):
        self.year_url_regexes = [
            r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{4}/\d{2}',        # YYYY/MM
            r'\d{4}-\d{2}',        # YYYY-MM
            r'\d{4}'               # YYYY
        ]

        self.confidence_threshold = confidence_threshold
        pass

    def detect_article(self, url: str, html_content: Soup) -> tuple[bool, float]:
        self.url = url
        self.soup = html_content

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
        # This method checks of the URL contains various formats of a date.
        # This will be factored into the ArticleDetector's "Confidence Score"
        # to determine if content on the page is an article or not.

        for regex_pattern in self.year_url_regexes:
            if regex.search(regex_pattern, self.url):

                # 0.1 is added to the confidence score when a valid date is found
                # in the URL via one of the regexes.
                return 0.25

        return 0.0

    def _check_article_in_url_heuristic(self) -> float:
        # This method checks if the URL contains the word "article" or "post"
        # in it. If it does, it returns a confidence score of 0.1
        if 'article' in self.url or 'post' in self.url:
            return 0.1
        return 0.0

    def _check_blacklist_url(self) -> float:
        blacklist = ['category', 'tag', 'search', 'archive', 'feed', 'page']
        if any(term in self.url.lower() for term in blacklist):
            return -0.4  # penalize heavily
        return 0.0

    def _check_headline_structure(self) -> float:
        if self.soup.find('h1') or self.soup.find('h2'):
            return 0.1
        return 0.0

    def _check_metadata_tags(self) -> float:
        meta_tags = self.soup.find_all('meta')
        score = 0.0
        for tag in meta_tags:
            if tag.get('property') == 'og:type' and tag.get('content') == 'article':
                score += 0.3
            if tag.get('name') == 'article:published_time':
                score += 0.2
        return score

    def _check_has_article_tags(self) -> float:
        article_tags = self.soup.find_all('article')
        added_confidence = 0.0
        if article_tags:
            # If there are any <article> tags, we assume it's an article
            added_confidence += 0.2

        other_tags = self.soup.find_all(['main', 'section'])

        # Looks for other tags that might indicate an article, and adds this to the confidence score.
        for tag in other_tags:
            if tag.get('role') == 'article':
                added_confidence += 0.2
            elif tag.get('class') and 'article' in tag.get('class'):
                added_confidence += 0.2

        return added_confidence

    def _check_text_density(self) -> float:
        paragraphs = self.soup.find_all('p')
        total_text = ' '.join(p.get_text() for p in paragraphs).strip()

        if len(paragraphs) >= 5:
            return 0.2
        if len(total_text.split()) > 300:
            return 0.2
        return 0.0


class Scraper:

    def __init__(self):
        self.starting_url = None  # The URL the scraper starts from.
        self.cached_urls = set()  # URLs that have been cached from the website.
        self.found_urls = set()   # New URLs found on a web page during scraping.
        self.scraped_urls = set() # URLs that have been scraped and whose content has been downloaded.
        self.detector = ArticleDetector(confidence_threshold=0.7)

    def on_site(self, url: str) -> bool:
        """
        Checks if the given URL is within the starting site domain.
        """
        if not self.starting_url:
            return False
        return self.starting_url in url or url.startswith('/')

    def scrape(self, domain: str, iterations: int = 2):
        """
        Scrapes the given domain for URLs and caches articles found on the site.
        :param domain: The domain to scrape, e.g., 'https://cnn.com'.
        :param iterations: The number of recursive iterations to perform.
        :return:
        """

        iteration = 0
        self.starting_url = domain
        start_page = requests.get(domain)
        parser = Soup(start_page.text, 'html.parser')
        initial_links = {urljoin(domain, a['href']) for a in parser.find_all('a', href=True) if self.on_site(a['href'])}
        to_scrape = list(initial_links)

        while iteration < iterations:
            new_soups = []
            iteration += 1
            logger.info(f'Scraping iteration {iteration}...')

            # Initialize a new set to collect URLs found in this iteration.
            new_found_urls = set()
            responses = manager.execute_request_batch(to_scrape)

            for response in responses:
                if response.url in self.scraped_urls:
                    # Skips the URL if it has already been scraped.
                    continue
                try:
                    if response.status_code != 200:
                        # If the response is not OK, log it and continue to the next URL.
                        logger.warning(f'Failed to retrieve {response.url}: HTTP {response.status_code}')
                        continue
                    if 'text/html' not in response.headers.get('Content-Type', ''):
                        logger.debug(f'Skipping non-HTML content at {response.url}')
                        continue

                    soup = Soup(response.content, 'html.parser')
                    self.scraped_urls.add(response.url)
                    title = soup.title.string if soup.title else 'No Title'
                    article = Article(response.url, soup) ## This is where I was, finish method to serialize article using ArticleBatch objects! #########################
                    new_soups.append(article)

                    # Caches the scraped URL if it's an article.
                    # The confidence threshold of the ArticleDetector can be adjusted.
                    is_article, confidence_score = self.detector.detect_article(response.url, soup)
                    if is_article:
                        logger.debug(f'[ARTICLE] {response.url} ({confidence_score})')
                        self.cached_urls.add(response.url)
                        self.scraped_urls.add(response.url)
                    else:
                        logger.debug(f'[SKIP] {response.url} ({confidence_score})')

                    found_links = {urljoin(response.url, a['href']) for a in soup.find_all('a', href=True) if self.on_site(a['href'])}
                    logger.info(f'Found {len(found_links)} links on {response.url}.')
                    new_found_urls.update(found_links)

                except requests.RequestException as e:
                    logger.error(f'Error fetching {response.url}: {e}')
                    continue

            to_scrape = list(new_found_urls - self.scraped_urls)
            yield ArticleBatch(new_soups)
        logger.info(f'Iteration {iteration} done. Scraping {len(to_scrape)} URLs in Iteration {iteration+1}, scraped {len(self.scraped_urls)} URLs.')



