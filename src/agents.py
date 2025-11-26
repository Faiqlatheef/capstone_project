# src/agents.py
import os
import time
from typing import Dict

# Optional: use google-generativeai if available
GENAI_AVAILABLE = False
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except Exception:
    GENAI_AVAILABLE = False

class BaseAgent:
    def __init__(self, name: str, tools: dict = None, use_mock: bool = True):
        self.name = name
        self.tools = tools or {}
        self.use_mock = use_mock
        self.client = None
        if GENAI_AVAILABLE and not self.use_mock:
            # We'll create GenerativeModel on demand to avoid heavy init
            pass

    def act(self, message: str, session=None) -> Dict[str, str]:
        raise NotImplementedError("act must be implemented by subclasses")

class ResearchAgent(BaseAgent):
    def act(self, message: str, session=None):
        query = message or ""
        # LOG what this agent received
        print(f"[ResearchAgent.act] received message: {query!r}")
        try:
            import logging, os
            logdir = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
            os.makedirs(logdir, exist_ok=True)
            with open(os.path.join(logdir, "agent_debug.log"), "a", encoding="utf-8") as fh:
                fh.write(f"{int(time.time())} RESEARCH_ACT received: {query!r}\n")
        except Exception:
            pass

        # Use search tool if provided and not mock
        if not self.use_mock and "search" in self.tools:
            try:
                resp = self.tools["search"].call(query)
                print(f"[ResearchAgent.act] tool returned status={resp.get('status')} result_source={resp.get('result', {}).get('source') if isinstance(resp.get('result'), dict) else None}")
                if resp.get("status") == "ok":
                    result = resp["result"]
                    hits = result.get("hits", [])
                    if hits:
                        findings = [f"{h.get('title','')} - {h.get('snippet','')}" for h in hits]
                        content = "\n".join(findings)
                        return {"role": self.name, "type": "findings", "content": content}
                    # If result included an error field, surface it for debugging
                    if result.get("error"):
                        return {"role": self.name, "type": "findings", "content": f"[search-error] {result.get('error')}"}
            except Exception as e:
                print(f"[ResearchAgent] search tool error: {e}")

        # LLM fallback if available & not mock (short retrieval)
        if not self.use_mock and GENAI_AVAILABLE:
            try:
                model_name = os.environ.get("GENAI_MODEL", "models/gemini-pro-latest")
                model = genai.GenerativeModel(model_name)
                prompt = f"Retrieve concise findings for: {query}\nProvide 3 bullet points (title - snippet)."
                resp = model.generate_content(contents=prompt)
                text = getattr(resp, "text", None) or str(resp)
                return {"role": self.name, "type": "findings", "content": text}
            except Exception as e:
                print("[ResearchAgent] genai LLM error:", e)

        # Mock fallback
        mock_findings = [
            "Found paper: Quantum Supremacy 2024 - improved qubit stability technique.",
            "News: Qubit coherence improvement announced by University X."
        ]
        return {"role": self.name, "type": "findings", "content": "\n".join(mock_findings)}

class SummarizerAgent(BaseAgent):
    def act(self, message: str, session=None):
        text = message or ""
        if not self.use_mock and GENAI_AVAILABLE:
            try:
                model_name = os.environ.get("GENAI_MODEL", "models/gemini-pro-latest")
                model = genai.GenerativeModel(model_name)
                prompt = f"Summarize the following findings in 3 clear bullets:\n\n{text}"
                resp = model.generate_content(contents=prompt)
                text_out = getattr(resp, "text", None) or str(resp)
                return {"role": self.name, "type": "summary", "content": text_out}
            except Exception as e:
                print("[SummarizerAgent] genai error:", e)

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        bullets = lines[:3] if lines else ["No findings to summarize."]
        summary = "Summary: " + " | ".join(bullets)
        return {"role": self.name, "type": "summary", "content": summary}

class CriticAgent(BaseAgent):
    def act(self, message: str, session=None):
        text = message or ""
        if not self.use_mock and GENAI_AVAILABLE:
            try:
                model_name = os.environ.get("GENAI_MODEL", "models/gemini-pro-latest")
                model = genai.GenerativeModel(model_name)
                prompt = f"Critically evaluate for factuality and gaps:\n\n{text}"
                resp = model.generate_content(contents=prompt)
                text_out = getattr(resp, "text", None) or str(resp)
                return {"role": self.name, "type": "critique", "content": text_out}
            except Exception as e:
                print("[CriticAgent] genai error:", e)

        critique = "Critique: Verify claims and add citations for key statements."
        return {"role": self.name, "type": "critique", "content": critique}

class WriterAgent(BaseAgent):
    def act(self, message: str, session=None):
        text = message or ""
        if not self.use_mock and GENAI_AVAILABLE:
            try:
                model_name = os.environ.get("GENAI_MODEL", "models/gemini-pro-latest")
                model = genai.GenerativeModel(model_name)
                prompt = f"Write a concise technical brief using the following input:\n\n{text}"
                resp = model.generate_content(contents=prompt)
                text_out = getattr(resp, "text", None) or str(resp)
                return {"role": self.name, "type": "draft", "content": text_out}
            except Exception as e:
                print("[WriterAgent] genai error:", e)

        draft = "Draft Brief:\n\n" + (text[:2000] + ("..." if len(text) > 2000 else ""))
        return {"role": self.name, "type": "draft", "content": draft}
