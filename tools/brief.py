"""Brief : heure + meteo + echeances + mails + Discord."""
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

    # Le briefing distingue maintenant les nouveaux/non-lus des anciens mails.
    if _mail_configure():
        try:
            from tools.brief_mail import compter_nouveaux_mails
            nb = compter_nouveaux_mails()
            if nb == 0:
                morceaux.append("MAILS_NOUVEAUX: 0 — aucun nouveau mail non lu.")
            else:
                morceaux.append(f"MAILS_NOUVEAUX: {nb} — mails non lus.")
                try:
                    mails = lire_mails(min(nb, 5))
                    morceaux.append(f"MAILS_RECENTS: {mails}")
                except Exception:
                    pass
        except Exception as e:
            morceaux.append(f"MAILS_NOUVEAUX: indisponible ({e})")
    else:
        morceaux.append(
            "MAILS_NOUVEAUX: MESSAGERIE_NON_CONFIGUREE — nombre inconnu. "
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

    # Une ligne = une source de verite. Le modele doit reformuler toutes les lignes,
    # pas completer les informations manquantes de sa propre imagination.
    return "\n".join(morceaux) if morceaux else "Aucune donnee de briefing disponible."
