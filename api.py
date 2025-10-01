"""
API Flask para criar agendamentos no CashBarber via n8n ou outras ferramentas.

Uso:
    POST /create-appointment
    Body (JSON):
    {
        "email": "seu@email.com",
        "password": "suasenha",
        "client": "Nome do Cliente",
        "date": "2025-10-03",
        "start_time": "11:40",
        "end_time": "11:50",
        "branch": "Centro",
        "professional": "Miguel Oliveira",
        "services": ["Corte de Cabelo"]
    }
"""

from flask import Flask, request, jsonify
import os
import sys
from schedule_cashbarber import (
    login_to_cashbarber,
    open_appointments_page,
    create_appointment
)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import traceback

app = Flask(__name__)

def create_driver():
    """Create a Chrome WebDriver instance with proper options for server environment."""
    options = Options()
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Forçar locale brasileiro - SOLUÇÃO DO PROBLEMA DE DATA
    options.add_argument("--lang=pt-BR")
    options.add_experimental_option("prefs", {
        "intl.accept_languages": "pt-BR,pt,en-US,en"
    })
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    
    # ===== DEBUG: VERIFICAR LOCALE DO CHROME =====
    try:
        locale_info = driver.execute_script("return navigator.language")
        print(f"🌍 Chrome locale detectado: {locale_info}")
        
        # Debug extra: verificar locale do sistema também
        import locale as py_locale
        system_locale = py_locale.getlocale()
        print(f"🖥️  Sistema locale: {system_locale}")
    except Exception as e:
        print(f"⚠️ Não foi possível detectar o locale: {e}")
    # ============================================
    
    return driver

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "cashbarber-automation"}), 200

@app.route('/create-appointment', methods=['POST'])
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
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'client', 'date', 'start_time', 
                          'end_time', 'branch', 'professional', 'services']
        
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        # Validate services is a list
        if not isinstance(data['services'], list) or len(data['services']) == 0:
            return jsonify({
                "success": False,
                "error": "services must be a non-empty array"
            }), 400
        
        # Log da requisição para debug
        print(f"\n📥 Nova requisição recebida:")
        print(f"   Cliente: {data['client']}")
        print(f"   Data: {data['date']}")
        print(f"   Horário: {data['start_time']} - {data['end_time']}")
        
        # Debug de credenciais (mascaradas)
        print(f"🔐 Credenciais recebidas:")
        print(f"   Email: {data['email'][:3]}***@{data['email'].split('@')[1] if '@' in data['email'] else '???'}")
        print(f"   Senha: {'*' * len(data['password'])} ({len(data['password'])} caracteres)")
        
        # Create driver and execute automation
        driver = create_driver()
        
        try:
            # Timeout aumentado para 30 segundos
            login_to_cashbarber(driver, data['email'], data['password'], timeout=30)
            open_appointments_page(driver)
            create_appointment(
                driver,
                client_name=data['client'],
                date=data['date'],
                start_time=data['start_time'],
                end_time=data['end_time'],
                branch_name=data['branch'],
                professional_name=data['professional'],
                services=data['services']
            )
            
            print(f"✅ Agendamento criado com sucesso!")
            
            return jsonify({
                "success": True,
                "message": "Appointment created successfully",
                "data": {
                    "client": data['client'],
                    "date": data['date'],
                    "start_time": data['start_time'],
                    "end_time": data['end_time'],
                    "branch": data['branch'],
                    "professional": data['professional'],
                    "services": data['services']
                }
            }), 200
            
        finally:
            driver.quit()
            
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Erro ao criar agendamento: {error_trace}", file=sys.stderr)
        
        return jsonify({
            "success": False,
            "error": str(e),
            "trace": error_trace
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
