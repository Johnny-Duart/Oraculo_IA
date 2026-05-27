import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("EVOLUTION_BASE_URL")
API_KEY = os.getenv("AUTHENTICATION_API_KEY")

headers = {"apikey": API_KEY, "Content-Type": "application/json"}

body = {"instanceName": "oraculo"}

response = requests.post(
    f"{BASE_URL}/instance/create", headers=headers, json=body
)

print(response.status_code)
print(response.text)
