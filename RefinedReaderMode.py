import gradio as gr
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urljoin, urlparse
import pymysql
import time
import re
from collections import Counter
import requests
from datetime import datetime
import os
import html

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

# ========== ENHANCED SCRAPER CLASS ==========
class SafariReaderScraper:
    def __init__(self, url):
        self.url = url
        self.title = None
        self.meta_description = None
        self.author = None
        self.published_date = None
        self.main_html = None
        self.word_count = 0
        self.reading_time = 0
        
    def _setup_driver(self):
        """Setup Chrome driver with optimal settings for scraping"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-images')
        options.add_argument('--disable-javascript')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        return webdriver.Chrome(options=options)
    
    def _extract_metadata(self, soup):
        """Extract comprehensive metadata from the page"""
        # Title extraction with fallbacks
        self.title = None
        title_selectors = [
            'h1',
            'title',
            '[property="og:title"]',
            '.entry-title',
            '.post-title',
            '.article-title'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                self.title = element.get_text(strip=True) if element.name != 'title' else element.string
                if self.title:
                    break
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or \
                   soup.find('meta', attrs={'property': 'og:description'})
        self.meta_description = meta_desc.get('content') if meta_desc else None
        
        # Author extraction
        author_selectors = [
            '[name="author"]',
            '[property="article:author"]',
            '[rel="author"]',
            '.author',
            '.byline',
            '.post-author'
        ]
        
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                self.author = element.get('content') or element.get_text(strip=True)
                if self.author:
                    break
        
        # Published date extraction
        date_selectors = [
            '[property="article:published_time"]',
            '[name="date"]',
            'time[datetime]',
            '.published',
            '.date',
            '.post-date'
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                date_str = element.get('datetime') or element.get('content') or element.get_text(strip=True)
                if date_str:
                    self.published_date = self._parse_date(date_str)
                    break
    
    def _parse_date(self, date_str):
        """Parse various date formats"""
        try:
            # Try common ISO formats first
            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%SZ']:
                try:
                    return datetime.strptime(date_str[:19], fmt)
                except ValueError:
                    continue
            return None
        except:
            return None
    

    
    def _calculate_text_density(self, element):
        """Calculate text density to identify content-rich areas"""
        if not element:
            return 0
        
        text_length = len(element.get_text(strip=True))
        html_length = len(str(element))
        
        return text_length / html_length if html_length > 0 else 0
    
    def _calculate_content_score(self, element):
        """Score elements based on content indicators"""
        if not element:
            return 0
        
        score = 0
        text = element.get_text(strip=True)
        
        # Basic text length score
        score += len(text) / 100
        
        # Paragraph count
        paragraphs = element.find_all('p')
        score += len(paragraphs) * 2
        
        # Positive indicators
        positive_classes = ['content', 'article', 'post', 'entry', 'main']
        for class_name in element.get('class', []):
            if any(pos in class_name.lower() for pos in positive_classes):
                score += 10
        
        # Negative indicators
        negative_classes = ['sidebar', 'footer', 'header', 'nav', 'ads', 'social']
        for class_name in element.get('class', []):
            if any(neg in class_name.lower() for neg in negative_classes):
                score -= 20
        
        return score
    
    def _clean_content(self, content):
        """Clean and optimize content for reader mode"""
        if not content:
            return None
        
        # Remove unwanted attributes but keep essential ones
        allowed_attrs = {
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'title', 'width', 'height'],
            'blockquote': ['cite'],
            'q': ['cite'],
            'abbr': ['title'],
            'acronym': ['title'],
            'time': ['datetime'],
            'code': ['class'],
            'pre': ['class']
        }
        
        for tag in content.find_all(True):
            # Remove all attributes except allowed ones
            if tag.name in allowed_attrs:
                attrs_to_keep = allowed_attrs[tag.name]
                new_attrs = {}
                for attr in attrs_to_keep:
                    if attr in tag.attrs:
                        new_attrs[attr] = tag.attrs[attr]
                tag.attrs = new_attrs
            else:
                tag.attrs = {}
        
        # Remove empty elements
        for tag in content.find_all():
            if not tag.get_text(strip=True) and tag.name not in ['img', 'br', 'hr']:
                tag.decompose()
        
        # Convert relative URLs to absolute
        base_url = self.url
        for tag in content.find_all(['a', 'img']):
            attr = 'href' if tag.name == 'a' else 'src'
            if tag.get(attr):
                tag[attr] = urljoin(base_url, tag[attr])
        
        # Enhance typography
        self._enhance_typography(content)
        
        return content
    
    def _enhance_typography(self, content):
        """Enhance typography for better readability"""
        if not content:
            return content
            
        # First, let's check if we actually have meaningful content
        text_content = content.get_text(strip=True)
        if len(text_content) < 100:  # If less than 100 characters, likely not real content
            return content
            
        # Add reader-friendly CSS classes
        reader_styles = """
        <style>
        .reader-content {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 18px;
            line-height: 1.6;
            max-width: 680px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }
        .reader-content h1, .reader-content h2, .reader-content h3 {
            font-weight: 600;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            color: #222;
        }
        .reader-content h1 { font-size: 2em; }
        .reader-content h2 { font-size: 1.5em; }
        .reader-content h3 { font-size: 1.25em; }
        .reader-content p {
            margin-bottom: 1.2em;
            text-align: justify;
        }
        .reader-content img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1.5em auto;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .reader-content blockquote {
            border-left: 4px solid #007AFF;
            padding-left: 1em;
            margin: 1.5em 0;
            font-style: italic;
            color: #666;
        }
        .reader-content code {
            background: #f5f5f5;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: 'SF Mono', Monaco, monospace;
        }
        .reader-content pre {
            background: #f5f5f5;
            padding: 1em;
            border-radius: 8px;
            overflow-x: auto;
            margin: 1.5em 0;
        }
        .reader-content a {
            color: #007AFF;
            text-decoration: none;
        }
        .reader-content a:hover {
            text-decoration: underline;
        }
        .reader-metadata {
            border-bottom: 1px solid #eee;
            padding-bottom: 1em;
            margin-bottom: 2em;
            color: #666;
        }
        .reader-title {
            font-size: 2.5em;
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: 0.5em;
            color: #222;
        }
        .reader-stats {
            font-size: 0.9em;
            color: #888;
            margin-top: 1em;
        }
        </style>
        """
        
        # Create a new soup for the wrapper
        wrapper = BeautifulSoup(reader_styles, 'html.parser')
        content_div = wrapper.new_tag('div', class_='reader-content')
        
        # Add metadata header if we have title/author/date
        if self.title or self.author or self.published_date:
            metadata_div = wrapper.new_tag('div', class_='reader-metadata')
            
            if self.title:
                title_tag = wrapper.new_tag('h1', class_='reader-title')
                title_tag.string = self.title
                metadata_div.append(title_tag)
            
            if self.author or self.published_date:
                byline_parts = []
                if self.author:
                    byline_parts.append(f"By {self.author}")
                if self.published_date:
                    byline_parts.append(self.published_date.strftime("%B %d, %Y"))
                
                if byline_parts:
                    byline = wrapper.new_tag('div')
                    byline.string = " • ".join(byline_parts)
                    metadata_div.append(byline)
            
            content_div.append(metadata_div)
        
        # Clone the content elements to avoid modifying the original
        for element in content.contents:
            if element.name:  # Only copy tag elements, not text nodes
                content_div.append(element.extract())
        
        # Add reading stats if we have meaningful content
        if self.word_count > 0:
            stats_div = wrapper.new_tag('div', class_='reader-stats')
            stats_div.string = f"{self.word_count} words • {self.reading_time} min read"
            content_div.append(stats_div)
        
        # Return the enhanced content
        return wrapper
    
    def _calculate_reading_stats(self, content):
        """Calculate word count and reading time from actual content"""
        if not content:
            self.word_count = 0
            self.reading_time = 0
            return
        
        # Extract text content, excluding style tags and scripts
        text_content = ""
        for element in content.find_all(text=True):
            if element.parent.name not in ['style', 'script', 'meta', 'title']:
                text_content += element.get_text() + " "
        
        # Clean and count words
        text_content = re.sub(r'\s+', ' ', text_content.strip())
        words = len(text_content.split()) if text_content else 0
        
        self.word_count = words
        self.reading_time = max(1, round(words / 200)) if words > 0 else 0
    
    def scrape(self):
        """Main scraping method with enhanced reader mode processing"""
        try:
            driver = self._setup_driver()
            driver.get(self.url)
            time.sleep(5)  # Increase wait time for content to load
            
            # Try to scroll to load dynamic content
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            driver.quit()
            
            # Extract metadata first
            self._extract_metadata(soup)
            
            # Find and extract main content
            main_content = self._find_main_content(soup)
            
            # Debug: Check if we found meaningful content
            if main_content:
                text_preview = main_content.get_text(strip=True)[:200]
                print(f"Content preview: {text_preview}")
                print(f"Content length: {len(text_preview)}")
            
            # Calculate reading statistics BEFORE cleaning
            self._calculate_reading_stats(main_content)
            
            # Clean and enhance content only if we have meaningful content
            if main_content and len(main_content.get_text(strip=True)) > 100:
                cleaned_content = self._clean_content(main_content)
                enhanced_content = self._enhance_typography(cleaned_content)
                self.main_html = str(enhanced_content) if enhanced_content else None
            else:
                # If no meaningful content found, try alternative approach
                self.main_html = self._fallback_content_extraction(soup)
                
        except Exception as e:
            raise Exception(f"Scraping failed: {str(e)}")
    
    def _fallback_content_extraction(self, soup):
        """Fallback method for content extraction"""
        # Try to find content in common selectors
        fallback_selectors = [
            'div[class*="content"]',
            'div[class*="article"]',
            'div[class*="post"]',
            'div[class*="body"]',
            'div[class*="text"]',
            'section',
            'main p',
            'article p',
            'body p'
        ]
        
        best_content = None
        best_score = 0
        
        for selector in fallback_selectors:
            elements = soup.select(selector)
            for element in elements:
                text_length = len(element.get_text(strip=True))
                if text_length > best_score:
                    best_score = text_length
                    best_content = element
        
        if best_content and best_score > 100:
            # Recalculate stats for fallback content
            self._calculate_reading_stats(best_content)
            cleaned = self._clean_content(best_content)
            enhanced = self._enhance_typography(cleaned)
            return str(enhanced)
        
        return "<p>Could not extract meaningful content from this page.</p>"
    
    def save(self):
        """Save to database with enhanced metadata"""
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cursor:
                # Update table structure if needed (you might need to add these columns)
                query = """
                    INSERT INTO blog_articles (
                        url, title, meta_description, cleaned_text, 
                        published_date, author, word_count, reading_time
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        title = VALUES(title),
                        meta_description = VALUES(meta_description),
                        cleaned_text = VALUES(cleaned_text),
                        published_date = VALUES(published_date),
                        author = VALUES(author),
                        word_count = VALUES(word_count),
                        reading_time = VALUES(reading_time)
                """
                cursor.execute(query, (
                    self.url, self.title, self.meta_description, self.main_html,
                    self.published_date, self.author, self.word_count, self.reading_time
                ))
                conn.commit()
                return f"✅ Scraped and saved! ({self.word_count} words, {self.reading_time} min read)"
        except Exception as e:
            return f"❌ DB Error: {e}"
        finally:
            conn.close()

# ========== GRADIO FUNCTIONS ==========
def start_scrap_gradio(url):
    try:
        scraper = SafariReaderScraper(url)
        scraper.scrape()
        result = scraper.save()
        return result
    except Exception as e:
        return f"❌ Scraping failed: {str(e)}"

def get_titles():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("SELECT title, word_count, reading_time FROM blog_articles ORDER BY id DESC")
            rows = cursor.fetchall()
        return [f"{row['title']} ({row['word_count']} words, {row['reading_time']} min)" for row in rows]
    except Exception as e:
        return [f"DB Error: {e}"]
    finally:
        conn.close()

def display_article(title_with_stats):
    try:
        # Extract just the title (remove stats)
        title = title_with_stats.split(' (')[0] if ' (' in title_with_stats else title_with_stats
        
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("SELECT cleaned_text FROM blog_articles WHERE title=%s", (title,))
            result = cursor.fetchone()
        return result['cleaned_text'] if result else "Not Found."
    except Exception as e:
        return f"DB Error: {e}"
    finally:
        conn.close()

def save_article_as_html(title_with_stats):
    try:
        if not title_with_stats:
            return "❌ Please select an article first."
        
        # Extract just the title (remove stats)
        title = title_with_stats.split(' (')[0] if ' (' in title_with_stats else title_with_stats
        
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT title, cleaned_text, url, author, published_date, 
                       word_count, reading_time, meta_description
                FROM blog_articles WHERE title=%s
            """, (title,))
            result = cursor.fetchone()
        
        if not result:
            return "❌ Article not found in database."
        
        # Create HTML template
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(result['title'] or 'Untitled Article')}</title>
    <meta name="description" content="{html.escape(result['meta_description'] or '')}">
    <meta name="author" content="{html.escape(result['author'] or '')}">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            background-color: #fff;
        }}
        
        .article-header {{
            border-bottom: 1px solid #eee;
            padding-bottom: 2rem;
            margin-bottom: 3rem;
        }}
        
        .article-title {{
            font-size: 2.5rem;
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: 1rem;
            color: #222;
        }}
        
        .article-meta {{
            color: #666;
            font-size: 1rem;
            margin-bottom: 1rem;
        }}
        
        .article-stats {{
            color: #888;
            font-size: 0.9rem;
            font-style: italic;
        }}
        
        .article-content {{
            font-size: 1.1rem;
            line-height: 1.8;
        }}
        
        .article-content h1, .article-content h2, .article-content h3,
        .article-content h4, .article-content h5, .article-content h6 {{
            font-weight: 600;
            margin-top: 2rem;
            margin-bottom: 1rem;
            color: #222;
        }}
        
        .article-content h1 {{ font-size: 2rem; }}
        .article-content h2 {{ font-size: 1.5rem; }}
        .article-content h3 {{ font-size: 1.25rem; }}
        .article-content h4 {{ font-size: 1.1rem; }}
        
        .article-content p {{
            margin-bottom: 1.5rem;
            text-align: justify;
        }}
        
        .article-content img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 2rem auto;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        
        .article-content blockquote {{
            border-left: 4px solid #007AFF;
            padding-left: 1.5rem;
            margin: 2rem 0;
            font-style: italic;
            color: #666;
            background-color: #f8f9fa;
            padding: 1rem 1.5rem;
            border-radius: 0 8px 8px 0;
        }}
        
        .article-content code {{
            background-color: #f1f3f4;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', monospace;
            font-size: 0.9em;
        }}
        
        .article-content pre {{
            background-color: #f8f9fa;
            padding: 1.5rem;
            border-radius: 8px;
            overflow-x: auto;
            margin: 2rem 0;
            border: 1px solid #e9ecef;
        }}
        
        .article-content pre code {{
            background-color: transparent;
            padding: 0;
        }}
        
        .article-content a {{
            color: #007AFF;
            text-decoration: none;
        }}
        
        .article-content a:hover {{
            text-decoration: underline;
        }}
        
        .article-content ul, .article-content ol {{
            margin: 1.5rem 0;
            padding-left: 2rem;
        }}
        
        .article-content li {{
            margin-bottom: 0.5rem;
        }}
        
        .article-content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 2rem 0;
        }}
        
        .article-content th, .article-content td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        
        .article-content th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        
        .article-footer {{
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 0.9rem;
        }}
        
        .original-url {{
            word-break: break-all;
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 20px 15px;
            }}
            
            .article-title {{
                font-size: 2rem;
            }}
            
            .article-content {{
                font-size: 1rem;
            }}
        }}
        
        @media print {{
            body {{
                max-width: none;
                padding: 0;
            }}
            
            .article-footer {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <article>
        <header class="article-header">
            <h1 class="article-title">{html.escape(result['title'] or 'Untitled Article')}</h1>
            
            <div class="article-meta">
                {f"By {html.escape(result['author'])}" if result['author'] else ""}
                {f" • {result['published_date'].strftime('%B %d, %Y')}" if result['published_date'] else ""}
            </div>
            
            <div class="article-stats">
                {f"{result['word_count']} words" if result['word_count'] else ""}
                {f" • {result['reading_time']} min read" if result['reading_time'] else ""}
            </div>
        </header>
        
        <main class="article-content">
            {result['cleaned_text'] or ''}
        </main>
        
        <footer class="article-footer">
            <p><strong>Original URL:</strong> <a href="{html.escape(result['url'])}" class="original-url">{html.escape(result['url'])}</a></p>
            <p><em>Saved on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</em></p>
        </footer>
    </article>
</body>
</html>"""
        
        # Create filename from title
        safe_title = re.sub(r'[^a-zA-Z0-9\s\-_]', '', title)
        safe_title = re.sub(r'\s+', '_', safe_title).strip('_')
        filename = f"{safe_title[:50]}.html"  # Limit filename length
        
        # Create downloads directory if it doesn't exist
        downloads_dir = "downloads"
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir)
        
        file_path = os.path.join(downloads_dir, filename)
        
        # Write HTML file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_template)
        
        return f"✅ Article saved as: {file_path}"
        
    except Exception as e:
        return f"❌ Error saving HTML: {str(e)}"
    finally:
        conn.close()

# ========== GRADIO UI ==========
def launch_viewer():
    with gr.Blocks(title="Safari Reader Mode Scraper") as demo:
        gr.Markdown("## 📖 Safari-Style Reader Mode Scraper")
        gr.Markdown("Extract clean, readable content from any web page with enhanced typography and metadata.")

        with gr.Row():
            url_input = gr.Textbox(
                label="Enter Web URL to Scrape", 
                placeholder="https://example.com/article"
            )
            start_btn = gr.Button("🚀 Start Scraping", variant="primary")

        warning_msg = gr.Markdown()
        scrape_result = gr.Markdown()

        refresh_trigger = gr.State(value=0)

        def show_warning(url):
            return "⏳ Extracting content in reader mode... Please wait while we process the page."

        def do_scrape(url, current_trigger):
            result = start_scrap_gradio(url)
            new_trigger = current_trigger + 1
            return result, new_trigger

        def update_dropdown(trigger):
            return gr.Dropdown(
                choices=get_titles(), 
                label="Select Scraped Article", 
                interactive=True
            )

        start_btn.click(fn=show_warning, inputs=url_input, outputs=warning_msg)

        gr.Markdown("---")

        dropdown = gr.Dropdown(
            choices=get_titles(), 
            label="Select Scraped Article", 
            interactive=True
        )
        
        with gr.Row():
            view_btn = gr.Button("📖 View Article", variant="secondary")
            save_html_btn = gr.Button("💾 Save as HTML", variant="secondary")
            refresh_btn = gr.Button("🔄 Refresh List")

        output = gr.HTML(label="Article Content")
        save_status = gr.Markdown()

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
        save_html_btn.click(fn=save_article_as_html, inputs=dropdown, outputs=save_status)
        refresh_btn.click(fn=update_dropdown, inputs=refresh_trigger, outputs=dropdown)

    demo.launch()

if __name__ == '__main__':
    launch_viewer()