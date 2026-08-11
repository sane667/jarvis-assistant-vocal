"""Capture d'ecran : Tony capture une image reelle pour le provider vision."""
from core.registre import outil

LARGEUR_CAPTURE = 1568


@outil(
    nom="capture_screen",
    description=(
        "Capture l'ecran de l'utilisateur pour permettre a Tony de VOIR ce qui est "
        "affiche. A utiliser pour toute demande sur l'ecran, une erreur, une fenetre, "
        "un texte visible ou ce qui est actuellement affiche. Apres la capture, decris "
        "uniquement ce que tu observes dans l'image fournie par le modele vision."
    ),
    parametres={
        "type": "object",
        "properties": {
            "ecran": {
                "type": "integer",
                "description": "Ecran a capturer : 0 = principal, 1 = premier ecran, 2 = deuxieme.",
            }
        },
    },
    lent=True,
    phrase_attente="Je regarde ton ecran.",
)
def capture_screen(ecran: int = 0):
    """Capture un ecran et retourne une image JPEG base64."""
    try:
        import base64
        import io
        import mss
        from PIL import Image
    except ImportError:
        return "La capture d'ecran n'est pas installee (mss et Pillow)."

    try:
        try:
            ecran = int(ecran)
        except (TypeError, ValueError):
            return "Numero d'ecran invalide : utilise 0, 1, 2..."
        if ecran < 0:
            return "Numero d'ecran invalide : utilise 0, 1, 2..."

        with mss.mss() as sct:
            moniteurs = sct.monitors
            # mss: monitors[0] = bureau virtuel, monitors[1..N] = ecrans physiques.
            if ecran == 0:
                index = 1 if len(moniteurs) > 1 else 0
            else:
                index = ecran
            if index >= len(moniteurs):
                return f"Ecran {ecran} introuvable. {max(0, len(moniteurs) - 1)} ecran(s) physique(s) detecte(s)."
            cible = moniteurs[index]
            brut = sct.grab(cible)

        image = Image.frombytes("RGB", brut.size, brut.rgb)
        largeur, hauteur = image.size
        if largeur > LARGEUR_CAPTURE:
            ratio = LARGEUR_CAPTURE / largeur
            image = image.resize((LARGEUR_CAPTURE, max(1, round(hauteur * ratio))))

        tampon = io.BytesIO()
        image.save(tampon, format="JPEG", quality=82, optimize=True)
        b64 = base64.b64encode(tampon.getvalue()).decode("ascii")
        return {
            "image": {"media_type": "image/jpeg", "data": b64},
            "apercu": f"Capture ecran {ecran} ({image.size[0]}x{image.size[1]}).",
        }
    except Exception as e:
        return f"Impossible de capturer l'ecran : {e}"
