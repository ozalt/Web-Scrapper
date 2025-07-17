import gradio as gr
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urljoin
import pymysql
import time

# ========== CONFIG ==========
BASE_URL = "https://docs.onezeroart.com/"
DB_CONFIG = {
    "host": '127.0.0.1',
    "user": 'root',
    "password": 'admin',
    "database": 'blog_scraper',
    "charset": 'utf8mb4',
    "cursorclass": pymysql.cursors.DictCursor
}

# ========== SCRAPER CLASS ==========
class WebScraper:
    def __init__(self, url):
        self.url = url
        self.title = None
        self.meta_description = None
        self.cleaned_text = None

    def scrape(self):
        # Setup selenium
        options = Options()
        options.headless = True
        driver = webdriver.Chrome(options=options)
        driver.get(self.url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()

        self.title = soup.title.string if soup.title else None
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        self.meta_description = meta_tag['content'] if meta_tag else None

        for aside in soup.find_all('aside'):
            aside.decompose()

        for pre in soup.find_all('pre'):
            for code in pre.find_all('code'):
                lines = []
                for line_span in code.find_all('span', class_='line'):
                    parts = [part.get_text(strip=True) for part in line_span.find_all('span')]
                    lines.append(' '.join(parts))
                pre.replace_with('\n'.join(lines))

        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4']):
            tag.insert_before(NavigableString('\n\n'))

        main = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        self.cleaned_text = self.extract_text(main if main else soup)

    def extract_text(self, tag):
        texts = []
        skip = {'script', 'style', 'head', 'title'}
        just_added_heading = False

        for elem in tag.descendants:
            if elem.name in ['h1', 'h2', 'h3', 'h4']:
                heading = elem.get_text(strip=True)
                if heading:
                    texts.append('\n\n' + heading + ':')
                    just_added_heading = True
            elif elem.name == 'img':
                src = elem.get('src')
                if src:
                    full_src = urljoin(BASE_URL, src)
                    texts.append(f'\n![Image]({full_src})\n')
            elif isinstance(elem, NavigableString):
                parent = elem.parent
                if parent.name in skip or parent.name in ['h1', 'h2', 'h3', 'h4']:
                    continue
                text = elem.strip()
                if not text:
                    continue
                if just_added_heading and text in ['\u200b', '\n', '\r', '', ' ']:
                    continue
                just_added_heading = False
                if parent.name == 'code':
                    texts.append(f'`{text}`')
                else:
                    texts.append(text)
        return '\n'.join(texts)

    def save(self):
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
                cursor.execute(query, (self.url, self.title, self.meta_description, self.cleaned_text, None))
                conn.commit()
                return "✅ Scraped and saved to database!"
        except Exception as e:
            return f"❌ DB Error: {e}"
        finally:
            conn.close()

# ========== GRADIO FUNCTIONS ==========
def start_scrap_gradio(url):
    try:
        scraper = WebScraper(url)
        scraper.scrape()
        result = scraper.save()
        return result
    except Exception as e:
        return f"❌ Scraping failed: {str(e)}"

def get_titles():
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

def display_article(title):
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


# ========== GRADIO UI ==========
def launch_viewer():
    with gr.Blocks(title="Scrap Viewer") as demo:
        gr.Markdown("## 📚 Scraped Article/Documents Viewer")

        with gr.Row():
            url_input = gr.Textbox(label="Enter Web URL to Scrap")
            start_btn = gr.Button("🚀 Start Scrap")

        warning_msg = gr.Markdown()
        scrape_result = gr.Markdown()

        # State to track refresh trigger
        refresh_trigger = gr.State(value=0)

        def show_warning(url):
            return "⏳ Scraping contents, **a browser window will pop up**. DO NOT CLOSE IT. Please wait..."

        def do_scrape(url, current_trigger):
            result = start_scrap_gradio(url)
            # Increment trigger to force refresh
            new_trigger = current_trigger + 1
            return result, new_trigger

        def update_dropdown(trigger):
            # This function will be called whenever refresh_trigger changes
            return gr.Dropdown(choices=get_titles(), label="Select Scraped Document", interactive=True)

        # First click: shows warning
        start_btn.click(fn=show_warning, inputs=url_input, outputs=warning_msg)

        gr.Markdown("---")

        dropdown = gr.Dropdown(choices=get_titles(), label="Select Scraped Document", interactive=True)
        with gr.Row():
            view_btn = gr.Button("🔍 View Scrapped Document")
            refresh_btn = gr.Button("🔄 Refresh List")

        output = gr.Markdown()

        # Chain the scraping and dropdown update
        start_btn.click(
            fn=do_scrape, 
            inputs=[url_input, refresh_trigger], 
            outputs=[scrape_result, refresh_trigger], 
            queue=True
        ).then(
            fn=update_dropdown,
            inputs=refresh_trigger,
            outputs=dropdown
        )

        view_btn.click(fn=display_article, inputs=dropdown, outputs=output)
        
        # Manual refresh
        refresh_btn.click(fn=update_dropdown, inputs=refresh_trigger, outputs=dropdown)

    demo.launch()

# --- RUN --- #
if __name__ == '__main__':
    launch_viewer()