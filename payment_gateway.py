#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""AriePulsa QRIS Realtime payment gateway client."""

from __future__ import annotations

from typing import Any

import requests


class AriePulsaClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://ariepulsa.my.id/api/qrisrealtime",
        timeout: int = 30,
    ):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").strip() or "https://ariepulsa.my.id/api/qrisrealtime"
        self.timeout = max(5, int(timeout))

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            return {
                "status": False,
                "data": {"pesan": "API key kosong"},
            }

        body = {
            "api_key": self.api_key,
            **payload,
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
        }

        try:
            response = requests.post(
                self.base_url,
                data=body,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            return {
                "status": False,
                "data": {"pesan": f"request_error: {exc}"},
            }

        try:
            parsed = response.json()
        except ValueError:
            preview = (response.text or "")[:500]
            return {
                "status": False,
                "data": {"pesan": f"invalid_json: HTTP {response.status_code} | {preview}"},
            }

        if not isinstance(parsed, dict):
            return {
                "status": False,
                "data": {"pesan": "invalid_response_format"},
            }

        return parsed

    def get_deposit(
        self,
        jumlah: int,
        reff_id: str,
        kode_channel: str = "QRISREALTIME",
    ) -> dict[str, Any]:
        return self._post(
            {
                "action": "get-deposit",
                "jumlah": str(max(0, int(jumlah))),
                "reff_id": str(reff_id or ""),
                "kode_channel": str(kode_channel or "QRISREALTIME"),
            }
        )

    def status_deposit(self, kode_deposit: str) -> dict[str, Any]:
        return self._post(
            {
                "action": "status-deposit",
                "kode_deposit": str(kode_deposit or ""),
            }
        )

    def cancel_deposit(self, kode_deposit: str) -> dict[str, Any]:
        return self._post(
            {
                "action": "cancel-deposit",
                "kode_deposit": str(kode_deposit or ""),
            }
        )

    def download_qr_image(self, image_url: str) -> bytes:
        if not image_url:
            raise ValueError("QR image URL kosong")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }

        response = requests.get(image_url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        content_type = (response.headers.get("Content-Type") or "").lower()
        if "image" not in content_type:
            raise ValueError(f"Response bukan image: {content_type}")

        data = response.content or b""
        if not data:
            raise ValueError("QR image kosong")
        return data
