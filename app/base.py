import os
from abc import ABC

from dotenv import load_dotenv

load_dotenv()


class Service(ABC):
    SSL = os.getenv("SSL", default=False)
    DOMAIN = os.getenv("DOMAIN", default="localhost:8000")
    BASE_URL = f"https://{DOMAIN}" if SSL else f"http://{DOMAIN}"
    WS_BASE_URL = f"wss://{DOMAIN}" if SSL else f"ws://{DOMAIN}"
