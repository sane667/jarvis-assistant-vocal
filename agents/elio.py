"""Elio: autonomous coding-agent implementation."""
from __future__ import annotations
from pathlib import Path
import subprocess
from core.agent_manager import AgentTask
from core.llm import llm

MAX_STEPS=24; MAX_FILE_CHARS=24000

def _safe_path(workspace, relative):
    candidate=(workspace/relative).resolve(); candidate.relative_to(workspace.resolve()); return candidate

def _list_files(workspace, pattern=""):
    files=[]
    for path in workspace.rglob("*"):
        if not path.is_file() or ".git" in path.parts or ".venv" in path.parts: continue
        rel=path.relative_to(workspace).as_posix()
        if not pattern or pattern.lower() in rel.lower(): files.append(rel)
        if len(files)>=250: break
    return "\n".join(files) or "Aucun fichier correspondant."

def _read_file(workspace,path):
    target=_safe_path(workspace,path); text=target.read_text(encoding="utf-8",errors="replace")
    return text[:MAX_FILE_CHARS]+("\n...[fichier tronqué]" if len(text)>MAX_FILE_CHARS else "")

def _write_file(workspace,path,content):
    target=_safe_path(workspace,path); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(content,encoding="utf-8")
    try:
        from core.project_store import store; store().refresh()
    except Exception: pass
    return f"Fichier écrit : {target.relative_to(workspace).as_posix()}"

def _run_command(workspace,command):
    raw=command.strip(); low=raw.lower(); forbidden=("git push","git reset --hard","git clean","shutdown","format ","del /","rmdir /s","rm -rf")
    if any(x in low for x in forbidden): return "Commande refusée par la politique de sécurité de l'agent."
    allowed=("python ","python -m ","pytest","uv ","ruff ","mypy ","npm ","npx ","node ","git status","git diff","git log")
    if not low.startswith(allowed): return "Commande refusée : utilise Python/pytest/uv/ruff/mypy/npm/node ou git en lecture."
    try: result=subprocess.run(raw,cwd=workspace,shell=True,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=90)
    except subprocess.TimeoutExpired: return "Commande interrompue : timeout de 90 secondes."
    output=((result.stdout or "")+("\n"+result.stderr if result.stderr else "")).strip(); output=output[-16000:] if len(output)>16000 else output
    return f"exit={result.returncode}\n{output}"

TOOLS=[
 {"name":"elio_lister_fichiers","description":"Liste les fichiers du workspace.","input_schema":{"type":"object","properties":{"pattern":{"type":"string"}}}},
 {"name":"elio_lire_fichier","description":"Lit un fichier texte du workspace.","input_schema":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}},
 {"name":"elio_ecrire_fichier","description":"Crée ou remplace un fichier texte dans le workspace.","input_schema":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}},
 {"name":"elio_executer","description":"Exécute une commande de développement autorisée dans le workspace.","input_schema":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}},
]

def _execute(workspace,name,args):
    if name=="elio_lister_fichiers": return _list_files(workspace,args.get("pattern",""))
    if name=="elio_lire_fichier": return _read_file(workspace,args["path"])
    if name=="elio_ecrire_fichier": return _write_file(workspace,args["path"],args["content"])
    if name=="elio_executer": return _run_command(workspace,args["command"])
    return f"Outil inconnu : {name}"

def _publish(task,message=""):
    try:
        import project_hud; project_hud.agent(task)
        if message: project_hud.activite(message)
    except Exception: pass

def run(task:AgentTask):
    workspace=Path(task.workspace).resolve(); workspace.mkdir(parents=True,exist_ok=True)
    system=("Tu es Elio, agent de développement de Tony. Tu travailles UNIQUEMENT dans le workspace fourni. "
            "Accomplis la tâche de code, inspecte d'abord le projet, modifie les fichiers nécessaires, exécute les tests, "
            "corrige les erreurs puis vérifie à nouveau. Ne supprime pas massivement de fichiers et ne fais jamais git push, "
            "git reset --hard, git clean ou commande destructive. Termine seulement quand le critère de succès est satisfait.")
    history=[{"role":"user","content":f"Objectif : {task.objectif}\nContexte : {task.contexte or 'aucun'}\nCritère de succès : {task.critere_succes or 'fonctionne comme demandé et les tests pertinents passent'}"}]
    for step in range(MAX_STEPS):
        if task.cancel_event.is_set(): task.status="cancelled"; task.message="Elio a été annulé."; _publish(task,task.message); return task.message
        task.progress=f"Étape {step+1}/{MAX_STEPS} · analyse et exécution"; _publish(task,f"Elio · {task.progress}")
        response=llm().repondre(system,history,TOOLS); calls=[b for b in response.content if b.type=="tool_use"]; texts=[b.text for b in response.content if b.type=="text" and b.text]
        if not calls:
            result=" ".join(texts).strip() or "Elio a terminé sans message final."; task.progress="Terminé"; _publish(task,result); return result
        history.append({"role":"assistant","content":response.content}); results=[]
        for call in calls:
            task.progress=f"Étape {step+1}/{MAX_STEPS} · {call.name}"; _publish(task,f"Elio utilise {call.name}")
            try: value=_execute(workspace,call.name,call.input or {})
            except Exception as exc: value=f"Erreur outil : {type(exc).__name__}: {exc}"
            results.append({"type":"tool_result","tool_use_id":call.id,"content":value})
        history.append({"role":"user","content":results})
    task.progress="Limite d'étapes atteinte"; _publish(task,task.progress); return f"Elio a atteint la limite de {MAX_STEPS} étapes sans pouvoir conclure."

def register(manager): manager.register("elio",run)
