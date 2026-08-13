"""Lavanda: agent de recherche Internet autonome.

Lavanda reste dans son role : recherche web, collecte de sources et synthese.
Elle ne manipule jamais le filesystem de l'utilisateur.
"""
from __future__ import annotations

from core.agent_manager import AgentTask


def _search(query: str, max_results: int = 6):
    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise RuntimeError("Le moteur web ddgs n'est pas installe.") from exc

    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))


def run(task: AgentTask):
    query = (task.objectif or "").strip()
    if not query:
        return "Lavanda a besoin d'un sujet de recherche."

    task.progress = "Recherche des sources web"
    results = _search(query, 6)
    if not results:
        return f"Aucun resultat web trouve pour : {query}"

    lines = [f"Recherche Lavanda : {query}"]
    for i, item in enumerate(results, 1):
        title = item.get("title") or "Sans titre"
        url = item.get("href") or item.get("url") or ""
        body = (item.get("body") or item.get("snippet") or "").replace("\n", " ").strip()
        lines.append(f"{i}. {title}\n   {body}\n   {url}")
        task.progress = f"Sources collectees {i}/{len(results)}"
        if task.cancel_event.is_set():
            return "Lavanda a ete interrompue."

    return "\n".join(lines)


def register(manager):
    manager.register("lavanda", run)
