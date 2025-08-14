import os
import glob
from PIL import Image, ImageFile
import boto3
from botocore.exceptions import ClientError
import re

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
    
def _get_b2_resource(b2_config: dict):
    """Cria e retorna um recurso S3 configurado para o Backblaze B2."""
    try:
        return boto3.resource('s3',
            endpoint_url=f"https://{b2_config['endpoint_url']}",
            aws_access_key_id=b2_config['key_id'],
            aws_secret_access_key=b2_config['application_key']
        )
    except Exception as e:
        raise ConnectionError(f"Falha ao criar o recurso B2/S3: {e}")
    
def find_and_download_latest_image_from_b2(b2_config: dict) -> str:
    """
    Encontra a imagem mais recente no bucket do Backblaze B2 que corresponde ao padrão,
    faz o download e retorna o caminho local temporário.
    """
    s3 = _get_b2_resource(b2_config)
    bucket_name = b2_config['bucket_name']
    
    try:
        print(f"Listando arquivos no bucket do B2: {bucket_name}...")
        bucket = s3.Bucket(bucket_name)
        
        # 1. Listar todos os objetos e filtrar em memória
        matching_files = []
        image_pattern = re.compile(r'^imagem\d+\.jpe?g$', re.IGNORECASE)

        for obj in bucket.objects.all():
            if image_pattern.match(obj.key):
                matching_files.append(obj)
        
        if not matching_files:
            raise FileNotFoundError(f"Nenhuma imagem com o padrão 'imagem{{x}}.jpg/jpeg' encontrada no bucket '{bucket_name}'.")

        # 2. Encontrar o mais recente
        # Ordena a lista de arquivos pela data da última modificação, em ordem decrescente
        latest_file_obj = sorted(matching_files, key=lambda obj: obj.last_modified, reverse=True)[0]
        
        file_name = latest_file_obj.key
        print(f"Arquivo mais recente encontrado: '{file_name}'")

        # 3. Fazer o download do arquivo
        download_path = os.path.join(b2_config['download_temp_dir'], file_name)
        
        print(f"Fazendo download de '{file_name}' para '{download_path}'...")
        bucket.download_file(file_name, download_path)
        
        print("Download concluído.")
        return download_path

    except ClientError as e:
        # Trata erros específicos da API, como bucket não encontrado
        if e.response['Error']['Code'] == 'NoSuchBucket':
            raise FileNotFoundError(f"O bucket '{bucket_name}' não foi encontrado. Verifique a configuração.")
        else:
            raise ConnectionError(f"Ocorreu um erro na API do B2: {e}")
    except Exception as e:
        raise RuntimeError(f"Ocorreu um erro inesperado ao processar arquivos do B2: {e}")
