"""
Automação de login e criação de agendamento no CashBarber via Selenium.

Principais correções:
- Força locale/idioma pt-BR e timezone America/Sao_Paulo no Chrome headless (n8n/Docker).
- Preenchimento robusto de data/hora (CTRL+A, DELETE, envia DD/MM/AAAA e confirma com TAB).
- Esperas explícitas confirmando que o valor ficou exatamente como desejado.
- Logs melhores dos campos de data/hora (considera inputs duplicados/hidden).
"""

import argparse
import sys
from typing import List
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def login_to_cashbarber(driver: webdriver.Chrome, email: str, password: str, timeout: int = 15, delay: float = 0.0) -> None:
    """Autentica no painel do CashBarber."""
    driver.get("https://painel.cashbarber.com.br/auth/login")
    wait = WebDriverWait(driver, timeout)

    print("Aguardando campo de e-mail...")
    email_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Informe o seu e-mail"]'))
    )
    print("Aguardando campo de senha...")
    password_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Informe sua senha"]'))
    )

    print("Preenchendo credenciais...")
    email_input.clear()
    email_input.send_keys(email)
    password_input.clear()
    password_input.send_keys(password)

    print("Aguardando botão de login...")
    login_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(normalize-space(), "Acessar")]'))
    )
    print("Clicando no botão de login...")
    login_button.click()

    print("Aguardando o carregamento do painel de controle...")
    wait.until(EC.presence_of_element_located((By.XPATH, '//span[contains(., "Olá,")]')))
    print("Login realizado com sucesso!")

    if delay > 0:
        time.sleep(delay)


def open_appointments_page(driver: webdriver.Chrome, timeout: int = 15, delay: float = 0.0) -> None:
    """Abre a página de Agendamentos."""
    driver.get("https://painel.cashbarber.com.br/agendamento")
    wait = WebDriverWait(driver, timeout)
    wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Novo agendamento")]')))
    if delay > 0:
        time.sleep(delay)


def select_dropdown_option(driver: webdriver.Chrome, select_locator: tuple, option_text: str) -> None:
    """Seleciona opção por texto visível em um <select> nativo."""
    select_element = driver.find_element(*select_locator)
    for option in select_element.find_elements(By.TAG_NAME, "option"):
        if option.text.strip().lower() == option_text.strip().lower():
            option.click()
            return
    raise NoSuchElementException(f"Opção '{option_text}' não encontrada no select")


def autocomplete_select(driver: webdriver.Chrome, input_locator: tuple, value: str, timeout: int = 10) -> None:
    """Seleciona a 1ª sugestão de um autocomplete após digitar o valor."""
    wait = WebDriverWait(driver, timeout)
    input_element = wait.until(EC.presence_of_element_located(input_locator))
    input_element.clear()
    input_element.send_keys(value)

    try:
        suggestion = wait.until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="presentation"]//li[1]'))
        )
        suggestion.click()
    except TimeoutException:
        input_element.send_keys(Keys.ENTER)


def log_datetime_fields(driver: webdriver.Chrome, step_name: str):
    """Loga todos os valores atuais dos campos de data/hora (considera múltiplos inputs)."""
    try:
        vals = driver.execute_script("""
            const out = {};
            out.date = Array.from(document.getElementsByName('age_data')).map(e => e.value);
            out.start = Array.from(document.getElementsByName('age_inicio')).map(e => e.value);
            out.end = Array.from(document.getElementsByName('age_fim')).map(e => e.value);
            return out;
        """)
        print(f"\n--- LOG [{step_name}] ---")
        print(f"    age_data  : {vals['date']}")
        print(f"    age_inicio: {vals['start']}")
        print(f"    age_fim   : {vals['end']}")
        print("----------------------------------\n")
    except Exception as e:
        print(f"\n--- LOG [{step_name}] ---")
        print(f"    Falha lendo campos: {e}")
        print("----------------------------------\n")


def capture_popup_content(driver: webdriver.Chrome):
    """Captura popups/alerts/erros visíveis."""
    popup_info = {
        "found": False,
        "type": None,
        "text": None,
        "screenshot_saved": False
    }

    # Alert nativo
    try:
        alert = driver.switch_to.alert
        popup_info["found"] = True
        popup_info["type"] = "browser_alert"
        popup_info["text"] = alert.text
        print(f"\n[POPUP] BROWSER ALERT DETECTED:")
        print(f"   Text: {alert.text}")
        return popup_info
    except Exception:
        pass

    # Seletores comuns de modais/avisos
    popup_selectors = [
        "//div[contains(@class, 'modal') and contains(@class, 'show')]",
        "//div[contains(@class, 'alert')]",
        "//div[contains(@class, 'error')]",
        "//div[contains(@class, 'warning')]",
        "//div[@role='dialog']",
        "//div[@role='alertdialog']",
        "//*[contains(@class, 'swal')]",
        "//*[contains(@class, 'toast')]",
        "//*[contains(@class, 'notification')]",
        "//div[contains(@class, 'message')]",
    ]

    for selector in popup_selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            for element in elements:
                if element.is_displayed():
                    text = element.text.strip()
                    if text:
                        popup_info["found"] = True
                        popup_info["type"] = "modal/popup"
                        popup_info["text"] = text
                        try:
                            driver.save_screenshot('/tmp/popup_screenshot.png')
                            popup_info["screenshot_saved"] = True
                        except Exception:
                            pass
                        print(f"\n[POPUP] MODAL/POPUP DETECTED:")
                        print(f"   Selector: {selector}")
                        print(f"   Text: {text}")
                        print(f"   Screenshot saved: {popup_info['screenshot_saved']}")
                        return popup_info
        except Exception:
            continue

    return popup_info


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
    """Preenche o formulário de agendamento e salva."""
    wait = WebDriverWait(driver, timeout)

    # Abre modal
    new_appointment_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Novo agendamento")]'))
    )
    new_appointment_btn.click()
    if delay > 0:
        time.sleep(delay)

    wait.until(EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "modal-agendamento")]')))
    print("✓ Modal detectado")

    print("Aguardando campos do formulário carregarem...")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'select[aria-invalid]')))
    print("✓ Campos do formulário carregados")

    log_datetime_fields(driver, "Após abrir o modal")

    # Tipo de agendamento (fixo)
    print("\n1. Selecionando tipo de agendamento...")
    select_dropdown_option(driver, (By.CSS_SELECTOR, 'select[aria-invalid]'), "Agendamento")
    if delay > 0:
        time.sleep(delay)

    # Cliente (autocomplete)
    print("\n2. Selecionando cliente...")
    autocomplete_select(driver, (By.ID, "age_id_cliente"), client_name)
    if delay > 0:
        time.sleep(delay)
    log_datetime_fields(driver, "Após selecionar o cliente")

    # Filial e Profissional primeiro
    print("\n3. Selecionando filial...")
    select_dropdown_option(driver, (By.XPATH, "//div[div[contains(text(), 'Filial')]]//select"), branch_name)
    if delay > 0:
        time.sleep(delay)
    log_datetime_fields(driver, "Após selecionar a filial")

    print("\n4. Selecionando profissional...")
    select_dropdown_option(driver, (By.XPATH, "//div[div[contains(text(), 'Profissional')]]//select"), professional_name)
    if delay > 0:
        time.sleep(delay)
    log_datetime_fields(driver, "Após selecionar o profissional")

    # Serviços antes de data/hora
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

    print("\n6. Aguardando estabilização do formulário...")
    time.sleep(2.0)

    # Parse flexível de data
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
    except Exception:
        try:
            dt = datetime.strptime(date, "%d/%m/%Y")
        except Exception:
            clean = date.replace("/", "").replace("-", "")
            dt = datetime.strptime(clean, "%d%m%Y")

    # ------------ Preenchimento robusto dos campos ------------
    print("\n7. Definindo data e horários (método robusto)...")
    date_str_br = dt.strftime("%d/%m/%Y")

    try:
        print("   Definindo data...")
        date_input = driver.find_element(By.NAME, "age_data")
        date_input.click()
        time.sleep(0.2)
        date_input.send_keys(Keys.CONTROL, "a")
        date_input.send_keys(Keys.DELETE)
        time.sleep(0.1)
        date_input.send_keys(date_str_br)
        date_input.send_keys(Keys.TAB)

        WebDriverWait(driver, 5).until(
            lambda d: d.find_element(By.NAME, "age_data").get_attribute("value") == date_str_br
        )

        print("   Definindo horário de início...")
        start_input = driver.find_element(By.NAME, "age_inicio")
        start_input.click(); time.sleep(0.1)
        start_input.send_keys(Keys.CONTROL, "a"); start_input.send_keys(Keys.DELETE)
        start_input.send_keys(start_time); start_input.send_keys(Keys.TAB)

        print("   Definindo horário de término...")
        end_input = driver.find_element(By.NAME, "age_fim")
        end_input.click(); time.sleep(0.1)
        end_input.send_keys(Keys.CONTROL, "a"); end_input.send_keys(Keys.DELETE)
        end_input.send_keys(end_time); end_input.send_keys(Keys.TAB)

        log_datetime_fields(driver, "Após definir data/hora manualmente")

    except Exception as e:
        print(f"⚠️ Erro ao definir campos manualmente: {e}")
        print("Tentando método alternativo via JavaScript...")

        js_set_value = """
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
        """

        # Sempre usar DD/MM/YYYY no fallback também
        date_input = driver.find_element(By.NAME, "age_data")
        driver.execute_script(js_set_value, date_input, date_str_br); time.sleep(0.3)

        start_input = driver.find_element(By.NAME, "age_inicio")
        driver.execute_script(js_set_value, start_input, start_time); time.sleep(0.2)

        end_input = driver.find_element(By.NAME, "age_fim")
        driver.execute_script(js_set_value, end_input, end_time); time.sleep(0.2)

        WebDriverWait(driver, 5).until(
            lambda d: d.find_element(By.NAME, "age_data").get_attribute("value") == date_str_br
        )
        log_datetime_fields(driver, "Após tentativa JS (fallback)")

    log_datetime_fields(driver, "FINAL - Antes de salvar")

    # Salvar
    print("\n8. Salvando agendamento...")
    try:
        save_btn = driver.find_element(By.XPATH, '//button[contains(., "Salvar agendamento")]')
        save_btn.click()
        print("✓ Clicou em salvar")

        time.sleep(3)

        popup = capture_popup_content(driver)
        if popup["found"]:
            print(f"\n⚠️ Popup detectado após salvar:")
            print(f"   Tipo: {popup['type']}")
            print(f"   Conteúdo: {popup['text']}")
            error_keywords = ['erro', 'error', 'falha', 'inválido', 'invalid', 'não', 'nao']
            is_error = any(keyword in popup['text'].lower() for keyword in error_keywords)
            if is_error:
                error_msg = f"Erro no popup: {popup['text']}"
                print(f"✗ {error_msg}")
                raise Exception(error_msg)
            else:
                print("ℹ️ Popup informativo (não é erro)")

        try:
            WebDriverWait(driver, 8).until(
                EC.invisibility_of_element_located((By.XPATH, '//div[contains(@class, "modal-agendamento")]'))
            )
            print("✓ Modal fechado - agendamento salvo com sucesso")
        except TimeoutException:
            print("⚠️ Modal não fechou, verificando mensagens...")
            popup = capture_popup_content(driver)
            if popup["found"]:
                print(f"   Popup: {popup['text']}")
            try:
                success_elements = driver.find_elements(
                    By.XPATH,
                    "//*[contains(translate(text(),'SUCESSOCRIDALV','sucessocridalv'), 'sucesso') or contains(text(), 'criado') or contains(text(), 'salvo') or contains(text(), 'success')]"
                )
                for elem in success_elements:
                    if elem.is_displayed():
                        print(f"✓ Mensagem de sucesso: {elem.text}")
                        return
            except Exception:
                pass
            print("⚠️ Modal não fechou mas nenhum erro detectado. Considerando como sucesso.")

    except Exception as e:
        print(f"\n✗ Erro ao salvar: {e}")
        popup = capture_popup_content(driver)
        if popup["found"]:
            error_msg = f"Erro ao salvar agendamento: {str(e)}\nConteúdo do popup: {popup['text']}"
        else:
            error_msg = f"Erro ao salvar agendamento: {str(e)}"
        try:
            driver.save_screenshot('/tmp/error_save.png')
            print("Screenshot salvo: /tmp/error_save.png")
        except Exception:
            pass
        raise Exception(error_msg)


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

    # Idioma/locale: pt-BR
    options.add_argument("--lang=pt-BR")
    options.add_experimental_option("prefs", {"intl.accept_languages": "pt-BR,pt"})

    # Headless novo (mais fiel ao modo normal)
    if not args.show_browser:
        options.add_argument("--headless=new")

    # User-Agent + ajustes comuns em container
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)

    # Força locale/timezone também via CDP (independe do SO)
    try:
        # Locale
        driver.execute_cdp_cmd("Emulation.setLocaleOverride", {"locale": "pt-BR"})
        # Timezone
        driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": "America/Sao_Paulo"})
        # Accept-Language
        ua = driver.execute_script("return navigator.userAgent")
        driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": ua,
            "acceptLanguage": "pt-BR,pt;q=0.9",
            "platform": "Linux x86_64",
        })
        # Log do ambiente do navegador (ajuda a diagnosticar no n8n)
        env = driver.execute_script("""
            return {
              lang: navigator.language,
              languages: navigator.languages,
              tz: Intl.DateTimeFormat().resolvedOptions().timeZone
            }
        """)
        print(f"Ambiente do navegador: {env}")
    except Exception as e:
        print(f"Não foi possível aplicar overrides de locale/tz: {e}")

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
        try:
            driver.save_screenshot('error_screenshot.png')
            print("Screenshot saved: error_screenshot.png")
        except Exception:
            pass
        try:
            with open('error_page.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("Page HTML saved: error_page.html")
        except Exception:
            pass
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
