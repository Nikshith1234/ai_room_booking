"""
inspect_modal.py
Run this script to print the exact HTML attributes of every
input field inside the Create New Booking modal.

Usage:
  python inspect_modal.py

It will open the browser (visible), log in, open the modal,
then print every input/select field's id, name, type, class, placeholder.
"""

import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

URL      = os.getenv("BOOKING_URL", "https://booking.heykoala.ai")
USERNAME = os.getenv("ADMIN_USERNAME")
PASSWORD = os.getenv("ADMIN_PASSWORD")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.set_default_timeout(30000)

    # Login
    print("Logging in ...")
    page.goto(URL, wait_until="networkidle")
    page.fill('input[placeholder="Enter username"]', USERNAME)
    page.fill('input[placeholder="Enter password"]', PASSWORD)
    page.click('button:has-text("Login")')
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)
    print(f"Logged in -> {page.url}")

    # Go to Bookings
    print("Going to Bookings ...")
    try:
        page.get_by_role("link", name="Bookings").click()
    except:
        page.goto(f"{URL}/bookings", wait_until="networkidle")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)

    # Open Create Booking modal
    print("Opening modal ...")
    page.click('button:has-text("Create Booking")')
    page.wait_for_selector('text="Create New Booking"', state="visible")
    page.wait_for_timeout(1000)

    # ── Print ALL input fields inside the modal ──────────────────────────────
    print("\n" + "="*60)
    print("ALL INPUT FIELDS IN MODAL:")
    print("="*60)

    fields = page.evaluate("""() => {
        const results = [];

        // Get all inputs
        document.querySelectorAll('input').forEach((el, i) => {
            if (el.offsetParent !== null) {  // only visible elements
                results.push({
                    tag:         'INPUT',
                    index:       i,
                    id:          el.id || '(none)',
                    name:        el.name || '(none)',
                    type:        el.type || '(none)',
                    placeholder: el.placeholder || '(none)',
                    className:   el.className || '(none)',
                    value:       el.value || '(empty)',
                });
            }
        });

        // Get all selects
        document.querySelectorAll('select').forEach((el, i) => {
            if (el.offsetParent !== null) {
                const opts = Array.from(el.options).map(o => o.text);
                results.push({
                    tag:         'SELECT',
                    index:       i,
                    id:          el.id || '(none)',
                    name:        el.name || '(none)',
                    type:        'select',
                    placeholder: '(select)',
                    className:   el.className || '(none)',
                    value:       opts.join(' | '),
                });
            }
        });

        return results;
    }""")

    for f in fields:
        print(f"\n[{f['tag']} #{f['index']}]")
        print(f"  id          : {f['id']}")
        print(f"  name        : {f['name']}")
        print(f"  type        : {f['type']}")
        print(f"  placeholder : {f['placeholder']}")
        print(f"  class       : {f['className'][:80]}")
        print(f"  value       : {f['value']}")

    print("\n" + "="*60)
    print("COPY THE id/name VALUES ABOVE TO USE AS SELECTORS")
    print("="*60)

    input("\nPress ENTER to close the browser ...")
    browser.close()