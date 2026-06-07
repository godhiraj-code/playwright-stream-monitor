import os
from playwright.sync_api import sync_playwright
from playwright_stream_monitor import StreamMonitor

def test_stream_monitor_live():
    # Construct local file URL
    html_path = os.path.abspath("C:/Users/dhira/playwright-stream-monitor/tests/stream_test.html")
    file_url = f"file:///{html_path.replace(os.sep, '/')}"
    
    print(f"Opening test page: {file_url}")
    
    with sync_playwright() as p:
        # Launch browser in headless mode
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(file_url)
        
        # Initialize the monitor on our selector
        monitor = StreamMonitor(page, "#output")
        
        # Start browser-side observer
        monitor.start_monitoring()
        
        # Click the start button to trigger the stream
        page.click("#start-btn")
        print("Click triggered, waiting for stream to complete...")
        
        # Wait dynamically for the stream to complete
        final_text = monitor.wait_for_stream_complete(timeout_sec=10.0, stall_timeout_sec=1.5)
        print(f"\nFinal Streamed Text:\n'{final_text}'\n")
        
        # Stop monitoring and get metrics
        metrics = monitor.stop_monitoring()
        
        print("=== STREAM MONITOR METRICS ===")
        print(f"Total Stream Duration: {metrics['total_duration_ms']:.2f}ms")
        print(f"Time-to-First-Token (TTFT): {metrics['ttft_ms']:.2f}ms")
        print(f"Total Mutations Detected: {metrics['total_mutations']}")
        print(f"Is Stream Stalled: {metrics['stalled']}")
        
        # Clean assertions
        assert metrics["stalled"] is False, "Stream should not be stalled."
        assert metrics["ttft_ms"] is not None, "First token should be detected."
        assert metrics["ttft_ms"] < 1000, "TTFT should be under 1s for a local simulated stream."
        assert len(final_text) > 50, "Stream text should contain the full sentence."
        
        print("\n🎉 ALL LIVE TEST ASSERTIONS PASSED SUCCESSFULLY!")
        browser.close()

if __name__ == "__main__":
    test_stream_monitor_live()
