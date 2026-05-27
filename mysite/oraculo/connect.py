import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("EVOLUTION_BASE_URL")
API_KEY = os.getenv("AUTHENTICATION_API_KEY")

headers = {"apikey": API_KEY}

response = requests.get(
    f"{BASE_URL}/instance/connect/oraculo", headers=headers
)

print(response.json())
