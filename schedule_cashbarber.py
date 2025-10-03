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
eles, melhorando a fiabilidade em ligações mais lentas. Ele usa texto visível
para selecionar valores de menus drop-down e autocompleta clientes/serviços
enviando teclas e escolhendo a primeira sugestão. Caso a interface do utilizador mude,
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
# --- ALTERAÇÃO INICIADA ---
# Adicionada a importação da exceção específica para o tratamento do erro
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
# --- ALTERAÇÃO FINALIZADA ---


def login_to_cashbarber(driver: webdriver.Chrome, email: str, password: str, timeout: int = 15, delay: float = 0.0) -> None:
    """Autentica o utilizador no painel CashBarber.

    Args:
        driver: Uma instância de um WebDriver Selenium já configurado.
        email: O endereço de e-mail usado para o login.
        password: A senha correspondente.
        timeout: Segundos a aguardar para que os elementos fiquem disponíveis.

    Raises:
        TimeoutException: Se os elementos da página de login não puderem ser localizados
            dentro do tempo de espera especificado.
    """
    # Navega para a página de login
    driver.get("https://painel.cashbarber.com.br/auth/login")

    wait = WebDriverWait(driver, timeout)

    # Usa esperas explícitas para todos os elementos para garantir que estão prontos.
    print("Aguardando campo de e-mail...")
    email_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Informe o seu e-mail"]'))
    )
    print("Aguardando campo de senha...")
    password_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Informe sua senha"]'))
    )

    # Limpa qualquer texto pré-preenchido e insere as credenciais
    print("Preenchendo credenciais...")
    email_input.clear()
    email_input.send_keys(email)
    password_input.clear()
    password_input.send_keys(password)

    # Aguarda que o botão de login se torne clicável e depois clica nele.
    print("Aguardando botão de login...")
    login_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(normalize-space(), "Acessar")]'))
    )
    print("Clicando no botão de login...")
    login_button.click()

    # Aguarda até que o painel de controlo seja carregado, verificando um elemento conhecido
    print("Aguardando o carregamento do painel de controlo...")
    wait.until(
        EC.presence_of_element_located((By.XPATH, '//span[contains(., "Olá,")]'))
    )
    print("Login realizado com sucesso!")

    if delay > 0:
        time.sleep(delay)


def open_appointments_page(driver: webdriver.Chrome, timeout: int = 15, delay: float = 0.0) -> None:
    """Navega para a secção de Agendamentos após o login.

    Args:
        driver: Uma instância de um WebDriver Selenium que já fez login.
        timeout: Segundos a aguardar pelo carregamento da página.

    Raises:
        TimeoutException: Se a página de agendamentos não carregar.
    """
    driver.get("https://painel.cashbarber.com.br/agendamento")
    wait = WebDriverWait(driver, timeout)
    # Aguarda que o botão "Novo agendamento" se torne clicável
    wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Novo agendamento")]'))
    )
    if delay > 0:
        time.sleep(delay)


def select_dropdown_option(driver: webdriver.Chrome, select_locator: tuple, option_text: str) -> None:
    """Seleciona uma opção de um elemento HTML `<select>` nativo pelo texto visível.

    Args:
        driver: Instância do WebDriver Selenium.
        select_locator: Tuplo localizador (By, localizador) para o elemento `<select>`.
        option_text: O texto visível da opção a ser escolhida.

    Raises:
        NoSuchElementException: Se a opção não for encontrada.
    """
    select_element = driver.find_element(*select_locator)
    # O `<select>` é um elemento HTML regular. Usa a API do Selenium para selecionar por texto.
    for option in select_element.find_elements(By.TAG_NAME, "option"):
        if option.text.strip().lower() == option_text.strip().lower():
            option.click()
            return
    raise NoSuchElementException(f"Opção '{option_text}' não encontrada no select")


def autocomplete_select(driver: webdriver.Chrome, input_locator: tuple, value: str, timeout: int = 10) -> None:
    """Seleciona um valor de um widget de autocompletar digitando e escolhendo a primeira sugestão.

    A função envia o `value` fornecido para o input de autocompletar e
    seleciona a primeira sugestão da lista. Se nenhuma sugestão
    aparecer, deixa o campo com o valor digitado, assumindo que o widget
    aceita texto livre.

    Args:
        driver: Instância do WebDriver Selenium.
        input_locator: Tuplo localizador (By, localizador) que aponta para o elemento `<input>`
            dentro do componente de autocompletar.
        value: Texto a ser digitado no autocompletar e selecionado.
        timeout: Segundos a aguardar pelo carregamento das sugestões.
    """
    wait = WebDriverWait(driver, timeout)
    input_element = wait.until(EC.presence_of_element_located(input_locator))
    input_element.clear()
    input_element.send_keys(value)

    # Aguarda que a janela de sugestões apareça
    try:
        suggestions_container = wait.until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="presentation"]//li[1]'))
        )
        # Seleciona a primeira sugestão
        suggestions_container.click()
    except TimeoutException:
        # Se nenhuma sugestão aparecer, pressiona Enter para aceitar o valor digitado, se permitido
        input_element.send_keys("\n")


def log_datetime_fields(driver: webdriver.Chrome, step_name: str):
    """Regista os valores atuais dos campos de data e hora para depuração."""
    try:
        # Usa JavaScript para obter o valor atual dos campos de input
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
    """Captura quaisquer pop-ups, alertas ou mensagens de erro visíveis."""
    popup_info = {
        "found": False,
        "type": None,
        "text": None,
        "screenshot_saved": False
    }

    # Verifica alertas do navegador
    try:
        alert = driver.switch_to.alert
        popup_info["found"] = True
        popup_info["type"] = "browser_alert"
        popup_info["text"] = alert.text
        print(f"\n[POPUP] ALERTA DO NAVEGADOR DETETADO:")
        print(f"  Texto: {alert.text}")
        return popup_info
    except:
        pass

    # Verifica seletores comuns de modais/pop-ups
    popup_selectors = [
        "//div[contains(@class, 'modal') and contains(@class, 'show')]",
        "//div[contains(@class, 'alert')]",
        "//div[contains(@class, 'error')]",
        "//div[contains(@class, 'warning')]",
        "//div[@role='dialog']",
        "//div[@role='alertdialog']",
        "//*[contains(@class, 'swal')]",  # SweetAlert
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

                        # Guarda a captura de ecrã
                        try:
                            driver.save_screenshot('/tmp/popup_screenshot.png')
                            popup_info["screenshot_saved"] = True
                        except:
                            pass

                        print(f"\n[POPUP] MODAL/POPUP DETETADO:")
                        print(f"  Seletor: {selector}")
                        print(f"  Texto: {text}")
                        print(f"  Captura de ecrã guardada: {popup_info['screenshot_saved']}")

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
    """Preenche o formulário de agendamento com os valores fornecidos e guarda.

    Args:
        driver: Instância do WebDriver Selenium já navegada para a página de agendamentos.
        client_name: Nome completo ou parcial do cliente a ser selecionado.
        date: Data do agendamento em formato ISO (YYYY-MM-DD).
        start_time: Hora de início (relógio 24h, ex: "14:00").
        end_time: Hora de término (relógio 24h, ex: "14:10").
        branch_name: Nome da filial a ser selecionada.
        professional_name: Nome do profissional que realizará o serviço.
        services: Uma lista de nomes de serviços a serem adicionados ao agendamento.
        timeout: Segundos a aguardar para que os elementos fiquem prontos.

    Raises:
        TimeoutException: Se os elementos necessários não aparecerem a tempo.
        NoSuchElementException: Se uma opção de drop-down esperada não for encontrada.
    """
    wait = WebDriverWait(driver, timeout)

    # Abre o modal
    new_appointment_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Novo agendamento")]'))
    )
    new_appointment_btn.click()
    if delay > 0:
        time.sleep(delay)

    # Aguarda que os campos do modal carreguem
    wait.until(
        EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "modal-agendamento")]'))
    )
    print("✓ Modal detetado")

    # Aguarda que os campos do formulário dentro do modal carreguem
    print("Aguardando campos do formulário carregarem...")
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'select[aria-invalid]'))
    )
    print("✓ Campos do formulário carregados")

    log_datetime_fields(driver, "Após abrir o modal")

    # Seleciona o tipo de agendamento (fixo para "Agendamento")
    print("\n1. Selecionando tipo de agendamento...")
    select_dropdown_option(
        driver,
        (By.CSS_SELECTOR, 'select[aria-invalid]'),
        "Agendamento",
    )
    if delay > 0:
        time.sleep(delay)

    # Define o cliente (autocompletar)
    print("\n2. Selecionando cliente...")
    autocomplete_select(driver, (By.ID, "age_id_cliente"), client_name)
    if delay > 0:
        time.sleep(delay)
    log_datetime_fields(driver, "Após selecionar o cliente")

    # Define a Filial e o Profissional PRIMEIRO
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

    # Adiciona serviços ANTES de definir data/hora
    print("\n5. Adicionando serviços...")
    for service in services:
        print(f"    Adicionando: {service}")
        autocomplete_select(driver, (By.ID, "id_usuario_servico"), service)

        # --- ALTERAÇÃO INICIADA ---
        # 1. Aguarda o pop-up de carregamento (SweetAlert) desaparecer antes de tentar clicar.
        print("    Aguardando o desaparecimento do pop-up de carregamento...")
        try:
            wait.until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "swal2-container"))
            )
        except TimeoutException:
            print("    Pop-up de carregamento não desapareceu, mas prosseguindo com cautela.")
            pass  # Continua mesmo se o pop-up não desaparecer a tempo

        if delay > 0:
            time.sleep(delay)

        plus_btn_locator = (
            By.XPATH,
            "//input[@id='id_usuario_servico']/ancestor::div[contains(@class, 'col-sm-11')]/following-sibling::div[contains(@class, 'col-sm-1')]//button"
        )
        plus_btn = wait.until(EC.element_to_be_clickable(plus_btn_locator))

        # 2. Tenta clicar no botão e, se for intercetado, captura o conteúdo do pop-up.
        try:
            plus_btn.click()
        except ElementClickInterceptedException:
            print("\n⚠️ Clique no botão '+' foi intercetado. Capturando conteúdo do pop-up...")
            popup = capture_popup_content(driver)

            if popup["found"]:
                error_msg = f"O clique foi bloqueado por um pop-up com a mensagem: '{popup['text']}'"
                print(f"✗ {error_msg}")
                raise Exception(error_msg)
            else:
                print("✗ Um pop-up intercetou o clique, mas o conteúdo não pôde ser lido.")
                raise  # Lança a exceção original ElementClickInterceptedException
        # --- ALTERAÇÃO FINALIZADA ---

        if delay > 0:
            time.sleep(delay)

    log_datetime_fields(driver, "Após adicionar serviços")

    # Aguarda mais tempo para que quaisquer operações assíncronas sejam concluídas
    print("\n6. Aguardando estabilização do formulário...")
    time.sleep(2.0)

    # Analisa a data
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
    except Exception:
        try:
            dt = datetime.strptime(date, "%d/%m/%Y")
        except Exception:
            clean = date.replace("/", "").replace("-", "")
            dt = datetime.strptime(clean, "%d%m%Y")

    date_iso = dt.strftime("%Y-%m-%d")

    # AGORA define data/hora usando o método manual (clique + limpar + send_keys)
    # Isto funciona melhor do que a injeção de JS para a validação deste site
    print("\n7. Definindo data e horários (método manual)...")

    try:
        print("    Definindo data...")
        date_input = driver.find_element(By.NAME, "age_data")
        date_input.click()
        time.sleep(0.3)
        date_input.clear()
        time.sleep(0.3)
        date_input.send_keys(dt.strftime("%d/%m/%Y"))
        time.sleep(0.5)

        print("    Definindo horário de início...")
        start_input = driver.find_element(By.NAME, "age_inicio")
        start_input.click()
        time.sleep(0.3)
        start_input.clear()
        time.sleep(0.3)
        start_input.send_keys(start_time)
        time.sleep(0.5)

        print("    Definindo horário de término...")
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

        # Recorre ao método JS se o manual falhar
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

    # Guardar
    print("\n8. Salvando agendamento...")

    try:
        save_btn = driver.find_element(By.XPATH, '//button[contains(., "Salvar agendamento")]')
        save_btn.click()
        print("✓ Clicou em salvar")

        # Aguarda pela resposta
        time.sleep(3)

        # Verifica pop-ups/alertas
        popup = capture_popup_content(driver)
        if popup["found"]:
            print(f"\n⚠️ Popup detetado após salvar:")
            print(f"  Tipo: {popup['type']}")
            print(f"  Conteúdo: {popup['text']}")

            # Verifica se é um pop-up de erro
            error_keywords = ['erro', 'error', 'falha', 'inválido', 'invalid', 'não', 'nao']
            is_error = any(keyword in popup['text'].lower() for keyword in error_keywords)

            if is_error:
                error_msg = f"Erro no popup: {popup['text']}"
                print(f"✗ {error_msg}")
                raise Exception(error_msg)
            else:
                print("ℹ️ Popup informativo (não é erro)")

        # Tenta aguardar que o modal feche
        try:
            wait.until(
                EC.invisibility_of_element_located((By.XPATH, '//div[contains(@class, "modal-agendamento")]')),
                message="Modal não fechou após salvar"
            )
            print("✓ Modal fechado - agendamento salvo com sucesso")
        except TimeoutException:
            # Se o modal não fechar, verifica mensagens de sucesso
            print("⚠️ Modal não fechou, verificando mensagens...")

            # Verifica novamente por pop-ups (podem aparecer com atraso)
            popup = capture_popup_content(driver)
            if popup["found"]:
                print(f"  Popup: {popup['text']}")

            # Procura por indicadores de sucesso
            try:
                success_elements = driver.find_elements(
                    By.XPATH,
                    "//*[contains(text(), 'sucesso') or contains(text(), 'criado') or contains(text(), 'salvo') or contains(text(), 'success')]"
                )
                for elem in success_elements:
                    if elem.is_displayed():
                        print(f"✓ Mensagem de sucesso: {elem.text}")
                        return
            except:
                pass

            # Se nenhuma mensagem de sucesso for encontrada, pode ter funcionado mesmo assim
            print("⚠️ Modal não fechou mas nenhum erro detetado. Considerando como sucesso.")

    except Exception as e:
        # Em qualquer erro, captura o conteúdo do pop-up
        print(f"\n✗ Erro ao salvar: {e}")
        popup = capture_popup_content(driver)

        if popup["found"]:
            error_msg = f"Erro ao salvar agendamento: {str(e)}\nConteúdo do popup: {popup['text']}"
        else:
            error_msg = f"Erro ao salvar agendamento: {str(e)}"

        # Guarda a captura de ecrã
        try:
            driver.save_screenshot('/tmp/error_save.png')
            print("Captura de ecrã salva: /tmp/error_save.png")
        except:
            pass

        raise Exception(error_msg)


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
    parser.add_argument(
        "--service",
        action="append",
        dest="services",
        help="Serviço a adicionar; pode ser fornecido várias vezes",
        required=True,
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Abre o Chrome com uma janela visível (omita para executar em modo headless)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Segundos a aguardar após cada passo para observação (ex: 1.0)",
    )
    args = parser.parse_args()

    options = Options()
    # Adiciona um user-agent comum para evitar deteção básica de bots
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    if not args.show_browser:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)

    try:
        login_to_cashberber(driver, args.email, args.password, delay=args.delay)
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
        driver.save_screenshot('error_screenshot.png')
        with open('error_page.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("Captura de ecrã salva: error_screenshot.png")
        print("HTML da página salvo: error_page.html")
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
