"""Simple A2A (Agent-to-Agent) protocol simulator for demos."""
import uuid, time, queue, threading
from typing import Dict, Any

class A2AMessage:
    def __init__(self, sender: str, receiver: str, content: str):
        self.id = str(uuid.uuid4())
        self.sender = sender
        self.receiver = receiver
        self.content = content
        self.ts = time.time()

    def to_dict(self):
        return {'id': self.id, 'sender': self.sender, 'receiver': self.receiver, 'content': self.content, 'ts': self.ts}

class A2ABus:
    def __init__(self):
        self.queues = {}

    def register(self, agent_name: str):
        self.queues.setdefault(agent_name, queue.Queue())

    def send(self, msg: A2AMessage):
        if msg.receiver not in self.queues:
            raise KeyError(f"Receiver {msg.receiver} not registered")
        self.queues[msg.receiver].put(msg)

    def receive(self, agent_name: str, timeout: float = 0.1):
        q = self.queues.get(agent_name)
        if q is None:
            return None
        try:
            return q.get(timeout=timeout)
        except Exception:
            return None
