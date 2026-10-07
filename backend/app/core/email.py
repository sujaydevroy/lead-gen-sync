"""Outgoing email.

No email provider is configured yet (see open question 3 in the backend plan), so messages
are written to the application log. Replace ConsoleEmailSender with an SMTP / SES / SendGrid
implementation without touching the callers.
"""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger("app.email")


class EmailSender(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class ConsoleEmailSender:
    def send(self, to: str, subject: str, body: str) -> None:
        logger.warning("EMAIL (not sent — no provider configured) to=%s subject=%s\n%s", to, subject, body)


def get_email_sender() -> EmailSender:
    return ConsoleEmailSender()
