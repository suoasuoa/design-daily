#!/usr/bin/env python3
"""OpenAI-compatible client for the Insta360 internal GPT gateway."""

import json
import os
import re
import subprocess
import time


DEFAULT_BASE_URL = "https://ai-gateway.insta360.cn/v1"
DEFAULT_MODEL = "gpt-5.5"
KEYCHAIN_SERVICE = "design-daily-company-gpt-api-key"
KEYCHAIN_ACCOUNT = "insta360"


class CompanyGPTError(RuntimeError):
    pass


def keychain_secret(service, account=KEYCHAIN_ACCOUNT):
    if os.uname().sysname != "Darwin":
        return ""
    result = subprocess.run(
        ["security", "find-generic-password", "-a", account, "-s", service, "-w"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def company_api_key():
    return os.environ.get("COMPANY_GPT_API_KEY", "").strip() or keychain_secret(KEYCHAIN_SERVICE)


def parse_json_object(text):
    text = str(text or "").strip()
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        text = match.group(0)
    return json.loads(text)


class CompanyGPTClient:
    def __init__(self, api_key=None, base_url=None, model=None, timeout=120):
        self.api_key = (api_key or company_api_key()).strip()
        self.base_url = (base_url or os.environ.get("COMPANY_GPT_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.model = (model or os.environ.get("COMPANY_GPT_MODEL") or DEFAULT_MODEL).strip()
        self.timeout = int(timeout)
        if not self.api_key:
            raise CompanyGPTError("COMPANY_GPT_API_KEY is missing from the environment and macOS Keychain")

    def chat_json(self, messages, max_tokens=1800, temperature=0, attempts=3):
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        last_error = None
        for attempt in range(1, attempts + 1):
            result = subprocess.run(
                [
                    "curl",
                    "--fail-with-body",
                    "--silent",
                    "--show-error",
                    "--location",
                    "--connect-timeout",
                    "15",
                    "--max-time",
                    str(self.timeout),
                    "-H",
                    f"Authorization: Bearer {self.api_key}",
                    "-H",
                    "Content-Type: application/json",
                    f"{self.base_url}/chat/completions",
                    "--data-binary",
                    "@-",
                ],
                input=json.dumps(body, ensure_ascii=False),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode == 0:
                try:
                    payload = json.loads(result.stdout)
                    content = payload["choices"][0]["message"]["content"]
                    return parse_json_object(content), payload.get("usage", {})
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                    last_error = exc
            else:
                last_error = CompanyGPTError(result.stderr.strip() or result.stdout.strip())

            if body.pop("response_format", None) and result.returncode != 0 and "400" in (result.stderr + result.stdout):
                continue
            if attempt < attempts:
                time.sleep(attempt * 2)
        raise CompanyGPTError(f"company GPT request failed after {attempts} attempts: {last_error}")
