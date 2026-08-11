"""Filesystem-backed project workspaces for Tony Mode Projet.

The store is intentionally independent from the LLM and tool registry. A project
is a real directory; .tony/project.json only contains metadata and graph data.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9à-ÿ]+", "-", value, flags=re.IGNORECASE)
    return value.strip("-") or "projet"


@dataclass
class Project:
    name: str
    slug: str
    path: str
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    active: bool = False
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)


class ProjectStore:
    """Create/open/list projects while keeping all writes inside the root."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._active: str | None = None

    @property
    def active(self) -> Project | None:
        if not self._active:
            return None
        return self.open(self._active)

    def _project_dir(self, slug: str) -> Path:
        target = (self.root / _slug(slug)).resolve()
        target.relative_to(self.root)
        return target

    def _metadata_path(self, directory: Path) -> Path:
        return directory / ".tony" / "project.json"

    def create(self, name: str, description: str = "") -> Project:
        slug = _slug(name)
        directory = self._project_dir(slug)
        if directory.exists():
            raise FileExistsError(f"Projet déjà existant : {slug}")

        for child in ("docs", "src", "assets", "output", "logs"):
            (directory / child).mkdir(parents=True, exist_ok=True)
        metadata = directory / ".tony"
        metadata.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc).isoformat()
        project = Project(name=name.strip(), slug=slug, path=str(directory),
                          description=description.strip(), created_at=now,
                          updated_at=now, active=False)
        self._write(project)
        return project

    def open(self, slug: str) -> Project:
        directory = self._project_dir(slug)
        metadata = self._metadata_path(directory)
        if not metadata.exists():
            raise FileNotFoundError(f"Projet introuvable : {slug}")
        data = json.loads(metadata.read_text(encoding="utf-8"))
        return Project(**data)

    def activate(self, slug: str) -> Project:
        project = self.open(slug)
        self._active = project.slug
        project.active = True
        project.updated_at = datetime.now(timezone.utc).isoformat()
        self._write(project)
        return project

    def deactivate(self) -> None:
        if not self._active:
            return
        project = self.open(self._active)
        project.active = False
        self._write(project)
        self._active = None

    def list(self) -> list[Project]:
        projects: list[Project] = []
        for directory in sorted(self.root.iterdir()):
            if directory.is_dir() and (directory / ".tony" / "project.json").exists():
                projects.append(self.open(directory.name))
        return projects

    def add_node(self, project: Project, node: dict[str, Any]) -> Project:
        project.nodes.append(node)
        project.updated_at = datetime.now(timezone.utc).isoformat()
        self._write(project)
        return project

    def add_edge(self, project: Project, edge: dict[str, Any]) -> Project:
        project.edges.append(edge)
        project.updated_at = datetime.now(timezone.utc).isoformat()
        self._write(project)
        return project

    def _write(self, project: Project) -> None:
        directory = Path(project.path).resolve()
        directory.relative_to(self.root)
        metadata = self._metadata_path(directory)
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata.write_text(json.dumps(asdict(project), ensure_ascii=False, indent=2), encoding="utf-8")
