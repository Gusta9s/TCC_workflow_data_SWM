import os
import json
from datetime import datetime


def read_origin_from_file(secrets_dir: str) -> dict:
    """Lê as coordenadas de ORIGEM do arquivo secretOrigem.env (método de fallback)."""
    try:
        coords = {}
        with open(os.path.join(secrets_dir, 'secretOrigem.env'), 'r') as f:
            for line in f:
                if line.strip().startswith('origem_latitude='):
                    coords['origem_latitude'] = line.strip().split('=')[1]
                if line.strip().startswith('origem_longitude='):
                    coords['origem_longitude'] = line.strip().split('=')[1]
        if 'origem_latitude' not in coords or 'origem_longitude' not in coords:
            raise ValueError("Não foi possível encontrar as coordenadas de origem no arquivo .env.")
        return coords
    except FileNotFoundError:
        raise FileNotFoundError(f"Arquivo de secret de origem não encontrado em '{secrets_dir}'.")
    except Exception as e:
        raise RuntimeError(f"Erro ao ler as coordenadas de origem do arquivo: {e}")


def read_destination_from_file(secrets_dir: str) -> dict:
    """Lê as coordenadas de DESTINO do arquivo secretDestino.env."""
    try:
        coords = {}
        with open(os.path.join(secrets_dir, 'secretDestino.env'), 'r') as f:
            for line in f:
                if line.strip().startswith('destino_latitude='):
                    coords['destino_latitude'] = line.strip().split('=')[1]
                if line.strip().startswith('destino_longitude='):
                    coords['destino_longitude'] = line.strip().split('=')[1]
        if 'destino_latitude' not in coords or 'destino_longitude' not in coords:
            raise ValueError("Não foi possível encontrar as coordenadas de destino no arquivo .env.")
        return coords
    except FileNotFoundError:
        raise FileNotFoundError(f"Arquivo de secret de destino não encontrado em '{secrets_dir}'.")
    except Exception as e:
        raise RuntimeError(f"Erro ao ler as coordenadas de destino do arquivo: {e}")


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