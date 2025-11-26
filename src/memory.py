# src/memory.py
import os
import json
import time
from typing import Any, Dict, List, Optional

class Session:
    """
    Simple conversation session container used by the UI.
    - session_id: string identifier
    - turns: list of dicts like {"role": "user"/"agent", "text": "...", "ts": 123456789}
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.turns: List[Dict[str, Any]] = []
        self.created_at = int(time.time())

    def add_turn(self, role: str, text: str):
        self.turns.append({
            "role": role,
            "text": text,
            "ts": int(time.time())
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "turns": self.turns
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Session":
        s = cls(d.get("session_id", f"session-{int(time.time())}"))
        s.created_at = d.get("created_at", s.created_at)
        s.turns = d.get("turns", [])
        return s

class MemoryStore:
    """
    Robust memory store:
    - Loads either a single JSON value, a JSON array, or a JSONL file.
    - Persists as a canonical JSON array.
    - Provides append() and find helpers.
    """
    def __init__(self, path: str):
        self.path = path
        self.store: List[Dict[str, Any]] = []
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            self.store = []
            return

        with open(self.path, "r", encoding="utf-8") as f:
            content = f.read()

        # Try parse as a single JSON value
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                self.store = parsed
            else:
                # single JSON object -> wrap in list
                self.store = [parsed]
            return
        except json.JSONDecodeError:
            # fallback: parse as JSON lines (one JSON object per line)
            items: List[Dict[str, Any]] = []
            for i, line in enumerate(content.splitlines(), start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    # skip invalid lines
                    continue
            self.store = items
            return

    def append(self, record: Dict[str, Any]):
        """
        Append a new record (dict) to memory and persist the canonical array.
        """
        self.store.append(record)
        self._persist()

    def _persist(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.store, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def find_last_by_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        for rec in reversed(self.store):
            if rec.get("session_id") == session_id:
                return rec
        return None

    def all_sessions(self) -> List[Dict[str, Any]]:
        return list(self.store)

    def clear(self):
        self.store = []
        self._persist()
