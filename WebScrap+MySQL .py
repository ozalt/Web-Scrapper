from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup, NavigableString
import time
import pymysql
from pymysql import Error
from urllib.parse import urljoin

base_url = "https://docs.onezeroart.com/"
# Database configuration
HOST = '127.0.0.1'
USER = 'root'
PASSWORD = 'admin'
DATABASE = 'blog_scraper'

def save_to_database(url, title, meta_description, cleaned_text, published_date=None):
    connection = None
    try:
        connection = pymysql.connect(
            host=HOST,
            user=USER,
            password=PASSWORD,
            database=DATABASE,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            query = """
            INSERT INTO blog_articles (url, title, meta_description, cleaned_text, published_date)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                title = VALUES(title),
                meta_description = VALUES(meta_description),
                cleaned_text = VALUES(cleaned_text),
                published_date = VALUES(published_date)
            """
            cursor.execute(query, (url, title, meta_description, cleaned_text, published_date))
            connection.commit()
            
            if cursor.rowcount == 1:
                print(f"Inserted new record for URL: {url}")
            elif cursor.rowcount == 2:
                print(f"Updated existing record for URL: {url}")
            
    except pymysql.Error as e:
        print(f"Database error while saving {url}: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()

# Configure Selenium (headless mode)
options = Options()
options.headless = True
driver = webdriver.Chrome(options=options)

# Load the page
url = "https://docs.onezeroart.com/zalultra/settings_page/general.html"
driver.get(url)
time.sleep(3)  # Wait for JavaScript to render content

# Parse HTML
soup = BeautifulSoup(driver.page_source, 'html.parser')
driver.quit()  # Close browser

# Extract title and meta description
title = soup.title.string if soup.title else None
meta_description_tag = soup.find('meta', attrs={'name': 'description'})
meta_description = meta_description_tag['content'] if meta_description_tag else None

# Remove sidebar content (all <aside> elements)
for aside in soup.find_all('aside'):
    aside.decompose()

# Clean and flatten <pre><code> command blocks
for pre in soup.find_all('pre'):
    for code in pre.find_all('code'):
        new_lines = []
        for line_span in code.find_all('span', class_='line'):
            parts = [part.get_text(strip=True) for part in line_span.find_all('span')]
            line = ' '.join(parts)
            new_lines.append(line)
        cleaned_code = '\n'.join(new_lines)
        pre.replace_with(cleaned_code)

for tag in soup.find_all(['h1', 'h2', 'h3', 'h4']):
    tag.insert_before(NavigableString('\n\n'))

# Try to find the main content container
main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')

def extract_with_heading_spacing(tag):
    texts = []
    skip_tags = {'script', 'style', 'head', 'title'}
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
                full_src = urljoin(base_url, src)
                texts.append(f'\n![Image]({full_src})\n')
        elif isinstance(elem, NavigableString):
            parent = elem.parent
            if parent.name in skip_tags or parent.name in ['h1', 'h2', 'h3', 'h4']:
                continue
            text = elem.strip()
            if not text:
                continue  # Skip empty lines always
            if just_added_heading:
                # Prevent line immediately after heading if it's just noise
                if text in ['\u200b', '\n', '\r', '', ' ']:  # includes non-breaking space
                    continue
                just_added_heading = False  # reset once real content appears
            
            # Check if this text is inside a <code> tag
            if parent.name == 'code':
                texts.append(f'`{text}`')
            else:
                texts.append(text)
    return '\n'.join(texts)

if main_content:
    full_text = extract_with_heading_spacing(main_content)
else:
    full_text = extract_with_heading_spacing(soup)

# Save to database instead of file
save_to_database(
    url=url,
    title=title,
    meta_description=meta_description,
    cleaned_text=full_text,
    published_date= None 
)