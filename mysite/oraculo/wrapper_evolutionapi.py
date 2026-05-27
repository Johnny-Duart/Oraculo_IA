import requests
from urllib.parse import urlencode, urljoin
import os
from dotenv import load_dotenv

load_dotenv()


class BaseEvolutionAPI:
    def __init__(self):

        self._BASE_URL = os.getenv("EVOLUTION_BASE_URL")
        self._API_KEY = os.getenv("AUTHENTICATION_API_KEY")

    def _send_request(
        self, path, method="GET", body=None, headers=None, params_url=None
    ):
        method = method.upper()
        url = self._mount_url(path, params_url)

        if headers is None:
            headers = {}

        headers.setdefault("Content-Type", "application/json")
        headers["apikey"] = self._API_KEY

        request = {
            "GET": requests.get,
            "POST": requests.post,
            "PUT": requests.put,
            "DELETE": requests.delete,
        }.get(method)

        if request is None:
            raise ValueError(f"Método HTTP inválido: {method}")

        response = request(
            url,
            headers=headers,
            json=body,
            timeout=30,
        )

        return response

    def _mount_url(self, path, params_url=None):
        parameters = ""

        if isinstance(params_url, dict):
            parameters = urlencode(params_url)
        base_url = self._BASE_URL.rstrip("/") + "/"

        url = urljoin(base_url, path.lstrip("/"))

        if parameters:
            url += f"?{parameters}"
        return url


class SendMessage(BaseEvolutionAPI):
    def send_message(self, instance, number, text):
        path = f"/message/sendText/{instance}/"
        body = {
            "number": number,
            "textMessage": {"text": text},
        }
        return self._send_request(
            path=path,
            method="POST",
            body=body,
        )


if __name__ == "__main__":
    client = SendMessage()

    response = client.send_message(
        instance="oraculo",
        number=os.getenv("TEST_PHONE"),
        text="Olá, estou enviando uma mensagem 🚀",
    )

    print(response.status_code)
    print(response.text)
