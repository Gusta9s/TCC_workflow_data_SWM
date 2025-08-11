#!/bin/bash

# ==============================================================================
# SCRIPT ORQUESTRADOR PARA O PIPELINE DE DADOS SWM
#
# Este script realiza as seguintes ações:
# 1. Sobe o container Docker com o modelo de ML.
# 2. Inicia o servidor frontend do Leaflet.
# 3. Executa o pipeline principal em Python (validação, processamento, predição).
# 4. Realiza a limpeza completa do ambiente (derruba container, imagem e servidor).
# ==============================================================================

# --- Configuração de Variáveis ---
# Caminhos absolutos para os diretórios dos projetos
PROJECT_DIR="/home/gustavo/Projetos/TCC_workflow_data_SWM"
MODEL_DIR="/home/gustavo/Projetos/TCC_Model1_CNN_SWM"
LEAFLET_DIR="/home/gustavo/Projetos/Routing_Machine_Leaflet_SWM"

# Nomes para o Docker
DOCKER_IMAGE_NAME="tcc-modelo-cnn"

# Arquivo para armazenar o PID do processo do Leaflet
LEAFLET_PID_FILE="/tmp/leaflet_server.pid"


# --- Função de Limpeza (Cleanup) ---
# Esta função será chamada sempre que o script terminar, seja por sucesso ou erro.
cleanup() {
    echo "--- INICIANDO PROCESSO DE LIMPEZA ---"

    # Parar o servidor do Leaflet (npm start)
    if [ -f "$LEAFLET_PID_FILE" ]; then
        LEAFLET_PID=$(cat "$LEAFLET_PID_FILE")
        echo "Parando o servidor do Leaflet (PID: $LEAFLET_PID)..."
        # Usa sudo pois pode ter sido iniciado por um script com sudo
        sudo kill "$LEAFLET_PID" > /dev/null 2>&1
        rm "$LEAFLET_PID_FILE"
    else
        echo "Arquivo de PID do Leaflet não encontrado. Pulando."
    fi

    # Parar e remover o container Docker
    CONTAINER_ID=$(sudo docker ps -q --filter "ancestor=$DOCKER_IMAGE_NAME")
    if [ -n "$CONTAINER_ID" ]; then
        echo "Parando e removendo o container Docker (ID: $CONTAINER_ID)..."
        sudo docker rm -f "$CONTAINER_ID"
    else
        echo "Nenhum container da imagem '$DOCKER_IMAGE_NAME' em execução."
    fi

    # Remover a imagem Docker
    IMAGE_ID=$(sudo docker images -q "$DOCKER_IMAGE_NAME")
    if [ -n "$IMAGE_ID" ]; then
        echo "Removendo a imagem Docker (ID: $IMAGE_ID)..."
        sudo docker rmi "$IMAGE_ID"
    else
        echo "Nenhuma imagem Docker com o nome '$DOCKER_IMAGE_NAME' encontrada."
    fi

    # Desativa o ambiente virtual se ainda estiver ativo
    if command -v deactivate &> /dev/null; then
        deactivate
    fi
    
    echo "--- LIMPEZA FINALIZADA ---"
}

# "trap" garante que a função 'cleanup' seja executada na saída do script (EXIT)
trap cleanup EXIT


# --- Início da Execução ---
echo "===================================================="
echo "Iniciando orquestrador do pipeline em $(date)"
echo "===================================================="


# --- 1. Setup do Ambiente de Backend (Docker) ---
echo "Navegando para o diretório do modelo: $MODEL_DIR"
cd "$MODEL_DIR" || { echo "Falha ao acessar o diretório do modelo. Abortando."; exit 1; }

echo "Construindo a imagem Docker: $DOCKER_IMAGE_NAME..."
sudo docker build -t "$DOCKER_IMAGE_NAME" . || { echo "Falha no build da imagem Docker. Abortando."; exit 1; }

echo "Executando o container Docker em background..."
# O container roda em modo 'detached' por padrão, mas o '&' garante que o script continue
sudo docker run --add-host=host.docker.internal:host-gateway -p 3001:3001 "$DOCKER_IMAGE_NAME" &

echo "Aguardando 30 segundos para o servidor do modelo iniciar..."
sleep 30


# --- 2. Setup do Ambiente de Frontend (Leaflet) ---
echo "Navegando para o diretório do Leaflet: $LEAFLET_DIR"
cd "$LEAFLET_DIR" || { echo "Falha ao acessar o diretório do Leaflet. Abortando."; exit 1; }

echo "Iniciando o servidor do Leaflet (npm start) em background..."
npm start &
# Salva o PID (Process ID) do último comando em background (&)
LEAFLET_PID=$!
echo "$LEAFLET_PID" > "$LEAFLET_PID_FILE"
echo "Servidor do Leaflet iniciado com PID: $LEAFLET_PID"


# --- 3. Execução do Pipeline Principal ---
echo "Navegando para o diretório principal do pipeline: $PROJECT_DIR"
cd "$PROJECT_DIR" || { echo "Falha ao acessar o diretório principal. Abortando."; exit 1; }

VENV_PATH="$PROJECT_DIR/.venv/bin/activate"

if [ -f "$VENV_PATH" ]; then
    echo "Ativando o ambiente virtual Python..."
    source "$VENV_PATH"
else
    echo "Erro: Ambiente virtual não encontrado em $VENV_PATH. Abortando."
    exit 1
fi

echo "--- EXECUTANDO O SCRIPT PYTHON PRINCIPAL (app.py) ---"
python app.py
PYTHON_EXIT_CODE=$? # Salva o código de saída do script python
echo "--- SCRIPT PYTHON FINALIZADO COM CÓDIGO DE SAÍDA: $PYTHON_EXIT_CODE ---"

echo "===================================================="
echo "Pipeline finalizado em $(date)"
echo "===================================================="

# Atingir o final do script acionará o 'trap cleanup EXIT' automaticamente.
exit $PYTHON_EXIT_CODE