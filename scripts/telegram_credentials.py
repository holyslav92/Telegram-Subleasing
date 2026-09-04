"""Загрузка учётных данных Telegram из env, site.env.local и tenant-config."""

import json
import os
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SITE_ENV_PATH = WORKSPACE_ROOT / "memory" / "site.env.local"
TENANT_CONFIG_PATH = WORKSPACE_ROOT / "shared" / "tenant-config.json"

TOKEN_ALIASES = (
    "TELEGRAM_BOT_TOKEN",
    "TG_BOT_TOKEN",
    "TELEGRAM_TOKEN",
    "BOT_TOKEN",
)

CHAT_ALIASES = (
    "TELEGRAM_CHAT_ID",
    "TG_CHAT_ID",
    "TELEGRAM_CHANNEL_ID",
    "CHANNEL_ID",
)


def _read_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _first_value(keys: tuple[str, ...], *sources: dict[str, str]) -> str:
    for source in sources:
        for key in keys:
            value = (source.get(key) or "").strip()
            if value:
                return value
    return ""


def load_telegram_credentials() -> dict[str, str]:
    """Возвращает bot_token и chat_id из всех доступных источников."""
    file_env = _read_env_file(SITE_ENV_PATH)
    os_env = {k: os.environ.get(k, "") for k in TOKEN_ALIASES + CHAT_ALIASES}

    tenant_token_key = "TELEGRAM_BOT_TOKEN"
    tenant_chat_key = "TELEGRAM_CHAT_ID"
    if TENANT_CONFIG_PATH.exists():
        try:
            tenant = json.loads(TENANT_CONFIG_PATH.read_text(encoding="utf-8"))
            tg = tenant.get("telegram_bot", {})
            tenant_token_key = tg.get("bot_token_env", tenant_token_key)
            tenant_chat_key = tg.get("target_chat_env", tenant_chat_key)
        except Exception:
            pass

    tenant_env = {
        tenant_token_key: os.environ.get(tenant_token_key, ""),
        tenant_chat_key: os.environ.get(tenant_chat_key, ""),
    }

    bot_token = _first_value(TOKEN_ALIASES, os_env, tenant_env, file_env)
    chat_id = _first_value(CHAT_ALIASES, os_env, tenant_env, file_env)

    return {
        "bot_token": bot_token,
        "chat_id": chat_id,
        "token_source": _detect_source(bot_token, TOKEN_ALIASES, (tenant_token_key,), file_env),
        "chat_source": _detect_source(chat_id, CHAT_ALIASES, (tenant_chat_key,), file_env),
    }


def _detect_source(value: str, aliases: tuple[str, ...], tenant_keys: tuple[str, ...], file_env: dict[str, str]) -> str:
    if not value:
        return "missing"
    for key in aliases:
        if os.environ.get(key, "").strip() == value:
            return f"env:{key}"
    for key in tenant_keys:
        if os.environ.get(key, "").strip() == value:
            return f"env:{key}"
    for key in aliases + tenant_keys:
        if file_env.get(key, "").strip() == value:
            return f"file:{SITE_ENV_PATH.name}:{key}"
    return "unknown"


def diagnose_telegram_credentials() -> dict:
    creds = load_telegram_credentials()
    injected = os.environ.get("CLOUD_AGENT_INJECTED_SECRET_NAMES", "")
    return {
        "bot_token_present": bool(creds["bot_token"]),
        "chat_id_present": bool(creds["chat_id"]),
        "token_source": creds["token_source"],
        "chat_source": creds["chat_source"],
        "site_env_exists": SITE_ENV_PATH.exists(),
        "injected_secret_names": [s for s in injected.split(",") if s],
        "telegram_in_injected_secrets": any(
            name in injected for name in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
        ),
    }
