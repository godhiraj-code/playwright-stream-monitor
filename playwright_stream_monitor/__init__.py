import time
from playwright.sync_api import Page, Locator

class StreamMonitor:
    def __init__(self, page: Page, selector: str):
        """
        Initialize the StreamMonitor with a Playwright page instance and a selector.
        
        Args:
            page (Page): The Playwright Page instance.
            selector (str): The CSS selector of the streaming element.
        """
        self.page = page
        self.selector = selector

    def start_monitoring(self):
        """Attaches a MutationObserver to the streaming element in the browser."""
        self.page.evaluate(
            """(sel) => {
                const target = document.querySelector(sel);
                if (!target) throw new Error(`Selector ${sel} not found`);
                
                window._streamHistory = [];
                window._streamStartTime = performance.now();
                window._streamFirstTokenTime = null;
                window._streamLastMutationTime = performance.now();
                window._streamIsActive = true;

                const observer = new MutationObserver((mutations) => {
                    const text = target.innerText || target.textContent;
                    const now = performance.now();
                    
                    if (!window._streamFirstTokenTime && text.trim().length > 0) {
                        window._streamFirstTokenTime = now;
                    }
                    
                    window._streamHistory.push({
                        timestamp: now,
                        text_length: text.length,
                        text_preview: text.slice(-20)
                    });
                    window._streamLastMutationTime = now;
                });

                observer.observe(target, { 
                    childList: true, 
                    characterData: true, 
                    subtree: true 
                });
                
                window._streamObserverInstance = observer;
            }""",
            self.selector
        )

    def stop_monitoring(self) -> dict:
        """Stops the observer and returns computed streaming metrics."""
        metrics = self.page.evaluate(
            """() => {
                if (window._streamObserverInstance) {
                    window._streamObserverInstance.disconnect();
                }
                
                const now = performance.now();
                const history = window._streamHistory || [];
                const start = window._streamStartTime;
                const firstToken = window._streamFirstTokenTime;
                
                return {
                    "total_duration_ms": now - start,
                    "ttft_ms": firstToken ? (firstToken - start) : null,
                    "total_mutations": history.length,
                    "stalled": (now - window._streamLastMutationTime) > 2000,
                    "history": history
                };
            }"""
        )
        return metrics

    def wait_for_stream_complete(self, timeout_sec: float = 30.0, stall_timeout_sec: float = 3.0) -> str:
        """
        Polls the streaming element. Returns the final text once 
        mutations stop for longer than the stall_timeout.
        
        Args:
            timeout_sec (float): The maximum time to wait for completion.
            stall_timeout_sec (float): How long the stream must remain unchanged to be considered complete.
            
        Returns:
            str: The final accumulated text.
        """
        start_time = time.monotonic()
        last_text = None
        last_mutation_time = start_time

        while time.monotonic() - start_time < timeout_sec:
            # Compare the actual text so same-length replacements count as changes.
            text = self.page.locator(self.selector).inner_text()
            now = time.monotonic()

            if text != last_text:
                last_text = text
                last_mutation_time = now
            elif now - last_mutation_time > stall_timeout_sec:
                # Stream has stopped mutating for longer than the stall threshold
                return text

            time.sleep(0.1)

        raise TimeoutError(f"Stream did not complete within {timeout_sec}s")
