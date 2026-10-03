import time
import uuid
from playwright.sync_api import Page

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
        self._monitor_key = "__streamMonitor_" + uuid.uuid4().hex

    def start_monitoring(self):
        """Attaches a MutationObserver to the streaming element in the browser."""
        self.page.evaluate(
            """({sel, key}) => {
                const target = document.querySelector(sel);
                if (!target) throw new Error(`Selector ${sel} not found`);

                // Restarting the same monitor must release its old observer.
                if (window[key] && window[key].observer) {
                    window[key].observer.disconnect();
                }
                const state = window[key] = {};
                
                state.history = [];
                state.start = performance.now();
                state.firstToken = null;
                state.lastMutation = state.start;

                const observer = new MutationObserver((mutations) => {
                    const text = target.innerText || target.textContent || '';
                    const now = performance.now();
                    
                    if (state.firstToken === null && text.trim().length > 0) {
                        state.firstToken = now;
                    }
                    
                    state.history.push({
                        timestamp: now,
                        text_length: text.length,
                        text_preview: text.slice(-20)
                    });
                    state.lastMutation = now;
                });

                observer.observe(target, { 
                    childList: true, 
                    characterData: true, 
                    subtree: true 
                });
                
                state.observer = observer;
            }""",
            {"sel": self.selector, "key": self._monitor_key}
        )

    def stop_monitoring(self) -> dict:
        """Stops the observer and returns computed streaming metrics."""
        metrics = self.page.evaluate(
            """(key) => {
                const state = window[key];
                if (!state) throw new Error('Monitor has not been started or was already stopped');
                state.observer.disconnect();
                delete window[key];
                
                const now = performance.now();
                const history = state.history;
                const start = state.start;
                const firstToken = state.firstToken;
                
                return {
                    "total_duration_ms": now - start,
                    "ttft_ms": firstToken !== null ? (firstToken - start) : null,
                    "total_mutations": history.length,
                    "stalled": (now - state.lastMutation) > 2000,
                    "history": history
                };
            }""",
            self._monitor_key
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
