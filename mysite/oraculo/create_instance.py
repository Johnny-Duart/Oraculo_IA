import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("EVOLUTION_BASE_URL")
API_KEY = os.getenv("AUTHENTICATION_API_KEY")
INSTANCE = os.getenv("EVOLUTION_INSTANCE_NAME", "oraculo")

# Opcional: se definido, já cadastra o webhook do Django na criação da instância.
# Exemplo: http://host.docker.internal:8001/oraculo/webhook_whatsapp/
DJANGO_WEBHOOK_URL = os.getenv("DJANGO_WEBHOOK_URL")


def criar_instancia():
    if not BASE_URL or not API_KEY:
        raise SystemExit(
            "EVOLUTION_BASE_URL ou AUTHENTICATION_API_KEY não definidos no .env"
        )

    headers = {"apikey": API_KEY, "Content-Type": "application/json"}

    body = {
        "instanceName": INSTANCE,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS",
    }

    if DJANGO_WEBHOOK_URL:
        body["webhook"] = {
            "url": DJANGO_WEBHOOK_URL,
            "events": ["MESSAGES_UPSERT"],
        }

    response = requests.post(
        f"{BASE_URL}/instance/create", headers=headers, json=body
    )

    print("STATUS:", response.status_code)
    print(response.text)

    if response.status_code not in (200, 201):
        print(
            "\nFalha ao criar a instância. Causas comuns:\n"
            "- A instância 'oraculo' já existe (rode connect.py direto para pegar o QR)\n"
            "- A API ainda não subiu / porta errada em EVOLUTION_BASE_URL\n"
            "- AUTHENTICATION_API_KEY não bate com a chave configurada no container"
        )


if __name__ == "__main__":
    criar_instancia()
