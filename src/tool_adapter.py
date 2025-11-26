# src/tool_adapter.py
import os
import time
import requests
import logging
from typing import Any, Dict, Callable, Optional

# --- Logging setup (writes to data/processed/search_debug.log) ---
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
os.makedirs(LOG_DIR, exist_ok=True)
log_path = os.path.join(LOG_DIR, "search_debug.log")
logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s [simple_search] %(message)s")

# --- Small Tool wrapper used by agents/orchestrator/ui ---
class Tool:
    """
    Simple wrapper for tools so agents call .call(query) and get a consistent return value.
    """
    def __init__(self, name: str, func: Callable):
        self.name = name
        self.func = func

    def call(self, *args, **kwargs):
        # Standardize try/except and return a consistent dict structure
        try:
            result = self.func(*args, **kwargs)
            if isinstance(result, dict):
                return {"status": "ok", "result": result}
            return {"status": "ok", "result": {"value": result}}
        except Exception as e:
            return {"status": "error", "error": str(e)}

# --- Mock results (fallback) ---
def _mock_results(query: str) -> Dict[str, Any]:
    time.sleep(0.2)
    return {
        "query": query,
        "hits": [
            {"title": "Quantum advances 2024", "snippet": "New technique stabilizes qubits."},
            {"title": "AI and quantum", "snippet": "Researchers explore hybrid models."}
        ],
        "source": "mock"
    }

# --- Google Custom Search JSON API adapter (fallback) ---
def _google_cse_search(query: str) -> Dict[str, Any]:
    api_key = os.environ.get("GOOGLE_API_KEY")
    cx = os.environ.get("GOOGLE_CX") or os.environ.get("CUSTOM_SEARCH_CX")
    if not api_key or not cx:
        return {"query": query, "hits": [], "source": "no_cse_config"}
    try:
        endpoint = "https://www.googleapis.com/customsearch/v1"
        params = {"key": api_key, "cx": cx, "q": query, "num": 5}
        resp = requests.get(endpoint, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        hits = []
        for item in data.get("items", [])[:5]:
            hits.append({"title": item.get("title"), "link": item.get("link"), "snippet": item.get("snippet")})
        return {"query": query, "hits": hits, "source": "google_cse"}
    except Exception as e:
        try:
            err_text = resp.text
        except Exception:
            err_text = str(e)
        return {"query": query, "hits": [], "error": f"{str(e)} | resp_text: {err_text}", "source": "error_fallback"}

# --- Retry helper for transient errors ---
def _with_retries(fn: Callable, attempts: int = 3, initial_backoff: float = 1.0, factor: float = 2.0):
    backoff = initial_backoff
    last_exc = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            logging.warning(f"[simple_search] attempt {i+1} failed: {e}; retrying after {backoff}s")
            time.sleep(backoff)
            backoff *= factor
    # if we exhaust attempts, re-raise the last exception
    raise last_exc

# --- GenAI web-search wrapper with graceful fallbacks ---
def _genai_web_search(query: str, retry_attempts: int = 3, backoff: float = 1.0) -> Dict[str, Any]:
    """
    Try the web-search tool (if SDK provides types). If the tool types are missing
    fallback to Google CSE (if configured), otherwise use a direct generate_content
    call (raw fallback). Returns dict with keys: query, hits, source, raw?, error?
    """
    # runtime import (avoid reliance on module-level import status)
    try:
        import google.generativeai as genai_runtime
    except Exception as e:
        return {"query": query, "hits": [], "error": f"genai_import_failed: {e}", "source": "genai_not_installed"}

    # require credentials (ADC or API key)
    if not (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GOOGLE_API_KEY")):
        return {"query": query, "hits": [], "error": "no_credentials", "source": "genai_no_creds"}

    # if API key present, configure (no-op when ADC used)
    try:
        if os.environ.get("GOOGLE_API_KEY"):
            genai_runtime.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    except Exception:
        # non-fatal
        pass

    # Attempt to use tool-based web-search types when available
    try:
        from google.generativeai.types import Tool as GenAITool, GoogleSearch as GenAIGoogleSearch

        model = genai_runtime.GenerativeModel("models/gemini-pro-latest")

        prompt = (
            f"Search the web for up-to-date findings about: {query}\n"
            "Return up to 5 concise search-style results: short title and one-line snippet per result."
        )

        def call_tool():
            # call generate_content via model (no explicit timeout param available in many SDK builds)
            return model.generate_content(contents=prompt, tools=[GenAITool(google_search=GenAIGoogleSearch())])

        # Use retry wrapper for transient network errors
        try:
            resp = _with_retries(call_tool, attempts=retry_attempts, initial_backoff=backoff)
        except Exception as e:
            return {"query": query, "hits": [], "error": f"genai_tool_failed: {e}", "source": "genai_error"}

        text = getattr(resp, "text", None) or str(resp)
        if not text:
            return {"query": query, "hits": [], "error": "empty_response", "source": "genai_empty", "raw": str(resp)}

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        hits = [{"title": ln[:80], "snippet": ln} for ln in lines[:5]]
        return {"query": query, "hits": hits, "source": "genai_search", "raw": text}

    except ImportError:
        # Tool types missing — attempt Google CSE if configured, else do a direct generate_content fallback
        api_key = os.environ.get("GOOGLE_API_KEY")
        cx = os.environ.get("GOOGLE_CX") or os.environ.get("CUSTOM_SEARCH_CX")
        if api_key and cx:
            try:
                return _google_cse_search(query)
            except Exception as e:
                return {"query": query, "hits": [], "error": f"cse_fallback_failed: {e}", "source": "cse_error"}

        # Direct generate_content fallback (not a true web-search tool — best effort)
        try:
            model = genai_runtime.GenerativeModel("models/gemini-pro-latest")
            prompt = (
                f"Provide an up-to-date summary of recent findings related to: {query}\n"
                "If you cannot access the live web, explicitly state that and provide the best plausible recent updates with a cautionary note."
            )

            def call_raw():
                return model.generate_content(contents=prompt)

            try:
                resp = _with_retries(call_raw, attempts=retry_attempts, initial_backoff=backoff)
            except Exception as e:
                return {"query": query, "hits": [], "error": f"genai_raw_failed: {e}", "source": "genai_error"}

            text = getattr(resp, "text", None) or str(resp)
            return {"query": query, "hits": [{"title": "Faiq's AI", "snippet": text[:400]}], "source": "genai_raw_fallback", "raw": text}
        except Exception as e2:
            return {"query": query, "hits": [], "error": f"genai_raw_failed: {e2}", "source": "genai_error"}
    except Exception as e:
        return {"query": query, "hits": [], "error": str(e), "source": "genai_error"}

# --- Top-level adapter: selects genai -> CSE -> mock with logging ---
def simple_search(query: str) -> Dict[str, Any]:
    """
    Robust top-level search adapter:
      1) Try genai (runtime): prefer tool-based web-search; fallback to CSE or direct genai.
      2) Try Google CSE if configured.
      3) Fallback to mock.
    """
    time.sleep(0.2)
    logging.info(f"[simple_search] called with query: {query!r}")

    # Try genai runtime first (call-time import)
    try:
        # quick check if runtime module importable
        import importlib
        try:
            importlib.import_module("google.generativeai")
            genai_runtime_available = True
        except Exception:
            genai_runtime_available = False

        if genai_runtime_available and (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GOOGLE_API_KEY")):
            logging.info("[simple_search] genai runtime available and credentials present -> calling _genai_web_search")
            resp = _genai_web_search(query)
            logging.info(f"[simple_search] genai resp source={resp.get('source')} hits={len(resp.get('hits', []))} error={resp.get('error', '')}")
            if resp.get("hits"):
                return resp
            if resp.get("raw"):
                # return raw as single hit so UI displays helpful text
                return {"query": query, "hits": [{"title": "Faiq's AI", "snippet": resp.get("raw")[:400]}], "source": resp.get("source"), "raw": resp.get("raw")}
    except Exception as e:
        logging.exception("[simple_search] unexpected error trying genai: %s", e)

    # Try Google Custom Search (CSE)
    api_key = os.environ.get("GOOGLE_API_KEY")
    cx = os.environ.get("GOOGLE_CX") or os.environ.get("CUSTOM_SEARCH_CX")
    if api_key and cx:
        logging.info("[simple_search] attempting Google Custom Search (CSE) fallback")
        try:
            resp = _google_cse_search(query)
            logging.info(f"[simple_search] cse resp source={resp.get('source')} hits={len(resp.get('hits', []))} error={resp.get('error', '')}")
            if resp.get("hits"):
                return resp
        except Exception as e:
            logging.exception("[simple_search] unexpected error calling CSE: %s", e)

    # Final fallback: mock
    logging.info(f"[simple_search] returning mock results for query: {query!r}")
    return _mock_results(query)
