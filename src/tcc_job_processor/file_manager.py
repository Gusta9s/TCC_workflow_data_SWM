import os
import json
from datetime import datetime

def read_coordinates(secrets_dir: str) -> dict:
    """Lê as coordenadas dos arquivos .env de origem e destino."""
    coords = {}
    try:
        with open(os.path.join(secrets_dir, 'secretOrigem.env'), 'r') as f:
            for line in f:
                if line.startswith('origem_latitude='):
                    coords['origem_latitude'] = line.strip().split('=')[1]
                if line.startswith('origem_longitude='):
                    coords['origem_longitude'] = line.strip().split('=')[1]

        with open(os.path.join(secrets_dir, 'secretDestino.env'), 'r') as f:
            for line in f:
                if line.startswith('destino_latitude='):
                    coords['destino_latitude'] = line.strip().split('=')[1]
                if line.startswith('destino_longitude='):
                    coords['destino_longitude'] = line.strip().split('=')[1]

        if len(coords) != 4:
            raise ValueError("Não foi possível encontrar todas as 4 coordenadas nos arquivos .env.")
        
        print("Coordenadas lidas com sucesso:", coords)
        
        return coords
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Arquivo de secret não encontrado: {e.filename}")
    except Exception as e:
        raise RuntimeError(f"Erro ao ler as coordenadas: {e}")
    
def write_result(base_path: str, status: str, data: dict):
    """
    Escreve o dicionário de dados em um arquivo .txt (formato JSON) no diretório
    apropriado (acpt ou rjct).
    """
    if status == 'success':
        target_dir = os.path.join(base_path, 'acpt')
    else:
        target_dir = os.path.join(base_path, 'rjct')
    
    os.makedirs(target_dir, exist_ok=True)
    
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f'resultado_{timestamp_str}.txt'
    file_path = os.path.join(target_dir, file_name)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"Resultado salvo em: {file_path}")
    return file_path