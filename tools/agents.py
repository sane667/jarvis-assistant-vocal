"""Tony tools for delegating and supervising background agents."""
from core.registre import outil
from core.agent_manager import manager
from core.project_store import store


def _register_agents():
    from agents.elio import register as register_elio
    from agents.lavanda import register as register_lavanda
    from agents.clover import register as register_clover
    m = manager()
    register_elio(m)
    register_lavanda(m)
    register_clover(m)


_register_agents()


def _workspace(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    project = store().active
    if project is None:
        raise RuntimeError("Aucun projet actif. Ouvre un projet avant de déléguer une tâche.")
    return project.path


def _context_with_project(contexte: str) -> str:
    """Keep the active project's brief attached to every delegated task."""
    project = store().active
    if project is None:
        return contexte
    brief = project.description.strip()
    if not brief:
        return contexte
    prefix = f'Contexte durable du projet "{project.name}" : {brief}'
    return f"{prefix}\n{contexte}" if contexte.strip() else prefix


def _workspace_hint(agent: str) -> str:
    roles = {
        "elio": "Elio : développement, code, tests, débogage et architecture.",
        "lavanda": "Lavanda : recherche Internet, collecte de sources et synthèse web.",
        "clover": "Clover : fichiers locaux, PDF, images, documents et organisation bureautique.",
    }
    return roles.get(agent.lower(), "")


def _dashboard(task, message=""):
    try:
        import project_hud
        project_hud.agent(task)
        if message:
            project_hud.activite(message)
    except Exception:
        pass


@outil(
    "lancer_agent",
    (
        "Délègue une tâche longue à un agent spécialisé. Elio = code/tests/debug, "
        "Lavanda = Internet/recherche/sources, Clover = fichiers locaux/PDF/images/documents. "
        "Dans un projet actif, le brief du projet est automatiquement transmis à l'agent. "
        "Choisis l'agent correspondant réellement à la nature de la tâche et ne lance pas "
        "deux agents redondants sans raison."
    ),
    {"type": "object", "properties": {
        "agent": {"type": "string", "enum": ["elio", "lavanda", "clover"]},
        "objectif": {"type": "string", "description": "Travail précis à accomplir"},
        "contexte": {"type": "string", "description": "Contexte utile; le brief du projet actif est ajouté automatiquement"},
        "critere_succes": {"type": "string", "description": "Comment savoir que la tâche est terminée"},
        "workspace": {"type": "string", "description": "Dossier de travail facultatif"},
    }, "required": ["agent", "objectif"]},
    lent=False,
)
def lancer_agent(agent: str, objectif: str, contexte: str = "", critere_succes: str = "", workspace: str = ""):
    try:
        contexte_final = _context_with_project(contexte)
        role = _workspace_hint(agent)
        if role:
            contexte_final = f"{role}\n{contexte_final}" if contexte_final else role
        task = manager().submit(
            agent,
            objectif,
            _workspace(workspace or None),
            contexte=contexte_final,
            critere_succes=critere_succes,
        )
        _dashboard(task, f"{task.agent} lancé : {objectif}")
        return f"Tâche {task.id} confiée à {task.agent}. Elle continue en arrière-plan."
    except Exception as exc:
        return f"Impossible de lancer l'agent : {exc}"


@outil(
    "statut_agent",
    "Donne l'état d'une tâche déléguée ou des tâches en cours.",
    {"type": "object", "properties": {"task_id": {"type": "string", "description": "Identifiant de tâche facultatif"}}},
)
def statut_agent(task_id: str = ""):
    if task_id:
        task = manager().get(task_id)
        if task is None:
            return f"Tâche inconnue : {task_id}"
        _dashboard(task)
        return f"{task.id} — {task.agent} — {task.status}. {task.progress or task.message}"
    tasks = manager().list()
    if not tasks:
        return "Aucune tâche d'agent."
    for task in tasks[-8:]:
        _dashboard(task)
    return " ; ".join(f"{t.id} {t.agent}: {t.status}{' — ' + t.progress if t.progress else ''}" for t in tasks[-8:])


@outil(
    "annuler_agent",
    "Annule une tâche d'agent en cours quand l'utilisateur le demande.",
    {"type": "object", "properties": {"task_id": {"type": "string", "description": "Identifiant de tâche"}}, "required": ["task_id"]},
    confirmation=True,
)
def annuler_agent(task_id: str):
    if manager().cancel(task_id):
        task = manager().get(task_id)
        if task:
            _dashboard(task, f"Annulation demandée pour {task_id}.")
        return f"Annulation demandée pour {task_id}."
    return f"Tâche introuvable : {task_id}"
