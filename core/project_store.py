"""Filesystem-backed workspaces for Tony's Mode Projet."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from core.config import reglage


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
    """Manage projects while keeping all writes inside the configured root."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._active: str | None = None
        self._load_active()

    @property
    def active(self) -> Project | None:
        if not self._active:
            return None
        try:
            return self.open(self._active)
        except FileNotFoundError:
            self._active = None
            return None

    @property
    def active_slug(self) -> str | None:
        return self._active

    def _active_file(self) -> Path:
        return self.root / ".tony-active.json"

    def _load_active(self) -> None:
        try:
            data = json.loads(self._active_file().read_text(encoding="utf-8"))
            slug = data.get("slug")
            if slug and (self.root / _slug(slug)).is_dir():
                self._active = _slug(slug)
        except (OSError, ValueError, TypeError):
            self._active = None

    def _save_active(self) -> None:
        if self._active:
            self._active_file().write_text(
                json.dumps({"slug": self._active}, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            try:
                self._active_file().unlink()
            except FileNotFoundError:
                pass

    def _project_dir(self, slug: str) -> Path:
        target = (self.root / _slug(slug)).resolve()
        target.relative_to(self.root)
        return target

    def _metadata_path(self, directory: Path) -> Path:
        return directory / ".tony" / "project.json"

    def _publish(self, project: Project | None, message: str = "") -> None:
        try:
            import project_hud
            project_hud.projet(project)
            if message:
                project_hud.activite(message)
        except Exception:
            pass

    def create(self, name: str, description: str = "") -> Project:
        name = name.strip()
        if not name:
            raise ValueError("Le nom du projet est obligatoire.")
        slug = _slug(name)
        directory = self._project_dir(slug)
        if directory.exists():
            raise FileExistsError(f"Projet déjà existant : {name}")
        for child in ("docs", "src", "assets", "output", "logs"):
            (directory / child).mkdir(parents=True, exist_ok=True)
        (directory / ".tony").mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        project = Project(name=name, slug=slug, path=str(directory),
                          description=description.strip(), created_at=now, updated_at=now)
        project.nodes.append({"id": slug, "label": name, "type": "project"})
        self._write(project)
        self._publish(project, f'Projet "{name}" créé.')
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
        if self._active and self._active != project.slug:
            try:
                previous = self.open(self._active)
                previous.active = False
                self._write(previous)
            except FileNotFoundError:
                pass
        self._active = project.slug
        project.active = True
        project.updated_at = datetime.now(timezone.utc).isoformat()
        self._write(project)
        self._save_active()
        self._publish(project, f'Projet "{project.name}" activé.')
        return project

    def deactivate(self) -> None:
        if not self._active:
            return
        try:
            project = self.open(self._active)
            project.active = False
            self._write(project)
            self._publish(project, f'Projet "{project.name}" fermé.')
        finally:
            self._active = None
            self._save_active()
            try:
                import project_hud
                project_hud.projet(None)
            except Exception:
                pass

    def list(self) -> list[Project]:
        projects: list[Project] = []
        for directory in sorted(self.root.iterdir()):
            if directory.is_dir() and (directory / ".tony" / "project.json").exists():
                try:
                    projects.append(self.open(directory.name))
                except (OSError, ValueError, TypeError):
                    continue
        return projects

    def add_node(self, project: Project, node: dict[str, Any]) -> Project:
        project.nodes.append(node)
        project.updated_at = datetime.now(timezone.utc).isoformat()
        self._write(project)
        if project.active:
            self._publish(project)
        return project

    def add_edge(self, project: Project, edge: dict[str, Any]) -> Project:
        project.edges.append(edge)
        project.updated_at = datetime.now(timezone.utc).isoformat()
        self._write(project)
        if project.active:
            self._publish(project)
        return project

    def _write(self, project: Project) -> None:
        directory = Path(project.path).resolve()
        directory.relative_to(self.root)
        metadata = self._metadata_path(directory)
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata.write_text(json.dumps(asdict(project), ensure_ascii=False, indent=2), encoding="utf-8")


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ROOT = _ROOT / "projets"
_STORE: ProjectStore | None = None


def store() -> ProjectStore:
    global _STORE
    if _STORE is None:
        _STORE = ProjectStore(reglage("projets.racine", str(_DEFAULT_ROOT)))
    return _STORE


def creer_projet(nom: str, description: str = "") -> str:
    project = store().create(nom, description)
    return f'Projet "{project.name}" créé dans {project.path}.'


def ouvrir_projet(nom: str) -> str:
    project = store().activate(nom)
    return f'Projet "{project.name}" ouvert. Workspace : {project.path}'


def fermer_projet() -> str:
    project = store().active
    if project is None:
        return "Aucun projet n'est actuellement ouvert."
    name = project.name
    store().deactivate()
    return f'Projet "{name}" fermé.'


def lister_projets() -> str:
    projects = store().list()
    if not projects:
        return "Aucun projet n'est créé."
    active = store().active_slug
    lignes = [f'- {p.name}{" (actif)" if p.slug == active else ""}' for p in projects]
    return "Projets : " + "; ".join(lignes)


def projet_actif() -> str:
    project = store().active
    if project is None:
        return "Aucun projet n'est actuellement ouvert."
    return f'Projet actif : "{project.name}" — {project.path}'
