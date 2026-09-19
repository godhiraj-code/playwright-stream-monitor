from unittest.mock import patch

import pytest

from playwright_stream_monitor import StreamMonitor


class FakeClock:
    def __init__(self) -> None:
        self.current = 0.0

    def monotonic(self) -> float:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current += seconds


class FakeLocator:
    def __init__(self, texts):
        self.texts = iter(texts)
        self.last_text = ""
        self.calls = 0

    def inner_text(self) -> str:
        self.calls += 1
        self.last_text = next(self.texts, self.last_text)
        return self.last_text


class FakePage:
    def __init__(self, texts):
        self.fake_locator = FakeLocator(texts)
        self.selector = None

    def locator(self, selector: str) -> FakeLocator:
        self.selector = selector
        return self.fake_locator


def wait_with_fake_clock(texts, timeout_sec=1.0, stall_timeout_sec=0.15):
    clock = FakeClock()
    page = FakePage(texts)
    monitor = StreamMonitor(page, "#output")

    with patch(
        "playwright_stream_monitor.time.monotonic", clock.monotonic
    ), patch("playwright_stream_monitor.time.sleep", clock.sleep):
        result = monitor.wait_for_stream_complete(timeout_sec, stall_timeout_sec)

    return result, page


def test_wait_returns_text_after_stream_stalls() -> None:
    result, page = wait_with_fake_clock(["", "a", "ab", "abc"])

    assert result == "abc"
    assert page.selector == "#output"


def test_same_length_replacement_resets_stall_timer() -> None:
    result, page = wait_with_fake_clock(["", "ab", "cd"])

    assert result == "cd"
    assert page.fake_locator.calls >= 5


def test_wait_times_out_when_text_keeps_changing() -> None:
    clock = FakeClock()
    page = FakePage([str(index) for index in range(20)])
    monitor = StreamMonitor(page, "#output")

    with patch(
        "playwright_stream_monitor.time.monotonic", clock.monotonic
    ), patch("playwright_stream_monitor.time.sleep", clock.sleep):
        with pytest.raises(TimeoutError, match=r"within 0\.3s"):
            monitor.wait_for_stream_complete(timeout_sec=0.3, stall_timeout_sec=1.0)
