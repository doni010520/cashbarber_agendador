"""
Automação de login e criação de agendamento no CashBarber via Selenium.

Melhorias-chave:
- Remove dependência do seletor frágil `select[aria-invalid]` (a UI pode não ter esse atributo)
  e usa um helper tolerante para definir o "Tipo" (select nativo, radios/segmented ou assume padrão).
- Preenchimento resiliente de data/hora: detecta <input type="date/time"> e usa ISO/HH:MM via JS;
  em inputs mascarados, digita só dígitos e valida o valor no MESMO elemento.
- Força locale pt-BR e timezone America/Sao_Paulo no headless, reduzindo confusões de DD/MM vs MM/DD.
- Esperas mais estáveis no modal (botão "Salvar agendamento" + inputs de data/hora).
- Captura e interpretação de popups (SweetAlert/toast/alert) para confirmar sucesso/erros.
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
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)


# ========================= Helpers Gerais =========================

def _wait_until_value(driver, element, expected_values, timeout=10):
    """Espera até o elemento ter um dos valores esperados."""
    if isinstance(expected_values, str):
        expected_values = [expected_values]

    def _ok(_):
        try:
            val = element.get_attribute("value") or ""
            return val in expected_values
        except Exception:
            return False

    WebDriverWait(driver, timeout).until(_ok)


def _clear(element):
    """Limpa input com CTRL+A + DELETE (mais confiável em inputs mascarados)."""
    element.send_keys(Keys.CONTROL, "a")
    element.send_keys(Keys.DELETE)


def _set_with_js(driver, element, value):
    """Define valor via JS e dispara eventos para frameworks (React/Vue/etc.)."""
    js = """
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));
    """
    driver.execute_script(js, element, value)


def _first_visible_by_name(driver, name):
    """Retorna o primeiro elemento visível (ou o primeiro existente) com determinado name."""
    try:
        el = driver.execute_script("""
            const name = arguments[0];
            const els = Array.from(document.getElementsByName(name));
            return els.find(e => !!(e.offsetParent) && e.getBoundingClientRect().width > 0 && e.getBoundingClientRect().height > 0) || els[0] || null;
        """, name)
        if el:
            return el
    except Exception:
        pass
    # Fallback Selenium direto
    return driver.find_element(By.NAME, name)


def log_datetime_fields(driver, step_name: str):
    """Loga valores dos campos de data/hora (considera múltiplos inputs)."""
    try:
        vals = driver.execute_script("""
            const out = {};
            out.type_date = (document.getElementsByName('age_data')[0]||{}).type || '';
            out.date  = Array.from(document.getElementsByName('age_data')).map(e => e.value);
            out.start = Array.from(document.getElementsByName('age_inicio')).map(e => e.value);
            out.end   = Array.from(document.getElementsByName('age_fim')).map(e => e.value);
            return out;
        """)
        print(f"\n--- LOG [{step_name}] ---")
        print(f"    type(age_data): {vals.get('type_date')}")
        print(f"    age_data      : {vals.get('date')}")
        print(f"    age_inicio    : {vals.get('start')}")
        print(f"    age_fim       : {vals.get('end')}")
        print("----------------------------------\n")
    except Exception as e:
        print(f"\n--- LOG [{step_name}] ---")
        print(f"    Falha lendo campos: {e}")
        print("----------------------------------\n")


def capture_popup_content(driver: webdriver.Chrome, timeout: int = 8) -> dict:
    """Captura texto de popups (SweetAlert/alert/toast)."""
    wait = WebDriverWait(driver, timeout)
    try:
        popup_element = wait.until(EC.visibility_of_element_located((
            By.XPATH,
            "//*[contains(@class,'swal2-container') or contains(@class,'toast') or contains(@class,'alert') or @role='alertdialog' or @role='alert']"
        )))
        text = popup_element.text.strip()
        print(f"[CAPTURE] Pop-up detectado: '{text}'")
        return {"found": True, "text": text}
    except TimeoutException:
        print("[CAPTURE] Nenhum pop-up detectado.")
        return {"found": False, "text": ""}


def handle_sweetalert_popup(driver: webdriver.Chrome, timeout: int = 3):
    """Se houver um SweetAlert aberto, tenta clicar em 'OK' e fechar."""
    try:
        wait = WebDriverWait(driver, timeout)
        swal_container = wait.until(EC.visibility_of_element_located((
            By.XPATH, "//*[contains(@class, 'swal2-container')]"
        )))
        print("    [Popup Handler] SweetAlert detectado.")
        try:
            confirm_button = swal_container.find_element(By.XPATH, ".//button[contains(@class, 'swal2-confirm')]")
            print("    [Popup Handler] Clicando 'OK'.")
            confirm_button.click()
            wait.until(EC.invisibility_of_element(swal_container))
            print("    [Popup Handler] Pop-up fechado.")
        except (NoSuchElementException, TimeoutException):
            print("    [Popup Handler] Não foi possível fechar o SweetAlert.")
    except TimeoutException:
        # silencioso
        pass


def try_set_tipo_agendamento(driver, desired: str = "Agendamento", timeout: int = 6, delay: float = 0.0) -> None:
    """Tenta definir o 'Tipo' para 'Agendamento' em diferentes UIs (select, radios, custom).
       Se não encontrar, assume que o padrão já é 'Agendamento' e segue sem erro.
    """
    wait = WebDriverWait(driver, timeout)

    # Escopo: o modal do agendamento
    modal = wait.until(
        EC.presence_of_element_located((
            By.XPATH,
            '//div[contains(@class,"modal-agendamento") or @role="dialog" or contains(@class,"modal")]'
        ))
    )

    # 1) Qualquer <select> no modal cujo options contenham 'Agendamento'
    try:
        selects = modal.find_elements(By.TAG_NAME, "select")
        for sel in selects:
            try:
                options = sel.find_elements(By.TAG_NAME, "option")
                for opt in options:
                    if opt.text.strip().lower() == desired.lower():
                        sel.click()
                        opt.click()
                        if delay > 0: time.sleep(delay)
                        print("✓ Tipo de agendamento selecionado via <select>.")
                        return
            except StaleElementReferenceException:
                continue
    except Exception:
        pass

    # 2) Rádio/segmented/custom: clique em algo com texto 'Agendamento'
    try:
        candidates = modal.find_elements(
            By.XPATH,
            './/*[self::label or self::span or self::div or self::button or self::a or self::li]'
            '[contains(normalize-space(), "%s")]' % desired
        )
        for el in candidates:
            try:
                if el.is_displayed() and el.is_enabled():
                    el.click()
                    if delay > 0: time.sleep(delay)
                    print("✓ Tipo de agendamento selecionado via componente custom.")
                    return
            except Exception:
                continue
    except Exception:
        pass

    # 3) Se nada encontrado, não falhe — assuma padrão e registre
    print(f"ℹ️ Campo 'Tipo' não encontrado/necessário. Assumindo padrão '{desired}'.")


def _set_date_time_fields(driver, dt: datetime, start_time: str, end_time: str):
    """Define campos de data/hora de forma resiliente (inputs nativos ou mascarados)."""

    # DATA
    date_input = _first_visible_by_name(driver, "age_data")
    date_type = (date_input.get_attribute("type") or "").lower()
    print(f"Tipo do campo de data: '{date_type or 'desconhecido'}'")

    ddmmyyyy = dt.strftime("%d/%m/%Y")
    iso_date = dt.strftime("%Y-%m-%d")

    try:
        date_input.click(); time.sleep(0.15)
    except ElementNotInteractableException:
        driver.execute_script("arguments[0].focus()", date_input)

    if date_type == "date":
        # Para <input type="date">, defina ISO
        _set_with_js(driver, date_input, iso_date)
        _wait_until_value(driver, date_input, iso_date, timeout=10)
    else:
        # Inputs mascarados: digite apenas dígitos para a máscara formatar
        _clear(date_input)
        digits = dt.strftime("%d%m%Y")
        for ch in digits:
            date_input.send_keys(ch)
            time.sleep(0.02)
        date_input.send_keys(Keys.TAB)
        _wait_until_value(driver, date_input, [ddmmyyyy, iso_date], timeout=10)

    # HORA INÍCIO
    start_input = _first_visible_by_name(driver, "age_inicio")
    start_type = (start_input.get_attribute("type") or "").lower()
    try:
        start_input.click(); time.sleep(0.1)
    except ElementNotInteractableException:
        driver.execute_script("arguments[0].focus()", start_input)

    if start_type == "time":
        _set_with_js(driver, start_input, start_time)
        _wait_until_value(driver, start_input, start_time, timeout=8)
    else:
        _clear(start_input)
        for ch in start_time.replace(":", ""):
            start_input.send_keys(ch)
            time.sleep(0.02)
        start_input.send_keys(Keys.TAB)
        _wait_until_value(driver, start_input, start_time, timeout=8)

    # HORA FIM
    end_input = _first_visible_by_name(driver, "age_fim")
    end_type = (end_input.get_attribute("type") or "").lower()
    try:
        end_input.click(); time.sleep(0.1)
    except ElementNotInteractableException:
        driver.execute_script("arguments[0].focus()", end_input)

    if end_type == "time":
        _set_with_js(driver, end_input, end_time)
        _wait_until_value(driver, end_input, end_time, timeout=8)
    else:
        _clear(end_input)
        for ch in end_time.replace(":", ""):
            end_input.send_keys(ch)
            time.sleep(0.02)
        end_input.send_keys(Keys.TAB)
        _wait_until_value(driver, end_input, end_time, timeout=8)


# ========================= Fluxo CashBarber =========================

def login_to_cashbarber(driver: webdriver.Chrome, email: str, password: str, timeout: int = 20, delay: float = 0.0) -> None:
    """Autentica o usuário no painel CashBarber."""
    driver.get("https://painel.cashbarber.com.br/auth/login")
    wait = WebDriverWait(driver, timeout)
    print("Aguardando campo de e-mail...")
    email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Informe o seu e-mail"]')))
    print("Aguardando campo de senha...")
    password_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Informe sua senha"]')))

    print("Preenchendo credenciais...")
    email_input.clear(); email_input.send_keys(email)
    password_input.clear(); password_input.send_keys(password)

    print("Aguardando botão de login...")
    login_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(normalize-space(), "Acessar")]')))
    print("Clicando no botão de login...")
    login_button.click()

    print("Aguardando o carregamento do painel de controle...")
    wait.until(EC.presence_of_element_located((By.XPATH, '//span[contains
