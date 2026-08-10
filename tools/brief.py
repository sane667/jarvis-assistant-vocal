"""Brief : heure + meteo + apercu des derniers mails, en un seul outil."""
from core.registre import outil
from tools.mail import _mail_configure, lire_mails
from tools.meteo import meteo
from tools.temps import heure_et_date


@outil(
    nom="faire_brief",
    description="Fait un brief : l'heure, la meteo et un apercu des derniers mails. "
                "A utiliser quand l'utilisateur dit 'fais-moi un brief', 'quoi de "
                "neuf', 'ma journee'. Apres le brief, propose de lire, repondre ou "
                "jeter un mail.",
    parametres={
        "type": "object",
        "properties": {},
    },
    lent=True,
    phrase_attente="D'accord, je te prepare ton brief, un instant.",
)
def faire_brief(**_arguments) -> str:
    """Brief du moment.

    Accepte volontairement d'eventuels arguments parasites emis par certains LLM
    pour un outil sans parametres (par exemple {"": {}}). Un briefing ne doit
    jamais echouer uniquement a cause de la forme du tool call.
    """
    morceaux = []

    # Chaque source est independante : une panne de meteo, mails ou deadlines
    # ne doit pas transformer tout le briefing en echec.
    for source in (heure_et_date, meteo):
        try:
            resultat = source()
            if resultat:
                morceaux.append(str(resultat))
        except Exception as e:
            morceaux.append(f"Source indisponible : {e}")

    try:
        from tools.loopstr import deadlines_brief
        deadlines = deadlines_brief()
        if deadlines:
            morceaux.append(str(deadlines))
    except Exception:
        pass

    if _mail_configure():
        try:
            morceaux.append(str(lire_mails(5)))
        except Exception as e:
            morceaux.append(f"Lecture des mails indisponible : {e}")
    else:
        # Important : on donne explicitement au LLM l'etat de la source au lieu
        # de le laisser inventer un nombre de mails.
        morceaux.append("La messagerie n'est pas configuree : aucun nombre de nouveaux mails disponible.")

    return " ".join(morceaux) if morceaux else "Aucune donnee de briefing disponible." 
