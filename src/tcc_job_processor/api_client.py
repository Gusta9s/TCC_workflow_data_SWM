import requests
import os

def get_origin_location(api_url: str) -> dict:
    """Busca as coordenadas de origem de uma API de localização."""
    try:
        print("Buscando coordenadas de origem via API de localização...")
        # Timeout de 10 segundos para a requisição
        response = requests.get(api_url, timeout=10)
        response.raise_for_status() # Lança exceção para erros HTTP (4xx ou 5xx)
        
        data = response.json()
        
        # Transforma o payload para o formato esperado pelo resto do pipeline
        origin_coords = {
            'origem_latitude': data['latitude'],
            'origem_longitude': data['longitude']
        }
        print("Coordenadas de origem obtidas com sucesso da API.")
        return origin_coords
        
    except requests.exceptions.RequestException as e:
        # Re-lança a exceção para que o app.py possa tratá-la no bloco try/except
        raise ConnectionError(f"Erro ao conectar com a API de localização: {e}")

def train_model(api_url: str) -> dict:
    """Envia o comando de treinamento para a API."""
    try:
        print("Enviando requisição de treinamento para o modelo...")
        response = requests.post(api_url, json={"command": "train"}, timeout=1200) # Timeout de 1200 secs
        response.raise_for_status() # Lança exceção para códigos de erro HTTP (4xx ou 5xx)
        print("Modelo treinado com sucesso.")
        return response.json()
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Erro na requisição de treinamento para a API: {e}")
    
def get_prediction(api_url: str, coords: dict, resized_image_path: str) -> dict:
    """Envia a imagem e os dados para obter uma previsão."""
    try:
        print("Enviando requisição de previsão com a imagem...")
        form_data = {
            'command': (None, 'predict'),
            'origem_latitude': (None, coords['origem_latitude']),
            'origem_longitude': (None, coords['origem_longitude']),
            'destino_latitude': (None, coords['destino_latitude']),
            'destino_longitude': (None, coords['destino_longitude']),
        }
        
        with open(resized_image_path, 'rb') as f:
            files = {'image': (os.path.basename(resized_image_path), f, 'image/jpeg')}
            response = requests.post(api_url, data=form_data, files=files, timeout=1000) # Timeout de 1000 secs

        response.raise_for_status()
        print("Previsão recebida com sucesso.")
        return response.json()
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Erro na requisição de previsão para a API: {e}")
