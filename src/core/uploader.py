import requests
from typing import Optional

class ImageUploader:
    API_URL = "https://tu-servidor-api.com/upload"

    def upload_image(self, file_path: str) -> Optional[str]:
        """
        Sube la imagen y retorna la URL pública.
        Retorna None si falla.
        """
        try:
            with open(file_path, 'rb') as f:
                response = requests.post(self.API_URL, files={'image': f}, timeout=10)
            
            if response.status_code == 200:
                return response.json().get('url')
            else:
                print(f"Error servidor: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error de conexión: {e}")
            return None