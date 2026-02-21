# 🤖 Room Booking AI Agent — HeyKoala

Monitors Gmail for booking requests → logs into booking.heykoala.ai → fills the form → emails confirmation back.

---

## ⚡ Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Copy and fill in your credentials
copy .env.example .env

# 3. Run (or just double-click run_agent.bat)
python -m backend.main
```

---

## 📧 How to Test

Send an email to your Gmail account:

| Field | Value |
|---|---|
| **Subject** | `Room Booking` |
| **Body** | `Book a Deluxe room from March 22, 2026 to March 25, 2026 for 2 adults. My name is Alice.` |

The agent will:
1. Detect it within 60 seconds
2. Log into `booking.heykoala.ai` as Admin
3. Open **Bookings → + Create Booking**
4. Fill the modal and click **Confirm Booking**
5. Email you the confirmation (or failure reason)

---

## 🗂️ Project Structure

```
room-booking-agent/
├── backend/
│   ├── main.py            # 🧠 Orchestrator + scheduler
│   ├── email_reader.py    # 👀 Gmail IMAP monitor
│   ├── rasa_service.py    # 👂 NLP parser (Claude AI + regex)
│   ├── booking_service.py # ✋ Playwright automation
│   └── email_sender.py    # 🗣️ HTML email sender
├── logs/                  # Auto-created: logs + screenshots
├── .env.example           # Template — copy to .env
├── requirements.txt
└── run_agent.bat          # Windows one-click launcher
```

---

## 🌐 Website Automation Map

| Step | UI Element | Selector Used |
|---|---|---|
| Login | Username input | `input[placeholder="Enter username"]` |
| Login | Password input | `input[placeholder="Enter password"]` |
| Login | Login button | `button:has-text("Login")` |
| Nav | Bookings sidebar link | `a:has-text("Bookings")` |
| Bookings | Create Booking button | `button:has-text("Create Booking")` |
| Modal | Guest email | `input[placeholder="john@example.com"]` |
| Modal | Check-in date | First `input[placeholder="mm/dd/yyyy"]` |
| Modal | Check-out date | Second `input[placeholder="mm/dd/yyyy"]` |
| Modal | Room Type | `select` containing `"Select Room Type"` |
| Modal | Adults | First `input[type="number"]` |
| Modal | Children | Second `input[type="number"]` |
| Modal | Confirm | `button:has-text("Confirm Booking")` |

---

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| Login fails | Check `ADMIN_USERNAME` / `ADMIN_PASSWORD` in `.env` |
| Email auth failed | Must be a 16-char **Gmail App Password**, not your normal password |
| Room type not selected | Set `HEADLESS=false` to watch and check available dropdown options |
| Timeout errors | Site may be slow — increase timeout in `booking_service.py` |
| Want to watch the browser | Set `HEADLESS=false` in `.env` |
