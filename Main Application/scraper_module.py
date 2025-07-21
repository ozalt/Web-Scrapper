# scraper_module.py

# ==== Imports ====
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urljoin
import pymysql
import time

# ==== Database Configuration ====
DB_CONFIG = {
    "host": '127.0.0.1',
    "user": 'root',
    "password": 'admin',
    "database": 'blog_scraper',
    "charset": 'utf8mb4',
    "cursorclass": pymysql.cursors.DictCursor
}

# ==== Core Scraper Class ====
class ScrapLogic:
    """
    Handles the logic for scraping and cleaning up a webpage.
    """
    def __init__(self, url):
        self.url = url
        self.title = None
        self.meta_description = None
        self.main_html = None

    def scrape(self):
        """
        Launches a headless browser, scrapes the target page,
        and performs aggressive cleanup to extract main content.
        """
        options = Options()
        options.headless = True
        driver = webdriver.Chrome(options=options)
        driver.get(self.url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()

        # Extract title and meta description
        self.title = soup.title.string if soup.title else None
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        self.meta_description = meta_tag['content'] if meta_tag else None

        # Remove irrelevant global tags
        for tag in ['aside', 'nav', 'footer', 'form', 'iframe', 'script', 'svg', 'button', 'select','input', 'label', 'source', 'form', 'audio', 'video']:
            for element in soup.find_all(tag):
                element.decompose()

        # Remove common UI containers in docs websites
        for tag in ['devsite-toc', 'devsite-feedback', 'devsite-nav', 'devsite-footer',
                    'devsite-banner', 'devsite-section-nav', 'devsite-book-nav', 'google-codelab-step',
                    'mdn-sidebar', 'mdn-toc', 'api-index', 'amp-sidebar', 'amp-accordion']:
            for element in soup.find_all(tag):
                element.decompose()

        # Handle header tags conditionally
        for header in soup.find_all('header'):
            parent = header.find_parent(['main', 'article'])
            if parent:
                for child in list(header.contents):
                    if not (getattr(child, 'name', None) in ['h1', 'h2', 'h3', 'h4']):
                        child.extract()
                if not header.find(['h1', 'h2', 'h3', 'h4']):
                    header.decompose()
            else:
                header.decompose()

        # Identify main content area
        main = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup.body

        # Cleanup nested or irrelevant tags
        for tag in main.find_all(['h1', 'h2', 'h3', 'h4', 'h5']):
            for div in tag.find_all('div'):
                div.decompose()

        for picture in main.find_all('picture'):
            img = picture.find('img')
            if img:
                picture.insert_after(img)
            picture.decompose()

        for div in main.find_all('div', attrs={'data-svelte-h': True}):
            div.decompose()

        # Remove divs containing only anchor tags
        for div in main.find_all('div'):
            contents = [child for child in div.contents if not isinstance(child, NavigableString) or child.strip()]
            if contents and all(child.name == 'a' for child in contents if hasattr(child, 'name')):
                div.decompose()

        # Remove by ID, role, aria-label, and class-based navigation/sidebar elements
        for div in main.find_all('div', id=lambda x: x and x.lower() in ['comment', 'comments','sidebar', 'right-sidebar', 'md-sidebar','breadcrumbs','breadcrumb','reviews','feedback']):
            div.decompose()

        for div in main.find_all('div', role=lambda x: x and x.lower() in ['nav', 'navigation', 'sidebar', 'breadcrumb', 'breadcrumbs','header','heading', 'menubar', 'menu']):
            div.decompose()

        for div in main.find_all('div', attrs={'aria-label': lambda x: x and x.lower() in ['nav', 'navbar','navigation', 'sidebar', 'breadcrumb', 'breadcrumbs', 'menubar', 'menu']}):
            div.decompose()

        for div in main.find_all('div', attrs={'class': lambda x: x and x.lower() in ['nav', 'navbar','navigation', 'sidebar', 'breadcrumb', 'breadcrumbs', 'menubar', 'menu']}):
            div.decompose()

        for div in main.find_all('ul', role=lambda x: x and x.lower() in ['nav', 'navigation', 'sidebar', 'breadcrumb', 'breadcrumbs','header','heading','menubar', 'menu']):
            div.decompose()

        for div in main.find_all('ul', attrs={'aria-label': lambda x: x and x.lower() in ['nav', 'navigation', 'sidebar', 'breadcrumb', 'breadcrumbs','menubar', 'menu']}):
            div.decompose()

        # Remove links, especially those containing images
        for a_tag in main.find_all('a'):
            a_tag.unwrap()

        for a_tag in main.find_all('a'):
            if a_tag.find('img'):
                a_tag.decompose()

        # Remove social or irrelevant list items
        for li in main.find_all('li'):
            class_id_values = ' '.join(filter(None, [*li.get('class', []), li.get('id') or ''])).lower()
            if any(social in class_id_values for social in ['instagram', 'facebook', 'twitter', 'whatsapp', 'snapchat']):
                li.decompose()

        for ul in main.find_all('ul', class_='table-of-contents'):
            ul.decompose()

        # Strip wrapping spans for anchors or images
        for span in main.find_all('span'):
            children = [child for child in span.contents if not isinstance(child, NavigableString) or child.strip()]
            if len(children) == 1 and getattr(children[0], 'name', None) in ['img', 'a']:
                span.decompose()

        # Remove inline styles
        for tag in main.find_all(True):
            if 'style' in tag.attrs:
                del tag['style']

        self.main_html = str(main)

    def save(self):
        """
        Saves the scraped data to the MySQL database.
        """
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cursor:
                query = """
                    INSERT INTO blog_articles (url, title, meta_description, cleaned_text, published_date)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        title = VALUES(title),
                        meta_description = VALUES(meta_description),
                        cleaned_text = VALUES(cleaned_text),
                        published_date = VALUES(published_date)
                """
                cursor.execute(query, (self.url, self.title, self.meta_description, self.main_html, None))
                conn.commit()
                return "✅ Scraped and saved to database!"
        except Exception as e:
            return f"❌ DB Error: {e}"
        finally:
            conn.close()

# ==== Helper Interface for Other Modules (e.g. Gradio) ====
class DocScraper:
    """
    Interface methods to trigger scraping, fetch data and display scraped articles from the database.
    """

    @staticmethod
    def start_scrap(url):
        """
        Wrapper to initialize scraper, run it over the url, and save to DB.
        """
        try:
            scraper = ScrapLogic(url)
            scraper.scrape()
            result = scraper.save()
            return result
        except Exception as e:
            return f"❌ Scraping failed: {str(e)}"

    @staticmethod
    def get_titles():
        """
        Fetches all scraped article titles list from the database.
        """
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cursor:
                cursor.execute("SELECT title FROM blog_articles")
                rows = cursor.fetchall()
            return [row['title'] for row in rows]
        except Exception as e:
            return [f"DB Error: {e}"]
        finally:
            conn.close()

    @staticmethod
    def display_article(title):
        """
        Returns HTML content for a specific article title.
        """
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cursor:
                cursor.execute("SELECT cleaned_text FROM blog_articles WHERE title=%s", (title,))
                result = cursor.fetchone()
            return result['cleaned_text'] if result else "Not Found."
        except Exception as e:
            return f"DB Error: {e}"
        finally:
            conn.close()
