from playwright.sync_api import sync_playwright


with sync_playwright() as p:

    browser = p.chromium.launch(
        channel="chrome",
        headless=False
    )

    page = browser.new_page()

    print("Opening Google Flights...")
    page.goto(
        "https://www.google.com/travel/flights",
        wait_until="networkidle"
    )

    try:

        print("Rejecting cookies...")
        page.get_by_role(
            "button",
            name="Reject all"
        ).click(timeout=5000)

    except Exception as e:
        print(f"Cookie dialog not found: {e}")

    print("Selecting one-way...")

    page.locator(".VfPpkd-aPP78e").first.click()
    page.get_by_role(
        "option",
        name="One way"
    ).click()

    print("Setting origin...")

    page.get_by_role(
        "combobox",
        name="Where from?"
    ).click()

    page.keyboard.press("Control+A")
    page.keyboard.press("Delete")

    page.keyboard.type("IST")

    page.wait_for_timeout(2000)

    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")

    print("Setting destination...")

    page.get_by_role(
        "combobox",
        name="Where to?"
    ).click()

    page.keyboard.type("CMB")

    page.wait_for_timeout(2000)

    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")

    print("Setting passengers...")

    page.get_by_role(
        "button",
        name="Passenger"
    ).click()

    page.get_by_role(
        "button",
        name="Add adult"
    ).click()

    for _ in range(3):

        page.get_by_role(
            "button",
            name="Add child"
        ).click()

    page.get_by_role(
        "button",
        name="Done"
    ).click()

    print("Setting departure date...")

    page.get_by_role(
        "textbox",
        name="Departure"
    ).click()

    page.get_by_role(
        "button",
        name="Saturday, April 17, 2027"
    ).click(timeout=10000)

    page.get_by_role(
        "button",
        name="Done"
    ).click()

    print("Executing search...")

    page.get_by_role(
        "button",
        name="Search"
    ).click()

    page.wait_for_timeout(10000)

    print("Saving screenshot...")

    page.screenshot(
        path="results.png",
        full_page=True
    )

    text = page.locator(
        "body"
    ).inner_text()

    with open(
        "results.txt",
        "w",
        encoding="utf8"
    ) as f:
        f.write(text)

    print("Completed.")

    input("Press Enter to exit...")

    browser.close()