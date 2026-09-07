"""One cooperative local analysis job for the browser UI."""

from copy import deepcopy
from datetime import datetime, timezone
from threading import Event, RLock, Thread

from modules.config import ConfigurationRequiredError
from modules.pipeline import Pipeline


class AnalysisJob:
    def __init__(self):
        self._lock = RLock()
        self._cancel = Event()
        self._state = {"status": "idle", "events": [], "result": None, "error": None}

    def status(self):
        with self._lock:
            return deepcopy(self._state)

    def start(self, config, modules):
        with self._lock:
            if self._state["status"] in {"running", "stopping"}:
                return None
            self._cancel = Event()
            effective = deepcopy(config)
            effective["modules"] = {**effective.get("modules", {}), **modules}
            self._state = {"status": "running", "events": [], "result": None, "error": None}
            self._event("start", "Analysis started.")
        Thread(target=self._run, args=(effective,), daemon=True).start()
        return self.status()

    def stop(self):
        with self._lock:
            if self._state["status"] != "running":
                state = deepcopy(self._state)
            else:
                self._state["status"] = "stopping"
                self._cancel.set()
                self._event("stopping", "Stop requested. Finishing the current safe checkpoint.")
                state = deepcopy(self._state)
        return state

    def _run(self, config):
        try:
            result = Pipeline(config_data=config, event_callback=self._event, cancel_event=self._cancel).run()
            with self._lock:
                self._state["status"] = result.get("status", "complete")
                self._state["result"] = result
        except ConfigurationRequiredError as error:
            self._fail(str(error))
        except Exception as error:  # Keep a local UI error concise; terminal retains traceback.
            self._fail(f"{type(error).__name__}: {error}")

    def _fail(self, message):
        with self._lock:
            self._state["status"] = "failed"
            self._state["error"] = message
            self._event("failed", message)

    def _event(self, stage, message):
        entry = {"stage": stage, "message": message, "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
        with self._lock:
            self._state.setdefault("events", []).append(entry)
            self._state["events"] = self._state["events"][-80:]
