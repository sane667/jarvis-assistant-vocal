"""Abstraction du modele de langage : le reste du code ignore quel provider tourne.

Providers disponibles via config.yaml :
  - ClaudeProvider : API Anthropic (cloud).
  - OllamaProvider : Ollama en local (http://localhost:11434), 100% offline.
  - NvidiaProvider : modeles NVIDIA NIM via API OpenAI-compatible.

Les trois exposent la meme methode `repondre(systeme, historique, outils)` et
renvoient un objet a la forme d'une reponse Anthropic (.stop_reason + .content,
chaque bloc ayant .type / .text / .name / .input / .id). Ainsi la boucle de
dialogue et les outils de Jarvis restent independants du provider.

L'historique interne reste au format "content blocks" d'Anthropic. Les providers
OpenAI-compatible (Ollama et NVIDIA) effectuent leur traduction en interne.
"""
import json
import logging
import os

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from core.config import reglage

LOG = logging.getLogger("jarvis")


class Bloc:
    """Imite un bloc de contenu Anthropic (text ou tool_use)."""

    def __init__(self, type, text=None, id=None, name=None, input=None):
        self.type = type
        self.text = text
        self.id = id
        self.name = name
        self.input = input


class Reponse:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


class ProviderLLM:
    nom = "?"

    def disponible(self):
        return True

    def repondre(self, systeme, historique, outils):
        raise NotImplementedError


class ClaudeProvider(ProviderLLM):
    nom = "Claude"

    def __init__(self):
        import anthropic
        cle = reglage("anthropic.cle", "")
        self.modele = reglage("anthropic.modele", "claude-haiku-4-5")
        self.client = anthropic.Anthropic(api_key=cle) if cle else None

    def disponible(self):
        return self.client is not None

    def repondre(self, systeme, historique, outils):
        return self.client.messages.create(
            model=self.modele,
            max_tokens=1024,
            system=[{"type": "text", "text": systeme,
                     "cache_control": {"type": "ephemeral"}}],
            messages=historique,
            tools=outils,
        )


class _OpenAICompatibleMixin:
    """Traductions communes aux APIs OpenAI-compatible."""

    def _traduire(self, systeme, historique, vision=True):
        messages = [{"role": "system", "content": systeme}]

        for m in historique:
            role = m.get("role")
            contenu = m.get("content")

            if role == "user":
                if isinstance(contenu, str):
                    messages.append({"role": "user", "content": contenu})
                    continue

                blocks = contenu or []
                text_parts = []
                image_parts = []
                tool_results = []

                for item in blocks:
                    if not isinstance(item, dict):
                        continue
                    typ = item.get("type")
                    if typ == "text":
                        text_parts.append(item.get("text", ""))
                    elif typ == "image":
                        if vision:
                            part = self._image_part(item)
                            if part:
                                image_parts.append(part)
                    elif typ == "tool_result":
                        tool_results.append(item)

                for result in tool_results:
                    value = result.get("content", "")
                    if isinstance(value, list):
                        value = " ".join(
                            str(x.get("text", "")) for x in value
                            if isinstance(x, dict) and x.get("type") == "text"
                        )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": result.get("tool_use_id", ""),
                        "content": str(value),
                    })

                if text_parts or image_parts:
                    if image_parts:
                        content = []
                        if text_parts:
                            content.append({"type": "text", "text": " ".join(text_parts)})
                        content.extend(image_parts)
                    else:
                        content = " ".join(text_parts)
                    messages.append({"role": "user", "content": content})

            elif role == "assistant":
                if isinstance(contenu, str):
                    messages.append({"role": "assistant", "content": contenu})
                    continue

                text = " ".join(
                    b.text for b in (contenu or [])
                    if getattr(b, "type", None) == "text" and b.text
                ).strip()
                appels = [
                    b for b in (contenu or [])
                    if getattr(b, "type", None) == "tool_use"
                ]
                msg = {"role": "assistant", "content": text or None}
                if appels:
                    msg["tool_calls"] = [
                        {
                            "id": b.id or f"call_{i}",
                            "type": "function",
                            "function": {
                                "name": b.name,
                                "arguments": json.dumps(b.input or {}, ensure_ascii=False),
                            },
                        }
                        for i, b in enumerate(appels)
                    ]
                messages.append(msg)

        return messages

    @staticmethod
    def _image_part(item):
        source = item.get("source") or {}
        media_type = source.get("media_type") or "image/png"
        data = source.get("data")
        if data:
            return {
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{data}"},
            }
        url = source.get("url") or item.get("url")
        if url:
            return {"type": "image_url", "image_url": {"url": url}}
        return None

    @staticmethod
    def _outils(outils):
        return [
            {
                "type": "function",
                "function": {
                    "name": o["name"],
                    "description": o["description"],
                    "parameters": o.get(
                        "input_schema",
                        {"type": "object", "properties": {}},
                    ),
                },
            }
            for o in outils
        ]

    @staticmethod
    def _parser(rep):
        choices = getattr(rep, "choices", None) or []
        if not choices:
            raise RuntimeError("Reponse LLM vide")

        msg = choices[0].message
        blocs = []
        texte = (getattr(msg, "content", None) or "").strip()
        if texte:
            blocs.append(Bloc("text", text=texte))

        for tc in getattr(msg, "tool_calls", None) or []:
            fn = getattr(tc, "function", None)
            if fn is None:
                continue
            args = getattr(fn, "arguments", {}) or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError as e:
                    raise RuntimeError(f"Arguments d'outil invalides : {e}") from e
            blocs.append(
                Bloc(
                    "tool_use",
                    id=getattr(tc, "id", None),
                    name=getattr(fn, "name", None),
                    input=args or {},
                )
            )

        finish = getattr(choices[0], "finish_reason", None)
        stop = "tool_use" if any(b.type == "tool_use" for b in blocs) else finish or "end"
        return Reponse(stop, blocs)


class OllamaProvider(_OpenAICompatibleMixin, ProviderLLM):
    nom = "Ollama"

    def __init__(self):
        self.hote = reglage("ollama.hote", "http://localhost:11434").rstrip("/")
        self.modele = reglage("ollama.modele", "qwen3.5:4b")

    def disponible(self):
        try:
            import requests
            requests.get(f"{self.hote}/api/version", timeout=3)
            return True
        except Exception:
            return False

    def _traduire_ollama(self, systeme, historique):
        messages = [{"role": "system", "content": systeme}]
        for m in historique:
            role, contenu = m.get("role"), m.get("content")
            if role == "user":
                if isinstance(contenu, str):
                    messages.append({"role": "user", "content": contenu})
                else:
                    for item in contenu or []:
                        if not isinstance(item, dict):
                            continue
                        if item.get("type") == "tool_result":
                            c = item.get("content")
                            if isinstance(c, list):
                                c = "[image capturee — la vision n'est pas disponible en mode local]"
                            messages.append({"role": "tool", "content": str(c)})
                        elif item.get("type") == "image":
                            messages.append({"role": "user", "content": "[image — vision indisponible en local]"})
            else:
                if isinstance(contenu, str):
                    messages.append({"role": "assistant", "content": contenu})
                else:
                    texte = " ".join(
                        b.text for b in (contenu or [])
                        if getattr(b, "type", None) == "text" and b.text
                    )
                    appels = [b for b in (contenu or []) if getattr(b, "type", None) == "tool_use"]
                    msg = {"role": "assistant", "content": texte}
                    if appels:
                        msg["tool_calls"] = [
                            {
                                "id": b.id or f"call_{i}",
                                "type": "function",
                                "function": {
                                    "name": b.name,
                                    "arguments": b.input or {},
                                },
                            }
                            for i, b in enumerate(appels)
                        ]
                    messages.append(msg)
        return messages

    def _chat(self, messages, tools, nudge=None):
        import requests
        if nudge:
            messages = messages + [{"role": "user", "content": nudge}]
        r = requests.post(
            f"{self.hote}/api/chat",
            timeout=120,
            json={
                "model": self.modele,
                "messages": messages,
                "tools": tools,
                "stream": False,
                "think": bool(reglage("ollama.think", False)),
                "options": {"temperature": 0.3},
            },
        )
        r.raise_for_status()
        return r.json()

    def _parser_ollama(self, rep):
        msg = rep.get("message", {}) or {}
        blocs = []
        texte = (msg.get("content") or "").strip()
        if texte:
            blocs.append(Bloc("text", text=texte))
        for i, tc in enumerate(msg.get("tool_calls") or []):
            fn = tc.get("function", {}) or {}
            args = fn.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            blocs.append(
                Bloc(
                    "tool_use",
                    id=tc.get("id") or f"call_{i}",
                    name=fn.get("name"),
                    input=args or {},
                )
            )
        stop = "tool_use" if any(b.type == "tool_use" for b in blocs) else "end"
        return Reponse(stop, blocs)

    def repondre(self, systeme, historique, outils):
        messages = self._traduire_ollama(systeme, historique)
        tools = self._outils(outils)
        try:
            return self._parser_ollama(self._chat(messages, tools))
        except Exception as e:
            LOG.warning("ollama: 1er essai en echec (%s), retry plus directif", e)
            nudge = (
                "Rappel : pour agir, appelle l'outil approprie via un tool call "
                "avec des arguments JSON valides ; sinon reponds simplement en texte."
            )
            try:
                return self._parser_ollama(self._chat(messages, tools, nudge=nudge))
            except Exception:
                LOG.exception("ollama: echec apres retry")
                return Reponse(
                    "end",
                    [Bloc("text", text=(
                        "Desole, le modele local n'a pas reussi a traiter la demande "
                        "correctement. Reessaie en reformulant, ou repasse en mode cloud."
                    ))],
                )


class NvidiaProvider(_OpenAICompatibleMixin, ProviderLLM):
    """Modeles NVIDIA NIM via l'API OpenAI-compatible.

    Par defaut, Tony utilise openai/gpt-oss-120b. Le modele est configurable
    pour pouvoir tester d'autres modeles NVIDIA sans changer le code.
    """

    nom = "NVIDIA"

    def __init__(self):
        from openai import OpenAI

        cle = os.getenv("NVIDIA_API_KEY") or reglage("nvidia.cle", "")
        self.modele = reglage("nvidia.modele", "openai/gpt-oss-120b")
        self.base_url = reglage(
            "nvidia.base_url",
            "https://integrate.api.nvidia.com/v1",
        ).rstrip("/")
        self.reasoning_effort = reglage("nvidia.reasoning_effort", "low")
        self.max_tokens = int(reglage("nvidia.max_tokens", 2048))
        self.temperature = float(reglage("nvidia.temperature", 0.3))
        self.client = (
            OpenAI(api_key=cle, base_url=self.base_url, timeout=120.0)
            if cle
            else None
        )

    def disponible(self):
        return self.client is not None

    def _chat(self, messages, tools):
        kwargs = {
            "model": self.modele,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }

        # NVIDIA attend tools/tool_choice uniquement quand des tools sont
        # fournis. Cela evite les erreurs de function references sur les requetes
        # texte simples.
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # GPT-OSS supporte officiellement reasoning_effort via Chat Completions.
        # On n'envoie la valeur que si elle est explicitement configuree.
        if self.modele.startswith("openai/gpt-oss") and self.reasoning_effort:
            kwargs["reasoning_effort"] = self.reasoning_effort

        return self.client.chat.completions.create(**kwargs)

    def repondre(self, systeme, historique, outils):
        if not self.client:
            return Reponse(
                "end",
                [Bloc("text", text=(
                    "NVIDIA n'est pas configure. Definis NVIDIA_API_KEY dans "
                    "l'environnement ou nvidia.cle dans config.yaml."
                ))],
            )

        messages = self._traduire(systeme, historique, vision=True)
        tools = self._outils(outils)
        try:
            return self._parser(self._chat(messages, tools))
        except Exception as e:
            LOG.exception("nvidia: appel NVIDIA echoue")
            return Reponse(
                "end",
                [Bloc("text", text=f"Erreur NVIDIA : {e}")],
            )


_LLM = None


def llm():
    """Provider LLM courant (mode: cloud | local | nvidia)."""
    global _LLM
    if _LLM is None:
        mode = (reglage("mode", "cloud") or "cloud").lower()
        if mode == "local":
            _LLM = OllamaProvider()
        elif mode == "nvidia":
            _LLM = NvidiaProvider()
        else:
            _LLM = ClaudeProvider()
        LOG.info("provider LLM : %s (mode %s)", _LLM.nom, mode)
    return _LLM
