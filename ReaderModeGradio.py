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
        self.main_html = None

    def scrape(self):
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

        for tag in ['aside', 'nav', 'footer', 'header', 'form', 'iframe', 'script', 'svg']:
            for element in soup.find_all(tag):
                element.decompose()

        main = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup.body

        for tag in main.find_all(True):
            if 'style' in tag.attrs:
                del tag['style']

        self.main_html = str(main)

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
                cursor.execute(query, (self.url, self.title, self.meta_description, self.main_html, None))
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

        refresh_trigger = gr.State(value=0)

        def show_warning(url):
            return "⏳ Scraping contents, **a browser window will pop up**. DO NOT CLOSE IT. Please wait..."

        def do_scrape(url, current_trigger):
            result = start_scrap_gradio(url)
            new_trigger = current_trigger + 1
            return result, new_trigger

        def update_dropdown(trigger):
            return gr.Dropdown(choices=get_titles(), label="Select Scraped Document", interactive=True)

        start_btn.click(fn=show_warning, inputs=url_input, outputs=warning_msg)

        gr.Markdown("---")

        dropdown = gr.Dropdown(choices=get_titles(), label="Select Scraped Document", interactive=True)
        with gr.Row():
            view_btn = gr.Button("🔍 View Scrapped Document")
            refresh_btn = gr.Button("🔄 Refresh List")

        output = gr.HTML()

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

        refresh_btn.click(fn=update_dropdown, inputs=refresh_trigger, outputs=dropdown)

    demo.launch()

if __name__ == '__main__':
    launch_viewer()
