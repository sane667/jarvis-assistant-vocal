"""Provider-agnostic foundation for Tony's future Elio/Lavanda/Clover agents."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Callable
from uuid import uuid4


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
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    future: Future | None = field(default=None, repr=False, compare=False)


class AgentManager:
    """Small, dependency-free async manager.

    Agent implementations are injected as callables. This keeps the manager
    independent from Claude/Ollama/NVIDIA and lets Elio/Lavanda/Clover share it.
    """

    def __init__(self, max_workers: int = 3):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tony-agent")
        self._tasks: dict[str, AgentTask] = {}
        self._handlers: dict[str, Callable[[AgentTask], Any]] = {}

    def register(self, name: str, handler: Callable[[AgentTask], Any]) -> None:
        self._handlers[name.lower()] = handler

    def submit(self, agent: str, objectif: str, workspace: str, *,
               contexte: str = "", contraintes: list[str] | None = None,
               critere_succes: str = "", deadline: str | None = None) -> AgentTask:
        name = agent.lower()
        if name not in self._handlers:
            raise ValueError(f"Agent inconnu : {agent}")
        task = AgentTask(agent=name, objectif=objectif, workspace=workspace,
                         contexte=contexte, contraintes=contraintes or [],
                         critere_succes=critere_succes, deadline=deadline)
        self._tasks[task.id] = task
        task.future = self._executor.submit(self._run, task)
        return task

    def _run(self, task: AgentTask) -> None:
        task.status = "running"
        try:
            task.result = self._handlers[task.agent](task)
            task.status = "success"
            task.message = "Tâche terminée."
        except Exception as exc:
            task.status = "failed"
            task.message = f"{type(exc).__name__}: {exc}"

    def get(self, task_id: str) -> AgentTask | None:
        return self._tasks.get(task_id)

    def list(self, status: str | None = None) -> list[AgentTask]:
        values = list(self._tasks.values())
        return [task for task in values if status is None or task.status == status]

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or not task.future:
            return False
        cancelled = task.future.cancel()
        if cancelled:
            task.status = "cancelled"
        return cancelled

    def shutdown(self, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=True)
