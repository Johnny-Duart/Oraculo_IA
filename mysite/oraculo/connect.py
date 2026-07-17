import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("EVOLUTION_BASE_URL")
API_KEY = os.getenv("AUTHENTICATION_API_KEY")
INSTANCE = os.getenv("EVOLUTION_INSTANCE_NAME", "oraculo")


def obter_qrcode():
    if not BASE_URL or not API_KEY:
        raise SystemExit(
            "EVOLUTION_BASE_URL ou AUTHENTICATION_API_KEY não definidos no .env"
        )

    headers = {"apikey": API_KEY}
    response = requests.get(
        f"{BASE_URL}/instance/connect/{INSTANCE}", headers=headers
    )

    print("STATUS:", response.status_code)

    if response.status_code != 200:
        print("ERRO:", response.text)
        return

    data = response.json()

    # Algumas versões retornam o código de pareamento por número de telefone
    pairing_code = data.get("pairingCode")
    if pairing_code:
        print(
            f"Código de pareamento: {pairing_code}\n"
            "(No WhatsApp do celular: Aparelhos conectados > Conectar com número de telefone)"
        )

    # O QR pode vir em "base64" direto ou aninhado em "qrcode": {"base64": ...}
    qrcode_base64 = data.get("base64")
    if not qrcode_base64 and isinstance(data.get("qrcode"), dict):
        qrcode_base64 = data["qrcode"].get("base64")

    if not qrcode_base64:
        print("Nenhum QR code retornado pela API. Resposta completa:")
        print(data)
        print(
            "\nSe a instância já estiver conectada, isso é esperado "
            "(não há QR para gerar de novo)."
        )
        return

    if qrcode_base64.startswith("data:image"):
        qrcode_base64 = qrcode_base64.split(",", 1)[1]

    caminho = "qrcode.png"
    with open(caminho, "wb") as f:
        f.write(base64.b64decode(qrcode_base64))

    print(f"QR Code salvo em '{caminho}'. Abra o arquivo e escaneie com o WhatsApp.")


if __name__ == "__main__":
    obter_qrcode()
