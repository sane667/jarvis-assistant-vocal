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
    """Construit un briefing uniquement a partir de donnees effectivement lues.

    Le **_arguments absorbe les arguments parasites des LLM pour les outils sans
    parametres (par exemple {"": {}}), afin que ce cas ne fasse pas echouer l'outil.
    Le LLM ne doit ensuite que reformuler le resultat : il ne doit pas inventer
    de compteurs absents.
    """
    morceaux = []

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
        morceaux.append(
            "MESSAGERIE_NON_CONFIGUREE : le nombre de nouveaux mails est inconnu. "
            "Ne donne aucun nombre de mails."
        )

    # Discord n'est ajoute que si une source Discord reelle existe dans le projet.
    # Ne jamais demander au LLM de deduire/inventer un nombre de mentions.
    try:
        from tools.notifications import discord_brief
        discord = discord_brief()
        if discord:
            morceaux.append(str(discord))
    except (ImportError, AttributeError):
        pass
    except Exception as e:
        morceaux.append(f"Discord indisponible : {e}")

    return " ".join(morceaux) if morceaux else "Aucune donnee de briefing disponible."
