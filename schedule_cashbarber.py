"""
This script automates the process of logging into the CashBarber panel and
creating a new appointment (agendamento) using Selenium.  It encapsulates
common steps such as navigating to the login page, entering credentials,
opening the appointment calendar and filling in the required fields.  The
script is designed as a reusable module—individual functions perform a
distinct part of the workflow and can be reused or extended in other
projects.

Usage:

```
python schedule_cashberber.py --email YOUR_EMAIL \
    --password YOUR_PASSWORD \
    --client "Client Name" \
    --date 2025-09-30 \
    --start-time 14:00 \
    --end-time 14:10 \
    --branch "Centro" \
    --professional "Miguel Oliveira" \
    --service "Corte de Cabelo"
```

The script waits for interactive elements to appear before interacting with
them, improving reliability on slower connections.  It uses visible text to
select values from drop‑down menus and autocompletes clients/services by
sending keys and choosing the first suggestion.  Should the UI change,
selectors may require adjustment.

**Disclaimer**: This code is provided for educational purposes.  Running
automated scripts against a production system without permission may
violate terms of service.  Always ensure you have authorization to
automate actions on any site.
"""

import argparse
import sys
from typing import List
import time  # Added for optional delays

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys  # for keyboard shortcuts
from datetime import datetime  # for parsing dates
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def login_to_cashbarber(driver: webdriver.Chrome, email: str, password: str, timeout: int = 15, delay: float = 0.0) -> None:
    """Authenticate the user on the CashBarber panel.

    Args:
        driver: An instance of a Selenium WebDriver already configured.
        email: The e‑mail address used to log in.
        password: The corresponding password.
        timeout: Seconds to wait for elements to become available.

    Raises:
        TimeoutException: If the login page elements cannot be located
            within the specified timeout.
    """
    # Navigate to the login page
    driver.get("https://painel.cashbarber.com.br/auth/login")

    wait = WebDriverWait(driver, timeout)

    # Use explicit waits for all elements to ensure they are ready.
    print("Aguardando campo de e-mail...")
    email_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Informe o seu e-mail"]'))
    )
    print("Aguardando campo de senha...")
    password_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Informe sua senha"]'))
    )

    # Clear any prefilled text and enter credentials
    print("Preenchendo credenciais...")
    email_input.clear()
    email_input.send_keys(email)
    password_input.clear()
    password_input.send_keys(password)

    # Wait for the login button to be clickable and then click it.
    print("Aguardando botão de login...")
    login_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(normalize-space(), "Acessar")]'))
    )
    print("Clicando no botão de login...")
    login_button.click()

    # Wait until the dashboard is loaded by checking for a known element
    print("Aguardando o carregamento do painel de controle...")
    wait.until(
        EC.presence_of_element_located((By.XPATH, '//span[contains(., "Olá,")]'))
    )
    print("Login realizado com sucesso!")
    
    if delay > 0:
        time.sleep(delay)


def open_appointments_page(driver: webdriver.Chrome, timeout: int = 15, delay: float = 0.0) -> None:
    """Navigate to the Agendamentos section after logging in.

    Args:
        driver: An instance of a Selenium WebDriver that has been logged in.
        timeout: Seconds to wait for the page to load.

    Raises:
        TimeoutException: If the appointments page fails to load.
    """
    driver.get("https://painel.cashbarber.com.br/agendamento")
    wait = WebDriverWait(driver, timeout)
    # Wait for the "Novo agendamento" button to become clickable
    wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Novo agendamento")]'))
    )
    if delay > 0:
        time.sleep(delay)


def select_dropdown_option(driver: webdriver.Chrome, select_locator: tuple, option_text: str) -> None:
    """Select an option from a native HTML `<select>` element by visible text.

    Args:
        driver: Selenium WebDriver instance.
        select_locator: Locator tuple (By, locator) for the `<select>` element.
        option_text: The visible text of the option to choose.

    Raises:
        NoSuchElementException: If the option cannot be found.
    """
    select_element = driver.find_element(*select_locator)
    # The `<select>` is a regular HTML element. Use Selenium's API to select by text.
    for option in select_element.find_elements(By.TAG_NAME, "option"):
        if option.text.strip().lower() == option_text.strip().lower():
            option.click()
            return
    raise NoSuchElementException(f"Option '{option_text}' not found in select")


def autocomplete_select(driver: webdriver.Chrome, input_locator: tuple, value: str, timeout: int = 10) -> None:
    """Select a value from an autocomplete widget by typing and choosing the first suggestion.

    The function sends the provided `value` to the autocomplete input and
    selects the first suggestion from the dropdown.  If no suggestions
    appear, it leaves the field with the typed value, assuming the widget
    accepts free text.

    Args:
        driver: Selenium WebDriver instance.
        input_locator: Locator tuple (By, locator) targeting the `<input>`
            element inside the autocomplete component.
        value: Text to type into the autocomplete and select.
        timeout: Seconds to wait for suggestions to load.
    """
    wait = WebDriverWait(driver, timeout)
    input_element = wait.until(EC.presence_of_element_located(input_locator))
    input_element.clear()
    input_element.send_keys(value)

    # Wait for the suggestions popper to appear
    try:
        suggestions_container = wait.until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="presentation"]//li[1]'))
        )
        # Select the first suggestion
        suggestions_container.click()
    except TimeoutException:
        # If no suggestions appear, press Enter to accept the typed value if allowed
        input_element.send_keys("\n")


def log_datetime_fields(driver: webdriver.Chrome, step_name: str):
    """Logs the current values of date and time fields for debugging."""
    try:
        # Use JavaScript to get the current value of the input fields
        date_val = driver.execute_script("return document.getElementsByName('age_data')[0].value;")
        start_val = driver.execute_script("return document.getElementsByName('age_inicio')[0].value;")
        end_val = driver.execute_script("return document.getElementsByName('age_fim')[0].value;")
        print(f"\n--- LOG [{step_name}] ---")
        print(f"    Data atual: '{date_val}'")
        print(f"    Início atual: '{start_val}'")
        print(f"    Fim atual: '{end_val}'")
        print("----------------------------------\n")
    except Exception as e:
        print(f"\n--- LOG [{step_name}] ---")
        print(f"    Não foi possível ler os campos de data/hora: {e}")
        print("----------------------------------\n")


def create_appointment(
    driver: webdriver.Chrome,
    client_name: str,
    date: str,
    start_time: str,
    end_time: str,
    branch_name: str,
    professional_name: str,
    services: List[str],
    timeout: int = 15,
    delay: float = 0.0,
) -> None:
    """Fill in the appointment form with provided values and save.

    Args:
        driver: Selenium WebDriver instance already navigated to appointments page.
        client_name: Full or partial name of the client to select.
        date: Appointment date in ISO format (YYYY-MM-DD).
        start_time: Start time (24h clock, e.g., "14:00").
        end_time: End time (24h clock, e.g., "14:10").
        branch_name: Name of the branch/filial to select.
        professional_name: Name of the professional performing the service.
        services: A list of service names to add to the appointment.
        timeout: Seconds to wait for elements to become ready.

    Raises:
        TimeoutException: If necessary elements do not appear in time.
        NoSuchElementException: If an expected dropdown option cannot be found.
    """
    wait = WebDriverWait(driver, timeout)

    # Open the modal
    new_appointment_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Novo agendamento")]'))
    )
    new_appointment_btn.click()
    if delay > 0:
        time.sleep(delay)

    # Wait for modal fields to load
    wait.until(
        EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "modal-agendamento")]'))
    )
    log_datetime_fields(driver, "Após abrir o modal")

    # Select appointment type (hardcoded to "Agendamento")
    print("\n1. Selecionando tipo de agendamento...")
    select_dropdown_option(
        driver,
        (By.CSS_SELECTOR, 'select[aria-invalid]'),
        "Agendamento",
    )
    if delay > 0:
        time.sleep(delay)

    # Set client (autocomplete)
    print("\n2. Selecionando cliente...")
    autocomplete_select(driver, (By.ID, "age_id_cliente"), client_name)
    if delay > 0:
        time.sleep(delay)
    log_datetime_fields(driver, "Após selecionar o cliente")
    
    # Set Branch and Professional FIRST
    print("\n3. Selecionando filial...")
    select_dropdown_option(
        driver,
        (By.XPATH, "//div[div[contains(text(), 'Filial')]]//select"),
        branch_name
    )
    if delay > 0:
        time.sleep(delay)
    log_datetime_fields(driver, "Após selecionar a filial")

    print("\n4. Selecionando profissional...")
    select_dropdown_option(
        driver,
        (By.XPATH, "//div[div[contains(text(), 'Profissional')]]//select"),
        professional_name
    )
    if delay > 0:
        time.sleep(delay)
    log_datetime_fields(driver, "Após selecionar o profissional")

    # Add services BEFORE setting date/time
    print("\n5. Adicionando serviços...")
    for service in services:
        print(f"   Adicionando: {service}")
        autocomplete_select(driver, (By.ID, "id_usuario_servico"), service)
        if delay > 0:
            time.sleep(delay)

        plus_btn_locator = (
            By.XPATH,
            "//input[@id='id_usuario_servico']/ancestor::div[contains(@class, 'col-sm-11')]/following-sibling::div[contains(@class, 'col-sm-1')]//button"
        )
        plus_btn = wait.until(EC.element_to_be_clickable(plus_btn_locator))
        plus_btn.click()
        if delay > 0:
            time.sleep(delay)
    
    log_datetime_fields(driver, "Após adicionar serviços")
    
    # Wait longer for any async operations to complete
    print("\n6. Aguardando estabilização do formulário...")
    time.sleep(2.0)

    # Parse date
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
    except Exception:
        try:
            dt = datetime.strptime(date, "%d/%m/%Y")
        except Exception:
            clean = date.replace("/", "").replace("-", "")
            dt = datetime.strptime(clean, "%d%m%Y")

    date_iso = dt.strftime("%Y-%m-%d")

    # NOW set date/time using manual method (click + clear + send_keys)
    # This works better than JS injection for this site's validation
    print("\n7. Definindo data e horários (método manual)...")
    
    try:
        print("   Definindo data...")
        date_input = driver.find_element(By.NAME, "age_data")
        date_input.click()
        time.sleep(0.3)
        date_input.clear()
        time.sleep(0.3)
        date_input.send_keys(dt.strftime("%d/%m/%Y"))
        time.sleep(0.5)
        
        print("   Definindo horário de início...")
        start_input = driver.find_element(By.NAME, "age_inicio")
        start_input.click()
        time.sleep(0.3)
        start_input.clear()
        time.sleep(0.3)
        start_input.send_keys(start_time)
        time.sleep(0.5)
        
        print("   Definindo horário de término...")
        end_input = driver.find_element(By.NAME, "age_fim")
        end_input.click()
        time.sleep(0.3)
        end_input.clear()
        time.sleep(0.3)
        end_input.send_keys(end_time)
        time.sleep(0.5)
        
        log_datetime_fields(driver, "Após definir data/hora manualmente")
        
    except Exception as e:
        print(f"⚠️ Erro ao definir campos manualmente: {e}")
        print("Tentando método alternativo via JavaScript...")
        
        # Fallback to JS method if manual fails
        js_set_value = """
            arguments[0].value = arguments[1]; 
            arguments[0].dispatchEvent(new Event('input', { bubbles: true })); 
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
        """
        
        date_input = driver.find_element(By.NAME, "age_data")
        driver.execute_script(js_set_value, date_input, date_iso)
        time.sleep(0.5)
        
        start_input = driver.find_element(By.NAME, "age_inicio")
        driver.execute_script(js_set_value, start_input, start_time)
        time.sleep(0.5)
        
        end_input = driver.find_element(By.NAME, "age_fim")
        driver.execute_script(js_set_value, end_input, end_time)
        time.sleep(0.5)
        
        log_datetime_fields(driver, "Após tentativa JS (fallback)")
    
    log_datetime_fields(driver, "FINAL - Antes de salvar")

    # Save
    print("\n8. Salvando agendamento...")
    save_btn = driver.find_element(By.XPATH, '//button[contains(., "Salvar agendamento")]')
    save_btn.click()
    if delay > 0:
        time.sleep(delay)

    wait.until(
        EC.invisibility_of_element_located((By.XPATH, '//div[contains(@class, "modal-agendamento")]'))
    )
    if delay > 0:
        time.sleep(delay)


def main() -> None:
    parser = argparse.ArgumentParser(description="Automate CashBarber appointment scheduling.")
    parser.add_argument("--email", required=True, help="Login email for CashBarber")
    parser.add_argument("--password", required=True, help="Login password for CashBarber")
    parser.add_argument("--client", required=True, help="Name of the client to schedule")
    parser.add_argument("--date", required=True, help="Date of the appointment (YYYY-MM-DD or DD/MM/YYYY)")
    parser.add_argument("--start-time", required=True, help="Start time (HH:MM, 24h)")
    parser.add_argument("--end-time", required=True, help="End time (HH:MM, 24h)")
    parser.add_argument("--branch", required=True, help="Name of the branch (Filial)")
    parser.add_argument("--professional", required=True, help="Name of the professional")
    parser.add_argument(
        "--service",
        action="append",
        dest="services",
        help="Service to add; can be provided multiple times",
        required=True,
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Open Chrome with a visible window (omit this to run headless)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Seconds to wait after each step for observation (e.g. 1.0)",
    )
    args = parser.parse_args()

    options = Options()
    # Add a common user-agent to avoid basic bot detection
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    if not args.show_browser:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)

    try:
        login_to_cashbarber(driver, args.email, args.password, delay=args.delay)
        open_appointments_page(driver, delay=args.delay)
        create_appointment(
            driver,
            client_name=args.client,
            date=args.date,
            start_time=args.start_time,
            end_time=args.end_time,
            branch_name=args.branch,
            professional_name=args.professional,
            services=args.services,
            delay=args.delay,
        )
        print("\n✓ Appointment created successfully.")
    except Exception as exc:
        print(f"\n✗ An error occurred: {exc}", file=sys.stderr)
        driver.save_screenshot('error_screenshot.png')
        with open('error_page.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("Screenshot saved: error_screenshot.png")
        print("Page HTML saved: error_page.html")
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
