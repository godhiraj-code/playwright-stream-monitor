from playwright.sync_api import sync_playwright

from playwright_stream_monitor import StreamMonitor


def test_monitors_are_independent_and_restart_disconnects_observer():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content('<div id="first"></div><div id="second"></div>')
            first = StreamMonitor(page, "#first")
            second = StreamMonitor(page, "#second")
            first.start_monitoring()
            second.start_monitoring()
            first.start_monitoring()
            page.eval_on_selector("#first", "el => el.textContent = 'hello'")
            first_metrics = first.stop_monitoring()
            page.eval_on_selector("#second", "el => el.textContent = 'world'")
            second_metrics = second.stop_monitoring()
            assert first_metrics["total_mutations"] == 1
            assert second_metrics["total_mutations"] == 1
            assert first_metrics["history"][0]["text_preview"] == "hello"
            assert second_metrics["history"][0]["text_preview"] == "world"
            assert page.evaluate("Object.keys(window).filter(k => k.startsWith('__streamMonitor_')).length") == 0
        finally:
            browser.close()
