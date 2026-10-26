import json
from datetime import datetime, timezone
from pathlib import Path
from .schemas import Event


class Trace:
    def __init__(self, path: Path, run_id: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path, self.run_id = path, run_id
        self.events: list[dict] = []
        # Never overwrite or silently append to a previous run.
        with path.open("x", encoding="utf-8"):
            pass

    def emit(self, sender: str, recipient: str, kind: str, payload):
        if hasattr(payload, "model_dump"):
            payload = payload.model_dump()
        number = len(self.events) + 1
        event = Event(run_id=self.run_id, message_id=f"m{number:04}", sequence=number,
                      timestamp=datetime.now(timezone.utc).isoformat(), sender=sender,
                      recipient=recipient, kind=kind, payload=payload).model_dump()
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")
            file.flush()
        self.events.append(event)
