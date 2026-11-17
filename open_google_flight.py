from playwright.sync_api import sync_playwright

with sync_playwright() as p:

    browser = p.chromium.launch(
        channel="chrome",
        headless=False
    )

    page = browser.new_page()

    page.goto(
        "https://www.google.com/travel/flights",
        wait_until="networkidle"
    )

    try:
        page.get_by_role(
            "button",
            name="reject all"
        ).click(timeout=5000)
    except:
        pass

    page.pause()