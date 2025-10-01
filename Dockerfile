# Utiliza a imagem oficial do Python 3.11 como base
FROM python:3.11-slim

# --- INÍCIO DA MODIFICAÇÃO: Instalar e configurar o locale pt_BR ---
# Instala o pacote de locales e remove o cache do apt para manter a imagem leve
RUN apt-get update && apt-get install -y locales && rm -rf /var/lib/apt/lists/* && \
    # Descomenta a linha do pt_BR.UTF-8 no arquivo de configuração de locales
    sed -i -e 's/# pt_BR.UTF-8 UTF-8/pt_BR.UTF-8 UTF-8/' /etc/locale.gen && \
    # Gera (compila) o locale pt_BR para que o sistema possa usá-lo
    dpkg-reconfigure --frontend=noninteractive locales

# Define as variáveis de ambiente do sistema para forçar o uso do locale brasileiro
# Isso garante que a formatação de datas, números e moedas siga o padrão do Brasil
ENV LANG pt_BR.UTF-8
ENV LANGUAGE pt_BR:pt
ENV LC_ALL pt_BR.UTF-8
# --- FIM DA MODIFICAÇÃO ---

# Instala o Google Chrome e outras dependências necessárias
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && mkdir -p /etc/apt/keyrings \
    && wget -q -O /etc/apt/keyrings/google-chrome.gpg https://dl-ssl.google.com/linux/linux_signing_key.pub \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Instala o ChromeDriver correspondente à versão do Chrome instalada
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d '.' -f 1) && \
    CHROMEDRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_VERSION}") && \
    wget -q -O /tmp/chromedriver-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver-linux64.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver*

# Define o diretório de trabalho da aplicação
WORKDIR /app

# Copia o arquivo de dependências primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia os arquivos da aplicação para o diretório de trabalho
COPY schedule_cashbarber.py .
COPY api.py .

# Expõe a porta que a aplicação Flask irá rodar
EXPOSE 5000

# Define variáveis de ambiente para a execução
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Comando para iniciar a aplicação usando Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "api:app"]
