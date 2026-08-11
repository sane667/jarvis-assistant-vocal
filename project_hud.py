"""Dashboard Holo du Mode Projet.

Petit serveur local independant du HUD vocal : il affiche le graphe du projet,
les agents en cours et leur progression via SSE. Aucune dependance externe.
"""
from __future__ import annotations

import json
import queue
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8771
_HTML = Path(__file__).parent / "project.html"
_CLIENTS: set[queue.Queue] = set()
_LOCK = threading.Lock()
_SERVER = None
_STATE = {
    "project": None,
    "agents": {},
}


def _send(event):
    raw = json.dumps(event, ensure_ascii=False)
    with _LOCK:
        for client in list(_CLIENTS):
            try:
                client.put_nowait(raw)
            except queue.Full:
                _CLIENTS.discard(client)


def demarrer(ouvrir=False):
    global _SERVER
    if _SERVER is not None:
        return _SERVER
    _SERVER = ThreadingHTTPServer(("127.0.0.1", PORT), _Handler)
    _SERVER.daemon_threads = True
    threading.Thread(target=_SERVER.serve_forever, daemon=True).start()
    print(f"Holo Mode Projet sur http://127.0.0.1:{PORT}/")
    if ouvrir:
        try:
            webbrowser.open(f"http://127.0.0.1:{PORT}/")
        except Exception:
            pass
    return _SERVER


def projet(project=None):
    """Publie l'etat complet d'un projet au dashboard."""
    demarrer(False)
    if project is None:
        _STATE["project"] = None
        _send({"t": "project", "project": None})
        return
    if hasattr(project, "__dict__"):
        data = {
            "name": project.name,
            "slug": project.slug,
            "path": project.path,
            "description": project.description,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "active": project.active,
            "nodes": project.nodes,
            "edges": project.edges,
        }
    else:
        data = project
    _STATE["project"] = data
    _send({"t": "project", "project": data})


def agent(task):
    """Publie l'etat d'une tache agent."""
    demarrer(False)
    data = task.public() if hasattr(task, "public") else dict(task)
    _STATE["agents"][data["id"]] = data
    _send({"t": "agent", "agent": data})


def activite(message, niveau="info"):
    demarrer(False)
    _send({"t": "activity", "message": str(message), "level": niveau})


def image_gen(path, prompt):
    demarrer(False)
    _send({"t": "image", "path": str(path), "prompt": str(prompt)})


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html", "/project.html"):
            try:
                body = _HTML.read_bytes()
            except OSError:
                self.send_error(500, "project.html introuvable")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/flux":
            self._flux()
        else:
            self.send_error(404)

    def _flux(self):
        client = queue.Queue(maxsize=300)
        with _LOCK:
            _CLIENTS.add(client)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            self._write({"t": "project", "project": _STATE["project"]})
            for item in _STATE["agents"].values():
                self._write({"t": "agent", "agent": item})
            while True:
                try:
                    self._write(json.loads(client.get(timeout=15)))
                except queue.Empty:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _LOCK:
                _CLIENTS.discard(client)

    def _write(self, event):
        raw = json.dumps(event, ensure_ascii=False)
        self.wfile.write(b"data: " + raw.encode("utf-8") + b"\n\n")
        self.wfile.flush()
