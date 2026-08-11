"""Elio: first autonomous coding-agent implementation.

Elio is deliberately workspace-scoped.  It can inspect/edit files and run a
small allow-list of development commands, then iterate with the configured LLM.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

from core.agent_manager import AgentTask
from core.llm import llm, Bloc


MAX_STEPS = 24
MAX_FILE_CHARS = 24000


def _safe_path(workspace: Path, relative: str) -> Path:
    candidate = (workspace / relative).resolve()
    candidate.relative_to(workspace.resolve())
    return candidate


def _list_files(workspace: Path, pattern: str = "") -> str:
    files = []
    for path in workspace.rglob("*"):
        if not path.is_file() or ".git" in path.parts or ".venv" in path.parts:
            continue
        rel = path.relative_to(workspace).as_posix()
        if not pattern or pattern.lower() in rel.lower():
            files.append(rel)
        if len(files) >= 250:
            break
    return "\n".join(files) or "Aucun fichier correspondant."


def _read_file(workspace: Path, path: str) -> str:
    target = _safe_path(workspace, path)
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > MAX_FILE_CHARS:
        text = text[:MAX_FILE_CHARS] + "\n...[fichier tronqué]"
    return text


def _write_file(workspace: Path, path: str, content: str) -> str:
    target = _safe_path(workspace, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Fichier écrit : {target.relative_to(workspace).as_posix()}"


def _run_command(workspace: Path, command: str) -> str:
    raw = command.strip()
    low = raw.lower()
    forbidden = ("git push", "git reset --hard", "git clean", "shutdown", "format ", "del /", "rmdir /s", "rm -rf")
    if any(x in low for x in forbidden):
        return "Commande refusée par la politique de sécurité de l'agent."
    allowed = (
        "python ", "python -m ", "pytest", "uv ", "ruff ", "mypy ",
        "npm ", "npx ", "node ", "git status", "git diff", "git log",
    )
    if not low.startswith(allowed):
        return "Commande refusée : utilise Python/pytest/uv/ruff/mypy/npm/node ou git en lecture."
    try:
        result = subprocess.run(
            raw,
            cwd=workspace,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
    except subprocess.TimeoutExpired:
        return "Commande interrompue : timeout de 90 secondes."
    output = ((result.stdout or "") + ("\n" + result.stderr if result.stderr else "")).strip()
    if len(output) > 16000:
        output = output[-16000:]
    return f"exit={result.returncode}\n{output}"


TOOLS = [
    {"name": "elio_lister_fichiers", "description": "Liste les fichiers du workspace.", "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}}},
    {"name": "elio_lire_fichier", "description": "Lit un fichier texte du workspace.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "elio_ecrire_fichier", "description": "Crée ou remplace un fichier texte dans le workspace.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "elio_executer", "description": "Exécute une commande de développement autorisée dans le workspace et retourne sa sortie.", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
]


def _execute(workspace: Path, name: str, args: dict) -> str:
    if name == "elio_lister_fichiers":
        return _list_files(workspace, args.get("pattern", ""))
    if name == "elio_lire_fichier":
        return _read_file(workspace, args["path"])
    if name == "elio_ecrire_fichier":
        return _write_file(workspace, args["path"], args["content"])
    if name == "elio_executer":
        return _run_command(workspace, args["command"])
    return f"Outil inconnu : {name}"


def run(task: AgentTask):
    workspace = Path(task.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    system = (
        "Tu es Elio, agent de développement de Tony. Tu travailles UNIQUEMENT dans le workspace fourni. "
        "Objectif : accomplir la tâche de code, pas seulement expliquer comment faire. "
        "Inspecte d'abord le projet, modifie les fichiers nécessaires, exécute des tests ou commandes de validation, "
        "corrige les erreurs puis vérifie à nouveau. Ne supprime pas massivement de fichiers. "
        "Ne fais jamais git push, git reset --hard, git clean ou commande destructive. "
        "Quand les critères de succès sont satisfaits, termine par un résumé très court."
    )
    history = [{"role": "user", "content": (
        f"Objectif : {task.objectif}\n"
        f"Contexte : {task.contexte or 'aucun'}\n"
        f"Critère de succès : {task.critere_succes or 'fonctionne comme demandé et les tests pertinents passent'}"
    )}]

    for step in range(MAX_STEPS):
        if task.cancel_event.is_set():
            return "Elio a été annulé."
        task.progress = f"Étape {step + 1}/{MAX_STEPS}"
        response = llm().repondre(system, history, TOOLS)
        tool_calls = [b for b in response.content if b.type == "tool_use"]
        texts = [b.text for b in response.content if b.type == "text" and b.text]

        if not tool_calls:
            return " ".join(texts).strip() or "Elio a terminé sans message final."

        assistant_blocks = response.content
        history.append({"role": "assistant", "content": assistant_blocks})
        results = []
        for call in tool_calls:
            try:
                value = _execute(workspace, call.name, call.input or {})
            except Exception as exc:
                value = f"Erreur outil : {type(exc).__name__}: {exc}"
            results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": value,
            })
        history.append({"role": "user", "content": results})

    return f"Elio a atteint la limite de {MAX_STEPS} étapes sans pouvoir conclure."


def register(manager):
    manager.register("elio", run)
