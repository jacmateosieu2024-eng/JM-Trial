"""Gmail API client helpers for the mail triage Streamlit app."""
from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


LOGGER = logging.getLogger(__name__)
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]


@dataclass
class GmailMessage:
    """Lightweight representation of a Gmail message."""

    id: str
    thread_id: str
    subject: str
    sender: str
    date: datetime
    snippet: str
    labels: List[str]
    unread: bool
    starred: bool
    important: bool
    thread_size: int
    body_text: str
    body_html: str
    to: str
    cc: str
    cc_only: bool


class GmailClient:
    """Thin wrapper around the Gmail API for the Streamlit app."""

    def __init__(
        self,
        credentials_path: str = "credentials.json",
        token_path: str = "token.json",
        scopes: Optional[List[str]] = None,
    ) -> None:
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.scopes = scopes or DEFAULT_SCOPES
        self.service = None
        self.compose_enabled = "https://www.googleapis.com/auth/gmail.compose" in self.scopes

    def authenticate(self) -> None:
        """Authenticate and cache the Gmail API service."""

        if self.service is not None:
            return

        creds: Optional[Credentials] = None
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Unable to read token.json: %s", exc)

        if not creds or not creds.valid:
            try:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.scopes
                    )
                    creds = flow.run_local_server(port=0)
            except FileNotFoundError as exc:
                raise RuntimeError(
                    "credentials.json is missing. Follow the README to configure OAuth."
                ) from exc
            except RefreshError as exc:
                LOGGER.error("Token refresh failed: %s", exc)
                raise RuntimeError("Failed to refresh OAuth token. Re-run the login flow.") from exc

            if creds:
                with open(self.token_path, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())

        self.service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    def fetch_recent_messages(self, days: int = 14) -> List[GmailMessage]:
        """Fetch messages in the INBOX received within the last `days` days."""

        self.authenticate()
        assert self.service is not None  # for mypy

        after = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
        query = f"after:{after}"
        messages: List[Dict[str, str]] = []
        page_token: Optional[str] = None

        try:
            while True:
                response = (
                    self.service.users()
                    .messages()
                    .list(
                        userId="me",
                        labelIds=["INBOX"],
                        q=query,
                        pageToken=page_token,
                        maxResults=100,
                    )
                    .execute()
                )
                messages.extend(response.get("messages", []))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
        except HttpError as exc:
            LOGGER.error("Failed to list messages: %s", exc)
            raise RuntimeError("Unable to reach Gmail. Check your connection and scopes.") from exc

        hydrated: List[GmailMessage] = []
        for message in messages:
            detailed = self._hydrate_message(message.get("id"))
            if detailed:
                hydrated.append(detailed)

        hydrated.sort(key=lambda msg: msg.date, reverse=True)
        return hydrated

    def _hydrate_message(self, message_id: Optional[str]) -> Optional[GmailMessage]:
        if not message_id:
            return None
        assert self.service is not None

        try:
            response = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
        except HttpError as exc:
            LOGGER.warning("Failed to load message %s: %s", message_id, exc)
            return None

        headers = {h["name"].lower(): h["value"] for h in response.get("payload", {}).get("headers", [])}
        subject = headers.get("subject", "(Sans objet)")
        sender = headers.get("from", "")
        date_str = headers.get("date")
        parsed_date = date_parser.parse(date_str) if date_str else datetime.now(timezone.utc)
        parsed_date = parsed_date.astimezone(timezone.utc)
        labels = response.get("labelIds", [])
        unread = "UNREAD" in labels
        starred = "STARRED" in labels
        important = "IMPORTANT" in labels or "CATEGORY_PERSONAL" in labels
        snippet = response.get("snippet", "")
        body_text, body_html = self._extract_bodies(response.get("payload", {}))
        to_header = headers.get("to", "")
        cc_header = headers.get("cc", "")
        cc_only = bool(cc_header and not to_header)
        thread_size = self._fetch_thread_size(response.get("threadId"))

        return GmailMessage(
            id=response.get("id", ""),
            thread_id=response.get("threadId", ""),
            subject=subject,
            sender=sender,
            date=parsed_date,
            snippet=snippet,
            labels=labels,
            unread=unread,
            starred=starred,
            important=important,
            thread_size=thread_size,
            body_text=body_text,
            body_html=body_html,
            to=to_header,
            cc=cc_header,
            cc_only=cc_only,
        )

    def _fetch_thread_size(self, thread_id: Optional[str]) -> int:
        if not thread_id:
            return 1
        assert self.service is not None
        try:
            thread = (
                self.service.users()
                .threads()
                .get(userId="me", id=thread_id, format="metadata")
                .execute()
            )
            return len(thread.get("messages", []))
        except HttpError:
            return 1

    @staticmethod
    def _extract_bodies(payload: Dict) -> tuple[str, str]:
        def _decode(part: Dict) -> str:
            body = part.get("body", {})
            data = body.get("data")
            if not data:
                return ""
            decoded = base64.urlsafe_b64decode(data.encode("UTF-8")).decode("utf-8", errors="ignore")
            if part.get("mimeType") == "text/html":
                soup = BeautifulSoup(decoded, "html.parser")
                return soup.prettify()
            return decoded

        if payload.get("mimeType") == "text/plain":
            return _decode(payload), ""
        if payload.get("mimeType") == "text/html":
            html = _decode(payload)
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text("\n"), html

        parts = payload.get("parts", [])
        text, html = "", ""
        for part in parts:
            mime_type = part.get("mimeType")
            if mime_type == "text/plain" and not text:
                text = _decode(part)
            elif mime_type == "text/html" and not html:
                html = _decode(part)
        if not text and html:
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text("\n")
        return text, html

    def create_draft(self, message: GmailMessage, reply_body: str) -> str:
        """Create a Gmail draft replying to `message` with `reply_body`. Returns draft id."""

        if not self.compose_enabled:
            raise RuntimeError("Gmail compose scope not configured. Cannot save drafts.")

        self.authenticate()
        assert self.service is not None

        headers = [
            f"To: {message.sender}",
            f"Subject: Re: {message.subject}",
            "Content-Type: text/plain; charset=UTF-8",
        ]
        email_content = "\r\n".join(headers) + "\r\n\r\n" + reply_body
        encoded_message = base64.urlsafe_b64encode(email_content.encode("utf-8")).decode("utf-8")

        try:
            draft = (
                self.service.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": encoded_message}})
                .execute()
            )
        except HttpError as exc:
            LOGGER.error("Failed to create draft: %s", exc)
            raise RuntimeError("Unable to save draft to Gmail. Check your compose scope.") from exc

        return draft.get("id", "")
