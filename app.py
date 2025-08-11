# app.py
import yaml
import os
import sys
from datetime import datetime
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
    start_timestamp = datetime.now().isoformat()
    config = load_config()
    image_path = None
    
    try:
        # 1. Encontrar a imagem mais recente
        image_path = image_handler.find_latest_image(
            config['image_source_dir'], config['image_pattern']
        )
        
        # 2. Validar a imagem
        image_handler.validate_image(image_path, config['max_file_size_mb'])
        
        # 3. Ler as coordenadas das secrets
        coords = file_manager.read_coordinates(config['secrets_dir'])
        
        # 4. Redimensionar a imagem
        resized_image_path = image_handler.resize_image(image_path, config['resize_dimensions'])
        
        # 5. Treinar o modelo (primeira requisição)
        api_client.train_model(config['api_endpoint'])
        
        # 6. Obter a previsão (segunda requisição)
        prediction_result = api_client.get_prediction(
            config['api_endpoint'], coords, resized_image_path
        )
        
        # Limpa o arquivo temporário
        os.remove(resized_image_path)

        # 7. Verifica o status da previsão
        if prediction_result.get('status') != 'success':
            previsao_insuficiente(start_timestamp, image_path, prediction_result, config)

        # 8. Preparar e salvar o resultado de sucesso
        success_data = {
            'start_timestamp': start_timestamp,
            'processed_image': os.path.basename(image_path),
            'status': 'success',
            **prediction_result
        }
        result_file = file_manager.write_result(config['results_dir'], 'success', success_data)
        print(f"Resultado salvo em: {result_file}")

    except Exception as e:
        print(f"\n--- OCORREU UMA EXCEÇÃO NO PIPELINE ---")
        print(f"Erro: {e}")
        
        rejection_data = {
            'start_timestamp': start_timestamp,
            'failed_image': os.path.basename(image_path) if image_path else 'N/A',
            'error_message': str(e)
        }
        result_file = file_manager.write_result(config['results_dir'], 'failure', rejection_data)
        print(f"Resultado de rejeição salvo em: {result_file}")
        sys.exit(1)

if __name__ == '__main__':
    main()