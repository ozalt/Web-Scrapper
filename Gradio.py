import gradio as gr
import pymysql

# --- DB CONFIG --- #
HOST = '127.0.0.1'
USER = 'root'         # Change me
PASSWORD = 'admin'     # Change me
DATABASE = 'blog_scraper'

# --- FUNCTION TO GET BLOG TITLES FROM DB --- #
def get_titles():
    conn = pymysql.connect(host=HOST, user=USER, password=PASSWORD, database=DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM blog_articles ORDER BY scraped_at DESC")
    results = cursor.fetchall()
    conn.close()
    return [(title, id) for id, title in results]

def display_article(blog_id):
    conn = pymysql.connect(host=HOST, user=USER, password=PASSWORD, database=DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT title, url, meta_description, cleaned_text, published_date, scraped_at
        FROM blog_articles WHERE id = %s
    """, (blog_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        title, url, meta, content, published, scraped = result
        # Convert newlines to double newlines for Markdown
        formatted_content = content.replace('\n', '\n\n')
        return f"""### 📝 {title}

📎 **URL:** {url}  
🕒 **Published:** {published if published else "N/A"}  
📥 **Scraped at:** {scraped}  
🧾 **Meta Description:** {meta if meta else "N/A"}

---

{formatted_content}
"""
    else:
        return "❌ Blog not found."

# --- SETUP GRADIO UI --- #
def launch_viewer():
    with gr.Blocks(title="Scrap Viewer") as demo:
        gr.Markdown("## 📚 Scraped Article/Documents Viewer")

        dropdown = gr.Dropdown(choices=get_titles(), label="Select a blog to view", interactive=True)
        view_btn = gr.Button("🔍 View Blog")
        output = gr.Markdown()

        view_btn.click(fn=display_article, inputs=dropdown, outputs=output)

    demo.launch()


# --- RUN --- #
if __name__ == '__main__':
    launch_viewer()
