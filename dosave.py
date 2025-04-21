import base64
import os
import re
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def print_page_to_pdf(url, output_folder="pdfs"):
    """
    Prints a webpage to PDF using headless Chrome's built-in print functionality.
    Includes advanced cookie consent handling.

    Args:
        url: The URL of the page to print
        output_folder: Folder where PDFs will be saved

    Returns:
        The path to the saved PDF file
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Setup Chrome options for headless browsing
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Pre-set cookies to avoid consent dialog (optional approach)
    chrome_options.add_argument("--cookie-file=cookies.txt")

    # Add user agent to appear more like a regular browser
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    # Initialize the Chrome driver
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)

    try:
        # Navigate to the page
        driver.get(url)
        print(f"Loading page: {url}")

        # Handle cookie consent - multiple approaches
        try_handle_cookie_consent(driver)

        # Allow time for page to render completely
        time.sleep(3)

        # Wait for the page to be considered fully loaded
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "h1, .topic__head h1, .page-title")
            )
        )

        # Extract page title to use for the filename
        page_title = driver.title
        # Remove section identifiers if present
        if " - " in page_title:
            page_title = page_title.split(" - ")[0]

        # Clean the filename
        safe_filename = re.sub(r"[^\w\-_]", "_", page_title).strip("_")
        pdf_filename = f"{safe_filename}.pdf"
        pdf_path = os.path.join(output_folder, pdf_filename)

        print(f"Page loaded. Preparing to create PDF: {pdf_filename}")

        # Take a screenshot for debugging if needed
        # driver.save_screenshot("before_print.png")

        # Generate PDF with Chrome's built-in functionality
        pdf_data = driver.execute_cdp_cmd(
            "Page.printToPDF",
            {
                "printBackground": True,
                "preferCSSPageSize": True,
                "marginTop": 0.4,
                "marginBottom": 0.4,
                "marginLeft": 0.4,
                "marginRight": 0.4,
                "scale": 0.9,
            },
        )

        # Save the PDF file
        with open(pdf_path, "wb") as file:
            file.write(base64.b64decode(pdf_data["data"]))

        print(f"PDF successfully saved to: {pdf_path}")
        return pdf_path

    except Exception as e:
        print(f"Error printing page to PDF: {e}")
        # Take a screenshot for debugging
        try:
            driver.save_screenshot("error_screenshot.png")
            print("Error screenshot saved as error_screenshot.png")
        except:
            pass
        return None

    finally:
        # Clean up
        driver.quit()


def try_handle_cookie_consent(driver):
    """Try multiple approaches to handle cookie consent modals"""

    # List of potential selectors for cookie accept buttons
    selectors = [
        "button.Accept.All.Cookies",
        ".Accept.All.Cookies",
        "button[aria-label*='Accept All Cookies']",
        "button:contains('Accept All')",
        "#onetrust-accept-btn-handler",
        ".accept-all-cookies",
        ".accept-cookies-button",
        "button.accept-cookies",
    ]

    # Try various CSS selectors
    for selector in selectors:
        try:
            element = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            print(f"Found cookie button with selector: {selector}")
            element.click()
            time.sleep(1)
            return True
        except:
            continue

    # Try looking for buttons with specific text
    cookie_button_texts = [
        "Accept All Cookies",
        "Accept All",
        "Accept",
        "I Agree",
        "OK",
        "Got it",
    ]

    try:
        # Get all buttons
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for button in buttons:
            button_text = button.text.strip()
            if button_text and any(
                accept_text.lower() in button_text.lower()
                for accept_text in cookie_button_texts
            ):
                print(f"Found cookie button with text: {button_text}")
                button.click()
                time.sleep(1)
                return True
    except:
        pass

    # Try executing JavaScript to remove cookie consent dialogs
    try:
        # Common cookie consent dialog IDs or classes
        for consent_id in [
            "#cookie-consent",
            "#cookie-banner",
            ".cookie-banner",
            "#cookie-notice",
        ]:
            driver.execute_script(
                f"var element = document.querySelector('{consent_id}'); if(element) element.remove();"
            )

        # Try to click an accept button via JavaScript
        driver.execute_script(
            """
            var buttons = document.querySelectorAll('button');
            for(var i=0; i<buttons.length; i++) {
                if(buttons[i].textContent.indexOf('Accept') !== -1 || 
                   buttons[i].textContent.indexOf('accept') !== -1 ||
                   buttons[i].textContent.indexOf('Allow') !== -1) {
                    buttons[i].click();
                    return;
                }
            }
        """
        )

        # Set cookies that might be set after accepting the dialog
        driver.execute_script(
            """
            document.cookie = "cookieConsent=true; path=/;";
            document.cookie = "cookies_accepted=true; path=/;";
        """
        )

        return True
    except:
        print("JavaScript attempts to handle cookie consent failed")
        return False


if __name__ == "__main__":
    # URL of the page to print
    url = "https://www.merckvetmanual.com/ear-disorders/deafness/deafness-in-animals"

    # Print the page to PDF
    pdf_file = print_page_to_pdf(url)

    if pdf_file:
        print(f"Process completed successfully. PDF saved at: {pdf_file}")
    else:
        print("Failed to save PDF.")
