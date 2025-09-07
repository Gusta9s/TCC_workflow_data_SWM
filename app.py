# app.py
import yaml
import os
import sys
from datetime import datetime
import time
from src.tcc_job_processor import file_manager, image_handler, api_client

def previsao_insuficiente(start_timestamp, image_path, prediction_result, config):
    """Função para tratar previsões insuficientes."""
    rejection_data = {
            'start_timestamp': start_timestamp,
            'processed_image': os.path.basename(image_path) if image_path else 'N/A',
            **prediction_result
        }
    result_file = file_manager.write_result(config['results_dir'], 'failure', rejection_data)
    print(f"Resultado de rejeição salvo em: {result_file}")
    sys.exit(1)

def load_config():
    """Carrega o arquivo de configuração config.yaml."""
    try:
        with open('config.yaml', 'r') as f:
            arquivo_yaml = yaml.safe_load(f)
            print("Configuração carregada com sucesso.")
            return arquivo_yaml
    except FileNotFoundError:
        print("Erro: 'config.yaml' não encontrado.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Erro ao ler o arquivo YAML: {e}")
        sys.exit(1)

def main():
    """Função principal que orquestra o pipeline."""
    logs = {}
    pipeline_start_time = time.perf_counter()
    start_timestamp = datetime.now().isoformat()
    config = load_config()
    downloaded_image_path = None
    resized_image_path = None
    
    try:
        step_start_time = time.perf_counter()
        # 1. Encontrar e baixar a imagem mais recente do Backblaze B2
        downloaded_image_path = image_handler.find_and_download_latest_image_from_b2(
            config['b2_storage']
        )
        logs['tempo_extracao_blackblaze'] = time.perf_counter() - step_start_time
        
        # 2. Validar a imagem
        step_start_time = time.perf_counter()
        image_handler.validate_image(downloaded_image_path, config['max_file_size_mb'])
        logs['tempo_validacao_arquivo'] = time.perf_counter() - step_start_time

        # 3. Redimensionar a imagem
        step_start_time = time.perf_counter()
        resized_image_path = image_handler.resize_image(downloaded_image_path, config['resize_dimensions'])
        logs['tempo_redimensionamento'] = time.perf_counter() - step_start_time

        coords = {}
        # 4.1: Tenta obter a ORIGEM da API
        try:
            origin_coords = api_client.get_origin_location(config['location_api_endpoint'])
            coords.update(origin_coords)
        except Exception as api_error:
            # 4.2: Se a API falhar, usa o FALLBACK (arquivo .env)
            print(f"AVISO: A API de localização falhou ({api_error}). Usando método de fallback (arquivo .env)...")
            origin_coords_fallback = file_manager.read_origin_from_file(config['secrets_dir'])
            coords.update(origin_coords_fallback)
        
        # 4.3: Obtém o DESTINO do arquivo .env
        destination_coords = file_manager.read_destination_from_file(config['secrets_dir'])
        
        # 4.4: Concatena os dicionários para formar o objeto final
        coords.update(destination_coords)
        print("Coordenadas finais montadas com sucesso.")
        
        # 5. Obter a previsão
        step_start_time = time.perf_counter()
        prediction_result = api_client.get_prediction(
            config['api_endpoint'], coords, resized_image_path
        )
        logs['tempo_obtencao_previsao'] = time.perf_counter() - step_start_time

        # 6. Verifica o status da previsão
        if prediction_result.get('status') != 'success':
            previsao_insuficiente(start_timestamp, resized_image_path, prediction_result, config)

        # 7. Preparar e salvar o resultado de sucesso
        success_data = {
            'start_timestamp': start_timestamp,
            'processed_image': os.path.basename(resized_image_path),
            'status': 'success',
            **prediction_result
        }
        step_start_time = time.perf_counter()
        result_file = file_manager.write_result(config['results_dir'], 'success', success_data)
        logs['tempo_salvamento_resultado'] = time.perf_counter() - step_start_time
        print(f"Resultado salvo em: {result_file}")

    except Exception as e:
        print(f"\n--- OCORREU UMA EXCEÇÃO NO PIPELINE ---")
        print(f"Erro: {e}")
        
        rejection_data = {
            'start_timestamp': start_timestamp,
            'failed_image': os.path.basename(resized_image_path) if resized_image_path else 'N/A',
            'error_message': str(e)
        }
        step_start_time = time.perf_counter()
        result_file = file_manager.write_result(config['results_dir'], 'failure', rejection_data)
        logs['tempo_salvamento_resultado'] = time.perf_counter() - step_start_time
        print(f"Resultado de rejeição salvo em: {result_file}")
        sys.exit(1)

    finally:

        # --- LÓGICA DE IMPRESSÃO DOS LOGS DE TEMPO ---
        pipeline_end_time = time.perf_counter()
        logs['tempo_total_pipeline'] = pipeline_end_time - pipeline_start_time
        
        print("\n" + "="*50)
        print("--- MÉTRICAS DE DESEMPENHO DO PIPELINE ---")
        print(f"  - Extração do arquivo (Backblaze):    {logs.get('tempo_extracao_blackblaze', 0):.4f} segundos")
        print(f"  - Validação do arquivo local:         {logs.get('tempo_validacao_arquivo', 0):.4f} segundos")
        print(f"  - Leitura das coordenadas:            {logs.get('tempo_leitura_coordenadas', 0):.4f} segundos")
        print(f"  - Redimensionamento da imagem:        {logs.get('tempo_redimensionamento', 0):.4f} segundos")
        print(f"  - Resposta da predição do modelo:     {logs.get('tempo_obtencao_previsao', 0):.4f} segundos")
        print(f"  - Salvamento do resultado final:      {logs.get('tempo_salvamento_resultado', 0):.4f} segundos")
        print("-" * 50)
        print(f"  - TEMPO TOTAL DE EXECUÇÃO:            {logs.get('tempo_total_pipeline', 0):.4f} segundos")
        print("="*50 + "\n")
        # ------------------------------------------------

        # Bloco de limpeza continua o mesmo e é crucial
        print("Limpando arquivos temporários...")
        if downloaded_image_path and os.path.exists(downloaded_image_path):
            os.remove(downloaded_image_path)
            print(f"Removido: {downloaded_image_path}")
        if resized_image_path and os.path.exists(resized_image_path):
            os.remove(resized_image_path)
            print(f"Removido: {resized_image_path}")

if __name__ == '__main__':
    main()