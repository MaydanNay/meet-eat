# telegram_verify.py

import hmac, hashlib
from typing import Dict

def build_data_check_string(init_data: dict) -> str:
    items = [f"{k}={v}" for k, v in sorted(init_data.items()) if k != "hash"]
    return "\n".join(items)

def verify_init_data(init_data: dict, bot_token: str) -> bool:
    if not init_data or "hash" not in init_data:
        return False
    data_check_string = build_data_check_string(init_data)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    hmac_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(hmac_value, init_data["hash"])
