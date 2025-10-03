"""
Este script automatiza o processo de login no painel CashBarber e
a criação de um novo agendamento usando Selenium. Ele encapsula
passos comuns como navegar para a página de login, inserir credenciais,
abrir o calendário de agendamentos e preencher os campos necessários. O
script foi projetado como um módulo reutilizável — funções individuais
realizam uma parte distinta do fluxo de trabalho e podem ser reutilizadas ou
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

O script aguarda que os elementos interativos apareçam antes de interagir com
eles, melhorando a confiabilidade em conexões mais lentas. Ele usa texto visível
para selecionar valores de menus drop-down e autocompleta clientes/serviços
enviando teclas e escolhendo a primeira sugestão. Caso a interface do usuário mude,
os seletores podem precisar de ajuste.

**Aviso**: Este código é fornecido para fins educacionais. Executar
scripts automatizados contra um sistema em produção sem permissão pode
violar os termos de serviço. Certifique-se sempre de que tem autorização para
automatizar ações em qualquer site.
"""

import argparse
import sys
from typing import List
import time  # Adicionado para atrasos opcionais

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys  # para atalhos de teclado
from datetime import datetime  # para analisar datas
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException


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
    print("Login realizado com sucesso!")
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
    """Seleciona uma opção de um elemento HTML `<select>` nativo pelo texto visível."""
    select_element = driver.find_element(*select_locator)
    for option in select_element.find_elements(By.TAG_NAME, "option"):
        if option.text.strip().lower() == option_text.strip().lower():
            option.click()
            return
    raise NoSuchElementException(f"Opção '{option_text}' não encontrada no select")


def autocomplete_select(driver: webdriver.Chrome, input_locator: tuple, value: str, timeout: int = 10) -> None:
    """Seleciona um valor de um widget de autocompletar digitando e escolhendo a primeira sugestão."""
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
        input_element.send_keys("\n")


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

# --- NOVO HELPER DE FALLBACK ---
def handle_sweetalert_popup(driver: webdriver.Chrome, timeout: int = 3):
    """
    Verifica se um pop-up SweetAlert está visível e tenta fechá-lo clicando no botão de confirmação.
    """
    try:
        # Usa uma espera curta para ver se o pop-up aparece
        wait = WebDriverWait(driver, timeout)
        swal_container = wait.until(
            EC.visibility_of_element_located((By.XPATH, "//*[contains(@class, 'swal2-container')]"))
        )
        print("    [Popup Handler] SweetAlert detectado.")
        
        # Tenta encontrar e clicar no botão "OK" ou "Confirmar"
        try:
            confirm_button = swal_container.find_element(By.XPATH, ".//button[contains(@class, 'swal2-confirm')]")
            print("    [Popup Handler] Clicando no botão 'OK' do pop-up.")
            confirm_button.click()
            
            # Aguarda o pop-up desaparecer após o clique para confirmar que foi fechado
            WebDriverWait(driver, 5).until(EC.invisibility_of_element(swal_container))
            print("    [Popup Handler] Pop-up fechado com sucesso.")
        except (NoSuchElementException, TimeoutException):
            print("    [Popup Handler] AVISO: Pop-up detectado, mas não foi possível fechá-lo.")
            # Se não conseguir fechar, apenas segue em frente e deixa a próxima ação falhar (se for o caso)
            
    except TimeoutException:
        # Caso bom: nenhum pop-up apareceu dentro do tempo de espera.
        print("    [Popup Handler] Nenhum pop-up SweetAlert detectado.")

def capture_popup_content(driver: webdriver.Chrome):
    """Captura quaisquer pop-ups, alertas ou mensagens de erro visíveis."""
    popup_info = {"found": False, "type": None, "text": None}
    try:
        alert = driver.switch_to.alert
        popup_info.update({"found": True, "type": "browser_alert", "text": alert.text})
        print(f"\n[POPUP] ALERTA DO NAVEGADOR DETECTADO: {alert.text}")
        return popup_info
    except:
        pass

    popup_selectors = [
        "//*[contains(@class, 'swal2-container')]",
        "//*[contains(@class, 'toast')]",
        "//div[contains(@class, 'alert')]",
    ]
    for selector in popup_selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            for element in elements:
                if element.is_displayed():
                    text = element.text.strip()
                    if text:
                        popup_info.update({"found": True, "type": "modal/popup", "text": text})
                        print(f"\n[POPUP] MODAL/POPUP DETECTADO: {text}")
                        return popup_info
        except:
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
    new_appointment_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Novo agendamento")]'))
    )
    new_appointment_btn.click()
    if delay > 0:
        time.sleep(delay)

    wait.until(EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "modal-agendamento")]')))
    print("✓ Modal de agendamento aberto.")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'select[aria-invalid]')))
    print("✓ Campos do formulário carregados.")
    log_datetime_fields(driver, "Após abrir o modal")

    # --- INÍCIO DA ORDEM DE PREENCHIMENTO ---

    print("\n1. Selecionando tipo de agendamento...")
    select_dropdown_option(driver, (By.CSS_SELECTOR, 'select[aria-invalid]'), "Agendamento")

    print("\n2. Selecionando cliente...")
    autocomplete_select(driver, (By.ID, "age_id_cliente"), client_name)
    time.sleep(1)
    log_datetime_fields(driver, "Após selecionar o cliente")
    
    print("\n3. Definindo data e horários...")
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
    except:
        dt = datetime.strptime(date, "%d/%m/%Y")
    
    try:
        date_input = driver.find_element(By.NAME, "age_data")
        date_input.click(); time.sleep(0.2)
        date_input.clear(); time.sleep(0.2)
        date_input.send_keys(dt.strftime("%d/%m/%Y")); time.sleep(0.3)

        start_input = driver.find_element(By.NAME, "age_inicio")
        start_input.click(); time.sleep(0.2)
        start_input.clear(); time.sleep(0.2)
        start_input.send_keys(start_time); time.sleep(0.3)

        end_input = driver.find_element(By.NAME, "age_fim")
        end_input.click(); time.sleep(0.2)
        end_input.clear(); time.sleep(0.2)
        end_input.send_keys(end_time); time.sleep(0.3)
        log_datetime_fields(driver, "Após definir data/hora")
    except Exception as e:
        print(f"⚠️ Erro ao definir campos de data/hora: {e}")

    print("\n4. Selecionando filial...")
    select_dropdown_option(driver, (By.XPATH, "//div[div[contains(text(), 'Filial')]]//select"), branch_name)

    print("\n5. Selecionando profissional...")
    select_dropdown_option(driver, (By.XPATH, "//div[div[contains(text(), 'Profissional')]]//select"), professional_name)
    time.sleep(1)
    
    print("\n6. Adicionando serviços...")
    for service in services:
        print(f"    Adicionando: {service}")
        autocomplete_select(driver, (By.ID, "id_usuario_servico"), service)
        
        # Chama a função de fallback para fechar pop-ups
        handle_sweetalert_popup(driver)

        try:
            plus_btn_locator = (By.XPATH, "//input[@id='id_usuario_servico']/ancestor::div[contains(@class, 'col-sm-11')]/following-sibling::div[contains(@class, 'col-sm-1')]//button")
            plus_btn = wait.until(EC.element_to_be_clickable(plus_btn_locator))
            driver.execute_script("arguments[0].click();", plus_btn)
            print("    Botão '+' clicado.")
            time.sleep(1)
        except Exception as e:
            print(f"    Falha ao clicar no botão '+' mesmo após o tratamento do pop-up: {e}")
            popup = capture_popup_content(driver)
            if popup["found"]:
                raise Exception(f"Erro final ao adicionar serviço. Pop-up encontrado: '{popup['text']}'")
            else:
                raise

    log_datetime_fields(driver, "FINAL - Antes de salvar")

    # 7. Salvar
    print("\n7. Salvando agendamento...")
    try:
        save_btn = driver.find_element(By.XPATH, '//button[contains(., "Salvar agendamento")]')
        save_btn.click()
        print("✓ Clicou em salvar.")
        time.sleep(3)
        
        # Verificação final
        try:
            wait.until(EC.invisibility_of_element_located((By.XPATH, '//div[contains(@class, "modal-agendamento")]')))
            print("✓ Agendamento salvo com sucesso (modal fechou).")
        except TimeoutException:
            popup = capture_popup_content(driver)
            if popup['found'] and any(keyword in popup['text'].lower() for keyword in ['erro', 'falha', 'inválido']):
                 raise Exception(f"Erro após salvar: {popup['text']}")
            else:
                print("⚠️ Modal não fechou, mas nenhum erro explícito foi detectado. Considerado sucesso.")
            
    except Exception as e:
        print(f"\n✗ Erro ao salvar: {e}")
        driver.save_screenshot('/tmp/error_save.png')
        raise

def main() -> None:
    parser = argparse.ArgumentParser(description="Automatiza o agendamento no CashBarber.")
    parser.add_argument("--email", required=True, help="E-mail de login do CashBarber")
    parser.add_argument("--password", required=True, help="Senha de login do CashBarber")
    parser.add_argument("--client", required=True, help="Nome do cliente para agendamento")
    parser.add_argument("--date", required=True, help="Data do agendamento (YYYY-MM-DD ou DD/MM/YYYY)")
    parser.add_argument("--start-time", required=True, help="Hora de início (HH:MM, 24h)")
    parser.add_argument("--end-time", required=True, help="Hora de término (HH:MM, 24h)")
    parser.add_argument("--branch", required=True, help="Nome da filial")
    parser.add_argument("--professional", required=True, help="Nome do profissional")
    parser.add_argument("--service", action="append", dest="services", required=True)
    parser.add_argument("--show-browser", action="store_true")
    parser.add_argument("--delay", type=float, default=0.0)
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
        print("\n✓ Agendamento criado com sucesso.")
    except Exception as exc:
        print(f"\n✗ Ocorreu um erro: {exc}", file=sys.stderr)
        try:
            driver.save_screenshot('error_screenshot.png')
            with open('error_page.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("Captura de tela e HTML da página salvos.")
        except:
            print("Não foi possível salvar os artefatos de erro.")
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    main()

