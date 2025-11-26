# src/genai_wrapper.py
import time, random, threading, re
from typing import Callable, Any, Optional

# Simple in-process rate limiter (sliding window)
class RateLimiter:
    def __init__(self, max_requests: int, per_seconds: int):
        self.max_requests = max_requests
        self.per_seconds = per_seconds
        self.lock = threading.Lock()
        self.timestamps = []

    def wait_for_slot(self):
        """Block until a slot is available. Keeps timestamps of recent requests."""
        while True:
            with self.lock:
                now = time.time()
                # drop old timestamps
                self.timestamps = [t for t in self.timestamps if t > now - self.per_seconds]
                if len(self.timestamps) < self.max_requests:
                    # we can proceed
                    self.timestamps.append(now)
                    return
                # otherwise compute sleep time until earliest timestamp falls out of window
                earliest = min(self.timestamps)
                sleep_for = (earliest + self.per_seconds) - now
            # sleep outside lock
            if sleep_for > 0:
                time.sleep(sleep_for + 0.01)  # tiny cushion

# Global rate limiter: adjust to your quota (example: free tier shows 2/min -> use 2)
# Set to allowed requests per minute. To be conservative, set slightly lower.
GLOBAL_RATE_LIMITER = RateLimiter(max_requests=2, per_seconds=60)

def _parse_retry_seconds_from_msg(msg: str) -> Optional[float]:
    """
    Try to parse a server-provided retry time from the error message.
    Returns seconds (float) or None.
    """
    if not msg:
        return None
    # common phrasing: "Please retry in 55.162194969s" or "retry_delay { seconds: 55 }"
    m = re.search(r"Please retry in (\d+(?:\.\d+)?)s", msg)
    if m:
        return float(m.group(1))
    m2 = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", msg)
    if m2:
        return float(m2.group(1))
    return None

def call_with_backoff(genai_call: Callable[[], Any],
                      max_attempts: int = 5,
                      initial_backoff: float = 1.0,
                      max_backoff: float = 120.0) -> Any:
    """
    Call the provided genai_call callable (which performs model.generate_content).
    Handles rate limiting (GLOBAL_RATE_LIMITER.wait_for_slot()), retries on errors,
    and honors server-provided retry seconds if available.
    """
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        # wait for rate-limit slot
        GLOBAL_RATE_LIMITER.wait_for_slot()
        try:
            return genai_call()
        except Exception as e:
            msg = str(e)
            # If server instructs a retry delay, use it
            retry_seconds = _parse_retry_seconds_from_msg(msg)
            if retry_seconds is not None:
                # jitter small
                sleep_for = min(max(retry_seconds, initial_backoff), max_backoff)
                jitter = random.uniform(0, min(2.0, sleep_for * 0.1))
                time.sleep(sleep_for + jitter)
                continue

            # If it's quota/rate-limit type or transient (429, 503, 502), do exponential backoff
            # We'll look for common HTTP codes or phrases
            if "429" in msg or "quota" in msg.lower() or "rate" in msg.lower() or "503" in msg or "Timeout" in msg:
                backoff = min(initial_backoff * (2 ** (attempt - 1)), max_backoff)
                jitter = random.uniform(0, backoff * 0.1)
                time.sleep(backoff + jitter)
                continue

            # For other exceptions, rethrow immediately
            raise
    # If we exhausted attempts, raise last exception
    raise RuntimeError("Exceeded retry attempts for genai call")
