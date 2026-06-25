"""HTTP client for the official Clash Royale API."""
import logging
import time
from urllib.parse import quote

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ClashRoyaleAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ClashRoyaleClient:
    def __init__(self):
        self.base_url = (getattr(settings, 'CLASH_ROYALE_API_BASE', '') or '').rstrip('/')
        self.token = getattr(settings, 'CLASH_ROYALE_API_TOKEN', '') or ''
        self.delay = float(getattr(settings, 'CLASH_CENTER_API_DELAY_SECONDS', 0.4))
        self._last_request_at = 0.0

    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def _request(self, path: str, params: dict | None = None) -> dict | list:
        if not self.configured():
            raise ClashRoyaleAPIError('CLASH_ROYALE_API_TOKEN is required')

        self._throttle()
        url = f'{self.base_url}/{path.lstrip("/")}'
        headers = {'Authorization': f'Bearer {self.token}', 'Accept': 'application/json'}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            self._last_request_at = time.monotonic()
        except requests.RequestException as exc:
            raise ClashRoyaleAPIError(str(exc)) from exc

        if response.status_code == 404:
            raise ClashRoyaleAPIError('Not found', status_code=404)
        if response.status_code == 429:
            raise ClashRoyaleAPIError('Rate limited', status_code=429)
        if response.status_code >= 400:
            raise ClashRoyaleAPIError(
                f'API error {response.status_code}: {response.text[:200]}',
                status_code=response.status_code,
            )
        return response.json()

    @staticmethod
    def normalize_tag(tag: str) -> str:
        tag = tag.strip().upper()
        if not tag.startswith('#'):
            tag = f'#{tag}'
        return tag

    @staticmethod
    def encode_tag(tag: str) -> str:
        return quote(ClashRoyaleClient.normalize_tag(tag), safe='')

    def get_cards(self) -> list[dict]:
        data = self._request('cards')
        return data.get('items', data) if isinstance(data, dict) else data

    def get_player(self, tag: str) -> dict:
        return self._request(f'players/{self.encode_tag(tag)}')

    def get_battlelog(self, tag: str) -> list[dict]:
        data = self._request(f'players/{self.encode_tag(tag)}/battlelog')
        return data if isinstance(data, list) else []
