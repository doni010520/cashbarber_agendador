"""
Este script automatiza o processo de login no painel CashBarber e a
criação de um novo agendamento usando Selenium. Ele encapsula passos
comuns como navegar para a página de login, inserir credenciais, abrir o
calendário de agendamentos e preencher os campos necessários. O script
foi projetado como um módulo reutilizável — funções individuais executam
uma parte distinta do fluxo de trabalho e podem ser reutilizadas ou
estendidas em outros projetos.

Uso:

```
python schedule_cashberber.py --email SEU_EMAIL \
    --password SUA_SENHA \
    --client "Nome do Cliente" \
    --date 2025-09-30 \
    --start-time 14:00 \
    --end-time 14:10 \
    --branch "Centro" \
    --professional "Miguel Oliveira" \
    --service "Corte de Cabelo"
```

O script aguarda que os elementos interativos apareçam antes de interagir
com eles, melhorando a confiabilidade em conexões mais lentas. Ele usa
texto visível para selecionar valores de menus suspensos e preenche
automaticamente clientes/serviços enviando teclas e escolhendo a primeira
sugestão. Se a interface do usuário mudar, os seletores podem precisar
de ajuste.

**Aviso**: Este código é fornecido para fins educacionais. Executar
scripts automatizados contra um sistema em produção sem permissão pode
violar os termos de serviço. Sempre garanta que você tem autorização para
automatizar ações em qualquer site.
"""

import argparse
import sys
from typing import List
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from datetime import datetime
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def login_to_cashbarber(driver: webdriver.Chrome, email: str, password: str, timeout: int = 15, delay: float = 0.0) -> None:
    """Autentica o usuário no painel CashBarber."""
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
    wait.until(
        EC.presence_of_element_located((By.XPATH, '//span[contains(., "Olá,")]'))
    )
    print("✓ Login realizado com sucesso!")
    
    if delay > 0:
        time.sleep(delay)


def open_appointments_page(driver: webdriver.Chrome, timeout: int = 15, delay: float = 0.0) -> None:
    """Navega para a seção de Agendamentos após o login."""
    driver.get("https://painel.cashbarber.com.br/agendamento")
    wait = WebDriverWait(driver, timeout)
    wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Novo agendamento")]'))
    )
    if delay > 0:
        time.sleep(delay)


def select_dropdown_option(driver: webdriver.Chrome, select_locator: tuple, option_text: str) -> None:
    """Seleciona uma opção de um elemento <select> pelo texto visível."""
    select_element = driver.find_element(*select_locator)
    for option in select_element.find_elements(By.TAG_NAME, "option"):
        if option.text.strip().lower() == option_text.strip().lower():
            option.click()
            return
    raise NoSuchElementException(f"Opção '{option_text}' não encontrada no seletor")


def autocomplete_select(driver: webdriver.Chrome, input_locator: tuple, value: str, timeout: int = 10) -> None:
    """Seleciona um valor de um campo de autocompletar."""
    wait = WebDriverWait(driver, timeout)
    input_element = wait.until(EC.presence_of_element_located(input_locator))
    input_element.clear()
    input_element.send_keys(value)

    try:
        suggestions_container = wait.until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="presentation"]//li[1]'))
        )
        suggestions_container.click()
    except TimeoutException:
        input_element.send_keys(Keys.ENTER)


def log_datetime_fields(driver: webdriver.Chrome, step_name: str):
    """Registra os valores atuais dos campos de data e hora para depuração."""
    try:
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


def capture_popup_content(driver: webdriver.Chrome):
    """Captura o conteúdo de qualquer popup, alerta ou mensagem de erro visível."""
    popup_info = {"found": False, "type": None, "text": None}
    
    try:
        alert = driver.switch_to.alert
        popup_info.update({"found": True, "type": "browser_alert", "text": alert.text})
        print(f"\n[POPUP] Alerta do navegador detectado: {alert.text}")
        return popup_info
    except Exception:
        pass
    
    popup_selectors = [
        "//div[contains(@class, 'modal') and contains(@class, 'show')]",
        "//div[contains(@class, 'alert')]", "//div[@role='alert']",
        "//*[contains(@class, 'swal')]", "//div[@role='dialog']",
        "//*[contains(@class, 'toast')]", "//*[contains(text(), 'sucesso') or contains(text(), 'erro')]"
    ]
    
    for selector in popup_selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            for element in elements:
                if element.is_displayed():
                    text = element.text.strip()
                    if text:
                        popup_info.update({"found": True, "type": "modal/popup", "text": text})
                        print(f"\n[POPUP] Modal/Popup detectado: {text}")
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
    """Preenche o formulário de agendamento com os valores fornecidos e salva."""
    wait = WebDriverWait(driver, timeout)

    # 1. Abrir o modal
    print("Abrindo modal de novo agendamento...")
    new_appointment_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Novo agendamento")]'))
    )
    new_appointment_btn.click()

    # 2. Esperar o modal carregar
    wait.until(
        EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "modal-agendamento")]'))
    )
    print("✓ Modal detectado e carregado")

    # 3. Preencher campos que disparam atualizações
    print("\nPreenchendo informações principais...")
    select_dropdown_option(driver, (By.CSS_SELECTOR, 'select[aria-invalid]'), "Agendamento")
    autocomplete_select(driver, (By.ID, "age_id_cliente"), client_name)
    select_dropdown_option(driver, (By.XPATH, "//div[div[contains(text(), 'Filial')]]//select"), branch_name)
    select_dropdown_option(driver, (By.XPATH, "//div[div[contains(text(), 'Profissional')]]//select"), professional_name)

    if delay > 0: time.sleep(delay)

    # 4. Adicionar serviços e esperar o formulário estabilizar
    print("\nAdicionando serviços...")
    for service in services:
        print(f"  Adicionando: {service}")
        autocomplete_select(driver, (By.ID, "id_usuario_servico"), service)

        plus_btn_locator = (By.XPATH, "//input[@id='id_usuario_servico']/ancestor::div[contains(@class, 'col-sm-11')]/following-sibling::div//button")
        plus_btn = wait.until(EC.element_to_be_clickable(plus_btn_locator))
        plus_btn.click()
        
        # Espera inteligente: aguarda o formulário estar pronto para a próxima ação
        wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Salvar agendamento")]')))
        print(f"  ✓ Serviço '{service}' adicionado e formulário estável.")
        if delay > 0: time.sleep(delay)

    # 5. Definir data e horários com o método mais confiável
    print("\nDefinindo data e horários...")
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        dt = datetime.strptime(date, "%d/%m/%Y")
    
    # **SOLUÇÃO DEFINITIVA**: Injetar data no formato ISO via JavaScript
    date_iso_format = dt.strftime("%Y-%m-%d")
    try:
        print(f"  Definindo data via JS para: {date_iso_format}")
        date_input = driver.find_element(By.NAME, "age_data")
        js_set_value = """
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
        """
        driver.execute_script(js_set_value, date_input, date_iso_format)
        print("  ✓ Data definida com sucesso via JS.")
        time.sleep(0.5)

    except Exception as e:
        print(f"⚠️ Erro crítico ao definir a data via JavaScript: {e}")
        raise

    # Usar método de digitação para os campos de hora, que são mais simples
    try:
        start_input = driver.find_element(By.NAME, "age_inicio")
        start_input.click(); time.sleep(0.2)
        start_input.clear()
        start_input.send_keys(start_time)
        start_input.send_keys(Keys.TAB)

        end_input = driver.find_element(By.NAME, "age_fim")
        end_input.click(); time.sleep(0.2)
        end_input.clear()
        end_input.send_keys(end_time)
        end_input.send_keys(Keys.TAB)
        print("  ✓ Horários definidos.")

    except Exception as e:
        print(f"⚠️ Erro ao definir campos de hora: {e}")
        raise

    log_datetime_fields(driver, "FINAL - Antes de salvar")

    # 6. Salvar e verificar o resultado
    print("\nSalvando agendamento...")
    try:
        save_btn = driver.find_element(By.XPATH, '//button[contains(., "Salvar agendamento")]')
        save_btn.click()
        
        # Espera explícita pela confirmação de sucesso ou fechamento do modal
        WebDriverWait(driver, 10).until(
            EC.any_of(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'sucesso')]")),
                EC.invisibility_of_element_located((By.XPATH, '//div[contains(@class, "modal-agendamento")]'))
            )
        )
        print("✓ Agendamento salvo com sucesso!")

    except TimeoutException:
        print("\n⚠️ A confirmação de sucesso não apareceu ou o modal não fechou.")
        popup = capture_popup_content(driver)
        if popup["found"] and any(err in popup["text"].lower() for err in ['erro', 'falha', 'inválido']):
            error_msg = f"Popup de erro detectado: {popup['text']}"
            print(f"✗ {error_msg}")
            raise Exception(error_msg)
        else:
            print("✓ Nenhum erro explícito encontrado, mas a confirmação falhou. Verifique o painel.")
    except Exception as e:
        print(f"\n✗ Erro ao clicar em salvar: {e}")
        capture_popup_content(driver)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Automatiza a criação de agendamentos no CashBarber.")
    parser.add_argument("--email", required=True, help="E-mail de login do CashBarber")
    parser.add_argument("--password", required=True, help="Senha de login do CashBarber")
    parser.add_argument("--client", required=True, help="Nome do cliente para agendar")
    parser.add_argument("--date", required=True, help="Data do agendamento (YYYY-MM-DD ou DD/MM/YYYY)")
    parser.add_argument("--start-time", required=True, help="Hora de início (HH:MM, 24h)")
    parser.add_argument("--end-time", required=True, help="Hora de término (HH:MM, 24h)")
    parser.add_argument("--branch", required=True, help="Nome da filial")
    parser.add_argument("--professional", required=True, help="Nome do profissional")
    parser.add_argument(
        "--service", action="append", dest="services",
        help="Serviço a ser adicionado; pode ser usado várias vezes", required=True,
    )
    parser.add_argument(
        "--show-browser", action="store_true",
        help="Abre o Chrome com uma janela visível (omitir para rodar em modo headless)",
    )
    parser.add_argument(
        "--delay", type=float, default=0.0,
        help="Segundos para esperar após cada passo para observação (ex: 1.0)",
    )
    args = parser.parse_args()

    options = Options()
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
        print("\n✓ Processo finalizado com sucesso.")
    except Exception as exc:
        print(f"\n✗ Ocorreu um erro: {exc}", file=sys.stderr)
        try:
            driver.save_screenshot('error_screenshot.png')
            with open('error_page.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("Screenshot salvo em: error_screenshot.png")
            print("HTML da página salvo em: error_page.html")
        except Exception as save_err:
            print(f"Não foi possível salvar os artefatos de depuração: {save_err}")
        sys.exit(1)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
