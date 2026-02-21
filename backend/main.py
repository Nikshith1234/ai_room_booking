"""
main.py - The Brain
Orchestrates the entire room-booking agent loop.
"""

import sys
import logging
import os
from datetime import datetime

# Fix emoji encoding on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from backend.email_reader import EmailReader
from backend.rasa_service import BookingParser
from backend.booking_service import BookingService
from backend.email_sender import EmailSender

load_dotenv()

# Logging
os.makedirs("logs", exist_ok=True)
log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/agent_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
    ],
)
logger = logging.getLogger("RoomBookingAgent")


def process_booking_emails():
    logger.info("-" * 60)
    logger.info("Checking Gmail for new booking requests ...")

    email_reader = EmailReader(
        gmail_address=os.getenv("GMAIL_ADDRESS"),
        app_password=os.getenv("GMAIL_APP_PASSWORD"),
    )
    booking_parser = BookingParser(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )
    booking_service = BookingService(
        website_url=os.getenv("BOOKING_URL", "https://booking.heykoala.ai"),
        admin_username=os.getenv("ADMIN_USERNAME"),
        admin_password=os.getenv("ADMIN_PASSWORD"),
        headless=os.getenv("HEADLESS", "true").lower() == "true",
    )
    email_sender = EmailSender(
        gmail_address=os.getenv("GMAIL_ADDRESS"),
        app_password=os.getenv("GMAIL_APP_PASSWORD"),
    )

    try:
        emails = email_reader.fetch_booking_emails()
    except Exception as e:
        logger.error(f"Failed to fetch emails: {e}")
        return

    if not emails:
        logger.info("No new booking emails.")
        return

    logger.info(f"{len(emails)} new request(s) found.")

    for email_data in emails:
        sender_email = email_data["from"]
        sender_name  = email_data["sender_name"]
        body         = email_data["body"]
        uid          = email_data["uid"]

        logger.info(f"From: {sender_email}  |  {email_data['subject']}")

        # 1. Parse
        try:
            details = booking_parser.extract_booking_info(
                email_body=body,
                sender_name=sender_name,
                sender_email=sender_email,
            )
            details["guest_email"] = sender_email
            logger.info(f"Parsed: {details}")
        except Exception as e:
            logger.error(f"Parse failed: {e}")
            email_sender.send_failure_email(
                to_email=sender_email, guest_name=sender_name,
                reason="We could not understand your booking request. Please include check-in date, check-out date, room type, and number of guests.",
            )
            email_reader.mark_as_read(uid)
            continue

        # 2. Validate minimum fields
        missing = [f for f, k in [("check-in date","check_in"),("check-out date","check_out"),("room type","room_type")] if not details.get(k)]
        if missing:
            email_sender.send_failure_email(
                to_email=sender_email,
                guest_name=details.get("guest_name", sender_name),
                reason=f"Your request was missing: {', '.join(missing)}. Please reply with all details.",
            )
            email_reader.mark_as_read(uid)
            continue

        # 3. Book
        try:
            result = booking_service.create_booking(details)
        except Exception as e:
            logger.error(f"Booking crashed: {e}", exc_info=True)
            result = {"success": False, "message": str(e), "booking_id": None}

        # 4. Respond
        guest_name = details.get("guest_name", sender_name)
        if result["success"]:
            logger.info(f"Booking confirmed - ID: {result.get('booking_id')}")
            email_sender.send_confirmation_email(
                to_email=sender_email, guest_name=guest_name,
                booking_details=details, booking_id=result.get("booking_id","N/A"),
                confirmation_message=result.get("message",""),
            )
        else:
            logger.warning(f"Booking failed: {result['message']}")
            email_sender.send_failure_email(
                to_email=sender_email, guest_name=guest_name,
                reason=result["message"],
            )

        email_reader.mark_as_read(uid)

    logger.info("All emails processed.")


def main():
    interval = int(os.getenv("CHECK_INTERVAL_SECONDS", 60))
    logger.info("=" * 60)
    logger.info("Room Booking AI Agent Starting")
    logger.info(f"  Gmail    : {os.getenv('GMAIL_ADDRESS')}")
    logger.info(f"  Hotel    : {os.getenv('BOOKING_URL')}")
    logger.info(f"  Username : {os.getenv('ADMIN_USERNAME')}")
    logger.info(f"  Interval : {interval}s")
    logger.info(f"  Headless : {os.getenv('HEADLESS','true')}")
    logger.info("=" * 60)

    process_booking_emails()

    scheduler = BlockingScheduler()
    scheduler.add_job(process_booking_emails, "interval", seconds=interval, id="email_check")
    try:
        logger.info(f"Scheduler running. Checking every {interval}s. Ctrl+C to stop.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Agent stopped. Goodbye!")


if __name__ == "__main__":
    main()