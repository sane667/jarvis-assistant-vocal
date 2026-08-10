"""Brief : heure + meteo + deadlines + mails + Discord."""
from core.registre import get, outil
from tools.mail import _mail_configure, lire_mails
from tools.meteo import meteo
from tools.temps import heure_et_date


@outil(
    nom="faire_brief",
    description="Fait un briefing complet : heure/date, meteo, echeances Loopstr, "
                "nouveaux mails et mentions Discord. A utiliser quand l'utilisateur "
                "dit 'fais-moi un brief', 'quoi de neuf', 'ma journee'. Le resultat "
                "contient uniquement les donnees effectivement disponibles ; ne "
                "jamais inventer une donnee manquante.",
    parametres={
        "type": "object",
        "properties": {},
    },
    lent=True,
    phrase_attente="D'accord, je te prepare ton brief, un instant.",
)
def faire_brief(**_arguments) -> str:
    """Construit un briefing uniquement a partir de sources reelles.

    Les arguments parasites des LLM pour les outils sans parametres sont absorbes
    volontairement (par exemple {"": {}}).
    """
    morceaux = []

    # Heure/date et meteo sont des sources directes, jamais generees par le LLM.
    for nom, source in (("HEURE", heure_et_date), ("METEO", meteo)):
        try:
            resultat = source()
            if resultat:
                morceaux.append(f"{nom}: {resultat}")
        except Exception as e:
            morceaux.append(f"{nom}: indisponible ({e})")

    try:
        from tools.loopstr import deadlines_brief
        deadlines = deadlines_brief()
        if deadlines:
            morceaux.append(f"AGENDA/ECHEANCES: {deadlines}")
    except Exception:
        pass

    if _mail_configure():
        try:
            mails = lire_mails(5)
            morceaux.append(f"MAILS: {mails}")
        except Exception as e:
            morceaux.append(f"MAILS: indisponible ({e})")
    else:
        morceaux.append(
            "MAILS: MESSAGERIE_NON_CONFIGUREE — nombre de nouveaux mails inconnu. "
            "Ne donne aucun nombre de mails."
        )

    # On passe par le registre : le module Discord peut donc rester auto-decouvert
    # sans que brief.py connaisse son nom de fichier.
    try:
        outil_discord = get("get_mentions_summary")
        if outil_discord is not None:
            mentions = outil_discord.fonction()
            if mentions:
                morceaux.append(f"DISCORD_MENTIONS: {mentions}")
        else:
            morceaux.append("DISCORD_MENTIONS: outil indisponible")
    except Exception as e:
        morceaux.append(f"DISCORD_MENTIONS: indisponible ({e})")

    return "\n".join(morceaux) if morceaux else "Aucune donnee de briefing disponible."
