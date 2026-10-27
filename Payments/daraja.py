# payments/daraja.py
import base64, re, time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from django.conf import settings

BASE = ("https://sandbox.safaricom.co.ke" if settings.MPESA_ENV == "sandbox"
        else "https://api.safaricom.co.ke")

_token = {"value": None, "expires_at": 0}


class DarajaError(Exception):
    pass


def normalize_phone(raw: str) -> str:
    # Accepts 07XX, 01XX, +2547XX, 2547XX -> returns 2547XXXXXXXX
    p = re.sub(r"[\s+\-]", "", raw)
    if p.startswith("0"):
        p = "254" + p[1:]
    if not re.fullmatch(r"254[17]\d{8}", p):
        raise DarajaError("Invalid Safaricom phone number")
    return p


def get_access_token() -> str:
    # Tokens last ~1 hour; cache to avoid hitting the auth endpoint per payment
    if _token["value"] and time.time() < _token["expires_at"]:
        return _token["value"]
    r = requests.get(
        f"{BASE}/oauth/v1/generate?grant_type=client_credentials",
        auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    _token["value"] = data["access_token"]
    _token["expires_at"] = time.time() + int(data.get("expires_in", 3599)) - 60
    return _token["value"]


def _timestamp_and_password():
    ts = datetime.now(ZoneInfo("Africa/Nairobi")).strftime("%Y%m%d%H%M%S")
    raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{ts}"
    return ts, base64.b64encode(raw.encode()).decode()


def _post(path: str, payload: dict) -> dict:
    r = requests.post(
        f"{BASE}{path}",
        json=payload,
        headers={"Authorization": f"Bearer {get_access_token()}"},
        timeout=30,
    )
    data = r.json() if r.content else {}
    if r.status_code != 200:
        raise DarajaError(data.get("errorMessage") or f"HTTP {r.status_code}: {data}")
    return data


def stk_push(phone: str, amount: int, account_ref: str, description: str) -> dict:
    ts, password = _timestamp_and_password()
    phone = normalize_phone(phone)
    return _post("/mpesa/stkpush/v1/processrequest", {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": ts,
        "TransactionType": "CustomerPayBillOnline",  # "CustomerBuyGoodsOnline" for a Till
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": account_ref[:12],   # max 12 chars
        "TransactionDesc": description[:13],    # max 13 chars
    })


def stk_query(checkout_request_id: str) -> dict:
    ts, password = _timestamp_and_password()
    return _post("/mpesa/stkpushquery/v1/query", {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": ts,
        "CheckoutRequestID": checkout_request_id,
    })