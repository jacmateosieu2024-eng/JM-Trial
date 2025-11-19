"""Streamlit app for Gmail triage."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

import streamlit as st
from dateutil import tz

from gmail_client import GmailClient, GmailMessage
from reply_generation import generate_reply

LOG_PATH = Path("logs/mail_triage.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
LOGGER = logging.getLogger(__name__)

CLIENT = GmailClient()
ACTION_WORDS = ["urgent", "deadline", "action", "répond", "reply", "due", "please", "asap"]
NEWSLETTER_PATTERNS = ["unsubscribe", "newsletter", "no-reply", "noreply", "bulletin"]


def score_message(message: GmailMessage) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []

    if message.unread:
        score += 25
        reasons.append("Non lu")
    if "no-reply" not in message.sender.lower() and "noreply" not in message.sender.lower():
        score += 15
        reasons.append("Expéditeur humain")
    text_blob = f"{message.subject} {message.snippet} {message.body_text}".lower()
    if "?" in message.subject or any(word in text_blob for word in ACTION_WORDS):
        score += 10
        reasons.append("Contient une question ou action")
    if message.subject.lower().startswith("re:") and message.thread_size > 2:
        score += 10
        reasons.append("Long fil 'Re:'")
    if message.starred or message.important:
        score += 15
        reasons.append("Marqué important")
    if (datetime.now(tz.UTC) - message.date).total_seconds() < 48 * 3600:
        score += 10
        reasons.append("Récent (<48h)")
    if message.cc_only:
        score -= 10
        reasons.append("Uniquement en copie")
    if any(pattern in text_blob for pattern in NEWSLETTER_PATTERNS):
        score -= 20
        reasons.append("Newsletter présumée")

    return max(0, min(100, score)), reasons


@st.cache_data(show_spinner=False)
def load_messages(days: int = 14) -> List[GmailMessage]:
    LOGGER.info("Fetching Gmail messages for the last %s days", days)
    return CLIENT.fetch_recent_messages(days=days)


def ensure_state_defaults() -> None:
    if "must_reply" not in st.session_state:
        st.session_state["must_reply"] = set()


def filter_messages(
    messages: List[Tuple[GmailMessage, int, List[str]]],
    start_date: datetime,
    end_date: datetime,
    unread_only: bool,
    min_score: int,
    search_term: str,
) -> List[Tuple[GmailMessage, int, List[str]]]:
    filtered = []
    search_term = search_term.lower()
    for message, score, reasons in messages:
        naive_date = message.date.astimezone(tz.UTC).replace(tzinfo=None)
        if not (start_date <= naive_date <= end_date):
            continue
        if unread_only and not message.unread:
            continue
        if score < min_score:
            continue
        if search_term:
            haystack = f"{message.subject} {message.sender} {message.snippet}".lower()
            if search_term not in haystack:
                continue
        filtered.append((message, score, reasons))
    return filtered


def render_message_card(message: GmailMessage, score: int, reasons: List[str]) -> None:
    ensure_state_defaults()
    must_reply: set = st.session_state["must_reply"]

    with st.container(border=True):
        cols = st.columns([3, 2, 2, 1])
        with cols[0]:
            st.subheader(message.subject)
            st.caption(message.sender)
        with cols[1]:
            local_dt = message.date.astimezone(tz.tzlocal())
            st.write(local_dt.strftime("%d %b %Y %H:%M"))
            st.caption(", ".join(message.labels))
        with cols[2]:
            st.metric("Score", score)
            st.caption(", ".join(reasons) or "")
        with cols[3]:
            st.write(" ")
            must_reply_label = "✅ Doit répondre" if message.id in must_reply else "Marquer must-reply"
            if st.button(must_reply_label, key=f"must_{message.id}"):
                if message.id in must_reply:
                    must_reply.remove(message.id)
                else:
                    must_reply.add(message.id)
                st.session_state["must_reply"] = must_reply

        st.write(message.snippet)

        with st.expander("📬 Ouvrir l'e-mail"):
            st.write(message.body_text or "(Pas de texte)")

        reply_key = f"reply_{message.id}"
        if st.button("✍️ Générer une réponse", key=f"gen_{message.id}"):
            st.session_state[reply_key] = generate_reply(message)
        current_reply = st.session_state.get(reply_key, "")
        st.text_area("Brouillon de réponse", value=current_reply, key=reply_key, height=180)

        if CLIENT.compose_enabled:
            if st.button("💾 Enregistrer en brouillon Gmail", key=f"draft_{message.id}"):
                try:
                    draft_id = CLIENT.create_draft(message, st.session_state.get(reply_key, ""))
                    st.success(f"Brouillon enregistré (ID: {draft_id})")
                except RuntimeError as exc:
                    st.error(str(exc))
        else:
            st.caption("Activez la portée gmail.compose pour sauvegarder un brouillon.")


def render_bulk_mode(messages: List[Tuple[GmailMessage, int, List[str]]], count: int) -> None:
    st.subheader("Mode bulk : réponses suggérées")
    top_messages = sorted(messages, key=lambda item: item[1], reverse=True)[:count]
    for message, score, reasons in top_messages:
        with st.expander(f"{message.subject} — score {score}"):
            reply_text = generate_reply(message)
            st.text_area("Proposition de réponse", value=reply_text, height=180, key=f"bulk_{message.id}")
            st.caption(", ".join(reasons))


def main() -> None:
    st.set_page_config(page_title="Mail Triage App", layout="wide")
    st.title("📧 Mail Triage App")
    st.caption("Analyse et priorisation intelligente de votre boîte de réception Gmail.")

    ensure_state_defaults()

    with st.sidebar:
        st.header("Filtres")
        refresh = st.button("🔄 Rafraîchir")
        try:
            if refresh:
                load_messages.clear()
            messages = load_messages(days=14)
        except RuntimeError as exc:
            st.error(str(exc))
            st.stop()

        if not messages:
            st.warning("Aucun e-mail trouvé dans les 14 derniers jours.")
            return

        dates = [msg.date for msg in messages]
        min_date = min(dates).date()
        max_date = max(dates).date()
        date_range = st.date_input(
            "Plage de dates",
            value=(max_date - timedelta(days=14), max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(date_range, tuple):
            start_date, end_date = date_range
        else:
            start_date = date_range
            end_date = date_range
        unread_only = st.checkbox("Seulement non lus", value=False)
        min_score = st.slider("Score minimum", 0, 100, 40)
        search_term = st.text_input("Recherche")
        sort_option = st.selectbox("Trier par", ["score", "date"], index=0)
        bulk_count = st.number_input("Mode bulk: top N", min_value=1, max_value=20, value=3)

    scored_messages = [(msg, *score_message(msg)) for msg in messages]

    filtered = filter_messages(
        scored_messages,
        start_date=datetime.combine(start_date, datetime.min.time()),
        end_date=datetime.combine(end_date, datetime.max.time()),
        unread_only=unread_only,
        min_score=min_score,
        search_term=search_term,
    )

    if sort_option == "score":
        filtered.sort(key=lambda item: item[1], reverse=True)
    else:
        filtered.sort(key=lambda item: item[0].date, reverse=True)

    st.write(f"{len(filtered)} e-mails correspondent aux filtres.")

    for message, score, reasons in filtered:
        render_message_card(message, score, reasons)

    st.divider()
    render_bulk_mode(filtered, count=int(bulk_count))


if __name__ == "__main__":
    main()
