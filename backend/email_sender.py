"""
email_sender.py - The Voice 🗣️
Sends beautiful HTML confirmation and failure notification emails via SMTP.
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Optional

logger = logging.getLogger("EmailSender")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


class EmailSender:
    def __init__(self, gmail_address: str, app_password: str):
        self.gmail_address = gmail_address
        self.app_password = app_password

    def send_confirmation_email(
        self,
        to_email: str,
        guest_name: str,
        booking_details: Dict,
        booking_id: str,
        confirmation_message: str = "",
    ):
        """Send a beautiful HTML confirmation email."""
        subject = f"✅ Room Booking Confirmed - #{booking_id}"
        html_body = self._build_confirmation_html(
            guest_name=guest_name,
            booking_details=booking_details,
            booking_id=booking_id,
        )
        self._send(to_email, subject, html_body)
        logger.info(f"✅ Confirmation email sent to {to_email}")

    def send_failure_email(
        self,
        to_email: str,
        guest_name: str,
        reason: str,
    ):
        """Send a friendly failure notification email."""
        subject = "⚠️ Room Booking - Action Required"
        html_body = self._build_failure_html(
            guest_name=guest_name,
            reason=reason,
        )
        self._send(to_email, subject, html_body)
        logger.info(f"📧 Failure notification sent to {to_email}")

    def _send(self, to_email: str, subject: str, html_body: str):
        """Core SMTP send logic."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Hotel Booking System <{self.gmail_address}>"
        msg["To"] = to_email

        # Plain text fallback
        plain_text = "Please view this email in an HTML-capable email client."
        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(self.gmail_address, self.app_password)
                server.sendmail(self.gmail_address, to_email, msg.as_string())
                logger.debug(f"📤 Email sent to {to_email}: '{subject}'")
        except smtplib.SMTPAuthenticationError:
            logger.error("❌ SMTP authentication failed. Check Gmail App Password.")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
            raise

    # ── HTML Templates ───────────────────────────────────────────────────────
    @staticmethod
    def _build_confirmation_html(
        guest_name: str,
        booking_details: Dict,
        booking_id: str,
    ) -> str:
        check_in = booking_details.get("check_in", "N/A")
        check_out = booking_details.get("check_out", "N/A")
        room_type = booking_details.get("room_type", "N/A")
        num_adults = booking_details.get("num_adults", 1)
        num_children = booking_details.get("num_children", 0)
        now = datetime.now().strftime("%B %d, %Y at %I:%M %p")

        # Calculate nights
        nights = "N/A"
        try:
            from datetime import date
            ci = date.fromisoformat(check_in)
            co = date.fromisoformat(check_out)
            nights = str((co - ci).days)
        except Exception:
            pass

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Booking Confirmation</title>
</head>
<body style="margin:0;padding:0;font-family:'Segoe UI',Arial,sans-serif;background:#f4f6f9;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:30px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
        
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#1a73e8,#0d47a1);padding:40px 40px 30px;text-align:center;">
            <div style="font-size:48px;margin-bottom:10px;">🏨</div>
            <h1 style="color:#ffffff;margin:0;font-size:26px;font-weight:700;letter-spacing:-0.5px;">Booking Confirmed!</h1>
            <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:15px;">Your reservation has been successfully created</p>
          </td>
        </tr>

        <!-- Greeting -->
        <tr>
          <td style="padding:35px 40px 20px;">
            <p style="color:#333;font-size:16px;margin:0 0 6px;">Dear <strong>{guest_name}</strong>,</p>
            <p style="color:#555;font-size:14px;margin:0;line-height:1.6;">
              We're delighted to confirm your room reservation. Your booking details are listed below.
              We look forward to welcoming you!
            </p>
          </td>
        </tr>

        <!-- Booking ID Banner -->
        <tr>
          <td style="padding:0 40px 20px;">
            <div style="background:#e8f0fe;border-left:4px solid #1a73e8;border-radius:6px;padding:14px 18px;">
              <span style="color:#1a73e8;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Booking Reference</span>
              <div style="color:#1a1a2e;font-size:22px;font-weight:700;margin-top:4px;">#{booking_id}</div>
            </div>
          </td>
        </tr>

        <!-- Booking Details -->
        <tr>
          <td style="padding:0 40px 30px;">
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8eaed;border-radius:8px;overflow:hidden;">
              <tr style="background:#f8f9fa;">
                <td colspan="2" style="padding:12px 18px;font-size:13px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:0.5px;">
                  Reservation Details
                </td>
              </tr>
              {EmailSender._detail_row("🛏️ Room Type", room_type)}
              {EmailSender._detail_row("📅 Check-In", check_in, alt=True)}
              {EmailSender._detail_row("📅 Check-Out", check_out)}
              {EmailSender._detail_row("🌙 Nights", nights, alt=True)}
              {EmailSender._detail_row("👤 Adults", str(num_adults))}
              {EmailSender._detail_row("👶 Children", str(num_children), alt=True)}
              {EmailSender._detail_row("👤 Guest Name", guest_name)}
            </table>
          </td>
        </tr>

        <!-- Info Box -->
        <tr>
          <td style="padding:0 40px 30px;">
            <div style="background:#fff8e1;border-radius:8px;padding:16px 18px;">
              <p style="margin:0;font-size:13px;color:#f57f17;font-weight:600;">📌 Important Information</p>
              <ul style="margin:8px 0 0;padding-left:18px;color:#555;font-size:13px;line-height:1.7;">
                <li>Please present this confirmation email upon check-in.</li>
                <li>Standard check-in time is 3:00 PM; check-out is 11:00 AM.</li>
                <li>Contact reception for early/late arrangements.</li>
              </ul>
            </div>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8f9fa;padding:25px 40px;text-align:center;border-top:1px solid #e8eaed;">
            <p style="margin:0;font-size:13px;color:#666;">
              Confirmation generated on {now}<br>
              Questions? Reply to this email or contact our front desk.
            </p>
            <p style="margin:12px 0 0;font-size:12px;color:#999;">
              This is an automated message from your Hotel Booking AI Agent 🤖
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    @staticmethod
    def _detail_row(label: str, value: str, alt: bool = False) -> str:
        bg = "#f8f9fa" if alt else "#ffffff"
        return f"""
              <tr style="background:{bg};">
                <td style="padding:12px 18px;font-size:13px;color:#888;width:40%;border-top:1px solid #e8eaed;">{label}</td>
                <td style="padding:12px 18px;font-size:13px;color:#1a1a2e;font-weight:600;border-top:1px solid #e8eaed;">{value}</td>
              </tr>"""

    @staticmethod
    def _build_failure_html(guest_name: str, reason: str) -> str:
        now = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Booking Issue</title>
</head>
<body style="margin:0;padding:0;font-family:'Segoe UI',Arial,sans-serif;background:#f4f6f9;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:30px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
        
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#e53935,#b71c1c);padding:40px 40px 30px;text-align:center;">
            <div style="font-size:48px;margin-bottom:10px;">⚠️</div>
            <h1 style="color:#ffffff;margin:0;font-size:26px;font-weight:700;">Booking Could Not Be Completed</h1>
            <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:15px;">Action required from your side</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:35px 40px 20px;">
            <p style="color:#333;font-size:16px;margin:0 0 6px;">Dear <strong>{guest_name}</strong>,</p>
            <p style="color:#555;font-size:14px;margin:0;line-height:1.6;">
              We were unable to complete your room booking request. Here's what happened:
            </p>
          </td>
        </tr>

        <!-- Reason Box -->
        <tr>
          <td style="padding:0 40px 25px;">
            <div style="background:#fdecea;border-left:4px solid #e53935;border-radius:6px;padding:16px 18px;">
              <p style="margin:0;font-size:13px;color:#b71c1c;font-weight:600;">Reason</p>
              <p style="margin:6px 0 0;font-size:14px;color:#333;line-height:1.6;">{reason}</p>
            </div>
          </td>
        </tr>

        <!-- What to do -->
        <tr>
          <td style="padding:0 40px 30px;">
            <div style="background:#e8f5e9;border-radius:8px;padding:16px 18px;">
              <p style="margin:0;font-size:13px;color:#2e7d32;font-weight:600;">✅ What to do next</p>
              <ul style="margin:8px 0 0;padding-left:18px;color:#555;font-size:13px;line-height:1.8;">
                <li>Reply to this email with the corrected details.</li>
                <li>Make sure to include: <strong>check-in date, check-out date, room type, number of guests, and your name</strong>.</li>
                <li>Our AI agent will try again on your next email.</li>
              </ul>
            </div>
          </td>
        </tr>

        <!-- Example -->
        <tr>
          <td style="padding:0 40px 30px;">
            <p style="margin:0 0 8px;font-size:13px;color:#888;font-weight:600;">Example Request Format:</p>
            <div style="background:#f8f9fa;border-radius:6px;padding:14px 18px;font-family:monospace;font-size:13px;color:#333;line-height:1.8;">
              Book a Deluxe room from March 22, 2026 to March 25, 2026<br>
              for 2 adults and 1 child.<br>
              My name is Alice Johnson.
            </div>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8f9fa;padding:25px 40px;text-align:center;border-top:1px solid #e8eaed;">
            <p style="margin:0;font-size:13px;color:#666;">
              Processed on {now}<br>
              We apologize for the inconvenience.
            </p>
            <p style="margin:12px 0 0;font-size:12px;color:#999;">
              This is an automated message from your Hotel Booking AI Agent 🤖
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
