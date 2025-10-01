# API Flask para criar agendamentos no CashBarber via Selenium.
#
# Este serviço expõe um endpoint ``/create-appointment`` que recebe as
# informações necessárias e automatiza o preenchimento do painel CashBarber
# usando Selenium WebDriver.  A configuração do WebDriver foi ajustada para
# utilizar o ``new headless`` do Chrome e definir corretamente o idioma e
# locale para pt‑BR, garantindo que campos de data e hora sejam
# interpretados corretamente em ambientes sem interface gráfica【972299686105822†L34-L46】.

from flask import Flask, request, jsonify
import os
import sys
from schedule_cashbarber import (
    login_to_cashbarber,
    open_appointments_page,
    create_appointment,
)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import traceback

app = Flask(__name__)


def create_driver() -> webdriver.Chrome:
    """Create a Chrome WebDriver instance with proper options for server environment.

    The driver is configured to run in headless mode using Chrome's *new* headless
    implementation.  This ensures that language arguments such as ``--lang=pt-BR``
    are respected【972299686105822†L34-L46】.  It also sets the user agent and
    disables automation flags to reduce detection by the target site.

    Returns:
        webdriver.Chrome: A configured Chrome WebDriver instance.
    """
    options = Options()
    # Define a realistic user‑agent to avoid basic bot detection
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    )
    # Use Chrome's new headless mode so that --lang is honoured
    options.add_argument("--headless=new")
    # Other recommended flags for headless environments
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # Force the browser to use the Brazilian Portuguese locale
    options.add_argument("--lang=pt-BR")
    options.add_experimental_option(
        "prefs",
        {
            "intl.accept_languages": "pt-BR,pt,en-US,en",
        },
    )
    # Reduce automation footprint
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    # Create the driver
    driver = webdriver.Chrome(options=options)
    return driver


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "cashbarber-automation"}), 200


@app.route("/create-appointment", methods=["POST"])
def create_appointment_api():
    """
    Create an appointment via API.

    Expected JSON body:
        {
            "email": "user@example.com",
            "password": "password123",
            "client": "Client Name",
            "date": "2025-10-03",
            "start_time": "11:40",
            "end_time": "11:50",
            "branch": "Centro",
            "professional": "Miguel Oliveira",
            "services": ["Corte de Cabelo", "Barba"]
        }

    Returns a JSON response indicating success or failure.
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = [
            "email",
            "password",
            "client",
            "date",
            "start_time",
            "end_time",
            "branch",
            "professional",
            "services",
        ]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Missing required fields: {', '.join(missing_fields)}",
                    }
                ),
                400,
            )
        # Validate services is a list and non-empty
        if not isinstance(data["services"], list) or len(data["services"]) == 0:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "services must be a non-empty array",
                    }
                ),
                400,
            )

        driver = create_driver()
        try:
            login_to_cashbarber(driver, data["email"], data["password"])
            open_appointments_page(driver)
            create_appointment(
                driver,
                client_name=data["client"],
                date=data["date"],
                start_time=data["start_time"],
                end_time=data["end_time"],
                branch_name=data["branch"],
                professional_name=data["professional"],
                services=data["services"],
            )
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Appointment created successfully",
                        "data": {
                            "client": data["client"],
                            "date": data["date"],
                            "start_time": data["start_time"],
                            "end_time": data["end_time"],
                            "branch": data["branch"],
                            "professional": data["professional"],
                            "services": data["services"],
                        },
                    }
                ),
                200,
            )
        finally:
            driver.quit()
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error creating appointment: {error_trace}", file=sys.stderr)
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "trace": error_trace,
                }
            ),
            500,
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
