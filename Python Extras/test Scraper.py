from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup, NavigableString
import time
import pymysql
from urllib.parse import urljoin
import os

class SafariReaderScraper:
    def __init__(self, url, base_url=None):
        self.url = url
        self.base_url = base_url or url

    def _get_html(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--ignore-certificate-errors")  # Prevent SSL errors

        driver = webdriver.Chrome(options=chrome_options)
        driver.get(self.url)

        # Simulate scroll
        for i in range(3):
            scroll_pos = (i + 1) / 3
            driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight*{scroll_pos});")
            time.sleep(1)

        html = driver.page_source
        driver.quit()
        return html

    def _clean_html(self, soup):
        # Remove unwanted tags
        for tag in soup(['aside', 'nav', 'footer', 'header', 'script', 'style']):
            tag.decompose()
        return soup

    def _process_content(self, soup):
        article = soup.body or soup
        main_content = []

        for element in article.descendants:
            if isinstance(element, NavigableString):
                text = element.strip()
                if text:
                    main_content.append(text)
            elif element.name == 'img':
                src = element.get('src')
                if src:
                    absolute_src = urljoin(self.base_url, src)
                    element['src'] = absolute_src
                    main_content.append(str(element))
            elif element.name in ['p', 'pre', 'code', 'strong', 'em', 'a']:
                main_content.append(str(element))

        return '\n'.join(main_content)

    def _save_html_file(self, html_content, filename='scraped_content.html'):
        path = os.path.join(os.getcwd(), filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"[✓] HTML content saved to {path}")


    def scrape(self):
        raw_html = self._get_html()
        soup = BeautifulSoup(raw_html, 'html.parser')
        soup = self._clean_html(soup)

        title_tag = soup.find('title')
        title = title_tag.get_text() if title_tag else 'No Title'

        processed_html = self._process_content(soup)

        # Save to HTML file
        self._save_html_file(processed_html)

        print("[✓] Scraping completed.")

# Example usage
scraper = SafariReaderScraper("https://docs.onezeroart.com/", base_url="https://docs.onezeroart.com/")
scraper.scrape()
