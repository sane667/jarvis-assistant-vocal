"""Provider-agnostic async manager for Tony's Elio/Lavanda/Clover agents."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Callable
from uuid import uuid4
import threading


STATUTS = {"queued", "running", "waiting_confirmation", "completed", "failed", "cancelled"}

# Backwards-compatible aliases for callers that still use the old vocabulary.
STATUS_ALIASES = {"success": "completed"}


@dataclass
class AgentTask:
    agent: str
    objectif: str
    workspace: str
    contexte: str = ""
    contraintes: list[str] = field(default_factory=list)
    critere_succes: str = ""
    deadline: str | None = None
    id: str = field(default_factory=lambda: f"task-{uuid4().hex[:12]}")
    status: str = "queued"
    message: str = ""
    result: Any = None
    progress: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    future: Future | None = field(default=None, repr=False, compare=False)
    cancel_event: threading.Event = field(default_factory=threading.Event, repr=False, compare=False)

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent": self.agent,
            "objectif": self.objectif,
            "workspace": self.workspace,
            "status": self.status,
            "message": self.message,
            "progress": self.progress,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": self.result if isinstance(self.result, (str, int, float, bool, type(None), list, dict)) else None,
        }


class AgentManager:
    """Small dependency-free async manager shared by all agents.

    Agent implementations are injected as callables. The manager never knows
    whether an agent uses NVIDIA, Ollama or another provider. Completion events
    are emitted without blocking the worker thread.
    """

    def __init__(self, max_workers: int = 3):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tony-agent")
        self._tasks: dict[str, AgentTask] = {}
        self._handlers: dict[str, Callable[[AgentTask], Any]] = {}
        self._listeners: list[Callable[[AgentTask], None]] = []
        self._lock = threading.RLock()

    def register(self, name: str, handler: Callable[[AgentTask], Any]) -> None:
        with self._lock:
            self._handlers[name.lower()] = handler

    def add_listener(self, listener: Callable[[AgentTask], None]) -> None:
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def _emit(self, task: AgentTask) -> None:
        with self._lock:
            listeners = tuple(self._listeners)
        for listener in listeners:
            try:
                listener(task)
            except Exception:
                pass

    def agents(self) -> list[str]:
        with self._lock:
            return sorted(self._handlers)

    def submit(
        self,
        agent: str,
        objectif: str,
        workspace: str,
        *,
        contexte: str = "",
        contraintes: list[str] | None = None,
        critere_succes: str = "",
        deadline: str | None = None,
    ) -> AgentTask:
        name = agent.lower().strip()
        with self._lock:
            if name not in self._handlers:
                raise ValueError(f"Agent inconnu : {agent}. Disponibles : {', '.join(self.agents()) or 'aucun'}")
            task = AgentTask(agent=name, objectif=objectif, workspace=workspace, contexte=contexte,
                             contraintes=contraintes or [], critere_succes=critere_succes, deadline=deadline)
            self._tasks[task.id] = task
            self._emit(task)
            task.future = self._executor.submit(self._run, task)
            return task

    def set_status(self, task: AgentTask, status: str, message: str = "") -> None:
        status = STATUS_ALIASES.get(status, status)
        if status not in STATUTS:
            raise ValueError(f"Statut agent invalide : {status}")
        with self._lock:
            task.status = status
            if message:
                task.message = message
        self._emit(task)

    def _run(self, task: AgentTask) -> None:
        with self._lock:
            if task.cancel_event.is_set():
                task.status = "cancelled"
                task.finished_at = datetime.now(timezone.utc).isoformat()
                self._emit(task)
                return
            task.status = "running"
            task.started_at = datetime.now(timezone.utc).isoformat()
        self._emit(task)
        try:
            result = self._handlers[task.agent](task)
            with self._lock:
                if task.cancel_event.is_set():
                    task.status = "cancelled"
                    task.message = "Tâche annulée."
                else:
                    task.result = result
                    task.status = "completed"
                    task.message = "Tâche terminée."
                task.finished_at = datetime.now(timezone.utc).isoformat()
            self._emit(task)
        except Exception as exc:
            with self._lock:
                task.status = "cancelled" if task.cancel_event.is_set() else "failed"
                task.message = f"{type(exc).__name__}: {exc}"
                task.finished_at = datetime.now(timezone.utc).isoformat()
            self._emit(task)

    def progress(self, task_id: str, message: str) -> None:
        task = self.get(task_id)
        if task:
            with self._lock:
                task.progress = message
            self._emit(task)

    def cancelled(self, task: AgentTask) -> bool:
        return task.cancel_event.is_set()

    def get(self, task_id: str) -> AgentTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    def list(self, status: str | None = None) -> list[AgentTask]:
        status = STATUS_ALIASES.get(status, status)
        with self._lock:
            values = list(self._tasks.values())
        return [task for task in values if status is None or task.status == status]

    def cancel(self, task_id: str) -> bool:
        task = self.get(task_id)
        if not task:
            return False
        task.cancel_event.set()
        if task.future and task.future.cancel():
            with self._lock:
                task.status = "cancelled"
                task.finished_at = datetime.now(timezone.utc).isoformat()
            self._emit(task)
        return True

    def shutdown(self, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=True)


_MANAGER: AgentManager | None = None


def manager() -> AgentManager:
    """Process-wide manager used by Tony tools and agent implementations."""
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = AgentManager(max_workers=3)
    return _MANAGER
