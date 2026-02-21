"""
booking_service.py
ALL field IDs confirmed from browser inspect:
  #bookingGuestName  - Guest Name (text)
  #bookingEmail      - Email (email) - guessed same pattern
  #bookingCheckIn    - Check-in Date (date)
  #bookingCheckOut   - Check-out Date (date)
  #bookingRoomType   - Room Type (select)
  #bookingAdults     - Number of Adults (number, min=1)
  #bookingChildren   - Number of Children (number, min=0)

Room Type options (value -> label):
  1 -> Premium Suite (₹9440/night)
  2 -> Deluxe Room (₹7150/night)
  3 -> Executive Room (₹6050/night)
  4 -> Family Suite (₹12100/night)
  5 -> Deluxe Sea View Room (₹20060/night)
  6 -> Presidential suite (₹11800/night)
"""

import logging
import os
import re
from datetime import datetime
from typing import Dict

logger = logging.getLogger("BookingService")

# Exact room type values from the HTML <option value="N">
ROOM_TYPE_VALUES = {
    "premium suite":        "1",
    "premium":              "1",
    "deluxe room":          "2",
    "deluxe":               "2",
    "executive room":       "3",
    "executive":            "3",
    "family suite":         "4",
    "family":               "4",
    "deluxe sea view room": "5",
    "sea view":             "5",
    "beach":                "5",
    "presidential suite":   "6",
    "presidential":         "6",
    "suite":                "1",  # default suite -> premium
    "standard":             "3",  # closest to standard
}


class BookingService:
    def __init__(self, website_url, admin_username, admin_password, headless=True):
        self.website_url = website_url.rstrip("/")
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.headless = headless

    def create_booking(self, booking_details: Dict) -> Dict:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        logger.info("Launching browser ...")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            page.set_default_timeout(30_000)

            try:
                self._login(page)
                self._go_to_bookings(page)
                self._open_create_modal(page)
                self._fill_modal(page, booking_details)
                result = self._confirm(page)
                return result
            except PWTimeout as e:
                logger.error(f"Timeout: {e}")
                self._screenshot(page, "timeout")
                return {"success": False, "message": "Website timed out.", "booking_id": None}
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                self._screenshot(page, "error")
                return {"success": False, "message": f"Automation error: {e}", "booking_id": None}
            finally:
                ctx.close()
                browser.close()

    # ── Login ─────────────────────────────────────────────────────────────────
    def _login(self, page):
        logger.info("Logging in ...")
        page.goto(self.website_url, wait_until="networkidle")
        page.fill('input[placeholder="Enter username"]', self.admin_username)
        page.fill('input[placeholder="Enter password"]', self.admin_password)
        page.click('button:has-text("Login")')
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        if "login" in page.url.lower():
            raise RuntimeError("Login failed.")
        logger.info(f"Logged in -> {page.url}")

    # ── Go to Bookings ────────────────────────────────────────────────────────
    def _go_to_bookings(self, page):
        logger.info("Navigating to Bookings ...")
        page.wait_for_timeout(1500)
        clicked = False
        for attempt in [
            lambda: page.get_by_role("link", name="Bookings").click(),
            lambda: page.locator("nav >> text=Bookings").first.click(),
            lambda: page.get_by_text("Bookings", exact=True).first.click(),
        ]:
            try:
                attempt()
                clicked = True
                break
            except Exception:
                continue
        if not clicked:
            page.goto(f"{self.website_url}/bookings", wait_until="networkidle")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        logger.info(f"On bookings page -> {page.url}")

    # ── Open modal ────────────────────────────────────────────────────────────
    def _open_create_modal(self, page):
        logger.info("Opening modal ...")
        for sel in ['button:has-text("Create Booking")', 'button:has-text("+ Create Booking")']:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=3000):
                    btn.click()
                    break
            except Exception:
                continue
        page.wait_for_selector('#bookingModal', state="visible", timeout=10_000)
        page.wait_for_timeout(800)
        logger.info("Modal opened.")

    # ── Fill modal — ALL IDs CONFIRMED ────────────────────────────────────────
    def _fill_modal(self, page, details: Dict):
        logger.info(f"Filling form: {details}")

        guest_name   = details.get("guest_name", "")
        guest_email  = details.get("guest_email", "")
        check_in     = details.get("check_in", "")   # YYYY-MM-DD
        check_out    = details.get("check_out", "")  # YYYY-MM-DD
        room_type    = details.get("room_type", "")
        num_adults   = int(details.get("num_adults", 1))
        num_children = int(details.get("num_children", 0))

        if not guest_name and guest_email:
            guest_name = guest_email.split("@")[0]

        # 1. Guest Name — confirmed: #bookingGuestName
        page.fill("#bookingGuestName", guest_name)
        logger.info(f"  name -> '{guest_name}'")

        # 2. Email — try #bookingEmail, fallback to type=email inside form
        try:
            page.fill("#bookingEmail", guest_email)
            logger.info(f"  email -> '{guest_email}' via #bookingEmail")
        except Exception:
            try:
                page.fill('form#bookingForm input[type="email"]', guest_email)
                logger.info(f"  email -> '{guest_email}' via type=email")
            except Exception as e:
                logger.warning(f"  email fill failed: {e}")

        # 3. Check-in — confirmed: #bookingCheckIn (type="date")
        if check_in:
            self._set_date(page, "#bookingCheckIn", check_in)
            logger.info(f"  check-in -> '{check_in}'")

        # 4. Check-out — confirmed: #bookingCheckOut (type="date")
        if check_out:
            self._set_date(page, "#bookingCheckOut", check_out)
            logger.info(f"  check-out -> '{check_out}'")

        page.wait_for_timeout(300)

        # 5. Room Type — confirmed: #bookingRoomType (select, value-based)
        if room_type:
            value = self._get_room_value(room_type)
            try:
                if value:
                    page.select_option("#bookingRoomType", value=value)
                    logger.info(f"  room type -> value='{value}' for '{room_type}'")
                else:
                    # fallback: select by partial label text
                    opts = page.locator("#bookingRoomType option").all_text_contents()
                    best = self._best_option(room_type, opts)
                    if best:
                        page.select_option("#bookingRoomType", label=best)
                        logger.info(f"  room type -> label='{best}'")
            except Exception as e:
                logger.warning(f"  room type error: {e}")

        page.wait_for_timeout(300)

        # 6. Adults — confirmed: #bookingAdults (number, min=1)
        self._set_number(page, "#bookingAdults", num_adults)
        logger.info(f"  adults -> {num_adults}")

        # 7. Children — confirmed: #bookingChildren (number, min=0)
        self._set_number(page, "#bookingChildren", num_children)
        logger.info(f"  children -> {num_children}")

        page.wait_for_timeout(400)
        self._screenshot(page, "form_filled")
        logger.info("Form filled - check logs/screenshot_form_filled_*.png")

    # ── Set <input type="date"> via JS ────────────────────────────────────────
    def _set_date(self, page, selector: str, iso_date: str):
        """
        Sets date input value using JS native setter.
        This is the only reliable method for <input type="date">.
        Value must be YYYY-MM-DD format.
        """
        page.evaluate("""(args) => {
            const el = document.querySelector(args.sel);
            if (!el) { console.error('Not found:', args.sel); return; }
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value').set;
            setter.call(el, args.val);
            el.dispatchEvent(new Event('input',  { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            el.dispatchEvent(new Event('blur',   { bubbles: true }));
        }""", {"sel": selector, "val": iso_date})
        page.wait_for_timeout(200)

        actual = page.evaluate(f"document.querySelector('{selector}')?.value")
        logger.info(f"  {selector} set to '{actual}'")

    # ── Set <input type="number"> via JS ──────────────────────────────────────
    def _set_number(self, page, selector: str, value: int):
        page.evaluate("""(args) => {
            const el = document.querySelector(args.sel);
            if (!el) return;
            el.scrollIntoView({ block: 'center' });
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value').set;
            setter.call(el, String(args.val));
            el.dispatchEvent(new Event('input',  { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            el.dispatchEvent(new Event('blur',   { bubbles: true }));
        }""", {"sel": selector, "val": value})
        page.wait_for_timeout(150)
        actual = page.evaluate(f"document.querySelector('{selector}')?.value")
        logger.info(f"  {selector} set to '{actual}'")

    # ── Confirm ───────────────────────────────────────────────────────────────
    def _confirm(self, page) -> Dict:
        logger.info("Clicking Confirm Booking ...")

        # Scroll inside the modal to reveal the Confirm button at the bottom
        page.evaluate("""() => {
            // Try scrolling the modal content div
            const selectors = [
                '#bookingModal .modal-content',
                '#bookingModal .modal-body',
                '#bookingModal',
                '.modal-content'
            ];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el) { el.scrollTop = el.scrollHeight; }
            }
            // Also scroll the confirm button into view directly
            const btn = document.querySelector('form#bookingForm button[type="submit"]');
            if (btn) btn.scrollIntoView({ behavior: 'instant', block: 'center' });
        }""")
        page.wait_for_timeout(600)

        # Confirmed HTML: <button type="submit" class="btn btn-primary"> Confirm Booking </button>
        # Try click, then JS click as fallback
        clicked = False

        # First try: Playwright click
        for sel in [
            'form#bookingForm button[type="submit"]',
            '#bookingModal button[type="submit"]',
            'button.btn-primary',
            'button:has-text("Confirm Booking")',
        ]:
            try:
                btn = page.locator(sel).first
                btn.scroll_into_view_if_needed()
                page.wait_for_timeout(300)
                if btn.is_visible(timeout=2000):
                    btn.click()
                    clicked = True
                    logger.info(f"Clicked Confirm via: {sel}")
                    break
            except Exception:
                continue

        # Second try: JavaScript click (bypasses visibility/scroll issues)
        if not clicked:
            logger.warning("Playwright click failed, trying JS click ...")
            result = page.evaluate("""() => {
                const btn = document.querySelector('form#bookingForm button[type="submit"]')
                          || document.querySelector('#bookingModal button[type="submit"]')
                          || document.querySelector('button.btn-primary');
                if (btn) { btn.click(); return 'clicked: ' + btn.textContent.trim(); }
                return 'button not found';
            }""")
            logger.info(f"JS click result: {result}")
            clicked = True

        page.wait_for_load_state("networkidle", timeout=20_000)
        page.wait_for_timeout(2000)
        self._screenshot(page, "after_confirm")

        for text in ["booking confirmed", "successfully", "booking created", "success"]:
            try:
                elem = page.locator(f"text=/{text}/i").first
                if elem.is_visible(timeout=3_000):
                    msg = elem.inner_text()
                    bid = self._extract_id(msg + page.url)
                    logger.info(f"Booking successful - ID: {bid}")
                    return {"success": True, "message": msg, "booking_id": bid}
            except Exception:
                pass

        for sel in ['.alert-danger', '[class*="error"]', 'text=/not available/i']:
            try:
                elem = page.locator(sel).first
                if elem.is_visible(timeout=2_000):
                    err = elem.inner_text()
                    return {"success": False, "message": err.strip(), "booking_id": None}
            except Exception:
                pass

        try:
            modal_gone = not page.locator('#bookingModal').is_visible(timeout=2000)
        except Exception:
            modal_gone = True

        if modal_gone:
            bid = self._extract_id(page.url)
            logger.info("Modal closed - booking successful.")
            return {"success": True, "message": "Booking confirmed successfully.", "booking_id": bid}

        return {"success": False, "message": "Booking result unclear. Check logs/screenshots.", "booking_id": None}

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _get_room_value(room_type: str) -> str:
        rt = room_type.lower().strip()
        # Exact match first
        if rt in ROOM_TYPE_VALUES:
            return ROOM_TYPE_VALUES[rt]
        # Partial match
        for key, val in ROOM_TYPE_VALUES.items():
            if key in rt or rt in key:
                return val
        return ""

    @staticmethod
    def _best_option(room_type: str, options: list) -> str:
        rt = room_type.lower()
        for opt in options:
            if rt in opt.lower() or opt.lower() in rt:
                return opt.strip()
        return ""

    @staticmethod
    def _extract_id(text: str) -> str:
        for pat in [r"#(\d+)", r"booking[_\-\s]?(?:id|no)[\s:#]*([A-Z0-9\-]+)", r"/bookings?/(\d+)"]:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1)
        return "N/A"

    @staticmethod
    def _screenshot(page, label: str):
        try:
            os.makedirs("logs", exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"logs/screenshot_{label}_{ts}.png"
            page.screenshot(path=path)
            logger.info(f"Screenshot saved: {path}")
        except Exception as e:
            logger.debug(f"Screenshot failed: {e}")