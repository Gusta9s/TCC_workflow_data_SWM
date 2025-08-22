# ==============================================================================
# SCRIPT ORQUESTRADOR PARA O PIPELINE DE DADOS SWM (Versão para Windows PowerShell)
#
# Este script realiza as seguintes ações:
# 1. Sobe o container Docker com o modelo de ML.
# 2. Sobe o container Docker com o frontend do Leaflet.
# 3. Executa o pipeline principal em Python (validação, processamento, predição).
# 4. Realiza a limpeza completa do ambiente (derruba containers e imagens).
# ==============================================================================

# --- Configuração de Variáveis ---
# Caminhos do Windows. Usar aspas é uma boa prática.
$ProjectDir = "C:\Projetos\TCC\TCC_workflow_data_SWM"
$ModelDir = "C:\Projetos\TCC\TCC_Model1_CNN_SWM"
$LeafletDir = "C:\Projetos\TCC\TCC-Routing-Machine-SWM"

# Nomes para o Docker
$DockerImageNameModel = "tcc-modelo-cnn"
$DockerImageNameLeaflet = "map-generator-tcc"


# --- Função de Limpeza (Cleanup) ---
# Esta função será chamada sempre que o script terminar, seja por sucesso ou erro.
function Cleanup {
    Write-Host "--- INICIANDO PROCESSO DE LIMPEZA ---" -ForegroundColor Yellow

    # Parar e remover o container Docker do Modelo
    $ContainerIdModel = docker ps -q --filter "ancestor=$DockerImageNameModel"
    if (-not [string]::IsNullOrEmpty($ContainerIdModel)) {
        Write-Host "Parando e removendo o container Docker do Modelo (ID: $ContainerIdModel)..."
        docker rm -f $ContainerIdModel
    } else {
        Write-Host "Nenhum container da imagem '$DockerImageNameModel' em execução."
    }

    # Parar e remover o container Docker do Leaflet pelo nome
    $ContainerIdLeaflet = docker ps -q --filter "name=map-generator-app"
    if (-not [string]::IsNullOrEmpty($ContainerIdLeaflet)) {
        Write-Host "Parando e removendo o container Docker do Leaflet (ID: $ContainerIdLeaflet)..."
        docker rm -f $ContainerIdLeaflet
    } else {
        Write-Host "Nenhum container com o nome 'map-generator-app' em execução."
    }

    # Remover a imagem Docker do Modelo
    $ImageIdModel = docker images -q $DockerImageNameModel
    if (-not [string]::IsNullOrEmpty($ImageIdModel)) {
        Write-Host "Removendo a imagem Docker do Modelo (ID: $ImageIdModel)..."
        docker rmi $ImageIdModel
    } else {
        Write-Host "Nenhuma imagem Docker com o nome '$DockerImageNameModel' encontrada."
    }

    # Remover a imagem Docker do Leaflet
    $ImageIdLeaflet = docker images -q $DockerImageNameLeaflet
    if (-not [string]::IsNullOrEmpty($ImageIdLeaflet)) {
        Write-Host "Removendo a imagem Docker do Leaflet (ID: $ImageIdLeaflet)..."
        docker rmi $ImageIdLeaflet
    } else {
        Write-Host "Nenhuma imagem Docker com o nome '$DockerImageNameLeaflet' encontrada."
    }

    Write-Host "--- LIMPEZA FINALIZADA ---" -ForegroundColor Green
}

# --- Início da Execução ---
# O bloco try/finally garante que a função Cleanup seja chamada no final, mesmo se ocorrer um erro.
# É o equivalente ao 'trap' do Bash.
try {
    Write-Host "====================================================" -ForegroundColor Cyan
    Write-Host "Iniciando orquestrador do pipeline em $(Get-Date)" -ForegroundColor Cyan
    Write-Host "====================================================" -ForegroundColor Cyan

    # --- 1. Setup dos Ambientes Docker ---
    Write-Host "Navegando para o diretório do modelo: $ModelDir"
    Set-Location -Path $ModelDir -ErrorAction Stop

    Write-Host "Construindo a imagem Docker do Modelo: $DockerImageNameModel..."
    docker build -t $DockerImageNameModel .
    if ($LASTEXITCODE -ne 0) { throw "Falha no build da imagem Docker do Modelo." }

    Write-Host "Navegando para o diretório do leaflet: $LeafletDir"
    Set-Location -Path $LeafletDir -ErrorAction Stop

    Write-Host "Construindo a imagem Docker do Leaflet: $DockerImageNameLeaflet..."
    docker build -t $DockerImageNameLeaflet .
    if ($LASTEXITCODE -ne 0) { throw "Falha no build da imagem Docker do Leaflet." }

    Write-Host "Executando o container Docker do modelo em background..."
    docker run -d --rm --add-host=host.docker.internal:host-gateway -p 3001:3001 $DockerImageNameModel

    Write-Host "Executando o container Docker do leaflet em background..."
    docker run -d --rm -p 3004:3004 --name map-generator-app -v "${PWD}\assets\images:/app/assets/images" $DockerImageNameLeaflet

    Write-Host "Aguardando 30 segundos para os serviços iniciarem..."
    Start-Sleep -Seconds 30

    # --- 2. Execução do Pipeline Principal ---
    Write-Host "Navegando para o diretório principal do pipeline: $ProjectDir"
    Set-Location -Path $ProjectDir -ErrorAction Stop

    # O caminho do script de ativação no Windows é '.\.venv\Scripts\Activate.ps1'
    $VenvPath = Join-Path -Path $ProjectDir -ChildPath ".\.venv\Scripts\Activate.ps1"

    if (Test-Path $VenvPath) {
        Write-Host "Ativando o ambiente virtual Python..."
        # A forma de "source" no PowerShell é usando o operador ponto '.'
        . $VenvPath
    } else {
        throw "Erro: Ambiente virtual não encontrado em $VenvPath. Abortando."
    }

    Write-Host "--- EXECUTANDO O SCRIPT PYTHON PRINCIPAL (app.py) ---" -ForegroundColor Green
    python app.py
    $PythonExitCode = $LASTEXITCODE # Salva o código de saída do script python
    Write-Host "--- SCRIPT PYTHON FINALIZADO COM CÓDIGO DE SAÍDA: $PythonExitCode ---" -ForegroundColor Green

    Write-Host "====================================================" -ForegroundColor Cyan
    Write-Host "Pipeline finalizado em $(Get-Date)" -ForegroundColor Cyan
    Write-Host "====================================================" -ForegroundColor Cyan

    # É importante usar exit dentro do bloco try para que o finally seja acionado corretamente
    exit $PythonExitCode
}
finally {
    # Este bloco será executado SEMPRE, seja em caso de sucesso ou de erro no bloco 'try'.
    Cleanup
}