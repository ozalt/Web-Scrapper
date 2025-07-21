
-----

**Web Scraper Class Explanation**

This document details the functionality of the `WebScraper` class, outlining its purpose, the tools it uses, and the specific operations it performs to extract and clean web content.

**Class: `WebScraper`**

**Purpose:** The `WebScraper` class is designed to visit a given URL, extract key information (title, meta description), and then extensively clean the HTML content to isolate the main article/body of the page, removing navigational elements, advertisements, footers, and other irrelevant markup. Finally, it stores the cleaned data into a database.

-----

**Block 1: Initialization (`__init__`)**

  * **Code:**
    ```python
    class WebScraper:
        def __init__(self, url):
            self.url = url
            self.title = None
            self.meta_description = None
            self.main_html = None
    ```
  * **Explanation:**
      * **`__init__(self, url)`:** This is the constructor method. When a `WebScraper` object is created, it requires a `url` as an argument.
      * **`self.url = url`:** Stores the URL of the webpage to be scraped.
      * **`self.title = None`:** Initializes an attribute to store the page's title. It's set to `None` initially, indicating no title has been captured yet.
      * **`self.meta_description = None`:** Initializes an attribute to store the page's meta description. Set to `None` initially.
      * **`self.main_html = None`:** Initializes an attribute to store the cleaned main HTML content of the page. Set to `None` initially.

-----

**Block 2: Scraping Mechanism (`scrape` method - Part 1: Fetching HTML)**

  * **Code:**
    ```python
    def scrape(self):
        options = Options()
        options.headless = True
        driver = webdriver.Chrome(options=options)
        driver.get(self.url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()
    ```
  * **Explanation:**
      * **`scrape(self)`:** This method orchestrates the web scraping process.
      * **`options = Options()` and `options.headless = True`:** Configures Selenium's Chrome WebDriver to run in "headless" mode. This means the browser will operate in the background without a visible GUI, which is efficient for automated scraping.
      * **`driver = webdriver.Chrome(options=options)`:** Initializes a Chrome web browser instance using Selenium WebDriver with the specified headless options.
      * **`driver.get(self.url)`:** Navigates the headless Chrome browser to the `self.url` (the target webpage).
      * **`time.sleep(3)`:** Introduces a 3-second pause. This is crucial for dynamic websites that load content asynchronously (e.g., via JavaScript). It gives the page time to fully render before its HTML is captured.
      * **`soup = BeautifulSoup(driver.page_source, 'html.parser')`:**
          * `driver.page_source`: Retrieves the complete HTML content of the page *after* it has been rendered by the browser (including dynamically loaded content).
          * `BeautifulSoup(...)`: Parses the obtained HTML string into a `BeautifulSoup` object. This object allows easy navigation and manipulation of the HTML structure. `'html.parser'` is the standard parser.
      * **`driver.quit()`:** Closes the Chrome WebDriver instance, releasing system resources. This is important to prevent memory leaks and ensure efficient operation, especially when scraping many pages.

-----

**Block 3: Initial Data Extraction (`scrape` method - Part 2: Title & Meta Description)**

  * **Code:**
    ```python
    self.title = soup.title.string if soup.title else None
    meta_tag = soup.find('meta', attrs={'name': 'description'})
    self.meta_description = meta_tag['content'] if meta_tag else None
    ```
  * **Explanation:**
      * **`self.title = soup.title.string if soup.title else None`:**
          * `soup.title`: Finds the `<title>` tag in the parsed HTML.
          * `.string`: Extracts the text content within the `<title>` tag.
          * `if soup.title else None`: This is a conditional assignment. If a `<title>` tag is found, its string content is assigned to `self.title`; otherwise, `self.title` remains `None`.
      * **`meta_tag = soup.find('meta', attrs={'name': 'description'})`:** Searches for the first `<meta>` tag that has a `name` attribute equal to `'description'`.
      * **`self.meta_description = meta_tag['content'] if meta_tag else None`:**
          * `meta_tag['content']`: If the `meta_tag` is found, this accesses the value of its `content` attribute, which typically holds the meta description.
          * `if meta_tag else None`: Similar to the title, if a meta description tag is found, its content is assigned; otherwise, `self.meta_description` is `None`.

-----

**Block 4: Global Tag Removal (`scrape` method - Part 3: Initial Cleaning - General UI Elements)**

  * **Code:**
    ```python
    for tag in ['aside', 'nav', 'footer', 'form', 'iframe', 'script', 'svg', 'button', 'select','input', 'label', 'source', 'form', 'audio', 'video']:
        for element in soup.find_all(tag):
            element.decompose()
    ```
  * **Explanation:**
      * **Purpose:** This block systematically removes common HTML tags that are typically part of a webpage's user interface, navigation, or non-content elements. The goal is to strip away visual clutter and functional components not relevant to the main article content.
      * **`for tag in [...]`:** Iterates through a predefined list of HTML tag names.
          * **`aside`:** Sidebars, supplementary content.
          * **`nav`:** Navigation links (menus).
          * **`footer`:** Page footer, copyright, contact info.
          * **`form`:** Interactive forms (redundant for content extraction).
          * **`iframe`:** Embedded content from other sources.
          * **`script`:** JavaScript code (not content).
          * **`svg`:** Scalable Vector Graphics (often icons or non-textual elements).
          * **`button`, `select`, `input`, `label`:** Form controls.
          * **`source`:** Used within media elements (audio/video).
          * **`audio`, `video`:** Media players (the media itself, not the text content).
      * **`for element in soup.find_all(tag):`:** For each tag in the list, it finds *all* occurrences of that tag throughout the entire `soup` (the parsed HTML).
      * **`element.decompose()`:** This is a `BeautifulSoup` method that completely removes the `element` and all its children from the `soup` object. This is a destructive operation.

-----

**Block 5: Global Tag Removal (`scrape` method - Part 4: Initial Cleaning - Google-Styled Docs Elements)**

  * **Code:**
    ```python
    for tag in ['devsite-toc', 'devsite-feedback', 'devsite-nav', 'devsite-footer',
                     'devsite-banner', 'devsite-section-nav', 'devsite-book-nav', 'google-codelab-step',
                     'mdn-sidebar', 'mdn-toc', 'api-index', 'amp-sidebar', 'amp-accordion']:
        for element in soup.find_all(tag):
            element.decompose()
    ```
  * **Explanation:**
      * **Purpose:** This block targets custom HTML tags or components often found on specific types of documentation sites, particularly those following Google's `devsite` styling or MDN (Mozilla Developer Network) structures, and AMP (Accelerated Mobile Pages). These are removed to further clean up the main content.
      * **`for tag in [...]`:** Iterates through a list of non-standard HTML tag names (often custom web components or specific class names).
          * `devsite-*`: Common on Google's developer documentation.
          * `mdn-*`: Common on MDN's documentation.
          * `google-codelab-step`: Specific to Google Codelabs.
          * `api-index`: Likely an index for API documentation.
          * `amp-sidebar`, `amp-accordion`: AMP-specific UI components.
      * **`for element in soup.find_all(tag):`** Finds all occurrences of these specialized tags.
      * **`element.decompose()`:** Removes the element and its children from the HTML.

-----

**Block 6: Header Handling (`scrape` method - Part 5: Specific Header Cleaning)**

  * **Code:**
    ```python
    for header in soup.find_all('header'):
        parent = header.find_parent(['main', 'article'])

        if parent:
            # If header is inside <main> or <article>, keep only h1–h4 tags
            for child in list(header.contents):
                if not (getattr(child, 'name', None) in ['h1', 'h2', 'h3', 'h4']):
                    child.extract()
            # If it becomes empty after stripping non-headings, remove it too
            if not header.find(['h1', 'h2', 'h3', 'h4']):
                header.decompose()
        else:
            # Header outside main/article: remove completely
            header.decompose()
    ```
  * **Explanation:**
      * **Purpose:** This block specifically processes `<header>` tags. Headers can contain important titles, but also navigation, logos, or other non-content elements. This logic aims to preserve *only* the heading tags (`h1`-`h4`) if the header is part of the main content, otherwise, it removes the entire header.
      * **`for header in soup.find_all('header'):`:** Iterates through all `<header>` tags found on the page.
      * **`parent = header.find_parent(['main', 'article'])`:** Checks if the current `<header>` element is nested within a `<main>` or `<article>` tag. This is a heuristic to determine if the header is part of the main content block.
      * **`if parent:` (Header inside main content):**
          * **`for child in list(header.contents):`:** Iterates through all direct children of the `<header>` tag. `list(header.contents)` is used to create a mutable list of children, as `extract()` modifies the original `contents` in place.
          * **`if not (getattr(child, 'name', None) in ['h1', 'h2', 'h3', 'h4']):`:** Checks if a child element is *not* an `h1`, `h2`, `h3`, or `h4` tag. `getattr(child, 'name', None)` safely gets the tag name if `child` is a tag, otherwise `None`.
          * **`child.extract()`:** If the child is not one of the desired heading tags, it's removed from the header. `extract()` removes the element but does not remove its children from the original parse tree.
          * **`if not header.find(['h1', 'h2', 'h3', 'h4']):`:** After removing non-heading children, this checks if the `header` element has become empty or no longer contains any `h1`-`h4` tags.
          * **`header.decompose()`:** If the header is now empty of relevant headings, the entire `<header>` tag is removed.
      * **`else:` (Header outside main content):**
          * **`header.decompose()`:** If the `<header>` tag is not found within a `<main>` or `<article>` element (meaning it's likely a global site header), it is completely removed.

-----

**Block 7: Identifying Main Content Area (`scrape` method - Part 6: Main Content Scope)**

  * **Code:**
    ```python
    main = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup.body
    ```
  * **Explanation:**
      * **Purpose:** This line is crucial for defining the scope of subsequent cleaning operations. It attempts to identify the primary content area of the webpage.
      * **`soup.find('main')`:** First, it tries to find the `<main>` HTML5 semantic tag, which is designed to encapsulate the dominant content of the `<body>`. This is the preferred method.
      * **`or soup.find('article')`:** If no `<main>` tag is found, it then tries to find an `<article>` tag, which represents a self-contained composition in a document.
      * **`or soup.find('div', class_='content')`:** If neither `<main>` nor `<article>` is found, it looks for a `<div>` tag with a `class` attribute set to `'content'`. This is a common convention for content divisions.
      * **`or soup.body`:** As a fallback, if none of the above are found, the entire `<body>` of the document is used as the "main" content area. This ensures that some content is always captured, even if semantic tags are not used.
      * **`main = ...`:** The selected element (or `<body>`) is assigned to the `main` variable. All subsequent content cleaning will focus within this `main` element.

-----

**Block 8: Cleaning within Main Content (`scrape` method - Part 7: Heading Divs & Pictures)**

  * **Code:**
    ```python
    for tag in main.find_all(['h1', 'h2', 'h3', 'h4', 'h5']):
        for div in tag.find_all('div'):
            div.decompose()

    for picture in main.find_all('picture'):
        img = picture.find('img')
        if img:
            picture.insert_after(img)  # Move <img> out
        picture.decompose()  # Remove the original <picture>
    ```
  * **Explanation:**
      * **Purpose:** This block performs more granular cleaning specifically within the `main` content area.
      * **Removing Divs within Headings:**
          * **`for tag in main.find_all(['h1', 'h2', 'h3', 'h4', 'h5']):`:** Iterates through all heading tags (h1 to h5) found *within* the `main` content.
          * **`for div in tag.find_all('div'):`:** For each heading, it looks for any nested `<div>` tags. Some CMS or styling might wrap parts of headings in divs, which are often unnecessary for plain text extraction.
          * **`div.decompose()`:** Removes these nested `div` elements.
      * **Handling `<picture>` Tags:**
          * **`for picture in main.find_all('picture'):`:** Iterates through all `<picture>` elements (used for responsive images) within the `main` content.
          * **`img = picture.find('img')`:** Attempts to find an `<img>` tag inside the `<picture>` tag.
          * **`if img:`:** If an `<img>` tag is found:
              * **`picture.insert_after(img)`:** Moves the found `<img>` tag *after* its parent `<picture>` tag. This extracts the actual image element from its responsive wrapper.
          * **`picture.decompose()`:** Removes the original `<picture>` tag (which now might be empty or contain only `<source>` tags, which are not needed for content). The goal is to retain only the direct `<img>` tag if present.

-----

**Block 9: Cleaning within Main Content (`scrape` method - Part 8: Specific Divs)**

  * **Code:**
    ```python
    for div in main.find_all('div', attrs={'data-svelte-h': True}):
        div.decompose()

    # Remove <div> that contains only <a> tags and nothing else
    for div in main.find_all('div'):
        contents = [child for child in div.contents if not isinstance(child, NavigableString) or child.strip()]
        if contents and all(child.name == 'a' for child in contents if hasattr(child, 'name')):
            div.decompose()
    ```
  * **Explanation:**
      * **Purpose:** Continues to remove specific `div` patterns that are typically not part of the main textual content.
      * **Removing Svelte-Specific Divs:**
          * **`for div in main.find_all('div', attrs={'data-svelte-h': True}):`:** Targets `div` elements that have a `data-svelte-h` attribute set to `True`. This is often a SvelteJS-specific attribute for handling hydration or unique IDs, and these divs usually wrap UI components or dynamic elements not central to static content.
          * **`div.decompose()`:** Removes these Svelte-related divs.
      * **Removing Divs Containing Only Links:**
          * **`for div in main.find_all('div'):`:** Iterates through all `div` elements within the `main` content.
          * **`contents = [child for child in div.contents if not isinstance(child, NavigableString) or child.strip()]`:** This line filters the direct children of the `div`. It keeps only actual HTML tags (not `NavigableString` objects like whitespace or comments) or non-empty strings.
          * **`if contents and all(child.name == 'a' for child in contents if hasattr(child, 'name')):`:** Checks two conditions:
              * `contents`: Ensures the `div` is not completely empty after filtering.
              * `all(child.name == 'a' for child in contents if hasattr(child, 'name'))`: Checks if *all* remaining children are `<a>` (anchor/link) tags. This identifies divs that are essentially just containers for lists of links (e.g., related posts, tag clouds, share buttons).
          * **`div.decompose()`:** If a `div` contains *only* `<a>` tags (and no other content), it's removed.

-----

**Block 10: Cleaning within Main Content (`scrape` method - Part 9: Divs by ID/Role/Class)**

  * **Code:**
    ```python
    for div in main.find_all('div', id=lambda x: x and x.lower() in ['comment', 'comments','sidebar', 'right-sidebar', 'md-sidebar','breadcrumbs','breadcrumb','reviews','feedback']):
        div.decompose()

    for div in main.find_all('div', role=lambda x: x and x.lower() in ['nav', 'navigation', 'sidebar', 'breadcrumb', 'breadcrumbs','header','heading', 'menubar', 'menu']):
        div.decompose()

    for div in main.find_all('div', attrs={'aria-label': lambda x: x and x.lower() in ['nav', 'navbar','navigation', 'sidebar', 'breadcrumb', 'breadcrumbs', 'menubar', 'menu']}):
        div.decompose()

    for div in main.find_all('div', attrs={'class': lambda x: x and x.lower() in ['nav', 'navbar','navigation', 'sidebar', 'breadcrumb', 'breadcrumbs', 'menubar', 'menu']}):
        div.decompose()
    ```
  * **Explanation:**
      * **Purpose:** These four loops are designed to aggressively remove `div` elements that are likely part of navigation, sidebars, comments sections, or other non-article content, based on their `id`, `role`, `aria-label`, or `class` attributes.
      * **Lambda Functions (`lambda x: x and x.lower() in [...]`):** This is a compact way to define an anonymous function that checks if an attribute's value (converted to lowercase) is present in a specific list of keywords. It also handles cases where the attribute might be `None` (`x and ...`).
      * **Removal by `id`:** Targets `div`s whose `id` attribute (case-insensitive) matches terms like 'comment', 'sidebar', 'breadcrumbs', 'reviews', 'feedback'.
      * **Removal by `role`:** Targets `div`s whose `role` attribute (case-insensitive) matches terms like 'nav', 'navigation', 'sidebar', 'breadcrumb', 'header', 'menubar', 'menu'. Roles provide semantic meaning for accessibility.
      * **Removal by `aria-label`:** Targets `div`s whose `aria-label` attribute (case-insensitive) matches terms like 'nav', 'navbar', 'navigation', 'sidebar', 'breadcrumb', 'menubar', 'menu'. `aria-label` provides a human-readable label for accessibility.
      * **Removal by `class`:** Targets `div`s whose `class` attribute (case-insensitive) matches terms like 'nav', 'navbar', 'navigation', 'sidebar', 'breadcrumb', 'menubar', 'menu'. This is a common way to style and identify UI components.
      * **`div.decompose()`:** In all these cases, the matched `div` element and its entire content are removed.

-----

**Block 11: Cleaning within Main Content (`scrape` method - Part 10: Anchor Tags & List Items)**

  * **Code:**
    ```python
    for ul in main.find_all('ul', role=lambda x: x and x.lower() in ['nav', 'navigation', 'sidebar', 'breadcrumb', 'breadcrumbs','header','heading','menubar', 'menu']):
        div.decompose()

    for ul in main.find_all('ul', attrs={'aria-label': lambda x: x and x.lower() in ['nav', 'navigation', 'sidebar', 'breadcrumb', 'breadcrumbs','menubar', 'menu']}):
        div.decompose()

    # Unwrap all <a> tags inside the main content
    for a_tag in main.find_all('a'):
        a_tag.unwrap()

    # Remove any <a> tags that contain images
    for a_tag in main.find_all('a'):
        if a_tag.find('img'):
            a_tag.decompose()

    #Remove any <li>
    for li in main.find_all('li'):
        class_id_values = ' '.join(filter(None, [*li.get('class', []), li.get('id') or ''])).lower()
        if any(social in class_id_values for social in ['instagram', 'facebook', 'twitter', 'whatsapp', 'snapchat']):
            li.decompose()
    ```
  * **Explanation:**
      * **Purpose:** This block further refines the cleaning, specifically targeting `<ul>` (unordered list) elements, `<a>` (anchor/link) tags, and `<li>` (list item) tags to remove more non-content elements.
      * **Removal of ULs by `role` and `aria-label`:** (Similar to `div` removal in previous block)
          * These two loops identify and remove `<ul>` elements that function as navigation menus, sidebars, or breadcrumbs based on their `role` or `aria-label` attributes.
          * **`ul.decompose()`:** Removes the identified `<ul>` elements.
      * **Unwrapping All Anchor Tags:**
          * **`for a_tag in main.find_all('a'):`:** Iterates through every `<a>` tag within the `main` content.
          * **`a_tag.unwrap()`:** This is a key operation. Instead of removing the `<a>` tag, `unwrap()` removes *only* the tag itself, leaving its contents (the text or other tags inside the link) in place. This is useful for preserving the textual content of links while removing the linking functionality, as the goal is usually to extract plain text.
      * **Removing Anchor Tags Containing Images:**
          * **`for a_tag in main.find_all('a'):`:** Iterates through `<a>` tags again (those that might not have been unwrapped if they were already processed, or newly exposed).
          * **`if a_tag.find('img'):`:** Checks if an `<img>` tag is present *inside* the `<a>` tag.
          * **`a_tag.decompose()`:** If an `<a>` tag contains an image, the entire `<a>` tag (and the image within it) is removed. This often targets image links which are not relevant to textual content.
      * **Removing Social Media List Items:**
          * **`for li in main.find_all('li'):`:** Iterates through all `<li>` (list item) tags.
          * **`class_id_values = ' '.join(filter(None, [*li.get('class', []), li.get('id') or ''])).lower()`:** This line cleverly combines the values of the `class` and `id` attributes of the `<li>` tag into a single lowercase string. `filter(None, ...)` removes any `None` values, and `*li.get('class', [])` expands the list of classes.
          * **`if any(social in class_id_values for social in ['instagram', 'facebook', 'twitter', 'whatsapp', 'snapchat']):`:** Checks if any of the specified social media keywords are present in the combined `class_id_values` string. This helps identify social sharing buttons or links.
          * **`li.decompose()`:** If a list item is identified as a social media link, it's removed.

-----

**Block 12: Cleaning within Main Content (`scrape` method - Part 11: Table of Contents & Spans)**

  * **Code:**
    ```python
    # Remove <ul> elements with class "table-of-contents"
    for ul in main.find_all('ul', class_='table-of-contents'):
        ul.decompose()

    #It ensures garbage markup like <span><a>…</a></span> or <span><img /></span> vanishes cleanly.
    for span in main.find_all('span'):
        children = [child for child in span.contents if not isinstance(child, NavigableString) or child.strip()]
        if len(children) == 1 and getattr(children[0], 'name', None) in ['img', 'a']:
            span.decompose()
    ```
  * **Explanation:**
      * **Purpose:** This block handles more specific clean-up scenarios, including common table-of-contents structures and problematic `<span>` tags.
      * **Removing Table of Contents ULs:**
          * **`for ul in main.find_all('ul', class_='table-of-contents'):`:** Explicitly targets `<ul>` elements that have the class `table-of-contents`. These are typically navigational aids, not part of the core content.
          * **`ul.decompose()`:** Removes these table of contents lists.
      * **Removing "Garbage Markup" Spans:**
          * **`for span in main.find_all('span'):`** Iterates through all `<span>` tags within the `main` content.
          * **`children = [child for child in span.contents if not isinstance(child, NavigableString) or child.strip()]`:** Filters the children of the `<span>` tag to include only significant elements (i.e., not just whitespace or comments).
          * **`if len(children) == 1 and getattr(children[0], 'name', None) in ['img', 'a']:`:** Checks if the `<span>` tag contains exactly one significant child, and if that child is either an `<img>` tag or an `<a>` tag. This pattern often indicates a `<span>` used for styling a single image or link, which is redundant or "garbage markup" for content extraction.
          * **`span.decompose()`:** If this pattern is matched, the entire `<span>` (and its single child) is removed.

-----

**Block 13: Final HTML Processing (`scrape` method - Part 12: Inline Styles & Final Output)**

  * **Code:**
    ```python
    # Remove inline styles
    for tag in main.find_all(True):
        if 'style' in tag.attrs:
            del tag['style']

    self.main_html = str(main)
    ```
  * **Explanation:**
      * **Purpose:** This final cleaning step removes inline styling and then converts the cleaned `BeautifulSoup` object back into an HTML string for storage.
      * **Removing Inline Styles:**
          * **`for tag in main.find_all(True):`:** Iterates through *every* HTML tag within the `main` content. `True` as an argument to `find_all` means "find all tags."
          * **`if 'style' in tag.attrs:`:** Checks if the current tag has a `style` attribute. This attribute often contains inline CSS that controls visual presentation but is irrelevant for content extraction and can add clutter.
          * **`del tag['style']`:** If a `style` attribute is found, it's removed from the tag.
      * **`self.main_html = str(main)`:**
          * `str(main)`: Converts the `main` BeautifulSoup element (which now contains the extensively cleaned HTML structure) back into a string representation.
          * This final cleaned HTML string is stored in the `self.main_html` attribute, ready to be saved.

-----

**Block 14: Saving Data (`save` method)**

  * **Code:**
    ```python
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
    ```
  * **Explanation:**
      * **`save(self)`:** This method is responsible for persisting the scraped and cleaned data into a MySQL database.
      * **`try...except...finally` block:** Ensures robust database interaction, handling potential errors and ensuring the database connection is always closed.
      * **`conn = pymysql.connect(**DB_CONFIG)`:** Establishes a connection to the MySQL database. `DB_CONFIG` (not shown in the snippet) would be a dictionary containing database connection parameters (host, user, password, database name).
      * **`with conn.cursor() as cursor:`:** Creates a database cursor, which is used to execute SQL queries. The `with` statement ensures the cursor is properly closed.
      * **`query = """ ... """`:** Defines the SQL `INSERT` query.
          * **`INSERT INTO blog_articles (...) VALUES (%s, %s, %s, %s, %s)`:** Attempts to insert a new row into the `blog_articles` table with the URL, title, meta description, cleaned HTML, and a `None` value for `published_date`.
          * **`ON DUPLICATE KEY UPDATE ...`:** This is a crucial part for handling cases where the `url` might already exist in the `blog_articles` table (assuming `url` is a `UNIQUE` key). If a duplicate `url` is found, instead of failing, it updates the existing record with the new `title`, `meta_description`, and `cleaned_text`. This makes the scraper idempotent for existing URLs.
      * **`cursor.execute(query, (self.url, self.title, self.meta_description, self.main_html, None))`:** Executes the SQL query with the scraped data passed as a tuple. The `%s` placeholders prevent SQL injection vulnerabilities.
      * **`conn.commit()`:** Commits the transaction to the database, making the changes permanent.
      * **`return "✅ Scraped and saved to database!"`:** Returns a success message if the operation completes without error.
      * **`except Exception as e:`:** Catches any exception that occurs during the database operation.
      * **`return f"❌ DB Error: {e}"`:** Returns an error message including the exception details.
      * **`finally:`:**
          * **`conn.close()`:** Ensures the database connection is closed regardless of whether the `try` block succeeded or an exception occurred. This is vital for resource management.

-----