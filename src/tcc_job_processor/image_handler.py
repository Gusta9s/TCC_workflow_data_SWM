import os
from PIL import Image, ImageFile
import re
import boto3
from botocore.exceptions import ClientError
import tempfile

ImageFile.LOAD_TRUNCATED_IMAGES = True

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
    Encontra a imagem mais recente no bucket do B2, faz o download para um
    diretório temporário do sistema e retorna o caminho local.
    """
    s3 = _get_b2_resource(b2_config)
    bucket_name = b2_config['bucket_name']
    
    try:
        print(f"Listando arquivos no bucket do B2: {bucket_name}...")
        bucket = s3.Bucket(bucket_name)
        
        matching_files = []
        image_pattern = re.compile(r'^foto_\d+\.jpg$', re.IGNORECASE)

        for obj in bucket.objects.all():
            if image_pattern.match(obj.key):
                matching_files.append(obj)
        
        if not matching_files:
            raise FileNotFoundError(f"Nenhuma imagem com o padrão 'foto_{{x}}.jpg' encontrada no bucket '{bucket_name}'.")

        latest_file_obj = sorted(matching_files, key=lambda obj: obj.last_modified, reverse=True)[0]
        file_name = latest_file_obj.key
        print(f"Arquivo mais recente encontrado: '{file_name}'")

        temp_dir = tempfile.gettempdir()
        download_path = os.path.join(temp_dir, file_name)
        
        print(f"Fazendo download de '{file_name}' para '{download_path}'...")
        bucket.download_file(file_name, download_path)
        
        print("Download concluído.")
        return download_path

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            raise FileNotFoundError(f"O bucket '{bucket_name}' não foi encontrado. Verifique a configuração.")
        else:
            raise ConnectionError(f"Ocorreu um erro na API do B2: {e}")
    except Exception as e:
        raise RuntimeError(f"Ocorreu um erro inesperado ao processar arquivos do B2: {e}")


def validate_image(image_path: str, max_size_mb: int) -> bool:
    if not os.path.exists(image_path) or not os.access(image_path, os.R_OK):
        raise IOError(f"Imagem não existe ou não pode ser lida: {image_path}")

    file_size = os.path.getsize(image_path) / (1024 * 1024)
    if file_size > max_size_mb:
        raise ValueError(f"Imagem excede o tamanho máximo de {max_size_mb} MB.")

    try:
        with Image.open(image_path) as img:
            img.verify()
        with Image.open(image_path) as img:
            if img.format.lower() not in ['jpeg', 'jpg']:
                 raise TypeError(f"Formato de imagem não suportado: {img.format}")
    except Exception as e:
        raise IOError(f"Arquivo corrompido ou não é uma imagem válida: {image_path}. Erro: {e}")
        
    print(f"Imagem '{os.path.basename(image_path)}' validada com sucesso.")
    return True


def resize_image(image_path: str, dimensions: list) -> str:
    """Redimensiona a imagem e a salva em um local temporário do sistema."""
    try:
        with Image.open(image_path) as img:
            img_resized = img.convert('RGB').resize(tuple(dimensions))
            
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"resized_{os.path.basename(image_path)}")
            img_resized.save(temp_path, 'JPEG')
            return temp_path
    except Exception as e:
        raise RuntimeError(f"Erro ao redimensionar a imagem: {e}")