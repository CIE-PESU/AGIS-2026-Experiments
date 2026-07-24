from cryptography.fernet import Fernet
from core.config import settings

cipher = Fernet(settings.FERNET_KEY.encode())
