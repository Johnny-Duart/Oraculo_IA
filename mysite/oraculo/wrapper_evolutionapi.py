import requests


class BaseEvolutionAPI:
    def __init__(self):
        self._BASE_URL = ""
        self._API_KEY = {"oraculo": ""}

    def _send_request(
        self, path, method="GET", body=None, headers={}, params_url={}
    ):
        method.upper()
