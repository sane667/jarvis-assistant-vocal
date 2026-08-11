"""Clover: agent fichiers local avec garde-fous stricts.

Clover ne supprime jamais de fichier. Les operations de rangement de masse sont
precedees d'une confirmation explicite du repertoire et les suppressions sont
redirigees vers ``a_supprimer`` afin de rester reversibles.
"""
from __future__ import annotations

from pathlib import Path
import re
import threading
from core.agent_manager import AgentTask

_LOCK = threading.RLock()
_PENDING: dict[str, dict] = {}

_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg", ".ico"}
_PDF_EXT = {".pdf"}
_DOC_EXT = {".doc", ".docx", ".odt", ".rtf", ".txt"}
_SHEET_EXT = {".xls", ".xlsx", ".ods", ".csv"}
_ARCHIVE_EXT = {".zip", ".rar", ".7z", ".tar", ".gz"}


def _safe_root(raw: str) -> Path:
    root = Path(raw).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Repertoire Clover invalide : {raw}")
    return root


def _safe_child(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    resolved.relative_to(root)
    return resolved


def request_confirmation(objectif: str, workspace: str, contexte: str = "") -> str:
    root = _safe_root(workspace)
    token = f"clover-{len(_PENDING) + 1}"
    with _LOCK:
        _PENDING[token] = {"objectif": objectif, "workspace": str(root), "contexte": contexte}
    return token


def pending(token: str | None = None):
    with _LOCK:
        if token:
            return _PENDING.get(token)
        return dict(_PENDING)


def consume(token: str) -> dict:
    with _LOCK:
        item = _PENDING.pop(token, None)
    if item is None:
        raise ValueError(f"Confirmation Clover inconnue : {token}")
    return item


def _category(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext in _PDF_EXT: return "PDF"
    if ext in _IMAGE_EXT: return "Images"
    if ext in _DOC_EXT: return "Documents"
    if ext in _SHEET_EXT: return "Tableurs"
    if ext in _ARCHIVE_EXT: return "Archives"
    return None


def _unique_destination(dest: Path) -> Path:
    if not dest.exists(): return dest
    stem, suffix = dest.stem, dest.suffix
    for i in range(2, 10000):
        candidate = dest.with_name(f"{stem}_{i}{suffix}")
        if not candidate.exists(): return candidate
    raise RuntimeError(f"Impossible de trouver un nom libre pour {dest.name}")


def _organize(root: Path, recursive: bool, task: AgentTask) -> str:
    files = []
    iterator = root.rglob("*") if recursive else root.iterdir()
    for p in iterator:
        if not p.is_file() or p.is_symlink(): continue
        try: p.relative_to(root)
        except ValueError: continue
        if "a_supprimer" in p.parts or ".clover" in p.parts: continue
        if _category(p): files.append(p)

    if not files:
        return "Aucun fichier PDF, image ou document correspondant n'a ete trouve. Rien n'a ete modifie."

    moved = []
    for i, src in enumerate(files, 1):
        if task.cancel_event.is_set():
            return f"Clover interrompue apres {len(moved)} deplacements."
        category = _category(src)
        if not category: continue
        dest_dir = root / category
        dest_dir.mkdir(exist_ok=True)
        dest = _unique_destination(dest_dir / src.name)
        _safe_child(root, dest)
        src_resolved = _safe_child(root, src)
        # Ne jamais ecraser un fichier existant et ne jamais supprimer.
        src_resolved.rename(dest)
        moved.append(f"{src.name} -> {category}/{dest.name}")
        task.progress = f"Rangement {i}/{len(files)}"

    return f"{len(moved)} fichier(s) range(s) sans suppression. " + "; ".join(moved[:12]) + (" ..." if len(moved) > 12 else "")


def _quarantine_requested(root: Path, task: AgentTask) -> str:
    """Pour une demande de suppression, deplace vers a_supprimer, jamais delete."""
    target = root / "a_supprimer"
    target.mkdir(exist_ok=True)
    return "Clover refuse toute suppression definitive. Les fichiers a supprimer doivent etre deplaces vers a_supprimer apres confirmation. La demande actuelle ne contient pas de liste de fichiers explicite, donc aucun fichier n'a ete deplace."


def run(task: AgentTask):
    root = _safe_root(task.workspace)
    objective = (task.objectif or "").lower()
    task.progress = f"Analyse securisee de {root}"

    if any(word in objective for word in ("supprime", "supprimer", "efface", "effacer", "delete")):
        return _quarantine_requested(root, task)

    recursive = any(word in objective for word in ("recursif", "récursif", "sous-dossier", "sous dossier", "partout"))
    return _organize(root, recursive, task)


def register(manager):
    manager.register("clover", run)
