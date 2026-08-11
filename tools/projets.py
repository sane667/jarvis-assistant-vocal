"""Tools for Tony's Mode Projet.

These are intentionally simple and deterministic.  They are the bridge between
natural-language intent and the filesystem-backed ProjectStore.
"""
from core.registre import outil
from core.project_store import (
    creer_projet as _creer_projet,
    ouvrir_projet as _ouvrir_projet,
    fermer_projet as _fermer_projet,
    lister_projets as _lister_projets,
    projet_actif as _projet_actif,
)


@outil(
    "creer_projet",
    "Crée un nouveau projet avec un workspace local. À utiliser quand l'utilisateur demande de créer un projet, et non une application.",
    {"type": "object", "properties": {
        "nom": {"type": "string", "description": "Nom du projet"},
        "description": {"type": "string", "description": "Description facultative du projet"},
    }, "required": ["nom"]},
    lent=False,
)
def creer_projet(nom: str, description: str = ""):
    return _creer_projet(nom, description)


@outil(
    "ouvrir_projet",
    "Ouvre et active un projet existant pour les prochaines actions de Tony et de ses agents.",
    {"type": "object", "properties": {
        "nom": {"type": "string", "description": "Nom du projet"},
    }, "required": ["nom"]},
)
def ouvrir_projet(nom: str):
    return _ouvrir_projet(nom)


@outil(
    "fermer_projet",
    "Ferme le projet actif sans supprimer ses fichiers.",
    {"type": "object", "properties": {}},
)
def fermer_projet():
    return _fermer_projet()


@outil(
    "lister_projets",
    "Liste les projets locaux de Tony et indique le projet actif.",
    {"type": "object", "properties": {}},
)
def lister_projets():
    return _lister_projets()


@outil(
    "projet_actif",
    "Indique quel projet est actuellement ouvert et où se trouve son workspace.",
    {"type": "object", "properties": {}},
)
def projet_actif():
    return _projet_actif()
