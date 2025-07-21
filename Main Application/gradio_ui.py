# gradio_ui.py

import gradio as gr
from scraper_module import DocScraper


scraper = DocScraper()
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
            result = scraper.start_scrap(url)
            new_trigger = current_trigger + 1
            return result, new_trigger

        def update_dropdown(trigger):
            return gr.Dropdown(choices=scraper.get_titles(), label="Select Scraped Document", interactive=True)

        start_btn.click(fn=show_warning, inputs=url_input, outputs=warning_msg)

        gr.Markdown("---")

        dropdown = gr.Dropdown(choices=scraper.get_titles(), label="Select Scraped Document", interactive=True)
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

        view_btn.click(fn=scraper.display_article, inputs=dropdown, outputs=output)
        refresh_btn.click(fn=update_dropdown, inputs=refresh_trigger, outputs=dropdown)

    demo.launch()


if __name__ == '__main__':
    launch_viewer()
