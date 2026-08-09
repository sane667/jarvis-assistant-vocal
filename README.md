# 🤖 Jarvis — assistant vocal local

*[English version](README.en.md)*

![Python](https://img.shields.io/badge/python-3.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![Mode](https://img.shields.io/badge/mode-cloud%20%7C%20local%20%7C%20kimi-orange)

Un assistant vocal en français qui tourne **sur ta machine**. Dis *« Hey Jarvis »*,
parle naturellement : il raisonne avec un LLM, utilise une boîte à outils extensible
(domotique, PC, web, téléphone…) et te répond à voix haute. Trois modes sont disponibles :
**cloud** (Claude + ElevenLabs), **local** (Ollama + Piper) ou **kimi** (Kimi K2.6 via NVIDIA NIM + TTS local/cloud).

> Projet perso partagé tel quel. Cible **Windows 11**, nécessite un micro. La plupart des intégrations sont **optionnelles** et se désactivent proprement si non configurées.

## ✨ Fonctionnalités

- 🎙️ **Tout à la voix** — mot d'activation (openWakeWord), transcription locale (Whisper), réponses parlées
- 👁️ **Vision de l'écran** — « c'est quoi cette erreur ? », « lis ça », « traduis » (capture → LLM)
- 💡 **Domotique** — Philips Hue (allumer, luminosité, couleur), ambiances/scènes
- 🎬 **Streaming** — contrôle d'OBS (direct, enregistrement, scènes, replay)
- 🖥️ **Contrôle PC** — lancer des apps, média/volume, stats GPU/CPU/RAM en direct
- 📅 **Agenda** — Google Agenda sur **tous** tes agendas (y compris abonnés iCal), création/suppression avec confirmation
- 📧 **Mail** — résumés Gmail et rédaction
- 💬 **Discord** — mentions + récap des messages du jour
- 📸 **Instagram** — abonnés & vues des vidéos vs la veille (multi-comptes)
- 🍽️ **Réservations web** — réserve resto/rendez-vous via un vrai navigateur (Playwright)
- 🌐 **Assistant navigateur** — résume/traduit l'onglet actif, gère les onglets, agit sur les pages (ton vrai Chrome)
- 📞 **Appels téléphoniques** — Twilio : jouer un message, ou une vraie conversation temps réel
- 🧠 **Mémoire long terme** — retient tes préférences, tes proches, tes projets
- 🎭 **Personnalités** — majordome sarcastique, neutre, concis — changeable à la voix
- 🏠 **Présence** — ping ton téléphone, déclenche des scènes quand tu pars/reviens
- 🌤️ **Utilitaires** — météo, minuteurs, heure/date
- 🔌 **Serveur MCP** — expose les outils domotique/PC à tout client MCP (Claude Desktop, Hermes…)

## 🏗️ Architecture

```mermaid
flowchart LR
    Mic([🎙️ Micro]) --> WW[openWakeWord<br/>« Hey Jarvis »]
    WW --> STT[faster-whisper<br/>STT — local]
    STT --> LLM{{LLM<br/>Claude ☁️ OU Ollama 🏠 OU Kimi/NVIDIA ☁️}}
    LLM <-->|appels d'outils| TOOLS[🧰 Outils]
    LLM --> TTS{{TTS<br/>ElevenLabs ☁️ OU Piper 🏠}}
    TTS --> SPK([🔊 Haut-parleurs])

    TOOLS -.-> HOME[💡 Hue / 🎬 OBS / 🖥️ PC]
    TOOLS -.-> NET[📅 Agenda / 📧 Mail / 💬 Discord / 📸 Instagram]
    TOOLS -.-> CDP[🌐 Chrome via CDP]
    TOOLS -.-> TW[📞 Appels Twilio]
    TOOLS -.-> MCP[[🔌 Serveur MCP]]
    MCP -.-> EXT[Hermes Agent / Claude Desktop]
```

## ☁️ Cloud vs 🏠 Local vs ⚡ Kimi

| | **cloud** | **local** | **kimi** |
|---|---|---|---|
| LLM | Claude (API Anthropic) | Ollama (`qwen3.5:4b`…) | Kimi K2.6 (NVIDIA NIM) |
| Voix | ElevenLabs | Piper | Piper ou ElevenLabs |
| Transcription | faster-whisper (local) | faster-whisper (local) | faster-whisper (local) |
| Tools | ✅ | ✅ | ✅ |
| Vision | ✅ | selon modèle | ✅ |
| Coût | à l'usage | gratuit | selon quota NVIDIA |
| Vie privée | appels API | **rien ne sort de la machine** | appels API NVIDIA |

Bascule en une ligne : `mode: cloud`, `mode: local` ou `mode: kimi`.

Pour Kimi, configure `nvidia.modele: "moonshotai/kimi-k2.6"` et mets ta clé dans la variable d'environnement `NVIDIA_API_KEY` (recommandé), ou dans `nvidia.cle` de ton `config.yaml` local.

Kimi K2.6 utilise l'API OpenAI-compatible de NVIDIA et prend en charge les outils et les images. Le provider conserve le format interne de Jarvis afin que la boucle d'outils n'ait pas à connaître le fournisseur utilisé.

## 🚀 Démarrage rapide

Prérequis : **Python 3.13**, [uv](https://docs.astral.sh/uv/), Windows 11, un micro.

```bash
uv sync
uv run playwright install chromium
copy config.example.yaml config.yaml
```

Pour Kimi sous PowerShell :

```powershell
$env:NVIDIA_API_KEY = "ta_cle_NVIDIA"
uv run python scripts/test_nvidia.py
```

Le smoke test vérifie une réponse texte puis un tool call sans exécuter réellement d'outil.

Pour lancer Jarvis :

```bash
uv run python jarvis14.py
```

Dis **« Hey Jarvis »**.

## ⚙️ Configuration

Tout est dans un unique `config.yaml` **non versionné** (copié depuis
`config.example.yaml`, qui documente chaque clé). Guides par intégration :

| Intégration | Guide |
|---|---|
| Cloud vs local, Ollama, Piper | [docs/local.md](docs/local.md) |
| Philips Hue | [docs/hue.md](docs/hue.md) |
| OBS | [docs/obs.md](docs/obs.md) |
| Google Agenda + iCal | [docs/agenda.md](docs/agenda.md) |
| Détection de présence | [docs/presence.md](docs/presence.md) |
| Bot Discord | [docs/discord.md](docs/discord.md) |
| Appels Twilio | [docs/appels.md](docs/appels.md) |
| Navigateur (Chrome CDP) | [docs/navigateur.md](docs/navigateur.md) |
| Réservations web | [docs/reservation.md](docs/reservation.md) |
| Instagram | [docs/instagram.md](docs/instagram.md) |
| Serveur MCP | [docs/mcp.md](docs/mcp.md) |
| **Latence perçue (UX)** | [docs/latency.md](docs/latency.md) |

## 🛡️ Éthique & Sécurité

La confiance est intégrée, pas rajoutée :

- **Confirmation vocale** avant toute action irréversible (envoi de mail, réservation, suppression, appel…).
- **Les appels se présentent** honnêtement : *« Bonjour, je suis l'assistant vocal automatisé de [prénom]… »* — jamais en se faisant passer pour un humain.
- **Jamais** de mot de passe ni de données bancaires saisis, jamais de paiement automatique.
- **Domaines protégés** (banque, impôts, santé) sur ton vrai navigateur = **lecture seule**.
- **Secrets & données perso jamais versionnés** (`config.yaml`, mémoire, logs, transcriptions d'appels, tokens OAuth — tous gitignorés).
- Au téléphone, Jarvis ne confirme que ce que tu as validé **avant** l'appel.

## 🗺️ Roadmap

- [ ] Contrôle des lampes vidéo Godox (aujourd'hui Hue seulement)
- [ ] Outils notes & rappels
- [ ] TTS en streaming phrase par phrase (voir [docs/latency.md](docs/latency.md))
- [ ] Boucle navigateur en 100 % local : la vision de `qwen3.5` lit déjà le texte des boutons (testé) — reste à valider le pilotage complet
- [ ] Rafraîchissement auto des tokens Instagram entre redémarrages (partiel aujourd'hui)

## 🤝 Contribuer

Ajouter un outil = un seul fichier dans `tools/` avec un décorateur `@outil(...)` — il
est auto-découvert, aucun câblage. Merci de ne jamais committer de vrais secrets (vois
`.gitignore`).

## 📄 Licence

MIT — voir [LICENSE](LICENSE).
