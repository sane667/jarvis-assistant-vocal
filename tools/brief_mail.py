"""Petite source dediee au briefing Gmail.

Le tool lire_mails liste les derniers messages, mais ne distingue pas les messages
non lus. Le briefing a besoin d'un compteur fiable de nouveaux/non-lus.
"""
import imaplib

from core.config import reglage


_SERVEUR = "imap.gmail.com"
_ADRESSE = reglage("mail.adresse", "")
_MDP = reglage("mail.mot_de_passe_app", "").replace(" ", "")


def compter_nouveaux_mails() -> int:
    """Retourne le nombre de messages non lus dans INBOX, ou leve une exception."""
    if not (_ADRESSE and _MDP):
        raise RuntimeError("messagerie non configuree")
    imap = imaplib.IMAP4_SSL(_SERVEUR)
    try:
        imap.login(_ADRESSE, _MDP)
        imap.select("INBOX", readonly=True)
        status, donnees = imap.uid("search", None, "UNSEEN")
        if status != "OK":
            raise RuntimeError("recherche Gmail UNSEEN impossible")
        return len((donnees[0] or b"").split())
    finally:
        try:
            imap.logout()
        except Exception:
            pass
