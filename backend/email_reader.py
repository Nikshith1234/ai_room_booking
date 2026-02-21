"""
email_reader.py - The Eyes 👀
Connects to Gmail via IMAP, finds unread Room Booking emails,
and extracts the plain-text body for further processing.
"""

import email
import imaplib
import logging
import re
from email.header import decode_header
from typing import List, Dict, Optional

logger = logging.getLogger("EmailReader")

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
BOOKING_SUBJECT_KEYWORD = "Room Booking"


class EmailReader:
    def __init__(self, gmail_address: str, app_password: str):
        if not gmail_address or not app_password:
            raise ValueError("Gmail address and App Password are required.")
        self.gmail_address = gmail_address
        self.app_password = app_password

    def _connect(self) -> imaplib.IMAP4_SSL:
        """Establish an authenticated IMAP connection."""
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
            mail.login(self.gmail_address, self.app_password)
            mail.select("INBOX")
            logger.debug("✅ Connected to Gmail IMAP.")
            return mail
        except imaplib.IMAP4.error as e:
            logger.error(f"❌ IMAP login failed: {e}")
            raise ConnectionError(
                f"Gmail authentication failed. Make sure you're using a 16-character App Password. Error: {e}"
            )

    def fetch_booking_emails(self) -> List[Dict]:
        """
        Search for unread emails with 'Room Booking' in the subject.
        Returns a list of parsed email dictionaries.
        """
        mail = self._connect()
        results = []

        try:
            # Search for unread emails matching the subject keyword
            search_criteria = f'(UNSEEN SUBJECT "{BOOKING_SUBJECT_KEYWORD}")'
            status, message_ids = mail.search(None, search_criteria)

            if status != "OK" or not message_ids[0]:
                return results

            uid_list = message_ids[0].split()
            logger.info(f"📬 Found {len(uid_list)} unread booking email(s).")

            for uid in uid_list:
                try:
                    email_data = self._fetch_email(mail, uid)
                    if email_data:
                        results.append(email_data)
                except Exception as e:
                    logger.error(f"Error parsing email UID {uid}: {e}")

        finally:
            mail.logout()

        return results

    def _fetch_email(self, mail: imaplib.IMAP4_SSL, uid: bytes) -> Optional[Dict]:
        """Fetch and parse a single email by UID."""
        status, raw_data = mail.fetch(uid, "(RFC822)")
        if status != "OK":
            return None

        raw_email = raw_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Decode subject
        subject = self._decode_header_value(msg.get("Subject", ""))

        # Decode sender
        from_raw = msg.get("From", "")
        sender_name, sender_email = self._parse_sender(from_raw)

        # Extract plain text body
        body = self._extract_body(msg)

        if not body:
            logger.warning(f"⚠️ Email UID {uid} has no readable text body. Skipping.")
            return None

        logger.debug(f"Parsed email: from={sender_email}, subject={subject}")

        return {
            "uid": uid,
            "subject": subject,
            "from": sender_email,
            "sender_name": sender_name,
            "body": body,
        }

    def _extract_body(self, msg: email.message.Message) -> str:
        """Walk email parts and extract plain text content."""
        body_parts = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))

                if content_type == "text/plain" and "attachment" not in disposition:
                    try:
                        charset = part.get_content_charset() or "utf-8"
                        text = part.get_payload(decode=True).decode(charset, errors="replace")
                        body_parts.append(text)
                    except Exception as e:
                        logger.debug(f"Could not decode email part: {e}")
        else:
            try:
                charset = msg.get_content_charset() or "utf-8"
                text = msg.get_payload(decode=True).decode(charset, errors="replace")
                body_parts.append(text)
            except Exception as e:
                logger.debug(f"Could not decode email body: {e}")

        return "\n".join(body_parts).strip()

    def mark_as_read(self, uid: bytes):
        """Mark an email as read (Seen) so it's not processed again."""
        try:
            mail = self._connect()
            mail.store(uid, "+FLAGS", "\\Seen")
            mail.logout()
            logger.debug(f"✅ Marked email UID {uid} as read.")
        except Exception as e:
            logger.error(f"❌ Could not mark email as read: {e}")

    @staticmethod
    def _decode_header_value(value: str) -> str:
        """Decode RFC 2047 encoded email headers."""
        decoded_parts = decode_header(value)
        parts = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                parts.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                parts.append(part)
        return " ".join(parts)

    @staticmethod
    def _parse_sender(from_raw: str):
        """Extract name and email address from a From: header."""
        match = re.match(r'"?([^"<]*)"?\s*<([^>]+)>', from_raw)
        if match:
            name = match.group(1).strip() or match.group(2).split("@")[0]
            email_addr = match.group(2).strip()
        else:
            email_addr = from_raw.strip()
            name = email_addr.split("@")[0]
        return name, email_addr
