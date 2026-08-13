"""Smoke tests for the Mode Projet and agent contracts.

No LLM call and no real project is left behind: everything runs in a temporary
workspace and Elio is tested only for registration/contract availability.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from core.project_store import ProjectStore
from core.agent_manager import AgentManager
from agents.elio import register as register_elio
from agents.lavanda import register as register_lavanda
from agents.clover import register as register_clover


def main():
    with TemporaryDirectory(prefix="tony-project-test-") as tmp:
        store = ProjectStore(Path(tmp) / "projets")
        p = store.create("Holo", "Projet Tony")
        assert (Path(p.path) / "src").is_dir()
        assert (Path(p.path) / ".tony" / "project.json").is_file()
        store.activate("holo")
        assert store.active and store.active.slug == "holo"
        assert len(store.list()) == 1
        store.deactivate()
        assert store.active is None

    manager = AgentManager(max_workers=1)
    register_elio(manager)
    register_lavanda(manager)
    register_clover(manager)
    assert manager.agents() == ["clover", "elio", "lavanda"]
    manager.shutdown(wait=True)
    print("OK: ProjectStore + AgentManager + Elio/Lavanda/Clover contracts")


if __name__ == "__main__":
    main()
