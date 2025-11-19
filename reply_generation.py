"""Reply draft generation utilities."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from gmail_client import GmailMessage

try:
    import openai
except ImportError:  # pragma: no cover - optional dependency
    openai = None  # type: ignore

LOGGER = logging.getLogger(__name__)


@dataclass
class ReplyContext:
    """Minimal context describing an email to reply to."""

    subject: str
    sender: str
    snippet: str
    body_text: str


def _call_openai_api(prompt: str) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not openai:
        return None

    try:
        openai.api_key = api_key
        response = openai.ChatCompletion.create(  # type: ignore[attr-defined]
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful executive assistant. Provide concise, polite replies "
                        "that include a TL;DR sentence and, when helpful, a single clarifying question."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=240,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("OpenAI API call failed: %s", exc)
        return None


def _rule_based_reply(context: ReplyContext) -> str:
    greeting = f"Bonjour {context.sender.split('<')[0].strip() or 'à tous'},"
    tldr = f"TL;DR : {context.snippet or context.body_text[:140]}".strip()
    next_step = "N'hésite pas à me dire si tu as besoin d'informations supplémentaires."
    return f"{greeting}\n\n{tldr}\n\n{next_step}\n\nBien à vous,\n[Votre nom]"


def generate_reply(message: GmailMessage) -> str:
    """Generate a reply draft for a GmailMessage."""

    context = ReplyContext(
        subject=message.subject,
        sender=message.sender,
        snippet=message.snippet,
        body_text=message.body_text or message.snippet,
    )
    prompt = (
        "Email subject: {subject}\n"
        "From: {sender}\n"
        "Summary/snippet: {snippet}\n"
        "Body: {body}\n"
        "Compose a brief and polite reply in French, include a TL;DR sentence and one clarifying question "
        "if more information is required."
    ).format(
        subject=context.subject,
        sender=context.sender,
        snippet=context.snippet,
        body=context.body_text[:2000],
    )

    ai_reply = _call_openai_api(prompt)
    if ai_reply:
        return ai_reply

    return _rule_based_reply(context)
