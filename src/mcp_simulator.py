"""Simple MCP (Multi-Component Platform) simulator for long-running ops and human approvals."""
import time
import uuid

class LongRunningOperation:
    def __init__(self, description: str, duration_s: int = 2):
        self.id = str(uuid.uuid4())
        self.description = description
        self.duration_s = duration_s
        self.completed = False
        self.approved = False

    def start(self):
        print(f"Starting LRO {self.id}: {self.description}")
        # Simulate pause awaiting human approval
        return self.id

    def wait_for_approval(self, timeout: int = 300):
        # In real system, this would poll or subscribe to approval events.
        # Here we just simulate a short wait and auto-approve for demo.
        print("Waiting for approval (simulated)...")
        time.sleep(min(self.duration_s, 2))
        self.approved = True
        return self.approved

    def resume(self):
        if not self.approved:
            raise RuntimeError("Cannot resume: not approved")
        print("Resuming long-running operation (simulated work)")
        time.sleep(min(self.duration_s, 2))
        self.completed = True
        return {"status": "completed", "id": self.id}
