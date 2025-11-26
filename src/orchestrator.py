# src/orchestrator.py
import os
import json
import time
from typing import List

class Orchestrator:
    def __init__(self, agents: List = None, bus=None, memory_path: str = None, use_mock: bool = True):
        self.agents = agents or []
        self.bus = bus
        self.memory_path = memory_path
        self.use_mock = use_mock

    def run_pipeline(self, session_id: str, user_query: str) -> dict:
        # Find agents by role name
        research = next((a for a in self.agents if 'Research' in a.name), None)
        summarizer = next((a for a in self.agents if 'Summarizer' in a.name), None)
        critic = next((a for a in self.agents if 'Critic' in a.name), None)
        writer = next((a for a in self.agents if 'Writer' in a.name), None)

        results = {}
        # 1) Research
        findings = research.act(user_query) if research else {"content": ""}
        findings_text = findings.get("content", "") if isinstance(findings, dict) else str(findings)
        results["findings"] = findings_text

        # 2) Summarize
        summary = summarizer.act(findings_text) if summarizer else {"content": ""}
        summary_text = summary.get("content", "") if isinstance(summary, dict) else str(summary)
        results["summary"] = summary_text

        # 3) Critique
        critique = critic.act(summary_text) if critic else {"content": ""}
        critique_text = critique.get("content", "") if isinstance(critique, dict) else str(critique)
        results["critique"] = critique_text

        # 4) Write final draft (combine)
        combined = "\n\nFindings:\n" + findings_text + "\n\nSummary:\n" + summary_text + "\n\nCritique:\n" + critique_text
        draft = writer.act(combined) if writer else {"content": ""}
        draft_text = draft.get("content", "") if isinstance(draft, dict) else str(draft)
        results["final_draft"] = draft_text

        # Basic persistence: append to memory file (simple JSON lines)
        try:
            if self.memory_path:
                os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
                rec = {
                    "session_id": session_id,
                    "timestamp": int(time.time()),
                    "query": user_query,
                    "findings": findings_text,
                    "summary": summary_text,
                    "critique": critique_text,
                    "draft": draft_text
                }
                with open(self.memory_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception as e:
            print("[Orchestrator] memory write error:", e)

        return results
