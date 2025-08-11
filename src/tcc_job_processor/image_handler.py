import os
import glob
from PIL import Image, ImageFile

# Permite o carregamento de imagens truncadas
ImageFile.LOAD_TRUNCATED_IMAGES = True

def find_latest_image(source_dir: str, pattern: str) -> str:
    """Encontra o arquivo mais recente que corresponde ao padrão no diretório."""
    try:
        list_of_files = glob.glob(os.path.join(source_dir, pattern))
        if not list_of_files:
            raise FileNotFoundError(f"Nenhuma imagem encontrada com o padrão '{pattern}' em '{source_dir}'")
        latest_file = max(list_of_files, key=os.path.getctime)
        return latest_file
    except Exception as e:
        raise RuntimeError(f"Erro ao procurar a imagem mais recente: {e}")
    
def validate_image(image_path: str, max_size_mb: int) -> bool:
    """Valida a integridade e segurança da imagem."""
    # 1. Validação de Existência e Leitura
    if not os.path.exists(image_path) or not os.access(image_path, os.R_OK):
        raise IOError(f"Imagem não existe ou não pode ser lida: {image_path}")

    # 2. Validação de Tamanho (Segurança contra DoS)
    file_size = os.path.getsize(image_path) / (1024 * 1024)
    if file_size > max_size_mb:
        raise ValueError(f"Imagem excede o tamanho máximo de {max_size_mb} MB.")

    # 3. Validação de Consistência (Verifica se é uma imagem válida)
    try:
        with Image.open(image_path) as img:
            img.verify() # Verifica a integridade dos dados da imagem
        # Reabrir após verify()
        with Image.open(image_path) as img:
            if img.format.lower() not in ['jpeg', 'jpg']:
                 raise TypeError(f"Formato de imagem não suportado: {img.format}")
    except Exception as e:
        raise IOError(f"Arquivo corrompido ou não é uma imagem válida: {image_path}. Erro: {e}")
        
    print(f"Imagem '{os.path.basename(image_path)}' validada com sucesso.")
    return True

def resize_image(image_path: str, dimensions: list) -> str:
    """Redimensiona a imagem e a salva em um local temporário."""
    try:
        with Image.open(image_path) as img:
            # Converte para RGB para garantir 3 canais de cor
            img_resized = img.convert('RGB').resize(tuple(dimensions))
            
            # Salva a imagem redimensionada temporariamente para o envio
            temp_path = f"/tmp/resized_{os.path.basename(image_path)}"
            img_resized.save(temp_path, 'JPEG')
            return temp_path
    except Exception as e:
        raise RuntimeError(f"Erro ao redimensionar a imagem: {e}")
