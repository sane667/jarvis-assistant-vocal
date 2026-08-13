"""Filesystem-backed workspaces for Tony's Mode Projet and Holo graph."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json, re
from pathlib import Path
from typing import Any
from core.config import reglage


def _slug(value: str) -> str:
    value = value.strip().lower(); value = re.sub(r"[^a-z0-9à-ÿ]+", "-", value, flags=re.IGNORECASE)
    return value.strip("-") or "projet"

@dataclass
class Project:
    name: str; slug: str; path: str; description: str = ""; created_at: str = ""; updated_at: str = ""; active: bool = False
    nodes: list[dict[str, Any]] = field(default_factory=list); edges: list[dict[str, Any]] = field(default_factory=list)

class ProjectStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve(); self.root.mkdir(parents=True, exist_ok=True); self._active: str | None = None; self._load_active()
    @property
    def active(self):
        if not self._active: return None
        try: return self.open(self._active)
        except FileNotFoundError: self._active = None; return None
    @property
    def active_slug(self): return self._active
    def _active_file(self): return self.root / ".tony-active.json"
    def _load_active(self):
        try:
            slug = json.loads(self._active_file().read_text(encoding="utf-8")).get("slug")
            if slug and (self.root / _slug(slug)).is_dir(): self._active = _slug(slug)
        except (OSError, ValueError, TypeError): self._active = None
    def _save_active(self):
        if self._active: self._active_file().write_text(json.dumps({"slug": self._active}, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            try: self._active_file().unlink()
            except FileNotFoundError: pass
    def _project_dir(self, slug):
        target = (self.root / _slug(slug)).resolve(); target.relative_to(self.root); return target
    def _metadata_path(self, directory): return directory / ".tony" / "project.json"
    def _publish(self, project, message=""):
        try:
            import project_hud
            project_hud.demarrer(ouvrir=bool(reglage("projets.dashboard_auto_ouvrir", True))); project_hud.projet(project)
            if message: project_hud.activite(message)
        except Exception: pass

    def _refresh_graph(self, project: Project):
        """Rebuild graph nodes/edges from the real workspace; .tony remains metadata only."""
        root = Path(project.path).resolve(); root.relative_to(self.root)
        nodes = [{"id": project.slug, "label": project.name, "type": "project"}]; edges = []
        visible = []
        for path in sorted(root.rglob("*")):
            if path.name == ".tony" or ".tony" in path.parts or ".git" in path.parts: continue
            rel = path.relative_to(root).as_posix()
            if len(rel.split("/")) > 3: continue
            visible.append((path, rel))
        for path, rel in visible:
            node_id = f"{project.slug}:{rel}"
            node_type = "folder" if path.is_dir() else "file"
            nodes.append({"id": node_id, "label": path.name, "type": node_type, "path": rel})
            parent = path.parent
            parent_rel = parent.relative_to(root).as_posix() if parent != root else ""
            parent_id = project.slug if not parent_rel else f"{project.slug}:{parent_rel}"
            edges.append({"from": parent_id, "to": node_id, "type": "contains"})
        project.nodes, project.edges = nodes, edges; project.updated_at = datetime.now(timezone.utc).isoformat(); self._write(project); return project

    def create(self, name, description=""):
        name = name.strip()
        if not name: raise ValueError("Le nom du projet est obligatoire.")
        slug = _slug(name); directory = self._project_dir(slug)
        if directory.exists(): raise FileExistsError(f"Projet déjà existant : {name}")
        for child in ("docs", "src", "assets", "output", "logs"): (directory / child).mkdir(parents=True, exist_ok=True)
        (directory / ".tony").mkdir(parents=True, exist_ok=True); now = datetime.now(timezone.utc).isoformat()
        project = Project(name, slug, str(directory), description.strip(), now, now); self._refresh_graph(project); self._publish(project, f'Projet "{name}" créé.'); return project

    def open(self, slug):
        directory = self._project_dir(slug); metadata = self._metadata_path(directory)
        if not metadata.exists(): raise FileNotFoundError(f"Projet introuvable : {slug}")
        return Project(**json.loads(metadata.read_text(encoding="utf-8")))
    def activate(self, slug):
        project = self.open(slug)
        if self._active and self._active != project.slug:
            try: previous = self.open(self._active); previous.active = False; self._write(previous)
            except FileNotFoundError: pass
        self._active = project.slug; project.active = True; self._refresh_graph(project); self._save_active(); self._publish(project, f'Projet "{project.name}" activé.'); return project
    def deactivate(self):
        if not self._active: return
        try:
            project = self.open(self._active); project.active = False; self._write(project); self._publish(project, f'Projet "{project.name}" fermé.')
        finally:
            self._active = None; self._save_active()
            try: import project_hud; project_hud.projet(None)
            except Exception: pass
    def list(self):
        out=[]
        for d in sorted(self.root.iterdir()):
            if d.is_dir() and (d/".tony"/"project.json").exists():
                try: out.append(self.open(d.name))
                except (OSError, ValueError, TypeError): pass
        return out
    def refresh(self, project=None):
        project = project or self.active
        if project is None: return None
        project = self._refresh_graph(project)
        if project.active: self._publish(project)
        return project
    def add_node(self, project, node): project.nodes.append(node); self._write(project); self._publish(project) if project.active else None; return project
    def add_edge(self, project, edge): project.edges.append(edge); self._write(project); self._publish(project) if project.active else None; return project
    def _write(self, project):
        directory=Path(project.path).resolve(); directory.relative_to(self.root); metadata=self._metadata_path(directory); metadata.parent.mkdir(parents=True, exist_ok=True); metadata.write_text(json.dumps(asdict(project), ensure_ascii=False, indent=2), encoding="utf-8")

_ROOT=Path(__file__).resolve().parent.parent; _DEFAULT_ROOT=_ROOT/"projets"; _STORE=None
def store():
    global _STORE
    if _STORE is None: _STORE=ProjectStore(reglage("projets.racine", str(_DEFAULT_ROOT)))
    return _STORE

def creer_projet(nom, description=""):
    p=store().create(nom, description); return f'Projet "{p.name}" créé dans {p.path}.'
def ouvrir_projet(nom):
    p=store().activate(nom); return f'Projet "{p.name}" ouvert. Workspace : {p.path}'
def fermer_projet():
    p=store().active
    if p is None: return "Aucun projet n'est actuellement ouvert."
    n=p.name; store().deactivate(); return f'Projet "{n}" fermé.'
def lister_projets():
    ps=store().list()
    if not ps: return "Aucun projet n'est créé."
    a=store().active_slug; return "Projets : "+"; ".join(f'- {p.name}{" (actif)" if p.slug==a else ""}' for p in ps)
def projet_actif():
    p=store().active
    return "Aucun projet n'est actuellement ouvert." if p is None else f'Projet actif : "{p.name}" — {p.path}'
