# playwright-stream-monitor

A lightweight utility pattern to track, measure, and validate Server-Sent Events (SSE) and streaming LLM responses in Playwright test suites.

## The Problem
Traditional automated tests (Selenium, Playwright) struggle with streaming AI chatbot interfaces because they trigger flaky timeouts. Waiting for the text to appear using standard loaders can create race conditions, and if the stream stalls mid-generation, tests hang without diagnosing *where* or *why* the failure occurred.

## The Solution
`playwright-stream-monitor` attaches a browser-side `MutationObserver` to your streaming chat container. It tracks character mutations in real-time, allowing you to:
1.  **Measure Time-To-First-Token (TTFT)**.
2.  **Verify stream continuity** (detect if generation stalls or errors mid-stream).
3.  **Capture metrics** like token velocity and mutation counts.
4.  **Wait dynamically** for streaming to complete without using hardcoded sleeps.

---

## Installation

```bash
pip install playwright-stream-monitor
```

---

## Usage

Here is how you can use `StreamMonitor` in a Pytest-Playwright test suite:

```python
import pytest
from playwright.sync_api import Page
from playwright_stream_monitor import StreamMonitor

def test_streaming_chatbot(page: Page):
    # 1. Navigate and trigger stream
    page.goto("https://your-ai-app.com/chat")
    page.fill("#prompt-input", "Write a 500-word story.")
    page.click("#send-btn")

    # 2. Initialize monitor on the chatbot response selector
    monitor = StreamMonitor(page, ".chat-bubble-latest")
    
    # 3. Start monitoring
    monitor.start_monitoring()

    # 4. Wait for stream to complete dynamically
    final_text = monitor.wait_for_stream_complete(timeout_sec=15.0, stall_timeout_sec=2.5)

    # 5. Extract metrics
    metrics = monitor.stop_monitoring()

    print(f"Time-to-First-Token (TTFT): {metrics['ttft_ms']:.2f}ms")
    print(f"Total Mutations: {metrics['total_mutations']}")

    # Assertions
    assert metrics["stalled"] is False, "The LLM stream stalled mid-generation!"
    assert metrics["ttft_ms"] < 1500, "TTFT exceeded the SLA threshold of 1.5s!"
    assert len(final_text) > 100, "Response content was unexpectedly short."
```

## Contributing
Contributions are welcome! Please open an issue or pull request on GitHub to suggest improvements or features.

## License
MIT
