#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
New NFT Gift Telegram Bot v12.1
- Поддержка: @mkrartem (https://t.me/mkrartem)
- Платная установка и смена фона профиля (1,500,000 ⭐ за установку, 500,000 ⭐ за смену).
- Кнопка «Улучшение» в профиле (в разработке).
- Список существующих NFT в разделе моделей маркета.
- Команды в чате «Передать» (звёзды от 1,000 ⭐ и подарки, доступно с 5-го уровня).
- Исправленная казна кланов (общая казна не уменьшается при депозите в баланс казны) и пожертвованные подарки клана.
- Режим техработ (отключение бота) в Админ-панели.
"""

import asyncio
import atexit
import base64
import datetime
import gzip
import hashlib
import hmac
import html
import inspect
import io
import json
import logging
import math
import os
import random
import re
import secrets
import shutil
import signal
import sqlite3
import subprocess
import tempfile
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple, Dict

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageChops, ImageEnhance
import requests

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    CallbackQuery,
    InputFile,
    InlineQueryResultArticle,
    InlineQueryResultCachedPhoto,
    InputTextMessageContent,
    InputMediaPhoto,
    LabeledPrice,
    WebAppInfo,
)
try:
    from telegram import LinkPreviewOptions
except ImportError:
    LinkPreviewOptions = None
from telegram.constants import ParseMode
from telegram.error import Forbidden, BadRequest, RetryAfter, TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    InlineQueryHandler,
    ChosenInlineResultHandler,
    PreCheckoutQueryHandler,
    filters,
)
from telegram.request import HTTPXRequest

# Попытка импорта Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import (
        credentials as fb_credentials,
        firestore as fb_firestore,
        storage as fb_storage,
    )
    FIREBASE_ADMIN_AVAILABLE = True
except ImportError:
    firebase_admin = None
    fb_credentials = None
    fb_firestore = None
    fb_storage = None
    FIREBASE_ADMIN_AVAILABLE = False

try:
    from aiohttp import web as aiohttp_web, WSMsgType
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp_web = None
    WSMsgType = None
    AIOHTTP_AVAILABLE = False

# ---------------------------------------------------------------------------
# Настройки и глобальные пути
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "images"
PLUSHPEPE_MODELS_DIR = IMAGES_DIR / "plushpepe_models"
HEART_LOCKET_MODELS_DIR = IMAGES_DIR / "heart_locket_models"
DUROV_CAP_MODELS_DIR = IMAGES_DIR / "durov_cap_models"
CUP_MODELS_DIR = IMAGES_DIR / "cup_models"
BONDED_RING_MODELS_DIR = IMAGES_DIR / "bonded_ring_models"
BACKGROUNDS_DIR = IMAGES_DIR / "backgrounds"
CLAN_AVATARS_DIR = IMAGES_DIR / "clan_avatars"
UI_ASSETS_DIR = IMAGES_DIR / "ui"
AVATARS_CACHE_DIR = IMAGES_DIR / "avatars"
FONTS_DIR = BASE_DIR / "fonts"
DB_PATH = BASE_DIR / "base.db"

FONTS_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
PLUSHPEPE_MODELS_DIR.mkdir(parents=True, exist_ok=True)
HEART_LOCKET_MODELS_DIR.mkdir(parents=True, exist_ok=True)
DUROV_CAP_MODELS_DIR.mkdir(parents=True, exist_ok=True)
CUP_MODELS_DIR.mkdir(parents=True, exist_ok=True)
BONDED_RING_MODELS_DIR.mkdir(parents=True, exist_ok=True)
BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
CLAN_AVATARS_DIR.mkdir(parents=True, exist_ok=True)
UI_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
AVATARS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "9036416244:AAGrJgI3jzMMU5bn6Q36r8cNBIJqGxniXmo")
SUPPORT_URL = os.environ.get("SUPPORT_URL", "https://t.me/mkrartem")
SUPPORT_HANDLE = "@mkrartem"
OFFICIAL_CHANNEL_HANDLE = "@NwNFTChannel"
OFFICIAL_CHANNEL_URL = "https://t.me/NwNFTChannel"
_BOT_USERNAME_CACHE: Optional[str] = None

COOLDOWN_SECONDS = 1 * 60 * 60          # 1 час между выбиванием NFT в группах
COOLDOWN_ENABLED = True
CHAT_DROP_CHANCE = 0.90                 # 90% шанс дропа при слове NFT
STAR_RUB_RATE = 1.5                     # 1 Star = 1.5 RUB
TON_RUB_RATE = 100.0                    # 1 TON = 100 RUB
ADMIN_IDS = {684535319, 7459502130}     # Telegram ID администраторов

BG_SET_COST = 1_500_000                 # Стоимость первой установки фона профиля
BG_CHANGE_COST = 500_000                # Стоимость смены уже установленного фона
TRANSFER_MIN_LEVEL = 5                  # Минимальный уровень для передачи звёзд и подарков
TRANSFER_MIN_STARS = 1_000              # Минимальная сумма передачи звёзд
CHECK_MIN_STARS = 1_000                 # Минимальная сумма чека
REFERRAL_REWARD_STARS = 100_000         # Награда за каждого нового реферала
AUTHOR_MIN_LEVEL = 10                   # Минимальный уровень для подачи заявки на авторство
AUTHOR_MIN_BALANCE = 100_000            # Минимальный баланс Stars для заявки на авторство

UPGRADE_COST_STARS = 300_000                 # Стоимость улучшения Plush Pepe
HEART_LOCKET_UPGRADE_COST_STARS = 200_000       # Стоимость улучшения Heart Locket
ALGORITHM_CUP_UPGRADE_COST_STARS = 200_000      # Стоимость улучшения Algorithm Cup
DUROV_CAP_UPGRADE_COST_STARS = 150_000          # Стоимость улучшения Durov's Cap
BONDED_RING_UPGRADE_COST_STARS = 150_000        # Стоимость улучшения Bonded Ring
UPGRADABLE_GIFT_KEYS = ("pepe_heart", "heart_lock_key", "cap_tg", "trophy_cup", "bonded_ring")
UPGRADED_VALUE_BOOST = 1.5                      # Глобальный буст ценности улучшенных NFT (1.5x)
MONO_PRICE_MULT = 6.0                   # Множитель ценности за Монохром-комбо (цвет модели = цвет фона)
MARKET_FEE_RATE = 0.15                  # Комиссия NFT маркета 15%
MARKET_MIN_PRICE = 1_000                # Минимальная цена лота на маркете
MARKET_MAX_PRICE = 100_000_000_000      # Максимальная цена лота на маркете (100 млрд)

SCARED_CAT_PROMO_PRICE = 750_000        # Цена лимитированного Scared Cat в разделе «Акции»
SCARED_CAT_MAX_SUPPLY = 1_000           # Жёсткий глобальный лимит тиража Scared Cat
CASE_CAPTCHA_INTERVAL = 100             # Каждые 100 открытых кейсов — проверка «Я человек»

PROMO_BONUS_BOT_USERNAME = "@NwNFTBot"
PROMO_BONUS_STARS = 50_000              # Награда за @NwNFTBot в имени ИЛИ описании (100k за оба)
PROMO_BONUS_CASE_KEY = "farm_cap"       # Бесплатный кейс за 10,000 ⭐ («Farm Кепки Дурова»)
SCARED_CAT_PROMO_INTERVAL_SEC = 3 * 3600

# Mini App & Crypto Exchange / Rocket / Upgrader (порт 3000)
MINI_APP_HOST = os.environ.get("MINI_APP_HOST", "0.0.0.0")
MINI_APP_PORT = int(os.environ.get("MINI_APP_PORT", "3000"))
MINI_APP_URL = os.environ.get("MINI_APP_URL", "").strip()
TON_STAR_RATE = 1_000.0
MEMECOIN_MIN_LEVEL = 30
MEMECOIN_CREATE_TON_COST = 20_000.0
UPGRADER_CHANCE_FACTOR = 0.78
ROCKET_UPGRADE_MULT_PENALTY = 1.28

CHECK_DISCLAIMER_QUOTE = (
    "<blockquote>"
    "⚠️ <b>Важно:</b> звёзды в этом чеке <b>ненастоящие</b> (не являются официальной валютой Telegram Stars). "
    "Это <b>внутриигровые звёзды</b>, созданные исключительно для игр и развлечений внутри бота."
    "</blockquote>"
)

BUFF_BACKDROP_OPTIONS = (20, 30, 40, 50, 75, 100)
BUFF_MODEL_OPTIONS = (20, 30, 40, 50, 75, 100)
BUFF_VALUE_OPTIONS = (10, 15, 20, 25, 35, 50)

# Пакеты донат-магазина за реальные Telegram Stars (XTR)
DONATE_PACKS: Dict[str, dict] = {
    "pack_1": {
        "title": "Starter Pack",
        "xtr_price": 69,
        "stars_reward": 25_000_000,
        "xp_reward": 50_000,
        "summary_nfts": "3× Plush Pepe (все 3 с баффами)",
        "invoice_desc": "25,000,000 игровых Stars + 3 Plush Pepe с баффами + 50,000 XP",
        "nfts": [
            ("pepe_heart", True),
            ("pepe_heart", True),
            ("pepe_heart", True),
        ],
    },
    "pack_2": {
        "title": "Pro Pack",
        "xtr_price": 129,
        "stars_reward": 50_000_000,
        "xp_reward": 250_000,
        "summary_nfts": "8 NFT (3 с баффами: Pepe, Bonded Ring, Cap)",
        "invoice_desc": "50,000,000 игровых Stars + 8 NFT (3 с баффами) + 250,000 XP",
        "nfts": [
            ("pepe_heart", True),
            ("bonded_ring", True),
            ("cap_tg", True),
            ("heart_lock_key", False),
            ("trophy_cup", False),
            ("hero_figure", False),
            ("hockey_mask", False),
            ("gem_crystal", False),
        ],
    },
    "pack_3": {
        "title": "Master Pack",
        "xtr_price": 249,
        "stars_reward": 120_000_000,
        "xp_reward": 600_000,
        "summary_nfts": "14 NFT (5 с баффами, Pepe/Ring/Cap/Locket)",
        "invoice_desc": "120,000,000 игровых Stars + 14 NFT (5 с баффами) + 600,000 XP",
        "nfts": [
            ("pepe_heart", True),
            ("pepe_heart", True),
            ("bonded_ring", True),
            ("cap_tg", True),
            ("heart_lock_key", True),
            ("trophy_cup", False),
            ("bonded_ring", False),
            ("cap_tg", False),
            ("heart_lock_key", False),
            ("hero_figure", False),
            ("hockey_mask", False),
            ("gem_crystal", False),
            ("sunglasses", False),
            ("briefcase", False),
        ],
    },
    "pack_4": {
        "title": "Grand Pack",
        "xtr_price": 499,
        "stars_reward": 300_000_000,
        "xp_reward": 1_500_000,
        "summary_nfts": "20 NFT (8 с баффами + Locket/Cup/Ring)",
        "invoice_desc": "300,000,000 игровых Stars + 20 NFT (8 с баффами) + 1,500,000 XP",
        "nfts": [
            ("pepe_heart", True),
            ("pepe_heart", True),
            ("heart_lock_key", True),
            ("heart_lock_key", True),
            ("trophy_cup", True),
            ("bonded_ring", True),
            ("bonded_ring", True),
            ("cap_tg", True),
            ("pepe_heart", False),
            ("trophy_cup", False),
            ("bonded_ring", False),
            ("cap_tg", False),
            ("heart_lock_key", False),
            ("hero_figure", False),
            ("hockey_mask", False),
            ("gem_crystal", False),
            ("sunglasses", False),
            ("briefcase", False),
            ("signet_ring", False),
            ("rose_bell_jar", False),
        ],
    },
    "pack_5": {
        "title": "VIP Legend Pack",
        "xtr_price": 999,
        "stars_reward": 750_000_000,
        "xp_reward": 4_000_000,
        "summary_nfts": "30 NFT (12 с баффами, 4× Pepe + топ NFT)",
        "invoice_desc": "750,000,000 игровых Stars + 30 NFT (12 с баффами) + 4,000,000 XP",
        "nfts": [
            ("pepe_heart", True),
            ("pepe_heart", True),
            ("pepe_heart", True),
            ("pepe_heart", True),
            ("heart_lock_key", True),
            ("heart_lock_key", True),
            ("cap_tg", True),
            ("cap_tg", True),
            ("trophy_cup", True),
            ("trophy_cup", True),
            ("bonded_ring", True),
            ("bonded_ring", True),
            ("pepe_heart", False),
            ("trophy_cup", False),
            ("bonded_ring", False),
            ("bonded_ring", False),
            ("cap_tg", False),
            ("cap_tg", False),
            ("heart_lock_key", False),
            ("heart_lock_key", False),
            ("hero_figure", False),
            ("hero_figure", False),
            ("hockey_mask", False),
            ("hockey_mask", False),
            ("gem_crystal", False),
            ("gem_crystal", False),
            ("sunglasses", False),
            ("briefcase", False),
            ("signet_ring", False),
            ("rose_bell_jar", False),
        ],
    },
}

BATTLE_MIN_CASES = 1
BATTLE_MAX_CASES = 15
BATTLE_MIN_PLAYERS = 1
BATTLE_MAX_PLAYERS = 5
BATTLE_COUNTDOWN_SECONDS = 15
_ACTIVE_BATTLE_TASKS: Dict[int, asyncio.Task] = {}

# ---------------------------------------------------------------------------
# Firebase Cloud Database Storage (Интеграция с проектом proar-5a642)
# ---------------------------------------------------------------------------

FIREBASE_SERVICE_ACCOUNT_CONFIG = {
    "type": "service_account",
    "project_id": "proar-5a642",
    "private_key_id": "039601a8db0c82988fe7ea83c3a3463301d7cd8b",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDZpDGlnJ67Qoxu\nGlxikHVtThmN7PdrOXKvVd7Nko2XWs8UZboV/6KmHREN3pEjzwdQb3tXGnWwwR+s\nnUkH5ILGoUpQ88XSxrbgTtKOU8TJbaIye8MmSDTmXHmwxRiMum/BfBdaoPR02P8P\nfLoP4ihwnKe8l7PRFRaybDungKuG7wIzCEUiZy828+DZk24z1ymqyrOwo0JSMpUI\nFWtCQb7cNTt1u9LOfCTCXKP46GTg2ghjYIUqQpVgX3zR4koKLuYava4vrNVAJT9B\nXiL+/YNGnvct5ZKT1OiHh8V4x7o2jN0R2D5sQ03z/Us6CB2LC/9NNQIxsnXp/gzB\nLvqbv94ZAgMBAAECggEABRkespmZxvAsTZ30y7hE5T5pmdSoXQzM8299rG9s5/6Q\nED3BH1J20xD7knQZY+8tutl0WFoofJn22HpyDgBxJx77GIIFVcZ4MoaWJxBY8Tuj\nYNmw/Ly/RHrREkN5AOmTGZittrPuK1iJQlRydVHKZGI/CaC8wmk4jWMR/f6lG0rY\nlLDLNCE9a6c6lLfEL72K7JRmRfbW96DIEnx6ObcqkPzaYb+pz24ewsUkY5b2QVZe\nifrQN2gAqNGq34qVp1m4/ywVC5E40sie0Un2nmINPqEA0VzVllEwgcCd5bx2X8Ya\nI2OW3TnvnoHtxNdXXY04advOMohHpNTdPd2Z5awYQQKBgQD1euUTbnEt8qcXRZYU\nmKEL5P4FvPQ7Ly3vQ8vGd7oK7lLE0zY+nEE1TW5mAaNM1W6QzZSAQsfUq8k1QZLI\n4m70f//UcnvADi/Ke12ze1xxCtHYADYb04bQ4CjfjtLk5ZstjO31mVqkNQXiSUo2\nTXYTpsi93zxj9SHaa6HT5F0zkQKBgQDi9+MtUw6ChXoiVF6V3C5AU5mtJA1eRdQy\n8AZ9GTrPAGh5ewVG+Nl9VG3ePIbZkmquh2zEo2f0LgPczegVIqDz0VBIW4LIw4wT\nmNG7MSOtJg2/wpoZexw7y1BknkWi8aV26BkEgxDEIXvvjUC3tHD9V0m2BZ4lVlsr\ng6+ZLWUuCQKBgC7JhJ3GgAXc6OHznl5AlPlaZNwdHoOlQ2EGD/G84hWxRM9E3mLi\njz8kifUhPMmpKFCrDjHACKxNLaVb4Skuly08tDr+sv1w9sTl7H8H9R+Ki2Ja7/Uv\nxNNM1h198E42QPRWlwgneXIwtPVjOKTO8MFgGYSu5qi6kQA7YXWsYeMxAoGBAItB\ncH9UoGhwoNkDTu0/pJkPMhDLN/CJg4KlRjXnDvAG3hL66ef7suV0sdxS4qIHdbET\noiab46IrwW7uXuDo2DwARvO+QeYQJJe5gaUKp0sLOBBZw9aydEYznmW9vhgVj2H/\nUao1CEpuCO6XigesjE7ECZPGqptZ+qIeL9UZxySRAoGBAIkU8wfatRMbuPmzgtst\nhEZt62FEe+0MP1QfPY6ByddLnzqlO6JpWRNUXkx6zFjf3Vy7J/J+fClAo10E4uWh\nFe7HkfG/CCamiAB4ki1WiSrrQkB/FtJAaBI3y4Ka1jN6IzniVJ0pH1Nb9N8+x8eE\nMSgIEVIFGwIPv3vQofyxnnTr\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-fbsvc@proar-5a642.iam.gserviceaccount.com",
    "client_id": "103737744652283306114",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40proar-5a642.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

class FirebaseCloudManager:
    """
    Безопасное облачное хранение базы данных SQLite (base.db) в Cloud Firestore.
    """
    def __init__(self):
        self.project_id: str = "proar-5a642"
        self.collection_name: str = "telegram_bot_data"
        self.doc_name: str = "sqlite_database"
        self.app = None
        self.firestore_client = None
        self.cached_token: Optional[str] = None
        self.token_expiry: float = 0.0
        self.initialized: bool = False
        self.active_key_id: str = "embedded"
        self.loaded_cred_dict: Optional[dict] = None
        self.last_sync_ts: float = 0.0
        self.last_sync_size: int = 0
        self.last_sync_status: str = "Ожидает первой синхронизации"
        self._lock = threading.Lock()
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._dirty: bool = False
        self._startup_download_error: bool = False
        self._cloud_doc_missing: bool = False

    @staticmethod
    def format_error(e: Exception) -> str:
        err_msg = str(e)
        if "Invalid JWT Signature" in err_msg or "invalid_grant" in err_msg:
            return "⚠️ Ошибка: Ключ сервисного аккаунта отозван в консоли Firebase (Invalid JWT Signature)."
        if "permission" in err_msg.lower() or "403" in err_msg:
            return "⚠️ Ошибка доступа: проверьте права сервисного аккаунта в Firebase Console."
        safe_msg = re.sub(r"<[^>]+>", "", err_msg)
        return f"Ошибка: {safe_msg[:200]}"

    def get_access_token(self) -> Optional[str]:
        now = time.time()
        if self.cached_token and self.token_expiry > now + 120:
            return self.cached_token

        key_dict = self.loaded_cred_dict or dict(FIREBASE_SERVICE_ACCOUNT_CONFIG)
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request
            scopes = [
                "https://www.googleapis.com/auth/datastore",
                "https://www.googleapis.com/auth/cloud-platform"
            ]
            creds = service_account.Credentials.from_service_account_info(key_dict, scopes=scopes)
            creds.refresh(Request())
            self.cached_token = creds.token
            self.token_expiry = now + 3500
            return self.cached_token
        except Exception:
            pass

        try:
            header = {"alg": "RS256", "typ": "JWT"}
            iat = int(now)
            payload = {
                "iss": key_dict["client_email"],
                "scope": "https://www.googleapis.com/auth/datastore https://www.googleapis.com/auth/cloud-platform",
                "aud": "https://oauth2.googleapis.com/token",
                "exp": iat + 3600,
                "iat": iat
            }
            def b64url(b):
                return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")

            eh = b64url(json.dumps(header).encode("utf-8"))
            ep = b64url(json.dumps(payload).encode("utf-8"))
            si = f"{eh}.{ep}".encode("utf-8")
            with tempfile.NamedTemporaryFile("w", delete=False) as kf, tempfile.NamedTemporaryFile("wb", delete=False) as df:
                kf.write(key_dict["private_key"])
                kf.flush()
                df.write(si)
                df.flush()
                sig = subprocess.check_output(["openssl", "dgst", "-sha256", "-sign", kf.name, df.name])
            assertion = f"{eh}.{ep}.{b64url(sig)}"
            data = urllib.parse.urlencode({
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion
            }).encode("utf-8")
            req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                self.cached_token = res["access_token"]
                self.token_expiry = now + int(res.get("expires_in", 3600)) - 60
                return self.cached_token
        except Exception as ex:
            log.warning(f"[Firebase Cloud] Не удалось получить OAuth2 токен через OpenSSL: {ex}")
            return None

    def init_app(self, force_reload: bool = False) -> bool:
        if self.initialized and not force_reload:
            return True

        candidate_files = [
            BASE_DIR / "firebase-service-account.json",
            BASE_DIR / "firebase_credentials.json",
        ]
        try:
            candidate_files += sorted(list(BASE_DIR.glob("*firebase*adminsdk*.json")), key=lambda p: p.stat().st_mtime, reverse=True)
            candidate_files += sorted(list(BASE_DIR.glob("*proar-5a642*.json")), key=lambda p: p.stat().st_mtime, reverse=True)
        except Exception:
            pass

        cred_dict = None
        loaded_source = "встроенного ключа"

        for candidate in candidate_files:
            if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 50:
                try:
                    with open(candidate, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if "private_key" in data and "client_email" in data:
                            data["private_key"] = data["private_key"].replace("\\n", "\n")
                            cred_dict = data
                            loaded_source = candidate.name
                            self.active_key_id = data.get("private_key_id", "external")
                            break
                except Exception as ex:
                    log.warning(f"[Firebase] Ошибка чтения {candidate}: {ex}")

        if not cred_dict:
            cred_dict = dict(FIREBASE_SERVICE_ACCOUNT_CONFIG)
            cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
            self.active_key_id = cred_dict.get("private_key_id", "embedded")

        self.loaded_cred_dict = cred_dict
        self.project_id = cred_dict.get("project_id", "proar-5a642")

        if FIREBASE_ADMIN_AVAILABLE and fb_firestore and fb_credentials:
            try:
                if force_reload and self.app:
                    try:
                        firebase_admin.delete_app(self.app)
                    except Exception:
                        pass
                    self.app = None

                cred = fb_credentials.Certificate(cred_dict)
                try:
                    self.app = firebase_admin.get_app()
                except ValueError:
                    self.app = firebase_admin.initialize_app(cred, {"projectId": self.project_id})
                self.firestore_client = fb_firestore.client(app=self.app)
                log.info(f"[Firebase] ✅ Cloud Firestore SDK инициализирован ({loaded_source})")
            except Exception as e:
                log.warning(f"[Firebase] Не удалось запустить Firestore SDK, будет использован REST API: {e}")
                self.firestore_client = None

        self.initialized = True
        return True

    @staticmethod
    def is_valid_sqlite(path: Path) -> bool:
        if not path.exists() or path.stat().st_size < 100:
            return False
        try:
            with open(path, "rb") as f:
                header = f.read(16)
                return header == b"SQLite format 3\x00"
        except Exception:
            return False

    @staticmethod
    def _count_local_users(path: Path) -> int:
        if not path.exists():
            return 0
        try:
            c = sqlite3.connect(path)
            cnt = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            c.close()
            return int(cnt)
        except Exception:
            return 0

    def download_db_on_startup(self) -> bool:
        if not self.init_app():
            self._startup_download_error = True
            return False

        try:
            b64_data = None
            doc_found = False

            if self.firestore_client:
                try:
                    doc_ref = self.firestore_client.collection(self.collection_name).document(self.doc_name)
                    doc = doc_ref.get()
                    if doc.exists:
                        doc_found = True
                        data = doc.to_dict() or {}
                        b64_data = data.get("data_gzip_b64")
                    else:
                        self._cloud_doc_missing = True
                except Exception as ex_sdk:
                    log.warning(f"[Firebase] SDK get doc: {ex_sdk}, пробуем REST...")

            if not b64_data and not doc_found:
                token = self.get_access_token()
                if token:
                    doc_url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/{self.collection_name}/{self.doc_name}"
                    req = urllib.request.Request(doc_url, headers={"Authorization": f"Bearer {token}"})
                    try:
                        with urllib.request.urlopen(req, timeout=15) as r:
                            doc_json = json.loads(r.read().decode("utf-8"))
                            doc_found = True
                            fields = doc_json.get("fields", {})
                            b64_data = fields.get("data_gzip_b64", {}).get("stringValue")
                    except urllib.error.HTTPError as he:
                        if he.code == 404:
                            log.info(f"[Firebase] ℹ️ Документ {self.collection_name}/{self.doc_name} в Firestore пока не существует.")
                            self.last_sync_status = "База еще не выгружалась в Firestore"
                            self._cloud_doc_missing = True
                            self._startup_download_error = False
                            return False
                        else:
                            raise he

            if not doc_found and self._cloud_doc_missing:
                self.last_sync_status = "База еще не выгружалась в Firestore"
                self._startup_download_error = False
                return False

            if not b64_data:
                if doc_found:
                    log.warning("[Firebase] ⚠️ Документ в Firestore существует, но data_gzip_b64 пусто. Облако защищено.")
                    self._startup_download_error = True
                else:
                    self.last_sync_status = "База еще не выгружалась в Firestore"
                    self._cloud_doc_missing = True
                return False

            raw_bytes = gzip.decompress(base64.b64decode(b64_data))
            if not raw_bytes.startswith(b"SQLite format 3\x00"):
                log.error("[Firebase] ❌ Данные из Firestore не являются SQLite базой!")
                self._startup_download_error = True
                return False

            tmp_path = BASE_DIR / "base.db.tmp_download"
            with open(tmp_path, "wb") as f:
                f.write(raw_bytes)

            if DB_PATH.exists():
                try:
                    shutil.copy2(DB_PATH, BASE_DIR / "base.db.backup_local")
                except Exception:
                    pass

            shutil.move(tmp_path, DB_PATH)
            self.last_sync_ts = time.time()
            self.last_sync_size = len(raw_bytes)
            self._startup_download_error = False
            self._cloud_doc_missing = False
            self.last_sync_status = f"Восстановлена из Firestore ({len(raw_bytes):,} байт)"
            log.info(f"[Firebase] ✅ База base.db ({len(raw_bytes):,} байт) успешно восстановлена из Firestore!")
            return True
        except Exception as e:
            log.error(f"[Firebase] Ошибка скачивания base.db из Firestore: {e}")
            self.last_sync_status = self.format_error(e)
            self._startup_download_error = True
            return False

    def upload_db_to_cloud(self, force: bool = False) -> bool:
        if not self.init_app():
            return False

        with self._lock:
            try:
                if self._startup_download_error:
                    log.warning("[Firebase] 🛑 Anti-Wipe: при старте была ошибка чтения Firestore, автовыгрузка заблокирована.")
                    return False

                if not DB_PATH.exists() or DB_PATH.stat().st_size < 100:
                    return False

                if not self.is_valid_sqlite(DB_PATH):
                    return False

                # Защита от затирания непустой облачной базы пустой локальной
                if self._count_local_users(DB_PATH) == 0 and not self._cloud_doc_missing:
                    if self.firestore_client:
                        try:
                            snap = self.firestore_client.collection(self.collection_name).document(self.doc_name).get()
                            if snap.exists:
                                log.warning("[Firebase] 🛑 Anti-Wipe: локальная база пуста (0 игроков), а в Firestore уже есть база. Отмена!")
                                return False
                        except Exception:
                            pass

                current_size = DB_PATH.stat().st_size
                if not force and self.last_sync_ts > 0 and (time.time() - self.last_sync_ts < 15):
                    return True

                snapshot_path = BASE_DIR / "base.db.upload_snapshot"
                try:
                    src_conn = sqlite3.connect(DB_PATH)
                    dst_conn = sqlite3.connect(snapshot_path)
                    src_conn.backup(dst_conn)
                    dst_conn.close()
                    src_conn.close()
                    target_file = snapshot_path
                except Exception:
                    target_file = DB_PATH

                with open(target_file, "rb") as f:
                    raw_db = f.read()

                if snapshot_path.exists():
                    try:
                        snapshot_path.unlink()
                    except Exception:
                        pass

                if not raw_db.startswith(b"SQLite format 3\x00"):
                    return False

                compressed = gzip.compress(raw_db, compresslevel=9)
                b64_data = base64.b64encode(compressed).decode("ascii")
                sha256_hash = hashlib.sha256(raw_db).hexdigest()
                now_utc = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
                now_ts = time.time()

                saved = False

                if self.firestore_client:
                    try:
                        doc_ref = self.firestore_client.collection(self.collection_name).document(self.doc_name)
                        doc_ref.set({
                            "database_file": "base.db",
                            "file_size": current_size,
                            "compressed_size": len(compressed),
                            "sha256": sha256_hash,
                            "updated_at": now_utc,
                            "updated_ts": now_ts,
                            "data_gzip_b64": b64_data
                        })
                        saved = True
                    except Exception as ex_sdk:
                        log.warning(f"[Firebase] Ошибка сохранения через SDK: {ex_sdk}, переключение на REST...")

                if not saved:
                    token = self.get_access_token()
                    if not token:
                        raise RuntimeError("Не удалось получить OAuth2 токен для Firestore")

                    doc_url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/{self.collection_name}/{self.doc_name}"
                    doc_body = json.dumps({
                        "fields": {
                            "database_file": {"stringValue": "base.db"},
                            "file_size": {"integerValue": str(current_size)},
                            "compressed_size": {"integerValue": str(len(compressed))},
                            "sha256": {"stringValue": sha256_hash},
                            "updated_at": {"stringValue": now_utc},
                            "updated_ts": {"doubleValue": now_ts},
                            "data_gzip_b64": {"stringValue": b64_data}
                        }
                    }).encode("utf-8")
                    req = urllib.request.Request(doc_url, data=doc_body, headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }, method="PATCH")
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        if resp.status in (200, 201):
                            saved = True

                if saved:
                    self.last_sync_ts = time.time()
                    self.last_sync_size = current_size
                    self.last_sync_status = f"Синхронизировано в {datetime.datetime.now().strftime('%H:%M:%S')} ({current_size:,} байт)"
                    self._dirty = False
                    log.info(f"[Firebase] ☁️ База base.db сохранена в Cloud Firestore ({current_size:,} -> {len(compressed):,} байт)")
                    return True
                else:
                    raise RuntimeError("Firestore не подтвердил сохранение документа")
            except Exception as e:
                log.error(f"[Firebase] Ошибка выгрузки в Firestore: {e}")
                self.last_sync_status = self.format_error(e)
                return False

    def schedule_sync(self):
        self._dirty = True

    def start_periodic_sync(self, interval_seconds: int = 60):
        if self._sync_thread and self._sync_thread.is_alive():
            return

        def _worker():
            while not self._stop_event.is_set():
                self._stop_event.wait(interval_seconds)
                if self._stop_event.is_set():
                    break
                try:
                    self.upload_db_to_cloud(force=False)
                except Exception as e:
                    log.error(f"[Firebase Worker] Ошибка: {e}")

        self._sync_thread = threading.Thread(target=_worker, daemon=True, name="FirebaseSyncWorker")
        self._sync_thread.start()

    def stop(self):
        self._stop_event.set()
        if self.initialized:
            self.upload_db_to_cloud(force=False)

FirebaseStorageManager = FirebaseCloudManager
firebase_manager = FirebaseCloudManager()

def _on_shutdown():
    try:
        firebase_manager.upload_db_to_cloud(force=False)
    except Exception:
        pass

atexit.register(_on_shutdown)

# FSM Состояния
(
    WAIT_CLAN_TAG,
    WAIT_CLAN_NAME,
    WAIT_CLAN_DESC,
    WAIT_CLAN_TYPE,
    WAIT_CLAN_FEE,
    WAIT_ADMIN_GIVE_STARS_USER,
    WAIT_ADMIN_GIVE_STARS_AMOUNT,
    WAIT_ADMIN_GIVE_NFT_USER,
    WAIT_PROFILE_BG,
    WAIT_ADMIN_BAN_USER,
    WAIT_ADMIN_BAN_HOURS,
    WAIT_ADMIN_BAN_REASON,
    WAIT_ADMIN_UNBAN_USER,
    WAIT_CLAN_AVATAR,
    WAIT_CLAN_DONATE_STARS,
    WAIT_ADMIN_FIREBASE_JSON,
    WAIT_GIFT_TRANSFER_USER,
    WAIT_MARKET_OFFER_PRICE,
    WAIT_CHECK_TARGET,
    WAIT_CHECK_AMOUNT,
    WAIT_CHECK_PASSWORD,
    WAIT_CHECK_CLAIM_PASSWORD,
    WAIT_AUTHOR_APP_CHANNELS,
    WAIT_AUTHOR_APP_AGE,
    WAIT_AUTHOR_APP_CONFIRM,
    WAIT_ADMIN_APP_REJECT_REASON,
    WAIT_ADMIN_GIVE_AUTH_STARS_USER,
    WAIT_ADMIN_GIVE_AUTH_STARS_AMOUNT,
    WAIT_AUTHOR_DEP_AMOUNT,
    WAIT_AUTHOR_WD_AMOUNT,
    WAIT_AUTHOR_CHANNEL_INPUT,
    WAIT_GW_CHANNELS,
    WAIT_GW_TEXT,
    WAIT_GW_PHOTO,
    WAIT_GW_WINNERS,
    WAIT_GW_PRIZE,
    WAIT_GW_BTN_CONFIG,
    WAIT_GW_BTN_TEXT,
    WAIT_GW_END_COND,
    WAIT_GW_END_CUSTOM_TIME,
    WAIT_GW_END_CUSTOM_MAX,
    WAIT_GW_PUBLISH,
    WAIT_GW_SCHED_TIME,
    WAIT_ADMIN_BROADCAST_MSG,
    WAIT_ADMIN_BROADCAST_CONFIRM,
    WAIT_PROMO_REDEEM_CODE,
    WAIT_ADMIN_PROMO_CODE,
    WAIT_ADMIN_PROMO_REWARD_TYPE,
    WAIT_ADMIN_PROMO_STARS,
    WAIT_ADMIN_PROMO_GIFT,
    WAIT_ADMIN_PROMO_GIFT_COUNT,
    WAIT_ADMIN_PROMO_MAX_USES,
    WAIT_ADMIN_PROMO_EDIT_MAX,
) = range(53)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("nft_bot")

# ---------------------------------------------------------------------------
# Загрузка шрифтов
# ---------------------------------------------------------------------------

FONT_REGULAR_PATH = FONTS_DIR / "NotoSans.ttf"
FONT_BOLD_PATH = FONTS_DIR / "NotoSans-Bold.ttf"

def ensure_fonts_exist():
    if not FONT_REGULAR_PATH.exists():
        url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                FONT_REGULAR_PATH.write_bytes(r.content)
        except Exception as e:
            log.warning("Не удалось скачать шрифт Regular: %s", e)

    if not FONT_BOLD_PATH.exists():
        url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Bold.ttf"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                FONT_BOLD_PATH.write_bytes(r.content)
        except Exception as e:
            log.warning("Не удалось скачать шрифт Bold: %s", e)

ensure_fonts_exist()

# ---------------------------------------------------------------------------
# Очистка строк, цветные кнопки и компактное форматирование
# ---------------------------------------------------------------------------

try:
    _BTN_HAS_STYLE = "style" in inspect.signature(InlineKeyboardButton.__init__).parameters
except Exception:
    _BTN_HAS_STYLE = False

try:
    _BTN_HAS_ICON_EMOJI = "icon_custom_emoji_id" in inspect.signature(InlineKeyboardButton.__init__).parameters
except Exception:
    _BTN_HAS_ICON_EMOJI = False

# Премиум-эмодзи интерфейса (Telegram Premium / Bot API 9.4)
CE_IDS: Dict[str, str] = {
    "eyes": "5210956306952758910",
    "smile": "5461117441612462242",
    "bolt": "5456140674028019486",
    "comet": "5224607267797606837",
    "bag": "5229064374403998351",
    "no_entry": "5260293700088511294",
    "prohibited": "5240241223632954241",
    "excl": "5274099962655816924",
    "dbl_excl": "5440660757194744323",
    "excl_q": "5314504236132747481",
    "quest": "5436113877181941026",
    "warn": "5447644880824181073",
    "warn2": "5420323339723881652",
    "globe": "5447410659077661506",
    "chat": "5443038326535759644",
    "thought": "5467538555158943525",
    "quest2": "5452069934089641166",
    "chart_bar": "5231200819986047254",
    "up_tri": "5449683594425410231",
    "down_tri": "5447183459602669338",
    "candle": "5451882707875276247",
    "chart_up": "5244837092042750681",
    "chart_down": "5246762912428603768",
    "check": "5206607081334906820",
    "cross": "5210952531676504517",
    "cool": "5222079954421818267",
    "bell": "5458603043203327669",
    "nerd": "5391112412445288650",
    "clown": "5269531045165816230",
    "lips": "5395444514028529554",
    "pin": "5397782960512444700",
    "dollar": "5409048419211682843",
    "money_wings": "5233326571099534068",
    "money_wings2": "5231449120635370684",
    "money_wings3": "5278751923338490157",
    "money_wings4": "5290017777174722330",
    "money_wings5": "5231005931550030290",
    "exchange": "5402186569006210455",
    "play": "5264919878082509254",
    "red_dot": "5411225014148014586",
    "green_dot": "5416081784641168838",
    "arrow_right": "5416117059207572332",
    "fire": "5424972470023104089",
    "boom": "5276032951342088188",
    "mic_studio": "5294339927318739359",
    "mic": "5224736245665511429",
    "megaphone": "5424818078833715060",
    "shush": "5431609822288033666",
    "thumbs_down": "5449875686837726134",
    "speaking": "5460795800101594035",
    "search": "5231012545799666522",
    "shield": "5251203410396458957",
    "link": "5271604874419647061",
    "desktop": "5282843764451195532",
    "copyright": "5323442290708985472",
    "info": "5334544901428229844",
    "thumbs_up": "5337080053119336309",
    "play2": "5348125953090403204",
    "pause": "5359543311897998264",
    "hundred": "5341498088408234504",
    "refresh": "5375338737028841420",
    "top": "5415655814079723871",
    "new": "5382357040008021292",
    "soon": "5440621591387980068",
    "pin_loc": "5391032818111363540",
    "plus": "5397916757333654639",
    "gem": "5427168083074628963",
    "star": "5438496463044752972",
    "sparkles": "5325547803936572038",
    "crown": "5217822164362739968",
    "trash": "5445267414562389170",
    "bookmark": "5222444124698853913",
    "mail": "5253742260054409879",
    "lock": "5296369303661067030",
    "wow": "5303479226882603449",
    "clip": "5305265301917549162",
    "gear": "5341715473882955310",
    "game": "5361741454685256344",
    "speaker": "5388632425314140043",
    "hourglass": "5386367538735104399",
    "down_arrow": "5406745015365943482",
    "sun": "5402477260982731644",
    "rain": "5399913388845322366",
    "moon": "5449569374065152798",
    "snow": "5449449325434266744",
    "rainbow": "5409109841538994759",
    "drop": "5393512611968995988",
    "calendar": "5413879192267805083",
    "bulb": "5422439311196834318",
    "gold": "5440539497383087970",
    "silver": "5447203607294265305",
    "bronze": "5453902265922376865",
    "music": "5463107823946717464",
    "free": "5406756500108501710",
    "pencil": "5395444784611480792",
    "siren": "5395695537687123235",
}

CE_FALLBACKS: Dict[str, str] = {
    "eyes": "👀", "smile": "🙂", "bolt": "⚡️", "comet": "☄️", "bag": "🛍",
    "no_entry": "⛔️", "prohibited": "🚫", "excl": "❗️", "dbl_excl": "‼️",
    "excl_q": "⁉️", "quest": "❓", "warn": "⚠️", "warn2": "⚠️", "globe": "🌐",
    "chat": "💬", "thought": "💭", "quest2": "❓", "chart_bar": "📊",
    "up_tri": "🔼", "down_tri": "🔽", "candle": "🕯", "chart_up": "📈",
    "chart_down": "📉", "check": "✔️", "cross": "❌", "cool": "🆒",
    "bell": "🔔", "nerd": "🥸", "clown": "🤡", "lips": "🫦", "pin": "📌",
    "dollar": "💵", "money_wings": "💸", "money_wings2": "💸",
    "money_wings3": "💸", "money_wings4": "💸", "money_wings5": "💸",
    "exchange": "💱", "play": "▶️", "red_dot": "🔴", "green_dot": "🟢",
    "arrow_right": "➡️", "fire": "🔥", "boom": "💥", "mic_studio": "🎙",
    "mic": "🎤", "megaphone": "📣", "shush": "🤫", "thumbs_down": "👎",
    "speaking": "🗣️", "search": "🔍", "shield": "🛡", "link": "🔗",
    "desktop": "🖥", "copyright": "©", "info": "ℹ️", "thumbs_up": "👍",
    "play2": "▶️", "pause": "⏸", "hundred": "💯", "refresh": "🔄",
    "top": "🔝", "new": "🆕", "soon": "🔜", "pin_loc": "📍", "plus": "➕",
    "gem": "💎", "star": "⭐️", "sparkles": "✨", "crown": "👑", "trash": "🗑",
    "bookmark": "🔖", "mail": "✉️", "lock": "🔒", "wow": "😮", "clip": "📎",
    "gear": "⚙️", "game": "🎮", "speaker": "🔈", "hourglass": "⌛",
    "down_arrow": "⬇️", "sun": "☀️", "rain": "🌧", "moon": "🌛", "snow": "❄️",
    "rainbow": "🌈", "drop": "💧", "calendar": "🗓", "bulb": "💡",
    "gold": "🥇", "silver": "🥈", "bronze": "🥉", "music": "🎵",
    "free": "🆓", "pencil": "✏️", "siren": "🚨",
}

CUSTOM_GIFT_EMOJI_IDS: List[str] = [
    "5456203011183371567", "5456305012361687632", "5456496533543346915", "5456264699798643395",
    "5456147077824274112", "5454407250997173562", "5453907269559278890", "5453896618040386188",
    "5453963559400660818", "5456346969897199046", "5454161501558430632", "5456265846554910766",
    "5456647377089749607", "5454037596046906791", "5456468276953506363", "5454064194779373874",
]

CUSTOM_PEPE_EMOJI_IDS: List[str] = [
    "5422543107671485267", "5422821717905009997", "5425082545739951006", "5424934983548560744",
    "5424690578434581413", "5424813272765330422", "5424953443317998789", "5422343627915422286",
    "5424955857089616771", "5425144049671627237", "5422676844363149011", "5424923975547377257",
    "5422796012525744455", "5422627061397220424",
]

def ce(key: str, fallback: Optional[str] = None) -> str:
    fb = fallback or CE_FALLBACKS.get(key, "✨")
    eid = CE_IDS.get(key)
    if not eid:
        return fb
    return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'

def ce_gift(index: Optional[int] = None) -> str:
    eid = CUSTOM_GIFT_EMOJI_IDS[index % len(CUSTOM_GIFT_EMOJI_IDS)] if index is not None else random.choice(CUSTOM_GIFT_EMOJI_IDS)
    return f'<tg-emoji emoji-id="{eid}">🎁</tg-emoji>'

def ce_pepe(index: Optional[int] = None) -> str:
    eid = CUSTOM_PEPE_EMOJI_IDS[index % len(CUSTOM_PEPE_EMOJI_IDS)] if index is not None else random.choice(CUSTOM_PEPE_EMOJI_IDS)
    return f'<tg-emoji emoji-id="{eid}">🐸</tg-emoji>'

def gift_tg_emoji(gift_key: str) -> str:
    if gift_key == "pepe_heart":
        return ce_pepe()
    return ce_gift()

def make_btn(
    text: str,
    style: Optional[str] = None,
    emoji_key: Optional[str] = None,
    emoji_id: Optional[str] = None,
    **kwargs,
) -> InlineKeyboardButton:
    """Создаёт InlineKeyboardButton с поддержкой Bot API 9.4 style и icon_custom_emoji_id."""
    if style in ("primary", "success", "danger"):
        if _BTN_HAS_STYLE:
            kwargs["style"] = style
        else:
            api_kw = dict(kwargs.pop("api_kwargs", {}) or {})
            api_kw["style"] = style
            kwargs["api_kwargs"] = api_kw

    eid = emoji_id or (CE_IDS.get(emoji_key) if emoji_key else None)
    if eid:
        if _BTN_HAS_ICON_EMOJI:
            kwargs["icon_custom_emoji_id"] = eid
        else:
            api_kw = dict(kwargs.pop("api_kwargs", {}) or {})
            api_kw["icon_custom_emoji_id"] = eid
            kwargs["api_kwargs"] = api_kw
    return InlineKeyboardButton(text, **kwargs)

async def safe_edit_or_reply(
    query: CallbackQuery,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = ParseMode.HTML,
) -> None:
    """Редактирует текстовое сообщение без лишнего удаления; пересылает только при наличии медиа."""
    msg = query.message
    if msg and not msg.photo and not msg.document and not msg.video:
        try:
            await query.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
            return
        except Exception as e:
            if "message is not modified" in str(e).lower():
                return
    if msg and (msg.photo or msg.document or msg.video):
        try:
            await msg.delete()
        except Exception:
            pass
    if msg:
        await msg.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup)

async def get_bot_username(bot) -> str:
    global _BOT_USERNAME_CACHE
    if _BOT_USERNAME_CACHE:
        return _BOT_USERNAME_CACHE
    try:
        uname = getattr(bot, "username", None)
        if not uname:
            me = await bot.get_me()
            uname = me.username
        if uname:
            _BOT_USERNAME_CACHE = uname
            return uname
    except Exception:
        pass
    return "bot"

def clean_html(text: Optional[str]) -> str:
    if not text:
        return ""
    return html.escape(str(text))

def _entity_type_str(ent) -> str:
    raw = getattr(ent, "type", None)
    val = getattr(raw, "value", raw)
    return str(val or "").strip().lower()

def _extract_custom_emoji_id(ent) -> str:
    ce_id = getattr(ent, "custom_emoji_id", None)
    if not ce_id:
        ak = getattr(ent, "api_kwargs", None)
        if isinstance(ak, dict):
            ce_id = ak.get("custom_emoji_id")
    if not ce_id and hasattr(ent, "to_dict"):
        try:
            d = ent.to_dict()
            if isinstance(d, dict):
                ce_id = d.get("custom_emoji_id")
        except Exception:
            pass
    return str(ce_id).strip() if ce_id else ""

def entities_to_html(text: Optional[str], entities) -> str:
    """Конвертирует Telegram Message + entities (UTF-16) в валидный вложенный HTML (статьи, цитаты, таблицы, custom_emoji)."""
    if not text:
        return ""
    if not entities:
        return html.escape(str(text), quote=False)

    raw_text = str(text)
    raw_u16 = raw_text.encode("utf-16-le")
    total_units = len(raw_u16) // 2

    def _u16_slice(u_start: int, u_end: int) -> str:
        s = max(0, min(total_units, u_start))
        e = max(s, min(total_units, u_end))
        return raw_u16[s * 2 : e * 2].decode("utf-16-le", errors="surrogatepass")

    # Приоритет вложенности: внешние блочные -> ссылки -> стилевые -> custom_emoji внутри всего
    _PRIO = {
        "blockquote": 10,
        "expandable_blockquote": 10,
        "pre": 20,
        "text_link": 30,
        "text_mention": 30,
        "url": 35,
        "bold": 40,
        "italic": 42,
        "underline": 44,
        "strikethrough": 46,
        "spoiler": 48,
        "code": 50,
        "custom_emoji": 90,
    }

    spans: List[dict] = []
    code_ranges: List[Tuple[int, int]] = []
    link_ranges: List[Tuple[int, int]] = []

    for idx, ent in enumerate(entities):
        etype = _entity_type_str(ent)
        if etype not in _PRIO:
            continue
        start = max(0, int(getattr(ent, "offset", 0) or 0))
        length = max(0, int(getattr(ent, "length", 0) or 0))
        end = min(total_units, start + length)
        if end <= start:
            continue
        if etype in ("code", "pre"):
            code_ranges.append((start, end))
        elif etype in ("text_link", "text_mention"):
            link_ranges.append((start, end))

        open_tag, close_tag = "", ""
        if etype == "bold":
            open_tag, close_tag = "<b>", "</b>"
        elif etype == "italic":
            open_tag, close_tag = "<i>", "</i>"
        elif etype == "underline":
            open_tag, close_tag = "<u>", "</u>"
        elif etype == "strikethrough":
            open_tag, close_tag = "<s>", "</s>"
        elif etype == "spoiler":
            open_tag, close_tag = "<tg-spoiler>", "</tg-spoiler>"
        elif etype == "code":
            open_tag, close_tag = "<code>", "</code>"
        elif etype == "pre":
            lang = getattr(ent, "language", None)
            if lang:
                open_tag = f'<pre><code class="language-{html.escape(str(lang), quote=True)}">'
                close_tag = "</code></pre>"
            else:
                open_tag, close_tag = "<pre>", "</pre>"
        elif etype == "text_link":
            url_val = getattr(ent, "url", None) or ""
            if url_val:
                open_tag = f'<a href="{html.escape(str(url_val), quote=True)}">'
                close_tag = "</a>"
        elif etype == "text_mention":
            t_user = getattr(ent, "user", None)
            uid_val = getattr(t_user, "id", 0) if t_user else 0
            if uid_val:
                open_tag = f'<a href="tg://user?id={uid_val}">'
                close_tag = "</a>"
        elif etype == "url":
            raw_u = _u16_slice(start, end).strip()
            if raw_u:
                href = raw_u if re.match(r"^(?:https?|tg)://", raw_u, re.IGNORECASE) else f"https://{raw_u}"
                open_tag = f'<a href="{html.escape(href, quote=True)}">'
                close_tag = "</a>"
        elif etype == "blockquote":
            open_tag, close_tag = "<blockquote>", "</blockquote>"
        elif etype == "expandable_blockquote":
            open_tag, close_tag = "<blockquote expandable>", "</blockquote>"
        elif etype == "custom_emoji":
            ce_id = _extract_custom_emoji_id(ent)
            if ce_id:
                open_tag = f'<tg-emoji emoji-id="{html.escape(ce_id, quote=True)}">'
                close_tag = "</tg-emoji>"

        if open_tag and close_tag:
            spans.append({
                "id": idx,
                "type": etype,
                "start": start,
                "end": end,
                "prio": _PRIO[etype],
                "open": open_tag,
                "close": close_tag,
            })

    # Убираем авто-url внутри code/pre или уже заданного text_link
    filtered_spans: List[dict] = []
    for sp in spans:
        if sp["type"] == "url":
            inside_code = any(cs <= sp["start"] and sp["end"] <= ce_u for cs, ce_u in code_ranges)
            inside_link = any(ls <= sp["start"] and sp["end"] <= le_u for ls, le_u in link_ranges)
            if inside_code or inside_link:
                continue
        filtered_spans.append(sp)

    if not filtered_spans:
        return html.escape(raw_text, quote=False)

    starts_at: Dict[int, List[dict]] = {}
    ends_at: Dict[int, set[int]] = {}
    points_set = {0, total_units}
    for sp in filtered_spans:
        starts_at.setdefault(sp["start"], []).append(sp)
        ends_at.setdefault(sp["end"], set()).add(sp["id"])
        points_set.add(sp["start"])
        points_set.add(sp["end"])

    points = sorted(points_set)
    active_stack: List[dict] = []
    out_parts: List[str] = []

    for i, pos in enumerate(points):
        closing_ids = ends_at.get(pos)
        reopen_list: List[dict] = []
        if closing_ids and active_stack:
            # Находим самый глубокий закрываемый тег в стеке; всё выше временно закрываем и потом переоткрываем
            earliest_idx = None
            for s_idx, item in enumerate(active_stack):
                if item["id"] in closing_ids:
                    earliest_idx = s_idx
                    break
            if earliest_idx is not None:
                while len(active_stack) > earliest_idx:
                    popped = active_stack.pop()
                    out_parts.append(popped["close"])
                    if popped["id"] not in closing_ids:
                        reopen_list.append(popped)
                reopen_list.reverse()

        opening_here = starts_at.get(pos, [])
        if reopen_list or opening_here:
            # Переоткрытые теги идут первыми (в порядке вложенности), затем новые (снаружи внутрь)
            for sp in reopen_list:
                active_stack.append(sp)
                out_parts.append(sp["open"])
            for sp in sorted(opening_here, key=lambda s: (s["prio"], -s["end"], s["id"])):
                active_stack.append(sp)
                out_parts.append(sp["open"])

        if i + 1 < len(points):
            nxt = points[i + 1]
            if nxt > pos:
                out_parts.append(html.escape(_u16_slice(pos, nxt), quote=False))

    while active_stack:
        out_parts.append(active_stack.pop()["close"])

    return "".join(out_parts)

def extract_message_html_with_custom_emojis(msg) -> str:
    if msg is None:
        return ""
    if getattr(msg, "text", None) is not None:
        ents = getattr(msg, "entities", None) or []
        return entities_to_html(msg.text, ents)
    if getattr(msg, "caption", None) is not None:
        ents = getattr(msg, "caption_entities", None) or []
        return entities_to_html(msg.caption, ents)
    return ""

def _telegram_visible_len(html_text: str) -> int:
    """Считает видимую длину текста после парсинга Telegram HTML (теги и атрибуты не учитываются)."""
    if not html_text:
        return 0
    plain = re.sub(r"<[^>]+>", "", html_text)
    plain = html.unescape(plain)
    return len(plain)

def _extract_first_external_url(html_text: str) -> Optional[str]:
    """Ищет первую URL-ссылку в HTML-тексте поста автора (для превью статьи)."""
    if not html_text:
        return None
    m_href = re.search(r'<a\s+href="(https?://[^"]+)"', html_text, re.IGNORECASE)
    if m_href:
        return html.unescape(m_href.group(1))
    plain = re.sub(r"<[^>]+>", " ", html_text)
    m_raw = re.search(r"(https?://[^\s<>\"']+)", plain, re.IGNORECASE)
    if m_raw:
        return html.unescape(m_raw.group(1))
    return None

def _build_link_preview_kwargs(body_html: str) -> dict:
    """Разрешает превью статьи/ссылки, если автор вставил URL, и отключает превью для внутренних deep-link кнопок."""
    ext_url = _extract_first_external_url(body_html)
    if ext_url:
        if LinkPreviewOptions is not None:
            return {"link_preview_options": LinkPreviewOptions(is_disabled=False, url=ext_url)}
        return {"disable_web_page_preview": False}
    if LinkPreviewOptions is not None:
        return {"link_preview_options": LinkPreviewOptions(is_disabled=True)}
    return {"disable_web_page_preview": True}

def strip_all_emojis_for_image(
    text: Optional[str],
    fallback_username: Optional[str] = None,
    fallback_id: Optional[int] = None,
) -> str:
    emoji_pattern = re.compile(
        "["
        "\U00010000-\U0010FFFF"
        "\u200d"
        "\ufe0f"
        "\ufe0e"
        "\u2600-\u27bf"
        "\u2300-\u23ff"
        "\u2b50"
        "\u2b06"
        "\u2190-\u21ff"
        "\u2934-\u2935"
        "\u3297"
        "\u3299"
        "\u3030"
        "\u00a9"
        "\u00ae"
        "]+",
        flags=re.UNICODE
    )

    def _clean(raw: str) -> str:
        cleaned = emoji_pattern.sub("", raw)
        res = []
        for char in unicodedata.normalize('NFKC', cleaned):
            cat = unicodedata.category(char)
            if cat in ('So', 'Cn', 'Co', 'Sk', 'Cs', 'Cf'):
                continue
            # Оставляем только символы, которые гарантированно отображаются шрифтом (латиница, кириллица, цифры, пунктуация)
            code = ord(char)
            if (
                0x0020 <= code <= 0x024F
                or 0x0400 <= code <= 0x04FF
                or char in ('_', '-', '.', '@', '#', ' ', '№')
            ):
                res.append(char)
        return re.sub(r"\s+", " ", "".join(res)).strip()

    _placeholders = {"unknown", "player", "none", "null"}

    if text:
        cleaned_main = _clean(str(text))
        if cleaned_main and cleaned_main.lower() not in _placeholders:
            return cleaned_main

    if fallback_username:
        uname_clean = _clean(str(fallback_username).lstrip("@"))
        if uname_clean:
            return f"@{uname_clean}"

    if fallback_id is not None:
        return f"ID {fallback_id}"

    return "User"

def normalize_telegram_name(
    name: Optional[str],
    username: Optional[str] = None,
    user_id: Optional[int] = None,
) -> str:
    _placeholders = {"unknown", "player", "none", "null"}
    raw_name = (name or "").strip()
    if raw_name and raw_name.lower() not in _placeholders:
        cleaned = re.sub(r"[\(\[\{].*?[\)\]\}]", "", raw_name).strip()
        if not cleaned:
            cleaned = raw_name
        # Проверяем, не состоит ли имя только из пробелов/невидимых символов
        if re.sub(r"[\s\u200b-\u200f\u2060\ufeff]+", "", cleaned) and cleaned.lower() not in _placeholders:
            return cleaned

    if username:
        uname = str(username).strip().lstrip("@")
        if uname and uname.lower() not in _placeholders:
            return f"@{uname}"

    if user_id is not None:
        return f"ID {user_id}"

    return "User"

def fmt_stars_compact(stars: int) -> str:
    """Форматирует звёзды: от 10,000,000 сокращает в млн / млрд / трлн."""
    val = int(stars or 0)
    abs_v = abs(val)
    if abs_v >= 1_000_000_000_000:
        num = val / 1_000_000_000_000
        unit = "трлн"
    elif abs_v >= 1_000_000_000:
        num = val / 1_000_000_000
        unit = "млрд"
    elif abs_v >= 10_000_000:
        num = val / 1_000_000
        unit = "млн"
    else:
        return f"{val:,}"
    num_str = f"{num:.2f}".rstrip("0").rstrip(".")
    return f"{num_str} {unit}"

def fmt_stars_rub(stars: int) -> str:
    rub_val = int(round(stars * STAR_RUB_RATE))
    if abs(stars) >= 10_000_000:
        return f"{fmt_stars_compact(stars)} ⭐ (~{fmt_stars_compact(rub_val)} ₽)"
    return f"{stars:,} ⭐ (~{rub_val:,} ₽)"

def fmt_ton(ton: float) -> str:
    return f"{ton:.2f} TON (~{ton * TON_RUB_RATE:,.0f} ₽)"

def seconds_to_hms(sec: int) -> str:
    sec = max(0, sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h: return f"{h} ч {m} мин"
    if m: return f"{m} мин {s} сек"
    return f"{s} сек"

# ---------------------------------------------------------------------------
# NFT Каталог
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GiftDef:
    key: str
    name: str
    stars: int
    chance: float
    xp: int
    model_group: str
    model_name: str

    @property
    def ton(self) -> float:
        return round((self.stars * STAR_RUB_RATE) / TON_RUB_RATE, 3)

    @property
    def rub(self) -> float:
        return round(self.stars * STAR_RUB_RATE, 2)


GIFTS: list[GiftDef] = [
    GiftDef("pepe_heart", "Plush Pepe (Пепе с сердцем)", 480_000, 0.0005, 120_000, "animals", "Животные и маскоты"),
    GiftDef("durov_dog", "Snoop Dogg (Пёс Дурова)", 3_000, 0.45, 1_800, "animals", "Животные и маскоты"),
    GiftDef("hockey_mask", "Hockey Mask (Хоккейная маска)", 26_000, 0.006, 15_000, "animals", "Животные и маскоты"),
    GiftDef("teddy_patrick", "Irish Bear (Мишка-лепрекон)", 65, 10.00, 50, "animals", "Животные и маскоты"),
    GiftDef("teddy_heart_white", "New Year's Bear (Белый мишка)", 65, 10.00, 50, "animals", "Животные и маскоты"),
    GiftDef("teddy_santa", "Santa Bear (Мишка-Санта)", 65, 10.00, 50, "animals", "Животные и маскоты"),
    GiftDef("teddy_football", "Football Bear (Мишка-футболист)", 65, 10.00, 50, "animals", "Животные и маскоты"),
    GiftDef("bunny_teddy", "Easter Bear (Мишка-кролик)", 65, 10.00, 50, "animals", "Животные и маскоты"),
    GiftDef("teddy_soldier", "Bear Soldier (Мишка-солдат)", 65, 10.00, 50, "animals", "Животные и маскоты"),
    GiftDef("teddy_builder", "Polar Bear (Мишка-строитель)", 65, 10.00, 50, "animals", "Животные и маскоты"),
    GiftDef("clown_teddy", "Clown Bear (Мишка-клоун)", 65, 10.00, 50, "animals", "Животные и маскоты"),
    GiftDef("teddy_flowers", "Pretty Posy (Мишка с букетом)", 420, 6.00, 220, "animals", "Животные и маскоты"),
    GiftDef("hero_figure", "Durov Figure (Фигурка Дурова)", 42_000, 0.003, 28_000, "figures", "Фигурки и трофеи"),
    GiftDef("trophy_cup", "Algorithm Cup (Кубок Чемпиона)", 85_000, 0.002, 42_000, "figures", "Фигурки и трофеи"),
    GiftDef("cap_tg", "Durov's Cap (Кепка Дурова)", 38_000, 0.004, 24_000, "figures", "Фигурки и трофеи"),
    GiftDef("sunglasses", "Durov's Glasses (Очки Дурова)", 9_500, 0.020, 6_500, "figures", "Фигурки и трофеи"),
    GiftDef("torch", "Liberty Figure (Факел Свободы)", 400, 6.20, 210, "figures", "Фигурки и трофеи"),
    GiftDef("bonded_ring", "Bonded Ring (Кольцо)", 40_000, 0.004, 24_000, "artifacts", "Артефакты и украшения"),
    GiftDef("heart_lock_key", "Heart Locket (Сердце-замок)", 22_000, 0.008, 12_000, "artifacts", "Артефакты и украшения"),
    GiftDef("gem_crystal", "Astral Shard (Кристалл Алмаз)", 12_000, 0.015, 7_500, "artifacts", "Артефакты и украшения"),
    GiftDef("signet_ring", "Signet Ring (Перстень)", 3_500, 0.70, 2_200, "artifacts", "Артефакты и украшения"),
    GiftDef("rose_bell_jar", "Eternal Rose (Роза под колпаком)", 2_600, 0.90, 1_700, "artifacts", "Артефакты и украшения"),
    GiftDef("crystal_ball", "Crystal Ball (Магический шар)", 1_300, 1.50, 900, "artifacts", "Артефакты и украшения"),
    GiftDef("mosque_moon", "Moon Pendant (Полумесяц)", 580, 4.00, 320, "artifacts", "Артефакты и украшения"),
    GiftDef("clover_green", "Clover Pin (Значок Клевер)", 420, 7.00, 190, "artifacts", "Артефакты и украшения"),
    GiftDef("pacifier_gold", "Hypno Lollipop (Золотая соска)", 340, 8.00, 150, "artifacts", "Артефакты и украшения"),
    GiftDef("skull_ghost", "Electric Skull (Призрачный череп)", 2_200, 1.10, 1_400, "mystic", "Мистика и Хэллоуин"),
    GiftDef("teddy_pumpkin", "Mad Pumpkin (Тыква Хэллоуин)", 1_150, 2.00, 700, "mystic", "Мистика и Хэллоуин"),
    GiftDef("broom_witch", "Flying Broom (Ведьмина метла)", 980, 2.20, 560, "mystic", "Мистика и Хэллоуин"),
    GiftDef("coffin", "Gravestone (Гробница)", 850, 2.50, 480, "mystic", "Мистика и Хэллоуин"),
    GiftDef("eye_evil", "Evil Eye (Глаз-оберег)", 680, 3.20, 380, "mystic", "Мистика и Хэллоуин"),
    GiftDef("briefcase", "Loot Bag (Дипломат)", 6_800, 0.40, 4_200, "festive", "Праздничные сувениры"),
    GiftDef("chocolate_box", "Berry Box (Коробка конфет)", 780, 2.80, 430, "festive", "Праздничные сувениры"),
    GiftDef("cupcake_bunny", "Bunny Muffin (Кекс-зайчик)", 690, 3.00, 370, "festive", "Праздничные сувениры"),
    GiftDef("fountain_pen", "Fine Pen (Золотое перо)", 650, 3.50, 350, "festive", "Праздничные сувениры"),
    GiftDef("candle", "Eternal Candle (Свеча)", 520, 4.20, 290, "festive", "Праздничные сувениры"),
    GiftDef("bday_calendar", "Desk Calendar (Календарь)", 510, 4.50, 280, "festive", "Праздничные сувениры"),
    GiftDef("bowtie", "Bow Tie (Бабочка)", 460, 5.00, 260, "festive", "Праздничные сувениры"),
    GiftDef("tg_rashguard", "Swag Bag (Рашгард)", 450, 5.20, 250, "festive", "Праздничные сувениры"),
    GiftDef("heart_cookie", "Cookie Heart (Пряник-сердце)", 430, 5.50, 240, "festive", "Праздничные сувениры"),
    GiftDef("easter_cake", "Homemade Cake (Кулич)", 400, 6.50, 210, "festive", "Праздничные сувениры"),
    GiftDef("peace_dove_stamp", "Dove of Peace (Марка мира)", 390, 6.80, 200, "festive", "Праздничные сувениры"),
    GiftDef("happy_bday_sign", "Star Notepad (Блокнот B-day)", 375, 7.20, 180, "festive", "Праздничные сувениры"),
    GiftDef("sneakers_black", "Fresh Socks (Кроссовки)", 360, 7.50, 170, "festive", "Праздничные сувениры"),
    GiftDef("coconut_drink", "Holiday Drink (Коктейль)", 350, 7.80, 160, "festive", "Праздничные сувениры"),
    GiftDef("egg_butterfly", "Easter Egg (Пасхальное яйцо)", 320, 8.20, 140, "festive", "Праздничные сувениры"),
    GiftDef("new_year_2025", "Big Year (Цифры 2025)", 310, 8.50, 130, "festive", "Праздничные сувениры"),
    GiftDef("candy_cane", "Candy Cane (Леденец)", 290, 8.80, 120, "festive", "Праздничные сувениры"),
    GiftDef("i_love_u_heart", "I Love You (Сердце)", 65, 10.00, 50, "festive", "Праздничные сувениры"),
    GiftDef("xmas_tree", "Christmas Tree (Ёлочка)", 65, 10.00, 50, "festive", "Праздничные сувениры"),
]

# Эксклюзивный акционный NFT: НЕ входит в список GIFTS (никогда не падает из кейсов и слова NFT)
SCARED_CAT_DEF = GiftDef("scared_cat", "Scared Cat (Уникальный кот)", SCARED_CAT_PROMO_PRICE, 0.0, 50_000, "animals", "Уникальные коллекционные")

GIFTS_BY_KEY = {g.key: g for g in GIFTS}
GIFTS_BY_KEY["scared_cat"] = SCARED_CAT_DEF
GIFTS_BY_KEY["ring_silver"] = GIFTS_BY_KEY["bonded_ring"]

MODEL_GROUPS = {
    "animals": "Животные и маскоты",
    "figures": "Фигурки и трофеи",
    "artifacts": "Артефакты и украшения",
    "mystic": "Мистика и Хэллоуин",
    "festive": "Праздничные сувениры",
}

PRICE_TIERS = {
    "low": ("До 500 ⭐", 0, 500),
    "mid": ("500 — 2,000 ⭐", 501, 2000),
    "high": ("2,000 — 15,000 ⭐", 2001, 15000),
    "ultra": ("От 15,000 ⭐", 15001, 10000000),
}

def get_gifts_filtered(filter_type: str, filter_key: str) -> List[GiftDef]:
    if filter_type == "model":
        if filter_key in MODEL_GROUPS:
            return [g for g in GIFTS if g.model_group == filter_key]
    elif filter_type == "gift":
        if filter_key in GIFTS_BY_KEY:
            return [GIFTS_BY_KEY[filter_key]]
    elif filter_type == "price":
        if filter_key in PRICE_TIERS:
            _, min_p, max_p = PRICE_TIERS[filter_key]
            return [g for g in GIFTS if min_p <= g.stars <= max_p]
    return GIFTS

def roll_gift_from_pool(pool: List[GiftDef], bonus_pct: float = 0.0) -> GiftDef:
    total_w = 0.0
    weights = []
    bonus_multiplier = 1.0 + (bonus_pct / 100.0)

    for g in pool:
        if g.stars >= 1000:
            w = g.chance * bonus_multiplier
        else:
            w = g.chance
        weights.append(w)
        total_w += w

    r = random.uniform(0, total_w)
    upto = 0.0
    for idx, g in enumerate(pool):
        upto += weights[idx]
        if upto >= r:
            return g
    return pool[-1]

def gift_image_path(key: str) -> Optional[Path]:
    for ext in [".webp", ".png", ".jpg", ".jpeg"]:
        p = IMAGES_DIR / f"{key}{ext}"
        if p.exists():
            return p
    if key == "trophy_cup":
        alt = IMAGES_DIR / "Algorithm Cup.webp"
        if alt.exists():
            return alt
    if key == "bonded_ring":
        alt = IMAGES_DIR / "ring_silver.webp"
        if alt.exists():
            return alt
    if key == "signet_ring":
        alt = IMAGES_DIR / "ring_signet_tg.webp"
        if alt.exists():
            return alt
    if key == "scared_cat":
        alt = IMAGES_DIR / "Scared Cat.webp"
        if alt.exists():
            return alt
    return None

# ---------------------------------------------------------------------------
# КАТАЛОГ УЛУЧШЕНИЙ PLUSH PEPE: 50 МОДЕЛЕЙ И 60 ФОНОВ (TELEGIFTER.RU)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PlushModelDef:
    name: str
    filename: str
    chance_pct: float
    price_mult: float

@dataclass(frozen=True)
class BackdropDef:
    key: str
    name: str
    palette: str
    center_hex: str
    edge_hex: str
    chance_pct: float
    price_mult: float
    rarity_label: str

PLUSHPEPE_MODELS: list[PlushModelDef] = [
    PlushModelDef("Amalgam", "Amalgam.webp", 2.0, 1.18),
    PlushModelDef("Aqua Plush", "Aqua Plush.webp", 3.0, 1.06),
    PlushModelDef("Barcelona", "Barcelona.webp", 2.0, 1.15),
    PlushModelDef("Bavaria", "Bavaria.webp", 2.0, 1.15),
    PlushModelDef("Birmingham", "Birmingham.webp", 2.0, 1.14),
    PlushModelDef("Christmas", "Christmas.webp", 2.0, 1.15),
    PlushModelDef("Cold Heart", "Cold Heart.webp", 3.0, 1.08),
    PlushModelDef("Cozy Galaxy", "Cozy Galaxy.webp", 1.0, 1.28),
    PlushModelDef("Donatello", "Donatello.webp", 1.0, 1.25),
    PlushModelDef("Eggplant", "Eggplant.webp", 3.0, 1.05),
    PlushModelDef("Emerald Plush", "Emerald Plush.webp", 1.0, 1.26),
    PlushModelDef("Emo Boi", "Emo Boi.webp", 2.0, 1.16),
    PlushModelDef("Fifty Shades", "Fifty Shades.webp", 1.0, 1.30),
    PlushModelDef("Frozen", "Frozen.webp", 2.0, 1.16),
    PlushModelDef("Gucci Leap", "Gucci Leap.webp", 1.0, 1.28),
    PlushModelDef("Gummy Frog", "Gummy Frog.webp", 3.0, 1.05),
    PlushModelDef("Hothead", "Hothead.webp", 3.0, 1.07),
    PlushModelDef("Hue Jester", "Hue Jester.webp", 3.0, 1.07),
    PlushModelDef("Kung Fu Pepe", "Kung Fu Pepe.webp", 2.0, 1.16),
    PlushModelDef("Leonardo", "Leonardo.webp", 1.0, 1.25),
    PlushModelDef("Louis Vuittoad", "Louis Vuittoad.webp", 1.0, 1.30),
    PlushModelDef("Magnate", "Magnate.webp", 1.0, 1.27),
    PlushModelDef("Marble", "Marble.webp", 2.0, 1.16),
    PlushModelDef("Midas Pepe", "Midas Pepe.webp", 1.0, 1.32),
    PlushModelDef("Milano", "Milano.webp", 2.0, 1.14),
    PlushModelDef("Ninja Mike", "Ninja Mike.webp", 1.0, 1.25),
    PlushModelDef("Pepe La Rana", "Pepe La Rana.webp", 2.0, 1.12),
    PlushModelDef("Pepemint", "Pepemint.webp", 3.0, 1.06),
    PlushModelDef("Pink Galaxy", "Pink Galaxy.webp", 2.0, 1.18),
    PlushModelDef("Pink Latex", "Pink Latex.webp", 2.0, 1.15),
    PlushModelDef("Poison Dart", "Poison Dart.webp", 3.0, 1.08),
    PlushModelDef("Polka Dots", "Polka Dots.webp", 3.0, 1.05),
    PlushModelDef("Princess", "Princess.webp", 2.0, 1.14),
    PlushModelDef("Pumpkin", "Pumpkin.webp", 3.0, 1.06),
    PlushModelDef("Puppy Pug", "Puppy Pug.webp", 1.0, 1.24),
    PlushModelDef("Raphael", "Raphael.webp", 1.0, 1.25),
    PlushModelDef("Red Menace", "Red Menace.webp", 3.0, 1.08),
    PlushModelDef("Red Pepple", "Red Pepple.webp", 2.0, 1.13),
    PlushModelDef("Santa Pepe", "Santa Pepe.webp", 2.0, 1.14),
    PlushModelDef("Sketchy", "Sketchy.webp", 2.0, 1.17),
    PlushModelDef("Spectrum", "Spectrum.webp", 3.0, 1.08),
    PlushModelDef("Steel Frog", "Steel Frog.webp", 1.0, 1.28),
    PlushModelDef("Stripes", "Stripes.webp", 2.0, 1.12),
    PlushModelDef("Sunset", "Sunset.webp", 2.0, 1.13),
    PlushModelDef("Toading...", "Toading....webp", 1.0, 1.26),
    PlushModelDef("Tropical", "Tropical.webp", 3.0, 1.05),
    PlushModelDef("Two Face", "Two Face.webp", 2.0, 1.18),
    PlushModelDef("X-Ray", "X-Ray.webp", 2.0, 1.20),
    PlushModelDef("Yellow Hug", "Yellow Hug.webp", 3.0, 1.05),
    PlushModelDef("Yellow Purp", "Yellow Purp.webp", 2.0, 1.12),
]

PLUSHPEPE_MODELS_BY_NAME = {m.name: m for m in PLUSHPEPE_MODELS}

# 61 модель для Heart Locket (images/heart_locket_models/*.webp)
HEART_LOCKET_MODELS: list[PlushModelDef] = [
    PlushModelDef("Acorn Hunter", "Acorn Hunter.webp", 2.0, 1.15),
    PlushModelDef("Angelic Pink", "Angelic Pink.webp", 2.0, 1.18),
    PlushModelDef("Azure Gem", "Azure Gem.webp", 1.5, 1.24),
    PlushModelDef("Black Hole", "Black Hole.webp", 1.0, 1.35),
    PlushModelDef("Casino Bugs", "Casino Bugs.webp", 2.0, 1.15),
    PlushModelDef("Cirque", "Cirque.webp", 2.0, 1.14),
    PlushModelDef("Comic Book", "Comic Book.webp", 2.0, 1.16),
    PlushModelDef("Compass", "Compass.webp", 2.5, 1.10),
    PlushModelDef("Disco", "Disco.webp", 2.0, 1.16),
    PlushModelDef("Emocore", "Emocore.webp", 1.5, 1.22),
    PlushModelDef("Fairy Dust", "Fairy Dust.webp", 1.5, 1.24),
    PlushModelDef("Gem Shards", "Gem Shards.webp", 1.5, 1.23),
    PlushModelDef("Glam Furry", "Glam Furry.webp", 2.0, 1.14),
    PlushModelDef("Golden", "Golden.webp", 1.0, 1.32),
    PlushModelDef("Great Wave", "Great Wave.webp", 1.5, 1.25),
    PlushModelDef("Heart Locket", "Heart Locket.webp", 3.0, 1.06),
    PlushModelDef("Heartwood", "Heartwood.webp", 2.5, 1.08),
    PlushModelDef("Hell Rise", "Hell Rise.webp", 1.5, 1.24),
    PlushModelDef("Jupiter", "Jupiter.webp", 2.0, 1.14),
    PlushModelDef("Karaoke Bar", "Karaoke Bar.webp", 2.0, 1.15),
    PlushModelDef("Koi Pond", "Koi Pond.webp", 1.5, 1.22),
    PlushModelDef("Lady Bug", "Lady Bug.webp", 2.5, 1.09),
    PlushModelDef("Love Ring", "Love Ring.webp", 2.0, 1.16),
    PlushModelDef("Luna", "Luna.webp", 1.5, 1.22),
    PlushModelDef("Lunar Grail", "Lunar Grail.webp", 1.0, 1.30),
    PlushModelDef("Mars", "Mars.webp", 2.0, 1.15),
    PlushModelDef("Matryoshka", "Matryoshka.webp", 2.0, 1.15),
    PlushModelDef("Mecha Love", "Mecha Love.webp", 1.5, 1.24),
    PlushModelDef("Mercury", "Mercury.webp", 2.0, 1.14),
    PlushModelDef("Mirror", "Mirror.webp", 1.5, 1.22),
    PlushModelDef("Neptune", "Neptune.webp", 2.0, 1.16),
    PlushModelDef("Nightclub", "Nightclub.webp", 1.5, 1.22),
    PlushModelDef("Ocean Star", "Ocean Star.webp", 2.0, 1.18),
    PlushModelDef("Pepperoni", "Pepperoni.webp", 3.0, 1.05),
    PlushModelDef("Pluto", "Pluto.webp", 2.0, 1.14),
    PlushModelDef("Queen Bee", "Queen Bee.webp", 1.5, 1.22),
    PlushModelDef("Reactor", "Reactor.webp", 1.5, 1.25),
    PlushModelDef("Rebellion", "Rebellion.webp", 1.5, 1.23),
    PlushModelDef("Royal Flush", "Royal Flush.webp", 1.0, 1.30),
    PlushModelDef("Royal Heart", "Royal Heart.webp", 1.5, 1.25),
    PlushModelDef("Sakura", "Sakura.webp", 1.5, 1.26),
    PlushModelDef("Sanctuary", "Sanctuary.webp", 2.0, 1.16),
    PlushModelDef("Satoru", "Satoru.webp", 1.0, 1.34),
    PlushModelDef("Saturn", "Saturn.webp", 2.0, 1.15),
    PlushModelDef("Shaman", "Shaman.webp", 2.0, 1.16),
    PlushModelDef("Shield of Sun", "Shield of Sun.webp", 1.5, 1.24),
    PlushModelDef("Soulkeeper", "Soulkeeper.webp", 1.0, 1.32),
    PlushModelDef("Spider Web", "Spider Web.webp", 2.0, 1.15),
    PlushModelDef("Stone Flower", "Stone Flower.webp", 2.0, 1.16),
    PlushModelDef("Synthwave", "Synthwave.webp", 1.5, 1.24),
    PlushModelDef("Telegram", "Telegram.webp", 1.0, 1.32),
    PlushModelDef("Toy Joy", "Toy Joy.webp", 2.5, 1.08),
    PlushModelDef("Trapped Heart", "Trapped Heart.webp", 1.5, 1.24),
    PlushModelDef("Turtles", "Turtles.webp", 2.0, 1.15),
    PlushModelDef("Tuxedo Mask", "Tuxedo Mask.webp", 1.5, 1.25),
    PlushModelDef("Uranus", "Uranus.webp", 2.0, 1.16),
    PlushModelDef("Valentine", "Valentine.webp", 2.5, 1.10),
    PlushModelDef("Vampire", "Vampire.webp", 1.5, 1.23),
    PlushModelDef("Venus", "Venus.webp", 2.0, 1.15),
    PlushModelDef("Waffle Maker", "Waffle Maker.webp", 3.0, 1.06),
    PlushModelDef("White Wolf", "White Wolf.webp", 1.0, 1.32),
]

HEART_LOCKET_MODELS_BY_NAME = {m.name: m for m in HEART_LOCKET_MODELS}

# 55 моделей для Durov's Cap (images/durov_cap_models/*.webp)
DUROV_CAP_MODELS: list[PlushModelDef] = [
    PlushModelDef("Apple Slice", "Apple Slice.webp", 2.0, 1.15),
    PlushModelDef("Artwork", "Artwork.webp", 1.5, 1.22),
    PlushModelDef("Ashen", "Ashen.webp", 2.0, 1.15),
    PlushModelDef("Asterix", "Asterix.webp", 2.0, 1.16),
    PlushModelDef("Aurora", "Aurora.webp", 1.5, 1.24),
    PlushModelDef("Autumn", "Autumn.webp", 2.5, 1.10),
    PlushModelDef("Bluebird", "Bluebird.webp", 2.5, 1.10),
    PlushModelDef("Bog Moss", "Bog Moss.webp", 2.5, 1.08),
    PlushModelDef("Bordeaux", "Bordeaux.webp", 2.0, 1.15),
    PlushModelDef("Candy Shade", "Candy Shade.webp", 2.0, 1.16),
    PlushModelDef("Captain", "Captain.webp", 1.5, 1.22),
    PlushModelDef("Cartoon", "Cartoon.webp", 2.0, 1.16),
    PlushModelDef("Chicago Bulls", "Chicago Bulls.webp", 1.5, 1.24),
    PlushModelDef("Classic", "Classic.webp", 3.0, 1.06),
    PlushModelDef("Corkwood", "Corkwood.webp", 2.5, 1.08),
    PlushModelDef("Cotton Candy", "Cotton Candy.webp", 2.0, 1.16),
    PlushModelDef("Creamsicle", "Creamsicle.webp", 2.5, 1.09),
    PlushModelDef("Dipper", "Dipper.webp", 1.5, 1.22),
    PlushModelDef("Duck Tales", "Duck Tales.webp", 1.5, 1.24),
    PlushModelDef("Duskwave", "Duskwave.webp", 2.0, 1.16),
    PlushModelDef("Falcon", "Falcon.webp", 2.0, 1.15),
    PlushModelDef("Freshwave", "Freshwave.webp", 2.5, 1.09),
    PlushModelDef("Frosted Brew", "Frosted Brew.webp", 2.5, 1.08),
    PlushModelDef("Frosthorn", "Frosthorn.webp", 2.0, 1.15),
    PlushModelDef("Fun Time", "Fun Time.webp", 2.0, 1.15),
    PlushModelDef("Goldrose", "Goldrose.webp", 1.0, 1.32),
    PlushModelDef("Honey Bee", "Honey Bee.webp", 2.0, 1.14),
    PlushModelDef("Ivory", "Ivory.webp", 2.0, 1.16),
    PlushModelDef("Jade", "Jade.webp", 2.0, 1.15),
    PlushModelDef("Jetspin", "Jetspin.webp", 1.5, 1.24),
    PlushModelDef("Krueger", "Krueger.webp", 1.5, 1.25),
    PlushModelDef("Macintosh", "Macintosh.webp", 1.0, 1.30),
    PlushModelDef("Mossy", "Mossy.webp", 2.5, 1.08),
    PlushModelDef("Negative", "Negative.webp", 1.0, 1.32),
    PlushModelDef("Neon", "Neon.webp", 1.5, 1.25),
    PlushModelDef("Night Ivy", "Night Ivy.webp", 2.0, 1.16),
    PlushModelDef("Nightshade", "Nightshade.webp", 1.5, 1.23),
    PlushModelDef("Patriot", "Patriot.webp", 2.0, 1.15),
    PlushModelDef("Pink Pop", "Pink Pop.webp", 2.5, 1.10),
    PlushModelDef("Pinkie Cap", "Pinkie Cap.webp", 2.0, 1.15),
    PlushModelDef("Pokemon", "Pokemon.webp", 1.0, 1.32),
    PlushModelDef("RGB Glitch", "RGB Glitch.webp", 1.0, 1.35),
    PlushModelDef("Redrum", "Redrum.webp", 1.5, 1.25),
    PlushModelDef("Sea Sunset", "Sea Sunset.webp", 2.0, 1.15),
    PlushModelDef("Seabreeze", "Seabreeze.webp", 2.5, 1.08),
    PlushModelDef("Sepium", "Sepium.webp", 2.5, 1.08),
    PlushModelDef("Shadeux", "Shadeux.webp", 2.0, 1.16),
    PlushModelDef("Shadow", "Shadow.webp", 1.0, 1.30),
    PlushModelDef("Sky High", "Sky High.webp", 2.5, 1.09),
    PlushModelDef("Snowfall", "Snowfall.webp", 2.0, 1.16),
    PlushModelDef("Sunrise", "Sunrise.webp", 2.0, 1.14),
    PlushModelDef("Toxic Guy", "Toxic Guy.webp", 1.5, 1.24),
    PlushModelDef("Tron", "Tron.webp", 1.0, 1.32),
    PlushModelDef("Villager", "Villager.webp", 2.0, 1.15),
    PlushModelDef("Voltage", "Voltage.webp", 1.5, 1.24),
]

DUROV_CAP_MODELS_BY_NAME = {m.name: m for m in DUROV_CAP_MODELS}

# 4 модели для Algorithm Cup (images/cup_models/*)
ALGORITHM_CUP_MODELS: list[PlushModelDef] = [
    PlushModelDef("Bronze", "Bronze.webp", 45.0, 1.15),
    PlushModelDef("Silver", "Silver.webp", 30.0, 1.25),
    PlushModelDef("Gold", "Gold.webp", 20.0, 1.40),
    PlushModelDef("Cyber Glitch", "1794832273556.jpg", 5.0, 1.65),
]

ALGORITHM_CUP_MODELS_BY_NAME = {m.name: m for m in ALGORITHM_CUP_MODELS}

# 50 моделей для Bonded Ring (images/bonded_ring_models/*.webp)
BONDED_RING_MODELS: list[PlushModelDef] = [
    PlushModelDef("Anaconda", "Anaconda.webp", 2.0, 1.16),
    PlushModelDef("Asteroid", "Asteroid.webp", 2.0, 1.15),
    PlushModelDef("Astro Silver", "Astro Silver.webp", 1.5, 1.24),
    PlushModelDef("Atomic Core", "Atomic Core.webp", 1.5, 1.25),
    PlushModelDef("Black Hole Ring", "Black Hole (1).webp", 1.0, 1.35),
    PlushModelDef("Bloody Mary", "Bloody Mary.webp", 2.0, 1.16),
    PlushModelDef("Cat Bed", "Cat Bed.webp", 2.5, 1.10),
    PlushModelDef("Cheese", "Cheese.webp", 3.0, 1.06),
    PlushModelDef("Dalmatian", "Dalmatian.webp", 2.5, 1.10),
    PlushModelDef("Duckling", "Duckling.webp", 2.5, 1.09),
    PlushModelDef("Duo Vision", "Duo Vision.webp", 2.0, 1.16),
    PlushModelDef("Eclipse", "Eclipse.webp", 1.5, 1.25),
    PlushModelDef("Fireball", "Fireball.webp", 2.0, 1.18),
    PlushModelDef("Froge Ring", "Froge Ring.webp", 2.0, 1.18),
    PlushModelDef("Frostband", "Frostband.webp", 2.0, 1.16),
    PlushModelDef("Golden Star", "Golden Star.webp", 1.0, 1.32),
    PlushModelDef("Goldsmith", "Goldsmith.webp", 1.5, 1.26),
    PlushModelDef("Hamster Wheel", "Hamster Wheel.webp", 2.5, 1.09),
    PlushModelDef("Highway", "Highway.webp", 2.5, 1.09),
    PlushModelDef("Hot Wheel", "Hot Wheel.webp", 2.0, 1.15),
    PlushModelDef("Hourglass", "Hourglass.webp", 2.0, 1.16),
    PlushModelDef("Ironwood", "Ironwood.webp", 2.5, 1.10),
    PlushModelDef("Kraken's Grip", "Kraken\u00e2\u0080\u0099s Grip.webp", 1.5, 1.24),
    PlushModelDef("Leopard", "Leopard.webp", 2.0, 1.15),
    PlushModelDef("Lime Factory", "Lime Factory.webp", 2.5, 1.09),
    PlushModelDef("Line Art", "Line Art.webp", 2.0, 1.16),
    PlushModelDef("Love Whisper", "Love Whisper.webp", 2.0, 1.17),
    PlushModelDef("Magic Runes", "Magic Runes.webp", 1.5, 1.24),
    PlushModelDef("Metal Forever", "Metal Forever.webp", 2.0, 1.16),
    PlushModelDef("Miami Art", "Miami Art.webp", 2.0, 1.17),
    PlushModelDef("Moon Dust", "Moon Dust.webp", 1.5, 1.22),
    PlushModelDef("Mouse Wheel", "Mouse Wheel.webp", 2.5, 1.08),
    PlushModelDef("Neo Matrix", "Neo Matrix.webp", 1.0, 1.32),
    PlushModelDef("Neo Tribe", "Neo Tribe.webp", 2.0, 1.15),
    PlushModelDef("Neon Pulse", "Neon Pulse.webp", 1.5, 1.25),
    PlushModelDef("Pixel Loot", "Pixel Loot.webp", 2.0, 1.16),
    PlushModelDef("Rainbow Halo", "Rainbow Halo.webp", 1.0, 1.34),
    PlushModelDef("Rainbow Ring", "Rainbow.webp", 1.5, 1.26),
    PlushModelDef("Ring of Roots", "Ring of Roots.webp", 2.5, 1.10),
    PlushModelDef("Runewood", "Runewood.webp", 2.5, 1.10),
    PlushModelDef("Soap Bubbles", "Soap Bubbles.webp", 2.5, 1.10),
    PlushModelDef("Solid Magma", "Solid Magma.webp", 1.5, 1.24),
    PlushModelDef("Space Inside", "Space Inside.webp", 1.5, 1.24),
    PlushModelDef("Spatial Grid", "Spatial Grid.webp", 2.0, 1.16),
    PlushModelDef("Spectrum Ring", "Spectrum (1).webp", 1.5, 1.22),
    PlushModelDef("Stratosphere", "Stratosphere.webp", 1.5, 1.23),
    PlushModelDef("Thunder Bolt", "Thunder Bolt.webp", 1.5, 1.24),
    PlushModelDef("Tiger Amulet", "Tiger Amulet.webp", 2.0, 1.16),
    PlushModelDef("Yin Yang", "Yin Yang.webp", 1.0, 1.30),
    PlushModelDef("Zebra", "Zebra.webp", 2.5, 1.10),
]

BONDED_RING_MODELS_BY_NAME = {m.name: m for m in BONDED_RING_MODELS}

# 61 фон: Радужный (Мифический x100, реже Чёрного: 0.05%) + 60 официальных палитр (суммарно 100.00%).
PLUSHPEPE_BACKDROPS: list[BackdropDef] = [
    # Мифический радужный фон (0.05%, x100 к цене)
    BackdropDef("rainbow", "Rainbow", "Переливающийся радужный", "#FF4D8D", "#6366F1", 0.05, 100.0, "Мифический"),

    # Ультра-редкие чёрные и серые (0.15% - 0.50%)
    BackdropDef("black", "Black", "Глубокий чёрный", "#363738", "#0E0F0F", 0.15, 10.5, "Ультра-редкий"),
    BackdropDef("onyx_black", "Onyx Black", "Ониксовый чёрный", "#4D5254", "#313638", 0.20, 9.5, "Ультра-редкий"),
    BackdropDef("battleship_grey", "Battleship Grey", "Стальной серый", "#8C8C85", "#6C6C66", 0.25, 8.8, "Ультра-редкий"),
    BackdropDef("steel_grey", "Steel Grey", "Холодный серый", "#97A2AC", "#63727C", 0.30, 8.4, "Ультра-редкий"),
    BackdropDef("pure_gold", "Pure Gold", "Чистое золото", "#CCAB41", "#987B32", 0.35, 8.2, "Ультра-редкий"),
    BackdropDef("roman_silver", "Roman Silver", "Римское серебро", "#A3A8B5", "#7C808A", 0.40, 7.6, "Ультра-редкий"),
    BackdropDef("platinum", "Platinum", "Платиновый серый", "#B2AEA7", "#88847E", 0.45, 7.2, "Ультра-редкий"),
    BackdropDef("ivory_white", "Ivory White", "Слоновая кость", "#BAB6B1", "#A19D97", 0.50, 6.8, "Ультра-редкий"),

    # Редкие тёмные и благородные (0.60% - 1.15%)
    BackdropDef("satin_gold", "Satin Gold", "Сатиновое золото", "#BF9B47", "#8D7739", 0.60, 6.2, "Редкий"),
    BackdropDef("midnight_blue", "Midnight Blue", "Полуночный синий", "#5C6985", "#354057", 0.65, 5.8, "Редкий"),
    BackdropDef("indigo_dye", "Indigo Dye", "Глубокий индиго", "#537991", "#416479", 0.70, 5.5, "Редкий"),
    BackdropDef("burgundy", "Burgundy", "Благородный бордо", "#A35E66", "#6D414A", 0.75, 5.2, "Редкий"),
    BackdropDef("chocolate", "Chocolate", "Шоколадный", "#A46E58", "#74443B", 0.80, 5.0, "Редкий"),
    BackdropDef("chestnut", "Chestnut", "Каштановый", "#BE6F54", "#994838", 0.85, 4.8, "Редкий"),
    BackdropDef("rosewood", "Rosewood", "Палисандр", "#B77A77", "#814C52", 0.90, 4.6, "Редкий"),
    BackdropDef("cappuccino", "Cappuccino", "Капучино", "#B1907E", "#7C6356", 0.95, 4.4, "Редкий"),
    BackdropDef("silver_blue", "Silver Blue", "Серебристо-синий", "#80A4B8", "#607C91", 1.00, 4.3, "Редкий"),
    BackdropDef("moonstone", "Moonstone", "Лунный камень", "#7EB1B4", "#588390", 1.05, 4.2, "Редкий"),
    BackdropDef("desert_sand", "Desert Sand", "Песчаный", "#B39F82", "#7E735B", 1.10, 4.0, "Редкий"),
    BackdropDef("pine_green", "Pine Green", "Хвойный зелёный", "#6BA97C", "#3E7970", 1.15, 3.9, "Редкий"),

    # Необычные насыщенные (1.25% - 1.85%)
    BackdropDef("dark_lilac", "Dark Lilac", "Тёмно-сиреневый", "#B17DA5", "#8C577A", 1.25, 3.8, "Необычный"),
    BackdropDef("english_violet", "English Violet", "Английский фиолет", "#B186BB", "#875A91", 1.30, 3.7, "Необычный"),
    BackdropDef("purple", "Purple", "Пурпурный", "#AE6CAE", "#844784", 1.35, 3.6, "Необычный"),
    BackdropDef("copper", "Copper", "Медный", "#D08656", "#9D6531", 1.40, 3.5, "Необычный"),
    BackdropDef("hunter_green", "Hunter Green", "Лесной зелёный", "#8FAE78", "#4B825B", 1.45, 3.4, "Необычный"),
    BackdropDef("pistachio", "Pistachio", "Фисташковый", "#97B07C", "#5C814C", 1.50, 3.3, "Необычный"),
    BackdropDef("khaki_green", "Khaki Green", "Хаки", "#ADB070", "#6B7D54", 1.50, 3.3, "Необычный"),
    BackdropDef("light_olive", "Light Olive", "Светло-оливковый", "#C2AF64", "#887E45", 1.55, 3.2, "Необычный"),
    BackdropDef("french_blue", "French Blue", "Французский синий", "#5C9BC4", "#37739A", 1.60, 3.1, "Необычный"),
    BackdropDef("cobalt_blue", "Cobalt Blue", "Кобальтовый синий", "#6088CF", "#5162B8", 1.65, 3.1, "Необычный"),
    BackdropDef("sapphire", "Sapphire", "Сапфировый", "#58A3C8", "#5379C2", 1.70, 3.0, "Необычный"),
    BackdropDef("navy_blue", "Navy Blue", "Тёмно-морской", "#6C9EDD", "#5C6EC9", 1.70, 3.0, "Необычный"),
    BackdropDef("grape", "Grape", "Виноградный", "#9D74C1", "#794DA0", 1.75, 2.9, "Необычный"),
    BackdropDef("mystic_pearl", "Mystic Pearl", "Мистический жемчуг", "#D08B6D", "#B05770", 1.80, 2.9, "Необычный"),
    BackdropDef("pacific_cyan", "Pacific Cyan", "Тихоокеанский циан", "#5ABEA6", "#3D95BA", 1.80, 2.8, "Необычный"),
    BackdropDef("turquoise", "Turquoise", "Бирюзовый", "#5EC0B8", "#3D928E", 1.85, 2.8, "Необычный"),

    # Обычные яркие и неоновые (2.15% - 2.85%)
    BackdropDef("aquamarine", "Aquamarine", "Яркий аквамарин", "#60B195", "#46ABB4", 2.15, 2.7, "Обычный"),
    BackdropDef("jade_green", "Jade Green", "Яркий нефритовый", "#55C49C", "#3B9977", 2.20, 2.7, "Обычный"),
    BackdropDef("emerald", "Emerald", "Яркий изумрудный", "#78C585", "#42A171", 2.25, 2.6, "Обычный"),
    BackdropDef("pacific_green", "Pacific Green", "Тихоокеанский зелёный", "#6FC793", "#3B9C84", 2.30, 2.6, "Обычный"),
    BackdropDef("malachite", "Malachite", "Малахитовый", "#95B457", "#3D9755", 2.35, 2.5, "Обычный"),
    BackdropDef("shamrock_green", "Shamrock Green", "Изумрудный трилистник", "#8AB163", "#559345", 2.40, 2.5, "Обычный"),
    BackdropDef("mint_green", "Mint Green", "Яркая мята", "#7ECB82", "#459E5A", 2.45, 2.5, "Обычный"),
    BackdropDef("lemongrass", "Lemongrass", "Яркий лемонграсс", "#AEB85A", "#559345", 2.50, 2.4, "Обычный"),
    BackdropDef("azure_blue", "Azure Blue", "Яркий лазурный", "#5DB1CB", "#448BAB", 2.50, 2.4, "Обычный"),
    BackdropDef("sky_blue", "Sky Blue", "Небесно-голубой", "#58B4C8", "#538BC2", 2.55, 2.4, "Обычный"),
    BackdropDef("neon_blue", "Neon Blue", "Неоновый синий", "#7596F9", "#6862E4", 2.55, 2.4, "Обычный"),
    BackdropDef("cyberpunk", "Cyberpunk", "Неоновый киберпанк", "#858FF3", "#865FD3", 2.60, 2.3, "Обычный"),
    BackdropDef("electric_indigo", "Electric Indigo", "Электрический индиго", "#A980F3", "#5B62D8", 2.60, 2.3, "Обычный"),
    BackdropDef("lavender", "Lavender", "Яркий лавандовый", "#B789E4", "#8A5ABC", 2.65, 2.3, "Обычный"),
    BackdropDef("electric_purple", "Electric Purple", "Электрический фиолет", "#CA70C6", "#9662D4", 2.65, 2.3, "Обычный"),
    BackdropDef("fandango", "Fandango", "Яркий фанданго", "#E28AB6", "#A4588B", 2.70, 2.2, "Обычный"),
    BackdropDef("raspberry", "Raspberry", "Яркий малиновый", "#E07B85", "#B65980", 2.70, 2.2, "Обычный"),
    BackdropDef("strawberry", "Strawberry", "Клубничный", "#DD8E6F", "#B75A60", 2.75, 2.2, "Обычный"),
    BackdropDef("coral_red", "Coral Red", "Яркий коралловый", "#DA896B", "#C4654F", 2.75, 2.2, "Обычный"),
    BackdropDef("persimmon", "Persimmon", "Яркая хурма", "#E7A75A", "#C5675F", 2.80, 2.1, "Обычный"),
    BackdropDef("carrot_juice", "Carrot Juice", "Морковный фреш", "#DB9867", "#C76F4F", 2.80, 2.1, "Обычный"),
    BackdropDef("orange", "Orange", "Яркий апельсиновый", "#D19A3A", "#C06F47", 2.85, 2.1, "Обычный"),
    BackdropDef("caramel", "Caramel", "Карамельный", "#D09932", "#B77431", 2.85, 2.1, "Обычный"),
    BackdropDef("amber", "Amber", "Яркий янтарный", "#DAB345", "#B1802A", 2.80, 2.1, "Обычный"),
]

BACKDROPS_BY_KEY = {b.key: b for b in PLUSHPEPE_BACKDROPS}

# Цветовые семейства моделей и фонов для системы МОНОХРОМ
MODEL_COLOR_FAMILIES: dict[str, str] = {
    "Aqua Plush": "blue",
    "Cold Heart": "blue",
    "Frozen": "blue",
    "Leonardo": "blue",
    "Toading...": "blue",
    "Hothead": "red",
    "Red Menace": "red",
    "Red Pepple": "red",
    "Raphael": "red",
    "Santa Pepe": "red",
    "Christmas": "red",
    "Emerald Plush": "green",
    "Gummy Frog": "green",
    "Pepe La Rana": "green",
    "Pepemint": "green",
    "Poison Dart": "green",
    "Tropical": "green",
    "Kung Fu Pepe": "green",
    "Eggplant": "purple",
    "Donatello": "purple",
    "Cozy Galaxy": "purple",
    "Pink Galaxy": "pink",
    "Pink Latex": "pink",
    "Princess": "pink",
    "Midas Pepe": "gold",
    "Yellow Hug": "gold",
    "Puppy Pug": "gold",
    "Pumpkin": "orange",
    "Sunset": "orange",
    "Ninja Mike": "orange",
    "Emo Boi": "dark",
    "Fifty Shades": "dark",
    "Steel Frog": "dark",
    "X-Ray": "dark",
    "Sketchy": "white",
    "Marble": "white",
    # Модели Heart Locket для системы МОНОХРОМ
    "Azure Gem": "blue",
    "Great Wave": "blue",
    "Neptune": "blue",
    "Ocean Star": "blue",
    "Telegram": "blue",
    "Uranus": "blue",
    "Hell Rise": "red",
    "Lady Bug": "red",
    "Mars": "red",
    "Royal Heart": "red",
    "Trapped Heart": "red",
    "Valentine": "red",
    "Reactor": "green",
    "Stone Flower": "green",
    "Turtles": "green",
    "Disco": "purple",
    "Fairy Dust": "purple",
    "Nightclub": "purple",
    "Satoru": "purple",
    "Synthwave": "purple",
    "Venus": "purple",
    "Angelic Pink": "pink",
    "Glam Furry": "pink",
    "Love Ring": "pink",
    "Sakura": "pink",
    "Golden": "gold",
    "Lunar Grail": "gold",
    "Queen Bee": "gold",
    "Saturn": "gold",
    "Shield of Sun": "gold",
    "Acorn Hunter": "orange",
    "Compass": "orange",
    "Heartwood": "orange",
    "Jupiter": "orange",
    "Pepperoni": "orange",
    "Waffle Maker": "orange",
    "Black Hole": "dark",
    "Emocore": "dark",
    "Pluto": "dark",
    "Rebellion": "dark",
    "Soulkeeper": "dark",
    "Spider Web": "dark",
    "Tuxedo Mask": "dark",
    "Vampire": "dark",
    "Luna": "white",
    "Mirror": "white",
    "White Wolf": "white",
    # Модели Durov's Cap для системы МОНОХРОМ
    "Bluebird": "blue",
    "Captain": "blue",
    "Cartoon": "blue",
    "Dipper": "blue",
    "Freshwave": "blue",
    "Patriot": "blue",
    "Seabreeze": "blue",
    "Sky High": "blue",
    "Tron": "blue",
    "Bordeaux": "red",
    "Chicago Bulls": "red",
    "Krueger": "red",
    "Pokemon": "red",
    "Redrum": "red",
    "Apple Slice": "green",
    "Aurora": "green",
    "Bog Moss": "green",
    "Jade": "green",
    "Mossy": "green",
    "Night Ivy": "green",
    "Toxic Guy": "green",
    "Artwork": "purple",
    "Duskwave": "purple",
    "Fun Time": "purple",
    "Neon": "purple",
    "Nightshade": "purple",
    "RGB Glitch": "purple",
    "Candy Shade": "pink",
    "Cotton Candy": "pink",
    "Pink Pop": "pink",
    "Pinkie Cap": "pink",
    "Asterix": "gold",
    "Duck Tales": "gold",
    "Frosted Brew": "gold",
    "Goldrose": "gold",
    "Honey Bee": "gold",
    "Voltage": "gold",
    "Autumn": "orange",
    "Corkwood": "orange",
    "Creamsicle": "orange",
    "Sea Sunset": "orange",
    "Sepium": "orange",
    "Sunrise": "orange",
    "Villager": "orange",
    "Ashen": "dark",
    "Classic": "dark",
    "Falcon": "dark",
    "Jetspin": "dark",
    "Negative": "dark",
    "Shadeux": "dark",
    "Shadow": "dark",
    "Frosthorn": "white",
    "Ivory": "white",
    "Macintosh": "white",
    "Snowfall": "white",
    # Модели Algorithm Cup для системы МОНОХРОМ
    "Bronze": "orange",
    "Silver": "blue",
    "Gold": "gold",
    "Cyber Glitch": "purple",
    # Модели Bonded Ring для системы МОНОХРОМ
    "Anaconda": "green",
    "Asteroid": "dark",
    "Astro Silver": "white",
    "Atomic Core": "blue",
    "Black Hole Ring": "dark",
    "Bloody Mary": "red",
    "Cat Bed": "orange",
    "Cheese": "gold",
    "Dalmatian": "white",
    "Duckling": "gold",
    "Duo Vision": "purple",
    "Eclipse": "dark",
    "Fireball": "orange",
    "Froge Ring": "green",
    "Frostband": "blue",
    "Golden Star": "gold",
    "Goldsmith": "gold",
    "Hamster Wheel": "orange",
    "Highway": "dark",
    "Hot Wheel": "red",
    "Hourglass": "gold",
    "Ironwood": "orange",
    "Kraken's Grip": "blue",
    "Leopard": "gold",
    "Lime Factory": "green",
    "Line Art": "white",
    "Love Whisper": "pink",
    "Magic Runes": "purple",
    "Metal Forever": "dark",
    "Miami Art": "pink",
    "Moon Dust": "white",
    "Mouse Wheel": "white",
    "Neo Matrix": "green",
    "Neo Tribe": "orange",
    "Neon Pulse": "purple",
    "Pixel Loot": "purple",
    "Rainbow Halo": "pink",
    "Rainbow Ring": "blue",
    "Ring of Roots": "green",
    "Runewood": "green",
    "Soap Bubbles": "blue",
    "Solid Magma": "red",
    "Space Inside": "purple",
    "Spatial Grid": "blue",
    "Spectrum Ring": "pink",
    "Stratosphere": "blue",
    "Thunder Bolt": "gold",
    "Tiger Amulet": "orange",
    "Yin Yang": "dark",
    "Zebra": "white",
}

BACKDROP_COLOR_FAMILIES: dict[str, str] = {
    "black": "dark",
    "onyx_black": "dark",
    "battleship_grey": "dark",
    "steel_grey": "dark",
    "roman_silver": "dark",
    "platinum": "dark",
    "ivory_white": "white",
    "pure_gold": "gold",
    "satin_gold": "gold",
    "desert_sand": "gold",
    "amber": "gold",
    "caramel": "gold",
    "copper": "orange",
    "persimmon": "orange",
    "carrot_juice": "orange",
    "orange": "orange",
    "midnight_blue": "blue",
    "indigo_dye": "blue",
    "silver_blue": "blue",
    "moonstone": "blue",
    "french_blue": "blue",
    "cobalt_blue": "blue",
    "sapphire": "blue",
    "navy_blue": "blue",
    "pacific_cyan": "blue",
    "turquoise": "blue",
    "aquamarine": "blue",
    "azure_blue": "blue",
    "sky_blue": "blue",
    "neon_blue": "blue",
    "pine_green": "green",
    "hunter_green": "green",
    "pistachio": "green",
    "khaki_green": "green",
    "light_olive": "green",
    "jade_green": "green",
    "emerald": "green",
    "pacific_green": "green",
    "malachite": "green",
    "shamrock_green": "green",
    "mint_green": "green",
    "lemongrass": "green",
    "burgundy": "red",
    "strawberry": "red",
    "coral_red": "red",
    "dark_lilac": "purple",
    "english_violet": "purple",
    "purple": "purple",
    "grape": "purple",
    "cyberpunk": "purple",
    "electric_indigo": "purple",
    "lavender": "purple",
    "electric_purple": "purple",
    "fandango": "pink",
    "raspberry": "pink",
    "mystic_pearl": "pink",
    "rosewood": "pink",
}

COLOR_FAMILY_RU: dict[str, str] = {
    "blue": "Синий",
    "red": "Красный",
    "green": "Зелёный",
    "purple": "Фиолетовый",
    "pink": "Розовый",
    "gold": "Золотой",
    "orange": "Оранжевый",
    "dark": "Тёмный",
    "white": "Светлый",
}

def is_monochrome_combo(model_name: Optional[str], backdrop_key: Optional[str]) -> bool:
    if not model_name or not backdrop_key or backdrop_key == "rainbow":
        return False
    m_fam = MODEL_COLOR_FAMILIES.get(model_name)
    b_fam = BACKDROP_COLOR_FAMILIES.get(backdrop_key)
    return bool(m_fam and b_fam and m_fam == b_fam)

def get_monochrome_combo_info(model_name: Optional[str], backdrop_key: Optional[str]) -> Tuple[bool, str]:
    if not model_name or not backdrop_key or backdrop_key == "rainbow":
        return False, ""
    m_fam = MODEL_COLOR_FAMILIES.get(model_name) or ""
    b_fam = BACKDROP_COLOR_FAMILIES.get(backdrop_key) or ""
    if m_fam and b_fam and m_fam == b_fam:
        return True, m_fam
    return False, ""

MARKET_PRICE_TIERS = {
    "m1": ("1,000 — 500,000 ⭐", 1_000, 500_000),
    "m2": ("500,001 — 2,000,000 ⭐", 500_001, 2_000_000),
    "m3": ("2,000,001 — 10,000,000 ⭐", 2_000_001, 10_000_000),
    "m4": ("От 10,000,001 ⭐", 10_000_001, MARKET_MAX_PRICE),
}

def canonical_gift_key(gift_key: Optional[str]) -> str:
    k = (gift_key or "").strip()
    if k == "ring_silver":
        return "bonded_ring"
    return k

def get_upgrade_cost(gift_key: str) -> int:
    gift_key = canonical_gift_key(gift_key)
    if gift_key == "heart_lock_key":
        return HEART_LOCKET_UPGRADE_COST_STARS
    if gift_key == "cap_tg":
        return DUROV_CAP_UPGRADE_COST_STARS
    if gift_key == "trophy_cup":
        return ALGORITHM_CUP_UPGRADE_COST_STARS
    if gift_key == "bonded_ring":
        return BONDED_RING_UPGRADE_COST_STARS
    return UPGRADE_COST_STARS

def get_upgraded_gift_title(gift_key: Optional[str]) -> str:
    gift_key = canonical_gift_key(gift_key)
    if gift_key == "heart_lock_key":
        return "Heart Locket"
    if gift_key == "cap_tg":
        return "Durov's Cap"
    if gift_key == "trophy_cup":
        return "Algorithm Cup"
    if gift_key == "bonded_ring":
        return "Bonded Ring"
    if gift_key == "scared_cat":
        return "Scared Cat"
    return "Plush Pepe"

def get_upgraded_gift_emoji(gift_key: Optional[str]) -> str:
    gift_key = canonical_gift_key(gift_key)
    if gift_key == "heart_lock_key":
        return "💝"
    if gift_key == "cap_tg":
        return "🧢"
    if gift_key == "trophy_cup":
        return "🏆"
    if gift_key == "bonded_ring":
        return "💍"
    if gift_key == "scared_cat":
        return "🙀"
    return "🐸"

def upgraded_gift_tg_emoji(gift_key: Optional[str]) -> str:
    gift_key = canonical_gift_key(gift_key)
    if gift_key == "pepe_heart":
        return ce_pepe()
    if gift_key == "heart_lock_key":
        return ce("gem")
    if gift_key == "cap_tg":
        return ce("crown")
    if gift_key == "trophy_cup":
        return ce("gold", "🏆")
    if gift_key == "bonded_ring":
        return ce("gem", "💍")
    if gift_key == "scared_cat":
        return ce("fire", "🙀")
    return ce("sparkles")

def get_models_for_gift(gift_key: Optional[str]) -> list[PlushModelDef]:
    gift_key = canonical_gift_key(gift_key)
    if gift_key == "heart_lock_key":
        return HEART_LOCKET_MODELS
    if gift_key == "cap_tg":
        return DUROV_CAP_MODELS
    if gift_key == "trophy_cup":
        return ALGORITHM_CUP_MODELS
    if gift_key == "bonded_ring":
        return BONDED_RING_MODELS
    return PLUSHPEPE_MODELS

def get_model_def(gift_key: Optional[str], model_name: Optional[str]) -> PlushModelDef:
    gift_key = canonical_gift_key(gift_key)
    if gift_key == "heart_lock_key":
        return HEART_LOCKET_MODELS_BY_NAME.get(model_name or "") or HEART_LOCKET_MODELS[0]
    if gift_key == "cap_tg":
        return DUROV_CAP_MODELS_BY_NAME.get(model_name or "") or DUROV_CAP_MODELS[0]
    if gift_key == "trophy_cup":
        return ALGORITHM_CUP_MODELS_BY_NAME.get(model_name or "") or ALGORITHM_CUP_MODELS[0]
    if gift_key == "bonded_ring":
        return BONDED_RING_MODELS_BY_NAME.get(model_name or "") or BONDED_RING_MODELS[0]
    return PLUSHPEPE_MODELS_BY_NAME.get(model_name or "") or PLUSHPEPE_MODELS[0]

def gift_model_image_path(gift_key: Optional[str], filename: str) -> Optional[Path]:
    if not filename:
        return None
    gift_key = canonical_gift_key(gift_key)
    if gift_key == "heart_lock_key":
        base_dir = HEART_LOCKET_MODELS_DIR
    elif gift_key == "cap_tg":
        base_dir = DUROV_CAP_MODELS_DIR
    elif gift_key == "trophy_cup":
        base_dir = CUP_MODELS_DIR
    elif gift_key == "bonded_ring":
        base_dir = BONDED_RING_MODELS_DIR
    else:
        base_dir = PLUSHPEPE_MODELS_DIR
    p = base_dir / filename
    if p.exists():
        return p
    stem = Path(filename).stem
    for ext in (".webp", ".png", ".jpg", ".jpeg"):
        alt = base_dir / f"{stem}{ext}"
        if alt.exists():
            return alt
    return None

def plush_model_image_path(filename: str) -> Optional[Path]:
    return gift_model_image_path("pepe_heart", filename)

def roll_item_buffs() -> Tuple[int, int, int]:
    """Генерирует 1 или 2 баффа для улучшаемого NFT из элитного кейса 1,000,000 ⭐."""
    count = 2 if random.random() < 0.35 else 1
    chosen_types = random.sample(["backdrop", "model", "value"], k=count)
    b_bg = random.choice(BUFF_BACKDROP_OPTIONS) if "backdrop" in chosen_types else 0
    b_mdl = random.choice(BUFF_MODEL_OPTIONS) if "model" in chosen_types else 0
    b_val = random.choice(BUFF_VALUE_OPTIONS) if "value" in chosen_types else 0
    return b_bg, b_mdl, b_val

def get_item_buffs(item) -> Tuple[int, int, int]:
    if item is None:
        return 0, 0, 0
    try:
        keys = item.keys() if hasattr(item, "keys") else ()
        b_bg = int(item["buff_backdrop_pct"] or 0) if "buff_backdrop_pct" in keys else int(item.get("buff_backdrop_pct", 0) or 0) if isinstance(item, dict) else 0
        b_mdl = int(item["buff_model_pct"] or 0) if "buff_model_pct" in keys else int(item.get("buff_model_pct", 0) or 0) if isinstance(item, dict) else 0
        b_val = int(item["buff_value_pct"] or 0) if "buff_value_pct" in keys else int(item.get("buff_value_pct", 0) or 0) if isinstance(item, dict) else 0
        return max(0, b_bg), max(0, b_mdl), max(0, b_val)
    except Exception:
        return 0, 0, 0

def has_item_buffs(item) -> bool:
    b_bg, b_mdl, b_val = get_item_buffs(item)
    return (b_bg + b_mdl + b_val) > 0

def format_buffs_lines(item) -> List[str]:
    b_bg, b_mdl, b_val = get_item_buffs(item)
    lines: List[str] = []
    if b_bg > 0:
        lines.append(f"🎨 <b>+{b_bg}%</b> к шансу редкого фона (чёрный / серый / золото / Rainbow)")
    if b_mdl > 0:
        lines.append(f"✨ <b>+{b_mdl}%</b> к шансу редкой модели при улучшении")
    if b_val > 0:
        lines.append(f"💎 <b>+{b_val}%</b> к оценочной стоимости (Float) после улучшения")
    return lines

def format_buffs_compact(item) -> str:
    b_bg, b_mdl, b_val = get_item_buffs(item)
    parts: List[str] = []
    if b_bg > 0:
        parts.append(f"Фон +{b_bg}%")
    if b_mdl > 0:
        parts.append(f"Модель +{b_mdl}%")
    if b_val > 0:
        parts.append(f"Цена +{b_val}%")
    return " • ".join(parts)

def roll_model_for_gift(gift_key: str, buff_pct: int = 0) -> PlushModelDef:
    models = get_models_for_gift(gift_key)
    available = [m for m in models if gift_model_image_path(gift_key, m.filename) is not None]
    pool = available if available else models
    mult = 1.0 + max(0, int(buff_pct or 0)) / 100.0
    weights = [
        (m.chance_pct * mult if (mult > 1.0 and (m.chance_pct <= 1.5 or m.price_mult >= 1.22)) else m.chance_pct)
        for m in pool
    ]
    return random.choices(pool, weights=weights, k=1)[0]

def roll_plush_model() -> PlushModelDef:
    return roll_model_for_gift("pepe_heart")

def roll_backdrop(buff_pct: int = 0) -> BackdropDef:
    mult = 1.0 + max(0, int(buff_pct or 0)) / 100.0
    weights = [
        (b.chance_pct * mult if (mult > 1.0 and b.rarity_label in ("Мифический", "Ультра-редкий", "Редкий")) else b.chance_pct)
        for b in PLUSHPEPE_BACKDROPS
    ]
    return random.choices(PLUSHPEPE_BACKDROPS, weights=weights, k=1)[0]

def calculate_upgraded_stars(
    base_stars: int,
    model: PlushModelDef,
    backdrop: BackdropDef,
    gift_key: str = "pepe_heart",
    value_buff_pct: int = 0,
) -> int:
    gift_key = canonical_gift_key(gift_key)
    mono_mult = MONO_PRICE_MULT if is_monochrome_combo(model.name, backdrop.key) else 1.0
    val_mult = 1.0 + max(0, int(value_buff_pct or 0)) / 100.0
    if gift_key == "heart_lock_key":
        effective_base = base_stars + HEART_LOCKET_UPGRADE_COST_STARS
        raw = effective_base * backdrop.price_mult * model.price_mult * mono_mult * val_mult * UPGRADED_VALUE_BOOST
        return max(225_000, int(round(raw / 5_000) * 5_000))
    if gift_key == "cap_tg":
        effective_base = base_stars + DUROV_CAP_UPGRADE_COST_STARS
        raw = effective_base * backdrop.price_mult * model.price_mult * mono_mult * val_mult * UPGRADED_VALUE_BOOST
        return max(150_000, int(round(raw / 5_000) * 5_000))
    if gift_key == "trophy_cup":
        effective_base = base_stars + ALGORITHM_CUP_UPGRADE_COST_STARS
        raw = effective_base * backdrop.price_mult * model.price_mult * mono_mult * val_mult * UPGRADED_VALUE_BOOST
        return max(375_000, int(round(raw / 5_000) * 5_000))
    if gift_key == "bonded_ring":
        effective_base = base_stars + BONDED_RING_UPGRADE_COST_STARS
        raw = effective_base * backdrop.price_mult * model.price_mult * mono_mult * val_mult * UPGRADED_VALUE_BOOST
        return max(225_000, int(round(raw / 5_000) * 5_000))
    raw = base_stars * backdrop.price_mult * model.price_mult * mono_mult * val_mult * UPGRADED_VALUE_BOOST
    return max(750_000, int(round(raw / 10_000) * 10_000))

def parse_hex_rgb(hex_str: str, fallback: Tuple[int, int, int] = (40, 48, 64)) -> Tuple[int, int, int]:
    try:
        s = (hex_str or "").strip().lstrip("#")
        if len(s) == 6:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except Exception:
        pass
    return fallback

def calculate_xp_level_info(total_xp: int) -> Tuple[int, int, int, float]:
    level = 0
    current_xp = total_xp
    req_xp = 1000

    while current_xp >= req_xp:
        current_xp -= req_xp
        level += 1
        req_xp = int(req_xp + 1500 + (level * 500))

    ratio = min(1.0, max(0.0, current_xp / req_xp))
    return level, current_xp, req_xp, ratio

def calculate_clan_level_info(total_xp: int) -> Tuple[int, int, int, float, float]:
    level = 0
    current_xp = max(0, total_xp)
    req_xp = 10000

    while current_xp >= req_xp and level < 100:
        current_xp -= req_xp
        level += 1
        req_xp = int(10000 + (level * 1800) + (level ** 1.85 * 60))

    if level >= 100:
        level = 100
        ratio = 1.0
        req_xp = current_xp
    else:
        ratio = min(1.0, max(0.0, current_xp / req_xp)) if req_xp > 0 else 1.0

    bonus_pct = round(1.0 + (level / 100.0) * 44.0, 1)
    return level, current_xp, req_xp, ratio, bonus_pct

# ---------------------------------------------------------------------------
# База данных SQLite
# ---------------------------------------------------------------------------

def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    firebase_manager.schedule_sync()
    return conn

def db_init() -> None:
    conn = db_connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS global_id_seq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id_num INTEGER UNIQUE NOT NULL,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                balance_stars INTEGER NOT NULL DEFAULT 0,
                xp INTEGER NOT NULL DEFAULT 0,
                hide_top INTEGER NOT NULL DEFAULT 0,
                hide_collection INTEGER NOT NULL DEFAULT 0,
                auto_sell INTEGER NOT NULL DEFAULT 0,
                max_inventory INTEGER NOT NULL DEFAULT 25,
                last_drop_ts INTEGER NOT NULL DEFAULT 0,
                last_daily_bonus_ts INTEGER NOT NULL DEFAULT 0,
                total_drops INTEGER NOT NULL DEFAULT 0,
                total_sold INTEGER NOT NULL DEFAULT 0,
                clan_id INTEGER DEFAULT NULL,
                bg_image_path TEXT DEFAULT NULL,
                is_banned INTEGER NOT NULL DEFAULT 0,
                ban_until_ts INTEGER NOT NULL DEFAULT 0,
                ban_reason TEXT NOT NULL DEFAULT '',
                ban_hours INTEGER NOT NULL DEFAULT 0,
                privacy_accepted INTEGER NOT NULL DEFAULT 0,
                privacy_accepted_ts INTEGER NOT NULL DEFAULT 0,
                onboarding_done INTEGER NOT NULL DEFAULT 0,
                bot_started INTEGER NOT NULL DEFAULT 0,
                referral_active INTEGER NOT NULL DEFAULT 0,
                referral_activated_ts INTEGER NOT NULL DEFAULT 0,
                referral_code TEXT DEFAULT NULL,
                referred_by INTEGER DEFAULT NULL,
                referral_rewarded INTEGER NOT NULL DEFAULT 0,
                referral_count INTEGER NOT NULL DEFAULT 0,
                referral_earned_stars INTEGER NOT NULL DEFAULT 0,
                channel_prompt_done INTEGER NOT NULL DEFAULT 0,
                start_timer_ts INTEGER NOT NULL DEFAULT 0,
                last_start_ts INTEGER NOT NULL DEFAULT 0,
                is_author INTEGER NOT NULL DEFAULT 0,
                author_balance_stars INTEGER NOT NULL DEFAULT 0,
                last_active_ts INTEGER NOT NULL DEFAULT 0,
                cases_opened_total INTEGER NOT NULL DEFAULT 0,
                cases_captcha_pending INTEGER NOT NULL DEFAULT 0,
                balance_tons REAL NOT NULL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS collection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                gift_key TEXT NOT NULL,
                obtained_ts INTEGER NOT NULL,
                is_favorite INTEGER NOT NULL DEFAULT 0,
                is_upgraded INTEGER NOT NULL DEFAULT 0,
                model_name TEXT DEFAULT NULL,
                backdrop_key TEXT DEFAULT NULL,
                upgraded_stars INTEGER NOT NULL DEFAULT 0,
                upgrade_num INTEGER NOT NULL DEFAULT 0,
                is_listed INTEGER NOT NULL DEFAULT 0,
                buff_backdrop_pct INTEGER NOT NULL DEFAULT 0,
                buff_model_pct INTEGER NOT NULL DEFAULT 0,
                buff_value_pct INTEGER NOT NULL DEFAULT 0,
                edition_num INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS market_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL,
                seller_id INTEGER NOT NULL,
                gift_key TEXT NOT NULL,
                model_name TEXT NOT NULL,
                backdrop_key TEXT NOT NULL,
                upgraded_stars INTEGER NOT NULL DEFAULT 0,
                upgrade_num INTEGER NOT NULL DEFAULT 0,
                price_stars INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                buyer_id INTEGER DEFAULT NULL,
                created_ts INTEGER NOT NULL,
                sold_ts INTEGER DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS market_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER NOT NULL,
                seller_id INTEGER NOT NULL,
                buyer_id INTEGER NOT NULL,
                gift_key TEXT NOT NULL,
                model_name TEXT NOT NULL,
                backdrop_key TEXT NOT NULL,
                price_stars INTEGER NOT NULL,
                fee_stars INTEGER NOT NULL,
                seller_received_stars INTEGER NOT NULL,
                sold_ts INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pending_drops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                gift_key TEXT NOT NULL,
                created_ts INTEGER NOT NULL,
                resolved INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_num INTEGER UNIQUE,
                owner_id INTEGER NOT NULL,
                tag TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                type TEXT NOT NULL DEFAULT 'public',
                entry_fee INTEGER NOT NULL DEFAULT 0,
                max_members INTEGER NOT NULL DEFAULT 15,
                xp INTEGER NOT NULL DEFAULT 0,
                donated_stars INTEGER NOT NULL DEFAULT 0,
                spent_stars INTEGER NOT NULL DEFAULT 0,
                avatar_path TEXT DEFAULT NULL,
                favorite_keys TEXT DEFAULT '',
                last_daily_xp_ts INTEGER NOT NULL DEFAULT 0,
                created_ts INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS clan_gifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clan_id INTEGER NOT NULL,
                donor_user_id INTEGER NOT NULL,
                gift_key TEXT NOT NULL,
                donated_ts INTEGER NOT NULL,
                is_favorite INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (clan_id) REFERENCES clans(id)
            );

            CREATE TABLE IF NOT EXISTS clan_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clan_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_ts INTEGER NOT NULL,
                UNIQUE(clan_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS star_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                creator_id INTEGER NOT NULL,
                amount_stars INTEGER NOT NULL,
                target_username TEXT NOT NULL DEFAULT '',
                target_user_id INTEGER DEFAULT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                claimed_by INTEGER DEFAULT NULL,
                rendered INTEGER NOT NULL DEFAULT 0,
                created_ts INTEGER NOT NULL,
                claimed_ts INTEGER DEFAULT NULL,
                max_claims INTEGER NOT NULL DEFAULT 1,
                claimed_count INTEGER NOT NULL DEFAULT 0,
                per_claim_stars INTEGER NOT NULL DEFAULT 0,
                password_hash TEXT NOT NULL DEFAULT '',
                has_password INTEGER NOT NULL DEFAULT 0,
                inline_message_id TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS star_check_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                amount_stars INTEGER NOT NULL,
                claimed_ts INTEGER NOT NULL,
                UNIQUE(check_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_user_id INTEGER UNIQUE NOT NULL,
                reward_stars INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                created_ts INTEGER NOT NULL,
                rewarded_ts INTEGER DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS author_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channels_text TEXT NOT NULL,
                age_text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                reject_reason TEXT NOT NULL DEFAULT '',
                reviewed_by INTEGER DEFAULT NULL,
                created_ts INTEGER NOT NULL,
                reviewed_ts INTEGER DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS author_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                username TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                chat_type TEXT NOT NULL DEFAULT 'channel',
                verified INTEGER NOT NULL DEFAULT 1,
                created_ts INTEGER NOT NULL,
                UNIQUE(author_id, chat_id)
            );

            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                author_id INTEGER NOT NULL,
                channels_json TEXT NOT NULL,
                text_html TEXT NOT NULL,
                photo_file_id TEXT NOT NULL DEFAULT '',
                winners_count INTEGER NOT NULL DEFAULT 1,
                total_prize_stars INTEGER NOT NULL DEFAULT 0,
                per_winner_stars INTEGER NOT NULL DEFAULT 0,
                btn_text TEXT NOT NULL DEFAULT 'Участвовать',
                btn_style TEXT NOT NULL DEFAULT 'success',
                btn_mode TEXT NOT NULL DEFAULT 'button',
                max_participants INTEGER NOT NULL DEFAULT 0,
                publish_ts INTEGER NOT NULL DEFAULT 0,
                end_ts INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                posted_messages_json TEXT NOT NULL DEFAULT '[]',
                winners_json TEXT NOT NULL DEFAULT '[]',
                deducted_from_author INTEGER NOT NULL DEFAULT 1,
                created_ts INTEGER NOT NULL,
                finished_ts INTEGER DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS giveaway_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                giveaway_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                joined_ts INTEGER NOT NULL,
                UNIQUE(giveaway_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS case_battles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER NOT NULL,
                cases_json TEXT NOT NULL,
                total_cost_stars INTEGER NOT NULL,
                max_players INTEGER NOT NULL DEFAULT 2,
                status TEXT NOT NULL DEFAULT 'waiting',
                countdown_ends_ts INTEGER NOT NULL DEFAULT 0,
                winner_id INTEGER DEFAULT NULL,
                winner_total_stars INTEGER NOT NULL DEFAULT 0,
                results_json TEXT NOT NULL DEFAULT '[]',
                created_ts INTEGER NOT NULL,
                finished_ts INTEGER DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS case_battle_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                battle_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                joined_ts INTEGER NOT NULL,
                ui_chat_id INTEGER DEFAULT NULL,
                ui_message_id INTEGER DEFAULT NULL,
                UNIQUE(battle_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS user_backgrounds (
                user_id INTEGER PRIMARY KEY,
                file_id TEXT NOT NULL DEFAULT '',
                bg_blob BLOB,
                updated_ts INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS shop_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                pack_key TEXT NOT NULL,
                xtr_amount INTEGER NOT NULL,
                stars_reward INTEGER NOT NULL,
                xp_reward INTEGER NOT NULL,
                nfts_count INTEGER NOT NULL,
                telegram_payment_charge_id TEXT UNIQUE NOT NULL,
                payload TEXT NOT NULL DEFAULT '',
                created_ts INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                reward_stars INTEGER NOT NULL DEFAULT 0,
                gift_key TEXT DEFAULT NULL,
                gift_count INTEGER NOT NULL DEFAULT 0,
                max_uses INTEGER NOT NULL DEFAULT 1,
                used_count INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_by INTEGER NOT NULL DEFAULT 0,
                created_ts INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS promo_redemptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                promo_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                redeemed_ts INTEGER NOT NULL,
                UNIQUE(promo_id, user_id),
                FOREIGN KEY (promo_id) REFERENCES promocodes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS memecoins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                ticker TEXT NOT NULL,
                image_b64 TEXT NOT NULL,
                reserve_ton REAL NOT NULL,
                reserve_token REAL NOT NULL,
                total_supply REAL NOT NULL,
                price_ton REAL NOT NULL,
                market_cap_ton REAL NOT NULL,
                volume_24h_ton REAL NOT NULL DEFAULT 0.0,
                holders_count INTEGER NOT NULL DEFAULT 1,
                created_ts INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memecoin_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                coin_id INTEGER NOT NULL,
                amount REAL NOT NULL DEFAULT 0.0,
                avg_buy_price_ton REAL NOT NULL DEFAULT 0.0,
                UNIQUE(user_id, coin_id),
                FOREIGN KEY (coin_id) REFERENCES memecoins(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS memecoin_candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id INTEGER NOT NULL,
                bucket_ts INTEGER NOT NULL,
                open_ton REAL NOT NULL,
                high_ton REAL NOT NULL,
                low_ton REAL NOT NULL,
                close_ton REAL NOT NULL,
                volume_ton REAL NOT NULL DEFAULT 0.0,
                UNIQUE(coin_id, bucket_ts),
                FOREIGN KEY (coin_id) REFERENCES memecoins(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS memecoin_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                side TEXT NOT NULL,
                ton_amount REAL NOT NULL,
                token_amount REAL NOT NULL,
                price_ton REAL NOT NULL,
                created_ts INTEGER NOT NULL,
                FOREIGN KEY (coin_id) REFERENCES memecoins(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS rocket_rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crash_point REAL NOT NULL,
                status TEXT NOT NULL,
                created_ts INTEGER NOT NULL,
                crashed_ts INTEGER DEFAULT NULL
            );
            """
        )

        coll_cols = [row["name"] for row in conn.execute("PRAGMA table_info(collection)").fetchall()]
        if "is_upgraded" not in coll_cols:
            conn.execute("ALTER TABLE collection ADD COLUMN is_upgraded INTEGER NOT NULL DEFAULT 0;")
        if "model_name" not in coll_cols:
            conn.execute("ALTER TABLE collection ADD COLUMN model_name TEXT DEFAULT NULL;")
        if "backdrop_key" not in coll_cols:
            conn.execute("ALTER TABLE collection ADD COLUMN backdrop_key TEXT DEFAULT NULL;")
        if "upgraded_stars" not in coll_cols:
            conn.execute("ALTER TABLE collection ADD COLUMN upgraded_stars INTEGER NOT NULL DEFAULT 0;")
        if "upgrade_num" not in coll_cols:
            conn.execute("ALTER TABLE collection ADD COLUMN upgrade_num INTEGER NOT NULL DEFAULT 0;")
        if "is_listed" not in coll_cols:
            conn.execute("ALTER TABLE collection ADD COLUMN is_listed INTEGER NOT NULL DEFAULT 0;")
        if "buff_backdrop_pct" not in coll_cols:
            conn.execute("ALTER TABLE collection ADD COLUMN buff_backdrop_pct INTEGER NOT NULL DEFAULT 0;")
        if "buff_model_pct" not in coll_cols:
            conn.execute("ALTER TABLE collection ADD COLUMN buff_model_pct INTEGER NOT NULL DEFAULT 0;")
        if "buff_value_pct" not in coll_cols:
            conn.execute("ALTER TABLE collection ADD COLUMN buff_value_pct INTEGER NOT NULL DEFAULT 0;")
        if "edition_num" not in coll_cols:
            conn.execute("ALTER TABLE collection ADD COLUMN edition_num INTEGER NOT NULL DEFAULT 0;")

        clan_cols = [row["name"] for row in conn.execute("PRAGMA table_info(clans)").fetchall()]
        if "id_num" not in clan_cols:
            conn.execute("ALTER TABLE clans ADD COLUMN id_num INTEGER DEFAULT NULL;")
        if "xp" not in clan_cols:
            conn.execute("ALTER TABLE clans ADD COLUMN xp INTEGER NOT NULL DEFAULT 0;")
        if "donated_stars" not in clan_cols:
            conn.execute("ALTER TABLE clans ADD COLUMN donated_stars INTEGER NOT NULL DEFAULT 0;")
        if "spent_stars" not in clan_cols:
            conn.execute("ALTER TABLE clans ADD COLUMN spent_stars INTEGER NOT NULL DEFAULT 0;")
        if "avatar_path" not in clan_cols:
            conn.execute("ALTER TABLE clans ADD COLUMN avatar_path TEXT DEFAULT NULL;")
        if "favorite_keys" not in clan_cols:
            conn.execute("ALTER TABLE clans ADD COLUMN favorite_keys TEXT DEFAULT '';")
        if "last_daily_xp_ts" not in clan_cols:
            conn.execute("ALTER TABLE clans ADD COLUMN last_daily_xp_ts INTEGER NOT NULL DEFAULT 0;")

        user_cols = [row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "id_num" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN id_num INTEGER DEFAULT NULL;")
        if "clan_id" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN clan_id INTEGER DEFAULT NULL;")
        if "bg_image_path" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN bg_image_path TEXT DEFAULT NULL;")
        if "is_banned" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER NOT NULL DEFAULT 0;")
        if "ban_until_ts" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN ban_until_ts INTEGER NOT NULL DEFAULT 0;")
        if "ban_reason" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN ban_reason TEXT NOT NULL DEFAULT '';")
        if "ban_hours" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN ban_hours INTEGER NOT NULL DEFAULT 0;")
        if "privacy_accepted" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN privacy_accepted INTEGER NOT NULL DEFAULT 0;")
        if "privacy_accepted_ts" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN privacy_accepted_ts INTEGER NOT NULL DEFAULT 0;")
        if "onboarding_done" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN onboarding_done INTEGER NOT NULL DEFAULT 0;")
            conn.execute("UPDATE users SET onboarding_done=1 WHERE privacy_accepted=1;")
        if "bot_started" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN bot_started INTEGER NOT NULL DEFAULT 0;")
            conn.execute("UPDATE users SET bot_started=1;")
        if "referral_active" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN referral_active INTEGER NOT NULL DEFAULT 0;")
        if "referral_activated_ts" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN referral_activated_ts INTEGER NOT NULL DEFAULT 0;")
        if "referral_code" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN referral_code TEXT DEFAULT NULL;")
        if "referred_by" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT NULL;")
        if "referral_rewarded" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN referral_rewarded INTEGER NOT NULL DEFAULT 0;")
        if "referral_count" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN referral_count INTEGER NOT NULL DEFAULT 0;")
        if "referral_earned_stars" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN referral_earned_stars INTEGER NOT NULL DEFAULT 0;")
        if "channel_prompt_done" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN channel_prompt_done INTEGER NOT NULL DEFAULT 0;")
        if "start_timer_ts" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN start_timer_ts INTEGER NOT NULL DEFAULT 0;")
        if "last_start_ts" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN last_start_ts INTEGER NOT NULL DEFAULT 0;")
        if "is_author" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN is_author INTEGER NOT NULL DEFAULT 0;")
        if "author_balance_stars" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN author_balance_stars INTEGER NOT NULL DEFAULT 0;")
        if "last_active_ts" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN last_active_ts INTEGER NOT NULL DEFAULT 0;")
        if "cases_opened_total" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN cases_opened_total INTEGER NOT NULL DEFAULT 0;")
        if "cases_captcha_pending" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN cases_captcha_pending INTEGER NOT NULL DEFAULT 0;")
        if "last_name_promo_bonus_ts" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN last_name_promo_bonus_ts INTEGER NOT NULL DEFAULT 0;")
        if "last_bio_promo_bonus_ts" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN last_bio_promo_bonus_ts INTEGER NOT NULL DEFAULT 0;")
        if "free_10k_cases" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN free_10k_cases INTEGER NOT NULL DEFAULT 0;")
        if "balance_tons" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN balance_tons REAL NOT NULL DEFAULT 0.0;")
        conn.execute("UPDATE collection SET is_listed=0 WHERE is_listed=2;")
        conn.execute(
            "UPDATE users SET last_active_ts = MAX(last_active_ts, last_start_ts, last_drop_ts, last_daily_bonus_ts) "
            "WHERE last_active_ts = 0;"
        )
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code) WHERE referral_code IS NOT NULL;")

        chk_cols = [row["name"] for row in conn.execute("PRAGMA table_info(star_checks)").fetchall()]
        if "max_claims" not in chk_cols:
            conn.execute("ALTER TABLE star_checks ADD COLUMN max_claims INTEGER NOT NULL DEFAULT 1;")
        if "claimed_count" not in chk_cols:
            conn.execute("ALTER TABLE star_checks ADD COLUMN claimed_count INTEGER NOT NULL DEFAULT 0;")
        if "per_claim_stars" not in chk_cols:
            conn.execute("ALTER TABLE star_checks ADD COLUMN per_claim_stars INTEGER NOT NULL DEFAULT 0;")
        if "password_hash" not in chk_cols:
            conn.execute("ALTER TABLE star_checks ADD COLUMN password_hash TEXT NOT NULL DEFAULT '';")
        if "has_password" not in chk_cols:
            conn.execute("ALTER TABLE star_checks ADD COLUMN has_password INTEGER NOT NULL DEFAULT 0;")
        if "inline_message_id" not in chk_cols:
            conn.execute("ALTER TABLE star_checks ADD COLUMN inline_message_id TEXT NOT NULL DEFAULT '';")
        conn.execute("UPDATE star_checks SET per_claim_stars=amount_stars WHERE per_claim_stars=0 AND amount_stars>0;")
        conn.execute("UPDATE star_checks SET claimed_count=1 WHERE status='claimed' AND claimed_count=0;")

        unlinked_clans = conn.execute("SELECT id FROM clans WHERE id_num IS NULL").fetchall()
        for c in unlinked_clans:
            cur = conn.execute("INSERT INTO global_id_seq (entity_type) VALUES ('clan')")
            conn.execute("UPDATE clans SET id_num=? WHERE id=?", (cur.lastrowid, c["id"]))
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_clans_id_num ON clans(id_num);")

        unlinked_users = conn.execute("SELECT user_id FROM users WHERE id_num IS NULL").fetchall()
        for u in unlinked_users:
            cur = conn.execute("INSERT INTO global_id_seq (entity_type) VALUES ('user')")
            conn.execute("UPDATE users SET id_num=? WHERE user_id=?", (cur.lastrowid, u["user_id"]))
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_id_num ON users(id_num);")

        # Миграция legacy ring_silver (Signet Ring с изображением Bonded Ring) -> bonded_ring
        for _mig_tbl in ("collection", "market_listings", "market_history", "pending_drops", "clan_gifts"):
            conn.execute(f"UPDATE {_mig_tbl} SET gift_key='bonded_ring' WHERE gift_key='ring_silver'")

        conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('maintenance_mode', '0')")
        conn.execute(
            "INSERT OR IGNORE INTO bot_settings (key, value) VALUES "
            "('scared_cat_minted', CAST((SELECT COUNT(*) FROM collection WHERE gift_key='scared_cat') AS TEXT))"
        )

        # Синхронизация локальных фонов пользователей <-> SQLite BLOB (защита от потери при рестартах/миграциях)
        bg_users = conn.execute("SELECT user_id, bg_image_path FROM users WHERE bg_image_path IS NOT NULL AND bg_image_path != ''").fetchall()
        for bu in bg_users:
            b_uid = int(bu["user_id"])
            stored_row = conn.execute("SELECT bg_blob FROM user_backgrounds WHERE user_id=?", (b_uid,)).fetchone()
            target_local = BACKGROUNDS_DIR / f"bg_{b_uid}.jpg"
            if stored_row and stored_row["bg_blob"]:
                if not target_local.exists() or target_local.stat().st_size == 0:
                    try:
                        tmp_bg = BACKGROUNDS_DIR / f".bg_{b_uid}.tmp"
                        tmp_bg.write_bytes(bytes(stored_row["bg_blob"]))
                        os.replace(tmp_bg, target_local)
                    except Exception:
                        pass
            else:
                src_cand = None
                raw_p = Path(bu["bg_image_path"])
                for cand in (raw_p, BACKGROUNDS_DIR / raw_p.name, target_local):
                    if cand.exists() and cand.is_file() and cand.stat().st_size > 0:
                        src_cand = cand
                        break
                if src_cand is not None:
                    try:
                        blob_data = src_cand.read_bytes()
                        norm = _normalize_bg_bytes_to_jpeg(blob_data) or blob_data
                        conn.execute(
                            "INSERT INTO user_backgrounds (user_id, file_id, bg_blob, updated_ts) VALUES (?, '', ?, ?) "
                            "ON CONFLICT(user_id) DO UPDATE SET bg_blob=excluded.bg_blob, updated_ts=excluded.updated_ts",
                            (b_uid, norm, int(time.time())),
                        )
                    except Exception:
                        pass

        # Однократная инициализация счётчиков оборота звёзд из исторических данных БД
        eco_boot = conn.execute("SELECT value FROM bot_settings WHERE key='eco_bootstrapped_v1'").fetchone()
        if not eco_boot or eco_boot["value"] != "1":
            cur_cap = int(conn.execute("SELECT COALESCE(SUM(balance_stars + author_balance_stars), 0) AS s FROM users").fetchone()["s"] or 0)
            mkt_row = conn.execute("SELECT COALESCE(SUM(price_stars), 0) AS p, COALESCE(SUM(fee_stars), 0) AS f FROM market_history").fetchone()
            mkt_vol = int(mkt_row["p"] or 0)
            mkt_fee = int(mkt_row["f"] or 0)

            upg_rows = conn.execute("SELECT gift_key, COUNT(*) AS cnt FROM collection WHERE is_upgraded=1 GROUP BY gift_key").fetchall()
            upg_burned = sum(int(r["cnt"] or 0) * get_upgrade_cost(r["gift_key"]) for r in upg_rows)

            bg_cnt = int(conn.execute("SELECT COUNT(*) AS cnt FROM users WHERE bg_image_path IS NOT NULL AND bg_image_path != ''").fetchone()["cnt"] or 0)
            bg_burned = bg_cnt * BG_SET_COST

            slots_rows = conn.execute("SELECT max_inventory FROM users WHERE max_inventory > 25").fetchall()
            slots_burned = sum(max(0, int(r["max_inventory"] or 25) - 25) * 26 for r in slots_rows)

            clan_cnt = int(conn.execute("SELECT COUNT(*) AS cnt FROM clans").fetchone()["cnt"] or 0)
            clan_sums = conn.execute("SELECT COALESCE(SUM(donated_stars), 0) AS d, COALESCE(SUM(spent_stars), 0) AS s FROM clans").fetchone()
            clan_burned = clan_cnt * CLAN_CREATE_COST + int(clan_sums["s"] or 0)
            clan_donated = int(clan_sums["d"] or 0)

            battles_vol = int(
                conn.execute(
                    "SELECT COALESCE(SUM(cb.total_cost_stars * (SELECT COUNT(*) FROM case_battle_participants p WHERE p.battle_id=cb.id)), 0) AS s "
                    "FROM case_battles cb WHERE cb.status IN ('countdown', 'running', 'finished')"
                ).fetchone()["s"] or 0
            )
            checks_vol = int(conn.execute("SELECT COALESCE(SUM(amount_stars), 0) AS s FROM star_checks WHERE status != 'cancelled'").fetchone()["s"] or 0)
            gw_vol = int(conn.execute("SELECT COALESCE(SUM(total_prize_stars), 0) AS s FROM giveaways WHERE status != 'cancelled'").fetchone()["s"] or 0)

            burned_base = mkt_fee + upg_burned + bg_burned + slots_burned + clan_burned
            purchased_base = mkt_vol + upg_burned + bg_burned + slots_burned + clan_burned
            spent_base = purchased_base + battles_vol + checks_vol + gw_vol
            issued_base = cur_cap + burned_base + clan_donated

            for k_eco, v_eco in (
                ("eco_stars_issued", str(issued_base)),
                ("eco_stars_spent", str(spent_base)),
                ("eco_stars_burned", str(burned_base)),
                ("eco_stars_purchased", str(purchased_base)),
                ("eco_bootstrapped_v1", "1"),
            ):
                conn.execute(
                    "INSERT INTO bot_settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (k_eco, v_eco),
                )

        conn.commit()
    finally:
        conn.close()

def get_bot_setting(key: str, default: str = "") -> str:
    conn = db_connect()
    try:
        row = conn.execute("SELECT value FROM bot_settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default
    except Exception:
        return default
    finally:
        conn.close()

def set_bot_setting(key: str, value: str) -> None:
    conn = db_connect()
    try:
        conn.execute(
            "INSERT INTO bot_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()

_LAST_ACTIVE_MEM: Dict[int, int] = {}
_LAST_ACTIVE_DB_WRITE: Dict[int, int] = {}
_ACTIVITY_LOCK = threading.Lock()

def touch_user_activity(user_id: int) -> None:
    """Фиксирует онлайн-активность пользователя в памяти и с троттлингом обновляет users.last_active_ts."""
    if not user_id or user_id <= 0:
        return
    now = int(time.time())
    should_write = False
    with _ACTIVITY_LOCK:
        _LAST_ACTIVE_MEM[user_id] = now
        prev_db = _LAST_ACTIVE_DB_WRITE.get(user_id, 0)
        if now - prev_db >= 45:
            _LAST_ACTIVE_DB_WRITE[user_id] = now
            should_write = True
    if should_write:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("UPDATE users SET last_active_ts=? WHERE user_id=? AND last_active_ts<?", (now, user_id, now))
            conn.commit()
        except Exception:
            pass
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

def _eco_inc_conn(conn: sqlite3.Connection, deltas: Dict[str, int]) -> None:
    for k, v in deltas.items():
        amt = int(v or 0)
        if amt <= 0:
            continue
        conn.execute(
            "INSERT INTO bot_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = CAST(COALESCE(NULLIF(bot_settings.value, ''), '0') AS INTEGER) + CAST(excluded.value AS INTEGER)",
            (k, str(amt)),
        )

def record_star_flow(
    issued: int = 0,
    spent: int = 0,
    burned: int = 0,
    purchased: int = 0,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    deltas = {
        "eco_stars_issued": int(issued or 0),
        "eco_stars_spent": int(spent or 0),
        "eco_stars_burned": int(burned or 0),
        "eco_stars_purchased": int(purchased or 0),
    }
    if not any(v > 0 for v in deltas.values()):
        return
    if conn is not None:
        _eco_inc_conn(conn, deltas)
        return
    c = db_connect()
    try:
        _eco_inc_conn(c, deltas)
        c.commit()
    finally:
        c.close()

def _normalize_bg_bytes_to_jpeg(raw_bytes: bytes) -> Optional[bytes]:
    """Нормализует загруженный фон (EXIF, RGB, размер под карточку) в компактный JPEG для локального кэша и SQLite."""
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img_raw:
            img_t = ImageOps.exif_transpose(img_raw)
            img_rgb = img_t.convert("RGB")
            fitted = ImageOps.fit(img_rgb, (1000, 560), method=Image.Resampling.LANCZOS)
            out = io.BytesIO()
            fitted.save(out, format="JPEG", quality=85, optimize=True)
            data = out.getvalue()
            return data if data else None
    except Exception:
        return None

def save_user_background_data(user_id: int, raw_bytes: bytes, file_id: str = "") -> str:
    """Атомарно сохраняет фон профиля в BACKGROUNDS_DIR и дублирует JPEG-блоб + file_id в SQLite."""
    BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    bg_file_path = BACKGROUNDS_DIR / f"bg_{user_id}.jpg"
    norm_bytes = _normalize_bg_bytes_to_jpeg(raw_bytes) or raw_bytes
    tmp_path = BACKGROUNDS_DIR / f".bg_{user_id}_{secrets.token_hex(4)}.tmp"
    tmp_path.write_bytes(norm_bytes)
    os.replace(tmp_path, bg_file_path)

    now = int(time.time())
    conn = db_connect()
    try:
        conn.execute(
            "INSERT INTO user_backgrounds (user_id, file_id, bg_blob, updated_ts) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "file_id=CASE WHEN excluded.file_id != '' THEN excluded.file_id ELSE user_backgrounds.file_id END, "
            "bg_blob=excluded.bg_blob, updated_ts=excluded.updated_ts",
            (user_id, file_id or "", norm_bytes, now),
        )
        conn.execute("UPDATE users SET bg_image_path=? WHERE user_id=?", (str(bg_file_path), user_id))
        conn.commit()
        firebase_manager.schedule_sync()
    finally:
        conn.close()
    return str(bg_file_path)

def get_user_bg_file_id(user_id: int) -> str:
    conn = db_connect()
    try:
        row = conn.execute("SELECT file_id FROM user_backgrounds WHERE user_id=?", (user_id,)).fetchone()
        return (row["file_id"] or "").strip() if row else ""
    except Exception:
        return ""
    finally:
        conn.close()

def resolve_user_bg_path(user_id: Optional[int], custom_bg_path: Optional[str]) -> Optional[Path]:
    """Ищет файл фона на диске (включая старые пути) и при необходимости восстанавливает его из SQLite."""
    candidates: List[Path] = []
    if custom_bg_path:
        p = Path(custom_bg_path)
        candidates.append(p)
        candidates.append(BACKGROUNDS_DIR / p.name)
    if user_id:
        candidates.append(BACKGROUNDS_DIR / f"bg_{user_id}.jpg")

    for cand in candidates:
        try:
            if cand.exists() and cand.is_file() and cand.stat().st_size > 0:
                return cand
        except Exception:
            pass

    if user_id:
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT bg_blob FROM user_backgrounds WHERE user_id=?", (user_id,)).fetchone()
            if row and row["bg_blob"]:
                BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
                target = BACKGROUNDS_DIR / f"bg_{user_id}.jpg"
                tmp_p = BACKGROUNDS_DIR / f".bg_restore_{user_id}_{secrets.token_hex(3)}.tmp"
                tmp_p.write_bytes(bytes(row["bg_blob"]))
                os.replace(tmp_p, target)
                return target
        except Exception:
            pass
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
    return None

def has_user_background(db_user) -> bool:
    if not db_user:
        return False
    if db_user["bg_image_path"]:
        return True
    try:
        uid = int(db_user["user_id"])
    except Exception:
        return False
    return resolve_user_bg_path(uid, None) is not None

def get_admin_dashboard_stats() -> dict:
    """Собирает сводную статистику бота для Админ-панели."""
    now = int(time.time())
    conn = db_connect()
    try:
        total_users = int(conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"] or 0)
        total_banned = int(conn.execute("SELECT COUNT(*) as cnt FROM users WHERE is_banned=1").fetchone()["cnt"] or 0)
        total_collection_gifts = int(conn.execute("SELECT COUNT(*) as cnt FROM collection").fetchone()["cnt"] or 0)
        total_sold = int(conn.execute("SELECT COALESCE(SUM(total_sold), 0) as s FROM users").fetchone()["s"] or 0)
        total_drops = int(conn.execute("SELECT COALESCE(SUM(total_drops), 0) as s FROM users").fetchone()["s"] or 0)
        total_stars_capital = int(conn.execute("SELECT COALESCE(SUM(balance_stars), 0) as s FROM users").fetchone()["s"] or 0)
        total_author_capital = int(conn.execute("SELECT COALESCE(SUM(author_balance_stars), 0) as s FROM users").fetchone()["s"] or 0)
        total_clans = int(conn.execute("SELECT COUNT(*) as cnt FROM clans").fetchone()["cnt"] or 0)
        pending_apps = int(conn.execute("SELECT COUNT(*) as cnt FROM author_applications WHERE status='pending'").fetchone()["cnt"] or 0)
        total_authors = int(conn.execute("SELECT COUNT(*) as cnt FROM users WHERE is_author=1").fetchone()["cnt"] or 0)

        # Активность / Онлайн (объединяем БД и in-memory кэш)
        cutoff_24h = now - 86400
        cutoff_5m = now - 300
        active_rows = conn.execute(
            "SELECT user_id, last_active_ts FROM users WHERE last_active_ts >= ?",
            (cutoff_24h,),
        ).fetchall()
        merged_active: Dict[int, int] = {int(r["user_id"]): int(r["last_active_ts"] or 0) for r in active_rows}
        with _ACTIVITY_LOCK:
            for uid_m, ts_m in _LAST_ACTIVE_MEM.items():
                if ts_m >= cutoff_24h and ts_m > merged_active.get(uid_m, 0):
                    merged_active[uid_m] = ts_m
        online_now = sum(1 for ts_v in merged_active.values() if ts_v >= cutoff_5m)
        active_24h = sum(1 for ts_v in merged_active.values() if ts_v >= cutoff_24h)

        # Дуэли / Баттлы
        duel_rooms_now = int(
            conn.execute(
                "SELECT COUNT(*) AS cnt FROM case_battles WHERE status IN ('waiting', 'countdown', 'running')"
            ).fetchone()["cnt"] or 0
        )
        duel_players_now = int(
            conn.execute(
                "SELECT COUNT(DISTINCT p.user_id) AS cnt "
                "FROM case_battle_participants p "
                "JOIN case_battles b ON b.id = p.battle_id "
                "WHERE b.status IN ('waiting', 'countdown', 'running')"
            ).fetchone()["cnt"] or 0
        )
        duel_finished_total = int(
            conn.execute("SELECT COUNT(*) AS cnt FROM case_battles WHERE status='finished'").fetchone()["cnt"] or 0
        )

        # Общая стоимость всех коллекций + лидеры по коллекции и богатству профиля
        coll_user_groups = conn.execute(
            "SELECT user_id, gift_key, is_upgraded, COUNT(*) AS cnt, COALESCE(SUM(upgraded_stars), 0) AS sum_upg "
            "FROM collection GROUP BY user_id, gift_key, is_upgraded"
        ).fetchall()
        total_collection_value = 0
        user_coll_vals: Dict[int, int] = {}
        user_coll_counts: Dict[int, int] = {}
        for cg in coll_user_groups:
            uid_c = int(cg["user_id"])
            cnt_c = int(cg["cnt"] or 0)
            g = GIFTS_BY_KEY.get(cg["gift_key"])
            base_val = int(g.stars) if g else 0
            if cg["is_upgraded"]:
                upg_val = int(cg["sum_upg"] or 0)
                val_c = upg_val if upg_val > 0 else cnt_c * base_val
            else:
                val_c = cnt_c * base_val
            total_collection_value += val_c
            user_coll_vals[uid_c] = user_coll_vals.get(uid_c, 0) + val_c
            user_coll_counts[uid_c] = user_coll_counts.get(uid_c, 0) + cnt_c

        user_info_rows = conn.execute(
            "SELECT user_id, username, first_name, balance_stars FROM users"
        ).fetchall()
        richest_profile: Optional[dict] = None
        top_collection: Optional[dict] = None
        for ur in user_info_rows:
            uid_u = int(ur["user_id"])
            bal_u = int(ur["balance_stars"] or 0)
            cval_u = user_coll_vals.get(uid_u, 0)
            ccnt_u = user_coll_counts.get(uid_u, 0)
            total_w = bal_u + cval_u
            disp_u = normalize_telegram_name(ur["first_name"], ur["username"], uid_u)
            if richest_profile is None or total_w > richest_profile["total_wealth"]:
                richest_profile = {
                    "user_id": uid_u,
                    "display_name": disp_u,
                    "balance_stars": bal_u,
                    "collection_value": cval_u,
                    "total_wealth": total_w,
                }
            if ccnt_u > 0 and (top_collection is None or cval_u > top_collection["collection_value"]):
                top_collection = {
                    "user_id": uid_u,
                    "display_name": disp_u,
                    "collection_value": cval_u,
                    "item_count": ccnt_u,
                }

        # Статистика акции Scared Cat, Маркета, Магазина, Кейсов и Розыгрышей
        sc_set_row = conn.execute("SELECT value FROM bot_settings WHERE key='scared_cat_minted'").fetchone()
        sc_coll_cnt = int(conn.execute("SELECT COUNT(*) AS cnt FROM collection WHERE gift_key='scared_cat'").fetchone()["cnt"] or 0)
        scared_cat_minted = max(int(sc_set_row["value"] or 0) if sc_set_row else 0, sc_coll_cnt)

        market_active_lots = int(conn.execute("SELECT COUNT(*) AS cnt FROM market_listings WHERE status='active'").fetchone()["cnt"] or 0)
        mkt_hist_row = conn.execute("SELECT COUNT(*) AS cnt, COALESCE(SUM(price_stars), 0) AS vol FROM market_history").fetchone()
        market_total_deals = int(mkt_hist_row["cnt"] or 0)
        market_total_volume = int(mkt_hist_row["vol"] or 0)

        shop_row = conn.execute("SELECT COUNT(*) AS cnt, COALESCE(SUM(xtr_amount), 0) AS xtr FROM shop_purchases").fetchone()
        shop_purchases_cnt = int(shop_row["cnt"] or 0)
        shop_total_xtr = int(shop_row["xtr"] or 0)

        total_cases_opened = int(conn.execute("SELECT COALESCE(SUM(cases_opened_total), 0) AS s FROM users").fetchone()["s"] or 0)
        active_giveaways = int(conn.execute("SELECT COUNT(*) AS cnt FROM giveaways WHERE status='active'").fetchone()["cnt"] or 0)

        # Оборот звёзд
        eco_rows = conn.execute(
            "SELECT key, value FROM bot_settings WHERE key IN ('eco_stars_issued', 'eco_stars_spent', 'eco_stars_burned', 'eco_stars_purchased')"
        ).fetchall()
        eco_map = {r["key"]: int(r["value"] or 0) for r in eco_rows}
        eco_issued = eco_map.get("eco_stars_issued", 0)
        eco_spent = eco_map.get("eco_stars_spent", 0)
        eco_burned = eco_map.get("eco_stars_burned", 0)
        eco_purchased = eco_map.get("eco_stars_purchased", 0)
        eco_total_turnover = max(
            total_stars_capital + total_author_capital + eco_burned,
            eco_issued + eco_spent,
        )

        return {
            "total_users": total_users,
            "total_banned": total_banned,
            "total_collection_gifts": total_collection_gifts,
            "total_sold": total_sold,
            "total_drops": total_drops,
            "total_stars_capital": total_stars_capital,
            "total_author_capital": total_author_capital,
            "total_clans": total_clans,
            "pending_apps": pending_apps,
            "total_authors": total_authors,
            "online_now": online_now,
            "active_24h": active_24h,
            "duel_rooms_now": duel_rooms_now,
            "duel_players_now": duel_players_now,
            "duel_finished_total": duel_finished_total,
            "total_collection_value": total_collection_value,
            "richest_profile": richest_profile,
            "top_collection": top_collection,
            "scared_cat_minted": scared_cat_minted,
            "market_active_lots": market_active_lots,
            "market_total_deals": market_total_deals,
            "market_total_volume": market_total_volume,
            "shop_purchases_cnt": shop_purchases_cnt,
            "shop_total_xtr": shop_total_xtr,
            "total_cases_opened": total_cases_opened,
            "active_giveaways": active_giveaways,
            "eco_issued": eco_issued,
            "eco_spent": eco_spent,
            "eco_burned": eco_burned,
            "eco_purchased": eco_purchased,
            "eco_total_turnover": eco_total_turnover,
        }
    finally:
        conn.close()

def is_maintenance_mode() -> bool:
    return get_bot_setting("maintenance_mode", "0") == "1"

def set_maintenance_mode(enabled: bool) -> None:
    set_bot_setting("maintenance_mode", "1" if enabled else "0")

def hash_check_password(password: str, code: str = "") -> str:
    return hashlib.sha256(f"{code}:{password}".encode("utf-8")).hexdigest()

def create_bot_star_check(
    creator_id: int,
    total_amount: int,
    target_username: str = "",
    max_claims: int = 1,
    password: str = "",
) -> Tuple[bool, str, Optional[sqlite3.Row], int]:
    """Создаёт активный чек внутри бота (1 или N активаций, опциональный пароль), резервируя ровную сумму."""
    norm_target = (target_username or "").strip().lstrip("@").lower()
    claims_limit = 1 if norm_target else max(1, int(max_claims))
    total_int = int(total_amount)
    if total_int < CHECK_MIN_STARS:
        return False, f"Минимальная сумма чека — {CHECK_MIN_STARS:,} ⭐.", None, 0

    per_claim = total_int // claims_limit
    if per_claim < 1:
        return False, "Сумма слишком мала для такого количества получателей.", None, 0

    locked_total = per_claim * claims_limit
    remainder = total_int - locked_total
    code = secrets.token_hex(6)
    pwd_clean = (password or "").strip()
    has_pwd = 1 if pwd_clean else 0
    pwd_hash = hash_check_password(pwd_clean, code) if pwd_clean else ""

    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            "UPDATE users SET balance_stars=balance_stars-? WHERE user_id=? AND balance_stars>=?",
            (locked_total, creator_id, locked_total),
        )
        if cur.rowcount != 1:
            conn.rollback()
            return False, f"Недостаточно Stars на балансе! Нужно {locked_total:,} ⭐.", None, 0

        conn.execute(
            "INSERT INTO star_checks "
            "(code, creator_id, amount_stars, target_username, status, rendered, created_ts, "
            "max_claims, claimed_count, per_claim_stars, password_hash, has_password) "
            "VALUES (?, ?, ?, ?, 'active', 1, ?, ?, 0, ?, ?, ?)",
            (code, creator_id, locked_total, norm_target, int(time.time()), claims_limit, per_claim, pwd_hash, has_pwd),
        )
        row = conn.execute("SELECT * FROM star_checks WHERE code=?", (code,)).fetchone()
        record_star_flow(spent=locked_total, conn=conn)
        conn.commit()
        return True, "OK", row, remainder
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Ошибка создания чека: {e}", None, 0
    finally:
        conn.close()

def create_star_check_draft(creator_id: int, amount_stars: int, target_username: str = "") -> str:
    code = secrets.token_hex(6)
    norm_target = (target_username or "").strip().lstrip("@").lower()
    conn = db_connect()
    try:
        conn.execute(
            "INSERT INTO star_checks "
            "(code, creator_id, amount_stars, target_username, status, created_ts, max_claims, claimed_count, per_claim_stars) "
            "VALUES (?, ?, ?, ?, 'draft', ?, 1, 0, ?)",
            (code, creator_id, int(amount_stars), norm_target, int(time.time()), int(amount_stars)),
        )
        conn.commit()
        return code
    finally:
        conn.close()

def get_star_check(code: str) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute("SELECT * FROM star_checks WHERE code=?", (code,)).fetchone()
    finally:
        conn.close()

def get_user_active_checks(creator_id: int) -> list[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute(
            "SELECT * FROM star_checks WHERE creator_id=? AND status='active' AND claimed_count < max_claims ORDER BY id DESC",
            (creator_id,),
        ).fetchall()
    finally:
        conn.close()

def set_star_check_inline_msg_id(code: str, inline_message_id: str) -> None:
    if not inline_message_id:
        return
    conn = db_connect()
    try:
        conn.execute("UPDATE star_checks SET inline_message_id=? WHERE code=?", (inline_message_id, code))
        conn.commit()
    finally:
        conn.close()

def cancel_star_check_db(code: str, creator_id: int) -> Tuple[bool, str, int]:
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        chk = conn.execute("SELECT * FROM star_checks WHERE code=? AND creator_id=?", (code, creator_id)).fetchone()
        if not chk:
            conn.rollback()
            return False, "Чек не найден.", 0
        if chk["status"] != "active":
            conn.rollback()
            return False, "Чек уже завершён или отменён.", 0
        per_claim = int(chk["per_claim_stars"] or chk["amount_stars"])
        rem_slots = max(0, int(chk["max_claims"] or 1) - int(chk["claimed_count"] or 0))
        refund = rem_slots * per_claim
        conn.execute("UPDATE star_checks SET status='cancelled' WHERE id=?", (chk["id"],))
        if refund > 0:
            conn.execute("UPDATE users SET balance_stars=balance_stars+? WHERE user_id=?", (refund, creator_id))
        conn.commit()
        return True, "OK", refund
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Ошибка отмены чека: {e}", 0
    finally:
        conn.close()

def mark_star_check_rendered(code: str) -> None:
    conn = db_connect()
    try:
        conn.execute("UPDATE star_checks SET rendered=1 WHERE code=?", (code,))
        conn.commit()
    finally:
        conn.close()

def activate_star_check_draft(code: str, creator_id: int) -> Tuple[bool, str, Optional[sqlite3.Row]]:
    """Резервирует (списывает) звёзды создателя в момент отправки инлайн-чека."""
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        chk = conn.execute("SELECT * FROM star_checks WHERE code=?", (code,)).fetchone()
        if not chk:
            conn.rollback()
            return False, "Чек не найден.", None
        if chk["creator_id"] != creator_id:
            conn.rollback()
            return False, "Нет доступа.", chk
        if chk["status"] == "active":
            conn.commit()
            return True, "OK", chk
        if chk["status"] != "draft":
            conn.commit()
            return False, "Чек уже использован или отменён.", chk

        cur = conn.execute(
            "UPDATE users SET balance_stars=balance_stars-? WHERE user_id=? AND balance_stars>=?",
            (chk["amount_stars"], creator_id, chk["amount_stars"]),
        )
        if cur.rowcount != 1:
            conn.execute("UPDATE star_checks SET status='cancelled' WHERE id=?", (chk["id"],))
            conn.commit()
            return False, "Недостаточно Stars на балансе отправителя.", chk

        conn.execute("UPDATE star_checks SET status='active' WHERE id=?", (chk["id"],))
        record_star_flow(spent=int(chk["amount_stars"] or 0), conn=conn)
        updated = conn.execute("SELECT * FROM star_checks WHERE id=?", (chk["id"],)).fetchone()
        conn.commit()
        return True, "OK", updated
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Ошибка активации: {e}", None
    finally:
        conn.close()

def claim_star_check_db(
    code: str,
    claimer_id: int,
    claimer_username: str,
    password_attempt: Optional[str] = None,
) -> Tuple[bool, str, Optional[sqlite3.Row]]:
    """Атомарно активирует чек (с поддержкой мульти-активаций и пароля) и зачисляет звёзды получателю."""
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        chk = conn.execute("SELECT * FROM star_checks WHERE code=?", (code,)).fetchone()
        if not chk:
            conn.rollback()
            return False, "Чек не найден.", None

        status = chk["status"]
        if status == "claimed":
            conn.rollback()
            return False, "Этот чек уже полностью активирован!", chk
        if status == "cancelled":
            conn.rollback()
            return False, "Этот чек отменён или просрочен.", chk

        max_claims = max(1, int(chk["max_claims"] or 1))
        claimed_count = int(chk["claimed_count"] or 0)
        if claimed_count >= max_claims:
            conn.execute("UPDATE star_checks SET status='claimed' WHERE id=?", (chk["id"],))
            conn.commit()
            return False, "Все активации этого чека уже разобраны!", chk

        target_uname = (chk["target_username"] or "").strip().lstrip("@").lower()
        cur_uname = (claimer_username or "").strip().lstrip("@").lower()
        if target_uname:
            is_target = bool(cur_uname and cur_uname == target_uname)
            if not is_target:
                conn.rollback()
                return False, f"Этот чек предназначен только для @{target_uname}!", chk

        already = conn.execute(
            "SELECT 1 FROM star_check_claims WHERE check_id=? AND user_id=?",
            (chk["id"], claimer_id),
        ).fetchone()
        if already:
            conn.rollback()
            return False, "Вы уже получили свою долю из этого чека!", chk

        if chk["has_password"]:
            if password_attempt is None:
                conn.rollback()
                return False, "NEED_PASSWORD", chk
            if hash_check_password(password_attempt.strip(), code) != chk["password_hash"]:
                conn.rollback()
                return False, "Неверный пароль! Попробуйте снова.", chk

        per_claim = int(chk["per_claim_stars"] or chk["amount_stars"])
        if status == "draft":
            ded = conn.execute(
                "UPDATE users SET balance_stars=balance_stars-? WHERE user_id=? AND balance_stars>=?",
                (chk["amount_stars"], chk["creator_id"], chk["amount_stars"]),
            )
            if ded.rowcount != 1:
                conn.execute("UPDATE star_checks SET status='cancelled' WHERE id=?", (chk["id"],))
                conn.commit()
                return False, "У отправителя недостаточно Stars для оплаты этого чека.", chk
            record_star_flow(spent=int(chk["amount_stars"] or 0), conn=conn)
        elif status != "active":
            conn.rollback()
            return False, "Чек недоступен.", chk

        now = int(time.time())
        new_count = claimed_count + 1
        new_status = "claimed" if new_count >= max_claims else "active"
        upd = conn.execute(
            "UPDATE star_checks SET status=?, claimed_by=?, claimed_ts=?, claimed_count=? "
            "WHERE id=? AND status IN ('draft', 'active') AND claimed_count=?",
            (new_status, claimer_id, now, new_count, chk["id"], claimed_count),
        )
        if upd.rowcount != 1:
            conn.rollback()
            return False, "Чек изменился, попробуйте ещё раз!", chk

        conn.execute(
            "INSERT INTO star_check_claims (check_id, user_id, amount_stars, claimed_ts) VALUES (?, ?, ?, ?)",
            (chk["id"], claimer_id, per_claim, now),
        )
        conn.execute(
            "UPDATE users SET balance_stars=balance_stars+? WHERE user_id=?",
            (per_claim, claimer_id),
        )
        updated = conn.execute("SELECT * FROM star_checks WHERE id=?", (chk["id"],)).fetchone()
        conn.commit()
        return True, "OK", updated
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Ошибка активации чека: {e}", None
    finally:
        conn.close()

MAINTENANCE_MESSAGE = (
    "🛠 <b>Бот сейчас на техработах.</b>\n\n"
    "Подождите немного и попробуйте позже."
)

def get_next_global_id(entity_type: str = "entity") -> int:
    conn = db_connect()
    try:
        cur = conn.execute("INSERT INTO global_id_seq (entity_type) VALUES (?)", (entity_type,))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def get_or_create_user(user_id: int, username: str, first_name: str) -> sqlite3.Row:
    conn = db_connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row is None:
            sys_id = get_next_global_id("user")
            conn.execute(
                "INSERT INTO users (id_num, user_id, username, first_name, xp, max_inventory) VALUES (?, ?, ?, ?, 0, 25)",
                (sys_id, user_id, username or "", first_name or ""),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        else:
            if username or first_name:
                conn.execute(
                    "UPDATE users SET username=?, first_name=? WHERE user_id=?",
                    (username or row["username"] or "", first_name or row["first_name"] or "", user_id),
                )
                conn.commit()
                row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return row
    finally:
        conn.close()

def has_accepted_privacy(user_id: int) -> bool:
    conn = db_connect()
    try:
        row = conn.execute("SELECT privacy_accepted FROM users WHERE user_id=?", (user_id,)).fetchone()
        return bool(row and row["privacy_accepted"])
    except Exception:
        return False
    finally:
        conn.close()

def accept_privacy_policy_db(user_id: int) -> None:
    conn = db_connect()
    try:
        conn.execute(
            "UPDATE users SET privacy_accepted=1, privacy_accepted_ts=? WHERE user_id=?",
            (int(time.time()), user_id),
        )
        conn.commit()
    finally:
        conn.close()

def has_completed_onboarding(user_id: int) -> bool:
    conn = db_connect()
    try:
        row = conn.execute("SELECT onboarding_done FROM users WHERE user_id=?", (user_id,)).fetchone()
        return bool(row and row["onboarding_done"])
    except Exception:
        return True
    finally:
        conn.close()

def set_onboarding_done(user_id: int) -> None:
    conn = db_connect()
    try:
        conn.execute("UPDATE users SET onboarding_done=1 WHERE user_id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()

def has_channel_prompt_done(user_id: int) -> bool:
    conn = db_connect()
    try:
        row = conn.execute("SELECT channel_prompt_done FROM users WHERE user_id=?", (user_id,)).fetchone()
        return bool(row and row["channel_prompt_done"])
    except Exception:
        return True
    finally:
        conn.close()

def mark_channel_prompt_done(user_id: int) -> None:
    conn = db_connect()
    try:
        conn.execute("UPDATE users SET channel_prompt_done=1 WHERE user_id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()

def sync_user_start_timer(user_id: int) -> Tuple[bool, int]:
    """Синхронизирует новый стартовый таймер только в момент нажатия /start."""
    now = int(time.time())
    conn = db_connect()
    try:
        row = conn.execute("SELECT start_timer_ts FROM users WHERE user_id=?", (user_id,)).fetchone()
        prev_ts = int(row["start_timer_ts"] or 0) if row else 0
        just_synced = (prev_ts == 0)
        new_ts = now if just_synced else prev_ts
        conn.execute(
            "UPDATE users SET start_timer_ts=?, last_start_ts=? WHERE user_id=?",
            (new_ts, now, user_id),
        )
        conn.commit()
        return just_synced, new_ts
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# РЕФЕРАЛЬНАЯ СИСТЕМА (БД И ПРОВЕРКИ)
# ---------------------------------------------------------------------------

def get_user_row_raw(user_id: int) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    finally:
        conn.close()

def mark_user_bot_started(user_id: int) -> None:
    conn = db_connect()
    try:
        conn.execute("UPDATE users SET bot_started=1 WHERE user_id=? AND bot_started=0", (user_id,))
        conn.commit()
    finally:
        conn.close()

def activate_referral_system_db(user_id: int) -> Tuple[bool, str, sqlite3.Row]:
    """Бесплатно активирует реферальную систему для пользователя и выдаёт уникальный код."""
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            conn.rollback()
            raise RuntimeError("Пользователь не найден")

        existing_code = (row["referral_code"] or "").strip()
        if row["referral_active"] and existing_code:
            conn.commit()
            return False, existing_code, row

        code = existing_code
        if not code:
            for _ in range(10):
                cand = secrets.token_hex(5)
                dup = conn.execute("SELECT 1 FROM users WHERE referral_code=?", (cand,)).fetchone()
                if not dup:
                    code = cand
                    break
            if not code:
                code = f"u{user_id}"

        now = int(time.time())
        conn.execute(
            "UPDATE users SET referral_active=1, "
            "referral_activated_ts=CASE WHEN referral_activated_ts=0 THEN ? ELSE referral_activated_ts END, "
            "referral_code=? WHERE user_id=?",
            (now, code, user_id),
        )
        updated = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        conn.commit()
        firebase_manager.schedule_sync()
        return True, code, updated
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        conn.close()

def bind_pending_referral_db(referred_user_id: int, ref_code: str) -> Tuple[bool, str, Optional[int]]:
    """
    Привязывает нового пользователя к пригласившему (статус pending).
    Засчитываются ТОЛЬКО новые пользователи, которые ещё не запускали бота и не принимали соглашение.
    """
    clean_code = (ref_code or "").strip()
    if not clean_code or not re.fullmatch(r"[A-Za-z0-9_]{1,40}", clean_code):
        return False, "invalid_code", None

    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        ref_user = conn.execute(
            "SELECT user_id, referral_active, is_banned, ban_until_ts FROM users WHERE referral_code=?",
            (clean_code,),
        ).fetchone()
        if not ref_user and clean_code.isdigit():
            ref_user = conn.execute(
                "SELECT user_id, referral_active, is_banned, ban_until_ts FROM users WHERE user_id=?",
                (int(clean_code),),
            ).fetchone()

        if not ref_user:
            conn.rollback()
            return False, "not_found", None

        referrer_id = int(ref_user["user_id"])
        if referrer_id == referred_user_id:
            conn.rollback()
            return False, "self_referral", None

        if not ref_user["referral_active"]:
            conn.rollback()
            return False, "not_active", None

        now = int(time.time())
        if ref_user["is_banned"] and (ref_user["ban_until_ts"] == 0 or ref_user["ban_until_ts"] > now):
            conn.rollback()
            return False, "referrer_banned", None

        target = conn.execute("SELECT * FROM users WHERE user_id=?", (referred_user_id,)).fetchone()
        if not target:
            conn.rollback()
            return False, "no_target", None

        if target["privacy_accepted"] or target["bot_started"] or target["referred_by"] is not None:
            conn.rollback()
            return False, "already_registered", None

        if int(target["xp"] or 0) > 0 or int(target["total_drops"] or 0) > 0 or int(target["balance_stars"] or 0) > 0:
            conn.rollback()
            return False, "not_new_user", None

        already_ref = conn.execute(
            "SELECT 1 FROM referrals WHERE referred_user_id=?",
            (referred_user_id,),
        ).fetchone()
        if already_ref:
            conn.rollback()
            return False, "already_bound", None

        cur = conn.execute(
            "UPDATE users SET referred_by=?, bot_started=1 "
            "WHERE user_id=? AND referred_by IS NULL AND privacy_accepted=0 AND bot_started=0",
            (referrer_id, referred_user_id),
        )
        if cur.rowcount != 1:
            conn.rollback()
            return False, "already_bound", None

        conn.execute(
            "INSERT INTO referrals (referrer_id, referred_user_id, reward_stars, status, created_ts) "
            "VALUES (?, ?, 0, 'pending', ?)",
            (referrer_id, referred_user_id, now),
        )
        conn.commit()
        return True, "bound", referrer_id
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        log.warning("bind_pending_referral_db error: %s", e)
        return False, "error", None
    finally:
        conn.close()

def claim_referral_reward_on_privacy_accept_db(referred_user_id: int) -> Tuple[bool, Optional[int], int, int, int]:
    """
    Атомарно начисляет 100,000 ⭐ пригласившему после того, как новый реферал
    нажал «Старт» и принял пользовательское соглашение.
    """
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        u = conn.execute(
            "SELECT user_id, referred_by, referral_rewarded, privacy_accepted FROM users WHERE user_id=?",
            (referred_user_id,),
        ).fetchone()
        if not u or not u["referred_by"] or u["referral_rewarded"]:
            conn.rollback()
            return False, None, 0, 0, 0

        referrer_id = int(u["referred_by"])
        if referrer_id == referred_user_id:
            conn.rollback()
            return False, None, 0, 0, 0

        ref_row = conn.execute(
            "SELECT * FROM referrals WHERE referred_user_id=? AND referrer_id=? AND status='pending'",
            (referred_user_id, referrer_id),
        ).fetchone()
        if not ref_row:
            conn.rollback()
            return False, None, 0, 0, 0

        referrer = conn.execute(
            "SELECT user_id, referral_active, is_banned, ban_until_ts FROM users WHERE user_id=?",
            (referrer_id,),
        ).fetchone()
        now = int(time.time())
        if not referrer or not referrer["referral_active"]:
            conn.rollback()
            return False, None, 0, 0, 0
        if referrer["is_banned"] and (referrer["ban_until_ts"] == 0 or referrer["ban_until_ts"] > now):
            conn.rollback()
            return False, None, 0, 0, 0

        upd_u = conn.execute(
            "UPDATE users SET referral_rewarded=1 WHERE user_id=? AND referral_rewarded=0",
            (referred_user_id,),
        )
        if upd_u.rowcount != 1:
            conn.rollback()
            return False, None, 0, 0, 0

        upd_r = conn.execute(
            "UPDATE referrals SET status='rewarded', reward_stars=?, rewarded_ts=? "
            "WHERE id=? AND status='pending'",
            (REFERRAL_REWARD_STARS, now, ref_row["id"]),
        )
        if upd_r.rowcount != 1:
            conn.rollback()
            return False, None, 0, 0, 0

        conn.execute(
            "UPDATE users SET balance_stars=balance_stars+?, "
            "referral_count=referral_count+1, referral_earned_stars=referral_earned_stars+? "
            "WHERE user_id=?",
            (REFERRAL_REWARD_STARS, REFERRAL_REWARD_STARS, referrer_id),
        )
        record_star_flow(issued=REFERRAL_REWARD_STARS, conn=conn)
        ref_stats = conn.execute(
            "SELECT referral_count, referral_earned_stars FROM users WHERE user_id=?",
            (referrer_id,),
        ).fetchone()
        conn.commit()
        firebase_manager.schedule_sync()
        return (
            True,
            referrer_id,
            REFERRAL_REWARD_STARS,
            int(ref_stats["referral_count"] or 0) if ref_stats else 1,
            int(ref_stats["referral_earned_stars"] or 0) if ref_stats else REFERRAL_REWARD_STARS,
        )
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        log.warning("claim_referral_reward_on_privacy_accept_db error: %s", e)
        return False, None, 0, 0, 0
    finally:
        conn.close()

def get_referral_stats_db(referrer_id: int) -> Tuple[int, int, int]:
    """Возвращает (rewarded_count, pending_count, total_earned_stars)."""
    conn = db_connect()
    try:
        row = conn.execute(
            "SELECT "
            "COALESCE(SUM(CASE WHEN status='rewarded' THEN 1 ELSE 0 END), 0) AS rewarded_cnt, "
            "COALESCE(SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END), 0) AS pending_cnt, "
            "COALESCE(SUM(CASE WHEN status='rewarded' THEN reward_stars ELSE 0 END), 0) AS earned_sum "
            "FROM referrals WHERE referrer_id=?",
            (referrer_id,),
        ).fetchone()
        if not row:
            return 0, 0, 0
        return int(row["rewarded_cnt"]), int(row["pending_cnt"]), int(row["earned_sum"])
    finally:
        conn.close()

def get_referrals_page_db(referrer_id: int, page: int = 1, page_size: int = 10) -> Tuple[list[sqlite3.Row], int]:
    conn = db_connect()
    try:
        total = conn.execute(
            "SELECT COUNT(*) AS cnt FROM referrals WHERE referrer_id=?",
            (referrer_id,),
        ).fetchone()["cnt"]
        offset = max(0, (page - 1) * page_size)
        rows = conn.execute(
            "SELECT r.*, u.username, u.first_name "
            "FROM referrals r LEFT JOIN users u ON u.user_id = r.referred_user_id "
            "WHERE r.referrer_id=? ORDER BY r.id DESC LIMIT ? OFFSET ?",
            (referrer_id, page_size, offset),
        ).fetchall()
        return rows, int(total)
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# СИСТЕМА АВТОРСТВА И РОЗЫГРЫШЕЙ (БД И ПРОВЕРКИ)
# ---------------------------------------------------------------------------

def get_latest_author_application_db(user_id: int) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute(
            "SELECT * FROM author_applications WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

def get_author_application_by_id_db(app_id: int) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute(
            "SELECT a.*, u.username, u.first_name, u.xp, u.balance_stars, u.total_drops, u.is_author "
            "FROM author_applications a LEFT JOIN users u ON u.user_id = a.user_id WHERE a.id=?",
            (app_id,),
        ).fetchone()
    finally:
        conn.close()

def list_author_applications_db(page: int = 1, page_size: int = 8) -> Tuple[list[sqlite3.Row], int, int]:
    """Возвращает (rows, total_count, pending_count)."""
    conn = db_connect()
    try:
        total = int(conn.execute("SELECT COUNT(*) AS cnt FROM author_applications").fetchone()["cnt"])
        pending_cnt = int(conn.execute("SELECT COUNT(*) AS cnt FROM author_applications WHERE status='pending'").fetchone()["cnt"])
        offset = max(0, (page - 1) * page_size)
        rows = conn.execute(
            "SELECT a.*, u.username, u.first_name, u.xp, u.balance_stars "
            "FROM author_applications a LEFT JOIN users u ON u.user_id = a.user_id "
            "ORDER BY CASE WHEN a.status='pending' THEN 0 ELSE 1 END, a.id DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()
        return rows, total, pending_cnt
    finally:
        conn.close()

def get_pending_author_apps_count_db() -> int:
    conn = db_connect()
    try:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM author_applications WHERE status='pending'").fetchone()
        return int(row["cnt"]) if row else 0
    except Exception:
        return 0
    finally:
        conn.close()

def submit_author_application_db(user_id: int, channels_text: str, age_text: str) -> Tuple[bool, str, Optional[sqlite3.Row]]:
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        u = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not u:
            conn.rollback()
            return False, "Пользователь не найден.", None
        if u["is_author"]:
            conn.rollback()
            return False, "Вы уже являетесь автором!", None
        lvl, _, _, _ = calculate_xp_level_info(u["xp"])
        if lvl < AUTHOR_MIN_LEVEL:
            conn.rollback()
            return False, f"Для подачи заявки нужен минимум {AUTHOR_MIN_LEVEL}-й уровень (у вас {lvl}).", None
        if int(u["balance_stars"] or 0) < AUTHOR_MIN_BALANCE:
            conn.rollback()
            return False, f"Для подачи заявки баланс должен быть от {AUTHOR_MIN_BALANCE:,} ⭐.", None
        dup = conn.execute(
            "SELECT id FROM author_applications WHERE user_id=? AND status='pending'",
            (user_id,),
        ).fetchone()
        if dup:
            conn.rollback()
            return False, "Ваша заявка уже находится на рассмотрении!", None

        now = int(time.time())
        cur = conn.execute(
            "INSERT INTO author_applications (user_id, channels_text, age_text, status, created_ts) "
            "VALUES (?, ?, ?, 'pending', ?)",
            (user_id, channels_text.strip(), age_text.strip(), now),
        )
        app_row = conn.execute("SELECT * FROM author_applications WHERE id=?", (cur.lastrowid,)).fetchone()
        conn.commit()
        firebase_manager.schedule_sync()
        return True, "OK", app_row
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Ошибка сохранения заявки: {e}", None
    finally:
        conn.close()

def review_author_application_db(
    app_id: int,
    admin_id: int,
    approve: bool,
    reject_reason: str = "",
) -> Tuple[bool, str, Optional[sqlite3.Row]]:
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        app_row = conn.execute("SELECT * FROM author_applications WHERE id=?", (app_id,)).fetchone()
        if not app_row:
            conn.rollback()
            return False, "Заявка не найдена.", None
        if app_row["status"] != "pending":
            conn.rollback()
            return False, "Эта заявка уже рассмотрена.", app_row

        now = int(time.time())
        new_status = "approved" if approve else "rejected"
        reason_clean = (reject_reason or "").strip() if not approve else ""
        conn.execute(
            "UPDATE author_applications SET status=?, reject_reason=?, reviewed_by=?, reviewed_ts=? WHERE id=?",
            (new_status, reason_clean, admin_id, now, app_id),
        )
        if approve:
            conn.execute("UPDATE users SET is_author=1 WHERE user_id=?", (app_row["user_id"],))
        updated = conn.execute("SELECT * FROM author_applications WHERE id=?", (app_id,)).fetchone()
        conn.commit()
        firebase_manager.schedule_sync()
        return True, "OK", updated
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Ошибка обработки заявки: {e}", None
    finally:
        conn.close()

def transfer_author_balance_db(user_id: int, amount: int, to_author: bool) -> Tuple[bool, str, int, int]:
    """Переводит Stars между основным балансом и авторским балансом."""
    amt = int(amount)
    if amt <= 0:
        return False, "Введите положительную сумму.", 0, 0
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if to_author:
            cur = conn.execute(
                "UPDATE users SET balance_stars=balance_stars-?, author_balance_stars=author_balance_stars+? "
                "WHERE user_id=? AND is_author=1 AND balance_stars>=?",
                (amt, amt, user_id, amt),
            )
            if cur.rowcount != 1:
                conn.rollback()
                return False, f"Недостаточно Stars на основном балансе (нужно {amt:,} ⭐).", 0, 0
        else:
            cur = conn.execute(
                "UPDATE users SET author_balance_stars=author_balance_stars-?, balance_stars=balance_stars+? "
                "WHERE user_id=? AND is_author=1 AND author_balance_stars>=?",
                (amt, amt, user_id, amt),
            )
            if cur.rowcount != 1:
                conn.rollback()
                return False, f"Недостаточно Stars на авторском балансе (нужно {amt:,} ⭐).", 0, 0
        row = conn.execute("SELECT balance_stars, author_balance_stars FROM users WHERE user_id=?", (user_id,)).fetchone()
        conn.commit()
        firebase_manager.schedule_sync()
        return True, "OK", int(row["balance_stars"]), int(row["author_balance_stars"])
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Ошибка перевода: {e}", 0, 0
    finally:
        conn.close()

def add_author_balance_admin_db(user_id: int, amount: int) -> Tuple[bool, int]:
    amt = int(amount)
    if amt <= 0:
        return False, 0
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            "UPDATE users SET author_balance_stars=author_balance_stars+? WHERE user_id=?",
            (amt, user_id),
        )
        if cur.rowcount != 1:
            conn.rollback()
            return False, 0
        record_star_flow(issued=amt, conn=conn)
        row = conn.execute("SELECT author_balance_stars FROM users WHERE user_id=?", (user_id,)).fetchone()
        conn.commit()
        firebase_manager.schedule_sync()
        return True, int(row["author_balance_stars"]) if row else amt
    finally:
        conn.close()

def upsert_author_channel_db(
    author_id: int,
    chat_id: int,
    username: str,
    title: str,
    chat_type: str,
) -> sqlite3.Row:
    conn = db_connect()
    try:
        now = int(time.time())
        uname = (username or "").strip().lstrip("@")
        conn.execute(
            "INSERT INTO author_channels (author_id, chat_id, username, title, chat_type, verified, created_ts) "
            "VALUES (?, ?, ?, ?, ?, 1, ?) "
            "ON CONFLICT(author_id, chat_id) DO UPDATE SET username=excluded.username, title=excluded.title, chat_type=excluded.chat_type, verified=1",
            (author_id, int(chat_id), uname, (title or "").strip(), (chat_type or "channel"), now),
        )
        row = conn.execute(
            "SELECT * FROM author_channels WHERE author_id=? AND chat_id=?",
            (author_id, int(chat_id)),
        ).fetchone()
        conn.commit()
        firebase_manager.schedule_sync()
        return row
    finally:
        conn.close()

def get_author_channels_db(author_id: int) -> list[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute(
            "SELECT * FROM author_channels WHERE author_id=? ORDER BY id DESC",
            (author_id,),
        ).fetchall()
    finally:
        conn.close()

def delete_author_channel_db(author_id: int, ch_row_id: int) -> bool:
    conn = db_connect()
    try:
        cur = conn.execute("DELETE FROM author_channels WHERE id=? AND author_id=?", (ch_row_id, author_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def create_giveaway_db(
    author_id: int,
    channels: list[dict],
    text_html: str,
    photo_file_id: str,
    winners_count: int,
    total_prize_stars: int,
    btn_text: str,
    btn_style: str,
    btn_mode: str,
    max_participants: int,
    publish_ts: int,
    end_ts: int,
) -> Tuple[bool, str, Optional[sqlite3.Row]]:
    winners_c = max(1, int(winners_count))
    total_p = int(total_prize_stars)
    per_w = total_p // winners_c
    if per_w < 1:
        return False, "Приз на одного победителя должен быть не менее 1 ⭐.", None
    locked_total = per_w * winners_c
    if not channels:
        return False, "Выберите хотя бы один канал или чат.", None

    now = int(time.time())
    pub_ts = int(publish_ts or 0)
    status = "scheduled" if pub_ts > now else "active"
    code = f"gw{secrets.token_hex(4)}"

    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            "UPDATE users SET author_balance_stars=author_balance_stars-? "
            "WHERE user_id=? AND is_author=1 AND author_balance_stars>=?",
            (locked_total, author_id, locked_total),
        )
        if cur.rowcount != 1:
            conn.rollback()
            return False, f"Недостаточно Stars на авторском балансе! Нужно {locked_total:,} ⭐.", None

        c_ins = conn.execute(
            "INSERT INTO giveaways ("
            "code, author_id, channels_json, text_html, photo_file_id, winners_count, "
            "total_prize_stars, per_winner_stars, btn_text, btn_style, btn_mode, "
            "max_participants, publish_ts, end_ts, status, deducted_from_author, created_ts"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (
                code, author_id, json.dumps(channels, ensure_ascii=False), text_html, photo_file_id or "",
                winners_c, locked_total, per_w, (btn_text or "Участвовать")[:40],
                (btn_style or "success"), (btn_mode or "button"),
                max(0, int(max_participants or 0)), pub_ts, max(0, int(end_ts or 0)),
                status, now,
            ),
        )
        gw_row = conn.execute("SELECT * FROM giveaways WHERE id=?", (c_ins.lastrowid,)).fetchone()
        record_star_flow(spent=locked_total, conn=conn)
        conn.commit()
        firebase_manager.schedule_sync()
        return True, "OK", gw_row
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Ошибка создания конкурса: {e}", None
    finally:
        conn.close()

def get_giveaway_by_id_db(gw_id: int) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute("SELECT * FROM giveaways WHERE id=?", (gw_id,)).fetchone()
    finally:
        conn.close()

def get_giveaway_by_code_db(code: str) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute("SELECT * FROM giveaways WHERE code=?", (code,)).fetchone()
    finally:
        conn.close()

def get_author_giveaways_db(author_id: int, page: int = 1, page_size: int = 6) -> Tuple[list[sqlite3.Row], int]:
    conn = db_connect()
    try:
        total = int(conn.execute("SELECT COUNT(*) AS cnt FROM giveaways WHERE author_id=?", (author_id,)).fetchone()["cnt"])
        offset = max(0, (page - 1) * page_size)
        rows = conn.execute(
            "SELECT * FROM giveaways WHERE author_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (author_id, page_size, offset),
        ).fetchall()
        return rows, total
    finally:
        conn.close()

def set_giveaway_posted_messages_db(gw_id: int, posted: list[dict], new_status: str = "active") -> None:
    conn = db_connect()
    try:
        conn.execute(
            "UPDATE giveaways SET posted_messages_json=?, status=? WHERE id=?",
            (json.dumps(posted, ensure_ascii=False), new_status, gw_id),
        )
        conn.commit()
        firebase_manager.schedule_sync()
    finally:
        conn.close()

def get_giveaway_participants_count_db(gw_id: int) -> int:
    conn = db_connect()
    try:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM giveaway_participants WHERE giveaway_id=?", (gw_id,)).fetchone()
        return int(row["cnt"]) if row else 0
    finally:
        conn.close()

def join_giveaway_db(gw_id: int, user_id: int) -> Tuple[bool, str, int, bool]:
    """Регистрирует участника. Возвращает (ok, msg, participants_count, reached_max)."""
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        gw = conn.execute("SELECT * FROM giveaways WHERE id=?", (gw_id,)).fetchone()
        if not gw:
            conn.rollback()
            return False, "Конкурс не найден.", 0, False
        if gw["status"] != "active":
            conn.rollback()
            return False, "Этот конкурс уже завершён или ещё не начался.", 0, False
        now = int(time.time())
        if gw["end_ts"] and now >= int(gw["end_ts"]):
            conn.rollback()
            return False, "Время приёма заявок на этот конкурс истекло.", 0, False

        dup = conn.execute(
            "SELECT 1 FROM giveaway_participants WHERE giveaway_id=? AND user_id=?",
            (gw_id, user_id),
        ).fetchone()
        if dup:
            cnt = int(conn.execute("SELECT COUNT(*) AS cnt FROM giveaway_participants WHERE giveaway_id=?", (gw_id,)).fetchone()["cnt"])
            conn.rollback()
            return False, "Вы уже участвуете в этом конкурсе!", cnt, False

        cur_cnt = int(conn.execute("SELECT COUNT(*) AS cnt FROM giveaway_participants WHERE giveaway_id=?", (gw_id,)).fetchone()["cnt"])
        max_p = int(gw["max_participants"] or 0)
        if max_p > 0 and cur_cnt >= max_p:
            conn.rollback()
            return False, "Достигнут лимит участников конкурса!", cur_cnt, True

        conn.execute(
            "INSERT INTO giveaway_participants (giveaway_id, user_id, joined_ts) VALUES (?, ?, ?)",
            (gw_id, user_id, now),
        )
        new_cnt = cur_cnt + 1
        reached_max = (max_p > 0 and new_cnt >= max_p)
        conn.commit()
        return True, "OK", new_cnt, reached_max
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Ошибка участия: {e}", 0, False
    finally:
        conn.close()

def cancel_scheduled_giveaway_db(gw_id: int, author_id: int) -> Tuple[bool, str, int]:
    """Отменяет ещё не опубликованный конкурс и возвращает звёзды на авторский баланс."""
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        gw = conn.execute("SELECT * FROM giveaways WHERE id=? AND author_id=?", (gw_id, author_id)).fetchone()
        if not gw:
            conn.rollback()
            return False, "Конкурс не найден.", 0
        if gw["status"] != "scheduled":
            conn.rollback()
            return False, "Можно отменить только запланированный конкурс до публикации.", 0
        refund = int(gw["total_prize_stars"] or 0)
        conn.execute("UPDATE giveaways SET status='cancelled', finished_ts=? WHERE id=?", (int(time.time()), gw_id))
        if refund > 0:
            conn.execute("UPDATE users SET author_balance_stars=author_balance_stars+? WHERE user_id=?", (refund, author_id))
        conn.commit()
        firebase_manager.schedule_sync()
        return True, "OK", refund
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Ошибка отмены: {e}", 0
    finally:
        conn.close()

def finalize_giveaway_db(gw_id: int) -> Tuple[bool, Optional[sqlite3.Row], list[dict], int]:
    """
    Атомарно завершает активный конкурс, выбирает случайных победителей,
    начисляет звёзды победителям и формирует официальные чеки (auto-claimed star_checks).
    Возвращает (ok, gw_row, winners_info_list, refunded_to_author).
    """
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        gw = conn.execute("SELECT * FROM giveaways WHERE id=?", (gw_id,)).fetchone()
        if not gw or gw["status"] != "active":
            conn.rollback()
            return False, gw, [], 0

        parts = conn.execute(
            "SELECT gp.user_id, u.username, u.first_name "
            "FROM giveaway_participants gp LEFT JOIN users u ON u.user_id = gp.user_id "
            "WHERE gp.giveaway_id=?",
            (gw_id,),
        ).fetchall()

        now = int(time.time())
        per_w = int(gw["per_winner_stars"] or 0)
        total_locked = int(gw["total_prize_stars"] or 0)
        winners_limit = max(1, int(gw["winners_count"] or 1))
        author_id = int(gw["author_id"])

        winners_info: list[dict] = []
        paid_total = 0

        if parts:
            pick_count = min(winners_limit, len(parts))
            chosen_rows = random.sample(list(parts), k=pick_count)
            for p_row in chosen_rows:
                w_uid = int(p_row["user_id"])
                w_uname = (p_row["username"] or "").strip()
                w_fname = (p_row["first_name"] or "").strip()
                chk_code = f"gw_{secrets.token_hex(5)}"
                if per_w > 0:
                    conn.execute(
                        "UPDATE users SET balance_stars=balance_stars+? WHERE user_id=?",
                        (per_w, w_uid),
                    )
                    c_chk = conn.execute(
                        "INSERT INTO star_checks "
                        "(code, creator_id, amount_stars, target_username, target_user_id, status, claimed_by, rendered, "
                        "created_ts, claimed_ts, max_claims, claimed_count, per_claim_stars, has_password) "
                        "VALUES (?, ?, ?, ?, ?, 'claimed', ?, 1, ?, ?, 1, 1, ?, 0)",
                        (chk_code, author_id, per_w, w_uname.lower(), w_uid, w_uid, now, now, per_w),
                    )
                    conn.execute(
                        "INSERT INTO star_check_claims (check_id, user_id, amount_stars, claimed_ts) VALUES (?, ?, ?, ?)",
                        (c_chk.lastrowid, w_uid, per_w, now),
                    )
                    paid_total += per_w
                winners_info.append({
                    "user_id": w_uid,
                    "username": w_uname,
                    "first_name": w_fname,
                    "amount_stars": per_w,
                    "check_code": chk_code,
                })

        refund = max(0, total_locked - paid_total)
        if refund > 0:
            conn.execute(
                "UPDATE users SET author_balance_stars=author_balance_stars+? WHERE user_id=?",
                (refund, author_id),
            )

        conn.execute(
            "UPDATE giveaways SET status='finished', winners_json=?, finished_ts=? WHERE id=? AND status='active'",
            (json.dumps(winners_info, ensure_ascii=False), now, gw_id),
        )
        upd_gw = conn.execute("SELECT * FROM giveaways WHERE id=?", (gw_id,)).fetchone()
        conn.commit()
        firebase_manager.schedule_sync()
        return True, upd_gw, winners_info, refund
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        log.error("finalize_giveaway_db(%s) error: %s", gw_id, e)
        return False, None, [], 0
    finally:
        conn.close()

def get_due_scheduled_giveaways_db(now_ts: int) -> list[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute(
            "SELECT * FROM giveaways WHERE status='scheduled' AND publish_ts<=? ORDER BY publish_ts ASC",
            (now_ts,),
        ).fetchall()
    finally:
        conn.close()

def get_due_active_giveaways_db(now_ts: int) -> list[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute(
            "SELECT * FROM giveaways WHERE status='active' AND end_ts>0 AND end_ts<=? ORDER BY end_ts ASC",
            (now_ts,),
        ).fetchall()
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# СИСТЕМА БАНОВ
# ---------------------------------------------------------------------------

def is_user_banned(user_id: int) -> Tuple[bool, int, str, int]:
    conn = db_connect()
    try:
        row = conn.execute("SELECT is_banned, ban_until_ts, ban_reason, ban_hours FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or not row["is_banned"]:
            return False, 0, "", 0

        now = int(time.time())
        until_ts = row["ban_until_ts"]
        if until_ts > 0 and now >= until_ts:
            conn.execute("UPDATE users SET is_banned=0, ban_until_ts=0, ban_reason='', ban_hours=0 WHERE user_id=?", (user_id,))
            conn.commit()
            return False, 0, "", 0

        return True, row["ban_until_ts"], row["ban_reason"], row["ban_hours"]
    finally:
        conn.close()

def ban_user(user_id: int, hours: int, reason: str) -> bool:
    now = int(time.time())
    until_ts = now + (hours * 3600) if hours > 0 else 0
    conn = db_connect()
    try:
        conn.execute(
            "UPDATE users SET is_banned=1, ban_until_ts=?, ban_reason=?, ban_hours=? WHERE user_id=?",
            (until_ts, reason, hours, user_id)
        )
        conn.commit()
        return True
    except Exception as e:
        log.error("Ошибка при бане пользователя: %s", e)
        return False
    finally:
        conn.close()

def unban_user(user_id: int) -> bool:
    conn = db_connect()
    try:
        conn.execute("UPDATE users SET is_banned=0, ban_until_ts=0, ban_reason='', ban_hours=0 WHERE user_id=?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        log.error("Ошибка при разбане пользователя: %s", e)
        return False
    finally:
        conn.close()

def format_ban_message(ban_until_ts: int, ban_reason: str, ban_hours: int) -> Tuple[str, InlineKeyboardMarkup]:
    if ban_until_ts > 0:
        dt_str = datetime.datetime.fromtimestamp(ban_until_ts, tz=datetime.timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
        time_text = f"• Время блокировки: <b>{ban_hours} ч.</b>\n• Заблокирован до: <b>{dt_str}</b>"
    else:
        time_text = "• Время блокировки: <b>Навсегда</b>"

    text = (
        "⛔️ <b>Доступ заблокирован!</b>\n"
        "━━━━━━━━━━━━\n"
        "Вы получили бан в системе бота и не можете использовать команды.\n\n"
        f"{time_text}\n"
        f"• Причина: <b>{clean_html(ban_reason or 'Нарушение правил')}</b>\n"
        "━━━━━━━━━━━━\n"
        f"Если вы считаете блокировку ошибочной, обратитесь в поддержку: {SUPPORT_HANDLE}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Поддержка", url=SUPPORT_URL)]
    ])
    return text, kb

# ---------------------------------------------------------------------------
# ОПЕРАЦИИ С БАЗОЙ ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ
# ---------------------------------------------------------------------------

def set_last_drop(user_id: int, ts: int) -> None:
    conn = db_connect()
    try:
        conn.execute(
            "UPDATE users SET last_drop_ts=?, total_drops=total_drops+1 WHERE user_id=?",
            (ts, user_id),
        )
        conn.commit()
    finally:
        conn.close()

def set_user_background(user_id: int, bg_path: Optional[str]) -> None:
    conn = db_connect()
    try:
        conn.execute("UPDATE users SET bg_image_path=? WHERE user_id=?", (bg_path, user_id))
        if bg_path is None:
            conn.execute("DELETE FROM user_backgrounds WHERE user_id=?", (user_id,))
        conn.commit()
        firebase_manager.schedule_sync()
    finally:
        conn.close()

def add_to_collection(
    user_id: int,
    gift_key: str,
    buff_backdrop_pct: int = 0,
    buff_model_pct: int = 0,
    buff_value_pct: int = 0,
) -> bool:
    g = GIFTS_BY_KEY.get(gift_key)
    add_xp = g.xp if g else 100
    conn = db_connect()
    try:
        user = conn.execute("SELECT max_inventory FROM users WHERE user_id=?", (user_id,)).fetchone()
        count = conn.execute("SELECT COUNT(*) as cnt FROM collection WHERE user_id=?", (user_id,)).fetchone()["cnt"]

        max_inv = user["max_inventory"] if user else 25
        if count >= max_inv:
            return False

        conn.execute(
            "INSERT INTO collection "
            "(user_id, gift_key, obtained_ts, is_favorite, buff_backdrop_pct, buff_model_pct, buff_value_pct) "
            "VALUES (?, ?, ?, 0, ?, ?, ?)",
            (
                user_id,
                gift_key,
                int(time.time()),
                max(0, int(buff_backdrop_pct or 0)),
                max(0, int(buff_model_pct or 0)),
                max(0, int(buff_value_pct or 0)),
            ),
        )
        conn.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (add_xp, user_id))
        conn.commit()
        return True
    finally:
        conn.close()

def get_item_display_value(item: sqlite3.Row) -> int:
    if item["is_upgraded"] and item["upgraded_stars"] > 0:
        return int(item["upgraded_stars"])
    g = GIFTS_BY_KEY.get(item["gift_key"])
    return g.stars if g else 0

def upgrade_collection_item(
    user_id: int,
    item_id: int,
    model_name: str,
    backdrop_key: str,
    upgraded_stars: int,
    cost: Optional[int] = None,
) -> Tuple[bool, str, int]:
    """Списывает Stars (300k Plush Pepe / 200k Heart Locket / 200k Algorithm Cup / 150k Durov's Cap / 150k Bonded Ring) и улучшает подарок."""
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        item = conn.execute("SELECT * FROM collection WHERE id=? AND user_id=?", (item_id, user_id)).fetchone()
        if not item:
            conn.rollback()
            return False, "Подарок не найден в вашей коллекции.", 0
        canon_key = canonical_gift_key(item["gift_key"])
        if canon_key not in UPGRADABLE_GIFT_KEYS:
            conn.rollback()
            return False, "Улучшение доступно для Plush Pepe, Heart Locket, Durov's Cap, Algorithm Cup и Bonded Ring!", 0
        if item["is_upgraded"]:
            conn.rollback()
            return False, "Этот подарок уже улучшен!", 0
        if item["is_listed"]:
            conn.rollback()
            return False, "Сначала снимите подарок с маркета.", 0

        actual_cost = cost if cost is not None else get_upgrade_cost(canon_key)
        user = conn.execute("SELECT balance_stars FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not user or user["balance_stars"] < actual_cost:
            conn.rollback()
            return False, f"Недостаточно Stars! Требуется {actual_cost:,} ⭐.", 0

        max_num_row = conn.execute("SELECT COALESCE(MAX(upgrade_num), 0) AS mx FROM collection").fetchone()
        next_num = int(max_num_row["mx"] or 0) + 1

        conn.execute("UPDATE users SET balance_stars=balance_stars-?, xp=xp+5000 WHERE user_id=?", (actual_cost, user_id))
        conn.execute(
            "UPDATE collection SET gift_key=?, is_upgraded=1, model_name=?, backdrop_key=?, upgraded_stars=?, upgrade_num=? WHERE id=?",
            (canon_key, model_name, backdrop_key, upgraded_stars, next_num, item_id),
        )
        record_star_flow(spent=actual_cost, burned=actual_cost, purchased=actual_cost, conn=conn)
        conn.commit()
        return True, "OK", next_num
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        conn.close()

def admin_grant_upgraded_nft_db(
    target_user_id: int,
    gift_key: str,
    model_name: str,
    backdrop_key: str,
    upgraded_stars: int,
) -> Tuple[bool, str, int, int]:
    """Выдаёт улучшенный NFT напрямую через Админ-панель с глобальной синхронизацией upgrade_num."""
    g = GIFTS_BY_KEY.get(gift_key)
    add_xp = (g.xp if g else 1000) + 5000
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        target = conn.execute("SELECT user_id FROM users WHERE user_id=?", (target_user_id,)).fetchone()
        if not target:
            conn.rollback()
            return False, "Игрок не найден.", 0, 0
        max_num_row = conn.execute("SELECT COALESCE(MAX(upgrade_num), 0) AS mx FROM collection").fetchone()
        next_num = int(max_num_row["mx"] or 0) + 1
        cur = conn.execute(
            "INSERT INTO collection "
            "(user_id, gift_key, obtained_ts, is_favorite, is_upgraded, model_name, backdrop_key, upgraded_stars, upgrade_num, is_listed) "
            "VALUES (?, ?, ?, 0, 1, ?, ?, ?, ?, 0)",
            (target_user_id, gift_key, int(time.time()), model_name, backdrop_key, int(upgraded_stars), next_num),
        )
        conn.execute("UPDATE users SET xp=xp+? WHERE user_id=?", (add_xp, target_user_id))
        conn.commit()
        return True, "OK", next_num, int(cur.lastrowid)
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Ошибка БД: {e}", 0, 0
    finally:
        conn.close()

def transfer_gift_between_users(sender_id: int, receiver_id: int, item_id: int) -> Tuple[bool, str]:
    """Безопасная передача подарка (обычного или улучшенного) от одного игрока другому."""
    conn = db_connect()
    try:
        item = conn.execute("SELECT * FROM collection WHERE id=? AND user_id=?", (item_id, sender_id)).fetchone()
        if not item:
            return False, "Предмет не найден в вашей коллекции."
        if item["is_listed"]:
            return False, "Подарок выставлен на маркете! Сначала снимите лот с продажи."

        recv = conn.execute("SELECT max_inventory FROM users WHERE user_id=?", (receiver_id,)).fetchone()
        if not recv:
            return False, "Получатель не найден."

        recv_count = conn.execute("SELECT COUNT(*) as cnt FROM collection WHERE user_id=?", (receiver_id,)).fetchone()["cnt"]
        if recv_count >= recv["max_inventory"]:
            return False, "У получателя переполнен инвентарь."

        conn.execute(
            "UPDATE collection SET user_id=?, is_favorite=0, obtained_ts=? WHERE id=?",
            (receiver_id, int(time.time()), item_id),
        )
        conn.commit()
        return True, item["gift_key"]
    finally:
        conn.close()

def sell_from_pending(user_id: int, gift_key: str, stars: int) -> None:
    g = GIFTS_BY_KEY.get(gift_key)
    add_xp = (g.xp // 2) if g else 50
    conn = db_connect()
    try:
        conn.execute(
            "UPDATE users SET balance_stars=balance_stars+?, total_sold=total_sold+1, xp=xp+? WHERE user_id=?",
            (stars, add_xp, user_id),
        )
        record_star_flow(issued=stars, conn=conn)
        conn.commit()
    finally:
        conn.close()

def get_user_collection(user_id: int) -> list[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute(
            "SELECT * FROM collection WHERE user_id=? ORDER BY is_upgraded DESC, is_favorite DESC, id DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

def sell_all_non_favorites(user_id: int) -> Tuple[int, int]:
    conn = db_connect()
    try:
        items = conn.execute(
            "SELECT id, gift_key FROM collection "
            "WHERE user_id=? AND is_favorite=0 AND is_upgraded=0 AND is_listed=0 AND gift_key != 'scared_cat'",
            (user_id,),
        ).fetchall()
        if not items:
            return 0, 0

        total_stars = 0
        ids_to_del = []
        for item in items:
            g = GIFTS_BY_KEY.get(item["gift_key"])
            if g:
                total_stars += g.stars
            ids_to_del.append(item["id"])

        conn.executemany("DELETE FROM collection WHERE id=?", [(i,) for i in ids_to_del])
        conn.execute("UPDATE users SET balance_stars=balance_stars+?, total_sold=total_sold+? WHERE user_id=?",
                     (total_stars, len(ids_to_del), user_id))
        record_star_flow(issued=total_stars, conn=conn)
        conn.commit()
        return len(ids_to_del), total_stars
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# АКЦИИ (SCARED CAT), КАПЧА КЕЙСОВ (100+) И ДОНАТ-МАГАЗИН (XTR) — БД
# ---------------------------------------------------------------------------

def get_scared_cat_supply_stats() -> Tuple[int, int]:
    """Возвращает (продано, осталось) для лимитированного Scared Cat (1,000 шт.)."""
    conn = db_connect()
    try:
        row = conn.execute("SELECT value FROM bot_settings WHERE key='scared_cat_minted'").fetchone()
        minted_setting = int(row["value"] or 0) if row else 0
        coll_cnt = int(conn.execute("SELECT COUNT(*) AS cnt FROM collection WHERE gift_key='scared_cat'").fetchone()["cnt"] or 0)
        sold = max(minted_setting, coll_cnt)
        rem = max(0, SCARED_CAT_MAX_SUPPLY - sold)
        return sold, rem
    finally:
        conn.close()

def buy_promo_scared_cat_db(user_id: int) -> Tuple[bool, str, int, int]:
    """Атомарная покупка лимитированного Scared Cat по акции с проверкой лимита 1,000 шт."""
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row_m = conn.execute("SELECT value FROM bot_settings WHERE key='scared_cat_minted'").fetchone()
        minted = int(row_m["value"] or 0) if row_m else 0
        coll_cnt_sc = int(conn.execute("SELECT COUNT(*) AS cnt FROM collection WHERE gift_key='scared_cat'").fetchone()["cnt"] or 0)
        minted = max(minted, coll_cnt_sc)
        if minted >= SCARED_CAT_MAX_SUPPLY:
            conn.rollback()
            return False, "Лимит тиража Scared Cat (1,000 шт.) полностью исчерпан!", 0, 0

        u = conn.execute("SELECT balance_stars, max_inventory FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not u:
            conn.rollback()
            return False, "Профиль не найден.", 0, 0
        if int(u["balance_stars"] or 0) < SCARED_CAT_PROMO_PRICE:
            conn.rollback()
            return False, f"Недостаточно Stars! Требуется {SCARED_CAT_PROMO_PRICE:,} ⭐.", 0, 0

        inv_cnt = int(conn.execute("SELECT COUNT(*) AS cnt FROM collection WHERE user_id=?", (user_id,)).fetchone()["cnt"] or 0)
        if inv_cnt >= int(u["max_inventory"] or 25):
            conn.rollback()
            return False, "Инвентарь переполнен! Освободите место или расширьте слоты.", 0, 0

        new_edition = minted + 1
        now = int(time.time())
        conn.execute(
            "UPDATE users SET balance_stars=balance_stars-?, xp=xp+? WHERE user_id=?",
            (SCARED_CAT_PROMO_PRICE, SCARED_CAT_DEF.xp, user_id),
        )
        cur = conn.execute(
            "INSERT INTO collection (user_id, gift_key, obtained_ts, is_favorite, edition_num) VALUES (?, 'scared_cat', ?, 0, ?)",
            (user_id, now, new_edition),
        )
        conn.execute(
            "INSERT INTO bot_settings (key, value) VALUES ('scared_cat_minted', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(new_edition),),
        )
        record_star_flow(
            spent=SCARED_CAT_PROMO_PRICE,
            burned=SCARED_CAT_PROMO_PRICE,
            purchased=SCARED_CAT_PROMO_PRICE,
            conn=conn,
        )
        conn.commit()
        return True, "OK", new_edition, int(cur.lastrowid)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()

def get_user_case_captcha_state(user_id: int) -> Tuple[int, bool]:
    conn = db_connect()
    try:
        r = conn.execute(
            "SELECT cases_opened_total, cases_captcha_pending FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
        if not r:
            return 0, False
        return int(r["cases_opened_total"] or 0), bool(int(r["cases_captcha_pending"] or 0))
    finally:
        conn.close()

def record_case_opened_check_captcha_db(user_id: int) -> Tuple[int, bool]:
    conn = db_connect()
    try:
        conn.execute("UPDATE users SET cases_opened_total = COALESCE(cases_opened_total, 0) + 1 WHERE user_id=?", (user_id,))
        row = conn.execute("SELECT cases_opened_total FROM users WHERE user_id=?", (user_id,)).fetchone()
        new_total = int(row["cases_opened_total"] or 0) if row else 1
        triggered = (new_total > 0 and new_total % CASE_CAPTCHA_INTERVAL == 0)
        if triggered:
            conn.execute("UPDATE users SET cases_captcha_pending=1 WHERE user_id=?", (user_id,))
        conn.commit()
        return new_total, triggered
    finally:
        conn.close()

def pass_case_captcha_db(user_id: int) -> None:
    conn = db_connect()
    try:
        conn.execute("UPDATE users SET cases_captcha_pending=0 WHERE user_id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()

def fulfill_donate_pack_db(
    user_id: int,
    pack_key: str,
    xtr_amount: int,
    payload: str,
    charge_id: str,
) -> Tuple[bool, str, dict]:
    """Идемпотентно начисляет содержимое купленного за XTR набора, автоматически расширяя слоты."""
    pack = DONATE_PACKS.get(pack_key)
    if not pack:
        return False, "Неизвестный пакет.", {}

    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        dup = conn.execute(
            "SELECT id FROM shop_purchases WHERE telegram_payment_charge_id=?",
            (charge_id,),
        ).fetchone()
        if dup:
            conn.rollback()
            return False, "ALREADY_PROCESSED", {}

        u = conn.execute("SELECT user_id, max_inventory FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not u:
            conn.rollback()
            return False, "Пользователь не найден.", {}

        nfts_spec: list = list(pack.get("nfts") or [])
        cur_inv = int(conn.execute("SELECT COUNT(*) AS cnt FROM collection WHERE user_id=?", (user_id,)).fetchone()["cnt"] or 0)
        max_inv = int(u["max_inventory"] or 25)
        needed_max = max(max_inv, cur_inv + len(nfts_spec))
        slots_added = max(0, needed_max - max_inv)

        stars_rew = int(pack["stars_reward"])
        xp_rew = int(pack["xp_reward"])
        now = int(time.time())

        conn.execute(
            "UPDATE users SET balance_stars=balance_stars+?, xp=xp+?, max_inventory=? WHERE user_id=?",
            (stars_rew, xp_rew, needed_max, user_id),
        )
        for g_key, with_buff in nfts_spec:
            b_bg, b_mdl, b_val = roll_item_buffs() if with_buff else (0, 0, 0)
            conn.execute(
                "INSERT INTO collection "
                "(user_id, gift_key, obtained_ts, is_favorite, buff_backdrop_pct, buff_model_pct, buff_value_pct) "
                "VALUES (?, ?, ?, 0, ?, ?, ?)",
                (user_id, g_key, now, b_bg, b_mdl, b_val),
            )

        conn.execute(
            "INSERT INTO shop_purchases "
            "(user_id, pack_key, xtr_amount, stars_reward, xp_reward, nfts_count, telegram_payment_charge_id, payload, created_ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, pack_key, int(xtr_amount), stars_rew, xp_rew, len(nfts_spec), charge_id, payload, now),
        )
        record_star_flow(issued=stars_rew, conn=conn)
        conn.commit()
        return True, "OK", {
            "title": pack["title"],
            "xtr_amount": int(xtr_amount),
            "stars_reward": stars_rew,
            "xp_reward": xp_rew,
            "nfts_count": len(nfts_spec),
            "slots_added": slots_added,
        }
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()

def toggle_user_setting(user_id: int, field: str) -> bool:
    if field not in ("hide_top", "hide_collection", "auto_sell"):
        return False
    conn = db_connect()
    try:
        row = conn.execute(f"SELECT {field} FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return False
        new_val = 1 if row[field] == 0 else 0
        conn.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (new_val, user_id))
        conn.commit()
        return True
    finally:
        conn.close()

def upgrade_inventory_capacity(user_id: int, cost: int, add_slots: int) -> bool:
    conn = db_connect()
    try:
        row = conn.execute("SELECT balance_stars, max_inventory FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or row["balance_stars"] < cost:
            return False
        conn.execute("UPDATE users SET balance_stars=balance_stars-?, max_inventory=max_inventory+? WHERE user_id=?",
                     (cost, add_slots, user_id))
        record_star_flow(spent=cost, burned=cost, purchased=cost, conn=conn)
        conn.commit()
        return True
    finally:
        conn.close()

def get_collection_item(item_id: int) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute("SELECT * FROM collection WHERE id=?", (item_id,)).fetchone()
    finally:
        conn.close()

def toggle_favorite(item_id: int, user_id: int) -> bool:
    conn = db_connect()
    try:
        item = conn.execute("SELECT * FROM collection WHERE id=? AND user_id=?", (item_id, user_id)).fetchone()
        if not item:
            return False

        if not item["is_favorite"]:
            fav_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM collection WHERE user_id=? AND is_favorite=1",
                (user_id,)
            ).fetchone()["cnt"]
            if fav_count >= 7:
                return False
            conn.execute("UPDATE collection SET is_favorite=1 WHERE id=?", (item_id,))
        else:
            conn.execute("UPDATE collection SET is_favorite=0 WHERE id=?", (item_id,))

        conn.commit()
        return True
    finally:
        conn.close()

def remove_from_collection(item_id: int, user_id: int) -> None:
    conn = db_connect()
    try:
        conn.execute("DELETE FROM collection WHERE id=? AND user_id=? AND is_listed=0", (item_id, user_id))
        conn.commit()
    finally:
        conn.close()

def add_user_stars(user_id: int, stars: int, track_issued: bool = True) -> None:
    conn = db_connect()
    try:
        conn.execute("UPDATE users SET balance_stars=balance_stars+? WHERE user_id=?", (stars, user_id))
        if track_issued and stars > 0:
            record_star_flow(issued=stars, conn=conn)
        conn.commit()
    finally:
        conn.close()

def deduct_user_stars(user_id: int, stars: int) -> bool:
    conn = db_connect()
    try:
        row = conn.execute("SELECT balance_stars FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or row["balance_stars"] < stars:
            return False
        conn.execute("UPDATE users SET balance_stars=balance_stars-? WHERE user_id=?", (stars, user_id))
        conn.commit()
        return True
    finally:
        conn.close()

def claim_daily_bonus(user_id: int) -> Optional[int]:
    conn = db_connect()
    try:
        row = conn.execute("SELECT last_daily_bonus_ts FROM users WHERE user_id=?", (user_id,)).fetchone()
        now = int(time.time())
        day_sec = 24 * 3600
        if row and (now - row["last_daily_bonus_ts"] < day_sec):
            return day_sec - (now - row["last_daily_bonus_ts"])

        conn.execute(
            "UPDATE users SET balance_stars=balance_stars+50, xp=xp+250, last_daily_bonus_ts=? WHERE user_id=?",
            (now, user_id),
        )
        record_star_flow(issued=50, conn=conn)
        conn.commit()
        return None
    finally:
        conn.close()

def get_bonus_status_db(user_id: int) -> dict:
    conn = db_connect()
    try:
        row = conn.execute(
            "SELECT last_daily_bonus_ts, last_name_promo_bonus_ts, last_bio_promo_bonus_ts, "
            "COALESCE(free_10k_cases, 0) AS free_10k_cases FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
        now = int(time.time())
        day_sec = 24 * 3600
        if not row:
            return {"daily_left": 0, "name_left": 0, "bio_left": 0, "free_10k_cases": 0}
        d_left = max(0, day_sec - (now - int(row["last_daily_bonus_ts"] or 0)))
        n_left = max(0, day_sec - (now - int(row["last_name_promo_bonus_ts"] or 0)))
        b_left = max(0, day_sec - (now - int(row["last_bio_promo_bonus_ts"] or 0)))
        return {
            "daily_left": d_left,
            "name_left": n_left,
            "bio_left": b_left,
            "free_10k_cases": max(0, int(row["free_10k_cases"] or 0)),
        }
    finally:
        conn.close()

def claim_promo_profile_bonus_db(user_id: int, has_name_tag: bool, has_bio_tag: bool) -> dict:
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT last_name_promo_bonus_ts, last_bio_promo_bonus_ts, COALESCE(free_10k_cases, 0) AS free_10k_cases "
            "FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
        if not row:
            conn.rollback()
            return {
                "awarded_stars": 0, "awarded_cases": 0,
                "claimed_name": False, "claimed_bio": False,
                "name_left": 0, "bio_left": 0, "total_free_cases": 0,
            }
        now = int(time.time())
        day_sec = 24 * 3600
        last_name = int(row["last_name_promo_bonus_ts"] or 0)
        last_bio = int(row["last_bio_promo_bonus_ts"] or 0)
        name_left = max(0, day_sec - (now - last_name))
        bio_left = max(0, day_sec - (now - last_bio))

        claim_name = bool(has_name_tag and name_left == 0)
        claim_bio = bool(has_bio_tag and bio_left == 0)
        awarded_stars = 0
        awarded_cases = 0
        new_last_name = last_name
        new_last_bio = last_bio

        if claim_name:
            awarded_stars += PROMO_BONUS_STARS
            awarded_cases += 1
            new_last_name = now
            name_left = day_sec
        if claim_bio:
            awarded_stars += PROMO_BONUS_STARS
            awarded_cases += 1
            new_last_bio = now
            bio_left = day_sec

        cur_free = max(0, int(row["free_10k_cases"] or 0))
        if awarded_stars > 0 or awarded_cases > 0:
            conn.execute(
                "UPDATE users SET balance_stars=balance_stars+?, free_10k_cases=COALESCE(free_10k_cases,0)+?, "
                "last_name_promo_bonus_ts=?, last_bio_promo_bonus_ts=? WHERE user_id=?",
                (awarded_stars, awarded_cases, new_last_name, new_last_bio, user_id),
            )
            if awarded_stars > 0:
                record_star_flow(issued=awarded_stars, conn=conn)
            conn.commit()
            cur_free += awarded_cases
        else:
            conn.rollback()

        return {
            "awarded_stars": awarded_stars,
            "awarded_cases": awarded_cases,
            "claimed_name": claim_name,
            "claimed_bio": claim_bio,
            "name_left": name_left,
            "bio_left": bio_left,
            "total_free_cases": cur_free,
        }
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        conn.close()

def use_free_10k_case_db(user_id: int) -> bool:
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT COALESCE(free_10k_cases, 0) AS fc FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row or int(row["fc"] or 0) <= 0:
            conn.rollback()
            return False
        conn.execute("UPDATE users SET free_10k_cases=free_10k_cases-1 WHERE user_id=? AND free_10k_cases>0", (user_id,))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return False
    finally:
        conn.close()

def get_all_broadcast_user_ids_db() -> List[int]:
    conn = db_connect()
    try:
        rows = conn.execute(
            "SELECT user_id FROM users WHERE COALESCE(is_banned, 0)=0 ORDER BY COALESCE(last_active_ts, 0) DESC, user_id ASC"
        ).fetchall()
        return [int(r["user_id"]) for r in rows]
    finally:
        conn.close()

def normalize_promo_code(raw_code: str) -> str:
    return re.sub(r"\s+", "", (raw_code or "").strip()).upper()

def create_promocode_db(
    code: str,
    reward_stars: int,
    gift_key: Optional[str],
    gift_count: int,
    max_uses: int,
    created_by: int = 0,
) -> Tuple[bool, str, Optional[int]]:
    norm = normalize_promo_code(code)
    if not norm or len(norm) < 2 or len(norm) > 40:
        return False, "Код промокода должен содержать от 2 до 40 символов.", None
    stars_val = max(0, int(reward_stars or 0))
    g_cnt = max(0, int(gift_count or 0)) if gift_key else 0
    if stars_val <= 0 and (not gift_key or g_cnt <= 0):
        return False, "Укажите награду: звёзды и/или NFT-подарок.", None
    if gift_key and gift_key not in GIFTS_BY_KEY:
        return False, "Выбранный подарок не найден.", None
    uses_val = max(1, int(max_uses or 1))
    conn = db_connect()
    try:
        cur = conn.execute(
            "INSERT INTO promocodes (code, reward_stars, gift_key, gift_count, max_uses, used_count, is_active, created_by, created_ts) "
            "VALUES (?, ?, ?, ?, ?, 0, 1, ?, ?)",
            (norm, stars_val, gift_key if g_cnt > 0 else None, g_cnt, uses_val, int(created_by), int(time.time())),
        )
        conn.commit()
        return True, "OK", int(cur.lastrowid)
    except sqlite3.IntegrityError:
        return False, f"Промокод <code>{clean_html(norm)}</code> уже существует!", None
    finally:
        conn.close()

def list_promocodes_db(page: int = 1, page_size: int = 8) -> Tuple[List[sqlite3.Row], int]:
    conn = db_connect()
    try:
        total = int(conn.execute("SELECT COUNT(*) AS cnt FROM promocodes").fetchone()["cnt"] or 0)
        offset = max(0, (page - 1) * page_size)
        rows = conn.execute(
            "SELECT * FROM promocodes ORDER BY is_active DESC, id DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()
        return rows, total
    finally:
        conn.close()

def get_promocode_by_id_db(promo_id: int) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute("SELECT * FROM promocodes WHERE id=?", (int(promo_id),)).fetchone()
    finally:
        conn.close()

def adjust_promocode_max_uses_db(promo_id: int, delta: int) -> Tuple[bool, str, int]:
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT max_uses, used_count FROM promocodes WHERE id=?", (int(promo_id),)).fetchone()
        if not row:
            conn.rollback()
            return False, "Промокод не найден.", 0
        min_allowed = max(1, int(row["used_count"] or 0))
        new_max = max(min_allowed, int(row["max_uses"] or 1) + int(delta))
        conn.execute("UPDATE promocodes SET max_uses=? WHERE id=?", (new_max, int(promo_id)))
        conn.commit()
        return True, "OK", new_max
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Ошибка: {e}", 0
    finally:
        conn.close()

def set_promocode_max_uses_db(promo_id: int, new_max: int) -> Tuple[bool, str, int]:
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT used_count FROM promocodes WHERE id=?", (int(promo_id),)).fetchone()
        if not row:
            conn.rollback()
            return False, "Промокод не найден.", 0
        used = int(row["used_count"] or 0)
        val = max(max(1, used), int(new_max))
        conn.execute("UPDATE promocodes SET max_uses=? WHERE id=?", (val, int(promo_id)))
        conn.commit()
        return True, "OK", val
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Ошибка: {e}", 0
    finally:
        conn.close()

def toggle_promocode_active_db(promo_id: int) -> Tuple[bool, int]:
    conn = db_connect()
    try:
        row = conn.execute("SELECT is_active FROM promocodes WHERE id=?", (int(promo_id),)).fetchone()
        if not row:
            return False, 0
        new_state = 0 if int(row["is_active"] or 0) else 1
        conn.execute("UPDATE promocodes SET is_active=? WHERE id=?", (new_state, int(promo_id)))
        conn.commit()
        return True, new_state
    finally:
        conn.close()

def delete_promocode_db(promo_id: int) -> bool:
    conn = db_connect()
    try:
        cur = conn.execute("DELETE FROM promocodes WHERE id=?", (int(promo_id),))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def redeem_promocode_db(user_id: int, raw_code: str) -> Tuple[bool, str, dict]:
    norm = normalize_promo_code(raw_code)
    if not norm:
        return False, "Введите текст промокода.", {}
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        promo = conn.execute("SELECT * FROM promocodes WHERE UPPER(code)=?", (norm,)).fetchone()
        if not promo:
            conn.rollback()
            return False, "Промокод не найден. Проверьте правильность написания.", {}
        if not int(promo["is_active"] or 0):
            conn.rollback()
            return False, "Этот промокод сейчас отключён.", {}
        if int(promo["used_count"] or 0) >= int(promo["max_uses"] or 0):
            conn.rollback()
            return False, "Лимит активаций этого промокода уже исчерпан!", {}

        already = conn.execute(
            "SELECT 1 FROM promo_redemptions WHERE promo_id=? AND user_id=?",
            (int(promo["id"]), int(user_id)),
        ).fetchone()
        if already:
            conn.rollback()
            return False, "Вы уже активировали этот промокод ранее!", {}

        u_row = conn.execute("SELECT max_inventory FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        if not u_row:
            conn.rollback()
            return False, "Профиль не найден.", {}

        now = int(time.time())
        r_stars = max(0, int(promo["reward_stars"] or 0))
        g_key = promo["gift_key"]
        g_cnt = max(0, int(promo["gift_count"] or 0)) if g_key else 0
        g_def = GIFTS_BY_KEY.get(g_key) if g_key else None
        if g_key and not g_def:
            g_cnt = 0

        conn.execute("UPDATE promocodes SET used_count=used_count+1 WHERE id=?", (int(promo["id"]),))
        conn.execute(
            "INSERT INTO promo_redemptions (promo_id, user_id, redeemed_ts) VALUES (?, ?, ?)",
            (int(promo["id"]), int(user_id), now),
        )

        add_xp = 0
        if r_stars > 0:
            conn.execute("UPDATE users SET balance_stars=balance_stars+? WHERE user_id=?", (r_stars, int(user_id)))
            record_star_flow(issued=r_stars, conn=conn)

        if g_def and g_cnt > 0:
            inv_cnt = int(conn.execute("SELECT COUNT(*) AS cnt FROM collection WHERE user_id=?", (int(user_id),)).fetchone()["cnt"] or 0)
            cur_max = int(u_row["max_inventory"] or 25)
            if inv_cnt + g_cnt > cur_max:
                conn.execute("UPDATE users SET max_inventory=? WHERE user_id=?", (inv_cnt + g_cnt, int(user_id)))
            for _ in range(g_cnt):
                ed_num = 0
                if g_def.key == "scared_cat":
                    row_m = conn.execute("SELECT value FROM bot_settings WHERE key='scared_cat_minted'").fetchone()
                    cur_sc = int(row_m["value"] or 0) if row_m else 0
                    coll_sc = int(conn.execute("SELECT COUNT(*) AS cnt FROM collection WHERE gift_key='scared_cat'").fetchone()["cnt"] or 0)
                    ed_num = max(cur_sc, coll_sc) + 1
                    conn.execute(
                        "INSERT INTO bot_settings (key, value) VALUES ('scared_cat_minted', ?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (str(ed_num),),
                    )
                conn.execute(
                    "INSERT INTO collection (user_id, gift_key, obtained_ts, is_favorite, edition_num) VALUES (?, ?, ?, 0, ?)",
                    (int(user_id), g_def.key, now, ed_num),
                )
            add_xp += g_def.xp * g_cnt
            conn.execute("UPDATE users SET xp=xp+? WHERE user_id=?", (add_xp, int(user_id)))

        conn.commit()
        return True, "OK", {
            "code": promo["code"],
            "reward_stars": r_stars,
            "gift_key": g_def.key if g_def else None,
            "gift_name": g_def.name if g_def else "",
            "gift_count": g_cnt,
            "xp_added": add_xp,
        }
    except sqlite3.IntegrityError:
        try: conn.rollback()
        except Exception: pass
        return False, "Вы уже активировали этот промокод ранее!", {}
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Ошибка активации: {e}", {}
    finally:
        conn.close()

def get_favorites(user_id: int) -> list[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute(
            "SELECT * FROM collection WHERE user_id=? AND is_favorite=1 LIMIT 7",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# P2P NFT МАРКЕТ — БАЗА ДАННЫХ (ТОЛЬКО УЛУЧШЕННЫЕ ПОДАРКИ, КОМИССИЯ 15%)
# ---------------------------------------------------------------------------

def create_market_listing(seller_id: int, item_id: int, price_stars: int) -> Tuple[bool, str, Optional[int]]:
    if price_stars < MARKET_MIN_PRICE or price_stars > MARKET_MAX_PRICE:
        return False, f"Цена должна быть от {MARKET_MIN_PRICE:,} ⭐ до {MARKET_MAX_PRICE:,} ⭐.", None

    conn = db_connect()
    try:
        item = conn.execute("SELECT * FROM collection WHERE id=? AND user_id=?", (item_id, seller_id)).fetchone()
        if not item:
            return False, "Подарок не найден в вашей коллекции.", None
        is_unique_unupgraded = (item["gift_key"] == "scared_cat")
        if not item["is_upgraded"] and not is_unique_unupgraded:
            return False, "На маркет можно выставлять только улучшенные подарки или уникальный Scared Cat!", None
        if item["is_listed"]:
            return False, "Этот подарок уже выставлен на маркете.", None

        if item["is_upgraded"]:
            m_name = item["model_name"] or get_upgraded_gift_title(item["gift_key"])
            b_key = item["backdrop_key"] or "black"
            u_stars = int(item["upgraded_stars"] or 0)
            u_num = int(item["upgrade_num"] or 0)
        else:
            m_name = "Unique Edition"
            b_key = "limited"
            u_stars = SCARED_CAT_DEF.stars
            u_num = int(item["edition_num"] or 0)

        now = int(time.time())
        conn.execute("UPDATE collection SET is_listed=1, is_favorite=0 WHERE id=?", (item_id,))
        cur = conn.execute(
            "INSERT INTO market_listings "
            "(collection_id, seller_id, gift_key, model_name, backdrop_key, upgraded_stars, upgrade_num, price_stars, status, created_ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)",
            (
                item_id,
                seller_id,
                item["gift_key"],
                m_name,
                b_key,
                u_stars,
                u_num,
                price_stars,
                now,
            ),
        )
        conn.commit()
        return True, "OK", cur.lastrowid
    finally:
        conn.close()

def cancel_market_listing(seller_id: int, listing_id: int) -> Tuple[bool, str]:
    conn = db_connect()
    try:
        lot = conn.execute(
            "SELECT * FROM market_listings WHERE id=? AND seller_id=? AND status='active'",
            (listing_id, seller_id),
        ).fetchone()
        if not lot:
            return False, "Активный лот не найден."

        conn.execute("UPDATE market_listings SET status='cancelled' WHERE id=?", (listing_id,))
        conn.execute("UPDATE collection SET is_listed=0 WHERE id=?", (lot["collection_id"],))
        conn.commit()
        return True, "Лот снят с продажи и возвращён в вашу коллекцию."
    finally:
        conn.close()

def get_market_listings(
    filter_type: str = "all",
    filter_key: str = "all",
    page: int = 1,
    page_size: int = 8,
) -> Tuple[list[sqlite3.Row], int, int]:
    conn = db_connect()
    try:
        where_clauses = ["ml.status='active'"]
        params: list = []

        if filter_type == "price" and filter_key in MARKET_PRICE_TIERS:
            _, min_p, max_p = MARKET_PRICE_TIERS[filter_key]
            where_clauses.append("ml.price_stars BETWEEN ? AND ?")
            params.extend([min_p, max_p])
        elif filter_type == "gift" and filter_key != "all":
            where_clauses.append("ml.gift_key=?")
            params.append(filter_key)
        elif filter_type == "model" and filter_key != "all":
            where_clauses.append("ml.model_name=?")
            params.append(filter_key)
        elif filter_type == "rarity" and filter_key != "all":
            matching_bgs = [b.key for b in PLUSHPEPE_BACKDROPS if b.rarity_label == filter_key]
            if matching_bgs:
                placeholders = ",".join("?" for _ in matching_bgs)
                where_clauses.append(f"ml.backdrop_key IN ({placeholders})")
                params.extend(matching_bgs)
            else:
                where_clauses.append("1=0")

        where_sql = " AND ".join(where_clauses)
        total = conn.execute(
            f"SELECT COUNT(*) as cnt FROM market_listings ml WHERE {where_sql}",
            tuple(params),
        ).fetchone()["cnt"]
        total_pages = max(1, math.ceil(total / page_size))
        page = max(1, min(page, total_pages))
        offset = (page - 1) * page_size

        rows = conn.execute(
            f"SELECT ml.*, u.first_name as seller_name, u.username as seller_username "
            f"FROM market_listings ml LEFT JOIN users u ON ml.seller_id = u.user_id "
            f"WHERE {where_sql} ORDER BY ml.id DESC LIMIT ? OFFSET ?",
            tuple(params) + (page_size, offset),
        ).fetchall()
        return rows, total_pages, total
    finally:
        conn.close()

def get_market_listing_by_id(listing_id: int) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute(
            "SELECT ml.*, u.first_name as seller_name, u.username as seller_username "
            "FROM market_listings ml LEFT JOIN users u ON ml.seller_id = u.user_id "
            "WHERE ml.id=?",
            (listing_id,),
        ).fetchone()
    finally:
        conn.close()

def get_active_listing_by_collection_id(collection_id: int) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute(
            "SELECT * FROM market_listings WHERE collection_id=? AND status='active' ORDER BY id DESC LIMIT 1",
            (collection_id,),
        ).fetchone()
    finally:
        conn.close()

def get_user_market_listings(user_id: int) -> list[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute(
            "SELECT * FROM market_listings WHERE seller_id=? AND status='active' ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

def buy_market_listing(buyer_id: int, listing_id: int) -> Tuple[bool, str, Optional[dict]]:
    conn = db_connect()
    try:
        lot = conn.execute("SELECT * FROM market_listings WHERE id=?", (listing_id,)).fetchone()
        if not lot or lot["status"] != "active":
            return False, "Лот уже продан или снят с продажи.", None
        if lot["seller_id"] == buyer_id:
            return False, "Нельзя купить собственный лот!", None

        buyer = conn.execute("SELECT balance_stars, max_inventory FROM users WHERE user_id=?", (buyer_id,)).fetchone()
        if not buyer:
            return False, "Профиль покупателя не найден.", None

        price = int(lot["price_stars"])
        if buyer["balance_stars"] < price:
            return False, f"Недостаточно Stars! Нужно {price:,} ⭐.", None

        buyer_cnt = conn.execute("SELECT COUNT(*) as cnt FROM collection WHERE user_id=?", (buyer_id,)).fetchone()["cnt"]
        if buyer_cnt >= buyer["max_inventory"]:
            return False, "Ваш инвентарь переполнен! Освободите место или расширьте слоты.", None

        fee_stars = int(price * MARKET_FEE_RATE)
        seller_gets = price - fee_stars
        now = int(time.time())

        conn.execute("UPDATE users SET balance_stars=balance_stars-? WHERE user_id=?", (price, buyer_id))
        conn.execute(
            "UPDATE users SET balance_stars=balance_stars+?, total_sold=total_sold+1 WHERE user_id=?",
            (seller_gets, lot["seller_id"]),
        )
        conn.execute(
            "UPDATE collection SET user_id=?, is_listed=0, is_favorite=0, obtained_ts=? WHERE id=?",
            (buyer_id, now, lot["collection_id"]),
        )
        conn.execute(
            "UPDATE market_listings SET status='sold', buyer_id=?, sold_ts=? WHERE id=?",
            (buyer_id, now, listing_id),
        )
        conn.execute(
            "INSERT INTO market_history "
            "(listing_id, seller_id, buyer_id, gift_key, model_name, backdrop_key, price_stars, fee_stars, seller_received_stars, sold_ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                listing_id,
                lot["seller_id"],
                buyer_id,
                lot["gift_key"],
                lot["model_name"],
                lot["backdrop_key"],
                price,
                fee_stars,
                seller_gets,
                now,
            ),
        )
        record_star_flow(spent=price, burned=fee_stars, purchased=price, conn=conn)
        conn.commit()
        return True, "OK", {
            "listing_id": listing_id,
            "collection_id": lot["collection_id"],
            "seller_id": lot["seller_id"],
            "gift_key": lot["gift_key"],
            "price_stars": price,
            "fee_stars": fee_stars,
            "seller_gets": seller_gets,
            "model_name": lot["model_name"],
            "backdrop_key": lot["backdrop_key"],
            "upgrade_num": lot["upgrade_num"],
            "upgraded_stars": lot["upgraded_stars"],
        }
    finally:
        conn.close()

def get_market_history(user_id: Optional[int] = None, limit: int = 12) -> list[sqlite3.Row]:
    conn = db_connect()
    try:
        if user_id is not None:
            return conn.execute(
                "SELECT * FROM market_history WHERE seller_id=? OR buyer_id=? ORDER BY id DESC LIMIT ?",
                (user_id, user_id, limit),
            ).fetchall()
        return conn.execute("SELECT * FROM market_history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    finally:
        conn.close()

def get_user_rank(user_id: int) -> int:
    conn = db_connect()
    try:
        rows = conn.execute("SELECT user_id FROM users ORDER BY balance_stars DESC, xp DESC").fetchall()
        for idx, r in enumerate(rows, start=1):
            if r["user_id"] == user_id:
                return idx
        return 1
    finally:
        conn.close()

def get_user_by_target(target: str) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        target = target.strip()
        if target.startswith("@"):
            uname = target.lstrip("@").lower()
            return conn.execute("SELECT * FROM users WHERE LOWER(username)=?", (uname,)).fetchone()
        elif target.isdigit():
            val = int(target)
            row = conn.execute("SELECT * FROM users WHERE user_id=?", (val,)).fetchone()
            if not row:
                row = conn.execute("SELECT * FROM users WHERE id_num=?", (val,)).fetchone()
            return row
        else:
            # Также поддерживаем поиск по username без @
            uname = target.lower()
            return conn.execute("SELECT * FROM users WHERE LOWER(username)=?", (uname,)).fetchone()
    finally:
        conn.close()

def get_top_users_page(page: int = 1, page_size: int = 10) -> Tuple[list[sqlite3.Row], int]:
    conn = db_connect()
    try:
        total = conn.execute("SELECT COUNT(*) as cnt FROM users WHERE hide_top=0").fetchone()["cnt"]
        total_pages = max(1, math.ceil(total / page_size))
        page = max(1, min(page, total_pages))
        offset = (page - 1) * page_size
        rows = conn.execute(
            "SELECT * FROM users WHERE hide_top=0 ORDER BY balance_stars DESC, xp DESC LIMIT ? OFFSET ?",
            (page_size, offset)
        ).fetchall()
        return rows, total_pages
    finally:
        conn.close()

def create_pending_drop(user_id: int, chat_id: int, gift_key: str) -> int:
    conn = db_connect()
    try:
        cur = conn.execute(
            "INSERT INTO pending_drops (user_id, chat_id, gift_key, created_ts) VALUES (?, ?, ?, ?)",
            (user_id, chat_id, gift_key, int(time.time())),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def get_pending_drop(drop_id: int) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute("SELECT * FROM pending_drops WHERE id=?", (drop_id,)).fetchone()
    finally:
        conn.close()

def resolve_pending_drop(drop_id: int) -> None:
    conn = db_connect()
    try:
        conn.execute("UPDATE pending_drops SET resolved=1 WHERE id=?", (drop_id,))
        conn.commit()
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# РЕЖИМ ИГРЫ: БАТТЛЫ (CASE BATTLES) — БАЗА ДАННЫХ И РАСЧЁТ
# ---------------------------------------------------------------------------

def create_case_battle_db(
    creator_id: int,
    case_keys: List[str],
    max_players: int,
    countdown_seconds: int = BATTLE_COUNTDOWN_SECONDS,
) -> Tuple[bool, str, Optional[dict]]:
    if not case_keys or len(case_keys) < BATTLE_MIN_CASES or len(case_keys) > BATTLE_MAX_CASES:
        return False, f"Выберите от {BATTLE_MIN_CASES} до {BATTLE_MAX_CASES} кейсов!", None
    if max_players < BATTLE_MIN_PLAYERS or max_players > BATTLE_MAX_PLAYERS:
        return False, f"Количество участников: от {BATTLE_MIN_PLAYERS} до {BATTLE_MAX_PLAYERS}!", None
    total_cost = 0
    for ck in case_keys:
        tier = CASE_TIERS.get(ck)
        if not tier:
            return False, f"Неизвестный кейс: {ck}", None
        total_cost += int(tier["price"])

    now = int(time.time())
    is_solo = (max_players == 1)
    init_status = "countdown" if is_solo else "waiting"
    cd_end = (now + max(1, int(countdown_seconds))) if is_solo else 0

    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        u = conn.execute("SELECT balance_stars FROM users WHERE user_id=?", (creator_id,)).fetchone()
        if not u or int(u["balance_stars"] or 0) < total_cost:
            conn.rollback()
            return False, f"Недостаточно Stars! Нужно {total_cost:,} ⭐.", None

        conn.execute("UPDATE users SET balance_stars=balance_stars-? WHERE user_id=?", (total_cost, creator_id))
        cur = conn.execute(
            """
            INSERT INTO case_battles
                (creator_id, cases_json, total_cost_stars, max_players, status, countdown_ends_ts, created_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (creator_id, json.dumps(list(case_keys)), total_cost, int(max_players), init_status, cd_end, now),
        )
        battle_id = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO case_battle_participants (battle_id, user_id, joined_ts) VALUES (?, ?, ?)",
            (battle_id, creator_id, now),
        )
        record_star_flow(spent=total_cost, conn=conn)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()

    detail = get_case_battle_detail_db(battle_id)
    return True, ("SOLO_COUNTDOWN" if is_solo else "CREATED"), detail

def get_open_case_battles_db(page: int = 1, page_size: int = 8) -> Tuple[List[dict], int, int]:
    conn = db_connect()
    try:
        total = int(
            conn.execute(
                "SELECT COUNT(*) AS cnt FROM case_battles WHERE status IN ('waiting', 'countdown', 'running')"
            ).fetchone()["cnt"]
        )
        total_pages = max(1, math.ceil(total / page_size))
        page = max(1, min(page, total_pages))
        offset = (page - 1) * page_size
        rows = conn.execute(
            """
            SELECT cb.*,
                   (SELECT COUNT(*) FROM case_battle_participants p WHERE p.battle_id=cb.id) AS joined_count
            FROM case_battles cb
            WHERE cb.status IN ('waiting', 'countdown', 'running')
            ORDER BY CASE cb.status WHEN 'waiting' THEN 0 WHEN 'countdown' THEN 1 ELSE 2 END, cb.id DESC
            LIMIT ? OFFSET ?
            """,
            (page_size, offset),
        ).fetchall()
        return [dict(r) for r in rows], total_pages, total
    finally:
        conn.close()

def get_case_battle_detail_db(battle_id: int) -> Optional[dict]:
    conn = db_connect()
    try:
        b = conn.execute("SELECT * FROM case_battles WHERE id=?", (battle_id,)).fetchone()
        if not b:
            return None
        parts = conn.execute(
            """
            SELECT p.*, u.first_name, u.username
            FROM case_battle_participants p
            LEFT JOIN users u ON u.user_id = p.user_id
            WHERE p.battle_id=?
            ORDER BY p.id ASC
            """,
            (battle_id,),
        ).fetchall()
        res = dict(b)
        res["cases"] = json.loads(res["cases_json"] or "[]")
        res["participants"] = [dict(p) for p in parts]
        res["results"] = json.loads(res["results_json"] or "[]")
        return res
    finally:
        conn.close()

def update_battle_participant_msg_db(battle_id: int, user_id: int, chat_id: int, message_id: int) -> None:
    conn = db_connect()
    try:
        conn.execute(
            "UPDATE case_battle_participants SET ui_chat_id=?, ui_message_id=? WHERE battle_id=? AND user_id=?",
            (int(chat_id), int(message_id), int(battle_id), int(user_id)),
        )
        conn.commit()
    finally:
        conn.close()

def join_case_battle_db(
    battle_id: int,
    user_id: int,
    countdown_seconds: int = BATTLE_COUNTDOWN_SECONDS,
) -> Tuple[bool, str, Optional[dict]]:
    now = int(time.time())
    started_countdown = False
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        b = conn.execute("SELECT * FROM case_battles WHERE id=?", (battle_id,)).fetchone()
        if not b:
            conn.rollback()
            return False, "Баттл не найден.", None
        if b["status"] != "waiting":
            conn.rollback()
            return False, "Набор участников в этот баттл уже закрыт!", None

        exists = conn.execute(
            "SELECT 1 FROM case_battle_participants WHERE battle_id=? AND user_id=?",
            (battle_id, user_id),
        ).fetchone()
        if exists:
            conn.rollback()
            return False, "Вы уже участвуете в этом баттле!", None

        cnt_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM case_battle_participants WHERE battle_id=?",
            (battle_id,),
        ).fetchone()
        cur_cnt = int(cnt_row["cnt"] or 0)
        max_p = int(b["max_players"] or 2)
        if cur_cnt >= max_p:
            conn.rollback()
            return False, "Все места в баттле уже заняты!", None

        cost = int(b["total_cost_stars"] or 0)
        u = conn.execute("SELECT balance_stars FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not u or int(u["balance_stars"] or 0) < cost:
            conn.rollback()
            return False, f"Недостаточно Stars! Для входа нужно {cost:,} ⭐.", None

        conn.execute("UPDATE users SET balance_stars=balance_stars-? WHERE user_id=?", (cost, user_id))
        conn.execute(
            "INSERT INTO case_battle_participants (battle_id, user_id, joined_ts) VALUES (?, ?, ?)",
            (battle_id, user_id, now),
        )
        new_cnt = cur_cnt + 1
        if new_cnt >= max_p:
            cd_end = now + max(1, int(countdown_seconds))
            conn.execute(
                "UPDATE case_battles SET status='countdown', countdown_ends_ts=? WHERE id=?",
                (cd_end, battle_id),
            )
            started_countdown = True
        record_star_flow(spent=cost, conn=conn)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()

    detail = get_case_battle_detail_db(battle_id)
    return True, ("FULL_COUNTDOWN" if started_countdown else "JOINED"), detail

def leave_or_cancel_battle_db(battle_id: int, user_id: int) -> Tuple[bool, str, int, List[int]]:
    now = int(time.time())
    refunded_ids: List[int] = []
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        b = conn.execute("SELECT * FROM case_battles WHERE id=?", (battle_id,)).fetchone()
        if not b:
            conn.rollback()
            return False, "Баттл не найден.", 0, []
        if b["status"] != "waiting":
            conn.rollback()
            return False, "Нельзя выйти — обратный отсчёт или баттл уже начался!", 0, []

        p = conn.execute(
            "SELECT 1 FROM case_battle_participants WHERE battle_id=? AND user_id=?",
            (battle_id, user_id),
        ).fetchone()
        if not p:
            conn.rollback()
            return False, "Вы не участвуете в этом баттле.", 0, []

        cost = int(b["total_cost_stars"] or 0)
        if int(b["creator_id"]) == int(user_id):
            parts = conn.execute(
                "SELECT user_id FROM case_battle_participants WHERE battle_id=?",
                (battle_id,),
            ).fetchall()
            for row in parts:
                uid = int(row["user_id"])
                conn.execute("UPDATE users SET balance_stars=balance_stars+? WHERE user_id=?", (cost, uid))
                refunded_ids.append(uid)
            conn.execute(
                "UPDATE case_battles SET status='cancelled', finished_ts=? WHERE id=?",
                (now, battle_id),
            )
            conn.commit()
            return True, "CANCELLED", cost, refunded_ids
        else:
            conn.execute(
                "DELETE FROM case_battle_participants WHERE battle_id=? AND user_id=?",
                (battle_id, user_id),
            )
            conn.execute("UPDATE users SET balance_stars=balance_stars+? WHERE user_id=?", (cost, user_id))
            refunded_ids.append(user_id)
            conn.commit()
            return True, "LEFT", cost, refunded_ids
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()

def start_battle_running_db(battle_id: int) -> bool:
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        b = conn.execute("SELECT status FROM case_battles WHERE id=?", (battle_id,)).fetchone()
        if not b or b["status"] != "countdown":
            conn.rollback()
            return False
        conn.execute("UPDATE case_battles SET status='running' WHERE id=?", (battle_id,))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()

def finish_case_battle_db(
    battle_id: int,
    winner_id: int,
    winner_total_stars: int,
    results_payload: dict,
    all_dropped_items: List[dict],
) -> bool:
    now = int(time.time())
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        b = conn.execute("SELECT status FROM case_battles WHERE id=?", (battle_id,)).fetchone()
        if not b or b["status"] not in ("countdown", "running"):
            conn.rollback()
            return False

        total_xp = 0
        for d in all_dropped_items:
            conn.execute(
                """
                INSERT INTO collection
                    (user_id, gift_key, obtained_ts, buff_backdrop_pct, buff_model_pct, buff_value_pct)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    int(winner_id),
                    d["gift_key"],
                    now,
                    int(d.get("buff_backdrop_pct", 0) or 0),
                    int(d.get("buff_model_pct", 0) or 0),
                    int(d.get("buff_value_pct", 0) or 0),
                ),
            )
            total_xp += int(d.get("xp", 0) or 0)

        conn.execute(
            "UPDATE users SET xp=xp+?, total_drops=total_drops+? WHERE user_id=?",
            (total_xp, len(all_dropped_items), int(winner_id)),
        )
        conn.execute(
            """
            UPDATE case_battles
            SET status='finished', winner_id=?, winner_total_stars=?, results_json=?, finished_ts=?
            WHERE id=?
            """,
            (int(winner_id), int(winner_total_stars), json.dumps(results_payload), now, int(battle_id)),
        )
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()

def get_stalled_battles_db() -> List[int]:
    conn = db_connect()
    try:
        rows = conn.execute(
            "SELECT id FROM case_battles WHERE status IN ('countdown', 'running') ORDER BY id ASC"
        ).fetchall()
        return [int(r["id"]) for r in rows]
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# КЛАНЫ — БАЗА ДАННЫХ, КАЗНА И ПОДАРКИ КЛАНА
# ---------------------------------------------------------------------------

def get_user_clan(user_id: int) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        user = conn.execute("SELECT clan_id FROM users WHERE user_id=?", (user_id,)).fetchone()
        if user and user["clan_id"]:
            return conn.execute("SELECT * FROM clans WHERE id=?", (user["clan_id"],)).fetchone()
        return None
    finally:
        conn.close()

def get_clan_by_id(clan_id: int) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute("SELECT * FROM clans WHERE id=?", (clan_id,)).fetchone()
    finally:
        conn.close()

def get_clan_treasury_and_members(clan_id: int) -> Tuple[int, int, list[sqlite3.Row]]:
    """
    Возвращает:
    - total_treasury: Общая казна (сумма балансов участников + баланс казны + потраченное из казны).
      При депозите участником в баланс казны общая казна НЕ уменьшается!
      При входе нового участника общая казна пополняется на его баланс!
    - donated_bank: Баланс казны (звёзды, доступные для клановых покупок).
    - members: отсортированный список участников с балансами.
    """
    conn = db_connect()
    try:
        members = conn.execute(
            "SELECT user_id, first_name, username, balance_stars FROM users WHERE clan_id=? ORDER BY balance_stars DESC",
            (clan_id,)
        ).fetchall()
        members_sum = sum(m["balance_stars"] for m in members)
        clan = conn.execute("SELECT donated_stars, spent_stars FROM clans WHERE id=?", (clan_id,)).fetchone()
        donated_bank = clan["donated_stars"] if clan else 0
        spent_bank = clan["spent_stars"] if (clan and "spent_stars" in clan.keys()) else 0
        total_treasury = members_sum + donated_bank + spent_bank
        return total_treasury, donated_bank, members
    finally:
        conn.close()

def check_and_award_clan_daily_xp(clan_id: int) -> Optional[int]:
    conn = db_connect()
    try:
        clan = conn.execute("SELECT last_daily_xp_ts, xp, donated_stars, spent_stars FROM clans WHERE id=?", (clan_id,)).fetchone()
        if not clan:
            return None
        now = int(time.time())
        last_ts = clan["last_daily_xp_ts"] or 0
        if now - last_ts < 24 * 3600:
            return None

        members = conn.execute("SELECT balance_stars FROM users WHERE clan_id=?", (clan_id,)).fetchall()
        spent_bank = clan["spent_stars"] if "spent_stars" in clan.keys() else 0
        treasury = sum(m["balance_stars"] for m in members) + (clan["donated_stars"] or 0) + (spent_bank or 0)

        if treasury < 5_000_000:
            conn.execute("UPDATE clans SET last_daily_xp_ts=? WHERE id=?", (now, clan_id))
            conn.commit()
            return None

        millions = treasury / 1_000_000
        awarded_xp = int(500 + 450 * math.log2(millions / 5 + 1))
        conn.execute("UPDATE clans SET xp=xp+?, last_daily_xp_ts=? WHERE id=?", (awarded_xp, now, clan_id))
        conn.commit()
        return awarded_xp
    finally:
        conn.close()

def donate_stars_to_clan(user_id: int, clan_id: int, stars: int) -> Tuple[bool, int]:
    """
    Пополнение баланса казны звездами:
    - Списывает звёзды с баланса игрока и переводит в Баланс казны (donated_stars)
    - Общая казна клана остаётся неизменной (баланс игрока перешёл в баланс казны)
    - Начисляет клану XP (800 XP за 1,000,000 ⭐)
    """
    if not deduct_user_stars(user_id, stars):
        return False, 0
    xp_earned = max(1, int(stars * 0.0008))
    conn = db_connect()
    try:
        conn.execute("UPDATE clans SET donated_stars=donated_stars+?, xp=xp+? WHERE id=?", (stars, xp_earned, clan_id))
        record_star_flow(spent=stars, conn=conn)
        conn.commit()
        return True, xp_earned
    finally:
        conn.close()

def set_clan_avatar(clan_id: int, avatar_path: Optional[str]) -> None:
    conn = db_connect()
    try:
        conn.execute("UPDATE clans SET avatar_path=? WHERE id=?", (avatar_path, clan_id))
        conn.commit()
    finally:
        conn.close()

def get_clan_gifts(clan_id: int) -> list[sqlite3.Row]:
    """Возвращает реальные подарки, подаренные игроками в клан."""
    conn = db_connect()
    try:
        return conn.execute(
            "SELECT cg.*, u.first_name, u.username FROM clan_gifts cg "
            "LEFT JOIN users u ON cg.donor_user_id = u.user_id "
            "WHERE cg.clan_id=? ORDER BY cg.is_favorite DESC, cg.id DESC",
            (clan_id,),
        ).fetchall()
    finally:
        conn.close()

def get_clan_gift_by_id(clan_gift_id: int) -> Optional[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute("SELECT * FROM clan_gifts WHERE id=?", (clan_gift_id,)).fetchone()
    finally:
        conn.close()

def get_clan_favorites(clan: sqlite3.Row) -> List[GiftDef]:
    """Избранные подарки клана берутся ТОЛЬКО из реально подаренных игроками подарков в clan_gifts."""
    conn = db_connect()
    try:
        rows = conn.execute(
            "SELECT gift_key FROM clan_gifts WHERE clan_id=? AND is_favorite=1 ORDER BY id DESC LIMIT 7",
            (clan["id"],),
        ).fetchall()
        return [GIFTS_BY_KEY[r["gift_key"]] for r in rows if r["gift_key"] in GIFTS_BY_KEY]
    finally:
        conn.close()

def toggle_clan_gift_favorite(clan_id: int, clan_gift_id: int) -> Tuple[bool, str]:
    conn = db_connect()
    try:
        row = conn.execute("SELECT * FROM clan_gifts WHERE id=? AND clan_id=?", (clan_gift_id, clan_id)).fetchone()
        if not row:
            return False, "Подарок не найден в клане."

        if not row["is_favorite"]:
            fav_cnt = conn.execute(
                "SELECT COUNT(*) as cnt FROM clan_gifts WHERE clan_id=? AND is_favorite=1",
                (clan_id,),
            ).fetchone()["cnt"]
            if fav_cnt >= 7:
                return False, "Максимум 7 избранных подарков у клана!"
            conn.execute("UPDATE clan_gifts SET is_favorite=1 WHERE id=?", (clan_gift_id,))
            msg = "⭐ Подарок добавлен в избранное клана!"
        else:
            conn.execute("UPDATE clan_gifts SET is_favorite=0 WHERE id=?", (clan_gift_id,))
            msg = "Подарок убран из избранного клана."

        conn.commit()
        return True, msg
    finally:
        conn.close()

def donate_gift_to_clan_db(user_id: int, clan_id: int, item_id: int) -> Tuple[bool, str, int]:
    """Переносит подарок из коллекции игрока в clan_gifts и начисляет клану XP."""
    conn = db_connect()
    try:
        item = conn.execute("SELECT * FROM collection WHERE id=? AND user_id=?", (item_id, user_id)).fetchone()
        if not item:
            return False, "Предмет не найден в вашей коллекции.", 0
        if item["is_listed"]:
            return False, "Подарок выставлен на маркете! Сначала снимите лот.", 0
        g = GIFTS_BY_KEY.get(item["gift_key"])
        if not g:
            return False, "Неизвестный подарок.", 0

        val_stars = get_item_display_value(item)
        xp_earned = max(1, int(val_stars * 0.0008))
        g_title = get_upgraded_gift_title(item["gift_key"])
        disp_name = f"{g_title} ({item['model_name']})" if item["is_upgraded"] and item["model_name"] else g.name
        conn.execute("DELETE FROM collection WHERE id=? AND user_id=?", (item_id, user_id))
        conn.execute(
            "INSERT INTO clan_gifts (clan_id, donor_user_id, gift_key, donated_ts, is_favorite) VALUES (?, ?, ?, ?, 0)",
            (clan_id, user_id, item["gift_key"], int(time.time())),
        )
        conn.execute("UPDATE clans SET xp=xp+? WHERE id=?", (xp_earned, clan_id))
        conn.commit()
        return True, disp_name, xp_earned
    finally:
        conn.close()

def get_all_clans(page: int = 1, page_size: int = 5) -> Tuple[list[sqlite3.Row], int]:
    conn = db_connect()
    try:
        total = conn.execute("SELECT COUNT(*) as cnt FROM clans").fetchone()["cnt"]
        total_pages = max(1, math.ceil(total / page_size))
        page = max(1, min(page, total_pages))
        offset = (page - 1) * page_size
        rows = conn.execute("SELECT * FROM clans ORDER BY xp DESC, id DESC LIMIT ? OFFSET ?", (page_size, offset)).fetchall()
        return rows, total_pages
    finally:
        conn.close()

def create_clan(owner_id: int, tag: str, name: str, desc: str, ctype: str, fee: int) -> Optional[int]:
    clan_sys_id = get_next_global_id("clan")
    conn = db_connect()
    try:
        cur = conn.execute(
            "INSERT INTO clans (id_num, owner_id, tag, name, description, type, entry_fee, max_members, xp, donated_stars, spent_stars, last_daily_xp_ts, created_ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 15, 0, 0, 0, ?, ?)",
            (clan_sys_id, owner_id, tag, name, desc, ctype, fee, int(time.time()), int(time.time()))
        )
        clan_id = cur.lastrowid
        conn.execute("UPDATE users SET clan_id=? WHERE user_id=?", (clan_id, owner_id))
        conn.commit()
        return clan_id
    except Exception as e:
        log.error("Ошибка создания клана: %s", e)
        return None
    finally:
        conn.close()

def add_user_to_clan(user_id: int, clan_id: int) -> bool:
    conn = db_connect()
    try:
        clan = conn.execute("SELECT max_members FROM clans WHERE id=?", (clan_id,)).fetchone()
        cnt = conn.execute("SELECT COUNT(*) as cnt FROM users WHERE clan_id=?", (clan_id,)).fetchone()["cnt"]
        if not clan or cnt >= clan["max_members"]:
            return False
        conn.execute("UPDATE users SET clan_id=? WHERE user_id=?", (clan_id, user_id))
        conn.execute("DELETE FROM clan_requests WHERE user_id=?", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()

def remove_user_from_clan(user_id: int) -> None:
    conn = db_connect()
    try:
        conn.execute("UPDATE users SET clan_id=NULL WHERE user_id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()

def delete_clan(clan_id: int) -> None:
    conn = db_connect()
    try:
        conn.execute("UPDATE users SET clan_id=NULL WHERE clan_id=?", (clan_id,))
        conn.execute("DELETE FROM clan_requests WHERE clan_id=?", (clan_id,))
        conn.execute("DELETE FROM clan_gifts WHERE clan_id=?", (clan_id,))
        conn.execute("DELETE FROM clans WHERE id=?", (clan_id,))
        conn.commit()
    finally:
        conn.close()

def get_clan_upgrade_cost(current_max: int) -> int:
    if current_max < 30: return 100_000
    if current_max < 45: return 500_000
    if current_max < 60: return 2_000_000
    return 5_000_000

def upgrade_clan_slots(clan_id: int, cost: int) -> Tuple[bool, str]:
    """Списывает стоимость улучшения мест сначала из Баланса казны (donated_stars), либо с баланса владельца."""
    conn = db_connect()
    try:
        clan = conn.execute("SELECT owner_id, max_members, donated_stars FROM clans WHERE id=?", (clan_id,)).fetchone()
        if not clan:
            return False, "Клан не найден."
        if (clan["donated_stars"] or 0) >= cost:
            conn.execute(
                "UPDATE clans SET donated_stars=donated_stars-?, spent_stars=spent_stars+?, max_members=max_members+15 WHERE id=?",
                (cost, cost, clan_id),
            )
            record_star_flow(burned=cost, purchased=cost, conn=conn)
            conn.commit()
            return True, "из баланса казны"

        owner = conn.execute("SELECT balance_stars FROM users WHERE user_id=?", (clan["owner_id"],)).fetchone()
        if not owner or owner["balance_stars"] < cost:
            return False, f"Недостаточно Stars! В балансе казны ({clan['donated_stars']:,} ⭐) и у владельца меньше {cost:,} ⭐."

        conn.execute("UPDATE users SET balance_stars=balance_stars-? WHERE user_id=?", (cost, clan["owner_id"]))
        conn.execute("UPDATE clans SET spent_stars=spent_stars+?, max_members=max_members+15 WHERE id=?", (cost, clan_id))
        record_star_flow(spent=cost, burned=cost, purchased=cost, conn=conn)
        conn.commit()
        return True, "с баланса владельца"
    finally:
        conn.close()

def add_clan_request(clan_id: int, user_id: int) -> bool:
    conn = db_connect()
    try:
        conn.execute("INSERT OR IGNORE INTO clan_requests (clan_id, user_id, created_ts) VALUES (?, ?, ?)",
                     (clan_id, user_id, int(time.time())))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_clan_requests(clan_id: int) -> list[sqlite3.Row]:
    conn = db_connect()
    try:
        return conn.execute(
            "SELECT r.*, u.first_name, u.username FROM clan_requests r JOIN users u ON r.user_id = u.user_id WHERE r.clan_id=?",
            (clan_id,)
        ).fetchall()
    finally:
        conn.close()

def remove_clan_request(clan_id: int, user_id: int) -> None:
    conn = db_connect()
    try:
        conn.execute("DELETE FROM clan_requests WHERE clan_id=? AND user_id=?", (clan_id, user_id))
        conn.commit()
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# РЕНДЕР КАРТОЧЕК И БАННЕРОВ (БЕЗ СМАЙЛИКОВ И КВАДРАТОВ)
# ---------------------------------------------------------------------------

def draw_rounded_rect(draw, coords, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(coords, radius=radius, fill=fill, outline=outline, width=width)

def make_smooth_rounded_mask(width: int, height: int, radius: int) -> Image.Image:
    """Создаёт сглаженную маску скруглённого прямоугольника без пиксельных лесенок (2x SSAA)."""
    scale = 2
    big = Image.new("L", (width * scale, height * scale), 0)
    bdraw = ImageDraw.Draw(big)
    bdraw.rounded_rectangle(
        [0, 0, width * scale - 1, height * scale - 1],
        radius=radius * scale,
        fill=255,
    )
    return big.resize((width, height), Image.Resampling.LANCZOS)

def apply_liquid_glass_panel(
    base_img: Image.Image,
    box: Tuple[int, int, int, int],
    radius: int = 24,
    blur_radius: int = 18,
    dark_tint: int = 62,
    top_light: int = 38,
    bottom_light: int = 10,
) -> Image.Image:
    """Накладывает настоящее жидкое стекло (iOS Liquid Glass) с рефракцией фона, кристальной ясностью и СТРОГО без обводки."""
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    if w <= 4 or h <= 4:
        return base_img

    src_rgba = base_img.convert("RGBA")
    img_w, img_h = src_rgba.size

    # Берём расширенный патч с безопасным отражением/клампингом краёв, чтобы размытие и преломление были чистыми
    pad = max(28, blur_radius + 16)
    cx1, cy1 = x1 - pad, y1 - pad
    cx2, cy2 = x2 + pad, y2 + pad

    patch_w = cx2 - cx1
    patch_h = cy2 - cy1
    patch = Image.new("RGBA", (patch_w, patch_h), (12, 17, 30, 255))

    ix1, iy1 = max(0, cx1), max(0, cy1)
    ix2, iy2 = min(img_w, cx2), min(img_h, cy2)
    if ix2 > ix1 and iy2 > iy1:
        sub = src_rgba.crop((ix1, iy1, ix2, iy2))
        patch.paste(sub, (ix1 - cx1, iy1 - cy1))
        # Заполняем вылеты за границу кадра краевыми полосами, чтобы не было тёмной каймы при размытии
        if ix1 > cx1:
            strip_l = sub.crop((0, 0, 1, sub.height)).resize((ix1 - cx1, sub.height), Image.Resampling.NEAREST)
            patch.paste(strip_l, (0, iy1 - cy1))
        if ix2 < cx2:
            strip_r = sub.crop((sub.width - 1, 0, sub.width, sub.height)).resize((cx2 - ix2, sub.height), Image.Resampling.NEAREST)
            patch.paste(strip_r, (ix2 - cx1, iy1 - cy1))
        if iy1 > cy1:
            strip_t = patch.crop((0, iy1 - cy1, patch_w, iy1 - cy1 + 1)).resize((patch_w, iy1 - cy1), Image.Resampling.NEAREST)
            patch.paste(strip_t, (0, 0))
        if iy2 < cy2:
            strip_b = patch.crop((0, iy2 - cy1 - 1, patch_w, iy2 - cy1)).resize((patch_w, cy2 - iy2), Image.Resampling.NEAREST)
            patch.paste(strip_b, (0, iy2 - cy1))

    # Лёгкий оптический MESH-дисторшн (линзовое преломление суперэллипса + мягкая текучая волна)
    cols = 14 if w >= 180 else 8
    rows = 8 if h >= 120 else 5
    half_w = w * 0.5
    half_h = h * 0.5
    max_sx = patch_w - 1.5
    max_sy = patch_h - 1.5

    def _refract_pt(px: float, py: float) -> Tuple[float, float]:
        u = (px - half_w) / max(1.0, half_w)
        v = (py - half_h) / max(1.0, half_h)
        d = (abs(u) ** 4 + abs(v) ** 4) ** 0.25

        # Центр чуть увеличивает фон (эффект объёмной линзы), к краям лучи заметно изгибаются
        zoom = 0.955
        edge_zone = max(0.0, (d - 0.45) / 0.55)
        edge_bend = (edge_zone ** 2.0) * 0.14
        wave_x = math.sin(v * math.pi * 1.5) * 3.2
        wave_y = math.cos(u * math.pi * 1.35) * 2.8

        su = u * (zoom + edge_bend)
        sv = v * (zoom + edge_bend)
        sx = pad + half_w + su * half_w + wave_x
        sy = pad + half_h + sv * half_h + wave_y
        return (max(1.0, min(max_sx, sx)), max(1.0, min(max_sy, sy)))

    xs = [int(round(w * c / cols)) for c in range(cols + 1)]
    ys = [int(round(h * r / rows)) for r in range(rows + 1)]
    mesh = []
    for r in range(rows):
        y_top, y_bot = ys[r], ys[r + 1]
        if y_bot <= y_top:
            continue
        for c in range(cols):
            x_left, x_right = xs[c], xs[c + 1]
            if x_right <= x_left:
                continue
            nw = _refract_pt(x_left, y_top)
            sw = _refract_pt(x_left, y_bot)
            se = _refract_pt(x_right, y_bot)
            ne = _refract_pt(x_right, y_top)
            mesh.append(((x_left, y_top, x_right, y_bot), (nw[0], nw[1], sw[0], sw[1], se[0], se[1], ne[0], ne[1])))

    refracted = patch.transform((w, h), Image.Transform.MESH, mesh, resample=Image.Resampling.BICUBIC)

    # Оптическое размытие + сочность цветов вместо мутного матового слоя
    eff_blur = max(5, int(round(blur_radius * 0.72)))
    blurred_rgb = refracted.convert("RGB").filter(ImageFilter.GaussianBlur(eff_blur))
    vibrant_rgb = ImageEnhance.Color(blurred_rgb).enhance(1.48)
    vibrant_rgb = ImageEnhance.Brightness(vibrant_rgb).enhance(1.05)
    vibrant_rgb = ImageEnhance.Contrast(vibrant_rgb).enhance(1.08)
    glass = vibrant_rgb.convert("RGBA")

    # Деликатнейшая полупрозрачная глубина (только для читаемости белого текста, без матовости)
    clarity_dark = max(16, min(42, int(round(dark_tint * 0.46))))
    glass = Image.alpha_composite(glass, Image.new("RGBA", (w, h), (8, 13, 24, clarity_dark)))

    # Объёмные внутренние каустики (мягкий свет сверху и холодный отсвет снизу, СТРОГО без обводки/линий)
    caustic = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(caustic)
    top_alpha = max(12, min(48, int(round(top_light * 0.95))))
    bot_alpha = max(6, min(28, int(round(bottom_light * 1.45))))
    cdraw.ellipse([-int(w * 0.12), -int(h * 0.55), int(w * 0.85), int(h * 0.52)], fill=(255, 255, 255, top_alpha))
    cdraw.ellipse([int(w * 0.25), int(h * 0.52), int(w * 1.15), int(h * 1.45)], fill=(155, 215, 255, bot_alpha))
    caustic = caustic.filter(ImageFilter.GaussianBlur(max(14, min(44, int(min(w, h) * 0.24)))))
    glass = Image.alpha_composite(glass, caustic)

    mask = make_smooth_rounded_mask(w, h, radius)
    out = src_rgba.copy()

    # Мягкая парящая тень позади стекла (визуально отделяет стекло от фона без обводки)
    sh_pad = 22
    sh_box_w = w + sh_pad * 2
    sh_box_h = h + sh_pad * 2
    sh_layer = Image.new("RGBA", (sh_box_w, sh_box_h), (0, 0, 0, 0))
    sh_draw = ImageDraw.Draw(sh_layer)
    sh_draw.rounded_rectangle(
        [sh_pad + 2, sh_pad + 6, sh_pad + w - 2, sh_pad + h + 4],
        radius=max(4, radius),
        fill=(2, 6, 16, 62),
    )
    sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(12))
    # Смещаем/обрезаем тень так, чтобы наклеить через alpha_composite безопасно
    sx1 = max(0, x1 - sh_pad)
    sy1 = max(0, y1 - sh_pad)
    sx2 = min(img_w, x2 + sh_pad)
    sy2 = min(img_h, y2 + sh_pad)
    if sx2 > sx1 and sy2 > sy1:
        sh_crop = sh_layer.crop((sx1 - (x1 - sh_pad), sy1 - (y1 - sh_pad), sx2 - (x1 - sh_pad), sy2 - (y1 - sh_pad)))
        out.alpha_composite(sh_crop, (sx1, sy1))

    out.paste(glass, (x1, y1), mask)
    return out

def load_font(size: int, bold: bool = False):
    p = FONT_BOLD_PATH if bold else FONT_REGULAR_PATH
    if p.exists():
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            pass
    return ImageFont.load_default()

def make_default_avatar(size: int = 200, text: str = "User") -> Image.Image:
    img = Image.new("RGBA", (size, size), (34, 42, 68, 255))
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([0, 0, int(size * 0.8), int(size * 0.8)], fill=(59, 130, 246, 120))
    gdraw.ellipse([int(size * 0.3), int(size * 0.3), size, size], fill=(139, 92, 246, 110))
    glow = glow.filter(ImageFilter.GaussianBlur(size // 6))
    img = Image.alpha_composite(img, glow)

    draw = ImageDraw.Draw(img)
    clean_txt = strip_all_emojis_for_image(text).strip()
    initials = clean_txt[:2].upper() if clean_txt else "U"
    font = load_font(int(size * 0.34), bold=True)
    draw.text((size // 2, size // 2), initials, font=font, fill=(255, 255, 255, 240), anchor="mm")
    return img

def _apply_volumetric_lighting(
    base_img: Image.Image,
    spots: List[Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]],
    blur_radius: int = 75,
    screen_strength: float = 0.55,
) -> Image.Image:
    """Накладывает мягкое объёмное студийное освещение (glow + screen bloom)."""
    w, h = base_img.size
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    for rect, color in spots:
        gdraw.ellipse(rect, fill=color)
    glow = glow.filter(ImageFilter.GaussianBlur(blur_radius))

    out = Image.alpha_composite(base_img.convert("RGBA"), glow)
    if screen_strength > 0:
        glow_rgb = glow.convert("RGB")
        if screen_strength < 1.0:
            glow_rgb = ImageEnhance.Brightness(glow_rgb).enhance(screen_strength)
        screened = ImageChops.screen(out.convert("RGB"), glow_rgb).convert("RGBA")
        out = screened
    return out


def _collect_plushpepe_and_nft_paths() -> Tuple[List[Path], List[Path]]:
    """Собирает пути к картинкам моделей Plush Pepe и обычных NFT-подарков."""
    pepe_paths: List[Path] = []
    if PLUSHPEPE_MODELS_DIR.exists():
        pepe_paths = sorted(
            p for p in PLUSHPEPE_MODELS_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in {".webp", ".png", ".jpg", ".jpeg"}
        )
    nft_paths: List[Path] = []
    if IMAGES_DIR.exists():
        nft_paths = sorted(
            p for p in IMAGES_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in {".webp", ".png", ".jpg", ".jpeg"}
        )
    return pepe_paths, nft_paths


def _build_nft_showcase_backdrop(
    width: int,
    height: int,
    seed_val: int = 0,
    favorite_gifts: Optional[List] = None,
    theme: str = "clan",
) -> Image.Image:
    """Создаёт объёмный фон с плюшевыми Пеппами, рандомными NFT и студийным освещением."""
    rng = random.Random(seed_val) if seed_val else random.Random()
    base = Image.new("RGBA", (width, height), (13, 18, 33, 255))

    if theme == "market":
        spots = [
            ((-80, -90, int(width * 0.48), int(height * 0.92)), (16, 185, 129, 130)),
            ((int(width * 0.48), -110, width + 90, int(height * 0.85)), (59, 130, 246, 115)),
            ((int(width * 0.22), int(height * 0.35), int(width * 0.82), height + 120), (139, 92, 246, 95)),
        ]
    else:
        spots = [
            ((-90, -100, int(width * 0.48), int(height * 0.85)), (56, 189, 248, 120)),
            ((int(width * 0.46), -90, width + 110, int(height * 0.88)), (168, 85, 247, 125)),
            ((int(width * 0.22), int(height * 0.38), int(width * 0.80), height + 130), (250, 204, 21, 88)),
        ]
    base = _apply_volumetric_lighting(base, spots, blur_radius=78, screen_strength=0.62)

    pepe_paths, nft_paths = _collect_plushpepe_and_nft_paths()
    chosen_paths: List[Path] = []

    if favorite_gifts:
        for fav in favorite_gifts[:4]:
            try:
                if isinstance(fav, sqlite3.Row):
                    if fav["is_upgraded"] and fav["model_name"]:
                        m_def = get_model_def(fav["gift_key"] or "pepe_heart", fav["model_name"])
                        mp = gift_model_image_path(fav["gift_key"] or "pepe_heart", m_def.filename)
                        if mp and mp.exists():
                            chosen_paths.append(mp)
                            continue
                    gp = gift_image_path(fav["gift_key"])
                else:
                    gp = gift_image_path(fav.key)
                if gp and gp.exists():
                    chosen_paths.append(gp)
            except Exception:
                pass

    pepe_pool = [p for p in pepe_paths if p not in chosen_paths]
    nft_pool = [p for p in nft_paths if p not in chosen_paths]
    rng.shuffle(pepe_pool)
    rng.shuffle(nft_pool)

    # Обязательно включаем плюшевых Пепп и рандомные NFT в композицию заднего фона
    mixed = chosen_paths + pepe_pool[:4] + nft_pool[:4]
    if not mixed:
        return base

    # Позиции (x_center_ratio, y_center_ratio, size, angle, blur, alpha, glow_rgb)
    layout = [
        (0.82, 0.48, int(height * 0.56), -7, 1.8, 225, (168, 85, 247)),   # Крупный герой справа
        (0.16, 0.30, int(height * 0.38), 11, 2.4, 195, (56, 189, 248)),   # Верх-лево
        (0.50, 0.52, int(height * 0.42), -4, 3.2, 165, (250, 204, 21)),   # Центр за стеклом
        (0.12, 0.82, int(height * 0.34), -12, 2.8, 190, (16, 185, 129)),  # Низ-лево
        (0.88, 0.84, int(height * 0.32), 14, 2.8, 185, (236, 72, 153)),   # Низ-право
        (0.35, 0.14, int(height * 0.28), 8, 3.6, 155, (99, 102, 241)),    # Верх-центр-лево
    ]

    glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow_layer)
    items_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    for idx, (rx, ry, target_sz, angle, blur_r, opacity, glow_rgb) in enumerate(layout):
        asset_path = mixed[idx % len(mixed)]
        try:
            art = Image.open(asset_path).convert("RGBA")
            art.thumbnail((target_sz, target_sz), Image.Resampling.LANCZOS)
            if angle:
                art = art.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
            if blur_r > 0:
                art = art.filter(ImageFilter.GaussianBlur(blur_r))
            if opacity < 255:
                r_ch, g_ch, b_ch, a_ch = art.split()
                a_ch = a_ch.point(lambda v: int(v * opacity / 255.0))
                art = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))

            cx = int(width * rx)
            cy = int(height * ry)
            halo_r = int(max(art.width, art.height) * 0.58)
            gdraw.ellipse(
                [cx - halo_r, cy - halo_r, cx + halo_r, cy + halo_r],
                fill=(glow_rgb[0], glow_rgb[1], glow_rgb[2], 78),
            )
            items_layer.alpha_composite(art, (cx - art.width // 2, cy - art.height // 2))
        except Exception:
            continue

    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(38))
    base = Image.alpha_composite(base, glow_layer)
    base = Image.alpha_composite(base, items_layer)

    # Лёгкая атмосферная вуаль сверху для контраста жидкого стекла
    veil = Image.new("RGBA", (width, height), (8, 12, 24, 58))
    return Image.alpha_composite(base, veil)


def make_default_clan_avatar(size: int = 190, tag: str = "CLAN", name: str = "Clan", clan_id: int = 0) -> Image.Image:
    """Возвращает минималистичную объёмную аватарку клана без шаблонов и обводок."""
    img = Image.new("RGBA", (size, size), (20, 28, 48, 255))
    img = _apply_volumetric_lighting(
        img,
        [
            ((-10, -10, int(size * 0.85), int(size * 0.85)), (59, 130, 246, 135)),
            ((int(size * 0.25), int(size * 0.25), size + 10, size + 10), (234, 179, 8, 115)),
        ],
        blur_radius=max(14, size // 6),
        screen_strength=0.65,
    )
    draw = ImageDraw.Draw(img)
    clean_tag = strip_all_emojis_for_image(tag or name or "CLAN").upper()[:5] or "CLAN"
    font = load_font(max(18, int(size * 0.23)), bold=True)
    draw.text((size // 2, size // 2), clean_tag, font=font, fill=(255, 255, 255, 235), anchor="mm")
    return img


async def generate_main_menu_banner() -> io.BytesIO:
    """Генерирует главное фото меню на основе menu_hero.jpg с названием бота в стиле жидкого стекла без обводок."""
    WIDTH, HEIGHT = 1000, 560
    hero_path = UI_ASSETS_DIR / "menu_hero.jpg"

    if hero_path.exists():
        try:
            raw_hero = Image.open(hero_path).convert("RGBA")
            img = ImageOps.fit(raw_hero, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
            rgb = ImageEnhance.Contrast(img.convert("RGB")).enhance(1.06)
            rgb = ImageEnhance.Color(rgb).enhance(1.08)
            img = rgb.convert("RGBA")
            img = _apply_volumetric_lighting(
                img,
                [
                    ((int(WIDTH * 0.18), int(HEIGHT * 0.08), int(WIDTH * 0.64), int(HEIGHT * 0.88)), (250, 204, 21, 32)),
                    ((int(WIDTH * 0.56), -40, WIDTH + 60, int(HEIGHT * 0.72)), (59, 130, 246, 40)),
                ],
                blur_radius=75,
                screen_strength=0.45,
            )
        except Exception as e:
            log.warning("Не удалось загрузить menu_hero.jpg: %s", e)
            img = _build_nft_showcase_backdrop(WIDTH, HEIGHT, seed_val=777, theme="clan")
    else:
        img = _build_nft_showcase_backdrop(WIDTH, HEIGHT, seed_val=777, theme="clan")

    # Название бота на главном фото (жидкое стекло без обводки)
    img = apply_liquid_glass_panel(
        img,
        box=(56, HEIGHT - 122, WIDTH - 56, HEIGHT - 32),
        radius=24,
        blur_radius=20,
        dark_tint=76,
        top_light=42,
        bottom_light=10,
    )
    draw = ImageDraw.Draw(img)
    draw.text((WIDTH // 2, HEIGHT - 89), "NEW NFT BOT", font=load_font(40, bold=True), fill=(255, 255, 255), anchor="mm")
    draw.text((WIDTH // 2, HEIGHT - 50), "NFT GIFTS  •  MARKETPLACE  •  CLANS", font=load_font(15, bold=True), fill=(250, 204, 21), anchor="mm")

    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.name = "menu.png"
    bio.seek(0)
    return bio


async def generate_market_banner() -> io.BytesIO:
    """Генерирует объёмный баннер NFT Маркета с улучшенным освещением и жидким стеклом без обводки."""
    WIDTH, HEIGHT = 1000, 440
    market_hero = UI_ASSETS_DIR / "market_hero.jpg"

    if market_hero.exists():
        try:
            raw = Image.open(market_hero).convert("RGBA")
            img = ImageOps.fit(raw, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
            img = _apply_volumetric_lighting(
                img,
                [
                    ((-40, -60, 460, 380), (16, 185, 129, 75)),
                    ((520, -60, 1040, 400), (59, 130, 246, 70)),
                ],
                blur_radius=70,
                screen_strength=0.50,
            )
        except Exception:
            img = _build_nft_showcase_backdrop(WIDTH, HEIGHT, seed_val=2025, theme="market")
    else:
        img = _build_nft_showcase_backdrop(WIDTH, HEIGHT, seed_val=2025, theme="market")

    # Мягко добавляем 2 светящихся Plush Pepe по краям для связи с коллекцией
    for idx, (m_name, cx, cy) in enumerate([("Emerald Plush", 145, 220), ("Midas Pepe", WIDTH - 145, 220)]):
        mp = PLUSHPEPE_MODELS_DIR / f"{m_name}.webp"
        if mp.exists():
            try:
                pepe = Image.open(mp).convert("RGBA")
                pepe.thumbnail((170, 170), Image.Resampling.LANCZOS)
                pepe = pepe.rotate(10 if idx == 0 else -10, resample=Image.Resampling.BICUBIC, expand=True)
                pepe = pepe.filter(ImageFilter.GaussianBlur(1.4))
                r_ch, g_ch, b_ch, a_ch = pepe.split()
                a_ch = a_ch.point(lambda v: int(v * 0.72))
                pepe = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))
                img.alpha_composite(pepe, (cx - pepe.width // 2, cy - pepe.height // 2))
            except Exception:
                pass

    # Главная панель жидкого стекла (строго без обводки)
    img = apply_liquid_glass_panel(
        img,
        box=(56, 56, WIDTH - 56, HEIGHT - 56),
        radius=30,
        blur_radius=22,
        dark_tint=64,
        top_light=48,
        bottom_light=10,
    )

    draw = ImageDraw.Draw(img)
    f_badge = load_font(16, bold=True)
    f_title = load_font(54, bold=True)
    f_sub = load_font(23, bold=True)
    f_meta = load_font(18, bold=True)

    draw.text((WIDTH // 2, 118), "P2P TRADE EXCHANGE", font=f_badge, fill=(52, 211, 153), anchor="mm")
    draw.text((WIDTH // 2, 194), "NFT MARKETPLACE", font=f_title, fill=(255, 255, 255), anchor="mm")
    draw.text((WIDTH // 2, 268), "Pepe, Locket, Cap, Cup, Bonded Ring", font=f_sub, fill=(226, 232, 240), anchor="mm")
    draw.text((WIDTH // 2, 322), "Комиссия 15%  •  От 1,000 до 100 млрд Stars", font=f_meta, fill=(250, 204, 21), anchor="mm")

    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.name = "market.png"
    bio.seek(0)
    return bio


async def generate_clans_hub_banner() -> io.BytesIO:
    """Генерирует баннер раздела Кланы с плюшевыми Пеппами, рандомными NFT на фоне, освещением и жидким стеклом."""
    WIDTH, HEIGHT = 1000, 440
    img = _build_nft_showcase_backdrop(WIDTH, HEIGHT, seed_val=0, theme="clan")

    img = apply_liquid_glass_panel(
        img,
        box=(56, 56, WIDTH - 56, HEIGHT - 56),
        radius=30,
        blur_radius=22,
        dark_tint=66,
        top_light=48,
        bottom_light=10,
    )

    draw = ImageDraw.Draw(img)
    f_badge = load_font(16, bold=True)
    f_title = load_font(52, bold=True)
    f_sub = load_font(23, bold=True)
    f_meta = load_font(18, bold=True)

    draw.text((WIDTH // 2, 118), "CLAN SYNDICATES  •  NEW NFT", font=f_badge, fill=(250, 204, 21), anchor="mm")
    draw.text((WIDTH // 2, 194), "КЛАНЫ И АЛЬЯНСЫ", font=f_title, fill=(255, 255, 255), anchor="mm")
    draw.text((WIDTH // 2, 268), "Общая казна, уникальные гербы и клановый рейтинг", font=f_sub, fill=(226, 232, 240), anchor="mm")
    draw.text((WIDTH // 2, 322), "Бонус к шансу выигрыша подарков от +1% до +45%", font=f_meta, fill=(52, 211, 153), anchor="mm")

    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.name = "clans_hub.png"
    bio.seek(0)
    return bio

def make_rainbow_gradient_bg(size: int) -> Image.Image:
    """Создаёт яркий мифический радужный градиент."""
    stops = [
        (0.00, (255, 59, 107)),   # Pink-Red
        (0.18, (255, 138, 36)),   # Orange
        (0.36, (250, 214, 48)),   # Gold-Yellow
        (0.54, (45, 224, 138)),   # Emerald
        (0.72, (34, 211, 238)),   # Cyan
        (0.86, (79, 124, 255)),   # Blue
        (1.00, (168, 85, 247)),   # Violet
    ]
    def _sample(t: float) -> Tuple[int, int, int]:
        t = max(0.0, min(1.0, t))
        for idx in range(len(stops) - 1):
            t0, c0 = stops[idx]
            t1, c1 = stops[idx + 1]
            if t <= t1:
                lt = (t - t0) / max(1e-6, (t1 - t0))
                return (
                    int(c0[0] + (c1[0] - c0[0]) * lt),
                    int(c0[1] + (c1[1] - c0[1]) * lt),
                    int(c0[2] + (c1[2] - c0[2]) * lt),
                )
        return stops[-1][1]

    # Диагональный градиент на полосе шириной size*2 + поворот 45 deg для идеальной скорости и гладкости
    strip_w = max(64, size)
    strip = Image.new("RGBA", (strip_w, 1))
    sdraw = ImageDraw.Draw(strip)
    for x in range(strip_w):
        col = _sample(x / float(max(1, strip_w - 1)))
        sdraw.point((x, 0), fill=col + (255,))
    base = strip.resize((size * 2, size * 2), Image.Resampling.BILINEAR).rotate(-35)
    left = (base.width - size) // 2
    top = (base.height - size) // 2
    img = base.crop((left, top, left + size, top + size))

    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    c = size // 2
    r = int(size * 0.38)
    gdraw.ellipse([c - r, c - r, c + r, c + r], fill=(255, 255, 255, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(max(4, size // 7)))
    return Image.alpha_composite(img, glow)

def make_radial_gradient_bg(size: int, center_hex: str, edge_hex: str, backdrop_key: str = "") -> Image.Image:
    """Создаёт плавный радиальный (или радужный) градиент как на карточках коллекционных подарков Telegram."""
    if backdrop_key == "rainbow":
        return make_rainbow_gradient_bg(size)
    c_rgb = parse_hex_rgb(center_hex, (70, 90, 120))
    e_rgb = parse_hex_rgb(edge_hex, (20, 26, 38))
    base = Image.new("RGBA", (size, size), e_rgb + (255,))
    draw = ImageDraw.Draw(base)
    steps = 72
    cx, cy = size / 2.0, size / 2.0
    max_r = size * 0.72
    for i in range(steps):
        t = i / float(steps - 1)
        r = max_r * (1.0 - t)
        blend = t ** 1.35
        col = (
            int(e_rgb[0] + (c_rgb[0] - e_rgb[0]) * blend),
            int(e_rgb[1] + (c_rgb[1] - e_rgb[1]) * blend),
            int(e_rgb[2] + (c_rgb[2] - e_rgb[2]) * blend),
            255,
        )
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    return base

def _load_model_rgba(m_path: Path, target_size: Tuple[int, int]) -> Image.Image:
    """Загружает модель в RGBA и при необходимости удаляет сплошной чёрный фон у JPEG."""
    m_img = Image.open(m_path).convert("RGBA")
    is_opaque_jpeg = m_path.suffix.lower() in (".jpg", ".jpeg") or min(m_img.getchannel("A").getextrema()) == 255
    if is_opaque_jpeg:
        w, h = m_img.size
        corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
        dark_corners = sum(1 for cx, cy in corners if max(m_img.getpixel((cx, cy))[:3]) <= 24)
        if dark_corners >= 3:
            for cx, cy in corners:
                if max(m_img.getpixel((cx, cy))[:3]) <= 24:
                    ImageDraw.floodfill(m_img, (cx, cy), (0, 0, 0, 0), thresh=26)
            # Смягчаем края альфа-канала после заливки
            r_c, g_c, b_c, a_c = m_img.split()
            a_c = a_c.filter(ImageFilter.GaussianBlur(0.8))
            m_img = Image.merge("RGBA", (r_c, g_c, b_c, a_c))
        else:
            rmask = make_smooth_rounded_mask(w, h, max(16, int(min(w, h) * 0.16)))
            out_r = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            out_r.paste(m_img, (0, 0), rmask)
            m_img = out_r
    m_img.thumbnail(target_size, Image.Resampling.LANCZOS)
    return m_img

def _render_upgraded_slot_thumbnail(
    slot_w: int,
    slot_h: int,
    model_name: str,
    backdrop_key: str,
    gift_key: str = "pepe_heart",
) -> Image.Image:
    bdef = BACKDROPS_BY_KEY.get(backdrop_key) or PLUSHPEPE_BACKDROPS[0]
    mdef = get_model_def(gift_key, model_name)
    grad = make_radial_gradient_bg(slot_w, bdef.center_hex, bdef.edge_hex, backdrop_key=bdef.key)

    m_path = gift_model_image_path(gift_key, mdef.filename)
    if m_path and m_path.exists():
        try:
            m_img = _load_model_rgba(m_path, (int(slot_w * 0.78), int(slot_h * 0.78)))
            mx = (slot_w - m_img.width) // 2
            my = (slot_h - m_img.height) // 2
            grad.paste(m_img, (mx, my), m_img)
        except Exception:
            pass

    mask = make_smooth_rounded_mask(slot_w, slot_h, 18)
    out = Image.new("RGBA", (slot_w, slot_h), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask)
    return out

async def generate_gift_card_image(gift: GiftDef) -> Optional[io.BytesIO]:
    """Генерирует минималистичную карточку обычного NFT-подарка в стиле жидкого стекла."""
    img_p = gift_image_path(gift.key)
    if not img_p or not img_p.exists():
        return None

    SIZE = 720
    img = Image.new("RGBA", (SIZE, SIZE), (16, 22, 36, 255))

    if gift.stars >= 80_000:
        c1, c2 = (234, 179, 8, 115), (168, 85, 247, 95)
    elif gift.stars >= 15_000:
        c1, c2 = (139, 92, 246, 115), (59, 130, 246, 95)
    elif gift.stars >= 2_000:
        c1, c2 = (59, 130, 246, 110), (14, 165, 233, 90)
    else:
        c1, c2 = (16, 185, 129, 95), (59, 130, 246, 85)

    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([-40, -40, 440, 440], fill=c1)
    gdraw.ellipse([260, 180, 760, 700], fill=c2)
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    img = Image.alpha_composite(img, glow)

    # Центральная стеклянная витрина (строго без обводки)
    img = apply_liquid_glass_panel(
        img,
        box=(34, 34, SIZE - 34, 496),
        radius=28,
        blur_radius=20,
        dark_tint=48,
        top_light=38,
        bottom_light=8,
    )
    # Верхние стеклянные бейджи
    img = apply_liquid_glass_panel(img, (54, 54, 214, 96), radius=13, blur_radius=12, dark_tint=56, top_light=34, bottom_light=8)
    img = apply_liquid_glass_panel(img, (SIZE - 214, 54, SIZE - 54, 96), radius=13, blur_radius=12, dark_tint=56, top_light=34, bottom_light=8)

    try:
        g_img = Image.open(img_p).convert("RGBA")
        g_img.thumbnail((340, 340), Image.Resampling.LANCZOS)
        gx = (SIZE - g_img.width) // 2
        gy = 104 + (365 - g_img.height) // 2
        img.paste(g_img, (gx, gy), g_img)
    except Exception:
        return None

    # Нижняя карточка характеристик в стиле жидкого стекла (без обводки)
    img = apply_liquid_glass_panel(
        img,
        box=(34, 514, SIZE - 34, SIZE - 34),
        radius=26,
        blur_radius=20,
        dark_tint=72,
        top_light=42,
        bottom_light=10,
    )

    draw = ImageDraw.Draw(img)
    f_badge = load_font(16, bold=True)
    f_title = load_font(30, bold=True)
    f_sub = load_font(19, bold=True)
    f_val = load_font(26, bold=True)

    draw.text((134, 75), "NFT GIFT", font=f_badge, fill=(226, 232, 240), anchor="mm")
    draw.text((SIZE - 134, 75), f"+{gift.xp:,} XP", font=f_badge, fill=(96, 165, 250), anchor="mm")

    clean_title = strip_all_emojis_for_image(gift.name)
    if len(clean_title) > 28:
        clean_title = clean_title[:26] + ".."
    clean_model = strip_all_emojis_for_image(gift.model_name)

    draw.text((62, 540), clean_title, font=f_title, fill=(255, 255, 255))
    draw.text((62, 582), f"Model: {clean_model}", font=f_sub, fill=(203, 213, 225))

    draw.rounded_rectangle([62, 624, 66, 660], radius=2, fill=(250, 204, 21, 235))
    draw.text((78, 628), f"{fmt_stars_compact(gift.stars)} STARS", font=f_val, fill=(250, 204, 21))

    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.name = f"gift_{gift.key}.png"
    bio.seek(0)
    return bio

async def generate_upgraded_gift_image(
    model: PlushModelDef,
    backdrop: BackdropDef,
    upgrade_num: int,
    upgraded_stars: int,
    list_price: Optional[int] = None,
    gift_key: str = "pepe_heart",
    buff_badge: str = "",
) -> io.BytesIO:
    SIZE = 720
    img = make_radial_gradient_bg(SIZE, backdrop.center_hex, backdrop.edge_hex, backdrop_key=backdrop.key)
    is_mono = is_monochrome_combo(model.name, backdrop.key)

    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for px, py, pr, alpha in [
        (115, 145, 4, 140), (610, 170, 5, 150), (145, 470, 3, 120),
        (585, 440, 4, 130), (210, 95, 3, 115), (520, 110, 3, 115),
    ]:
        odraw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(255, 255, 255, alpha))
    img = Image.alpha_composite(img, overlay)

    f_badge = load_font(19, bold=True)
    f_title = load_font(30, bold=True)
    f_sub = load_font(20, bold=False)
    f_val = load_font(26, bold=True)

    title_upper = get_upgraded_gift_title(gift_key).upper()
    # Бейджи в стиле жидкого стекла (строго без обводки)
    img = apply_liquid_glass_panel(img, (34, 34, 316, 82), radius=16, blur_radius=16, dark_tint=72, top_light=42, bottom_light=10)
    draw = ImageDraw.Draw(img)
    draw.text((175, 58), f"{title_upper} #{upgrade_num}", font=f_badge, fill=(255, 255, 255), anchor="mm")

    rarity_color = (
        (244, 114, 182) if backdrop.rarity_label == "Мифический"
        else (250, 204, 21) if backdrop.rarity_label == "Ультра-редкий"
        else (96, 165, 250) if backdrop.rarity_label == "Редкий"
        else (192, 132, 252) if backdrop.rarity_label == "Необычный"
        else (52, 211, 153)
    )
    img = apply_liquid_glass_panel(img, (SIZE - 260, 34, SIZE - 34, 82), radius=16, blur_radius=16, dark_tint=72, top_light=42, bottom_light=10)
    draw = ImageDraw.Draw(img)
    draw.text((SIZE - 147, 58), backdrop.rarity_label.upper(), font=load_font(17, bold=True), fill=rarity_color, anchor="mm")

    if is_mono:
        img = apply_liquid_glass_panel(img, (SIZE - 260, 92, SIZE - 34, 130), radius=14, blur_radius=14, dark_tint=78, top_light=38, bottom_light=10)
        draw = ImageDraw.Draw(img)
        draw.text((SIZE - 147, 111), "MONOCHROME x6", font=load_font(15, bold=True), fill=(125, 211, 252), anchor="mm")

    if buff_badge:
        img = apply_liquid_glass_panel(img, (34, 92, 316, 130), radius=14, blur_radius=14, dark_tint=78, top_light=38, bottom_light=10)
        draw = ImageDraw.Draw(img)
        draw.text((175, 111), buff_badge[:28], font=load_font(14, bold=True), fill=(167, 243, 208), anchor="mm")

    # Модель в центре
    m_path = gift_model_image_path(gift_key, model.filename)
    if m_path and m_path.exists():
        try:
            m_img = _load_model_rgba(m_path, (390, 390))
            mx = (SIZE - m_img.width) // 2
            my = 110 + (390 - m_img.height) // 2
            img.paste(m_img, (mx, my), m_img)
        except Exception as e:
            log.warning("Ошибка загрузки модели %s: %s", model.filename, e)

    # Нижняя стеклянная карточка характеристик (жидкое стекло без обводки)
    img = apply_liquid_glass_panel(img, (34, 514, SIZE - 34, SIZE - 30), radius=26, blur_radius=20, dark_tint=84, top_light=44, bottom_light=10)
    draw = ImageDraw.Draw(img)

    draw.text((62, 538), f"Model: {model.name} ({model.chance_pct}%)", font=f_title, fill=(255, 255, 255))
    mono_note = " • MONOCHROME" if is_mono else ""
    draw.text((62, 582), f"Backdrop: {backdrop.name} ({backdrop.chance_pct}%){mono_note}", font=f_sub, fill=(226, 232, 240))

    if list_price is not None:
        draw.rounded_rectangle([62, 624, 66, 658], radius=2, fill=(52, 211, 153, 235))
        draw.text((78, 626), f"MARKET: {fmt_stars_compact(list_price)} STARS", font=f_val, fill=(52, 211, 153))
        draw.text((SIZE - 62, 632), f"Est: {fmt_stars_compact(upgraded_stars)}", font=load_font(18, bold=True), fill=(250, 204, 21), anchor="ra")
    else:
        draw.rounded_rectangle([62, 624, 66, 658], radius=2, fill=(250, 204, 21, 235))
        draw.text((78, 626), f"EST. VALUE: ~{fmt_stars_compact(upgraded_stars)} STARS", font=f_val, fill=(250, 204, 21))

    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.name = f"{gift_key}_{upgrade_num}.png"
    bio.seek(0)
    return bio

async def generate_check_card_image(
    amount_stars: Optional[int],
    creator_name: str,
    target_label: str = "Для всех игроков",
    claimed_by: Optional[str] = None,
    max_claims: int = 1,
    claimed_count: int = 0,
    per_claim_stars: Optional[int] = None,
    has_password: bool = False,
) -> io.BytesIO:
    """Генерирует карточку чека поверх главного фото меню (menu_hero.jpg) в стиле жидкого стекла без обводки."""
    WIDTH, HEIGHT = 920, 440
    hero_path = UI_ASSETS_DIR / "menu_hero.jpg"
    base = None
    if hero_path.exists():
        try:
            raw_hero = Image.open(hero_path).convert("RGBA")
            base = ImageOps.fit(raw_hero, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
            veil = Image.new("RGBA", (WIDTH, HEIGHT), (8, 12, 24, 38))
            base = Image.alpha_composite(base, veil)
        except Exception:
            base = None

    if base is None:
        base = Image.new("RGBA", (WIDTH, HEIGHT), (16, 22, 36, 255))
        glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        gdraw.ellipse([-50, -70, 460, 360], fill=(37, 99, 235, 115))
        gdraw.ellipse([480, -40, 990, 380], fill=(139, 92, 246, 90))
        gdraw.ellipse([240, 150, 700, 470], fill=(16, 185, 129, 75) if claimed_by else (234, 179, 8, 70))
        glow = glow.filter(ImageFilter.GaussianBlur(65))
        base = Image.alpha_composite(base, glow)

    # Верхняя панель жидкого стекла (без обводки)
    img = apply_liquid_glass_panel(
        base,
        box=(36, 32, WIDTH - 36, 298),
        radius=28,
        blur_radius=20,
        dark_tint=76,
        top_light=42,
        bottom_light=10,
    )
    # Верхние стеклянные бейджи: тип / защита паролем / статус
    img = apply_liquid_glass_panel(img, (60, 56, 286, 92), radius=13, blur_radius=12, dark_tint=52, top_light=34, bottom_light=8)
    img = apply_liquid_glass_panel(img, (346, 56, 574, 92), radius=13, blur_radius=12, dark_tint=52, top_light=34, bottom_light=8)
    img = apply_liquid_glass_panel(img, (WIDTH - 246, 56, WIDTH - 60, 92), radius=13, blur_radius=12, dark_tint=52, top_light=34, bottom_light=8)

    # Нижняя панель жидкого стекла (без обводки)
    img = apply_liquid_glass_panel(
        img,
        box=(36, 314, WIDTH - 36, HEIGHT - 32),
        radius=24,
        blur_radius=20,
        dark_tint=72,
        top_light=34,
        bottom_light=8,
    )

    draw = ImageDraw.Draw(img)

    c_clean = strip_all_emojis_for_image(creator_name, fallback_id=None)
    t_clean = strip_all_emojis_for_image(target_label)

    draw.text((173, 74), "NFT STARS VOUCHER", font=load_font(15, bold=True), fill=(203, 213, 225), anchor="mm")

    pwd_lbl = "PASSWORD LOCKED" if has_password else "NO PASSWORD"
    pwd_col = (250, 204, 21) if has_password else (125, 211, 252)
    draw.text((460, 74), pwd_lbl, font=load_font(15, bold=True), fill=pwd_col, anchor="mm")

    fully_claimed = bool(claimed_by) or (max_claims > 1 and claimed_count >= max_claims)
    status_lbl = "CLAIMED" if fully_claimed else (f"CLAIMS {claimed_count}/{max_claims}" if max_claims > 1 else "ACTIVE CHECK")
    status_col = (52, 211, 153) if fully_claimed else (250, 204, 21)
    draw.text((WIDTH - 153, 74), status_lbl, font=load_font(15, bold=True), fill=status_col, anchor="mm")

    display_stars = per_claim_stars if (per_claim_stars and max_claims > 1) else amount_stars
    if display_stars is not None:
        amount_str = f"{fmt_stars_compact(display_stars)} STARS"
        if max_claims > 1 and amount_stars is not None:
            rub_str = f"PER USER  •  TOTAL {fmt_stars_compact(amount_stars)} STARS ({claimed_count}/{max_claims})"
        else:
            rub_str = f"~{fmt_stars_compact(int(round(display_stars * STAR_RUB_RATE)))} RUB"
    else:
        amount_str = "STARS VOUCHER"
        rub_str = "TELEGRAM STARS CHECK"

    draw.text((WIDTH // 2, 178), amount_str, font=load_font(62, bold=True), fill=(255, 255, 255), anchor="mm")
    draw.text((WIDTH // 2, 240), rub_str, font=load_font(20, bold=True), fill=(250, 204, 21), anchor="mm")

    if fully_claimed and claimed_by:
        cl_clean = strip_all_emojis_for_image(claimed_by)
        footer_left = f"От: {c_clean[:20]}"
        footer_right = f"Активировал: {cl_clean[:22]}"
        accent_col = (52, 211, 153, 235)
    elif fully_claimed:
        footer_left = f"От: {c_clean[:20]}"
        footer_right = f"Активаций: {claimed_count}/{max_claims}"
        accent_col = (52, 211, 153, 235)
    else:
        footer_left = f"От: {c_clean[:22]}"
        footer_right = f"Кому: {t_clean[:24]}"
        accent_col = (250, 204, 21, 235)

    draw.rounded_rectangle([60, 344, 64, 378], radius=2, fill=accent_col)
    draw.text((78, 361), footer_left, font=load_font(20, bold=True), fill=(255, 255, 255), anchor="lm")
    draw.text((WIDTH - 60, 361), footer_right, font=load_font(20, bold=True), fill=(203, 213, 225), anchor="rm")

    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.name = "star_check.png"
    bio.seek(0)
    return bio

async def generate_profile_card_image(
    user_name: str,
    user_sys_id: int,
    stars_balance: int,
    user_xp: int,
    rank: int,
    favorite_gifts: List,
    avatar_bytes: Optional[bytes] = None,
    clan_tag: Optional[str] = None,
    custom_bg_path: Optional[str] = None,
    fallback_username: Optional[str] = None,
    telegram_user_id: Optional[int] = None,
) -> io.BytesIO:
    WIDTH, HEIGHT = 1000, 560
    clean_name = strip_all_emojis_for_image(
        user_name,
        fallback_username=fallback_username,
        fallback_id=telegram_user_id or user_sys_id,
    )

    has_custom_bg = False
    resolved_bg_path = resolve_user_bg_path(telegram_user_id, custom_bg_path)
    if resolved_bg_path and resolved_bg_path.exists():
        try:
            with Image.open(resolved_bg_path) as custom_img_raw:
                custom_img = custom_img_raw.convert("RGBA")
            base_bg = ImageOps.fit(custom_img, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
            # Деликатное затемнение без мыла, чтобы фон чётко искажался и размывался за жидким стеклом
            darken_overlay = Image.new("RGBA", (WIDTH, HEIGHT), (8, 12, 22, 34))
            base_bg = Image.alpha_composite(base_bg, darken_overlay)
            has_custom_bg = True
        except Exception as e:
            log.warning("Не удалось обработать кастомный фон пользователя: %s", e)

    if not has_custom_bg:
        base_bg = Image.new("RGBA", (WIDTH, HEIGHT), (16, 22, 36, 255))
        glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse([-40, -60, 420, 380], fill=(37, 99, 235, 105))
        glow_draw.ellipse([540, -80, 1020, 320], fill=(139, 92, 246, 85))
        glow_draw.ellipse([260, 260, 780, 620], fill=(14, 165, 233, 65))
        glow = glow.filter(ImageFilter.GaussianBlur(65))
        base_bg = Image.alpha_composite(base_bg, glow)

    # Верхняя панель жидкого стекла (строго без обводки)
    base_bg = apply_liquid_glass_panel(
        base_bg,
        box=(36, 36, 964, 282),
        radius=28,
        blur_radius=20,
        dark_tint=68,
        top_light=42,
        bottom_light=10,
    )
    # Нижняя панель для избранного (жидкое стекло без обводки)
    base_bg = apply_liquid_glass_panel(
        base_bg,
        box=(36, 300, 964, 514),
        radius=28,
        blur_radius=20,
        dark_tint=64,
        top_light=34,
        bottom_light=8,
    )

    draw = ImageDraw.Draw(base_bg)

    font_title = load_font(38, bold=True)
    font_sub = load_font(21, bold=True)
    font_small = load_font(18, bold=True)
    font_stat_val = load_font(33, bold=True)
    font_stat_lbl = load_font(15, bold=True)

    av_size = 190
    if avatar_bytes:
        try:
            loaded_av = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            av_img = ImageOps.fit(loaded_av, (av_size, av_size), method=Image.Resampling.LANCZOS)
        except Exception:
            av_img = make_default_avatar(av_size, clean_name)
    else:
        av_img = make_default_avatar(av_size, clean_name)

    av_mask = make_smooth_rounded_mask(av_size, av_size, 26)
    av_x, av_y = 62, 64
    base_bg.paste(av_img, (av_x, av_y), av_mask)

    text_x = 282
    curr_x = text_x
    if clan_tag:
        tag_str = f"[{clan_tag.upper()}] "
        draw.text((curr_x, 68), tag_str, font=font_title, fill=(250, 204, 21))
        bbox = draw.textbbox((curr_x, 68), tag_str, font=font_title)
        curr_x = bbox[2]

    disp_name = clean_name if len(clean_name) <= 17 else (clean_name[:15] + "..")
    draw.text((curr_x, 68), disp_name, font=font_title, fill=(255, 255, 255))

    lvl, cur_xp, req_xp, ratio = calculate_xp_level_info(user_xp)
    draw.text((text_x, 122), f"LEVEL {lvl}  •  {cur_xp:,} / {req_xp:,} XP", font=font_sub, fill=(226, 232, 240))

    bar_x, bar_y, bar_w, bar_h = text_x, 158, 410, 11
    draw_rounded_rect(draw, [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=5, fill=(255, 255, 255, 42))
    fill_w = max(12, int(bar_w * ratio))
    draw_rounded_rect(draw, [bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=5, fill=(250, 204, 21, 240))

    draw.text((936, 74), f"ID #{user_sys_id}", font=font_small, fill=(203, 213, 225), anchor="ra")

    stats_y = 198
    draw.rounded_rectangle([text_x, stats_y + 2, text_x + 4, stats_y + 48], radius=2, fill=(250, 204, 21, 235))
    draw.text((text_x + 15, stats_y), "STARS BALANCE", font=font_stat_lbl, fill=(203, 213, 225))
    draw.text((text_x + 15, stats_y + 18), f"{fmt_stars_compact(stars_balance)} STARS", font=font_stat_val, fill=(255, 255, 255))

    rank_x = text_x + 310
    draw.rounded_rectangle([rank_x, stats_y + 2, rank_x + 4, stats_y + 48], radius=2, fill=(96, 165, 250, 235))
    draw.text((rank_x + 15, stats_y), "GLOBAL RANK", font=font_stat_lbl, fill=(203, 213, 225))
    draw.text((rank_x + 15, stats_y + 18), f"#{rank}", font=font_stat_val, fill=(255, 255, 255))

    draw.text((62, 318), "FAVORITES", font=font_stat_lbl, fill=(203, 213, 225))

    slot_y = 352
    slot_w, slot_h = 113, 113
    spacing = 15
    start_x = 62

    for i in range(7):
        cur_x = start_x + i * (slot_w + spacing)
        base_bg = apply_liquid_glass_panel(
            base_bg,
            box=(cur_x, slot_y, cur_x + slot_w, slot_y + slot_h),
            radius=18,
            blur_radius=12,
            dark_tint=42,
            top_light=32,
            bottom_light=10,
        )
        draw = ImageDraw.Draw(base_bg)

        if i < len(favorite_gifts):
            fav_item = favorite_gifts[i]
            if isinstance(fav_item, sqlite3.Row):
                is_upg = bool(fav_item["is_upgraded"])
                g = GIFTS_BY_KEY.get(fav_item["gift_key"])
                if is_upg:
                    slot_thumb = _render_upgraded_slot_thumbnail(
                        slot_w,
                        slot_h,
                        fav_item["model_name"] or "Amalgam",
                        fav_item["backdrop_key"] or "black",
                        gift_key=fav_item["gift_key"] or "pepe_heart",
                    )
                    base_bg.paste(slot_thumb, (cur_x, slot_y), slot_thumb)
                    continue
            else:
                g = fav_item

            if g:
                img_p = gift_image_path(g.key)
                if img_p and img_p.exists():
                    try:
                        g_img = Image.open(img_p).convert("RGBA")
                        g_img.thumbnail((78, 78), Image.Resampling.LANCZOS)
                        gx = cur_x + (slot_w - g_img.width) // 2
                        gy = slot_y + (slot_h - g_img.height) // 2
                        base_bg.paste(g_img, (gx, gy), g_img)
                    except Exception:
                        pass
                else:
                    clean_g_name = g.name.split('(')[0].strip()[:9]
                    draw.text((cur_x + slot_w // 2, slot_y + slot_h // 2 - 8), clean_g_name, font=load_font(13, bold=True), fill=(255, 255, 255), anchor="mm")
                    draw.text((cur_x + slot_w // 2, slot_y + slot_h - 22), f"{fmt_stars_compact(g.stars)}", font=load_font(11, bold=True), fill=(250, 204, 21), anchor="mm")
        else:
            cx, cy = cur_x + slot_w // 2, slot_y + slot_h // 2
            arm = 11
            thick = 2
            draw.line([(cx - arm, cy - arm), (cx + arm, cy + arm)], fill=(255, 255, 255, 65), width=thick)
            draw.line([(cx + arm, cy - arm), (cx - arm, cy + arm)], fill=(255, 255, 255, 65), width=thick)

    if has_custom_bg:
        base_bg = apply_liquid_glass_panel(base_bg, (36, HEIGHT - 40, 224, HEIGHT - 12), radius=10, blur_radius=12, dark_tint=60, top_light=28, bottom_light=8)
        draw = ImageDraw.Draw(base_bg)
        draw.text((130, HEIGHT - 26), "CUSTOM BACKGROUND", font=load_font(12, bold=True), fill=(241, 245, 249), anchor="mm")

    bio = io.BytesIO()
    base_bg.save(bio, "PNG")
    bio.name = "profile.png"
    bio.seek(0)
    return bio

async def generate_clan_card_image(
    clan_name: str,
    clan_tag: str,
    clan_sys_id: int,
    clan_xp: int,
    treasury_stars: int,
    members_count: int,
    max_members: int,
    favorite_gifts: List[GiftDef],
    avatar_path: Optional[str] = None
) -> io.BytesIO:
    WIDTH, HEIGHT = 1000, 560
    clean_name = strip_all_emojis_for_image(clan_name, fallback_id=clan_sys_id)
    clean_tag = strip_all_emojis_for_image(clan_tag, fallback_id=clan_sys_id).upper()

    # Объёмный задний фон с плюшевыми Пеппами, рандомными NFT и улучшенным студийным светом
    base_bg = _build_nft_showcase_backdrop(
        WIDTH,
        HEIGHT,
        seed_val=clan_sys_id or 1,
        favorite_gifts=favorite_gifts,
        theme="clan",
    )

    # Верхняя панель жидкого стекла (строго без обводки, как в профиле)
    base_bg = apply_liquid_glass_panel(
        base_bg,
        box=(36, 36, 964, 282),
        radius=28,
        blur_radius=20,
        dark_tint=64,
        top_light=48,
        bottom_light=10,
    )
    # Нижняя панель для избранного клана (жидкое стекло без обводки)
    base_bg = apply_liquid_glass_panel(
        base_bg,
        box=(36, 300, 964, 514),
        radius=28,
        blur_radius=20,
        dark_tint=60,
        top_light=38,
        bottom_light=8,
    )

    draw = ImageDraw.Draw(base_bg)

    font_title = load_font(38, bold=True)
    font_sub = load_font(21, bold=True)
    font_small = load_font(18, bold=True)
    font_stat_val = load_font(30, bold=True)
    font_stat_lbl = load_font(15, bold=True)

    av_size = 190
    if avatar_path and Path(avatar_path).exists():
        try:
            loaded_av = Image.open(avatar_path).convert("RGBA")
            av_img = ImageOps.fit(loaded_av, (av_size, av_size), method=Image.Resampling.LANCZOS)
        except Exception:
            av_img = make_default_clan_avatar(av_size, clean_tag, clean_name, clan_id=clan_sys_id)
    else:
        av_img = make_default_clan_avatar(av_size, clean_tag, clean_name, clan_id=clan_sys_id)

    av_mask = make_smooth_rounded_mask(av_size, av_size, 26)
    av_x, av_y = 62, 64
    base_bg.paste(av_img, (av_x, av_y), av_mask)

    text_x = 282
    tag_str = f"[{clean_tag}] "
    draw.text((text_x, 68), tag_str, font=font_title, fill=(250, 204, 21))
    bbox = draw.textbbox((text_x, 68), tag_str, font=font_title)
    disp_name = clean_name if len(clean_name) <= 15 else (clean_name[:13] + "..")
    draw.text((bbox[2], 68), disp_name, font=font_title, fill=(255, 255, 255))

    lvl, cur_xp, req_xp, ratio, drop_bonus = calculate_clan_level_info(clan_xp)
    draw.text((text_x, 122), f"CLAN LEVEL {lvl}  •  {cur_xp:,} / {req_xp:,} XP", font=font_sub, fill=(226, 232, 240))

    bar_x, bar_y, bar_w, bar_h = text_x, 158, 410, 11
    draw_rounded_rect(draw, [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=5, fill=(255, 255, 255, 42))
    fill_w = max(12, int(bar_w * ratio))
    draw_rounded_rect(draw, [bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=5, fill=(250, 204, 21, 240))

    draw.text((936, 74), f"CLAN ID #{clan_sys_id}", font=font_small, fill=(203, 213, 225), anchor="ra")

    stats_y = 198
    draw.rounded_rectangle([text_x, stats_y + 2, text_x + 4, stats_y + 48], radius=2, fill=(250, 204, 21, 235))
    draw.text((text_x + 15, stats_y), "TOTAL TREASURY", font=font_stat_lbl, fill=(203, 213, 225))
    draw.text((text_x + 15, stats_y + 18), f"{fmt_stars_compact(treasury_stars)} STARS", font=font_stat_val, fill=(255, 255, 255))

    col2_x = text_x + 260
    draw.rounded_rectangle([col2_x, stats_y + 2, col2_x + 4, stats_y + 48], radius=2, fill=(96, 165, 250, 235))
    draw.text((col2_x + 15, stats_y), "MEMBERS", font=font_stat_lbl, fill=(203, 213, 225))
    draw.text((col2_x + 15, stats_y + 18), f"{members_count}/{max_members}", font=font_stat_val, fill=(255, 255, 255))

    col3_x = col2_x + 185
    draw.rounded_rectangle([col3_x, stats_y + 2, col3_x + 4, stats_y + 48], radius=2, fill=(52, 211, 153, 235))
    draw.text((col3_x + 15, stats_y), "WIN BONUS", font=font_stat_lbl, fill=(203, 213, 225))
    draw.text((col3_x + 15, stats_y + 18), f"+{drop_bonus}%", font=font_stat_val, fill=(52, 211, 153))

    draw.text((62, 318), "CLAN FAVORITES", font=font_stat_lbl, fill=(203, 213, 225))

    slot_y = 352
    slot_w, slot_h = 113, 113
    spacing = 15
    start_x = 62

    for i in range(7):
        cur_x = start_x + i * (slot_w + spacing)
        base_bg = apply_liquid_glass_panel(
            base_bg,
            box=(cur_x, slot_y, cur_x + slot_w, slot_y + slot_h),
            radius=18,
            blur_radius=12,
            dark_tint=42,
            top_light=32,
            bottom_light=10,
        )
        draw = ImageDraw.Draw(base_bg)

        if i < len(favorite_gifts):
            g = favorite_gifts[i]
            img_p = gift_image_path(g.key)
            if img_p and img_p.exists():
                try:
                    g_img = Image.open(img_p).convert("RGBA")
                    g_img.thumbnail((78, 78), Image.Resampling.LANCZOS)
                    gx = cur_x + (slot_w - g_img.width) // 2
                    gy = slot_y + (slot_h - g_img.height) // 2
                    base_bg.paste(g_img, (gx, gy), g_img)
                except Exception:
                    pass
            else:
                clean_g_name = g.name.split('(')[0].strip()[:9]
                draw.text((cur_x + slot_w // 2, slot_y + slot_h // 2 - 8), clean_g_name, font=load_font(13, bold=True), fill=(255, 255, 255), anchor="mm")
                draw.text((cur_x + slot_w // 2, slot_y + slot_h - 22), f"{fmt_stars_compact(g.stars)}", font=load_font(11, bold=True), fill=(250, 204, 21), anchor="mm")
        else:
            cx, cy = cur_x + slot_w // 2, slot_y + slot_h // 2
            arm = 11
            thick = 2
            draw.line([(cx - arm, cy - arm), (cx + arm, cy + arm)], fill=(255, 255, 255, 65), width=thick)
            draw.line([(cx + arm, cy - arm), (cx - arm, cy + arm)], fill=(255, 255, 255, 65), width=thick)

    bio = io.BytesIO()
    base_bg.save(bio, "PNG")
    bio.name = "clan.png"
    bio.seek(0)
    return bio

async def generate_scared_cat_promo_card_image(sold: int, remaining: int) -> io.BytesIO:
    """Генерирует акционную красную карточку Red / Scared Cat в стиле iOS Liquid Glass (без обводок)."""
    WIDTH, HEIGHT = 1000, 560
    base = Image.new("RGBA", (WIDTH, HEIGHT), (24, 6, 10, 255))

    # Красное / алое объёмное студийное освещение
    base = _apply_volumetric_lighting(
        base,
        [
            ((-110, -100, int(WIDTH * 0.54), int(HEIGHT * 0.96)), (239, 68, 68, 175)),
            ((int(WIDTH * 0.42), -90, WIDTH + 120, int(HEIGHT * 0.85)), (220, 38, 38, 155)),
            ((int(WIDTH * 0.16), int(HEIGHT * 0.35), int(WIDTH * 0.86), HEIGHT + 140), (251, 146, 60, 115)),
        ],
        blur_radius=74,
        screen_strength=0.68,
    )

    cat_path = gift_image_path("scared_cat")
    # Полупрозрачные акценты красного кота на фоне, чтобы их искажало и размывало жидкое стекло
    if cat_path and cat_path.exists():
        try:
            bg_cat = Image.open(cat_path).convert("RGBA")
            bg_cat.thumbnail((290, 290), Image.Resampling.LANCZOS)
            c1 = bg_cat.rotate(-14, resample=Image.Resampling.BICUBIC, expand=True)
            r1, g1, b1, a1 = c1.split()
            c1 = Image.merge("RGBA", (r1, g1, b1, a1.point(lambda v: int(v * 0.55))))
            base.alpha_composite(c1, (WIDTH - c1.width + 20, -25))

            c2 = bg_cat.rotate(12, resample=Image.Resampling.BICUBIC, expand=True)
            r2, g2, b2, a2 = c2.split()
            c2 = Image.merge("RGBA", (r2, g2, b2, a2.point(lambda v: int(v * 0.48))))
            base.alpha_composite(c2, (-30, HEIGHT - c2.height + 25))
        except Exception:
            pass

    # Светящиеся красные/янтарные частицы позади стекла
    orb = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(orb)
    for ox, oy, orad, ocol in [
        (180, 110, 42, (254, 202, 202, 110)),
        (760, 150, 58, (248, 113, 113, 120)),
        (510, 420, 64, (251, 146, 60, 100)),
        (340, 290, 32, (239, 68, 68, 130)),
    ]:
        odraw.ellipse([ox - orad, oy - orad, ox + orad, oy + orad], fill=ocol)
    orb = orb.filter(ImageFilter.GaussianBlur(14))
    base = Image.alpha_composite(base, orb)

    # Левая и правая панели жидкого стекла (строго без обводки)
    img = apply_liquid_glass_panel(
        base,
        box=(38, 42, 418, HEIGHT - 42),
        radius=30,
        blur_radius=16,
        dark_tint=48,
        top_light=44,
        bottom_light=12,
    )
    img = apply_liquid_glass_panel(
        img,
        box=(444, 42, WIDTH - 38, HEIGHT - 42),
        radius=30,
        blur_radius=18,
        dark_tint=54,
        top_light=42,
        bottom_light=10,
    )

    if cat_path and cat_path.exists():
        try:
            hero_cat = Image.open(cat_path).convert("RGBA")
            hero_cat.thumbnail((315, 315), Image.Resampling.LANCZOS)
            hx = 38 + (380 - hero_cat.width) // 2
            hy = 42 + ((HEIGHT - 84) - hero_cat.height) // 2
            img.paste(hero_cat, (hx, hy), hero_cat)
        except Exception:
            pass

    draw = ImageDraw.Draw(img)
    f_tag = load_font(16, bold=True)
    f_title = load_font(48, bold=True)
    f_sub = load_font(21, bold=True)
    f_stat_lbl = load_font(14, bold=True)
    f_stat_val = load_font(31, bold=True)

    draw.text((482, 82), "LIMITED PROMO  •  RED EDITION", font=f_tag, fill=(254, 154, 154))
    draw.text((482, 114), "SCARED CAT", font=f_title, fill=(255, 255, 255))
    draw.text((482, 174), "Уникальный NFT с ограниченным тиражом", font=f_sub, fill=(254, 215, 215))

    # Блок остатка тиража
    rem_val = max(0, int(remaining))
    sold_val = max(0, int(sold))
    ratio = rem_val / float(max(1, SCARED_CAT_MAX_SUPPLY))

    draw.rounded_rectangle([482, 232, 486, 286], radius=2, fill=(248, 113, 113, 240))
    draw.text((498, 232), "ОСТАЛОСЬ В АКЦИИ", font=f_stat_lbl, fill=(254, 202, 202))
    draw.text((498, 250), f"{rem_val:,} / {SCARED_CAT_MAX_SUPPLY:,} ШТ.", font=f_stat_val, fill=(255, 255, 255))

    # Прогресс-бар остатка
    bar_x, bar_y, bar_w, bar_h = 482, 310, 442, 13
    draw_rounded_rect(draw, [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=6, fill=(255, 255, 255, 42))
    fill_w = max(14, int(bar_w * ratio)) if rem_val > 0 else 0
    if fill_w > 0:
        draw_rounded_rect(draw, [bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=6, fill=(248, 113, 113, 245))
    draw.text((482, 336), f"Уже выкуплено: {sold_val:,} шт.", font=load_font(16, bold=True), fill=(254, 202, 202))

    # Блок цены
    draw.rounded_rectangle([482, 392, 486, 446], radius=2, fill=(250, 204, 21, 240))
    draw.text((498, 392), "ЦЕНА В АКЦИЯХ", font=f_stat_lbl, fill=(254, 240, 138))
    draw.text((498, 410), f"{SCARED_CAT_PROMO_PRICE:,} STARS", font=f_stat_val, fill=(250, 204, 21))
    draw.text((482, 472), "Успей забрать в разделе «Акции»", font=load_font(17, bold=True), fill=(255, 255, 255))

    bio = io.BytesIO()
    img.save(bio, "PNG")
    bio.name = "promo_scared_cat.png"
    bio.seek(0)
    return bio

# ---------------------------------------------------------------------------
# КЛАВИАТУРЫ И КЕЙСЫ
# ---------------------------------------------------------------------------

def main_menu_keyboard(user_id: int = 0) -> InlineKeyboardMarkup:
    buttons = [
        [
            make_btn("Профиль", emoji_key="smile", callback_data="nav_profile"),
            make_btn("NFT Маркет", emoji_key="exchange", callback_data="nav_market"),
        ],
        [
            make_btn("Mystery Cases", emoji_key="game", callback_data="nav_cases_hub"),
            make_btn("Режимы", emoji_key="bolt", callback_data="nav_modes"),
        ],
        [
            make_btn("Акции", emoji_key="fire", callback_data="nav_promos"),
            make_btn("Магазин", emoji_key="star", callback_data="nav_donate_shop"),
        ],
        [
            make_btn("Кланы", emoji_key="shield", callback_data="nav_clans_hub"),
            make_btn("ТОП 100", emoji_key="top", callback_data="nav_top_page:1"),
        ],
        [
            make_btn("Улучшения", emoji_key="bag", callback_data="nav_shop"),
            make_btn("Чеки", emoji_key="dollar", callback_data="nav_checks"),
        ],
        [
            make_btn("Бонусы", emoji_key="calendar", callback_data="nav_bonus"),
            make_btn("Реферальная система", emoji_key="megaphone", callback_data="nav_referral"),
        ],
        [
            make_btn("Аукцион", emoji_key="soon", callback_data="nav_auction"),
            *(
                [make_btn("Mini App", style="primary", emoji_key="globe", web_app=WebAppInfo(url=MINI_APP_URL))]
                if MINI_APP_URL.startswith("https://")
                else []
            ),
        ],
    ]
    if user_id in ADMIN_IDS:
        buttons.append([make_btn("Админ-Панель", style="primary", emoji_key="crown", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)

def quick_nav_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            make_btn("Профиль", emoji_key="smile", callback_data="nav_profile"),
            make_btn("Коллекция", emoji_key="bookmark", callback_data="nav_collection_page:1"),
        ],
        [
            make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")
        ]
    ])

def back_to_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")]
    ])

_CHEAP_BEAR_KEYS = (
    "teddy_patrick",
    "teddy_heart_white",
    "teddy_santa",
    "teddy_football",
    "bunny_teddy",
    "teddy_soldier",
    "teddy_builder",
    "clown_teddy",
)

def _build_case_weights(
    fixed_pcts: Dict[str, float],
    filler_gifts: List[GiftDef],
    uniform_filler: bool = False,
) -> Tuple[List[GiftDef], List[float]]:
    pool: List[GiftDef] = []
    weights: List[float] = []
    used_keys = set()
    fixed_sum = 0.0
    for k, pct in fixed_pcts.items():
        g = GIFTS_BY_KEY.get(k)
        if g and pct > 0:
            pool.append(g)
            weights.append(float(pct))
            used_keys.add(k)
            fixed_sum += float(pct)

    rem_pool = [g for g in filler_gifts if g.key not in used_keys]
    rem_pct = max(0.0, 100.0 - fixed_sum)
    if rem_pool and rem_pct > 0:
        if uniform_filler:
            each = rem_pct / float(len(rem_pool))
            for g in rem_pool:
                pool.append(g)
                weights.append(each)
        else:
            raw_sum = sum(max(0.001, g.chance) for g in rem_pool)
            for g in rem_pool:
                pool.append(g)
                weights.append(rem_pct * (max(0.001, g.chance) / raw_sum))
    return pool, weights

def roll_case_gift(tier: dict, clan_bonus_pct: float = 0.0) -> GiftDef:
    custom_weights = tier.get("weights")
    pool: List[GiftDef] = tier["pool"]
    if not custom_weights:
        return roll_gift_from_pool(pool, bonus_pct=clan_bonus_pct)

    bonus_mult = 1.0 + max(0.0, clan_bonus_pct) / 100.0
    adj_weights = []
    for g, w in zip(pool, custom_weights):
        if g.key in UPGRADABLE_GIFT_KEYS or g.stars >= 10_000:
            adj_weights.append(w * bonus_mult)
        else:
            adj_weights.append(w)
    return random.choices(pool, weights=adj_weights, k=1)[0]

_FARM_50_POOL, _FARM_50_WEIGHTS = _build_case_weights(
    {"pepe_heart": 0.001},
    [GIFTS_BY_KEY[k] for k in _CHEAP_BEAR_KEYS if k in GIFTS_BY_KEY],
    uniform_filler=True,
)
_ALL_OR_NOTHING_POOL, _ALL_OR_NOTHING_WEIGHTS = _build_case_weights(
    {"pepe_heart": 0.1},
    [g for g in GIFTS if g.key != "pepe_heart"],
)
_FARM_CAP_POOL, _FARM_CAP_WEIGHTS = _build_case_weights(
    {"cap_tg": 6.5, "heart_lock_key": 1.0, "pepe_heart": 0.8},
    [g for g in GIFTS if g.key not in ("cap_tg", "heart_lock_key", "pepe_heart")],
)
_FARM_LOCKET_POOL, _FARM_LOCKET_WEIGHTS = _build_case_weights(
    {"heart_lock_key": 6.5, "cap_tg": 12.0, "pepe_heart": 2.0},
    [g for g in GIFTS if g.key not in ("cap_tg", "heart_lock_key", "pepe_heart")],
)
_FARM_50K_POOL, _FARM_50K_WEIGHTS = _build_case_weights(
    {"cap_tg": 20.0, "heart_lock_key": 10.0, "pepe_heart": 3.0},
    [g for g in GIFTS if g.stars <= 3_500],
)
_FARM_PLUS_POOL, _FARM_PLUS_WEIGHTS = _build_case_weights(
    {"pepe_heart": 25.0, "cap_tg": 25.0, "heart_lock_key": 15.0},
    [g for g in GIFTS if g.stars <= 450],
    uniform_filler=True,
)
_ELITE_1M_EXPENSIVE_WEIGHTS: Dict[str, float] = {
    "pepe_heart": 20.0,
    "heart_lock_key": 13.0,
    "cap_tg": 12.0,
    "trophy_cup": 12.0,
    "hero_figure": 10.0,
    "bonded_ring": 9.0,
    "hockey_mask": 8.0,
    "gem_crystal": 6.0,
    "sunglasses": 5.0,
    "briefcase": 5.0,
}
_ELITE_1M_POOL = [GIFTS_BY_KEY[k] for k in _ELITE_1M_EXPENSIVE_WEIGHTS if k in GIFTS_BY_KEY]
_ELITE_1M_WEIGHTS = [_ELITE_1M_EXPENSIVE_WEIGHTS[g.key] for g in _ELITE_1M_POOL]

CASE_TIERS = {
    "farm_50": {
        "name": "🧸 Farm Мишки",
        "price": 50,
        "desc": "Мишки 65⭐ + 0.001% Plush Pepe",
        "pool": _FARM_50_POOL,
        "weights": _FARM_50_WEIGHTS,
        "rolls_buffs": False,
    },
    "tier1": {
        "name": "📦 Farm",
        "price": 100,
        "desc": "Базовый кейс (до 8,000 ⭐)",
        "pool": [g for g in GIFTS if g.stars <= 8000],
        "weights": None,
        "rolls_buffs": False,
    },
    "all_or_nothing": {
        "name": "🎲 Всё или ничего",
        "price": 1_000,
        "desc": "0.1% Plush Pepe + все подарки",
        "pool": _ALL_OR_NOTHING_POOL,
        "weights": _ALL_OR_NOTHING_WEIGHTS,
        "rolls_buffs": False,
    },
    "tier3": {
        "name": "🟣 Кейс 2,500",
        "price": 2_500,
        "desc": "Подарки от 500 ⭐",
        "pool": [g for g in GIFTS if g.stars >= 500],
        "weights": None,
        "rolls_buffs": False,
    },
    "farm_cap": {
        "name": "🧢 Farm Кепки Дурова",
        "price": 10_000,
        "desc": "6.5% Кепка • 1% Сердце • 0.8% Пепе",
        "pool": _FARM_CAP_POOL,
        "weights": _FARM_CAP_WEIGHTS,
        "rolls_buffs": False,
    },
    "farm_locket": {
        "name": "💝 Farm Heart Locket",
        "price": 25_000,
        "desc": "6.5% Сердце • 12% Кепка • 2% Пепе",
        "pool": _FARM_LOCKET_POOL,
        "weights": _FARM_LOCKET_WEIGHTS,
        "rolls_buffs": False,
    },
    "farm_50k": {
        "name": "🔥 Farm Кейс",
        "price": 50_000,
        "desc": "20% Кепка • 10% Сердце • 3% Пепе",
        "pool": _FARM_50K_POOL,
        "weights": _FARM_50K_WEIGHTS,
        "rolls_buffs": False,
    },
    "farm_plus": {
        "name": "🐸 Farm +",
        "price": 250_000,
        "desc": "25% Пепе • 25% Кепка • 15% Сердце",
        "pool": _FARM_PLUS_POOL,
        "weights": _FARM_PLUS_WEIGHTS,
        "rolls_buffs": False,
    },
    "elite_1m": {
        "name": "💎 Elite Buff Case",
        "price": 1_000_000,
        "desc": "45% Топ NFT с БАФФАМИ + дорогие",
        "pool": _ELITE_1M_POOL,
        "weights": _ELITE_1M_WEIGHTS,
        "rolls_buffs": True,
    },
}

# ---------------------------------------------------------------------------
# ПРОВЕРКА ДОСТУПА (ТЕХРАБОТЫ И БАН)
# ---------------------------------------------------------------------------

async def check_access_allowed(update: Update) -> bool:
    """
    Проверяет:
    1. Включён ли режим техработ (админы обходят блокировку).
    2. Забанен ли пользователь.
    Возвращает True, если доступ разрешён.
    """
    user = update.effective_user
    if not user:
        return True

    if is_maintenance_mode() and user.id not in ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer(
                "🛠 Бот сейчас на техработах, подождите немного и попробуйте позже.",
                show_alert=True,
            )
        elif update.effective_message:
            await update.effective_message.reply_text(MAINTENANCE_MESSAGE, parse_mode=ParseMode.HTML)
        return False

    is_banned, until_ts, reason, hours = is_user_banned(user.id)
    if is_banned and user.id not in ADMIN_IDS:
        ban_text, ban_kb = format_ban_message(until_ts, reason, hours)
        if update.callback_query:
            await update.callback_query.answer("⛔️ Ваш аккаунт заблокирован!", show_alert=True)
            if update.callback_query.message and update.callback_query.message.chat.type == "private":
                await update.callback_query.message.reply_text(ban_text, parse_mode=ParseMode.HTML, reply_markup=ban_kb)
        elif update.effective_message:
            await update.effective_message.reply_text(ban_text, parse_mode=ParseMode.HTML, reply_markup=ban_kb)
        return False

    touch_user_activity(user.id)
    return True

def build_privacy_terms_text() -> str:
    return (
        f"{ce('clip')} <b>ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ И УСЛОВИЯ ПОЛЬЗОВАНИЯ</b>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('siren')} <b>ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ (ПРОЧТИТЕ ОБЯЗАТЕЛЬНО):</b>\n"
        f"{ce('dbl_excl')} <b>ВСЕ ЗВЁЗДЫ ({ce('star')}) И NFT-ПОДАРКИ В ЭТОМ БОТЕ — ВИРТУАЛЬНЫЕ ИГРОВЫЕ ПРЕДМЕТЫ!</b>\n"
        f"{ce('free')} <b>ОСНОВНАЯ ИГРА ПОЛНОСТЬЮ БЕСПЛАТНА И НЕ ТРЕБУЕТ ВЛОЖЕНИЙ. ВИРТУАЛЬНЫЕ НАГРАДЫ НЕ ПОДЛЕЖАТ ВЫВОДУ В РЕАЛЬНЫЕ ДЕНЬГИ ИЛИ TELEGRAM STARS!</b>\n"
        f"{ce('lock')} <b>В РАЗДЕЛЕ «МАГАЗИН» ДОСТУПНЫ ТОЛЬКО ОПЦИОНАЛЬНЫЕ ИГРОВЫЕ НАБОРЫ ЧЕРЕЗ ОФИЦИАЛЬНЫЕ TELEGRAM STARS (XTR). БОТ НИКОГДА НЕ ПРОСИТ ПАРОЛИ ИЛИ ПЕРЕВОДЫ ВНЕ TELEGRAM.</b>\n"
        "━━━━━━━━━━━━\n\n"
        "<blockquote expandable>"
        f"{ce('gem')} <b>1. Игровой статус валюты и подарков</b>\n"
        "• Внутриигровые звёзды, рубли/TON на карточках, кейсы и NFT-подарки являются исключительно виртуальной игровой статистикой для развлечения.\n"
        "• Указанная ценность в ₽ и TON носит справочно-игровой характер и не подлежит обмену или выводу в реальные активы.\n\n"
        f"{ce('game')} <b>2. Правила игры и честная игра</b>\n"
        "• Выбивайте подарки в группах по слову <code>NFT</code> (раз в час), открывайте <b>Mystery Cases</b>, соревнуйтесь в <b>Баттлах</b>, улучшайте <b>Plush Pepe</b>, <b>Heart Locket</b>, <b>Durov's Cap</b>, <b>Algorithm Cup</b> и <b>Bonded Ring</b> (с баффами из элитного кейса), участвуйте в лимитированных <b>Акциях</b> (например, <b>Scared Cat</b>), объединяйтесь в кланы и торгуйте на P2P Маркете (комиссия площадки 15%).\n"
        "• Переводы звёзд (<code>Передать 1000</code>, <code>/pay</code>), чеки в разделе <b>«Чеки»</b> (на 1 или несколько игроков, с паролем и без) и передача обычных подарков доступны с <b>5-го уровня</b>.\n"
        "• Запрещены мультиаккаунты, накрутка, использование скриптов/ботов, эксплуатация багов и обман других игроков. Нарушение ведёт к блокировке аккаунта.\n\n"
        f"{ce('lock')} <b>3. Политика конфиденциальности (обработка данных)</b>\n"
        "• Бот сохраняет только публичные данные Telegram (ваш <b>User ID</b>, <code>@username</code>, отображаемое имя) и внутриигровой прогресс (баланс, XP, коллекция, клан, лоты маркета).\n"
        "• Бот не запрашивает и не хранит номера телефонов, личные переписки или пароли 2FA.\n"
        "• В разделе <b>«Настройки»</b> (через Профиль) вы можете в любой момент скрыть свой профиль из ТОП-100 и закрыть просмотр коллекции.\n\n"
        f"{ce('crown')} <b>4. Авторство и проведение розыгрышей</b>\n"
        f"• Статус <b>Автора</b> доступен по заявке из профиля для игроков от <b>{AUTHOR_MIN_LEVEL}-го уровня</b> с балансом от <b>{AUTHOR_MIN_BALANCE:,} ⭐</b> после проверки администрацией.\n"
        "• Авторы получают отдельный <b>Авторский баланс</b> (используется исключительно для розыгрышей и призов), привязывают свои каналы/чаты и публикуют конкурсы с автоматической проверкой подписки, регистрации в боте и автовыплатой звёзд/чеков победителям.\n"
        "• Запрещены фейковые конкурсы, накрутка и вводящие в заблуждение условия — за нарушения статус автора аннулируется.\n\n"
        f"{ce('chat')} <b>5. Поддержка</b>\n"
        f"• По всем вопросам, багам и апелляциям обращайтесь в поддержку: {SUPPORT_HANDLE}"
        "</blockquote>\n\n"
        f"{ce('check')} Нажимая кнопку ниже, вы подтверждаете, что ознакомились с правилами, понимаете, что <b>звёзды и подарки ненастоящие (игра без донатов)</b>, и принимаете Политику конфиденциальности и Условия пользования."
    )

async def send_privacy_consent_prompt(update_or_query, user_id: int, pending_arg: str = "") -> None:
    cb_data = "accept_privacy"
    if pending_arg and len(pending_arg) <= 44 and re.fullmatch(r"[A-Za-z0-9_]+", pending_arg):
        cb_data = f"accept_privacy:{pending_arg}"

    kb = InlineKeyboardMarkup([
        [make_btn("Принять политику и условия пользования", style="success", emoji_key="check", callback_data=cb_data)],
    ])
    text = build_privacy_terms_text()

    if isinstance(update_or_query, CallbackQuery):
        if update_or_query.message and update_or_query.message.photo:
            try:
                await update_or_query.message.delete()
            except Exception:
                pass
            await update_or_query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        elif update_or_query.message:
            await update_or_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        target_msg = update_or_query.effective_message if hasattr(update_or_query, "effective_message") else update_or_query
        if target_msg:
            await target_msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def ensure_privacy_accepted_private(update: Update, context: ContextTypes.DEFAULT_TYPE, pending_arg: str = "") -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or chat.type != "private":
        return True
    get_or_create_user(user.id, user.username or "", user.first_name or "")
    if has_accepted_privacy(user.id):
        return True
    if pending_arg:
        context.user_data["pending_start_arg"] = pending_arg
    if update.callback_query:
        await update.callback_query.answer("📜 Сначала примите Политику конфиденциальности и Условия пользования!", show_alert=False)
        await send_privacy_consent_prompt(update.callback_query, user.id, pending_arg)
    else:
        await send_privacy_consent_prompt(update, user.id, pending_arg)
    return False

async def maybe_send_channel_subscribe_prompt(
    bot,
    chat_id: int,
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    ref_status_note: str = "",
) -> bool:
    """Один раз предлагает игроку подписаться на официальный канал @NwNFTChannel (с кнопкой 'Я не хочу')."""
    if has_channel_prompt_done(user_id):
        return False

    if ref_status_note:
        context.user_data["ch_prompt_ref_note"] = ref_status_note
    else:
        context.user_data.pop("ch_prompt_ref_note", None)

    text = (
        f"{ce('megaphone')} <b>Официальный канал новостей и раздач — {OFFICIAL_CHANNEL_HANDLE}</b>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('sparkles')} Подпишитесь на наш Telegram-канал, чтобы не пропустить:\n"
        f"• {ce('new')} Крупные обновления бота, новые NFT-модели и кейсы\n"
        f"• {ce('star')} Масштабные розыгрыши звёзд и секретные чеки\n"
        f"• {ce('bolt')} Новости экономики и специальные события\n\n"
        "<i>Это предложение показывается один раз. Вы можете подписаться или отказаться кнопкой ниже:</i>"
    )
    kb = InlineKeyboardMarkup([
        [make_btn(f"Подписаться на {OFFICIAL_CHANNEL_HANDLE}", style="primary", emoji_key="megaphone", url=OFFICIAL_CHANNEL_URL)],
        [make_btn("Я подписался / Продолжить", style="success", emoji_key="check", callback_data="channel_prompt_ack:sub")],
        [make_btn("🙅 Я не хочу", emoji_key="cross", callback_data="channel_prompt_ack:skip")],
    ])
    await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return True

# ---------------------------------------------------------------------------
# ПРОФИЛЬ ИГРОКА И ПЛАТНЫЙ ФОН
# ---------------------------------------------------------------------------

async def fetch_user_avatar_bytes(bot, user_id: int) -> Optional[bytes]:
    """Загружает аватарку игрока из Telegram (profile_photos -> get_chat) с дисковым кэшем."""
    cache_path = AVATARS_CACHE_DIR / f"av_{user_id}.jpg"
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if photos and photos.total_count > 0 and photos.photos:
            file_id = photos.photos[0][-1].file_id
            tg_file = await bot.get_file(file_id)
            bio = io.BytesIO()
            await tg_file.download_to_memory(bio)
            data = bio.getvalue()
            if data:
                try:
                    cache_path.write_bytes(data)
                except Exception:
                    pass
                return data
    except Exception as e:
        log.debug("get_user_profile_photos(%s): %s", user_id, e)

    try:
        chat = await bot.get_chat(user_id)
        if chat and chat.photo:
            fid = chat.photo.big_file_id or chat.photo.small_file_id
            if fid:
                tg_file = await bot.get_file(fid)
                bio = io.BytesIO()
                await tg_file.download_to_memory(bio)
                data = bio.getvalue()
                if data:
                    try:
                        cache_path.write_bytes(data)
                    except Exception:
                        pass
                    return data
    except Exception as e:
        log.debug("get_chat.photo(%s): %s", user_id, e)

    if cache_path.exists():
        try:
            cached = cache_path.read_bytes()
            if cached:
                return cached
        except Exception:
            pass
    return None

async def show_profile_handler(update_or_query, target_user_id: int, context: ContextTypes.DEFAULT_TYPE, back_to_top_page: Optional[int] = None) -> None:
    viewer_user = (
        update_or_query.effective_user
        if hasattr(update_or_query, "effective_user") and update_or_query.effective_user
        else update_or_query.from_user
    )
    current_viewer_id = viewer_user.id

    if current_viewer_id == target_user_id:
        db_user = get_or_create_user(target_user_id, viewer_user.username or "", viewer_user.first_name or "")
    else:
        db_user = get_or_create_user(target_user_id, "", "")
        if not (db_user["first_name"] or "").strip() and not (db_user["username"] or "").strip():
            try:
                chat_info = await context.bot.get_chat(target_user_id)
                if chat_info and (chat_info.first_name or chat_info.username):
                    db_user = get_or_create_user(
                        target_user_id,
                        chat_info.username or "",
                        chat_info.first_name or "",
                    )
            except Exception:
                pass

    clean_name = normalize_telegram_name(db_user["first_name"], db_user["username"], target_user_id)
    avatar_bytes = await fetch_user_avatar_bytes(context.bot, target_user_id)

    fav_rows = get_favorites(target_user_id)
    rank = get_user_rank(target_user_id)
    lvl, cur_xp, req_xp, _ = calculate_xp_level_info(db_user["xp"])

    clan = get_user_clan(target_user_id)
    clan_tag = clan["tag"] if clan else None

    custom_bg_val = db_user["bg_image_path"]
    if custom_bg_val and resolve_user_bg_path(target_user_id, custom_bg_val) is None:
        bg_fid = get_user_bg_file_id(target_user_id)
        if bg_fid:
            try:
                tg_bg = await context.bot.get_file(bg_fid)
                raw_bg = bytes(await tg_bg.download_as_bytearray())
                if raw_bg:
                    custom_bg_val = save_user_background_data(target_user_id, raw_bg, file_id=bg_fid)
            except Exception as e:
                log.debug("Не удалось восстановить фон по file_id (%s): %s", target_user_id, e)

    card_img_io = None
    try:
        card_img_io = await generate_profile_card_image(
            db_user["first_name"] or clean_name,
            db_user["id_num"],
            db_user["balance_stars"],
            db_user["xp"],
            rank,
            fav_rows,
            avatar_bytes=avatar_bytes,
            clan_tag=clan_tag,
            custom_bg_path=custom_bg_val,
            fallback_username=db_user["username"],
            telegram_user_id=target_user_id,
        )
    except Exception as e:
        log.error("Ошибка при генерации карточки профиля: %s", e)

    clan_display = f"[{clean_html(clan_tag)}] {clean_html(clan['name'])}" if clan else "Отсутствует"
    display_title = f"[{clean_html(clan_tag)}] {clean_html(clean_name)}" if clan_tag else clean_html(clean_name)

    is_self = (current_viewer_id == target_user_id)
    bot_username = await get_bot_username(context.bot)
    profile_link = f"https://t.me/{bot_username}?start=profile_{target_user_id}"
    share_profile_url = (
        f"https://t.me/share/url?url={urllib.parse.quote(profile_link)}"
        f"&text={urllib.parse.quote(f'👤 Профиль игрока {clean_name} в New NFT Bot')}"
    )

    author_line = f"{ce('crown')} Статус: <b>Официальный Автор</b>\n" if db_user["is_author"] else ""
    caption = (
        f"{ce('smile')} <b>Профиль игрока:</b> {display_title}\n"
        f"━━━━━━━━━━━━\n"
        f"{author_line}"
        f"{ce('bolt')} Уровень: <b>{lvl} ({cur_xp:,}/{req_xp:,} XP)</b>\n"
        f"{ce('shield')} Клан: <b>{clan_display}</b>\n"
        f"{ce('top')} Место в глобальном ТОПе: <b>#{rank}</b>\n"
        f"{ce('dollar')} Баланс: <b>{fmt_stars_rub(db_user['balance_stars'])}</b>\n"
        f"{ce('bookmark')} Вместимость инвентаря: <b>{db_user['max_inventory']} слотов</b>\n"
        f"{ce_gift(0)} Выбито подарков: <b>{db_user['total_drops']}</b> шт.\n"
        f"{ce('money_wings')} Продано предметов: <b>{db_user['total_sold']}</b> шт.\n"
        f"━━━━━━━━━━━━"
    )

    buttons = []
    if is_self:
        author_btn_label = "Кабинет автора" if db_user["is_author"] else "Авторство"
        author_btn_style = "success" if db_user["is_author"] else "primary"
        buttons.append([
            make_btn("Коллекция", emoji_key="bookmark", callback_data="nav_collection_page:1"),
            make_btn("Настройки", emoji_key="gear", callback_data="nav_settings"),
        ])
        buttons.append([
            make_btn("Улучшение", style="primary", emoji_key="sparkles", callback_data="nav_shop"),
            make_btn(author_btn_label, style=author_btn_style, emoji_key="crown", callback_data="nav_author"),
        ])
        buttons.append([
            make_btn("Промокоды", style="success", emoji_key="fire", callback_data="nav_promocodes"),
            make_btn("Информация", emoji_key="info", callback_data="nav_info"),
        ])
        buttons.append([
            make_btn("Поделиться профилем", style="primary", emoji_key="link", url=share_profile_url),
        ])
        buttons.append([
            make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")
        ])
    else:
        buttons.append([make_btn("Поделиться профилем", style="primary", emoji_key="link", url=share_profile_url)])
        if back_to_top_page:
            buttons.append([InlineKeyboardButton("◀️ Назад в ТОП 100", callback_data=f"nav_top_page:{back_to_top_page}")])
        buttons.append([
            make_btn("Моя коллекция", emoji_key="bookmark", callback_data="nav_collection_page:1"),
            make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")
        ])

    kb = InlineKeyboardMarkup(buttons)

    if hasattr(update_or_query, "message") and update_or_query.message and update_or_query.message.photo:
        try: await update_or_query.message.delete()
        except Exception: pass

    target_chat_id = (
        update_or_query.effective_chat.id
        if hasattr(update_or_query, "effective_chat") and update_or_query.effective_chat
        else (update_or_query.message.chat.id if hasattr(update_or_query, "message") and update_or_query.message else current_viewer_id)
    )

    if card_img_io:
        try:
            await context.bot.send_photo(
                chat_id=target_chat_id,
                photo=InputFile(card_img_io, filename="profile.png"),
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
            return
        except Exception as e:
            log.warning("Не удалось отправить фото профиля: %s", e)

    await context.bot.send_message(
        chat_id=target_chat_id,
        text=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

async def bg_change_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END

    query = update.callback_query
    user = query.from_user
    db_user = get_or_create_user(user.id, user.username or "", user.first_name or "")

    has_bg = has_user_background(db_user)
    cost = BG_CHANGE_COST if has_bg else BG_SET_COST
    action_label = "смены фона" if has_bg else "установки фона"

    if db_user["balance_stars"] < cost:
        await query.answer(
            f"❌ Недостаточно Stars для {action_label}! Требуется {cost:,} ⭐ (у вас {db_user['balance_stars']:,} ⭐).",
            show_alert=True,
        )
        return ConversationHandler.END

    await query.answer()
    context.user_data["bg_pending_cost"] = cost

    text = (
        f"🖼 <b>{'Смена' if has_bg else 'Установка'} кастомного фона профиля</b>\n\n"
        f"• Стоимость: <b>{cost:,} ⭐</b>\n"
        f"• Ваш баланс: <b>{db_user['balance_stars']:,} ⭐</b>\n\n"
        "Отправьте любое изображение в этот чат (как фото или файл-картинку).\n"
        "Оно будет <b>слегка затемнено и размыто</b> на заднем плане вашей карточки, "
        "а звёзды спишутся автоматически после загрузки.\n\n"
        "<i>Для отмены отправьте /cancel или нажмите кнопку ниже.</i>"
    )
    kb = InlineKeyboardMarkup([[make_btn("❌ Отмена", style="danger", callback_data="bg_cancel")]])

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_PROFILE_BG

async def bg_photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END

    user = update.effective_user
    msg = update.message
    bg_file_id = ""
    if msg and msg.photo:
        bg_file_id = msg.photo[-1].file_id
    elif msg and msg.document:
        mime = (msg.document.mime_type or "").lower()
        fname = (msg.document.file_name or "").lower()
        is_img_doc = mime.startswith("image/") or fname.endswith((".jpg", ".jpeg", ".png", ".webp"))
        if is_img_doc:
            bg_file_id = msg.document.file_id

    if not bg_file_id:
        await update.message.reply_text("❌ Пожалуйста, отправьте именно изображение (как фото или файл-картинку), либо напишите /cancel.")
        return WAIT_PROFILE_BG

    db_user = get_or_create_user(user.id, user.username or "", user.first_name or "")
    has_bg = has_user_background(db_user)
    cost = BG_CHANGE_COST if has_bg else BG_SET_COST

    if not deduct_user_stars(user.id, cost):
        await update.message.reply_text(
            f"❌ Недостаточно Stars на балансе! Требуется <b>{cost:,} ⭐</b>.",
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard(),
        )
        return ConversationHandler.END

    try:
        photo_file = await context.bot.get_file(bg_file_id)
        raw_bytes = bytes(await photo_file.download_as_bytearray())
        if not raw_bytes:
            raise ValueError("Пустой файл изображения")
        save_user_background_data(user.id, raw_bytes, file_id=bg_file_id)
        record_star_flow(spent=cost, burned=cost, purchased=cost)

        await update.message.reply_text(
            f"🎉 <b>Фон профиля успешно {'обновлён' if has_bg else 'установлен'}!</b>\n"
            f"С вашего баланса списано <b>{cost:,} ⭐</b>.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👤 Посмотреть профиль", callback_data="nav_profile")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="nav_main")]
            ])
        )
    except Exception as e:
        add_user_stars(user.id, cost, track_issued=False)
        log.error("Ошибка загрузки фона: %s", e)
        await update.message.reply_text("❌ Ошибка при сохранении изображения. Звёзды возвращены на баланс.")

    return ConversationHandler.END

async def bg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer("Отменено.")
        await show_settings_page(query, query.from_user.id)
    else:
        await update.message.reply_text("Отменено.", reply_markup=back_to_main_keyboard())
    return ConversationHandler.END

async def bg_reset_handler(query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    set_user_background(user_id, None)
    bg_file_path = BACKGROUNDS_DIR / f"bg_{user_id}.jpg"
    if bg_file_path.exists():
        try: bg_file_path.unlink()
        except Exception: pass
    await query.answer("🗑 Фон сброшен на стандартный!", show_alert=True)
    await show_settings_page(query, user_id)

# ---------------------------------------------------------------------------
# ПРОФИЛЬ КЛАНА, КАЗНА, ПОДАРКИ КЛАНА
# ---------------------------------------------------------------------------

async def show_clan_profile_handler(update_or_query, clan_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_viewer_id = (
        update_or_query.effective_user.id
        if hasattr(update_or_query, "effective_user") and update_or_query.effective_user
        else update_or_query.from_user.id
    )

    clan = get_clan_by_id(clan_id)
    if not clan:
        if hasattr(update_or_query, "answer"):
            await update_or_query.answer("Клан не найден.", show_alert=True)
        return

    awarded_xp = check_and_award_clan_daily_xp(clan_id)
    if awarded_xp:
        clan = get_clan_by_id(clan_id)

    total_treasury, donated_bank, members = get_clan_treasury_and_members(clan_id)
    fav_gifts = get_clan_favorites(clan)
    clan_gifts = get_clan_gifts(clan_id)

    clan_sys_id = clan["id_num"] if clan["id_num"] else clan["id"]
    lvl, cur_xp, req_xp, ratio, drop_bonus = calculate_clan_level_info(clan["xp"])

    is_owner = (clan["owner_id"] == current_viewer_id)
    user_clan = get_user_clan(current_viewer_id)
    is_member = (user_clan and user_clan["id"] == clan["id"])

    owner_user = get_or_create_user(clan["owner_id"], "", "")
    owner_name = normalize_telegram_name(owner_user["first_name"], owner_user["username"], clan["owner_id"])

    clan_card_io = None
    try:
        clan_card_io = await generate_clan_card_image(
            clan["name"],
            clan["tag"],
            clan_sys_id,
            clan["xp"],
            total_treasury,
            len(members),
            clan["max_members"],
            fav_gifts,
            avatar_path=clan["avatar_path"]
        )
    except Exception as e:
        log.error("Ошибка при генерации карточки клана: %s", e)

    ctype_str = "Открытый (свободный вход)" if clan["type"] == "public" else ("Вход за звёзды" if clan["type"] == "stars" else "Закрытый (по заявкам)")
    fee_str = f"\n💰 Стоимость входа: <b>{clan['entry_fee']} ⭐</b>" if clan["type"] == "stars" else ""

    caption = (
        f"{ce('shield')} <b>Клан [{clan['tag']}] {clean_html(clan['name'])}</b>\n"
        f"━━━━━━━━━━━━\n"
        f"{ce('bolt')} Уровень клана: <b>{lvl} ({cur_xp:,}/{req_xp:,} XP)</b>\n"
        f"{ce('comet')} Клановый бонус к выигрышу: <b>+{drop_bonus}%</b>\n"
        f"{ce('crown')} Создатель / Владелец: <b>{clean_html(owner_name)}</b>\n"
        f"{ce('smile')} Состав: <b>{len(members)}/{clan['max_members']}</b> чел.\n"
        f"{ce('dollar')} <b>Общая казна клана:</b> <b>{fmt_stars_rub(total_treasury)}</b>\n"
        f"{ce('candle')} <b>Баланс казны (для покупок):</b> <b>{fmt_stars_compact(donated_bank)} ⭐</b>\n"
        f"{ce_gift(1)} Подарено подарков клану: <b>{len(clan_gifts)}</b> шт.\n"
        f"{ce('lock')} Тип входа: <b>{ctype_str}</b>{fee_str}\n"
        f"{ce('pencil')} Описание: <i>{clean_html(clan['description']) or 'Отсутствует'}</i>\n"
        f"━━━━━━━━━━━━"
    )

    buttons = [
        [
            make_btn("Участники и казна", emoji_key="chart_bar", callback_data=f"clan_members_detail:{clan_id}"),
            make_btn(f"Подарки ({len(clan_gifts)})", emoji_id=CUSTOM_GIFT_EMOJI_IDS[0], callback_data=f"clan_gifts_menu:{clan_id}:1"),
        ],
    ]

    if is_member:
        buttons.append([
            make_btn("Депозит в казну", emoji_key="money_wings", callback_data=f"clan_donate_stars_start:{clan_id}"),
            make_btn("Подарить подарок", emoji_id=CUSTOM_GIFT_EMOJI_IDS[1], callback_data=f"clan_donate_gift_menu:{clan_id}:1")
        ])

    if is_owner:
        upgrade_cost = get_clan_upgrade_cost(clan["max_members"])
        buttons.append([
            make_btn("Сменить герб клана", emoji_key="pencil", callback_data=f"clan_avatar_start:{clan_id}"),
            make_btn("Избранное клана", emoji_key="star", callback_data=f"clan_gifts_menu:{clan_id}:1")
        ])
        buttons.append([
            make_btn(f"+15 мест ({upgrade_cost:,}⭐)", emoji_key="up_tri", callback_data=f"clan_upgrade:{clan_id}"),
            make_btn("Заявки в клан", emoji_key="mail", callback_data=f"clan_requests:{clan_id}")
        ])
        buttons.append([make_btn("Расформировать клан", style="danger", emoji_key="fire", callback_data=f"clan_delete_confirm:{clan_id}")])
    elif is_member:
        buttons.append([InlineKeyboardButton("🚪 Покинуть клан", callback_data="clan_leave:1")])
    elif not user_clan and len(members) < clan["max_members"]:
        if clan["type"] == "public":
            buttons.append([InlineKeyboardButton("🚪 Вступить в клан", callback_data=f"clan_join:{clan_id}")])
        elif clan["type"] == "stars":
            buttons.append([InlineKeyboardButton(f"⭐ Войти за {clan['entry_fee']} Stars", callback_data=f"clan_join_stars:{clan_id}")])
        elif clan["type"] == "private":
            buttons.append([InlineKeyboardButton("📩 Подать заявку в клан", callback_data=f"clan_apply:{clan_id}")])

    buttons.append([
        InlineKeyboardButton("📋 Список кланов", callback_data="clan_list:1"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="nav_main")
    ])

    kb = InlineKeyboardMarkup(buttons)

    if hasattr(update_or_query, "message") and update_or_query.message and update_or_query.message.photo:
        try: await update_or_query.message.delete()
        except Exception: pass

    if clan_card_io:
        try:
            await context.bot.send_photo(
                chat_id=current_viewer_id,
                photo=InputFile(clan_card_io, filename="clan.png"),
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
            return
        except Exception as e:
            log.warning("Не удалось отправить фото карточки клана: %s", e)

    await context.bot.send_message(
        chat_id=current_viewer_id,
        text=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

async def show_clan_members_detail(query, clan_id: int):
    clan = get_clan_by_id(clan_id)
    if not clan:
        await query.answer("Клан не найден.")
        return

    total_treasury, donated_bank, members = get_clan_treasury_and_members(clan_id)

    lines = [
        f"👥 <b>Участники и казна клана [{clan['tag']}] {clean_html(clan['name'])}</b>",
        "━━━━━━━━━━━━",
        f"💰 <b>Общая казна клана:</b> <b>{fmt_stars_compact(total_treasury)} ⭐</b>",
        f"🏦 <b>Баланс казны (доступно для покупок):</b> <b>{fmt_stars_compact(donated_bank)} ⭐</b>",
        f"👥 <b>Всего участников:</b> <b>{len(members)}/{clan['max_members']}</b>",
        "━━━━━━━━━━━━",
        "<b>Баланс каждого участника:</b>\n"
    ]

    for idx, m in enumerate(members, start=1):
        is_owner = (m["user_id"] == clan["owner_id"])
        role_badge = "👑 Создатель" if is_owner else "Участник"
        mname = normalize_telegram_name(m["first_name"], m["username"], m["user_id"])
        lines.append(f"{idx}. <b>{clean_html(mname)}</b> ({role_badge}) — <b>{fmt_stars_compact(m['balance_stars'])} ⭐</b>")

    lines.append("\n━━━━━━━━━━━━")
    text = "\n".join(lines)

    buttons = []
    if clan["owner_id"] == query.from_user.id:
        for m in members:
            if m["user_id"] != clan["owner_id"]:
                mname = normalize_telegram_name(m["first_name"], m["username"], m["user_id"])
                buttons.append([make_btn(f"❌ Исключить {mname[:10]}", style="danger", callback_data=f"clan_kick:{m['user_id']}")])

    buttons.append([InlineKeyboardButton("⬅️ Назад в профиль клана", callback_data=f"clan_info:{clan_id}")])
    buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="nav_main")])

    kb = InlineKeyboardMarkup(buttons)
    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

# --- ПОДАРКИ КЛАНА И ИЗБРАННОЕ ---

async def show_clan_gifts_menu(query, clan_id: int, page: int = 1):
    clan = get_clan_by_id(clan_id)
    if not clan:
        await query.answer("Клан не найден.", show_alert=True)
        return

    gifts = get_clan_gifts(clan_id)
    is_owner = (clan["owner_id"] == query.from_user.id)
    user_clan = get_user_clan(query.from_user.id)
    is_member = bool(user_clan and user_clan["id"] == clan_id)

    fav_count = sum(1 for row in gifts if row["is_favorite"])

    if not gifts:
        text = (
            f"🎁 <b>Подарки клана [{clan['tag']}] {clean_html(clan['name'])}</b>\n"
            f"━━━━━━━━━━━━\n"
            f"В клане пока нет подаренных подарков.\n\n"
            f"<i>Участники клана могут нажать «🎁 Подарить подарок», выбрать предмет из своей коллекции и передать его клану! Покупать подарки здесь нельзя.</i>"
        )
        buttons = []
        if is_member:
            buttons.append([InlineKeyboardButton("🎁 Подарить подарок из коллекции", callback_data=f"clan_donate_gift_menu:{clan_id}:1")])
        buttons.append([InlineKeyboardButton("⬅️ В профиль клана", callback_data=f"clan_info:{clan_id}")])
        kb = InlineKeyboardMarkup(buttons)

        if query.message.photo:
            await query.message.delete()
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    page_size = 8
    total_pages = max(1, math.ceil(len(gifts) / page_size))
    page = max(1, min(page, total_pages))
    page_items = gifts[(page - 1) * page_size : page * page_size]

    lines = [
        f"🎁 <b>Подарки клана [{clan['tag']}] {clean_html(clan['name'])}</b>",
        f"━━━━━━━━━━━━",
        f"Всего подарков: <b>{len(gifts)}</b> | В избранном: <b>{fav_count}/7</b>\n",
    ]
    if is_owner:
        lines.append("<i>Нажмите на подарок ниже, чтобы закрепить его в Избранное клана (до 7 слотов) или убрать оттуда:</i>\n")
    else:
        lines.append("<i>Список подарков, подаренных участниками клана:</i>\n")

    buttons = []
    for cg in page_items:
        g = GIFTS_BY_KEY.get(cg["gift_key"])
        if not g:
            continue
        donor_name = normalize_telegram_name(cg["first_name"], cg["username"], cg["donor_user_id"])
        fav_icon = "⭐ " if cg["is_favorite"] else "🎁 "
        lines.append(f"{fav_icon}<b>{g.name}</b> — от <b>{clean_html(donor_name)}</b>")
        if is_owner:
            action_lbl = "Убрать из ⭐" if cg["is_favorite"] else "В избранное ⭐"
            buttons.append([
                InlineKeyboardButton(f"{fav_icon}{g.name[:22]} • {action_lbl}", callback_data=f"clan_toggle_gift_fav:{clan_id}:{cg['id']}:{page}")
            ])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"clan_gifts_menu:{clan_id}:{page-1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"clan_gifts_menu:{clan_id}:{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    if is_member:
        buttons.append([InlineKeyboardButton("🎁 Подарить подарок клану", callback_data=f"clan_donate_gift_menu:{clan_id}:1")])
    buttons.append([InlineKeyboardButton("⬅️ В профиль клана", callback_data=f"clan_info:{clan_id}")])
    buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="nav_main")])

    text = "\n".join(lines)
    kb = InlineKeyboardMarkup(buttons)

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_clan_donate_gift_menu(query, clan_id: int, user_id: int, page: int = 1):
    user_clan = get_user_clan(user_id)
    if not user_clan or user_clan["id"] != clan_id:
        await query.answer("❌ Вы не состоите в этом клане!", show_alert=True)
        return

    items = [it for it in get_user_collection(user_id) if not it["is_listed"]]
    if not items:
        await query.answer("У вас нет доступных предметов в коллекции для подарка клану!", show_alert=True)
        return

    page_size = 8
    total_pages = max(1, math.ceil(len(items) / page_size))
    page = max(1, min(page, total_pages))
    page_items = items[(page - 1) * page_size : page * page_size]

    text = (
        f"🎁 <b>Подарить подарок клану (Стр. {page}/{total_pages})</b>\n\n"
        "Выберите подарок из вашей коллекции.\n"
        "После подтверждения он перейдёт в собственность клана и принесёт клану XP:"
    )

    buttons = []
    for item in page_items:
        g = GIFTS_BY_KEY.get(item["gift_key"])
        if not g:
            continue
        val_stars = get_item_display_value(item)
        g_emoji = get_upgraded_gift_emoji(item["gift_key"])
        lbl = f"{g_emoji} #{item['upgrade_num']} {item['model_name']}" if item["is_upgraded"] and item["model_name"] else g.name[:24]
        buttons.append([
            InlineKeyboardButton(
                f"🎁 {lbl} ({fmt_stars_compact(val_stars)}⭐)",
                callback_data=f"clan_donate_gift_confirm:{clan_id}:{item['id']}"
            )
        ])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"clan_donate_gift_menu:{clan_id}:{page-1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"clan_donate_gift_menu:{clan_id}:{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton("⬅️ В профиль клана", callback_data=f"clan_info:{clan_id}")])
    kb = InlineKeyboardMarkup(buttons)

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_clan_donate_gift_confirm(query, clan_id: int, item_id: int, user_id: int):
    clan = get_clan_by_id(clan_id)
    user_clan = get_user_clan(user_id)
    if not clan or not user_clan or user_clan["id"] != clan_id:
        await query.answer("❌ Вы не состоите в этом клане!", show_alert=True)
        return

    item = get_collection_item(item_id)
    if not item or item["user_id"] != user_id:
        await query.answer("❌ Предмет не найден в вашей коллекции!", show_alert=True)
        return
    if item["is_listed"]:
        await query.answer("❌ Сначала снимите подарок с маркета!", show_alert=True)
        return

    g = GIFTS_BY_KEY.get(item["gift_key"])
    if not g:
        await query.answer("❌ Ошибка предмета.", show_alert=True)
        return

    val_stars = get_item_display_value(item)
    xp_earned = max(1, int(val_stars * 0.0008))
    g_title = get_upgraded_gift_title(item["gift_key"])
    disp_name = f"{g_title} #{item['upgrade_num']} ({item['model_name']})" if item["is_upgraded"] else g.name
    text = (
        "🎁 <b>Подтверждение подарка клану</b>\n"
        "━━━━━━━━━━━━\n"
        f"Клан: <b>[{clan['tag']}] {clean_html(clan['name'])}</b>\n"
        f"Подарок: <b>{clean_html(disp_name)}</b>\n"
        f"Ценность: <b>{fmt_stars_rub(val_stars)}</b>\n"
        f"Бонус опыта клану: <b>+{xp_earned:,} XP</b>\n"
        "━━━━━━━━━━━━\n"
        "⚠️ Предмет будет удалён из вашей коллекции и появится в разделе подарков клана.\n"
        "Подтвердить передачу?"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("✅ Подтвердить подарок", style="success", callback_data=f"clan_donate_gift_do:{clan_id}:{item_id}")],
        [make_btn("❌ Отмена", style="danger", callback_data=f"clan_donate_gift_menu:{clan_id}:1")],
    ])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def execute_clan_donate_gift(query, clan_id: int, item_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    user_clan = get_user_clan(user_id)
    if not user_clan or user_clan["id"] != clan_id:
        await query.answer("❌ Вы не состоите в этом клане!", show_alert=True)
        return

    ok, gift_name, xp_earned = donate_gift_to_clan_db(user_id, clan_id, item_id)
    if not ok:
        await query.answer(f"❌ {gift_name}", show_alert=True)
        return

    await query.answer(f"🎉 Подарок {gift_name} подарен клану! (+{xp_earned} XP)", show_alert=True)
    await show_clan_gifts_menu(query, clan_id, 1)

# ---------------------------------------------------------------------------
# АВАТАРКА КЛАНА (FSM)
# ---------------------------------------------------------------------------

async def clan_avatar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END

    query = update.callback_query
    clan_id = int(query.data.split(":")[1])
    clan = get_clan_by_id(clan_id)

    if not clan or clan["owner_id"] != query.from_user.id:
        await query.answer("❌ Только создатель клана может менять герб!", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    context.user_data["clan_avatar_clan_id"] = clan_id

    text = (
        "🖼 <b>Установка герба (аватарки) клана</b>\n\n"
        "Отправьте свою фотографию прямо в этот чат (как фото).\n\n"
        "<i>Отправьте /cancel или нажмите кнопку ниже для отмены.</i>"
    )
    kb = InlineKeyboardMarkup([[make_btn("❌ Отмена", style="danger", callback_data="clan_avatar_cancel")]])

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_CLAN_AVATAR

async def clan_avatar_photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END

    if not update.message.photo:
        await update.message.reply_text("❌ Пожалуйста, отправьте именно фото или /cancel.")
        return WAIT_CLAN_AVATAR

    clan_id = context.user_data.get("clan_avatar_clan_id")
    if not clan_id:
        await update.message.reply_text("Ошибка сессии.")
        return ConversationHandler.END

    photo_file = await update.message.photo[-1].get_file()
    av_path = CLAN_AVATARS_DIR / f"clan_{clan_id}.jpg"

    try:
        await photo_file.download_to_drive(custom_path=av_path)
        set_clan_avatar(clan_id, str(av_path))

        await update.message.reply_text(
            "🎉 <b>Герб клана успешно установлен!</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛡 В профиль клана", callback_data=f"clan_info:{clan_id}")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="nav_main")]
            ])
        )
    except Exception as e:
        log.error("Ошибка сохранения герба клана: %s", e)
        await update.message.reply_text("❌ Ошибка при сохранении герба. Попробуйте еще раз.")

    return ConversationHandler.END

async def clan_avatar_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer("Отменено.")
        clan_id = context.user_data.get("clan_avatar_clan_id")
        if clan_id:
            await show_clan_profile_handler(query, clan_id, context)
    else:
        await update.message.reply_text("Отменено.")
    return ConversationHandler.END

# ---------------------------------------------------------------------------
# ПОПОЛНЕНИЕ БАЛАНСА КАЗНЫ КЛАНА ЗВЁЗДАМИ (FSM)
# ---------------------------------------------------------------------------

async def clan_donate_stars_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END

    query = update.callback_query
    clan_id = int(query.data.split(":")[1])
    await query.answer()

    context.user_data["donate_clan_id"] = clan_id
    text = (
        "💰 <b>Депозит в баланс казны клана</b>\n\n"
        "Внесённые Stars попадают в <b>Баланс казны</b> (на них клан может покупать улучшения) "
        "и приносят клану опыт (~800 XP за 1,000,000 ⭐).\n"
        "<i>Общая казна клана при этом не уменьшается!</i>\n\n"
        "Введите количество Stars (⭐) для внесения в баланс казны:"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="clan_donate_cancel")]])

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_CLAN_DONATE_STARS

async def clan_donate_stars_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END

    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("❌ Введите положительное число звёзд:")
        return WAIT_CLAN_DONATE_STARS

    amount = int(text)
    clan_id = context.user_data.get("donate_clan_id")
    user = update.effective_user

    success, xp_awarded = donate_stars_to_clan(user.id, clan_id, amount)
    if not success:
        await update.message.reply_text("❌ У вас недостаточно Stars на балансе!")
        return ConversationHandler.END

    clan = get_clan_by_id(clan_id)
    total_treasury, donated_bank, _ = get_clan_treasury_and_members(clan_id)
    lvl, cur_xp, req_xp, _, bonus = calculate_clan_level_info(clan["xp"])

    await update.message.reply_text(
        f"🎉 <b>Вы внесли {amount:,} ⭐ в баланс казны клана!</b>\n\n"
        f"• Общая казна клана: <b>{total_treasury:,} ⭐</b>\n"
        f"• Баланс казны (для покупок): <b>{donated_bank:,} ⭐</b>\n"
        f"• Клан получил: <b>+{xp_awarded:,} XP</b>\n"
        f"• Уровень клана: <b>{lvl}</b> ({cur_xp:,}/{req_xp:,} XP, +{bonus}% к победе)",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛡 В профиль клана", callback_data=f"clan_info:{clan_id}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="nav_main")]
        ])
    )
    return ConversationHandler.END

async def clan_donate_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer("Отменено.")
        clan_id = context.user_data.get("donate_clan_id")
        if clan_id:
            await show_clan_profile_handler(query, clan_id, context)
    else:
        await update.message.reply_text("Отменено.")
    return ConversationHandler.END

# ---------------------------------------------------------------------------
# РАЗДЕЛ "ИНФО"
# ---------------------------------------------------------------------------

async def show_info_page(query_or_update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_info = await context.bot.get_me()
    bot_user = bot_info.username or "Bot"
    add_group_url = f"https://t.me/{bot_user}?startgroup=true"

    text = (
        f"{ce('info')} <b>Справочный центр New NFT Bot</b>\n"
        "━━━━━━━━━━━━\n"
        "Добро пожаловать в официальную информационную панель бота!\n\n"
        "<blockquote expandable>"
        f"{ce('pin')} <b>Основные возможности бота:</b>\n"
        f"• {ce('comet')} Выбивание редких Telegram Gifts в любых чатах словом <code>NFT</code>\n"
        f"• {ce_gift(2)} Передача звёзд и подарков прямо в чате командой <code>Передать</code>\n"
        f"• {ce('dollar')} Многопользовательские и запароленные чеки в разделе <b>«Чеки»</b>\n"
        f"• {ce('exchange')} Торговый <b>NFT Marketplace</b> и <b>Mystery Cases</b>\n"
        f"• {ce('shield')} Кланы с гербами, уровнями, казной и бонусами к дропу\n"
        f"• {ce('crown')} <b>Авторство и конкурсы</b> — запуск розыгрышей в своих каналах с авто-чеками победителям\n"
        f"• {ce('sparkles')} Улучшения <b>Plush Pepe</b> {ce_pepe(0)}, <b>Heart Locket</b>, <b>Algorithm Cup</b>, <b>Durov's Cap</b> и <b>Bonded Ring</b> с редкими моделями и фонами\n"
        f"• {ce('fire')} Раздел <b>«Акции»</b> — лимитированный <b>Scared Cat</b> (1,000 шт.) и <b>«Магазин»</b> наборов за XTR\n"
        f"• {ce('chat')} Служба поддержки: {SUPPORT_HANDLE}"
        "</blockquote>\n"
        "━━━━━━━━━━━━\n"
        "Выберите интересующий подраздел:"
    )

    kb = InlineKeyboardMarkup([
        [make_btn("Подключение бота к группе и права", emoji_key="globe", callback_data="info_group_guide")],
        [make_btn("Политика конфиденциальности", emoji_key="clip", callback_data="info_privacy")],
        [make_btn("Правила игры и команды", emoji_key="thought", callback_data="info_rules")],
        [make_btn("Написать в поддержку", emoji_key="chat", url=SUPPORT_URL)],
        [make_btn("Добавить бота в группу", style="primary", emoji_key="plus", url=add_group_url)],
        [
            make_btn("Назад в профиль", emoji_key="smile", callback_data="nav_profile"),
            make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main"),
        ],
    ])

    if isinstance(query_or_update, CallbackQuery):
        await safe_edit_or_reply(query_or_update, text, reply_markup=kb)
    else:
        target_msg = query_or_update.effective_message if hasattr(query_or_update, "effective_message") else query_or_update
        if target_msg:
            await target_msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_group_guide(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_info = await context.bot.get_me()
    bot_user = bot_info.username or "Bot"
    add_group_url = f"https://t.me/{bot_user}?startgroup=true"

    text = (
        f"{ce('globe')} <b>Подключение бота к вашей группе</b>\n"
        "━━━━━━━━━━━━\n"
        "1️⃣ Нажмите кнопку <b>«Добавить бота в группу»</b> ниже.\n"
        "2️⃣ Выберите нужный чат и выдайте права на чтение и отправку сообщений/фото.\n"
        "3️⃣ В чате доступны команды: <code>NFT</code>, <code>Профиль</code>, <code>Передать</code>!"
    )

    kb = InlineKeyboardMarkup([
        [make_btn("Добавить бота в группу", style="primary", emoji_key="plus", url=add_group_url)],
        [InlineKeyboardButton("◀️ Назад в Инфо", callback_data="nav_info")],
        [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")]
    ])
    await safe_edit_or_reply(query, text, reply_markup=kb)

async def show_privacy_policy(query) -> None:
    text = build_privacy_terms_text()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад в Инфо", callback_data="nav_info")],
        [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")]
    ])
    await safe_edit_or_reply(query, text, reply_markup=kb)

async def show_rules_page(query) -> None:
    text = (
        f"{ce('thought')} <b>Правила игры и команды</b>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('comet')} <b>Дроп в чатах:</b> Напишите <code>NFT</code> (раз в 1 час). Шанс дропа — <b>90%</b>.\n\n"
        "<blockquote expandable>"
        f"{ce('sparkles')} <b>Улучшения, Баффы и NFT Маркет:</b>\n"
        f"• Улучшайте <b>Plush Pepe</b> {ce_pepe(1)} ({UPGRADE_COST_STARS:,} ⭐ • 50 моделей), <b>Heart Locket</b> ({HEART_LOCKET_UPGRADE_COST_STARS:,} ⭐ • 61 модель), <b>Algorithm Cup</b> ({ALGORITHM_CUP_UPGRADE_COST_STARS:,} ⭐ • 4 модели), <b>Durov's Cap</b> ({DUROV_CAP_UPGRADE_COST_STARS:,} ⭐ • 55 моделей) и <b>Bonded Ring</b> ({BONDED_RING_UPGRADE_COST_STARS:,} ⭐ • 50 моделей) в разделе <b>«Улучшения»</b>.\n"
        "• Из кейса <b>💎 Elite Buff Case (1,000,000 ⭐)</b> улучшаемые подарки выпадают с <b>1–2 Баффами</b> (усиление шанса редкого фона, редкой модели или оценочной цены!).\n"
        "• Улучшенные NFT и лимитированный <b>Scared Cat</b> (из раздела <b>«Акции»</b>, всего 1,000 шт.) нельзя продать боту — они торгуются только между игроками на P2P Маркете (комиссия 15%) или передаются бесплатно.\n"
        "• Если цвет модели совпадает с цветом фона, срабатывает множитель <b>MONOCHROME x6</b>!\n\n"
        f"{ce('dollar')} <b>Чеки и переводы (с 5-го уровня):</b>\n"
        "• Создавайте чеки на 1 или нескольких игроков (с паролем или без) внутри бота в разделе <b>«Чеки»</b> (от <b>1,000 ⭐</b>) и делитесь ими в любом чате.\n"
        "• <b>Передача звёзд:</b> <code>Передать 1000</code> (ответом на сообщение) или <code>Передать 1000 @user</code> (от <b>1,000 ⭐</b>).\n"
        "• <b>Передача подарков:</b> Напишите просто <code>Передать</code> в чате, чтобы сразу открыть окно выбора подарка!\n\n"
        f"{ce('shield')} <b>Кланы (с 10-го уровня):</b>\n"
        "• Кланы дают общий уровень, герб и бонус до <b>+45%</b> к шансу выпадения редких подарков.\n\n"
        f"{ce('crown')} <b>Авторство и розыгрыши (с {AUTHOR_MIN_LEVEL}-го уровня и {AUTHOR_MIN_BALANCE:,} ⭐):</b>\n"
        "• Подайте заявку через <b>Профиль → Авторство</b>, указав свои каналы/чаты и возраст.\n"
        "• После одобрения вы получаете <b>Авторский баланс</b> (пополнение/вывод с основного баланса, только для конкурсов), привязываете каналы и запускаете конкурсы.\n"
        "• Для участия игрок должен запустить бота и подписаться на все каналы конкурса. По завершении бот сам выплачивает звёзды и отправляет чеки победителям!"
        "</blockquote>\n\n"
        f"{ce('chat')} <b>Поддержка:</b> {SUPPORT_HANDLE}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад в Инфо", callback_data="nav_info")],
        [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")]
    ])
    await safe_edit_or_reply(query, text, reply_markup=kb)

# ---------------------------------------------------------------------------
# РАЗДЕЛ "NFT МАРКЕТ" (P2P ТОРГОВЛЯ УЛУЧШЕННЫМИ NFT, КОМИССИЯ 15%)
# ---------------------------------------------------------------------------

async def show_market_hub(update_or_query) -> None:
    banner_io = await generate_market_banner()
    _, _, active_total = get_market_listings("all", "all", page=1, page_size=1)

    caption = (
        f"{ce('exchange')} <b>NFT Marketplace (P2P Биржа)</b>\n"
        "━━━━━━━━━━━━\n"
        f"Официальная торговая площадка улучшенных NFT {ce_pepe(2)} <b>Plush Pepe</b>, <b>Heart Locket</b>, <b>Durov's Cap</b>, <b>Algorithm Cup</b>, <b>Bonded Ring</b> и уникального <b>Scared Cat</b> между игроками.\n\n"
        f"• {ce('chart_bar')} Активных лотов сейчас: <b>{active_total}</b>\n"
        f"• {ce('money_wings')} Комиссия маркета при продаже: <b>{int(MARKET_FEE_RATE * 100)}%</b>\n"
        f"• {ce('dollar')} Диапазон цен: <b>{MARKET_MIN_PRICE:,} — {MARKET_MAX_PRICE:,} ⭐</b>\n"
        "━━━━━━━━━━━━\n"
        "Выставляйте свои улучшенные подарки и уникальных Scared Cat или ищите редкие модели:"
    )

    kb = InlineKeyboardMarkup([
        [make_btn("Продать NFT на маркете", style="success", emoji_key="plus", callback_data="market_create_offer")],
        [make_btn(f"Все лоты ({active_total})", style="primary", emoji_key="bookmark", callback_data="market_view:all:all:1")],
        [
            make_btn("По стоимости", emoji_key="dollar", callback_data="market_filter_price_menu"),
            make_btn("По редкости фона", emoji_key="sparkles", callback_data="market_filter_rarity_menu"),
        ],
        [
            make_btn("Plush Pepe (50)", emoji_id=CUSTOM_PEPE_EMOJI_IDS[0], callback_data="market_filter_model_menu:pepe_heart:1"),
            make_btn("Heart Locket (61)", emoji_key="gem", callback_data="market_filter_model_menu:heart_lock_key:1"),
        ],
        [
            make_btn("Durov's Cap (55)", emoji_key="crown", callback_data="market_filter_model_menu:cap_tg:1"),
            make_btn("Algorithm Cup (4)", emoji_key="gold", callback_data="market_filter_model_menu:trophy_cup:1"),
        ],
        [
            make_btn("Bonded Ring (50)", emoji_key="gem", callback_data="market_filter_model_menu:bonded_ring:1"),
            make_btn("Scared Cat (Уник.)", emoji_key="fire", callback_data="market_view:gift:scared_cat:1"),
        ],
        [
            make_btn("Мои лоты", emoji_key="eyes", callback_data="market_my_offers"),
            make_btn("История сделок", emoji_key="chart_bar", callback_data="market_history"),
        ],
        [
            make_btn("Моя коллекция", emoji_key="bookmark", callback_data="nav_collection_page:1"),
            make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main"),
        ]
    ])

    if isinstance(update_or_query, CallbackQuery):
        if update_or_query.message and update_or_query.message.photo:
            try: await update_or_query.message.delete()
            except Exception: pass
        if update_or_query.message:
            await update_or_query.message.reply_photo(
                photo=InputFile(banner_io, filename="market.png"),
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
    else:
        target_msg = update_or_query.effective_message if hasattr(update_or_query, "effective_message") else update_or_query
        if target_msg:
            if getattr(target_msg, "photo", None):
                try: await target_msg.delete()
                except Exception: pass
            await target_msg.reply_photo(
                photo=InputFile(banner_io, filename="market.png"),
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )

async def show_market_filter_price_menu(query):
    text = (
        "💰 <b>Фильтр маркета по стоимости:</b>\n"
        "Выберите интересующий ценовой диапазон:"
    )
    buttons = []
    for pkey, (ptitle, _, _) in MARKET_PRICE_TIERS.items():
        buttons.append([InlineKeyboardButton(ptitle, callback_data=f"market_view:price:{pkey}:1")])
    buttons.append([InlineKeyboardButton("⬅️ Назад в маркет", callback_data="nav_market")])
    kb = InlineKeyboardMarkup(buttons)

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_market_filter_rarity_menu(query):
    text = (
        "🎨 <b>Фильтр по редкости фона:</b>\n"
        "Самые редкие и дорогие — <b>Мифический Rainbow (0.05%, x100)</b> и <b>Ультра-редкие</b> (чёрные, серые, золото)."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌈 Мифический (Rainbow 0.05% • x100)", callback_data="market_view:rarity:Мифический:1")],
        [InlineKeyboardButton("👑 Ультра-редкий (0.15%–0.50%)", callback_data="market_view:rarity:Ультра-редкий:1")],
        [InlineKeyboardButton("💎 Редкий (0.60%–1.15%)", callback_data="market_view:rarity:Редкий:1")],
        [InlineKeyboardButton("🟣 Необычный (1.25%–1.85%)", callback_data="market_view:rarity:Необычный:1")],
        [InlineKeyboardButton("🟢 Обычный яркий (2.15%–2.80%)", callback_data="market_view:rarity:Обычный:1")],
        [InlineKeyboardButton("⬅️ Назад в маркет", callback_data="nav_market")],
    ])
    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_market_filter_model_menu(query, gift_key: str = "pepe_heart", page: int = 1):
    """Список моделей Plush Pepe (50) или Heart Locket (61) для фильтрации лотов на маркете."""
    if gift_key not in UPGRADABLE_GIFT_KEYS:
        gift_key = "pepe_heart"
    models_pool = get_models_for_gift(gift_key)
    g_title = get_upgraded_gift_title(gift_key)
    g_emoji = get_upgraded_gift_emoji(gift_key)

    page_size = 10
    total_pages = max(1, math.ceil(len(models_pool) / page_size))
    page = max(1, min(page, total_pages))
    page_models = models_pool[(page - 1) * page_size : page * page_size]

    text = (
        f"{g_emoji} <b>Модели {g_title} на маркете (Стр. {page}/{total_pages})</b>\n"
        "Выберите модель для поиска активных лотов:"
    )
    buttons = []
    for m in page_models:
        buttons.append([
            InlineKeyboardButton(f"{g_emoji} {m.name} (шанс {m.chance_pct}%)", callback_data=f"market_view:model:{m.name}:1")
        ])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"market_filter_model_menu:{gift_key}:{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"market_filter_model_menu:{gift_key}:{page+1}"))
    buttons.append(nav_row)

    buttons.append([InlineKeyboardButton("⬅️ Назад в маркет", callback_data="nav_market")])
    kb = InlineKeyboardMarkup(buttons)

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_market_view_page(query, ftype: str, fkey: str, page: int = 1):
    lots, total_pages, total_count = get_market_listings(ftype, fkey, page=page, page_size=8)
    if ftype == "price":
        filter_name = MARKET_PRICE_TIERS.get(fkey, ("По цене", 0, 0))[0]
    elif ftype == "gift":
        filter_name = f"Коллекция: {get_upgraded_gift_title(fkey)}"
    elif ftype == "model":
        filter_name = f"Модель: {fkey}"
    elif ftype == "rarity":
        filter_name = f"Редкость фона: {fkey}"
    else:
        filter_name = "Все активные лоты"

    buttons = []
    lines = [
        f"📋 <b>Маркет: {clean_html(filter_name)}</b> (Стр. {page}/{total_pages})",
        "━━━━━━━━━━━━",
        f"Найдено лотов: <b>{total_count}</b>\n",
    ]

    if not lots:
        lines.append("<i>Активных лотов по выбранному фильтру пока нет.</i>")
    else:
        lines.append("<i>Нажмите на лот ниже, чтобы посмотреть карточку NFT и купить:</i>")
        for lot in lots:
            g_emoji = get_upgraded_gift_emoji(lot["gift_key"])
            if lot["gift_key"] == "scared_cat" and lot["backdrop_key"] == "limited":
                btn_lbl = f"{g_emoji} #{lot['upgrade_num']} Scared Cat (Уник.) — {fmt_stars_compact(lot['price_stars'])}⭐"
            else:
                bg_def = BACKDROPS_BY_KEY.get(lot["backdrop_key"])
                bg_name = bg_def.name if bg_def else lot["backdrop_key"]
                btn_lbl = f"{g_emoji} #{lot['upgrade_num']} {lot['model_name']} • {bg_name} — {fmt_stars_compact(lot['price_stars'])}⭐"
            buttons.append([InlineKeyboardButton(btn_lbl[:60], callback_data=f"market_lot:{lot['id']}")])

    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("◀️", callback_data=f"market_view:{ftype}:{fkey}:{page-1}"))
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("▶️", callback_data=f"market_view:{ftype}:{fkey}:{page+1}"))
        buttons.append(nav_row)

    buttons.append([make_btn("Продать NFT на маркете", style="primary", emoji_key="plus", callback_data="market_create_offer")])
    buttons.append([
        InlineKeyboardButton("💰 По цене", callback_data="market_filter_price_menu"),
        InlineKeyboardButton("🎨 По фону", callback_data="market_filter_rarity_menu"),
    ])
    buttons.append([InlineKeyboardButton("⬅️ В витрину маркета", callback_data="nav_market")])
    buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="nav_main")])

    text = "\n".join(lines)
    kb = InlineKeyboardMarkup(buttons)
    await safe_edit_or_reply(query, text, reply_markup=kb)

async def show_market_lot_detail(update_or_query, listing_id: int, viewer_id: int, context: Optional[ContextTypes.DEFAULT_TYPE] = None):
    lot = get_market_listing_by_id(listing_id)
    is_callback = hasattr(update_or_query, "answer") and hasattr(update_or_query, "from_user")
    msg_obj = update_or_query.message if is_callback else update_or_query.effective_message

    if not lot or lot["status"] != "active":
        if is_callback:
            await update_or_query.answer("❌ Этот лот уже продан или снят с продажи.", show_alert=True)
            await show_market_view_page(update_or_query, "all", "all", 1)
        elif msg_obj:
            await msg_obj.reply_text(
                "❌ Этот лот уже продан или снят с продажи.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 В маркет", callback_data="nav_market")]]),
            )
        return

    gift_key = lot["gift_key"] or "pepe_heart"
    g_title = get_upgraded_gift_title(gift_key)
    g_emoji = get_upgraded_gift_emoji(gift_key)
    seller_name = normalize_telegram_name(lot["seller_name"], lot["seller_username"], lot["seller_id"])
    lot_item = get_collection_item(lot["collection_id"]) if lot["collection_id"] else None
    is_unique_scared = (
        gift_key == "scared_cat"
        and (lot["backdrop_key"] == "limited" or (lot_item and not lot_item["is_upgraded"]))
    )

    bot_obj = context.bot if context else (update_or_query.get_bot() if hasattr(update_or_query, "get_bot") else None)
    bot_username = await get_bot_username(bot_obj) if bot_obj else (_BOT_USERNAME_CACHE or "bot")
    lot_link = f"https://t.me/{bot_username}?start=lot_{lot['id']}"
    lot_num_val = lot["upgrade_num"]
    lot_price_txt = fmt_stars_compact(lot["price_stars"])
    fee_pct = int(MARKET_FEE_RATE * 100)
    seller_gets = lot["price_stars"] - int(lot["price_stars"] * MARKET_FEE_RATE)
    g_ce = upgraded_gift_tg_emoji(gift_key)
    is_owner = (lot["seller_id"] == viewer_id)

    if is_unique_scared:
        card_io = await generate_gift_card_image(SCARED_CAT_DEF)
        if not card_io:
            img_p = gift_image_path("scared_cat")
            if img_p and img_p.exists():
                card_io = io.BytesIO(img_p.read_bytes())
                card_io.name = "scared_cat.webp"
                card_io.seek(0)
        share_text = f"{g_emoji} Scared Cat #{lot_num_val}/{SCARED_CAT_MAX_SUPPLY} за {lot_price_txt} ⭐ на маркете!"
        cap = (
            f"{ce('exchange')} <b>Лот #{lot['id']} • Scared Cat #{lot_num_val}/{SCARED_CAT_MAX_SUPPLY}</b>\n"
            f"━━━━━━━━━━━━\n"
            f"{g_ce} Тип: <b>Уникальный коллекционный NFT</b> (тир. {SCARED_CAT_MAX_SUPPLY:,} шт.)\n"
            f"{ce('gem')} Базовая ценность: <b>{fmt_stars_rub(SCARED_CAT_DEF.stars)}</b>\n"
            f"{ce('smile')} Продавец: <b>{clean_html(seller_name)}</b>\n"
            f"━━━━━━━━━━━━\n"
            f"{ce('dollar')} Цена покупки: <b>{fmt_stars_rub(lot['price_stars'])}</b>\n\n"
            f"<blockquote expandable>"
            f"{ce('thought')} <b>Аннотация сделки:</b>\n"
            f"• Мгновенная передача уникального <b>Scared Cat #{lot_num_val}</b> в вашу коллекцию сразу после оплаты.\n"
            f"• Комиссия P2P-маркета: <b>{fee_pct}%</b> (продавец получит <b>{fmt_stars_compact(seller_gets)} ⭐</b>).\n"
            f"• Лимитированный <b>Scared Cat</b> не выпадает в кейсах и не продаётся боту — только торговля на маркете или передача игрокам."
            f"</blockquote>"
        )
    else:
        model = get_model_def(gift_key, lot["model_name"])
        backdrop = BACKDROPS_BY_KEY.get(lot["backdrop_key"]) or PLUSHPEPE_BACKDROPS[0]
        is_mono, mono_fam = get_monochrome_combo_info(model.name, backdrop.key)
        lot_buff_badge = format_buffs_compact(lot_item) if lot_item else ""
        lot_buff_lines = format_buffs_lines(lot_item) if lot_item else []

        card_io = await generate_upgraded_gift_image(
            model,
            backdrop,
            lot["upgrade_num"],
            lot["upgraded_stars"],
            list_price=lot["price_stars"],
            gift_key=gift_key,
            buff_badge=lot_buff_badge,
        )
        share_text = f"{g_emoji} {g_title} #{lot_num_val} ({model.name} • {backdrop.name}) за {lot_price_txt} ⭐ на маркете!"
        mono_line = f"\n{ce('rainbow')} Комбо: <b>MONOCHROME x6</b> ({COLOR_FAMILY_RU.get(mono_fam, mono_fam)})" if is_mono else ""
        buffs_block = (
            "\n⚡ <b>Баффы NFT:</b>\n" + "\n".join(f"• {ln}" for ln in lot_buff_lines)
            if lot_buff_lines else ""
        )
        cap = (
            f"{ce('exchange')} <b>Лот #{lot['id']} • {g_title} #{lot['upgrade_num']}</b>\n"
            f"━━━━━━━━━━━━\n"
            f"{g_ce} Модель: <b>{clean_html(model.name)}</b> (шанс {model.chance_pct}%)\n"
            f"{ce('sparkles')} Фон: <b>{clean_html(backdrop.name)}</b> • <i>{backdrop.rarity_label}</i> ({backdrop.chance_pct}%){mono_line}{buffs_block}\n"
            f"{ce('gem')} Оценочная стоимость: <b>{fmt_stars_rub(lot['upgraded_stars'])}</b>\n"
            f"{ce('smile')} Продавец: <b>{clean_html(seller_name)}</b>\n"
            f"━━━━━━━━━━━━\n"
            f"{ce('dollar')} Цена покупки: <b>{fmt_stars_rub(lot['price_stars'])}</b>\n\n"
            f"<blockquote expandable>"
            f"{ce('thought')} <b>Аннотация сделки:</b>\n"
            f"• Мгновенная передача NFT в вашу коллекцию сразу после оплаты.\n"
            f"• Комиссия P2P-маркета: <b>{fee_pct}%</b> (продавец получит <b>{fmt_stars_compact(seller_gets)} ⭐</b>).\n"
            f"• Улучшенные NFT нельзя продать боту — только торговать на маркете или передавать игрокам."
            f"</blockquote>"
        )

    share_url = (
        f"https://t.me/share/url?url={urllib.parse.quote(lot_link)}"
        f"&text={urllib.parse.quote(share_text)}"
    )

    buttons = []
    if is_owner:
        buttons.append([make_btn("Снять лот с продажи", style="danger", emoji_key="cross", callback_data=f"market_cancel_lot:{lot['id']}")])
    else:
        buttons.append([make_btn(f"Купить за {fmt_stars_compact(lot['price_stars'])} ⭐", style="success", emoji_key="check", callback_data=f"market_buy:{lot['id']}")])
    buttons.append([make_btn("Поделиться подарком", style="primary", emoji_key="link", url=share_url)])
    buttons.append([
        make_btn("Все лоты", emoji_key="bookmark", callback_data="market_view:all:all:1"),
        make_btn("В маркет", emoji_key="exchange", callback_data="nav_market"),
    ])
    kb = InlineKeyboardMarkup(buttons)

    if is_callback and msg_obj:
        try: await msg_obj.delete()
        except Exception: pass

    if card_io:
        await msg_obj.reply_photo(
            photo=InputFile(card_io, filename=f"lot_{lot['id']}.png"),
            caption=cap,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    else:
        await msg_obj.reply_text(cap, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_market_create_offer_list(query, user_id: int, page: int = 1):
    items = [
        it for it in get_user_collection(user_id)
        if (it["is_upgraded"] or it["gift_key"] == "scared_cat") and not it["is_listed"]
    ]
    if not items:
        text = (
            f"{ce('plus')} <b>Выставить NFT на маркет</b>\n"
            "━━━━━━━━━━━━\n"
            "У вас пока нет доступных <b>улучшенных NFT</b> или уникального <b>Scared Cat</b> для продажи.\n\n"
            f"Улучшите <b>Plush Pepe</b> {ce_pepe(3)} ({UPGRADE_COST_STARS:,} ⭐), <b>Heart Locket</b> ({HEART_LOCKET_UPGRADE_COST_STARS:,} ⭐), <b>Algorithm Cup</b> ({ALGORITHM_CUP_UPGRADE_COST_STARS:,} ⭐), <b>Durov's Cap</b> ({DUROV_CAP_UPGRADE_COST_STARS:,} ⭐) или <b>Bonded Ring</b> ({BONDED_RING_UPGRADE_COST_STARS:,} ⭐) в разделе «Улучшения», либо приобретите <b>Scared Cat</b> в разделе «Акции»!"
        )
        kb = InlineKeyboardMarkup([
            [make_btn("Перейти к улучшениям", style="primary", emoji_key="sparkles", callback_data="nav_shop")],
            [make_btn("Акции (Scared Cat)", emoji_key="fire", callback_data="nav_promos")],
            [InlineKeyboardButton("◀️ Назад в маркет", callback_data="nav_market")],
        ])
        await safe_edit_or_reply(query, text, reply_markup=kb)
        return

    page_size = 8
    total_pages = max(1, math.ceil(len(items) / page_size))
    page = max(1, min(page, total_pages))
    page_items = items[(page - 1) * page_size : page * page_size]

    buttons = []
    for it in page_items:
        g_emoji = get_upgraded_gift_emoji(it["gift_key"])
        if it["gift_key"] == "scared_cat" and not it["is_upgraded"]:
            ed = int(it["edition_num"] or it["id"])
            lbl = f"{g_emoji} #{ed} Scared Cat (Уник.) • ~{fmt_stars_compact(SCARED_CAT_DEF.stars)}⭐"
        else:
            bg = BACKDROPS_BY_KEY.get(it["backdrop_key"])
            bg_name = bg.name if bg else (it["backdrop_key"] or "")
            lbl = f"{g_emoji} #{it['upgrade_num']} {it['model_name']} ({bg_name}) • ~{fmt_stars_compact(it['upgraded_stars'])}⭐"
        buttons.append([InlineKeyboardButton(lbl[:60], callback_data=f"market_sell_start:{it['id']}")])

    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("◀️", callback_data=f"market_create_offer_pg:{page-1}"))
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("▶️", callback_data=f"market_create_offer_pg:{page+1}"))
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton("⬅️ Назад в маркет", callback_data="nav_market")])
    kb = InlineKeyboardMarkup(buttons)
    text = (
        "➕ <b>Выберите NFT для продажи на маркете:</b>\n"
        f"<i>Комиссия маркета при продаже: {int(MARKET_FEE_RATE * 100)}%.</i>"
    )
    await safe_edit_or_reply(query, text, reply_markup=kb)

async def show_market_my_offers(query, user_id: int):
    lots = get_user_market_listings(user_id)
    buttons = []
    if not lots:
        text = "🔍 <b>Мои активные лоты</b>\n\nУ вас сейчас нет активных лотов на маркете."
    else:
        lines = [f"🔍 <b>Мои активные лоты ({len(lots)}):</b>\n"]
        for lot in lots:
            g_emoji = get_upgraded_gift_emoji(lot["gift_key"])
            if lot["gift_key"] == "scared_cat" and lot["backdrop_key"] == "limited":
                lines.append(f"• Лот #{lot['id']}: {g_emoji} <b>Scared Cat #{lot['upgrade_num']}/{SCARED_CAT_MAX_SUPPLY}</b> (Уник.) — <b>{fmt_stars_compact(lot['price_stars'])} ⭐</b>")
            else:
                bg = BACKDROPS_BY_KEY.get(lot["backdrop_key"])
                bg_name = bg.name if bg else lot["backdrop_key"]
                lines.append(f"• Лот #{lot['id']}: {g_emoji} <b>#{lot['upgrade_num']} {clean_html(lot['model_name'])}</b> ({clean_html(bg_name)}) — <b>{fmt_stars_compact(lot['price_stars'])} ⭐</b>")
            buttons.append([
                InlineKeyboardButton(f"⚙️ Лот #{lot['id']} ({fmt_stars_compact(lot['price_stars'])}⭐)", callback_data=f"market_lot:{lot['id']}")
            ])
        text = "\n".join(lines)

    buttons.append([InlineKeyboardButton("➕ Продать улучшенный NFT", callback_data="market_create_offer")])
    buttons.append([InlineKeyboardButton("⬅️ Назад в маркет", callback_data="nav_market")])
    kb = InlineKeyboardMarkup(buttons)

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_market_history(query, user_id: int):
    rows = get_market_history(limit=12)
    if not rows:
        text = "📊 <b>История сделок маркета</b>\n\nСделок пока ещё не было."
    else:
        lines = ["📊 <b>Последние сделки на NFT Маркете:</b>\n━━━━━━━━━━━━"]
        for r in rows:
            bg = BACKDROPS_BY_KEY.get(r["backdrop_key"])
            bg_name = bg.name if bg else r["backdrop_key"]
            g_emoji = get_upgraded_gift_emoji(r["gift_key"])
            role_mark = "🟢 Продано вами" if r["seller_id"] == user_id else "🔵 Куплено вами" if r["buyer_id"] == user_id else "🔸 Сделка"
            lines.append(
                f"{role_mark}: {g_emoji} <b>{clean_html(r['model_name'])}</b> ({clean_html(bg_name)}) — "
                f"<b>{fmt_stars_compact(r['price_stars'])} ⭐</b>"
            )
        text = "\n".join(lines)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в маркет", callback_data="nav_market")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="nav_main")],
    ])
    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

# FSM: Выставление лота на маркет (market_offer_conv)
async def market_sell_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    query = update.callback_query
    user = query.from_user
    item_id = int(query.data.split(":")[1])

    item = get_collection_item(item_id)
    if not item or item["user_id"] != user.id:
        await query.answer("❌ Подарок не найден.", show_alert=True)
        return ConversationHandler.END
    if not item["is_upgraded"] and item["gift_key"] != "scared_cat":
        await query.answer("❌ На маркет можно выставлять только улучшенные подарки или Scared Cat!", show_alert=True)
        return ConversationHandler.END
    if item["is_listed"]:
        await query.answer("⚠️ Подарок уже выставлен на маркете.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    context.user_data["market_sell_item_id"] = item_id
    g_title = get_upgraded_gift_title(item["gift_key"])
    g_emoji = get_upgraded_gift_emoji(item["gift_key"])
    if item["gift_key"] == "scared_cat" and not item["is_upgraded"]:
        ed_n = int(item["edition_num"] or item["id"])
        text = (
            f"🛒 <b>Выставление на NFT Маркет</b>\n"
            f"━━━━━━━━━━━━\n"
            f"Подарок: <b>{g_title} #{ed_n}/{SCARED_CAT_MAX_SUPPLY}</b>\n"
            f"{g_emoji} Тип: <b>Уникальный коллекционный NFT</b>\n"
            f"💎 Базовая стоимость: <b>~{fmt_stars_compact(SCARED_CAT_DEF.stars)} ⭐</b>\n"
            f"━━━━━━━━━━━━\n"
            f"Введите цену продажи в Stars (от <b>{MARKET_MIN_PRICE:,}</b> до <b>{fmt_stars_compact(MARKET_MAX_PRICE)} ⭐</b>):\n"
            f"<i>При покупке маркет удержит комиссию {int(MARKET_FEE_RATE * 100)}%.</i>"
        )
    else:
        bg = BACKDROPS_BY_KEY.get(item["backdrop_key"])
        bg_name = bg.name if bg else (item["backdrop_key"] or "")
        text = (
            f"🛒 <b>Выставление на NFT Маркет</b>\n"
            f"━━━━━━━━━━━━\n"
            f"Подарок: <b>{g_title} #{item['upgrade_num']}</b>\n"
            f"{g_emoji} Модель: <b>{clean_html(item['model_name'])}</b>\n"
            f"🎨 Фон: <b>{clean_html(bg_name)}</b>\n"
            f"💎 Рекомендованная цена: <b>~{fmt_stars_compact(item['upgraded_stars'])} ⭐</b>\n"
            f"━━━━━━━━━━━━\n"
            f"Введите цену продажи в Stars (от <b>{MARKET_MIN_PRICE:,}</b> до <b>{fmt_stars_compact(MARKET_MAX_PRICE)} ⭐</b>):\n"
            f"<i>При покупке маркет удержит комиссию {int(MARKET_FEE_RATE * 100)}%.</i>"
        )
    kb = InlineKeyboardMarkup([[make_btn("❌ Отмена", style="danger", callback_data="market_sell_cancel")]])
    await safe_edit_or_reply(query, text, reply_markup=kb)
    return WAIT_MARKET_OFFER_PRICE

async def market_sell_price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    raw = re.sub(r"[\s,_.]", "", update.message.text.strip())
    if not raw.isdigit():
        await update.message.reply_text(
            f"❌ Введите целое число от {MARKET_MIN_PRICE:,} до {MARKET_MAX_PRICE:,} (или /cancel):"
        )
        return WAIT_MARKET_OFFER_PRICE

    price = int(raw)
    if price < MARKET_MIN_PRICE or price > MARKET_MAX_PRICE:
        await update.message.reply_text(
            f"❌ Цена должна быть от <b>{MARKET_MIN_PRICE:,} ⭐</b> до <b>{MARKET_MAX_PRICE:,} ⭐</b>!",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_MARKET_OFFER_PRICE

    item_id = context.user_data.get("market_sell_item_id")
    if not item_id:
        await update.message.reply_text("❌ Сессия устарела. Попробуйте снова.", reply_markup=quick_nav_keyboard())
        return ConversationHandler.END

    item_row = get_collection_item(item_id)
    g_title = get_upgraded_gift_title(item_row["gift_key"] if item_row else "pepe_heart")

    ok, msg_res, listing_id = create_market_listing(update.effective_user.id, item_id, price)
    context.user_data.pop("market_sell_item_id", None)
    if not ok:
        await update.message.reply_text(f"❌ {msg_res}", reply_markup=quick_nav_keyboard())
        return ConversationHandler.END

    fee = int(price * MARKET_FEE_RATE)
    seller_gets = price - fee
    bot_username = await get_bot_username(context.bot)
    lot_link = f"https://t.me/{bot_username}?start=lot_{listing_id}"
    share_url = (
        f"https://t.me/share/url?url={urllib.parse.quote(lot_link)}"
        f"&text={urllib.parse.quote(f'🛒 Выставил {g_title} на NFT Маркет за {fmt_stars_compact(price)} ⭐! Лот #{listing_id}')}"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("🔗 Поделиться подарком", style="primary", url=share_url)],
        [make_btn(f"🔎 Открыть лот #{listing_id}", style="success", callback_data=f"market_lot:{listing_id}")],
        [InlineKeyboardButton("🛒 В NFT Маркет", callback_data="nav_market")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="nav_main")],
    ])
    await update.message.reply_text(
        f"✅ <b>Лот #{listing_id} выставлен на маркет!</b>\n"
        f"━━━━━━━━━━━━\n"
        f"• Цена для покупателей: <b>{fmt_stars_compact(price)} ⭐</b>\n"
        f"• Комиссия площадки (15%): <b>-{fmt_stars_compact(fee)} ⭐</b>\n"
        f"• Вы получите при продаже: <b>+{fmt_stars_compact(seller_gets)} ⭐</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END

async def market_sell_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("market_sell_item_id", None)
    if update.callback_query:
        await update.callback_query.answer("Отменено.")
        await show_market_hub(update.callback_query)
    elif update.message:
        await update.message.reply_text("❌ Выставление на маркет отменено.", reply_markup=quick_nav_keyboard())
    return ConversationHandler.END

# FSM: Бесплатная передача подарка по кнопке (gift_transfer_conv)
async def gift_transfer_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    query = update.callback_query
    user = query.from_user
    parts = query.data.split(":")
    if parts[0] == "chat_gx_pick" and len(parts) >= 3:
        sender_id = int(parts[1])
        item_id = int(parts[2])
        if user.id != sender_id:
            await query.answer("❌ Это не ваше меню передачи!", show_alert=True)
            return ConversationHandler.END
    else:
        item_id = int(parts[1])

    item = get_collection_item(item_id)
    if not item or item["user_id"] != user.id:
        await query.answer("❌ Подарок не найден.", show_alert=True)
        return ConversationHandler.END
    if item["is_listed"]:
        await query.answer("❌ Сначала снимите подарок с маркета!", show_alert=True)
        return ConversationHandler.END

    if not item["is_upgraded"]:
        sender_db = get_or_create_user(user.id, user.username or "", user.first_name or "")
        lvl, _, _, _ = calculate_xp_level_info(sender_db["xp"])
        if lvl < TRANSFER_MIN_LEVEL:
            await query.answer(f"❌ Передача обычных подарков доступна с {TRANSFER_MIN_LEVEL}-го уровня!", show_alert=True)
            return ConversationHandler.END

    await query.answer()
    context.user_data["gift_transfer_item_id"] = item_id
    g = GIFTS_BY_KEY.get(item["gift_key"])
    g_title = get_upgraded_gift_title(item["gift_key"])
    title = f"{g_title} #{item['upgrade_num']} ({item['model_name']})" if item["is_upgraded"] else (g.name if g else "Подарок")

    text = (
        f"🎁 <b>Бесплатная передача подарка</b>\n"
        f"━━━━━━━━━━━━\n"
        f"Подарок: <b>{clean_html(title)}</b>\n\n"
        f"Отправьте <code>@username</code> или <code>Telegram ID</code> игрока, которому хотите подарить этот NFT бесплатно:"
    )
    kb = InlineKeyboardMarkup([[make_btn("❌ Отмена", style="danger", callback_data="gift_transfer_cancel")]])
    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_GIFT_TRANSFER_USER

async def gift_transfer_user_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    sender = update.effective_user
    target_str = update.message.text.strip()
    target_row = get_user_by_target(target_str)
    if not target_row and update.message.reply_to_message and update.message.reply_to_message.from_user:
        ru = update.message.reply_to_message.from_user
        if not ru.is_bot:
            target_row = get_or_create_user(ru.id, ru.username or "", ru.first_name or "")

    if not target_row:
        await update.message.reply_text("❌ Игрок не найден в базе бота. Введите @username или ID заново (или /cancel):")
        return WAIT_GIFT_TRANSFER_USER
    if target_row["user_id"] == sender.id:
        await update.message.reply_text("❌ Нельзя передать подарок самому себе! Укажите другого игрока (или /cancel):")
        return WAIT_GIFT_TRANSFER_USER

    item_id = context.user_data.get("gift_transfer_item_id")
    item = get_collection_item(item_id) if item_id else None
    if not item or item["user_id"] != sender.id:
        context.user_data.pop("gift_transfer_item_id", None)
        await update.message.reply_text("❌ Подарок не найден.", reply_markup=quick_nav_keyboard())
        return ConversationHandler.END

    ok, res = transfer_gift_between_users(sender.id, target_row["user_id"], item_id)
    context.user_data.pop("gift_transfer_item_id", None)
    if not ok:
        await update.message.reply_text(f"❌ {res}", reply_markup=quick_nav_keyboard())
        return ConversationHandler.END

    g = GIFTS_BY_KEY.get(res)
    if item["is_upgraded"]:
        g_label = f"{get_upgraded_gift_title(item['gift_key'])} #{item['upgrade_num']} ({item['model_name']})"
    else:
        g_label = g.name if g else res

    receiver_name = normalize_telegram_name(target_row["first_name"], target_row["username"], target_row["user_id"])

    try:
        if item["is_upgraded"]:
            m = get_model_def(item["gift_key"], item["model_name"])
            b = BACKDROPS_BY_KEY.get(item["backdrop_key"]) or PLUSHPEPE_BACKDROPS[0]
            card_io = await generate_upgraded_gift_image(
                m, b, item["upgrade_num"], item["upgraded_stars"], gift_key=item["gift_key"], buff_badge=format_buffs_compact(item)
            )
            await context.bot.send_photo(
                chat_id=target_row["user_id"],
                photo=InputFile(card_io, filename=f"gift_{item['id']}.png"),
                caption=(
                    f"🎁 <b>Вам бесплатно подарили улучшенный NFT!</b>\n\n"
                    f"От: <b>{clean_html(sender.first_name)}</b>\n"
                    f"Предмет: <b>{clean_html(g_label)}</b>\n"
                    f"🎨 Фон: <b>{clean_html(b.name)}</b> ({b.chance_pct}%)\n"
                    f"Подарок уже добавлен в вашу коллекцию!"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=quick_nav_keyboard(),
            )
        else:
            await context.bot.send_message(
                chat_id=target_row["user_id"],
                text=(
                    f"🎁 <b>Вам бесплатно подарили подарок!</b>\n\n"
                    f"От: <b>{clean_html(sender.first_name)}</b>\n"
                    f"Предмет: <b>{clean_html(g_label)}</b>"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=quick_nav_keyboard(),
            )
    except Exception:
        pass

    await update.message.reply_text(
        f"✅ <b>Подарок бесплатно передан!</b>\n"
        f"Предмет <b>{clean_html(g_label)}</b> отправлен игроку <b>{clean_html(receiver_name)}</b>.",
        parse_mode=ParseMode.HTML,
        reply_markup=quick_nav_keyboard(),
    )
    return ConversationHandler.END

async def gift_transfer_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("gift_transfer_item_id", None)
    if update.callback_query:
        await update.callback_query.answer("Отменено.")
        await update.callback_query.edit_message_text("❌ Передача подарка отменена.", reply_markup=quick_nav_keyboard())
    elif update.message:
        await update.message.reply_text("❌ Передача отменена.", reply_markup=quick_nav_keyboard())
    return ConversationHandler.END

# ---------------------------------------------------------------------------
# АДМИН-ПАНЕЛЬ И ОТКЛЮЧЕНИЕ БОТА (ТЕХРАБОТЫ)
# ---------------------------------------------------------------------------

def build_admin_panel_view() -> Tuple[str, InlineKeyboardMarkup]:
    st = get_admin_dashboard_stats()
    maint_on = is_maintenance_mode()
    maint_status = f"{ce('red_dot')} ОТКЛЮЧЁН (Техработы)" if maint_on else f"{ce('green_dot')} ВКЛЮЧЁН (Работает)"
    maint_btn_text = "Включить бота (Откл. техработы)" if maint_on else "Отключить бота (Техработы)"
    maint_btn_emoji = "green_dot" if maint_on else "red_dot"
    maint_style = "success" if maint_on else "danger"
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    pending_apps = st["pending_apps"]

    rp = st.get("richest_profile")
    if rp:
        rp_line = (
            f"{ce('top')} Самый дорогой профиль: <b>{clean_html(rp['display_name'])}</b> "
            f"(<code>{rp['user_id']}</code>) — <b>{fmt_stars_compact(rp['total_wealth'])} ⭐</b> "
            f"(<i>бал. {fmt_stars_compact(rp['balance_stars'])} + колл. {fmt_stars_compact(rp['collection_value'])}</i>)\n"
        )
    else:
        rp_line = f"{ce('top')} Самый дорогой профиль: <i>нет данных</i>\n"

    tc = st.get("top_collection")
    if tc:
        tc_line = (
            f"{ce('gem')} Самая дорогая коллекция: <b>{clean_html(tc['display_name'])}</b> "
            f"(<code>{tc['user_id']}</code>) — <b>{fmt_stars_compact(tc['collection_value'])} ⭐</b> "
            f"({tc['item_count']:,} шт.)\n"
        )
    else:
        tc_line = f"{ce('gem')} Самая дорогая коллекция: <i>нет данных</i>\n"

    text = (
        f"{ce('crown')} <b>Панель управления администратора</b>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('gear')} Статус бота: <b>{maint_status}</b>\n"
        f"{ce('green_dot')} Онлайн сейчас (5 мин): <b>{st['online_now']:,}</b> (за 24ч: <b>{st['active_24h']:,}</b>)\n"
        f"{ce('smile')} Зарегистрировано игроков: <b>{st['total_users']:,}</b>\n"
        f"{ce('crown')} Авторов: <b>{st['total_authors']:,}</b> (заявок: <b>{pending_apps:,}</b> • конк. акт.: <b>{st['active_giveaways']:,}</b>)\n"
        f"{ce('no_entry')} Заблокировано игроков: <b>{st['total_banned']:,}</b>\n"
        f"{ce('shield')} Создано кланов: <b>{st['total_clans']:,}</b>\n"
        f"{ce('bolt')} Играют в дуэли (баттлы): <b>{st['duel_players_now']:,}</b> "
        f"(комнат: <b>{st['duel_rooms_now']:,}</b> • сыграно: <b>{st['duel_finished_total']:,}</b>)\n"
        f"{ce('game')} Открыто кейсов (всего): <b>{st['total_cases_opened']:,}</b>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('dollar')} Баланс игроков: <b>{fmt_stars_compact(st['total_stars_capital'])} ⭐</b>\n"
        f"{ce('gem')} Стоимость всех коллекций: <b>{fmt_stars_compact(st['total_collection_value'])} ⭐</b>\n"
        f"{rp_line}"
        f"{tc_line}"
        f"{ce('star')} Всего в обороте звёзд: <b>{fmt_stars_compact(st['eco_total_turnover'])} ⭐</b>\n"
        f"   <i>Выдано: <b>{fmt_stars_compact(st['eco_issued'])}</b> • "
        f"Потрачено/куплено: <b>{fmt_stars_compact(st['eco_spent'])}</b> • "
        f"Сожжено: <b>{fmt_stars_compact(st['eco_burned'])}</b></i>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('fire')} Акция Scared Cat: <b>{st['scared_cat_minted']:,} / {SCARED_CAT_MAX_SUPPLY:,}</b>\n"
        f"{ce('exchange')} NFT Маркет: лотов <b>{st['market_active_lots']:,}</b> • сделок <b>{st['market_total_deals']:,}</b> (<b>{fmt_stars_compact(st['market_total_volume'])} ⭐</b>)\n"
        f"{ce('star')} Магазин (XTR): покупок <b>{st['shop_purchases_cnt']:,}</b> (<b>{st['shop_total_xtr']:,} XTR</b>)\n"
        f"{ce_gift(0)} Подарков в коллекциях: <b>{st['total_collection_gifts']:,}</b> • выбито: <b>{st['total_drops']:,}</b> • продано: <b>{st['total_sold']:,}</b>\n"
        f"{ce('hourglass')} Обновлено: <code>{now_str}</code>\n"
        "━━━━━━━━━━━━\n"
        "Выберите действие:"
    )

    kb = InlineKeyboardMarkup([
        [make_btn(maint_btn_text, style=maint_style, emoji_key=maint_btn_emoji, callback_data="admin_toggle_maintenance")],
        [make_btn("Обновить", style="primary", emoji_key="refresh", callback_data="admin_refresh")],
        [
            make_btn("Рассылка всем", style="primary", emoji_key="megaphone", callback_data="admin_broadcast_start"),
            make_btn("Промокоды", style="success", emoji_key="fire", callback_data="admin_promos_menu:1"),
        ],
        [make_btn(f"Заявки на авторство ({pending_apps})", style="primary" if pending_apps else None, emoji_key="crown", callback_data="admin_author_apps:1")],
        [
            make_btn("Выдать Звёзды игроку", emoji_key="star", callback_data="admin_give_stars_start"),
            make_btn("Авторские Звёзды", emoji_key="crown", callback_data="admin_give_author_stars_start"),
        ],
        [make_btn("Выдать NFT-подарок (фильтры)", emoji_id=CUSTOM_GIFT_EMOJI_IDS[0], callback_data="admin_give_nft_start")],
        [
            make_btn("Забанить игрока", style="danger", emoji_key="no_entry", callback_data="admin_ban_start"),
            make_btn("Разбанить игрока", style="success", emoji_key="check", callback_data="admin_unban_start"),
        ],
        [make_btn("Firebase Облако (base.db)", emoji_key="globe", callback_data="admin_firebase_menu")],
        [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")],
    ])
    return text, kb

async def show_admin_panel(query) -> None:
    text, kb = build_admin_panel_view()

    try:
        if query.message.photo:
            await query.message.delete()
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            log.warning("show_admin_panel error: %s", e)

async def show_admin_firebase_menu(query) -> None:
    status_icon = "🟢" if firebase_manager.initialized else "⚠️"
    status_msg = (
        "Подключено к Cloud Firestore (100% бесплатно)" if firebase_manager.initialized
        else "Инициализация..."
    )

    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    if firebase_manager.last_sync_ts > 0:
        diff = int(time.time() - firebase_manager.last_sync_ts)
        ago_str = f"{diff} сек. назад"
    else:
        ago_str = "еще не производилась"

    safe_status_msg = clean_html(status_msg)
    safe_col = clean_html(firebase_manager.collection_name)
    safe_doc = clean_html(firebase_manager.doc_name)
    clean_sync_raw = re.sub(r"<[^>]+>", "", str(firebase_manager.last_sync_status))
    safe_sync_status = clean_html(clean_sync_raw)

    text = (
        "☁️ <b>Управление облачной базой Firebase Firestore</b>\n"
        "━━━━━━━━━━━━\n"
        "• Проект: <b>proar-5a642</b>\n"
        f"• Коллекция: <code>{safe_col}</code>\n"
        f"• Документ: <code>{safe_doc}</code>\n"
        f"• Статус: {status_icon} <b>{safe_status_msg}</b>\n"
        f"• Локальная база: <b>{db_size:,} байт</b>\n"
        f"• Синхронизация: <b>{safe_sync_status}</b> ({ago_str})\n"
        "━━━━━━━━━━━━\n"
    )

    kb = InlineKeyboardMarkup([
        [make_btn("🔄 Сохранить в Firestore сейчас", style="success", callback_data="admin_firebase_sync")],
        [make_btn("📥 Восстановить из Firestore", style="primary", callback_data="admin_firebase_restore")],
        [InlineKeyboardButton("🔑 Обновить JSON-ключ Firebase", callback_data="admin_firebase_upload_key")],
        [InlineKeyboardButton("👑 В админ-панель", callback_data="admin_panel")],
    ])

    try:
        if query.message.photo:
            await query.message.delete()
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception:
        plain_text = re.sub(r"<[^>]+>", "", text)
        if query.message.photo:
            await query.message.reply_text(plain_text, reply_markup=kb)
        else:
            await query.edit_message_text(plain_text, reply_markup=kb)

async def admin_firebase_upload_key_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Доступ запрещен!", show_alert=True)
        return ConversationHandler.END
    await query.answer()

    text = (
        "🔑 <b>Обновление сервисного JSON-ключа Firebase</b>\n\n"
        "Отправьте скачанный <code>.json</code> файл сервисного аккаунта в этот чат как документ (файл)."
    )
    kb = InlineKeyboardMarkup([[make_btn("❌ Отмена", style="danger", callback_data="admin_cancel")]])

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_ADMIN_FIREBASE_JSON

async def admin_firebase_json_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END

    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith(".json"):
        await update.message.reply_text("⚠️ Пожалуйста, отправьте файл ключа с расширением .json как документ.")
        return WAIT_ADMIN_FIREBASE_JSON

    try:
        tg_file = await doc.get_file()
        file_bytes = await tg_file.download_as_bytearray()
        data = json.loads(file_bytes.decode("utf-8"))

        if "private_key" not in data or "client_email" not in data:
            await update.message.reply_text("❌ В этом файле нет полей private_key или client_email.")
            return WAIT_ADMIN_FIREBASE_JSON

        target_path = BASE_DIR / "firebase-service-account.json"
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        firebase_manager.init_app(force_reload=True)
        sync_ok = firebase_manager.upload_db_to_cloud(force=True)

        if sync_ok:
            await update.message.reply_text(
                f"✅ <b>Новый ключ Firebase установлен и проверен!</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👑 В админ-панель", callback_data="admin_panel")]])
            )
        else:
            clean_err = clean_html(re.sub(r"<[^>]+>", "", str(firebase_manager.last_sync_status)))
            await update.message.reply_text(
                f"⚠️ Ключ сохранен, но возникла ошибка:\n<code>{clean_err}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👑 В админ-панель", callback_data="admin_panel")]])
            )
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка обработки файла: {e}")
        return ConversationHandler.END

# --- БАН / РАЗБАН ---

async def admin_ban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Доступ запрещен!", show_alert=True)
        return ConversationHandler.END
    await query.answer()

    text = "🔨 <b>Блокировка игрока</b>\n\nВведите Telegram ID или @username нарушителя:"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel")]])

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_ADMIN_BAN_USER

async def admin_ban_user_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_user_by_target(update.message.text.strip())
    if not target:
        await update.message.reply_text("❌ Пользователь не найден в базе данных. Попробуйте снова:")
        return WAIT_ADMIN_BAN_USER

    if target["user_id"] in ADMIN_IDS:
        await update.message.reply_text("❌ Нельзя заблокировать администратора!")
        return ConversationHandler.END

    context.user_data["ban_target_id"] = target["user_id"]
    tname = normalize_telegram_name(target["first_name"], target["username"], target["user_id"])
    await update.message.reply_text(
        f"✅ Игрок найден: <b>{clean_html(tname)}</b> (ID: <code>{target['user_id']}</code>).\n\n"
        "Введите срок блокировки в часах:",
        parse_mode=ParseMode.HTML
    )
    return WAIT_ADMIN_BAN_HOURS

async def admin_ban_hours_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hours_str = update.message.text.strip()
    if not hours_str.isdigit() or int(hours_str) <= 0:
        await update.message.reply_text("❌ Введите корректное положительное число часов:")
        return WAIT_ADMIN_BAN_HOURS

    context.user_data["ban_hours"] = int(hours_str)
    await update.message.reply_text("📝 Введите причину блокировки (кратко):")
    return WAIT_ADMIN_BAN_REASON

async def admin_ban_reason_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason = update.message.text.strip()
    target_id = context.user_data.get("ban_target_id")
    hours = context.user_data.get("ban_hours", 24)

    ban_user(target_id, hours, reason)

    try:
        until_ts = int(time.time()) + (hours * 3600)
        ban_text, ban_kb = format_ban_message(until_ts, reason, hours)
        await context.bot.send_message(chat_id=target_id, text=ban_text, parse_mode=ParseMode.HTML, reply_markup=ban_kb)
    except Exception:
        pass

    await update.message.reply_text(
        f"⛔️ <b>Игрок (ID: <code>{target_id}</code>) заблокирован!</b>\n"
        f"• Срок: <b>{hours} ч.</b>\n• Причина: <b>{clean_html(reason)}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 В админ-панель", callback_data="admin_panel")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="nav_main")]
        ])
    )
    return ConversationHandler.END

async def admin_unban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Доступ запрещен!", show_alert=True)
        return ConversationHandler.END
    await query.answer()

    text = "🔓 <b>Разблокировка игрока</b>\n\nВведите Telegram ID или @username игрока:"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel")]])

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_ADMIN_UNBAN_USER

async def admin_unban_user_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_user_by_target(update.message.text.strip())
    if not target:
        await update.message.reply_text("❌ Пользователь не найден. Попробуйте снова:")
        return WAIT_ADMIN_UNBAN_USER

    target_id = target["user_id"]
    unban_user(target_id)

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text="🎉 <b>Ваш аккаунт разблокирован администрацией!</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard()
        )
    except Exception:
        pass

    await update.message.reply_text(
        f"✅ <b>Игрок (ID: <code>{target_id}</code>) разблокирован!</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 В админ-панель", callback_data="admin_panel")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="nav_main")]
        ])
    )
    return ConversationHandler.END

# --- ВЫДАЧА STARS ---

async def admin_give_stars_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Доступ запрещен!", show_alert=True)
        return ConversationHandler.END
    await query.answer()

    text = "⭐ <b>Выдача Звёзд игроку</b>\n\nВведите Telegram ID или @username игрока:"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel")]])

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_ADMIN_GIVE_STARS_USER

async def admin_give_stars_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_user_by_target(update.message.text.strip())
    if not target:
        await update.message.reply_text("❌ Пользователь не найден. Попробуйте снова:")
        return WAIT_ADMIN_GIVE_STARS_USER

    context.user_data["admin_target_user_id"] = target["user_id"]
    target_name = normalize_telegram_name(target["first_name"], target["username"], target["user_id"])
    await update.message.reply_text(
        f"✅ Пользователь найден: <b>{clean_html(target_name)}</b> (ID: <code>{target['user_id']}</code>).\n\n"
        "Введите количество Stars (⭐) для начисления:",
        parse_mode=ParseMode.HTML
    )
    return WAIT_ADMIN_GIVE_STARS_AMOUNT

async def admin_give_stars_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amt_str = update.message.text.strip()
    if not amt_str.isdigit() or int(amt_str) <= 0:
        await update.message.reply_text("❌ Введите положительное число звёзд:")
        return WAIT_ADMIN_GIVE_STARS_AMOUNT

    amount = int(amt_str)
    target_id = context.user_data.get("admin_target_user_id")
    add_user_stars(target_id, amount)

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"🎉 <b>Вам начислено +{amount:,} ⭐ от Администрации!</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard()
        )
    except Exception:
        pass

    await update.message.reply_text(
        f"✅ Успешно начислено <b>{amount:,} ⭐</b> пользователю (ID: <code>{target_id}</code>)!",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 В админ-панель", callback_data="admin_panel")],
            [InlineKeyboardButton("🏠 В главное меню", callback_data="nav_main")]
        ])
    )
    return ConversationHandler.END

# --- ВЫДАЧА NFT ПО ФИЛЬТРАМ ---

async def admin_give_nft_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Доступ запрещен!", show_alert=True)
        return ConversationHandler.END
    await query.answer()

    text = "🎁 <b>Выдача NFT-подарка игроку</b>\n\nВведите Telegram ID или @username игрока:"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="admin_cancel")]])

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_ADMIN_GIVE_NFT_USER

async def admin_give_nft_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_user_by_target(update.message.text.strip())
    if not target:
        await update.message.reply_text("❌ Пользователь не найден. Попробуйте еще раз:")
        return WAIT_ADMIN_GIVE_NFT_USER

    target_id = target["user_id"]
    context.user_data["admin_nft_target_user_id"] = target_id
    target_name = normalize_telegram_name(target["first_name"], target["username"], target_id)

    await show_admin_nft_filter_selector(update.message, target_id, target_name)
    return ConversationHandler.END

async def show_admin_nft_filter_selector(msg_or_query, target_id: int, target_name: str):
    text = (
        f"🎁 <b>Выдача подарка для игрока {clean_html(target_name)} (ID: {target_id})</b>\n\n"
        "Выберите способ фильтрации подарков или сразу выдайте кастомный улучшенный NFT:"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Выдать улучшенный NFT (Модель + Фон)", callback_data=f"adm_give_upg_pick:{target_id}")],
        [InlineKeyboardButton("💰 Фильтр: По стоимости", callback_data=f"adm_filt_price:{target_id}")],
        [InlineKeyboardButton("🧸 Фильтр: По моделям", callback_data=f"adm_filt_model:{target_id}")],
        [InlineKeyboardButton("📋 Все подарки", callback_data=f"adm_items:all:all:{target_id}:1")],
        [InlineKeyboardButton("👑 В админ-панель", callback_data="admin_panel")]
    ])
    if hasattr(msg_or_query, "reply_text"):
        await msg_or_query.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await msg_or_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_admin_nft_price_tiers(query, target_id: int):
    text = f"💰 <b>Выбор по стоимости (ID получателя: {target_id}):</b>"
    buttons = [[InlineKeyboardButton(ptitle, callback_data=f"adm_items:price:{pkey}:{target_id}:1")] for pkey, (ptitle, _, _) in PRICE_TIERS.items()]
    buttons.append([InlineKeyboardButton("⬅️ К выбору фильтра", callback_data=f"adm_back_filters:{target_id}")])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def show_admin_nft_model_groups(query, target_id: int):
    text = f"🧸 <b>Выбор по моделям Telegram (ID получателя: {target_id}):</b>"
    buttons = [[InlineKeyboardButton(mtitle, callback_data=f"adm_items:model:{mkey}:{target_id}:1")] for mkey, mtitle in MODEL_GROUPS.items()]
    buttons.append([InlineKeyboardButton("⬅️ К выбору фильтра", callback_data=f"adm_back_filters:{target_id}")])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def show_admin_nft_items_page(query, ftype: str, fkey: str, target_id: int, page: int = 1):
    gifts_pool = get_gifts_filtered(ftype, fkey)
    page_size = 6
    total_pages = max(1, math.ceil(len(gifts_pool) / page_size))
    page = max(1, min(page, total_pages))

    items = gifts_pool[(page - 1) * page_size : page * page_size]

    text = (
        f"🎁 <b>Выберите подарок для выдачи (Стр. {page}/{total_pages})</b>\n"
        f"Получатель ID: <code>{target_id}</code>"
    )

    buttons = []
    for g in items:
        if g.key in UPGRADABLE_GIFT_KEYS:
            buttons.append([InlineKeyboardButton(f"✨ {g.name[:25]} ({g.stars:,}⭐)", callback_data=f"adm_give_mode:{g.key}:{target_id}")])
        else:
            buttons.append([InlineKeyboardButton(f"🎁 {g.name[:25]} ({g.stars:,}⭐)", callback_data=f"adm_give_do:{g.key}:{target_id}")])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"adm_items:{ftype}:{fkey}:{target_id}:{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"adm_items:{ftype}:{fkey}:{target_id}:{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton("📂 Сменить фильтр", callback_data=f"adm_back_filters:{target_id}")])
    buttons.append([InlineKeyboardButton("👑 Админ-Панель", callback_data="admin_panel")])

    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def show_admin_give_mode_selector(query, gift_key: str, target_id: int):
    g = GIFTS_BY_KEY.get(gift_key)
    g_name = g.name if g else gift_key
    text = (
        f"✨ <b>Выдача подарка «{clean_html(g_name)}»</b>\n"
        f"Получатель ID: <code>{target_id}</code>\n\n"
        "Выберите тип подарка:"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Обычный подарок", callback_data=f"adm_give_std:{gift_key}:{target_id}")],
        [InlineKeyboardButton("✨ Улучшенный NFT (выбрать модель и фон)", callback_data=f"adm_give_upg_models:{gift_key}:{target_id}:1")],
        [InlineKeyboardButton("⬅️ К фильтрам", callback_data=f"adm_back_filters:{target_id}")],
    ])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_admin_upg_gift_picker(query, target_id: int):
    text = (
        f"✨ <b>Выдача улучшенного NFT</b>\n"
        f"Получатель ID: <code>{target_id}</code>\n\n"
        "Выберите коллекцию улучшаемого NFT:"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🐸 Plush Pepe (50 моделей)", callback_data=f"adm_give_upg_models:pepe_heart:{target_id}:1")],
        [InlineKeyboardButton("💝 Heart Locket (61 модель)", callback_data=f"adm_give_upg_models:heart_lock_key:{target_id}:1")],
        [InlineKeyboardButton("🧢 Durov's Cap (55 моделей)", callback_data=f"adm_give_upg_models:cap_tg:{target_id}:1")],
        [InlineKeyboardButton("🏆 Algorithm Cup (4 модели)", callback_data=f"adm_give_upg_models:trophy_cup:{target_id}:1")],
        [InlineKeyboardButton("💍 Bonded Ring (50 моделей)", callback_data=f"adm_give_upg_models:bonded_ring:{target_id}:1")],
        [InlineKeyboardButton("⬅️ Назад к фильтрам", callback_data=f"adm_back_filters:{target_id}")],
    ])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_admin_upg_models_page(query, gift_key: str, target_id: int, page: int = 1):
    if gift_key not in UPGRADABLE_GIFT_KEYS:
        gift_key = "pepe_heart"
    models_pool = get_models_for_gift(gift_key)
    g_title = get_upgraded_gift_title(gift_key)
    g_emoji = get_upgraded_gift_emoji(gift_key)

    page_size = 10
    total_pages = max(1, math.ceil(len(models_pool) / page_size))
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * page_size
    page_models = models_pool[start_idx : start_idx + page_size]

    text = (
        f"{g_emoji} <b>Выберите модель {g_title} (Стр. {page}/{total_pages})</b>\n"
        f"Получатель ID: <code>{target_id}</code>"
    )
    buttons = []
    for offset, m in enumerate(page_models):
        m_idx = start_idx + offset
        buttons.append([
            InlineKeyboardButton(
                f"{g_emoji} {m.name} ({m.chance_pct}% • x{m.price_mult})",
                callback_data=f"adm_give_upg_bgs:{gift_key}:{m_idx}:{target_id}:1",
            )
        ])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"adm_give_upg_models:{gift_key}:{target_id}:{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"adm_give_upg_models:{gift_key}:{target_id}:{page+1}"))
    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton("⬅️ Выбор коллекции NFT", callback_data=f"adm_give_upg_pick:{target_id}")])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def show_admin_upg_backdrops_page(query, gift_key: str, m_idx: int, target_id: int, page: int = 1):
    if gift_key not in UPGRADABLE_GIFT_KEYS:
        gift_key = "pepe_heart"
    models_pool = get_models_for_gift(gift_key)
    m_idx = max(0, min(m_idx, len(models_pool) - 1))
    chosen_model = models_pool[m_idx]

    page_size = 10
    total_pages = max(1, math.ceil(len(PLUSHPEPE_BACKDROPS) / page_size))
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * page_size
    page_bgs = PLUSHPEPE_BACKDROPS[start_idx : start_idx + page_size]

    text = (
        f"🎨 <b>Выберите фон (Стр. {page}/{total_pages})</b>\n"
        f"Модель: <b>{clean_html(chosen_model.name)}</b>\n"
        f"Получатель ID: <code>{target_id}</code>"
    )
    buttons = []
    for offset, b in enumerate(page_bgs):
        b_idx = start_idx + offset
        mono_mark = " 🌈x6" if is_monochrome_combo(chosen_model.name, b.key) else ""
        buttons.append([
            InlineKeyboardButton(
                f"{b.name} ({b.rarity_label}, {b.chance_pct}%){mono_mark}",
                callback_data=f"adm_give_upg_confirm:{gift_key}:{m_idx}:{b_idx}:{target_id}",
            )
        ])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"adm_give_upg_bgs:{gift_key}:{m_idx}:{target_id}:{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"adm_give_upg_bgs:{gift_key}:{m_idx}:{target_id}:{page+1}"))
    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton("⬅️ К моделям", callback_data=f"adm_give_upg_models:{gift_key}:{target_id}:1")])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def show_admin_upg_confirm(query, gift_key: str, m_idx: int, b_idx: int, target_id: int):
    if gift_key not in UPGRADABLE_GIFT_KEYS:
        gift_key = "pepe_heart"
    models_pool = get_models_for_gift(gift_key)
    chosen_model = models_pool[max(0, min(m_idx, len(models_pool) - 1))]
    chosen_bg = PLUSHPEPE_BACKDROPS[max(0, min(b_idx, len(PLUSHPEPE_BACKDROPS) - 1))]
    g = GIFTS_BY_KEY[gift_key]
    est_stars = calculate_upgraded_stars(g.stars, chosen_model, chosen_bg, gift_key=gift_key)
    is_mono, mono_fam = get_monochrome_combo_info(chosen_model.name, chosen_bg.key)
    g_title = get_upgraded_gift_title(gift_key)
    g_emoji = get_upgraded_gift_emoji(gift_key)
    mono_line = f"\n🌈 Комбо: <b>MONOCHROME x6</b> ({COLOR_FAMILY_RU.get(mono_fam, mono_fam)})" if is_mono else ""

    text = (
        f"✨ <b>Подтверждение выдачи улучшенного NFT</b>\n"
        "━━━━━━━━━━━━\n"
        f"👤 Получатель ID: <code>{target_id}</code>\n"
        f"{g_emoji} Коллекция: <b>{g_title}</b>\n"
        f"🎭 Модель: <b>{clean_html(chosen_model.name)}</b> (шанс {chosen_model.chance_pct}%)\n"
        f"🎨 Фон: <b>{clean_html(chosen_bg.name)}</b> • <i>{chosen_bg.rarity_label}</i> ({chosen_bg.chance_pct}%){mono_line}\n"
        f"💎 Оценочная ценность: <b>{fmt_stars_rub(est_stars)}</b>\n"
        "━━━━━━━━━━━━\n"
        "Номер <code>#upgrade_num</code> будет присвоен автоматически по глобальному счётчику."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Выдать улучшенный NFT", callback_data=f"adm_give_upg_do:{gift_key}:{m_idx}:{b_idx}:{target_id}")],
        [InlineKeyboardButton("🎨 Изменить фон", callback_data=f"adm_give_upg_bgs:{gift_key}:{m_idx}:{target_id}:1")],
        [InlineKeyboardButton("⬅️ К моделям", callback_data=f"adm_give_upg_models:{gift_key}:{target_id}:1")],
    ])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def execute_admin_give_upgraded_nft(
    query,
    gift_key: str,
    m_idx: int,
    b_idx: int,
    target_id: int,
    context: ContextTypes.DEFAULT_TYPE,
):
    if gift_key not in UPGRADABLE_GIFT_KEYS:
        await query.answer("❌ Неподдерживаемый NFT для улучшения.", show_alert=True)
        return
    models_pool = get_models_for_gift(gift_key)
    chosen_model = models_pool[max(0, min(m_idx, len(models_pool) - 1))]
    chosen_bg = PLUSHPEPE_BACKDROPS[max(0, min(b_idx, len(PLUSHPEPE_BACKDROPS) - 1))]
    g = GIFTS_BY_KEY[gift_key]
    est_stars = calculate_upgraded_stars(g.stars, chosen_model, chosen_bg, gift_key=gift_key)
    is_mono, mono_fam = get_monochrome_combo_info(chosen_model.name, chosen_bg.key)

    ok, msg_res, upgrade_num, _item_id = admin_grant_upgraded_nft_db(
        target_user_id=target_id,
        gift_key=gift_key,
        model_name=chosen_model.name,
        backdrop_key=chosen_bg.key,
        upgraded_stars=est_stars,
    )
    if not ok:
        await query.answer(f"❌ {msg_res}", show_alert=True)
        return

    g_title = get_upgraded_gift_title(gift_key)
    g_emoji = get_upgraded_gift_emoji(gift_key)
    g_ce = upgraded_gift_tg_emoji(gift_key)
    mono_line = f"\n{ce('rainbow')} Комбо: <b>MONOCHROME x6</b> ({COLOR_FAMILY_RU.get(mono_fam, mono_fam)})" if is_mono else ""

    try:
        card_io = await generate_upgraded_gift_image(
            chosen_model, chosen_bg, upgrade_num, est_stars, gift_key=gift_key
        )
        await context.bot.send_photo(
            chat_id=target_id,
            photo=InputFile(card_io, filename=f"adm_upgraded_{gift_key}_{upgrade_num}.png"),
            caption=(
                f"{ce('boom')} <b>Вам выдан улучшенный NFT от Администрации!</b>\n"
                f"━━━━━━━━━━━━\n"
                f"{g_ce} <b>{g_title} #{upgrade_num}</b>\n"
                f"🎭 Модель: <b>{clean_html(chosen_model.name)}</b> (шанс {chosen_model.chance_pct}%)\n"
                f"{ce('sparkles')} Фон: <b>{clean_html(chosen_bg.name)}</b> • <i>{chosen_bg.rarity_label}</i> ({chosen_bg.chance_pct}%){mono_line}\n"
                f"{ce('gem')} Оценочная ценность: <b>{fmt_stars_rub(est_stars)}</b>\n"
                f"Подарок уже в вашей коллекции!"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard(),
        )
    except Exception:
        pass

    await query.answer(f"✅ Выдан {g_title} #{upgrade_num}!", show_alert=True)
    text = (
        f"✅ <b>Улучшенный NFT выдан игроку ID <code>{target_id}</code>!</b>\n\n"
        f"{g_emoji} <b>{g_title} #{upgrade_num}</b>\n"
        f"Модель: <b>{clean_html(chosen_model.name)}</b>\n"
        f"Фон: <b>{clean_html(chosen_bg.name)}</b> ({chosen_bg.rarity_label})\n"
        f"Ценность: <b>{fmt_stars_rub(est_stars)}</b>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Выдать ещё улучшенный NFT", callback_data=f"adm_give_upg_pick:{target_id}")],
        [InlineKeyboardButton("🎁 К фильтрам выдачи", callback_data=f"adm_back_filters:{target_id}")],
        [InlineKeyboardButton("👑 В админ-панель", callback_data="admin_panel")],
    ])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def execute_admin_give_nft(query, gift_key: str, target_id: int, context: ContextTypes.DEFAULT_TYPE):
    gift = GIFTS_BY_KEY.get(gift_key)
    if not gift:
        await query.answer("❌ Подарок не найден!", show_alert=True)
        return

    add_to_collection(target_id, gift_key)

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                f"🎁 <b>Вам выдан NFT-подарок от Администрации!</b>\n"
                f"<b>{gift.name}</b> ({fmt_stars_rub(gift.stars)})"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard()
        )
    except Exception:
        pass

    await query.answer(f"✅ Выдан: {gift.name}!", show_alert=True)
    text = f"✅ <b>Подарок {gift.name} выдан игроку ID <code>{target_id}</code>!</b>"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Выдать еще", callback_data=f"adm_back_filters:{target_id}")],
        [InlineKeyboardButton("👑 В админ-панель", callback_data="admin_panel")],
    ])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

# --- АДМИН-РАССЫЛКА ВСЕМ ПОЛЬЗОВАТЕЛЯМ ---

_ADMIN_BROADCAST_TASK: Optional[asyncio.Task] = None

async def _run_admin_broadcast_task(bot, admin_chat_id: int, html_body: str, photo_file_id: str) -> None:
    user_ids = get_all_broadcast_user_ids_db()
    sent = 0
    blocked = 0
    failed = 0
    for uid in user_ids:
        try:
            if photo_file_id:
                await bot.send_photo(
                    chat_id=uid,
                    photo=photo_file_id,
                    caption=(html_body or None),
                    parse_mode=(ParseMode.HTML if html_body else None),
                )
            else:
                await bot.send_message(
                    chat_id=uid,
                    text=html_body,
                    parse_mode=ParseMode.HTML,
                )
            sent += 1
        except RetryAfter as e:
            await asyncio.sleep(float(getattr(e, "retry_after", 2)) + 0.5)
            try:
                if photo_file_id:
                    await bot.send_photo(
                        chat_id=uid,
                        photo=photo_file_id,
                        caption=(html_body or None),
                        parse_mode=(ParseMode.HTML if html_body else None),
                    )
                else:
                    await bot.send_message(chat_id=uid, text=html_body, parse_mode=ParseMode.HTML)
                sent += 1
            except Forbidden:
                blocked += 1
            except Exception:
                failed += 1
        except Forbidden:
            blocked += 1
        except BadRequest as e:
            err_l = str(e).lower()
            if "chat not found" in err_l or "blocked" in err_l or "deactivated" in err_l or "user is deactivated" in err_l:
                blocked += 1
            else:
                failed += 1
        except TelegramError:
            failed += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.04)

    summary = (
        f"{ce('megaphone')} <b>Рассылка завершена!</b>\n"
        "━━━━━━━━━━━━\n"
        f"• Всего в базе: <b>{len(user_ids):,}</b>\n"
        f"• {ce('check')} Доставлено: <b>{sent:,}</b>\n"
        f"• {ce('no_entry')} Заблокировали бота / недоступны: <b>{blocked:,}</b>\n"
        f"• {ce('warn')} Прочие ошибки: <b>{failed:,}</b>"
    )
    try:
        await bot.send_message(
            chat_id=admin_chat_id,
            text=summary,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👑 В админ-панель", callback_data="admin_panel")]]),
        )
    except Exception:
        pass

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Доступ запрещен!", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    context.user_data.pop("adm_bc_html", None)
    context.user_data.pop("adm_bc_photo", None)

    total_users = len(get_all_broadcast_user_ids_db())
    text = (
        f"{ce('megaphone')} <b>Рассылка всем игрокам</b>\n"
        "━━━━━━━━━━━━\n"
        f"Получателей в базе: <b>{total_users:,}</b>\n\n"
        "Отправьте сообщение для рассылки:\n"
        "• Можно отправить <b>текст</b> (поддерживаются жирный, курсив, цитаты и <b>премиум-эмодзи Telegram</b>)\n"
        "• Или <b>фото с подписью</b>\n\n"
        "<i>Блокировки бота и ошибки доставки автоматически пропускаются.</i>"
    )
    kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="admin_cancel")]])
    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_ADMIN_BROADCAST_MSG

async def admin_broadcast_msg_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    msg = update.message
    html_body = extract_message_html_with_custom_emojis(msg).strip()
    photo_fid = msg.photo[-1].file_id if msg.photo else ""
    if not html_body and not photo_fid:
        await msg.reply_text("❌ Отправьте текстовое сообщение или фото с подписью (либо /cancel):")
        return WAIT_ADMIN_BROADCAST_MSG
    if photo_fid and len(html_body) > 1024:
        await msg.reply_text("⚠️ Подпись к фото не должна превышать 1024 символа. Отправьте более короткую подпись:")
        return WAIT_ADMIN_BROADCAST_MSG

    context.user_data["adm_bc_html"] = html_body
    context.user_data["adm_bc_photo"] = photo_fid
    total_users = len(get_all_broadcast_user_ids_db())

    # Предпросмотр
    try:
        if photo_fid:
            await msg.reply_photo(photo=photo_fid, caption=(html_body or None), parse_mode=(ParseMode.HTML if html_body else None))
        else:
            await msg.reply_text(html_body, parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.reply_text(f"⚠️ Ошибка предпросмотра HTML: <code>{clean_html(str(e))}</code>\nПопробуйте отправить текст заново:", parse_mode=ParseMode.HTML)
        return WAIT_ADMIN_BROADCAST_MSG

    kb = InlineKeyboardMarkup([
        [make_btn(f"Отправить ({total_users:,} чел.)", style="success", emoji_key="megaphone", callback_data="admin_broadcast_confirm")],
        [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="admin_cancel")],
    ])
    await msg.reply_text(
        f"📣 <b>Предпросмотр выше.</b>\nЗапустить рассылку на <b>{total_users:,}</b> пользователей?",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAIT_ADMIN_BROADCAST_CONFIRM

async def admin_broadcast_confirm_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _ADMIN_BROADCAST_TASK
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Доступ запрещен!", show_alert=True)
        return ConversationHandler.END
    html_body = context.user_data.pop("adm_bc_html", "")
    photo_fid = context.user_data.pop("adm_bc_photo", "")
    if not html_body and not photo_fid:
        await query.answer("❌ Сообщение не найдено.", show_alert=True)
        await show_admin_panel(query)
        return ConversationHandler.END

    if _ADMIN_BROADCAST_TASK and not _ADMIN_BROADCAST_TASK.done():
        await query.answer("⏳ Предыдущая рассылка ещё выполняется!", show_alert=True)
        return ConversationHandler.END

    await query.answer("🚀 Рассылка запущена!")
    _ADMIN_BROADCAST_TASK = asyncio.create_task(
        _run_admin_broadcast_task(context.bot, query.from_user.id, html_body, photo_fid)
    )
    await query.edit_message_text(
        f"{ce('refresh')} <b>Рассылка запущена в фоне!</b>\n"
        "Когда отправка завершится, бот пришлёт подробный отчёт.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👑 В админ-панель", callback_data="admin_panel")]]),
    )
    return ConversationHandler.END

# --- ПРОМОКОДЫ (АДМИН-УПРАВЛЕНИЕ + АКТИВАЦИЯ ИГРОКАМИ) ---

_PROMO_GIFT_PRESETS = ("pepe_heart", "heart_lock_key", "cap_tg", "trophy_cup", "bonded_ring", "scared_cat")

def _format_promo_reward_summary(promo: sqlite3.Row) -> str:
    parts = []
    if int(promo["reward_stars"] or 0) > 0:
        parts.append(f"{int(promo['reward_stars']):,} ⭐")
    if promo["gift_key"] and int(promo["gift_count"] or 0) > 0:
        g = GIFTS_BY_KEY.get(promo["gift_key"])
        gname = g.name if g else promo["gift_key"]
        parts.append(f"{gname} ×{int(promo['gift_count'])}")
    return " + ".join(parts) if parts else "Пусто"

async def show_admin_promos_menu(query_or_msg, page: int = 1) -> None:
    page_size = 6
    rows, total = list_promocodes_db(page=page, page_size=page_size)
    total_pages = max(1, math.ceil(total / page_size))
    page = max(1, min(page, total_pages))

    lines = [
        f"{ce('fire')} <b>Управление промокодами (стр. {page}/{total_pages})</b>",
        "━━━━━━━━━━━━",
        f"Всего промокодов в базе: <b>{total:,}</b>\n",
    ]
    buttons = [[make_btn("Создать промокод", style="success", emoji_key="plus", callback_data="admin_promo_create_start")]]

    if not rows:
        lines.append("<i>Промокодов пока нет. Создайте первый промокод кнопкой выше!</i>")
    else:
        for idx, p in enumerate(rows, start=(page - 1) * page_size + 1):
            st_icon = "🟢" if int(p["is_active"] or 0) else "🔴"
            rew_txt = _format_promo_reward_summary(p)
            lines.append(
                f"{idx}. {st_icon} <code>{clean_html(p['code'])}</code> — "
                f"<b>{int(p['used_count'])}/{int(p['max_uses'])}</b> акц. • {clean_html(rew_txt)}"
            )
            buttons.append([
                make_btn(
                    f"{st_icon} {p['code']} ({int(p['used_count'])}/{int(p['max_uses'])})",
                    style="primary" if int(p["is_active"] or 0) else None,
                    callback_data=f"admin_promo_view:{p['id']}",
                )
            ])

    nav_row = []
    if page > 1:
        nav_row.append(make_btn("◀️ Назад", callback_data=f"admin_promos_menu:{page - 1}"))
    if page < total_pages:
        nav_row.append(make_btn("Вперёд ▶️", callback_data=f"admin_promos_menu:{page + 1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([make_btn("В админ-панель", emoji_key="crown", callback_data="admin_panel")])
    text = "\n".join(lines)
    kb = InlineKeyboardMarkup(buttons)

    if isinstance(query_or_msg, CallbackQuery):
        await safe_edit_or_reply(query_or_msg, text, reply_markup=kb)
    else:
        await query_or_msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_admin_promo_detail(query_or_msg, promo_id: int) -> None:
    p = get_promocode_by_id_db(promo_id)
    if not p:
        if isinstance(query_or_msg, CallbackQuery):
            await query_or_msg.answer("❌ Промокод не найден.", show_alert=True)
            await show_admin_promos_menu(query_or_msg, 1)
        else:
            await query_or_msg.reply_text("❌ Промокод не найден.")
        return

    is_on = bool(int(p["is_active"] or 0))
    st_lbl = f"{ce('green_dot')} Активен" if is_on else f"{ce('red_dot')} Отключён"
    rem = max(0, int(p["max_uses"] or 0) - int(p["used_count"] or 0))
    rew_txt = _format_promo_reward_summary(p)
    dt_str = datetime.datetime.fromtimestamp(int(p["created_ts"] or 0)).strftime("%d.%m.%Y %H:%M")

    text = (
        f"{ce('fire')} <b>Промокод:</b> <code>{clean_html(p['code'])}</code>\n"
        "━━━━━━━━━━━━\n"
        f"• Статус: <b>{st_lbl}</b>\n"
        f"• Награда: <b>{clean_html(rew_txt)}</b>\n"
        f"• Активации: <b>{int(p['used_count']):,} / {int(p['max_uses']):,}</b> (осталось: <b>{rem:,}</b>)\n"
        f"• Создан: <code>{dt_str}</code>\n"
        "━━━━━━━━━━━━\n"
        "Вы можете изменить лимит активаций, отключить или удалить промокод:"
    )
    kb = InlineKeyboardMarkup([
        [
            make_btn("-10", callback_data=f"admin_promo_adj:{promo_id}:-10"),
            make_btn("-1", callback_data=f"admin_promo_adj:{promo_id}:-1"),
            make_btn("+1", callback_data=f"admin_promo_adj:{promo_id}:1"),
            make_btn("+10", callback_data=f"admin_promo_adj:{promo_id}:10"),
            make_btn("+100", callback_data=f"admin_promo_adj:{promo_id}:100"),
        ],
        [make_btn("Задать лимит вручную", style="primary", emoji_key="gear", callback_data=f"admin_promo_edit_max_start:{promo_id}")],
        [make_btn("Отключить" if is_on else "Включить", style="danger" if is_on else "success", emoji_key="red_dot" if is_on else "green_dot", callback_data=f"admin_promo_toggle:{promo_id}")],
        [make_btn("Удалить промокод", style="danger", emoji_key="trash", callback_data=f"admin_promo_del_confirm:{promo_id}")],
        [make_btn("К списку промокодов", emoji_key="bookmark", callback_data="admin_promos_menu:1")],
    ])
    if isinstance(query_or_msg, CallbackQuery):
        await safe_edit_or_reply(query_or_msg, text, reply_markup=kb)
    else:
        await query_or_msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def admin_promo_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Доступ запрещен!", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    for k in ("adm_new_promo_code", "adm_new_promo_rtype", "adm_new_promo_stars", "adm_new_promo_gift", "adm_new_promo_gcnt"):
        context.user_data.pop(k, None)

    text = (
        f"{ce('plus')} <b>Создание промокода — Шаг 1: Код</b>\n"
        "━━━━━━━━━━━━\n"
        "Отправьте текст нового промокода (например: <code>NEWNFT2026</code>) или нажмите кнопку авто-генерации:"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("Сгенерировать случайный код", style="primary", emoji_key="sparkles", callback_data="admin_promo_gen_code")],
        [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="admin_cancel")],
    ])
    await safe_edit_or_reply(query, text, reply_markup=kb)
    return WAIT_ADMIN_PROMO_CODE

async def _prompt_admin_promo_reward_type(msg_or_query, code_val: str, is_edit: bool = False):
    text = (
        f"{ce('fire')} <b>Создание промокода:</b> <code>{clean_html(code_val)}</code>\n"
        "━━━━━━━━━━━━\n"
        "<b>Шаг 2:</b> Выберите тип награды за активацию:"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("Только Звёзды (⭐)", style="primary", emoji_key="star", callback_data="admin_promo_rtype:stars")],
        [make_btn("Только NFT-подарок", style="primary", emoji_id=CUSTOM_GIFT_EMOJI_IDS[0], callback_data="admin_promo_rtype:nft")],
        [make_btn("Звёзды + NFT-подарок", style="success", emoji_key="fire", callback_data="admin_promo_rtype:both")],
        [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="admin_cancel")],
    ])
    if is_edit:
        await safe_edit_or_reply(msg_or_query, text, reply_markup=kb)
    else:
        await msg_or_query.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_ADMIN_PROMO_REWARD_TYPE

async def admin_promo_gen_code_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    await query.answer()
    code = "NFT" + secrets.token_hex(3).upper()
    context.user_data["adm_new_promo_code"] = code
    return await _prompt_admin_promo_reward_type(query, code, is_edit=True)

async def admin_promo_code_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    code = normalize_promo_code(update.message.text)
    if len(code) < 2 or len(code) > 40:
        await update.message.reply_text("❌ Код должен быть от 2 до 40 символов (без пробелов). Попробуйте ещё раз:")
        return WAIT_ADMIN_PROMO_CODE
    context.user_data["adm_new_promo_code"] = code
    return await _prompt_admin_promo_reward_type(update.message, code, is_edit=False)

async def _prompt_admin_promo_gift_step(msg_or_query, is_edit: bool = False):
    text = (
        f"{ce('gem')} <b>Выбор NFT-подарка для промокода</b>\n"
        "━━━━━━━━━━━━\n"
        "Выберите один из популярных NFT кнопкой ниже или отправьте <b>название / ключ</b> любого подарка текстом (например: <code>pepe_heart</code>, <code>Scared Cat</code>, <code>Bonded Ring</code>):"
    )
    btns = []
    for gk in _PROMO_GIFT_PRESETS:
        g = GIFTS_BY_KEY.get(gk)
        if g:
            btns.append([make_btn(f"{g.name} ({fmt_stars_compact(g.stars)}⭐)", callback_data=f"admin_promo_pick_gift:{gk}")])
    btns.append([make_btn("Отмена", style="danger", emoji_key="cross", callback_data="admin_cancel")])
    kb = InlineKeyboardMarkup(btns)
    if is_edit:
        await safe_edit_or_reply(msg_or_query, text, reply_markup=kb)
    else:
        await msg_or_query.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_ADMIN_PROMO_GIFT

async def admin_promo_rtype_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    await query.answer()
    rtype = query.data.split(":", 1)[1]
    context.user_data["adm_new_promo_rtype"] = rtype
    context.user_data["adm_new_promo_stars"] = 0
    context.user_data["adm_new_promo_gift"] = None
    context.user_data["adm_new_promo_gcnt"] = 0

    if rtype in ("stars", "both"):
        kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="admin_cancel")]])
        await safe_edit_or_reply(
            query,
            f"{ce('star')} Введите количество <b>Звёзд (⭐)</b> за 1 активацию промокода:",
            reply_markup=kb,
        )
        return WAIT_ADMIN_PROMO_STARS
    return await _prompt_admin_promo_gift_step(query, is_edit=True)

async def admin_promo_stars_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    raw = re.sub(r"[\s,_.]", "", update.message.text.strip())
    if not raw.isdigit() or int(raw) <= 0:
        await update.message.reply_text("❌ Введите положительное число звёзд:")
        return WAIT_ADMIN_PROMO_STARS
    context.user_data["adm_new_promo_stars"] = int(raw)
    if context.user_data.get("adm_new_promo_rtype") == "both":
        return await _prompt_admin_promo_gift_step(update.message, is_edit=False)
    return await _prompt_admin_promo_max_uses_step(update.message, is_edit=False)

async def admin_promo_gift_picked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    gk = query.data.split(":", 1)[1]
    g = GIFTS_BY_KEY.get(gk)
    if not g:
        await query.answer("❌ Подарок не найден.", show_alert=True)
        return WAIT_ADMIN_PROMO_GIFT
    await query.answer()
    context.user_data["adm_new_promo_gift"] = g.key
    kb = InlineKeyboardMarkup([
        [
            make_btn("1 шт.", style="primary", callback_data="admin_promo_gcnt:1"),
            make_btn("2 шт.", callback_data="admin_promo_gcnt:2"),
            make_btn("5 шт.", callback_data="admin_promo_gcnt:5"),
        ],
        [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="admin_cancel")],
    ])
    await safe_edit_or_reply(
        query,
        f"🎁 Выбран подарок: <b>{clean_html(g.name)}</b>.\nВведите количество подарков за 1 активацию (или выберите кнопкой):",
        reply_markup=kb,
    )
    return WAIT_ADMIN_PROMO_GIFT_COUNT

async def admin_promo_gift_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    q = update.message.text.strip().lower()
    matched = GIFTS_BY_KEY.get(canonical_gift_key(q))
    if not matched:
        for g in GIFTS:
            if q in g.name.lower() or q == g.key.lower():
                matched = g
                break
    if not matched:
        await update.message.reply_text("❌ Подарок с таким ключом/названием не найден. Попробуйте снова или выберите кнопкой выше:")
        return WAIT_ADMIN_PROMO_GIFT
    context.user_data["adm_new_promo_gift"] = matched.key
    kb = InlineKeyboardMarkup([
        [
            make_btn("1 шт.", style="primary", callback_data="admin_promo_gcnt:1"),
            make_btn("2 шт.", callback_data="admin_promo_gcnt:2"),
            make_btn("5 шт.", callback_data="admin_promo_gcnt:5"),
        ],
        [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="admin_cancel")],
    ])
    await update.message.reply_text(
        f"🎁 Выбран подарок: <b>{clean_html(matched.name)}</b>.\nВведите количество подарков за 1 активацию (или выберите кнопкой):",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAIT_ADMIN_PROMO_GIFT_COUNT

async def _prompt_admin_promo_max_uses_step(msg_or_query, is_edit: bool = False):
    kb = InlineKeyboardMarkup([
        [
            make_btn("1", callback_data="admin_promo_max:1"),
            make_btn("10", callback_data="admin_promo_max:10"),
            make_btn("50", callback_data="admin_promo_max:50"),
            make_btn("100", style="primary", callback_data="admin_promo_max:100"),
        ],
        [
            make_btn("500", callback_data="admin_promo_max:500"),
            make_btn("1,000", callback_data="admin_promo_max:1000"),
        ],
        [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="admin_cancel")],
    ])
    text = f"{ce('top')} <b>Последний шаг:</b> Введите лимит активаций промокода (сколько всего игроков смогут его использовать) или выберите кнопкой:"
    if is_edit:
        await safe_edit_or_reply(msg_or_query, text, reply_markup=kb)
    else:
        await msg_or_query.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_ADMIN_PROMO_MAX_USES

async def admin_promo_gcnt_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    await query.answer()
    context.user_data["adm_new_promo_gcnt"] = max(1, int(query.data.split(":", 1)[1]))
    return await _prompt_admin_promo_max_uses_step(query, is_edit=True)

async def admin_promo_gcnt_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    raw = re.sub(r"[\s,_.]", "", update.message.text.strip())
    if not raw.isdigit() or int(raw) < 1 or int(raw) > 50:
        await update.message.reply_text("❌ Введите количество от 1 до 50:")
        return WAIT_ADMIN_PROMO_GIFT_COUNT
    context.user_data["adm_new_promo_gcnt"] = int(raw)
    return await _prompt_admin_promo_max_uses_step(update.message, is_edit=False)

async def _finalize_admin_promo_create(msg_or_query, admin_id: int, max_uses: int, context: ContextTypes.DEFAULT_TYPE):
    code = context.user_data.pop("adm_new_promo_code", "")
    context.user_data.pop("adm_new_promo_rtype", None)
    stars = int(context.user_data.pop("adm_new_promo_stars", 0) or 0)
    gkey = context.user_data.pop("adm_new_promo_gift", None)
    gcnt = int(context.user_data.pop("adm_new_promo_gcnt", 0) or 0)
    ok, err, pid = create_promocode_db(code, stars, gkey, gcnt, max_uses, created_by=admin_id)
    if not ok or not pid:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("👑 К промокодам", callback_data="admin_promos_menu:1")]])
        if isinstance(msg_or_query, CallbackQuery):
            await safe_edit_or_reply(msg_or_query, f"❌ {err}", reply_markup=kb)
        else:
            await msg_or_query.reply_text(f"❌ {err}", parse_mode=ParseMode.HTML, reply_markup=kb)
        return ConversationHandler.END
    await show_admin_promo_detail(msg_or_query, pid)
    return ConversationHandler.END

async def admin_promo_max_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    await query.answer("✅ Промокод создан!")
    max_u = max(1, int(query.data.split(":", 1)[1]))
    return await _finalize_admin_promo_create(query, query.from_user.id, max_u, context)

async def admin_promo_max_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    raw = re.sub(r"[\s,_.]", "", update.message.text.strip())
    if not raw.isdigit() or int(raw) < 1 or int(raw) > 10_000_000:
        await update.message.reply_text("❌ Введите целое число активаций от 1 до 10,000,000:")
        return WAIT_ADMIN_PROMO_MAX_USES
    return await _finalize_admin_promo_create(update.message, update.effective_user.id, int(raw), context)

async def admin_promo_edit_max_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Доступ запрещен!", show_alert=True)
        return ConversationHandler.END
    promo_id = int(query.data.split(":", 1)[1])
    p = get_promocode_by_id_db(promo_id)
    if not p:
        await query.answer("❌ Промокод не найден.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    context.user_data["adm_edit_promo_id"] = promo_id
    kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="admin_cancel")]])
    await safe_edit_or_reply(
        query,
        f"{ce('gear')} Введите новый максимум активаций для промокода <code>{clean_html(p['code'])}</code>\n"
        f"(сейчас: <b>{int(p['used_count'])} / {int(p['max_uses'])}</b>):",
        reply_markup=kb,
    )
    return WAIT_ADMIN_PROMO_EDIT_MAX

async def admin_promo_edit_max_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    promo_id = int(context.user_data.get("adm_edit_promo_id") or 0)
    raw = re.sub(r"[\s,_.]", "", update.message.text.strip())
    if not raw.isdigit() or int(raw) < 1:
        await update.message.reply_text("❌ Введите положительное целое число:")
        return WAIT_ADMIN_PROMO_EDIT_MAX
    ok, err, _new_val = set_promocode_max_uses_db(promo_id, int(raw))
    context.user_data.pop("adm_edit_promo_id", None)
    if not ok:
        await update.message.reply_text(f"❌ {err}")
        return ConversationHandler.END
    await show_admin_promo_detail(update.message, promo_id)
    return ConversationHandler.END

async def promo_redeem_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    if not await ensure_privacy_accepted_private(update, context):
        return ConversationHandler.END
    query = update.callback_query
    if query:
        if query.message and query.message.chat.type != "private":
            await query.answer("⚠️ Активировать промокоды можно только в личных сообщениях с ботом!", show_alert=True)
            return ConversationHandler.END
        await query.answer()
    text = (
        f"{ce('fire')} <b>Активация промокода</b>\n"
        "━━━━━━━━━━━━\n"
        "Отправьте промокод в ответном сообщении, чтобы мгновенно получить бонусные Звёзды или NFT-подарок:"
    )
    kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="promo_redeem_cancel")]])
    if query:
        await safe_edit_or_reply(query, text, reply_markup=kb)
    elif update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_PROMO_REDEEM_CODE

async def promo_redeem_code_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    user = update.effective_user
    get_or_create_user(user.id, user.username or "", user.first_name or "")
    ok, msg_res, info = redeem_promocode_db(user.id, update.message.text or "")
    if not ok:
        kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="promo_redeem_cancel")]])
        await update.message.reply_text(
            f"{ce('cross')} <b>{clean_html(msg_res)}</b>\nПопробуйте ввести другой код или нажмите «Отмена»:",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
        return WAIT_PROMO_REDEEM_CODE

    rew_lines = []
    if info.get("reward_stars"):
        rew_lines.append(f"• {ce('star')} Звёзды: <b>+{info['reward_stars']:,} ⭐</b>")
    if info.get("gift_key") and info.get("gift_count"):
        g_ce = gift_tg_emoji(info["gift_key"])
        rew_lines.append(f"• {g_ce} Подарок: <b>{clean_html(info['gift_name'])}</b> ×<b>{info['gift_count']} шт.</b>")
    if info.get("xp_added"):
        rew_lines.append(f"• {ce('bolt')} Опыт: <b>+{info['xp_added']:,} XP</b>")

    await update.message.reply_text(
        f"{ce('boom')} <b>Промокод <code>{clean_html(info['code'])}</code> успешно активирован!</b>\n"
        "━━━━━━━━━━━━\n"
        + "\n".join(rew_lines),
        parse_mode=ParseMode.HTML,
        reply_markup=quick_nav_keyboard(),
    )
    return ConversationHandler.END

async def promo_redeem_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer("Отменено.")
        await show_profile_handler(query, query.from_user.id, context)
    elif update.message:
        await update.message.reply_text("❌ Ввод промокода отменён.", reply_markup=quick_nav_keyboard())
    return ConversationHandler.END

async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer("Отменено.")
        await show_admin_panel(query)
    else:
        await update.message.reply_text("Отменено.")
    return ConversationHandler.END

# ---------------------------------------------------------------------------
# КЛАНЫ — СОЗДАНИЕ И СПИСОК
# ---------------------------------------------------------------------------

CLAN_CREATE_LEVEL_REQ = 10
CLAN_CREATE_COST = 100_000

async def show_clans_hub(query_or_update, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_clan = get_user_clan(user_id)
    if user_clan:
        await show_clan_profile_handler(query_or_update, user_clan["id"], context)
        return

    db_user = get_or_create_user(user_id, "", "")
    lvl, _, _, _ = calculate_xp_level_info(db_user["xp"])

    text = (
        f"{ce('shield')} <b>Система Кланов New NFT</b>\n\n"
        f"• {ce('bolt')} Ваш уровень: <b>{lvl}</b> (требуется 10+)\n"
        f"• {ce('dollar')} Стоимость основания: <b>100,000 ⭐</b>\n\n"
        f"Клан даёт клановый тег, собственный герб, общую казну и мощный {ce('comet')} <b>бонус к шансу выигрыша подарков (+1%..+45%)</b>!\n\n"
        "Вы можете основать свой клан или вступить в существующий:"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("Основать клан", style="success", emoji_key="plus", callback_data="clan_create_start")],
        [make_btn("Просмотреть список кланов", style="primary", emoji_key="bookmark", callback_data="clan_list:1")],
        [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")],
    ])

    banner_io = None
    try:
        banner_io = await generate_clans_hub_banner()
    except Exception as e:
        log.warning("Не удалось сгенерировать баннер раздела Кланы: %s", e)

    if isinstance(query_or_update, CallbackQuery):
        msg = query_or_update.message
        if msg:
            try:
                await msg.delete()
            except Exception:
                pass
            if banner_io:
                await msg.reply_photo(
                    photo=InputFile(banner_io, filename="clans_hub.png"),
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                )
            else:
                await msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        target_msg = query_or_update.effective_message if hasattr(query_or_update, "effective_message") else query_or_update
        if target_msg:
            if banner_io:
                await target_msg.reply_photo(
                    photo=InputFile(banner_io, filename="clans_hub.png"),
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                )
            else:
                await target_msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_clans_list(query, page: int = 1) -> None:
    clans, total_pages = get_all_clans(page, page_size=5)
    text = f"📋 <b>Список кланов (Стр. {page}/{total_pages}):</b>\n\n"
    buttons = []

    for c in clans:
        total_treasury, _, members = get_clan_treasury_and_members(c["id"])
        lvl, _, _, _, bonus = calculate_clan_level_info(c["xp"])
        ctype = "Публичный" if c["type"] == "public" else ("За звёзды" if c["type"] == "stars" else "Закрытый")

        text += (
            f"🛡 <b>[{c['tag']}] {clean_html(c['name'])}</b>\n"
            f"• Ур. {lvl} (+{bonus}% бонус) | {len(members)}/{c['max_members']} чел.\n"
            f"• Общая казна: {total_treasury:,} ⭐ ({ctype})\n\n"
        )
        buttons.append([InlineKeyboardButton(f"[{c['tag']}] {c['name']} (Ур. {lvl})", callback_data=f"clan_info:{c['id']}")])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"clan_list:{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"clan_list:{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="nav_main")])
    kb = InlineKeyboardMarkup(buttons)

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def start_clan_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    if not await ensure_privacy_accepted_private(update, context):
        return ConversationHandler.END

    query = update.callback_query
    if query:
        user = query.from_user
        msg_obj = query.message
    else:
        user = update.effective_user
        msg_obj = update.message

    db_user = get_or_create_user(user.id, user.username or "", user.first_name or "")
    lvl, _, _, _ = calculate_xp_level_info(db_user["xp"])

    if lvl < CLAN_CREATE_LEVEL_REQ:
        text = f"❌ Для создания клана нужен {CLAN_CREATE_LEVEL_REQ} уровень!"
        if query: await query.answer(text, show_alert=True)
        else: await msg_obj.reply_text(text)
        return ConversationHandler.END

    if db_user["balance_stars"] < CLAN_CREATE_COST:
        text = f"❌ Создание клана стоит {CLAN_CREATE_COST:,} ⭐!"
        if query: await query.answer(text, show_alert=True)
        else: await msg_obj.reply_text(text)
        return ConversationHandler.END

    if query:
        await query.answer()

    msg_text = (
        "🏷 <b>Шаг 1 из 4: Клантег</b>\n\n"
        "Введите заглавный английский клантег (от 3 до 6 символов, только A-Z и 0-9).\n"
        "<i>Пример: TOP1, GODS, ALPHA</i>"
    )
    if query and query.message.photo:
        await query.message.delete()
        await query.message.reply_text(msg_text, parse_mode=ParseMode.HTML)
    elif query:
        await query.edit_message_text(msg_text, parse_mode=ParseMode.HTML)
    else:
        await msg_obj.reply_text(msg_text, parse_mode=ParseMode.HTML)
    return WAIT_CLAN_TAG

async def clan_tag_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tag = update.message.text.strip().upper()
    if not re.match(r"^[A-Z0-9]{3,6}$", tag):
        await update.message.reply_text("❌ Некорректный клантег! Введите 3-6 заглавных английских букв или цифр:")
        return WAIT_CLAN_TAG

    context.user_data["clan_tag"] = tag
    await update.message.reply_text(
        "📝 <b>Шаг 2 из 4: Название клана</b>\n\n"
        "Введите название вашего клана (от 2 до 15 символов):",
        parse_mode=ParseMode.HTML
    )
    return WAIT_CLAN_NAME

async def clan_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) > 15 or len(name) < 2:
        await update.message.reply_text("❌ Название должно содержать от 2 до 15 символов! Попробуйте снова:")
        return WAIT_CLAN_NAME

    context.user_data["clan_name"] = name
    await update.message.reply_text(
        "ℹ️ <b>Шаг 3 из 4: Описание клана</b>\n\n"
        "Напишите краткое описание вашего клана (или точку):",
        parse_mode=ParseMode.HTML
    )
    return WAIT_CLAN_DESC

async def clan_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["clan_desc"] = update.message.text.strip()

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Публичный (Свободный вход)", callback_data="ctype:public")],
        [InlineKeyboardButton("🔒 Закрытый (По заявкам)", callback_data="ctype:private")],
        [InlineKeyboardButton("⭐ Вход за звёзды", callback_data="ctype:stars")],
    ])
    await update.message.reply_text(
        "🔒 <b>Шаг 4 из 4: Тип клана</b>\n\nВыберите способ вступления в клан:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )
    return WAIT_CLAN_TYPE

async def clan_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ctype = query.data.split(":")[1]
    context.user_data["clan_type"] = ctype

    if ctype == "stars":
        await query.edit_message_text("💰 Укажите стоимость входа в клан в ⭐ (Stars):")
        return WAIT_CLAN_FEE
    else:
        return await finalize_clan_creation(query.from_user.id, context, query.message)

async def clan_fee_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() or int(text) < 1:
        await update.message.reply_text("❌ Введите корректное число звёзд:")
        return WAIT_CLAN_FEE

    context.user_data["clan_fee"] = int(text)
    return await finalize_clan_creation(update.effective_user.id, context, update.message)

async def finalize_clan_creation(user_id: int, context: ContextTypes.DEFAULT_TYPE, msg_obj):
    tag = context.user_data.get("clan_tag")
    name = context.user_data.get("clan_name")
    desc = context.user_data.get("clan_desc", "")
    ctype = context.user_data.get("clan_type", "public")
    fee = context.user_data.get("clan_fee", 0)

    if not deduct_user_stars(user_id, CLAN_CREATE_COST):
        await msg_obj.reply_text("❌ Недостаточно Stars на балансе!")
        return ConversationHandler.END

    clan_id = create_clan(user_id, tag, name, desc, ctype, fee)
    if clan_id:
        record_star_flow(spent=CLAN_CREATE_COST, burned=CLAN_CREATE_COST, purchased=CLAN_CREATE_COST)
        clan = get_clan_by_id(clan_id)
        clan_sys_id = clan["id_num"] if clan["id_num"] else clan["id"]
        text = (
            f"🎉 <b>Клан [{tag}] {clean_html(name)} успешно создан!</b>\n"
            f"Единый глобальный номер клана: <b>ID #{clan_sys_id}</b>\n\n"
            f"С вашего баланса списано {CLAN_CREATE_COST:,} ⭐."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛡 В профиль клана", callback_data=f"clan_info:{clan_id}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="nav_main")]
        ])
        if hasattr(msg_obj, "edit_text"):
            await msg_obj.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await msg_obj.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        add_user_stars(user_id, CLAN_CREATE_COST, track_issued=False)
        await msg_obj.reply_text("❌ Ошибка при создании клана. Возможно, клантег уже занят.")

    return ConversationHandler.END

async def cancel_clan_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Создание клана отменено.", reply_markup=back_to_main_keyboard())
    return ConversationHandler.END

# ---------------------------------------------------------------------------
# МАГАЗИН, НАСТРОЙКИ, КОЛЛЕКЦИЯ И ТОП-100
# ---------------------------------------------------------------------------

async def show_shop_page(query_or_msg, user_id: int) -> None:
    db_user = get_or_create_user(user_id, "", "")
    all_items = get_user_collection(user_id)
    upgradable = [
        it for it in all_items
        if canonical_gift_key(it["gift_key"]) in UPGRADABLE_GIFT_KEYS and not it["is_upgraded"] and not it["is_listed"]
    ]

    lines = [
        f"{ce('sparkles')} <b>Улучшения NFT (Pepe, Locket, Cap, Cup & Bonded Ring)</b>",
        "━━━━━━━━━━━━",
        f"{ce('dollar')} Ваш баланс: <b>{fmt_stars_rub(db_user['balance_stars'])}</b>",
        f"• {ce_pepe(0)} <b>Plush Pepe</b> — <b>{UPGRADE_COST_STARS:,} ⭐</b> (50 моделей)",
        f"• {ce('gem')} <b>Heart Locket</b> — <b>{HEART_LOCKET_UPGRADE_COST_STARS:,} ⭐</b> (61 модель)",
        f"• {ce('gold', '🏆')} <b>Algorithm Cup</b> — <b>{ALGORITHM_CUP_UPGRADE_COST_STARS:,} ⭐</b> (4 модели)",
        f"• {ce('crown')} <b>Durov's Cap</b> — <b>{DUROV_CAP_UPGRADE_COST_STARS:,} ⭐</b> (55 моделей)",
        f"• {ce('gem', '💍')} <b>Bonded Ring</b> — <b>{BONDED_RING_UPGRADE_COST_STARS:,} ⭐</b> (50 моделей)\n",
        "<blockquote expandable>"
        f"{ce('thought')} <b>Как работает улучшение NFT:</b>\n"
        f"• Выпадает случайная <b>уникальная модель</b> из коллекции выбранного подарка.\n"
        f"• Назначается <b>1 из 61 фонов</b> (мифический <b>Rainbow x100 • 0.05%</b>, чёрные, серые, золото).\n"
        f"• {ce('rainbow')} <b>MONOCHROME x6:</b> если цвет модели совпадает с цветом фона — ценность умножается в <b>6 раз</b>!\n"
        f"• {ce('bolt')} <b>Баффы:</b> подарки из кейса <b>{ce('gem')} Elite Buff Case (1,000,000 {ce('star')})</b> могут выпасть с 1–2 баффами на шанс редкого фона, редкой модели или стоимость!\n"
        f"• {ce('exchange')} Улучшенный NFT можно <b>продать на Маркете</b> или <b>передать бесплатно</b> (боту не продаётся)."
        "</blockquote>",
        "━━━━━━━━━━━━",
    ]

    buttons = []
    if not upgradable:
        lines.append(
            "<i>У вас пока нет обычных Plush Pepe, Heart Locket, Durov's Cap, Algorithm Cup или Bonded Ring для улучшения.</i>\n"
            "Выбейте их в группе по слову <code>NFT</code> или в <b>Mystery Cases</b>!"
        )
    else:
        lines.append(f"Доступно подарков для улучшения: <b>{len(upgradable)}</b> шт.\nВыберите подарок ниже:")
        for it in upgradable[:8]:
            it_key = canonical_gift_key(it["gift_key"])
            g_title = get_upgraded_gift_title(it_key)
            u_cost = get_upgrade_cost(it_key)
            buff_mark = "⚡ " if has_item_buffs(it) else ""
            if it_key == "pepe_heart":
                btn_eid = CUSTOM_PEPE_EMOJI_IDS[0]
            elif it_key == "cap_tg":
                btn_eid = CE_IDS["crown"]
            elif it_key == "trophy_cup":
                btn_eid = CE_IDS["gold"]
            else:
                btn_eid = CE_IDS["gem"]
            buttons.append([
                make_btn(
                    f"{buff_mark}Улучшить {g_title} (#ID {it['id']}) — {u_cost:,}⭐",
                    style="primary",
                    emoji_id=btn_eid,
                    callback_data=f"upgrade_item:{it['id']}"
                )
            ])

    buttons.append([make_btn(f"Слоты инвентаря ({db_user['max_inventory']} мест)", emoji_key="bag", callback_data="shop_slots_menu")])
    buttons.append([
        make_btn("В коллекцию", emoji_key="bookmark", callback_data="nav_collection_page:1"),
        make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")
    ])

    text = "\n".join(lines)
    kb = InlineKeyboardMarkup(buttons)

    if isinstance(query_or_msg, CallbackQuery):
        await safe_edit_or_reply(query_or_msg, text, reply_markup=kb)
    else:
        target_msg = query_or_msg.effective_message if hasattr(query_or_msg, "effective_message") else query_or_msg
        if target_msg:
            await target_msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_shop_slots_menu(query, user_id: int) -> None:
    db_user = get_or_create_user(user_id, "", "")
    text = (
        f"{ce('bag')} <b>Расширение слотов коллекции</b>\n\n"
        f"{ce('bookmark')} Текущие слоты коллекции: <b>{db_user['max_inventory']}</b>\n"
        f"{ce('dollar')} Ваш баланс: <b>{fmt_stars_rub(db_user['balance_stars'])}</b>\n\n"
        "Доступные расширения слотов:\n"
        "• <b>+10 Слотов</b> — <b>300 ⭐</b>\n"
        "• <b>+25 Слотов</b> — <b>650 ⭐</b>\n"
        "• <b>+50 Слотов</b> — <b>1,200 ⭐</b>"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("+10 Слотов (300⭐)", emoji_key="plus", callback_data="buy_slots:10:300")],
        [make_btn("+25 Слотов (650⭐)", emoji_key="plus", callback_data="buy_slots:25:650")],
        [make_btn("+50 Слотов (1200⭐)", emoji_key="plus", callback_data="buy_slots:50:1200")],
        [InlineKeyboardButton("◀️ Назад к улучшениям", callback_data="nav_shop")],
        [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")],
    ])
    await safe_edit_or_reply(query, text, reply_markup=kb)

async def show_gift_upgrade_confirm(query, user_id: int, item_id: int) -> None:
    item = get_collection_item(item_id)
    if not item or item["user_id"] != user_id:
        await query.answer("❌ Подарок не найден.", show_alert=True)
        return
    gift_key = canonical_gift_key(item["gift_key"])
    if gift_key not in UPGRADABLE_GIFT_KEYS:
        await query.answer("❌ Улучшение доступно для Plush Pepe, Heart Locket, Durov's Cap, Algorithm Cup и Bonded Ring!", show_alert=True)
        return
    if item["is_upgraded"]:
        await query.answer("⚠️ Этот подарок уже улучшен!", show_alert=True)
        return
    if item["is_listed"]:
        await query.answer("⚠️ Сначала снимите подарок с маркета!", show_alert=True)
        return

    g_title = get_upgraded_gift_title(gift_key)
    u_cost = get_upgrade_cost(gift_key)
    models_cnt = len(get_models_for_gift(gift_key))
    db_user = get_or_create_user(user_id, "", "")
    buff_lines = format_buffs_lines(item)
    buffs_note = (
        f"\n{ce('bolt')} <b>Активные баффы подарка (сработают при улучшении):</b>\n"
        + "\n".join(f"• {ce('sparkles')} {ln}" for ln in buff_lines)
        + "\n"
        if buff_lines else ""
    )
    g_ce = upgraded_gift_tg_emoji(gift_key)
    text = (
        f"{ce('sparkles')} <b>Подтверждение улучшения {g_ce} {g_title} (#ID {item_id})</b>\n"
        f"━━━━━━━━━━━━\n"
        f"• {ce('dollar')} Ваш баланс: <b>{fmt_stars_rub(db_user['balance_stars'])}</b>\n"
        f"• {ce('star')} Стоимость улучшения: <b>{u_cost:,} {ce('star')}</b>\n"
        f"{buffs_note}\n"
        f"{ce('hourglass')} После нажатия начнётся 5-секундная распаковка: сначала откроется случайная модель из {models_cnt} вариантов, затем — один из 61 фонов (включая мифический Rainbow x100 и комбо MONOCHROME x6)!\n"
        f"━━━━━━━━━━━━"
    )
    kb = InlineKeyboardMarkup([
        [make_btn(f"Улучшить за {u_cost:,} ⭐", style="success", emoji_key="sparkles", callback_data=f"upgrade_confirm:{item_id}")],
        [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="nav_shop")],
    ])
    await safe_edit_or_reply(query, text, reply_markup=kb)

async def execute_gift_upgrade(query, user_id: int, item_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    item = get_collection_item(item_id)
    if not item or item["user_id"] != user_id:
        await query.answer("❌ Подарок не найден.", show_alert=True)
        return
    gift_key = canonical_gift_key(item["gift_key"])
    if gift_key not in UPGRADABLE_GIFT_KEYS or item["is_upgraded"] or item["is_listed"]:
        await query.answer("❌ Невозможно улучшить этот предмет.", show_alert=True)
        return

    u_cost = get_upgrade_cost(gift_key)
    g_title = get_upgraded_gift_title(gift_key)
    g_ce = upgraded_gift_tg_emoji(gift_key)
    models_cnt = len(get_models_for_gift(gift_key))

    db_user = get_or_create_user(user_id, "", "")
    if db_user["balance_stars"] < u_cost:
        await query.answer(f"❌ Недостаточно Stars! Нужно {u_cost:,} ⭐.", show_alert=True)
        return

    b_bg, b_mdl, b_val = get_item_buffs(item)
    chosen_model = roll_model_for_gift(gift_key, buff_pct=b_mdl)
    chosen_backdrop = roll_backdrop(buff_pct=b_bg)
    g = GIFTS_BY_KEY[gift_key]
    est_stars = calculate_upgraded_stars(
        g.stars,
        chosen_model,
        chosen_backdrop,
        gift_key=gift_key,
        value_buff_pct=b_val,
    )
    is_mono, mono_fam = get_monochrome_combo_info(chosen_model.name, chosen_backdrop.key)
    buff_badge_txt = format_buffs_compact(item)
    buff_lines = format_buffs_lines(item)

    ok, msg_res, upgrade_num = upgrade_collection_item(
        user_id=user_id,
        item_id=item_id,
        model_name=chosen_model.name,
        backdrop_key=chosen_backdrop.key,
        upgraded_stars=est_stars,
        cost=u_cost,
    )
    if not ok:
        await query.answer(f"❌ {msg_res}", show_alert=True)
        return

    await query.answer("✨ Запускаем улучшение!")
    step1_text = (
        f"{ce('sparkles')} <b>Улучшение {g_ce} {g_title}...</b>\n\n"
        f"{ce('hourglass')} Шаг 1/2: Генерируем модель из {models_cnt} вариантов..."
    )
    if query.message.photo:
        try: await query.message.delete()
        except Exception: pass
        anim_msg = await query.message.reply_text(step1_text, parse_mode=ParseMode.HTML)
    else:
        anim_msg = await query.edit_message_text(step1_text, parse_mode=ParseMode.HTML)

    await asyncio.sleep(1.5)
    try:
        await anim_msg.edit_text(
            f"{ce('sparkles')} <b>Улучшение {g_title}...</b>\n\n"
            f"{g_ce} Открыта модель: <b>{clean_html(chosen_model.name)}</b> (шанс {chosen_model.chance_pct}%)!\n"
            f"{ce('bulb')} Шаг 2/2: Подбираем редкий фон из 61 палитры...",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await asyncio.sleep(1.5)
    try:
        await anim_msg.edit_text(
            f"{ce('sparkles')} <b>Улучшение {g_title}...</b>\n\n"
            f"{g_ce} Модель: <b>{clean_html(chosen_model.name)}</b> ({chosen_model.chance_pct}%)\n"
            f"{ce('gem')} Проявляем фон: <b>{clean_html(chosen_backdrop.name)}</b> ({chosen_backdrop.rarity_label})...",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await asyncio.sleep(2.0)

    card_io = await generate_upgraded_gift_image(
        chosen_model, chosen_backdrop, upgrade_num, est_stars, gift_key=gift_key, buff_badge=buff_badge_txt
    )
    try:
        await anim_msg.delete()
    except Exception:
        pass

    mono_line = f"\n{ce('rainbow')} <b>МОНОХРОМНОЕ КОМБО x6!</b> ({COLOR_FAMILY_RU.get(mono_fam, mono_fam)})" if is_mono else ""
    buffs_applied_block = (
        f"\n{ce('bolt')} <b>Применённые баффы:</b>\n" + "\n".join(f"• {ce('sparkles')} {ln}" for ln in buff_lines)
        if buff_lines else ""
    )
    g_ce = upgraded_gift_tg_emoji(gift_key)
    cap = (
        f"{ce('boom')} <b>Улучшение завершено! {g_title} #{upgrade_num}</b>\n"
        f"━━━━━━━━━━━━\n"
        f"{g_ce} Модель: <b>{clean_html(chosen_model.name)}</b> (шанс {chosen_model.chance_pct}%)\n"
        f"{ce('sparkles')} Фон: <b>{clean_html(chosen_backdrop.name)}</b> • <i>{chosen_backdrop.rarity_label}</i> ({chosen_backdrop.chance_pct}%){mono_line}{buffs_applied_block}\n"
        f"{ce('gem')} Оценочная ценность: <b>{fmt_stars_rub(est_stars)}</b>\n"
        f"{ce('bolt')} Бонус опыта: <b>+5,000 XP</b>\n"
        f"━━━━━━━━━━━━\n"
        f"<blockquote expandable>"
        f"{ce('thought')} <b>Что можно сделать с улучшенным NFT:</b>\n"
        f"• Выставить на <b>NFT Маркет</b> по своей цене (комиссия площадки 15%).\n"
        f"• Бесплатно передать другому игроку в коллекции или командой <code>Передать</code>.\n"
        f"• Закрепить на витрине <b>Избранного</b> в профиле (улучшенные NFT нельзя продать боту)."
        f"</blockquote>"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("Выставить на маркет", style="primary", emoji_key="exchange", callback_data=f"market_sell_start:{item_id}")],
        [make_btn("Передать бесплатно", emoji_id=CUSTOM_GIFT_EMOJI_IDS[2], callback_data=f"gift_transfer_start:{item_id}")],
        [make_btn("В избранное", emoji_key="star", callback_data=f"toggle_fav:{item_id}:1")],
        [
            make_btn("В коллекцию", emoji_key="bookmark", callback_data="nav_collection_page:1"),
            make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main"),
        ],
    ])
    await context.bot.send_photo(
        chat_id=user_id,
        photo=InputFile(card_io, filename=f"upgraded_{gift_key}_{upgrade_num}.png"),
        caption=cap,
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )

async def show_settings_page(query, user_id: int) -> None:
    db_user = get_or_create_user(user_id, "", "")
    hide_top = f"{ce('check')} Да" if db_user["hide_top"] else f"{ce('cross')} Нет"
    hide_coll = f"{ce('check')} Да" if db_user["hide_collection"] else f"{ce('cross')} Нет"
    auto_sell = f"{ce('green_dot')} Включена" if db_user["auto_sell"] else f"{ce('red_dot')} Выключена"
    has_bg_flag = has_user_background(db_user)
    has_bg = f"{ce('check')} Установлен" if has_bg_flag else f"{ce('cross')} Стандартный"

    text = (
        f"{ce('gear')} <b>Настройки аккаунта и профиля</b>\n"
        "━━━━━━━━━━━━\n"
        f"• {ce('top')} Скрывать из ТОП-100: <b>{hide_top}</b>\n"
        f"• {ce('lock')} Скрывать коллекцию: <b>{hide_coll}</b>\n"
        f"• {ce('money_wings')} Авто-продажа кейсов: <b>{auto_sell}</b>\n"
        f"• {ce('pencil')} Кастомный фон профиля: <b>{has_bg}</b>"
    )

    bg_cost = BG_CHANGE_COST if has_bg_flag else BG_SET_COST
    bg_btn_label = f"Сменить фон профиля ({bg_cost:,}⭐)" if has_bg_flag else f"Поставить фон профиля ({bg_cost:,}⭐)"
    ht_lbl = "Да" if db_user["hide_top"] else "Нет"
    hc_lbl = "Да" if db_user["hide_collection"] else "Нет"
    as_lbl = "Вкл" if db_user["auto_sell"] else "Выкл"
    buttons = [
        [make_btn(f"Скрытие из ТОПа: {ht_lbl}", emoji_key="green_dot" if db_user["hide_top"] else "red_dot", callback_data="toggle_set:hide_top")],
        [make_btn(f"Скрытие коллекции: {hc_lbl}", emoji_key="green_dot" if db_user["hide_collection"] else "red_dot", callback_data="toggle_set:hide_collection")],
        [make_btn(f"Авто-продажа: {as_lbl}", emoji_key="green_dot" if db_user["auto_sell"] else "red_dot", callback_data="toggle_set:auto_sell")],
        [make_btn(bg_btn_label, emoji_key="pencil", callback_data="bg_change_start")],
    ]
    if has_bg_flag:
        buttons.append([make_btn("Сбросить фон на стандартный", style="danger", emoji_key="trash", callback_data="bg_reset")])
    buttons.append([
        make_btn("Назад в профиль", emoji_key="smile", callback_data="nav_profile"),
        make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main"),
    ])
    kb = InlineKeyboardMarkup(buttons)
    await safe_edit_or_reply(query, text, reply_markup=kb)

async def show_collection_page(query, user_id: int, page: int = 1) -> None:
    items = get_user_collection(user_id)
    db_user = get_or_create_user(user_id, "", "")
    max_inv = db_user["max_inventory"]

    if not items:
        kb = InlineKeyboardMarkup([
            [make_btn("Открыть кейсы", style="primary", emoji_key="game", callback_data="nav_cases_hub")],
            [
                make_btn("Профиль", emoji_key="smile", callback_data="nav_profile"),
                make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main"),
            ],
        ])
        msg_text = f"{ce('bookmark')} <b>Твоя коллекция пока пуста (0/{max_inv}).</b>\nВыбивай подарки по слову <code>NFT</code> в группах или открывай кейсы!"
        await safe_edit_or_reply(query, msg_text, reply_markup=kb)
        return

    items_per_page = 10
    total_pages = max(1, math.ceil(len(items) / items_per_page))
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * items_per_page
    page_items = items[start_idx : start_idx + items_per_page]

    buttons = []
    for item in page_items:
        g = GIFTS_BY_KEY.get(item["gift_key"])
        if not g: continue
        fav_star = "⭐ " if item["is_favorite"] else ""
        buff_mark = "⚡ " if has_item_buffs(item) else ""
        val_stars = get_item_display_value(item)
        if item["is_upgraded"]:
            listed_mark = " 🛒" if item["is_listed"] else ""
            btn_text = f"{fav_star}{buff_mark}#{item['upgrade_num']} {item['model_name']}{listed_mark} ({fmt_stars_compact(val_stars)}⭐)"
            if item["gift_key"] == "pepe_heart":
                item_eid = CUSTOM_PEPE_EMOJI_IDS[0]
            elif item["gift_key"] == "cap_tg":
                item_eid = CE_IDS["crown"]
            elif item["gift_key"] == "trophy_cup":
                item_eid = CE_IDS["gold"]
            else:
                item_eid = CE_IDS["gem"]
            buttons.append([make_btn(btn_text[:60], emoji_id=item_eid, callback_data=f"view_item:{item['id']}:{page}")])
        elif item["gift_key"] == "scared_cat":
            listed_mark = " 🛒" if item["is_listed"] else ""
            ed_num = int(item["edition_num"] or item["id"])
            btn_text = f"{fav_star}{buff_mark}#{ed_num} Scared Cat{listed_mark} ({fmt_stars_compact(val_stars)}⭐)"
            buttons.append([make_btn(btn_text[:60], emoji_key="fire", callback_data=f"view_item:{item['id']}:{page}")])
        else:
            btn_text = f"{fav_star}{buff_mark}{g.name} ({fmt_stars_compact(val_stars)}⭐)"
            buttons.append([InlineKeyboardButton(btn_text[:60], callback_data=f"view_item:{item['id']}:{page}")])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"nav_collection_page:{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"nav_collection_page:{page+1}"))
    buttons.append(nav_row)

    buttons.append([make_btn("Продать всё (кроме избр., уник. и улучш.)", style="danger", emoji_key="trash", callback_data="sell_all_confirm")])
    buttons.append([
        make_btn("Профиль", emoji_key="smile", callback_data="nav_profile"),
        make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")
    ])

    kb = InlineKeyboardMarkup(buttons)
    text = f"{ce('bookmark')} <b>Твоя NFT-Коллекция ({len(items)}/{max_inv}):</b>"
    await safe_edit_or_reply(query, text, reply_markup=kb)

async def show_top_page(query, page: int = 1) -> None:
    page_size = 10
    rows, total_pages = get_top_users_page(page, page_size)

    lines = [f"{ce('top')} <b>Глобальный ТОП-100 Игроков (Стр. {page}/{total_pages})</b>\n━━━━━━━━━━━━"]
    buttons = []

    start_rank = (page - 1) * page_size + 1
    for idx, u in enumerate(rows, start=start_rank):
        medal_ce = ce("gold") if idx == 1 else ce("silver") if idx == 2 else ce("bronze") if idx == 3 else f"<b>#{idx}</b>"
        medal_btn = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"#{idx}"
        clan = get_user_clan(u['user_id'])
        tag_str = f"[{clan['tag']}] " if clan else ""
        name = normalize_telegram_name(u['first_name'], u['username'], u['user_id'])
        lvl, _, _, _ = calculate_xp_level_info(u['xp'])
        stars_disp = fmt_stars_compact(u['balance_stars'])
        lines.append(f"{medal_ce} <b>{tag_str}{clean_html(name)}</b> — <b>{stars_disp} ⭐</b> (Ур. {lvl})")

        btn_text = f"{medal_btn} {tag_str}{name[:12]} ({stars_disp}⭐)"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"view_top_user:{u['user_id']}:{page}")])

    lines.append("━━━━━━━━━━━━\n<i>Нажмите на игрока выше, чтобы открыть его профиль!</i>")

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"nav_top_page:{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"nav_top_page:{page+1}"))

    buttons.append(nav_row)
    buttons.append([
        make_btn("Мой профиль", emoji_key="smile", callback_data="nav_profile"),
        make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")
    ])

    kb = InlineKeyboardMarkup(buttons)
    full_text = "\n".join(lines)

    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(full_text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(full_text, parse_mode=ParseMode.HTML, reply_markup=kb)

# ---------------------------------------------------------------------------
# ЧАТ-КОМАНДА "ПЕРЕДАТЬ" (ЗВЁЗДЫ И ПОДАРКИ НА РУССКОМ И АНГЛИЙСКОМ)
# ---------------------------------------------------------------------------

TRANSFER_KEYWORDS = ("передать", "transfer", "send", "give")
GIFT_WORDS = {"подарок", "подарка", "gift", "nft", "нфт"}

def _extract_reply_or_target(msg, tokens: list[str]) -> Tuple[Optional[sqlite3.Row], list[str]]:
    """
    Определяет получателя либо через reply_to_message, либо через @username / ID / text_mention в токенах.
    Возвращает (target_db_row, оставшиеся_токены).
    """
    # 1. Проверяем текстовое упоминание (text_mention) без username
    if msg.entities:
        for ent in msg.entities:
            if ent.type == "text_mention" and ent.user and not ent.user.is_bot:
                row = get_or_create_user(ent.user.id, ent.user.username or "", ent.user.first_name or "")
                mention_txt = msg.text[ent.offset : ent.offset + ent.length].lower()
                rem = [t for t in tokens if t.lower() not in mention_txt.split()]
                return row, rem

    # 2. Проверяем токены на @username или числовой ID (если есть reply — сначала проверим явный @username, иначе reply)
    remaining = []
    explicit_target = None
    for tok in tokens:
        if tok.startswith("@") and len(tok) > 1 and explicit_target is None:
            found = get_user_by_target(tok)
            if found:
                explicit_target = found
                continue
        remaining.append(tok)

    if explicit_target:
        return explicit_target, remaining

    # 3. Проверяем ответ на сообщение (swipe / reply)
    if msg.reply_to_message and msg.reply_to_message.from_user:
        ruser = msg.reply_to_message.from_user
        if ruser.is_bot:
            return None, tokens
        row = get_or_create_user(ruser.id, ruser.username or "", ruser.first_name or "")
        return row, tokens

    # 4. Если нет reply, ищем числовой ID среди токенов (например, `Передать 1000 684535319` или `Передать подарок 684535319`)
    for idx in range(len(remaining) - 1, -1, -1):
        tok = remaining[idx]
        if tok.isdigit():
            found = get_user_by_target(tok)
            if found:
                new_rem = remaining[:idx] + remaining[idx + 1:]
                return found, new_rem

    return None, tokens

async def show_chat_gift_picker(
    msg,
    sender_id: int,
    target_row: Optional[sqlite3.Row],
    page: int = 1,
    edit_query=None,
):
    items = [it for it in get_user_collection(sender_id) if not it["is_listed"]]
    target_id = int(target_row["user_id"]) if target_row is not None else 0

    if not items:
        text = "❌ У вас нет доступных подарков в коллекции для передачи."
        if edit_query:
            await edit_query.edit_message_text(text)
        else:
            await msg.reply_text(text)
        return

    page_size = 8
    total_pages = max(1, math.ceil(len(items) / page_size))
    page = max(1, min(page, total_pages))
    page_items = items[(page - 1) * page_size : page * page_size]

    if target_row is not None:
        target_name = normalize_telegram_name(target_row["first_name"], target_row["username"], target_row["user_id"])
        text = (
            f"🎁 <b>Передача подарка игроку {clean_html(target_name)}</b> (Стр. {page}/{total_pages})\n"
            f"Выберите подарок из вашей коллекции:"
        )
    else:
        text = (
            f"🎁 <b>Передача подарка</b> (Стр. {page}/{total_pages})\n"
            f"Выберите подарок из вашей коллекции (затем укажете <code>@username</code> или ID получателя):"
        )

    buttons = []
    for item in page_items:
        g = GIFTS_BY_KEY.get(item["gift_key"])
        if not g:
            continue
        val_stars = get_item_display_value(item)
        g_emoji = get_upgraded_gift_emoji(item["gift_key"])
        lbl = f"{g_emoji} #{item['upgrade_num']} {item['model_name']}" if item["is_upgraded"] else g.name[:24]
        cb_data = (
            f"chat_gx_do:{sender_id}:{target_id}:{item['id']}"
            if target_id > 0
            else f"chat_gx_pick:{sender_id}:{item['id']}"
        )
        buttons.append([
            InlineKeyboardButton(
                f"🎁 {lbl} ({fmt_stars_compact(val_stars)}⭐)",
                callback_data=cb_data,
            )
        ])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"chat_gx_pg:{sender_id}:{target_id}:{page-1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"chat_gx_pg:{sender_id}:{target_id}:{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([make_btn("❌ Отмена", style="danger", callback_data=f"chat_gx_cancel:{sender_id}")])
    kb = InlineKeyboardMarkup(buttons)

    if edit_query:
        await edit_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def handle_chat_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Обрабатывает чат-команды вида:
      - Передать (сразу открывает окно выбора подарка из коллекции!)
      - Передать @username / Передать (ответом на сообщение) -> выбор подарка для этого игрока
      - Передать подарок [<название>] [@username / ID]
      - Передать 1000 (в ответ на сообщение) / Передать 1000 @username
    Возвращает True, если сообщение было распознано как команда передачи.
    """
    msg = update.effective_message
    if not msg or not msg.text:
        return False

    raw = msg.text.strip()
    parts = raw.split()
    if not parts:
        return False

    first_word = parts[0].lower()
    if first_word not in TRANSFER_KEYWORDS:
        return False

    if not await check_access_allowed(update):
        return True

    sender = update.effective_user
    sender_db = get_or_create_user(sender.id, sender.username or "", sender.first_name or "")
    sender_lvl, _, _, _ = calculate_xp_level_info(sender_db["xp"])

    rest_tokens = parts[1:]
    star_noise = {"звёзд", "звезд", "звезды", "звёзды", "stars", "star", "⭐"}
    has_gift_word = any(t.lower() in GIFT_WORDS for t in rest_tokens)

    # Определяем, передаются ли звёзды (есть числовая сумма, не являющаяся @username/ID получателя при gift-слове)
    has_amount_number = False
    if not has_gift_word:
        for tok in rest_tokens:
            if tok.startswith("@") or tok.lower() in star_noise:
                continue
            clean_num = tok.replace(",", "").replace(".", "")
            if clean_num.isdigit():
                # Если число ровно одно и больше похоже на ID пользователя в базе?
                # Проверяем: при >= 1000 без gift_word при reply или с ещё одним токеном — это перевод звёзд.
                # Если нет reply и это одиночный ID пользователя (len >= 6), проверим в базе; иначе считаем суммой звёзд.
                if len(rest_tokens) == 1 and not msg.reply_to_message and len(clean_num) >= 7 and get_user_by_target(clean_num):
                    has_amount_number = False
                else:
                    has_amount_number = True
                break

    is_gift_mode = has_gift_word or not has_amount_number

    if is_gift_mode:
        clean_tokens = [t for t in rest_tokens if t.lower() not in GIFT_WORDS]
        target_row, leftover = _extract_reply_or_target(msg, clean_tokens)

        if sender_lvl < TRANSFER_MIN_LEVEL:
            has_upgraded = any(it["is_upgraded"] and not it["is_listed"] for it in get_user_collection(sender.id))
            if not has_upgraded:
                await msg.reply_text(
                    f"❌ Передавать обычные подарки можно только с <b>{TRANSFER_MIN_LEVEL}-го уровня</b>!\n"
                    f"Ваш текущий уровень: <b>{sender_lvl}</b>. (Улучшенные NFT передаются на любом уровне)",
                    parse_mode=ParseMode.HTML,
                )
                return True

        if target_row and target_row["user_id"] == sender.id:
            await msg.reply_text("❌ Нельзя передать подарок самому себе.")
            return True

        if target_row and leftover:
            query_str = " ".join(leftover).strip().lower()
            items = get_user_collection(sender.id)
            matched_item = None
            for it in items:
                if query_str.isdigit() and it["id"] == int(query_str):
                    matched_item = it
                    break
                g = GIFTS_BY_KEY.get(it["gift_key"])
                if g and (query_str in g.name.lower() or query_str == g.key.lower()):
                    matched_item = it
                    break

            if matched_item:
                ok, res = transfer_gift_between_users(sender.id, target_row["user_id"], matched_item["id"])
                if not ok:
                    await msg.reply_text(f"❌ {res}")
                    return True
                g = GIFTS_BY_KEY.get(res)
                g_name = (
                    f"{get_upgraded_gift_title(matched_item['gift_key'])} #{matched_item['upgrade_num']} ({matched_item['model_name']})"
                    if matched_item["is_upgraded"]
                    else (g.name if g else res)
                )
                receiver_name = normalize_telegram_name(target_row["first_name"], target_row["username"], target_row["user_id"])
                await msg.reply_text(
                    f"🎁 <b>Подарок передан!</b>\n"
                    f"Игрок <b>{clean_html(sender.first_name)}</b> передал <b>{clean_html(g_name)}</b> "
                    f"игроку <b>{clean_html(receiver_name)}</b>!",
                    parse_mode=ParseMode.HTML,
                )
                try:
                    await context.bot.send_message(
                        chat_id=target_row["user_id"],
                        text=f"🎁 <b>Вам передали подарок!</b>\nОт: <b>{clean_html(sender.first_name)}</b>\nПодарок: <b>{clean_html(g_name)}</b>",
                        parse_mode=ParseMode.HTML,
                        reply_markup=quick_nav_keyboard(),
                    )
                except Exception:
                    pass
                return True

        await show_chat_gift_picker(msg, sender.id, target_row, page=1)
        return True

    # Режим передачи звёзд
    if sender_lvl < TRANSFER_MIN_LEVEL:
        await msg.reply_text(
            f"❌ Передавать звёзды можно только с <b>{TRANSFER_MIN_LEVEL}-го уровня</b>!\n"
            f"Ваш текущий уровень: <b>{sender_lvl}</b>.",
            parse_mode=ParseMode.HTML,
        )
        return True

    clean_tokens = [t for t in rest_tokens if t.lower() not in star_noise]
    amount = None
    tokens_without_amount = []
    for tok in clean_tokens:
        clean_num = tok.replace(",", "").replace(".", "")
        if amount is None and clean_num.isdigit():
            amount = int(clean_num)
            continue
        tokens_without_amount.append(tok)

    if amount is None:
        await show_chat_gift_picker(msg, sender.id, None, page=1)
        return True

    target_row, _ = _extract_reply_or_target(msg, tokens_without_amount)
    if not target_row:
        await msg.reply_text(
            "❌ Получатель не найден!\n"
            "Ответьте (свайпните) на сообщение пользователя и напишите <code>Передать 1000</code>, "
            "либо укажите <code>Передать 1000 @username</code> или <code>ID</code>.",
            parse_mode=ParseMode.HTML,
        )
        return True

    if target_row["user_id"] == sender.id:
        await msg.reply_text("❌ Нельзя переводить звёзды самому себе.")
        return True

    if amount < TRANSFER_MIN_STARS:
        await msg.reply_text(
            f"❌ Минимальная сумма перевода — <b>{TRANSFER_MIN_STARS:,} ⭐</b>!",
            parse_mode=ParseMode.HTML,
        )
        return True

    if not deduct_user_stars(sender.id, amount):
        await msg.reply_text(
            f"❌ Недостаточно Stars на балансе! Ваш баланс: <b>{sender_db['balance_stars']:,} ⭐</b>.",
            parse_mode=ParseMode.HTML,
        )
        return True

    add_user_stars(target_row["user_id"], amount, track_issued=False)
    record_star_flow(spent=amount)
    receiver_name = normalize_telegram_name(target_row["first_name"], target_row["username"], target_row["user_id"])

    await msg.reply_text(
        f"💸 <b>Перевод выполнен!</b>\n"
        f"<b>{clean_html(sender.first_name)}</b> передал <b>{amount:,} ⭐</b> игроку <b>{clean_html(receiver_name)}</b>!",
        parse_mode=ParseMode.HTML,
    )

    try:
        await context.bot.send_message(
            chat_id=target_row["user_id"],
            text=(
                f"💸 <b>Вам поступил перевод!</b>\n\n"
                f"От игрока: <b>{clean_html(sender.first_name)}</b>\n"
                f"Сумма: <b>+{amount:,} ⭐</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard()
        )
    except Exception:
        pass

    return True

# ---------------------------------------------------------------------------
# МИНИ-ОБУЧЕНИЕ ДЛЯ НОВЫХ ПОЛЬЗОВАТЕЛЕЙ (ONBOARDING)
# ---------------------------------------------------------------------------

async def send_onboarding_step1(bot, chat_id: int, user_first_name: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["onboarding_step"] = 1
    text = (
        f"{ce('smile')} <b>Добро пожаловать, {clean_html(user_first_name)}!</b>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('bulb')} <b>Быстрый старт (Шаг 1/3): Первый NFT-подарок</b>\n\n"
        f"В группах и здесь игроки выбивают редкие подарки {ce_gift(0)} словом <code>NFT</code>.\n"
        "Попробуйте прямо сейчас: напишите в чат слово <b><code>NFT</code></b> "
        "(или нажмите кнопку ниже), чтобы выбить свой первый подарок без ожидания!"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("Выбить первый NFT", style="success", emoji_id=CUSTOM_GIFT_EMOJI_IDS[0], callback_data="onb_drop")],
        [make_btn("Пропустить обучение", emoji_key="arrow_right", callback_data="onb_finish")],
    ])
    await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def send_onboarding_drop_reward(
    bot,
    chat_id: int,
    user,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    row = get_or_create_user(user.id, user.username or "", user.first_name or "")
    clan = get_user_clan(user.id)
    clan_bonus_pct = 0.0
    if clan:
        _, _, _, _, clan_bonus_pct = calculate_clan_level_info(clan["xp"])

    gift = roll_gift_from_pool(GIFTS, bonus_pct=clan_bonus_pct)
    drop_id = create_pending_drop(user.id, chat_id, gift.key)
    context.user_data["onboarding_step"] = 2

    kb = InlineKeyboardMarkup([
        [make_btn("Сохранить и открыть профиль", style="success", emoji_key="check", callback_data=f"onb_keep_drop:{drop_id}")],
        [make_btn("Продать и открыть профиль", emoji_key="money_wings", callback_data=f"onb_sell_drop:{drop_id}")],
    ])
    g_ce = gift_tg_emoji(gift.key)
    caption = (
        f"{ce('boom')} <b>Отлично, {clean_html(user.first_name)}!</b> Вы выбили свой первый подарок:\n\n"
        f"{g_ce} <b>{gift.name}</b>\n"
        f"• Модель: <b>{gift.model_name}</b>\n"
        f"• Опыт: <b>+{gift.xp} XP</b>\n"
        f"• Ценность: {fmt_stars_rub(gift.stars)} / {fmt_ton(gift.ton)}\n\n"
        f"Нажмите кнопку ниже, чтобы забрать подарок и перейти к <b>Шагу 2/3 — вашему профилю</b>:"
    )
    try:
        card_io = await generate_gift_card_image(gift)
        if card_io:
            await bot.send_photo(chat_id=chat_id, photo=InputFile(card_io, filename=f"gift_{gift.key}.png"), caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
            return
    except Exception:
        pass
    await bot.send_message(chat_id=chat_id, text=caption, parse_mode=ParseMode.HTML, reply_markup=kb)

async def send_onboarding_step2_profile(
    query,
    user,
    context: ContextTypes.DEFAULT_TYPE,
    action_note: str,
) -> None:
    context.user_data["onboarding_step"] = 2
    await show_profile_handler(query, user.id, context)
    guide_text = (
        f"{action_note}\n\n"
        f"{ce('bulb')} <b>Шаг 2/3: Ваш профиль</b>\n"
        "━━━━━━━━━━━━\n"
        "На карточке профиля выше отображаются:\n"
        f"• {ce('bolt')} Ваш <b>уровень, XP и место в глобальном ТОП-100</b>\n"
        f"• {ce('dollar')} Текущий баланс <b>Stars</b> и клановый тег\n"
        f"• {ce('star')} До <b>7 Избранных NFT</b> на витрине + кастомный фон профиля\n\n"
        "Нажмите кнопку ниже для финального обзора разделов:"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("Дальше: обзор разделов (3/3)", style="primary", emoji_key="arrow_right", callback_data="onb_step3")],
        [make_btn("В Главное меню", emoji_key="desktop", callback_data="onb_finish")],
    ])
    await context.bot.send_message(chat_id=user.id, text=guide_text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def send_onboarding_step3_overview(bot, chat_id: int) -> None:
    text = (
        f"{ce('bulb')} <b>Шаг 3/3: Краткий гид по разделам</b>\n"
        "━━━━━━━━━━━━\n"
        f"Вы прошли старт! Всё самое важное собрано в аннотации ниже:\n\n"
        "<blockquote expandable>"
        f"• {ce('bookmark')} <b>Коллекция</b> — храните NFT, добавляйте в Избранное или продавайте\n"
        f"• {ce('sparkles')} <b>Улучшения</b> — улучшайте <b>Plush Pepe</b> {ce_pepe(0)} ({UPGRADE_COST_STARS:,} ⭐), <b>Heart Locket</b> ({HEART_LOCKET_UPGRADE_COST_STARS:,} ⭐), <b>Algorithm Cup</b> ({ALGORITHM_CUP_UPGRADE_COST_STARS:,} ⭐), <b>Durov's Cap</b> ({DUROV_CAP_UPGRADE_COST_STARS:,} ⭐) и <b>Bonded Ring</b> ({BONDED_RING_UPGRADE_COST_STARS:,} ⭐) с редкими моделями и баффами\n"
        f"• {ce('fire')} <b>Акции и Магазин</b> — успейте забрать лимитированного <b>Scared Cat</b> (1,000 шт.) или буст-наборы за реальные Telegram Stars\n"
        f"• {ce('dollar')} <b>Чеки</b> — создавайте чеки на 1 или нескольких игроков (можно с паролем!) и делитесь ими в любом чате\n"
        f"• {ce_gift(1)} <b>Передача в чате</b> — напишите просто <code>Передать</code>, чтобы сразу выбрать подарок, или <code>Передать 1000 @user</code>\n"
        f"• {ce('exchange')} <b>NFT Маркет</b> — P2P-биржа улучшенных NFT и Scared Cat между игроками\n"
        f"• {ce('game')} <b>Mystery Cases</b> и {ce('shield')} <b>Кланы</b> — кейсы с редким дропом и клановые бонусы!"
        "</blockquote>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('thumbs_up')} Готовы начать игру?"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("Открыть Главное меню", style="success", emoji_key="play", callback_data="onb_finish")],
    ])
    await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML, reply_markup=kb)

# ---------------------------------------------------------------------------
# ОБРАБОТКА В ЧАТАХ (ДРОПЫ NFT И КОМАНДЫ БЕЗ СЛЭША)
# ---------------------------------------------------------------------------

async def on_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None or msg.text is None:
        return

    chat = update.effective_chat
    if chat and chat.type == "private":
        if not await ensure_privacy_accepted_private(update, context):
            return

    # 1. Сначала проверяем чат-команду "Передать ..."
    if await handle_chat_transfer(update, context):
        return

    text_raw = msg.text.strip()
    text_lower = text_raw.lower()

    if text_lower in ("я", "кто я"):
        if not await check_access_allowed(update):
            return
        u = update.effective_user
        db_user = get_or_create_user(u.id, u.username or "", u.first_name or "")
        clean_name = normalize_telegram_name(db_user["first_name"], db_user["username"], u.id)
        lvl, cur_xp, req_xp, _ = calculate_xp_level_info(db_user["xp"])
        rank = get_user_rank(u.id)
        clan = get_user_clan(u.id)
        clan_tag = clan["tag"] if clan else None
        display_title = f"[{clean_html(clan_tag)}] {clean_html(clean_name)}" if clan_tag else clean_html(clean_name)
        author_badge = f" • {ce('crown')} <b>Автор</b>" if db_user["is_author"] else ""

        fav_rows = get_favorites(u.id)
        avatar_bytes = await fetch_user_avatar_bytes(context.bot, u.id)
        custom_bg_val = db_user["bg_image_path"]
        if custom_bg_val and resolve_user_bg_path(u.id, custom_bg_val) is None:
            bg_fid = get_user_bg_file_id(u.id)
            if bg_fid:
                try:
                    tg_bg = await context.bot.get_file(bg_fid)
                    raw_bg = bytes(await tg_bg.download_as_bytearray())
                    if raw_bg:
                        custom_bg_val = save_user_background_data(u.id, raw_bg, file_id=bg_fid)
                except Exception:
                    pass
        card_img_io = None
        try:
            card_img_io = await generate_profile_card_image(
                db_user["first_name"] or clean_name,
                db_user["id_num"],
                db_user["balance_stars"],
                db_user["xp"],
                rank,
                fav_rows,
                avatar_bytes=avatar_bytes,
                clan_tag=clan_tag,
                custom_bg_path=custom_bg_val,
                fallback_username=db_user["username"],
                telegram_user_id=u.id,
            )
        except Exception:
            pass

        compact_cap = (
            f"{ce('smile')} <b>{display_title}</b>{author_badge}\n"
            f"{ce('bolt')} Ур. <b>{lvl}</b> ({cur_xp:,}/{req_xp:,} XP) • {ce('top')} ТОП <b>#{rank}</b>\n"
            f"{ce('dollar')} Баланс: <b>{fmt_stars_rub(db_user['balance_stars'])}</b>\n"
            f"{ce_gift(0)} Выбито: <b>{db_user['total_drops']}</b> • {ce('money_wings')} Продано: <b>{db_user['total_sold']}</b>"
        )
        if card_img_io:
            try:
                await msg.reply_photo(
                    photo=InputFile(card_img_io, filename="me.png"),
                    caption=compact_cap,
                    parse_mode=ParseMode.HTML,
                )
                return
            except Exception:
                pass
        await msg.reply_text(compact_cap, parse_mode=ParseMode.HTML)
        return

    if text_lower in ("баланс", "б", "balance"):
        if not await check_access_allowed(update):
            return
        u = update.effective_user
        db_user = get_or_create_user(u.id, u.username or "", u.first_name or "")
        clean_name = normalize_telegram_name(db_user["first_name"], db_user["username"], u.id)
        author_bal_line = (
            f"\n{ce('crown')} Авторский баланс: <b>{int(db_user['author_balance_stars'] or 0):,} {ce('star')}</b>"
            if db_user["is_author"] else ""
        )
        await msg.reply_text(
            f"{ce('dollar')} <b>Баланс {clean_html(clean_name)}:</b> <b>{fmt_stars_rub(db_user['balance_stars'])}</b>{author_bal_line}",
            parse_mode=ParseMode.HTML,
        )
        return

    if text_lower in ("коллекция", "инвентарь", "collection"):
        if not await check_access_allowed(update):
            return
        u = update.effective_user
        db_user = get_or_create_user(u.id, u.username or "", u.first_name or "")
        items = get_user_collection(u.id)
        clean_name = normalize_telegram_name(db_user["first_name"], db_user["username"], u.id)
        if not items:
            await msg.reply_text(
                f"{ce('bookmark')} <b>Коллекция {clean_html(clean_name)} пуста</b> (0/{db_user['max_inventory']}).",
                parse_mode=ParseMode.HTML,
            )
            return

        total_val = sum(get_item_display_value(it) for it in items)
        upgraded_items = [it for it in items if it["is_upgraded"]]
        regular_counts: Dict[str, Tuple[str, int, int]] = {}
        for it in items:
            if it["is_upgraded"]:
                continue
            g = GIFTS_BY_KEY.get(it["gift_key"])
            gname = g.name if g else it["gift_key"]
            gstars = g.stars if g else 0
            prev = regular_counts.get(it["gift_key"])
            regular_counts[it["gift_key"]] = (gname, (prev[1] + 1) if prev else 1, gstars)

        lines = [
            f"{ce('bookmark')} <b>Коллекция {clean_html(clean_name)} ({len(items)}/{db_user['max_inventory']})</b> • {fmt_stars_compact(total_val)} {ce('star')}"
        ]
        shown = 0
        for it in upgraded_items[:7]:
            g_ce = upgraded_gift_tg_emoji(it["gift_key"])
            g_title = get_upgraded_gift_title(it["gift_key"])
            val_s = get_item_display_value(it)
            lines.append(f"• {g_ce} <b>{g_title} #{it['upgrade_num']}</b> ({clean_html(it['model_name'])}) — <b>{fmt_stars_compact(val_s)} {ce('star')}</b>")
            shown += 1
        if len(upgraded_items) > 7:
            lines.append(f"<i>… и ещё {len(upgraded_items) - 7} улучшенных NFT</i>")
        reg_sorted = sorted(regular_counts.values(), key=lambda x: x[2] * x[1], reverse=True)
        for gname, cnt, gstars in reg_sorted[:max(1, 10 - shown)]:
            lines.append(f"• {ce_gift(0)} {clean_html(gname)} ×<b>{cnt}</b> ({fmt_stars_compact(gstars * cnt)} {ce('star')})")
        if len(reg_sorted) > max(1, 10 - shown):
            lines.append(f"<i>… и ещё {len(reg_sorted) - max(1, 10 - shown)} видов подарков</i>")

        await msg.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
        return

    if text_lower in ("профиль", "profile"):
        if not await check_access_allowed(update):
            return
        u = update.effective_user
        get_or_create_user(u.id, u.username or "", u.first_name or "")
        await show_profile_handler(update, u.id, context)
        return

    allowed_words = {"nft", "нфт", "подарок"}
    if text_lower not in allowed_words:
        return

    if not await check_access_allowed(update):
        return

    user = update.effective_user
    if chat and chat.type == "private" and context.user_data.get("onboarding_step") == 1:
        await send_onboarding_drop_reward(context.bot, chat.id, user, context)
        return

    row = get_or_create_user(user.id, user.username or "", user.first_name or "")

    now = int(time.time())
    if COOLDOWN_ENABLED:
        remaining = row["last_drop_ts"] + COOLDOWN_SECONDS - now
        if remaining > 0:
            await msg.reply_text(f"⏳ Рано! Команду NFT можно использовать 1 раз в час.\nПопробуйте через {seconds_to_hms(remaining)}.")
            return

    set_last_drop(user.id, now)

    if random.random() > CHAT_DROP_CHANCE:
        await msg.reply_text("💨 В этот раз ничего не выпало! Попробуйте снова через 1 час.")
        return

    clan = get_user_clan(user.id)
    clan_bonus_pct = 0.0
    clan_note = ""
    if clan:
        _, _, _, _, clan_bonus_pct = calculate_clan_level_info(clan["xp"])
        clan_note = f"\n🛡 Бонус клана [{clan['tag']}]: <b>+{clan_bonus_pct}%</b> к выигрышу!"

    gift = roll_gift_from_pool(GIFTS, bonus_pct=clan_bonus_pct)
    drop_id = create_pending_drop(user.id, update.effective_chat.id, gift.key)

    keyboard = InlineKeyboardMarkup([
        [
            make_btn("Сохранить в коллекцию", style="success", emoji_key="check", callback_data=f"keep:{drop_id}"),
            make_btn("Продать за Stars", style="primary", emoji_key="money_wings", callback_data=f"sell:{drop_id}"),
        ]
    ])

    g_ce = gift_tg_emoji(gift.key)
    caption = (
        f"{ce('boom')} <b>{clean_html(user.first_name)}</b>, вам выпал подарок!\n\n"
        f"{g_ce} <b>{gift.name}</b>\n"
        f"• Модель: <b>{gift.model_name}</b>\n"
        f"• Опыт: <b>+{gift.xp} XP</b>\n"
        f"• Ценность: {fmt_stars_rub(gift.stars)} / {fmt_ton(gift.ton)}"
        f"{clan_note}\n\n"
        f"Выберите действие ниже:"
    )

    try:
        card_io = await generate_gift_card_image(gift)
        if card_io:
            await msg.reply_photo(photo=InputFile(card_io, filename=f"gift_{gift.key}.png"), caption=caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            return
    except Exception:
        pass

    img_path = gift_image_path(gift.key)
    if img_path:
        try:
            with open(img_path, "rb") as f:
                await msg.reply_photo(photo=InputFile(f, filename=img_path.name), caption=caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            return
        except Exception:
            pass

    await msg.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)

# ---------------------------------------------------------------------------
# АКЦИИ (SCARED CAT) И МАГАЗИН ЗА TELEGRAM STARS (XTR)
# ---------------------------------------------------------------------------

async def show_promos_hub(query_or_msg, user_id: int) -> None:
    db_user = get_or_create_user(user_id, "", "")
    sold, remaining = get_scared_cat_supply_stats()
    pct = min(100, int(round((sold / SCARED_CAT_MAX_SUPPLY) * 100))) if SCARED_CAT_MAX_SUPPLY else 100
    status_line = (
        f"{ce('green_dot')} В наличии: <b>{remaining:,}</b> из <b>{SCARED_CAT_MAX_SUPPLY:,}</b> шт."
        if remaining > 0
        else f"{ce('red_dot')} <b>Тираж полностью распродан!</b>"
    )
    cap = (
        f"{ce('fire')} <b>Акции и Лимитированные NFT</b>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('star')} Ваш баланс: <b>{fmt_stars_rub(db_user['balance_stars'])}</b>\n\n"
        f"{ce('gem')} <b>Scared Cat (Уникальный коллекционный NFT)</b>\n"
        f"• Цена: <b>{SCARED_CAT_PROMO_PRICE:,} {ce('star')}</b>\n"
        f"• Тираж: <b>{sold:,} / {SCARED_CAT_MAX_SUPPLY:,}</b> ({pct}%)\n"
        f"• Статус: {status_line}\n"
        f"• Награда опыта: <b>+{SCARED_CAT_DEF.xp:,} XP</b>\n\n"
        "<blockquote expandable>"
        f"{ce('thought')} <b>Особенности лимитированного Scared Cat:</b>\n"
        "• Никогда не выпадает в кейсах и по слову <code>NFT</code>.\n"
        "• Всего ровно <b>1,000 экземпляров</b> на весь сервер (у каждого свой уникальный номер <code>#1..#1000</code>).\n"
        "• Не продаётся боту — можно свободно торговать на <b>NFT Маркете</b> без улучшений или передавать игрокам!"
        "</blockquote>"
    )
    buttons = []
    if remaining > 0:
        buttons.append([
            make_btn(
                f"Купить Scared Cat ({SCARED_CAT_PROMO_PRICE:,} ⭐)",
                style="success",
                emoji_key="fire",
                callback_data="promo_buy:scared_cat",
            )
        ])
    else:
        buttons.append([make_btn("Тираж распродан (1,000/1,000)", emoji_key="cross", callback_data="noop")])
    buttons.append([make_btn("Искать Scared Cat на Маркете", style="primary", emoji_key="exchange", callback_data="market_view:gift:scared_cat:1")])
    buttons.append([
        make_btn("В коллекцию", emoji_key="bookmark", callback_data="nav_collection_page:1"),
        make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main"),
    ])
    kb = InlineKeyboardMarkup(buttons)

    card_io = None
    try:
        card_io = await generate_scared_cat_promo_card_image(sold, remaining)
    except Exception:
        card_io = None
    if not card_io:
        card_io = await generate_gift_card_image(SCARED_CAT_DEF)
    if not card_io:
        img_p = gift_image_path("scared_cat")
        if img_p and img_p.exists():
            card_io = io.BytesIO(img_p.read_bytes())
            card_io.name = "scared_cat.webp"
            card_io.seek(0)

    if isinstance(query_or_msg, CallbackQuery):
        msg_obj = query_or_msg.message
        if msg_obj:
            try:
                await msg_obj.delete()
            except Exception:
                pass
            if card_io:
                await msg_obj.reply_photo(photo=InputFile(card_io, filename="promo_scared_cat.png"), caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await msg_obj.reply_text(cap, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        target_msg = query_or_msg.effective_message if hasattr(query_or_msg, "effective_message") else query_or_msg
        if target_msg:
            if card_io:
                await target_msg.reply_photo(photo=InputFile(card_io, filename="promo_scared_cat.png"), caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await target_msg.reply_text(cap, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_donate_shop(query_or_msg, user_id: int) -> None:
    db_user = get_or_create_user(user_id, "", "")
    lines = [
        f"{ce('bag')} <b>Магазин наборов (Telegram Stars XTR)</b>",
        "━━━━━━━━━━━━",
        f"{ce('dollar')} Игровой баланс: <b>{fmt_stars_rub(db_user['balance_stars'])}</b>\n",
        "Официальные буст-наборы с игровыми звёздами, опытом и улучшаемыми NFT (оплата в один клик через Telegram Stars):\n",
    ]
    buttons = []
    for pkey, p in DONATE_PACKS.items():
        lines.append(
            f"• <b>{p['title']}</b> — <b>{p['xtr_price']} Telegram ⭐</b>\n"
            f"   <i>+{fmt_stars_compact(p['stars_reward'])} игр. ⭐ • +{p['xp_reward']:,} XP • {p['summary_nfts']}</i>"
        )
        buttons.append([
            make_btn(
                f"{p['title']} — {p['xtr_price']} Telegram ⭐",
                style="primary" if p["xtr_price"] >= 249 else "success",
                emoji_key="star",
                callback_data=f"donate_buy:{pkey}",
            )
        ])
    lines.append(
        "\n<blockquote expandable>"
        f"{ce('info')} <b>Информация об оплате:</b>\n"
        "• Все пакеты опциональны — игра остаётся полностью бесплатной.\n"
        "• После оплаты Telegram Stars (XTR) бот мгновенно начислит звёзды, XP и все NFT (при нехватке мест слоты расширятся автоматически)."
        "</blockquote>"
    )
    buttons.append([make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")])
    text = "\n".join(lines)
    kb = InlineKeyboardMarkup(buttons)

    if isinstance(query_or_msg, CallbackQuery):
        await safe_edit_or_reply(query_or_msg, text, reply_markup=kb)
    else:
        target_msg = query_or_msg.effective_message if hasattr(query_or_msg, "effective_message") else query_or_msg
        if target_msg:
            await target_msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def send_donate_pack_invoice(query, user_id: int, pack_key: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    pack = DONATE_PACKS.get(pack_key)
    if not pack:
        await query.answer("❌ Набор не найден.", show_alert=True)
        return
    await query.answer()
    payload = f"donate:{pack_key}:{user_id}:{int(time.time())}"
    try:
        await context.bot.send_invoice(
            chat_id=user_id,
            title=pack["title"],
            description=pack["invoice_desc"][:250],
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(pack["title"], int(pack["xtr_price"]))],
        )
    except Exception as e:
        log.error("Ошибка отправки инвойса (%s, user=%s): %s", pack_key, user_id, e)
        await context.bot.send_message(
            chat_id=user_id,
            text=f"{ce('cross')} Не удалось создать счёт оплаты Telegram Stars. Попробуйте позже.",
            parse_mode=ParseMode.HTML,
        )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pre = update.pre_checkout_query
    if not pre:
        return
    payload = pre.invoice_payload or ""
    parts = payload.split(":")
    if len(parts) >= 2 and parts[0] == "donate" and parts[1] in DONATE_PACKS:
        pack = DONATE_PACKS[parts[1]]
        if pre.currency == "XTR" and int(pre.total_amount) == int(pack["xtr_price"]):
            await pre.answer(ok=True)
            return
    await pre.answer(ok=False, error_message="Некорректный платёжный пакет. Попробуйте создать счёт заново.")

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if not msg or not msg.successful_payment or not user:
        return
    sp = msg.successful_payment
    payload = sp.invoice_payload or ""
    parts = payload.split(":")
    if len(parts) < 2 or parts[0] != "donate" or parts[1] not in DONATE_PACKS:
        return
    pack_key = parts[1]
    get_or_create_user(user.id, user.username or "", user.first_name or "")
    charge_id = sp.telegram_payment_charge_id or f"local_{user.id}_{int(time.time())}"
    ok, res_msg, info = fulfill_donate_pack_db(
        user_id=user.id,
        pack_key=pack_key,
        xtr_amount=int(sp.total_amount),
        payload=payload,
        charge_id=charge_id,
    )
    if not ok:
        if res_msg == "ALREADY_PROCESSED":
            return
        await msg.reply_text(f"{ce('warn')} Платёж получен, но возникла ошибка начисления: {clean_html(res_msg)}", parse_mode=ParseMode.HTML)
        return

    slot_note = f"\n• {ce('bag')} Слоты коллекции расширены на <b>+{info['slots_added']}</b>" if info.get("slots_added") else ""
    text = (
        f"{ce('boom')} <b>Оплата прошла успешно — набор «{clean_html(info['title'])}» начислен!</b>\n"
        "━━━━━━━━━━━━\n"
        f"• {ce('star')} Игровые Stars: <b>+{info['stars_reward']:,} {ce('star')}</b>\n"
        f"• {ce('bolt')} Опыт: <b>+{info['xp_reward']:,} XP</b>\n"
        f"• {ce_gift(0)} NFT в коллекцию: <b>+{info['nfts_count']} шт.</b>{slot_note}\n"
        "━━━━━━━━━━━━\n"
        "Спасибо за поддержку New NFT Bot!"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("Открыть коллекцию", style="primary", emoji_key="bookmark", callback_data="nav_collection_page:1")],
        [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")],
    ])
    await msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

# ---------------------------------------------------------------------------
# ОБРАБОТЧИКИ CALLBACK QUERY
# ---------------------------------------------------------------------------

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data or ""
    user = query.from_user

    if data == "noop":
        await query.answer()
        return

    if not await check_access_allowed(update):
        return

    # Инлайн-чеки (работают в любом чате, query.message может быть None)
    if data.startswith("check_done:"):
        code = data.split(":", 1)[1]
        chk = get_star_check(code)
        if chk and int(chk["max_claims"] or 1) > 1:
            await query.answer(
                f"✅ Этот чек на {fmt_stars_compact(chk['amount_stars'])} ⭐ полностью разобран ({chk['claimed_count']}/{chk['max_claims']}).",
                show_alert=True,
            )
        elif chk and chk["claimed_by"]:
            cl = get_or_create_user(chk["claimed_by"], "", "")
            cname = normalize_telegram_name(cl["first_name"], cl["username"], chk["claimed_by"])
            await query.answer(f"✅ Этот чек на {fmt_stars_compact(chk['amount_stars'])} ⭐ уже активировал {cname}.", show_alert=True)
        else:
            await query.answer("✅ Этот чек уже активирован.", show_alert=True)
        return

    if data.startswith("claim_check:"):
        code = data.split(":", 1)[1]
        get_or_create_user(user.id, user.username or "", user.first_name or "")
        ok, msg_txt, chk = claim_star_check_db(code, user.id, user.username or "")
        if not ok:
            if msg_txt == "NEED_PASSWORD":
                bot_username = await get_bot_username(context.bot)
                await query.answer(
                    f"🔐 Чек защищён паролем! Откройте бота (@{bot_username}) для ввода пароля.",
                    show_alert=True,
                )
            else:
                await query.answer(f"❌ {msg_txt}", show_alert=True)
            return

        per_claim = int(chk["per_claim_stars"] or chk["amount_stars"])
        claimer_name = normalize_telegram_name(user.first_name, user.username, user.id)
        creator_row = get_or_create_user(chk["creator_id"], "", "")
        creator_name = normalize_telegram_name(creator_row["first_name"], creator_row["username"], chk["creator_id"])
        bot_username = await get_bot_username(context.bot)

        await query.answer(f"🎉 Вы получили +{fmt_stars_compact(per_claim)} ⭐ по чеку!", show_alert=True)

        await _refresh_shared_check_message(
            bot=context.bot,
            chk=chk,
            creator_name=creator_name,
            bot_username=bot_username,
            claimer_name=claimer_name,
            inline_message_id=query.inline_message_id,
            message=query.message,
        )

        if chk["creator_id"] != user.id:
            max_claims = max(1, int(chk["max_claims"] or 1))
            claimed_cnt = int(chk["claimed_count"] or 0)
            slots_note = f"\n{ce('sparkles')} Активаций: <b>{claimed_cnt}/{max_claims}</b>" if max_claims > 1 else ""
            try:
                await context.bot.send_message(
                    chat_id=chk["creator_id"],
                    text=(
                        f"{ce('dollar')} <b>Активация вашего чека (+{fmt_stars_compact(per_claim)} {ce('star')})!</b>\n"
                        f"{ce('smile')} Получатель: <b>{clean_html(claimer_name)}</b>{slots_note}"
                    ),
                    parse_mode=ParseMode.HTML,
                    reply_markup=quick_nav_keyboard(),
                )
            except Exception:
                pass
        return

    if data.startswith("gw_join:"):
        gw_id_str = data.split(":", 1)[1]
        if gw_id_str.isdigit():
            await handle_giveaway_join_callback(query, user, context, int(gw_id_str))
        else:
            await query.answer("❌ Конкурс не найден.", show_alert=True)
        return

    if data == "accept_privacy" or data.startswith("accept_privacy:"):
        get_or_create_user(user.id, user.username or "", user.first_name or "")
        accept_privacy_policy_db(user.id)
        mark_user_bot_started(user.id)
        await query.answer("✅ Политика конфиденциальности и условия приняты!")

        ref_rewarded, referrer_id, reward_amt, total_refs, total_ref_earned = claim_referral_reward_on_privacy_accept_db(user.id)
        if ref_rewarded and referrer_id:
            ref_disp = normalize_telegram_name(user.first_name, user.username, user.id)
            uname_part = f" (@{clean_html(user.username)})" if user.username else ""
            try:
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=(
                        f"{ce('boom')} <b>Новый реферал активирован!</b>\n"
                        "━━━━━━━━━━━━\n"
                        f"{ce('smile')} Пользователь: <b>{clean_html(ref_disp)}</b>{uname_part}\n"
                        f"{ce('check')} Выполнил условия: нажал <code>/start</code> и принял соглашение\n"
                        f"{ce('star')} Начислено: <b>+{reward_amt:,} {ce('star')}</b>\n"
                        "━━━━━━━━━━━━\n"
                        f"{ce('chart_bar')} Всего приглашено: <b>{total_refs:,}</b> чел.\n"
                        f"{ce('dollar')} Заработано с рефералов: <b>{fmt_stars_rub(total_ref_earned)}</b>"
                    ),
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [make_btn("Реферальная система", style="primary", emoji_key="megaphone", callback_data="nav_referral")],
                        [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")],
                    ]),
                )
            except Exception:
                pass

        pending_arg = data.split(":", 1)[1].strip() if ":" in data else context.user_data.pop("pending_start_arg", "")
        context.user_data.pop("pending_start_arg", None)

        if pending_arg.startswith("lot_") and pending_arg[4:].isdigit():
            await show_market_lot_detail(query, int(pending_arg[4:]), user.id, context)
            if query.message:
                try: await query.message.delete()
                except Exception: pass
            return

        if pending_arg.startswith("profile_") and pending_arg[8:].isdigit():
            target_id = int(pending_arg[8:])
            target_row = get_user_by_target(str(target_id))
            if not target_row:
                try:
                    chat_info = await context.bot.get_chat(target_id)
                    if chat_info:
                        target_row = get_or_create_user(target_id, chat_info.username or "", chat_info.first_name or "")
                except Exception:
                    target_row = None
            if target_row:
                await show_profile_handler(query, target_id, context)
                if query.message:
                    try: await query.message.delete()
                    except Exception: pass
                return

        if pending_arg.startswith("chk_") and len(pending_arg) > 4:
            code = pending_arg[4:]
            chk = get_star_check(code)
            chat_id = query.message.chat_id if query.message else user.id
            if query.message:
                try: await query.message.delete()
                except Exception: pass
            if not chk or chk["status"] != "active":
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"{ce('cross')} Этот чек недействителен или уже активирован.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=quick_nav_keyboard(),
                )
                return
            per_claim = int(chk["per_claim_stars"] or chk["amount_stars"])
            creator_row = get_or_create_user(chk["creator_id"], "", "")
            creator_name = normalize_telegram_name(creator_row["first_name"], creator_row["username"], chk["creator_id"])
            btn = (
                make_btn(f"Ввести пароль и забрать {fmt_stars_compact(per_claim)} ⭐", style="success", emoji_key="lock", callback_data=f"claim_check_pwd:{code}")
                if chk["has_password"]
                else make_btn(f"Забрать {fmt_stars_compact(per_claim)} ⭐", style="success", emoji_key="dollar", callback_data=f"claim_check:{code}")
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"{ce('dollar')} <b>Чек на {fmt_stars_compact(per_claim)} {ce('star')}</b>\n"
                    f"{ce('smile')} От: <b>{clean_html(creator_name)}</b>\n\n"
                    f"{ce('arrow_right')} Нажмите кнопку ниже, чтобы забрать чек:"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [btn],
                    [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")],
                ]),
            )
            return

        if pending_arg.startswith("gw_") and len(pending_arg) > 3:
            gw_code = pending_arg[3:]
            chat_id = query.message.chat_id if query.message else user.id
            if query.message:
                try: await query.message.delete()
                except Exception: pass
            await handle_giveaway_join_deeplink(chat_id, user, context, gw_code)
            return

        chat_id = query.message.chat_id if query.message else user.id
        if query.message:
            try: await query.message.delete()
            except Exception: pass
        if await maybe_send_channel_subscribe_prompt(context.bot, chat_id, user.id, context):
            return

        if not has_completed_onboarding(user.id):
            await send_onboarding_step1(context.bot, chat_id, user.first_name or "Игрок", context)
            return

        banner_img = await generate_main_menu_banner()
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=InputFile(banner_img, filename="menu.png"),
            caption=(
                f"{ce('smile')} <b>Привет, {clean_html(user.first_name)}! Добро пожаловать в New NFT Bot!</b>\n\n"
                f"Пишите слово <code>NFT</code> в группах, чтобы выбивать редчайшие Telegram Gifts! {ce_gift(0)}\n\n"
                f"• {ce('shield')} Вступайте в кланы, качайте уровень клана и гербы\n"
                f"• {ce('dollar')} Создавайте чеки на 1 или нескольких игроков (можно с паролем) в <b>«Чеки»</b>\n"
                f"• {ce('megaphone')} Приглашайте друзей в <b>«Реферальная система»</b> и получайте <b>+{REFERRAL_REWARD_STARS:,} {ce('star')}</b>\n"
                f"• {ce_gift(1)} Передавайте подарки и звёзды командой <code>Передать</code> прямо в чате\n"
                f"• {ce_pepe(0)} Улучшайте <b>Plush Pepe</b>, <b>Heart Locket</b>, <b>Algorithm Cup</b>, <b>Durov's Cap</b> и <b>Bonded Ring</b> (с баффами) и торгуйте на <b>NFT Маркете</b>\n"
                f"• {ce('fire')} Забирайте лимитированного <b>Scared Cat</b> в <b>«Акциях»</b> и буст-наборы в <b>«Магазине»</b>\n"
                f"• {ce('game')} Соревнуйтесь в <b>Режимах игры → Баттлы</b> (1–15 кейсов, 1–5 игроков) и забирайте весь дроп!\n"
                f"• {ce('chat')} Поддержка: {SUPPORT_HANDLE}\n\n"
                "Используйте кнопки меню для комфортного управления:"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(user.id),
        )
        return

    # Защита приватных разделов в группах
    if query.message and query.message.chat.type != "private" and (
        data in (
            "nav_cases_hub", "nav_top_page:1", "nav_settings", "nav_shop", "shop_slots_menu",
            "nav_clans_hub", "admin_panel", "admin_refresh", "nav_market", "market_create_offer", "market_my_offers",
            "market_history", "profile_upgrade_wip", "nav_checks", "check_create_start",
            "nav_referral", "ref_activate", "ref_copy_link", "ref_delete_msg",
            "nav_author", "author_policy", "author_apply_start", "author_dep_start", "author_wd_start",
            "author_ch_add_start", "author_channels", "gw_create_start", "admin_give_author_stars_start",
            "nav_modes", "btl_create_start", "btl_cases_next", "btl_clear_cases", "btl_pop_case", "btl_launch",
            "nav_promos", "nav_donate_shop", "nav_bonus", "bonus_claim_daily", "bonus_claim_promo",
            "nav_promocodes", "admin_broadcast_start",
        )
        or data.startswith("ref_list:")
        or data.startswith("author_")
        or data.startswith("admin_author_app")
        or data.startswith("admin_app_")
        or data.startswith("admin_promo")
        or data.startswith("admin_broadcast")
        or data.startswith("battles_")
        or data.startswith("battle_")
        or data.startswith("btl_")
        or data.startswith("promo_buy:")
        or data.startswith("donate_buy:")
        or data.startswith("case_captcha_ok:")
    ):
        await query.answer("⚠️ Откройте личные сообщения с ботом для этого меню!", show_alert=True)
        return

    if query.message and query.message.chat.type == "private":
        if not await ensure_privacy_accepted_private(update, context):
            return

    if data.startswith("channel_prompt_ack:"):
        ack_kind = data.split(":", 1)[1]
        mark_channel_prompt_done(user.id)
        await query.answer("✅ Спасибо!" if ack_kind == "sub" else "👌 Больше не будем предлагать.")
        chat_id = query.message.chat_id if query.message else user.id
        if query.message:
            try: await query.message.delete()
            except Exception: pass
        if not has_completed_onboarding(user.id):
            context.user_data.pop("ch_prompt_ref_note", None)
            await send_onboarding_step1(context.bot, chat_id, user.first_name or "Игрок", context)
            return
        ref_note = context.user_data.pop("ch_prompt_ref_note", "")
        banner_img = await generate_main_menu_banner()
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=InputFile(banner_img, filename="menu.png"),
            caption=(
                f"{ref_note}"
                f"{ce('smile')} <b>Привет, {clean_html(user.first_name)}! Добро пожаловать в New NFT Bot!</b>\n\n"
                f"Пишите слово <code>NFT</code> в группах, чтобы выбивать редчайшие Telegram Gifts! {ce_gift(0)}\n\n"
                f"• {ce('shield')} Вступайте в кланы, качайте уровень клана и гербы\n"
                f"• {ce('dollar')} Создавайте чеки на 1 или нескольких игроков (можно с паролем) в <b>«Чеки»</b>\n"
                f"• {ce('megaphone')} Приглашайте друзей в <b>«Реферальная система»</b> и получайте <b>+{REFERRAL_REWARD_STARS:,} {ce('star')}</b>\n"
                f"• {ce_gift(1)} Передавайте подарки и звёзды командой <code>Передать</code> прямо в чате\n"
                f"• {ce_pepe(0)} Улучшайте <b>Plush Pepe</b>, <b>Heart Locket</b>, <b>Algorithm Cup</b>, <b>Durov's Cap</b> и <b>Bonded Ring</b> (с баффами) и торгуйте на <b>NFT Маркете</b>\n"
                f"• {ce('fire')} Забирайте лимитированного <b>Scared Cat</b> в <b>«Акциях»</b> и буст-наборы в <b>«Магазине»</b>\n"
                f"• {ce('game')} Соревнуйтесь в <b>Режимах игры → Баттлы</b> (1–15 кейсов, 1–5 игроков) и забирайте весь дроп!\n"
                f"• {ce('chat')} Поддержка: {SUPPORT_HANDLE}\n\n"
                "Используйте кнопки меню для комфортного управления:"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(user.id),
        )
        return

    if data == "nav_promos":
        await query.answer()
        await show_promos_hub(query, user.id)
        return

    if data == "nav_auction":
        await query.answer("🔨 Аукцион пока не доступен и находится на этапе разработки.", show_alert=True)
        return

    if data == "promo_buy:scared_cat":
        get_or_create_user(user.id, user.username or "", user.first_name or "")
        ok_p, msg_p, ed_num, _item_id = buy_promo_scared_cat_db(user.id)
        if not ok_p:
            await query.answer(f"❌ {msg_p}", show_alert=True)
            return
        await query.answer(f"🎉 Scared Cat #{ed_num}/{SCARED_CAT_MAX_SUPPLY} ваш!", show_alert=True)
        _, remaining = get_scared_cat_supply_stats()
        cap = (
            f"{ce('boom')} <b>Поздравляем с покупкой Scared Cat #{ed_num}/{SCARED_CAT_MAX_SUPPLY}!</b>\n"
            "━━━━━━━━━━━━\n"
            f"{ce('fire')} Вы приобрели уникальный лимитированный NFT <b>Scared Cat</b>.\n"
            f"• Номер экземпляра: <b>#{ed_num} из {SCARED_CAT_MAX_SUPPLY:,}</b>\n"
            f"• Бонус опыта: <b>+{SCARED_CAT_DEF.xp:,} XP</b>\n"
            f"• Осталось в продаже: <b>{remaining:,} шт.</b>\n"
            "━━━━━━━━━━━━\n"
            "Экземпляр уже добавлен в вашу коллекцию — его можно выставить на <b>NFT Маркет</b> или передать игрокам!"
        )
        kb = InlineKeyboardMarkup([
            [make_btn("Выставить на маркет", style="primary", emoji_key="exchange", callback_data=f"market_sell_start:{_item_id}")],
            [make_btn("В коллекцию", emoji_key="bookmark", callback_data="nav_collection_page:1")],
            [make_btn("К акциям", emoji_key="fire", callback_data="nav_promos")],
            [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")],
        ])
        card_io = await generate_gift_card_image(SCARED_CAT_DEF)
        if query.message:
            try:
                await query.message.delete()
            except Exception:
                pass
            if card_io:
                await query.message.reply_photo(photo=InputFile(card_io, filename=f"scared_cat_{ed_num}.png"), caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await query.message.reply_text(cap, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    if data == "nav_donate_shop":
        await query.answer()
        await show_donate_shop(query, user.id)
        return

    if data.startswith("donate_buy:"):
        pack_key = data.split(":", 1)[1]
        await send_donate_pack_invoice(query, user.id, pack_key, context)
        return

    if data.startswith("case_captcha_ok:"):
        tier_key = data.split(":", 1)[1]
        pass_case_captcha_db(user.id)
        await query.answer("✅ Проверка пройдена! Можно открывать кейсы дальше.")
        if tier_key in CASE_TIERS:
            tinfo = CASE_TIERS[tier_key]
            kb = InlineKeyboardMarkup([
                [make_btn(f"Открыть {tinfo['name']} ({tinfo['price']:,}⭐)", style="success", emoji_key="game", callback_data=f"open_case:{tier_key}")],
                [make_btn("К кейсам", emoji_key="game", callback_data="nav_cases_hub")],
                [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")],
            ])
            await safe_edit_or_reply(
                query,
                f"{ce('check')} <b>Проверка пройдена!</b>\nНажмите кнопку ниже, чтобы продолжить открывать кейсы:",
                reply_markup=kb,
            )
        else:
            await safe_edit_or_reply(
                query,
                f"{ce('check')} <b>Проверка пройдена!</b>\nМожете продолжать открывать кейсы.",
                reply_markup=InlineKeyboardMarkup([[make_btn("К кейсам", emoji_key="game", callback_data="nav_cases_hub")]]),
            )
        return

    if data == "profile_upgrade_wip":
        await query.answer()
        await show_shop_page(query, user.id)
        return

    if data in ("admin_panel", "admin_refresh"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        await query.answer("🔄 Статистика обновлена!" if data == "admin_refresh" else None)
        await show_admin_panel(query)
        return

    if data == "admin_toggle_maintenance":
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        new_state = not is_maintenance_mode()
        set_maintenance_mode(new_state)
        status_alert = "🔴 Бот отключён (включены техработы)!" if new_state else "🟢 Бот снова включён и работает!"
        await query.answer(status_alert, show_alert=True)
        await show_admin_panel(query)
        return

    if data == "admin_firebase_menu":
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        await query.answer()
        await show_admin_firebase_menu(query)
        return

    if data == "admin_firebase_sync":
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        ok = firebase_manager.upload_db_to_cloud(force=True)
        if ok:
            await query.answer("✅ База base.db успешно сохранена в Cloud Firestore!", show_alert=True)
        else:
            await query.answer("❌ Ошибка синхронизации. Проверьте статус в меню или логи.", show_alert=True)
        await show_admin_firebase_menu(query)
        return

    if data == "admin_firebase_restore":
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        ok = firebase_manager.download_db_on_startup()
        if ok:
            db_init()
            await query.answer("📥 База base.db успешно восстановлена из Firestore!", show_alert=True)
        else:
            await query.answer("❌ Не удалось восстановить базу.", show_alert=True)
        await show_admin_firebase_menu(query)
        return

    if data.startswith("admin_promos_menu:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        await query.answer()
        pg = int(data.split(":", 1)[1] or 1)
        await show_admin_promos_menu(query, page=pg)
        return

    if data.startswith("admin_promo_view:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        await query.answer()
        pid = int(data.split(":", 1)[1])
        await show_admin_promo_detail(query, pid)
        return

    if data.startswith("admin_promo_adj:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        _, pid_s, delta_s = data.split(":")
        ok_a, msg_a, new_max = adjust_promocode_max_uses_db(int(pid_s), int(delta_s))
        await query.answer(f"Лимит: {new_max:,}" if ok_a else f"❌ {msg_a}")
        await show_admin_promo_detail(query, int(pid_s))
        return

    if data.startswith("admin_promo_toggle:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        pid = int(data.split(":", 1)[1])
        ok_t, st_val = toggle_promocode_active_db(pid)
        await query.answer("🟢 Промокод включён" if (ok_t and st_val) else "🔴 Промокод отключён")
        await show_admin_promo_detail(query, pid)
        return

    if data.startswith("admin_promo_del_confirm:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        await query.answer()
        pid = int(data.split(":", 1)[1])
        p = get_promocode_by_id_db(pid)
        code_txt = p["code"] if p else str(pid)
        kb = InlineKeyboardMarkup([
            [
                make_btn("Да, удалить", style="danger", emoji_key="trash", callback_data=f"admin_promo_del_do:{pid}"),
                make_btn("Отмена", callback_data=f"admin_promo_view:{pid}"),
            ]
        ])
        await safe_edit_or_reply(
            query,
            f"⚠️ Удалить промокод <code>{clean_html(code_txt)}</code> безвозвратно?",
            reply_markup=kb,
        )
        return

    if data.startswith("admin_promo_del_do:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        pid = int(data.split(":", 1)[1])
        delete_promocode_db(pid)
        await query.answer("🗑 Промокод удалён.")
        await show_admin_promos_menu(query, 1)
        return

    # Чат-передача подарка через инлайн-кнопки
    if data.startswith("chat_gx_cancel:"):
        sender_id = int(data.split(":")[1])
        if user.id != sender_id:
            await query.answer("❌ Это не ваше меню передачи!", show_alert=True)
            return
        await query.answer("Отменено.")
        await query.edit_message_text("❌ Передача подарка отменена.")
        return

    if data.startswith("chat_gx_pg:"):
        _, sender_s, target_s, page_s = data.split(":")
        sender_id, target_id, page = int(sender_s), int(target_s), int(page_s)
        if user.id != sender_id:
            await query.answer("❌ Это не ваше меню передачи!", show_alert=True)
            return
        await query.answer()
        target_row = get_or_create_user(target_id, "", "") if target_id > 0 else None
        await show_chat_gift_picker(query.message, sender_id, target_row, page=page, edit_query=query)
        return

    if data.startswith("chat_gx_do:"):
        _, sender_s, target_s, item_s = data.split(":")
        sender_id, target_id, item_id = int(sender_s), int(target_s), int(item_s)
        if user.id != sender_id:
            await query.answer("❌ Это не ваше меню передачи!", show_alert=True)
            return
        item_before = get_collection_item(item_id)
        ok, res = transfer_gift_between_users(sender_id, target_id, item_id)
        if not ok:
            await query.answer(f"❌ {res}", show_alert=True)
            return
        await query.answer("🎁 Подарок передан!")
        g = GIFTS_BY_KEY.get(res)
        if item_before and item_before["is_upgraded"]:
            g_name = f"{get_upgraded_gift_title(item_before['gift_key'])} #{item_before['upgrade_num']} ({item_before['model_name']})"
        else:
            g_name = g.name if g else res
        target_row = get_or_create_user(target_id, "", "")
        receiver_name = normalize_telegram_name(target_row["first_name"], target_row["username"], target_id)
        await query.edit_message_text(
            f"🎁 <b>Подарок передан!</b>\n"
            f"Игрок <b>{clean_html(user.first_name)}</b> передал <b>{clean_html(g_name)}</b> "
            f"игроку <b>{clean_html(receiver_name)}</b>!",
            parse_mode=ParseMode.HTML,
        )
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"🎁 <b>Вам передали подарок!</b>\nОт: <b>{clean_html(user.first_name)}</b>\nПодарок: <b>{clean_html(g_name)}</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=quick_nav_keyboard(),
            )
        except Exception:
            pass
        return

    # Мини-обучение (Onboarding)
    if data == "onb_drop":
        await query.answer()
        if query.message:
            try: await query.message.delete()
            except Exception: pass
        await send_onboarding_drop_reward(context.bot, user.id, user, context)
        return

    if data.startswith("onb_keep_drop:") or data.startswith("onb_sell_drop:"):
        action_onb, drop_s = data.split(":", 1)
        drop_id = int(drop_s)
        drop = get_pending_drop(drop_id)
        if not drop or drop["user_id"] != user.id:
            await query.answer("❌ Это не ваш подарок!", show_alert=True)
            return
        await query.answer()
        gift = GIFTS_BY_KEY.get(drop["gift_key"])
        if not drop["resolved"]:
            resolve_pending_drop(drop_id)
            if action_onb == "onb_keep_drop":
                added = add_to_collection(user.id, gift.key)
                if added:
                    note = f"✅ Подарок <b>{gift.name}</b> сохранён в коллекцию (+{gift.xp} XP)!"
                else:
                    sell_from_pending(user.id, gift.key, gift.stars)
                    note = f"💰 Подарок <b>{gift.name}</b> продан за {fmt_stars_rub(gift.stars)}!"
            else:
                sell_from_pending(user.id, gift.key, gift.stars)
                note = f"💰 Подарок <b>{gift.name}</b> продан за {fmt_stars_rub(gift.stars)} (+{gift.xp // 2} XP)!"
        else:
            note = "✅ Переходим к вашему профилю!"
        await send_onboarding_step2_profile(query, user, context, note)
        return

    if data == "onb_step3":
        await query.answer()
        if query.message:
            try: await query.message.delete()
            except Exception: pass
        await send_onboarding_step3_overview(context.bot, user.id)
        return

    if data == "onb_finish":
        set_onboarding_done(user.id)
        context.user_data.pop("onboarding_step", None)
        await query.answer("🚀 Обучение завершено!")
        if query.message:
            try: await query.message.delete()
            except Exception: pass
        banner_img = await generate_main_menu_banner()
        await context.bot.send_photo(
            chat_id=user.id,
            photo=InputFile(banner_img, filename="menu.png"),
            caption="🏠 <b>Главное меню New NFT Bot:</b>\nВыберите нужный раздел кнопками ниже:",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(user.id),
        )
        return

    # Чеки (раздел внутри бота)
    if data == "nav_checks":
        await query.answer()
        await show_checks_hub(query, user.id, context)
        return

    if data.startswith("check_cancel:"):
        code = data.split(":", 1)[1]
        ok, err_txt, refund = cancel_star_check_db(code, user.id)
        if not ok:
            await query.answer(f"❌ {err_txt}", show_alert=True)
            return
        await query.answer(f"✅ Чек отменён! Возвращено +{fmt_stars_compact(refund)} ⭐.", show_alert=True)
        await show_checks_hub(query, user.id, context)
        return

    # Реферальная система
    if data == "nav_referral":
        await query.answer()
        await show_referral_hub(query, user.id, context)
        return

    # Авторство и конкурсы
    if data == "nav_author":
        await query.answer()
        await show_author_hub(query, user.id, context)
        return

    if data == "author_policy":
        await query.answer()
        await show_author_policy_page(query)
        return

    if data == "author_channels":
        await query.answer()
        await show_author_channels_page(query, user.id)
        return

    if data.startswith("author_ch_del:"):
        ch_row_id = int(data.split(":")[1])
        if delete_author_channel_db(user.id, ch_row_id):
            await query.answer("🗑 Канал удалён из списка.")
        else:
            await query.answer("❌ Канал не найден.", show_alert=True)
        await show_author_channels_page(query, user.id)
        return

    if data == "verify_author_channel":
        await handle_verify_author_channel(query, user.id, context)
        return

    if data.startswith("author_giveaways:"):
        await query.answer()
        page = int(data.split(":")[1])
        await show_author_giveaways_page(query, user.id, page)
        return

    if data.startswith("author_gw_view:"):
        await query.answer()
        gw_id = int(data.split(":")[1])
        await show_author_giveaway_detail(query, user.id, gw_id)
        return

    if data.startswith("author_gw_end:"):
        gw_id = int(data.split(":")[1])
        gw = get_giveaway_by_id_db(gw_id)
        if not gw or gw["author_id"] != user.id:
            await query.answer("❌ Конкурс не найден.", show_alert=True)
            return
        if gw["status"] != "active":
            await query.answer("⚠️ Конкурс уже завершён или ещё не опубликован.", show_alert=True)
            return
        await query.answer("🏁 Завершаем конкурс и выплачиваем призы...")
        await finalize_giveaway_and_notify(context.bot, gw_id)
        await show_author_giveaway_detail(query, user.id, gw_id)
        return

    if data.startswith("author_gw_cancel:"):
        gw_id = int(data.split(":")[1])
        ok, err_m, refund = cancel_scheduled_giveaway_db(gw_id, user.id)
        if not ok:
            await query.answer(f"❌ {err_m}", show_alert=True)
            return
        await query.answer(f"✅ Отменено! Возвращено +{refund:,} ⭐ на авторский баланс.", show_alert=True)
        await show_author_giveaways_page(query, user.id, 1)
        return

    if data.startswith("admin_author_apps:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        await query.answer()
        page = int(data.split(":")[1])
        await show_admin_author_apps_page(query, page)
        return

    if data.startswith("admin_author_app:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        await query.answer()
        app_id = int(data.split(":")[1])
        await show_admin_author_app_detail(query, app_id)
        return

    if data.startswith("admin_app_approve:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        app_id = int(data.split(":")[1])
        await execute_admin_approve_author_app(query, user.id, app_id, context)
        return

    if data == "ref_activate":
        created_now, _, _ = activate_referral_system_db(user.id)
        if created_now:
            await query.answer("🎉 Реферальная система успешно активирована бесплатно!", show_alert=True)
        else:
            await query.answer("✅ Реферальная система уже активирована!")
        await show_referral_hub(query, user.id, context)
        return

    if data == "ref_copy_link":
        db_user = get_or_create_user(user.id, user.username or "", user.first_name or "")
        if not db_user["referral_active"] or not db_user["referral_code"]:
            await query.answer("⚠️ Сначала активируйте реферальную систему!", show_alert=True)
            return
        bot_username = await get_bot_username(context.bot)
        ref_link = f"https://t.me/{bot_username}?start=ref_{db_user['referral_code']}"
        await query.answer("Нажмите на ссылку в сообщении ниже, чтобы скопировать!")
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                f"{ce('link')} <b>Ваша реферальная ссылка:</b>\n"
                f"<i>Нажмите на ссылку ниже, чтобы скопировать её в буфер обмена:</i>\n\n"
                f"<code>{clean_html(ref_link)}</code>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [make_btn("Закрыть", emoji_key="cross", callback_data="ref_delete_msg")],
            ]),
        )
        return

    if data == "ref_delete_msg":
        await query.answer()
        if query.message:
            try: await query.message.delete()
            except Exception: pass
        return

    if data.startswith("ref_list:"):
        await query.answer()
        page_str = data.split(":", 1)[1]
        page = int(page_str) if page_str.isdigit() else 1
        await show_referral_list_page(query, user.id, page, context)
        return

    # Кланы
    if data == "nav_clans_hub":
        await query.answer()
        await show_clans_hub(query, user.id, context)
        return

    if data.startswith("clan_info:"):
        await query.answer()
        clan_id = int(data.split(":")[1])
        await show_clan_profile_handler(query, clan_id, context)
        return

    if data.startswith("clan_members_detail:"):
        await query.answer()
        clan_id = int(data.split(":")[1])
        await show_clan_members_detail(query, clan_id)
        return

    if data.startswith("clan_gifts_menu:"):
        await query.answer()
        parts = data.split(":")
        clan_id = int(parts[1])
        page = int(parts[2]) if len(parts) > 2 else 1
        await show_clan_gifts_menu(query, clan_id, page)
        return

    if data.startswith("clan_toggle_gift_fav:"):
        _, clan_s, cg_s, page_s = data.split(":")
        clan_id, cg_id, page = int(clan_s), int(cg_s), int(page_s)
        clan = get_clan_by_id(clan_id)
        if not clan or clan["owner_id"] != user.id:
            await query.answer("❌ Только создатель клана может управлять избранным!", show_alert=True)
            return
        ok, msg_txt = toggle_clan_gift_favorite(clan_id, cg_id)
        await query.answer(msg_txt, show_alert=not ok)
        await show_clan_gifts_menu(query, clan_id, page)
        return

    if data.startswith("clan_donate_gift_menu:"):
        await query.answer()
        parts = data.split(":")
        clan_id = int(parts[1])
        page = int(parts[2]) if len(parts) > 2 else 1
        await show_clan_donate_gift_menu(query, clan_id, user.id, page)
        return

    if data.startswith("clan_donate_gift_confirm:"):
        await query.answer()
        _, clan_s, item_s = data.split(":")
        await show_clan_donate_gift_confirm(query, int(clan_s), int(item_s), user.id)
        return

    if data.startswith("clan_donate_gift_do:"):
        _, clan_id_str, item_id_str = data.split(":")
        await execute_clan_donate_gift(query, int(clan_id_str), int(item_id_str), user.id, context)
        return

    # Админ-выдача подарков по фильтрам
    if data.startswith("adm_filt_price:"):
        await query.answer()
        await show_admin_nft_price_tiers(query, int(data.split(":")[1]))
        return

    if data.startswith("adm_filt_model:"):
        await query.answer()
        await show_admin_nft_model_groups(query, int(data.split(":")[1]))
        return

    if data.startswith("adm_back_filters:"):
        await query.answer()
        target_id = int(data.split(":")[1])
        target = get_user_by_target(str(target_id))
        tname = normalize_telegram_name(
            target["first_name"] if target else None,
            target["username"] if target else None,
            target_id,
        )
        await show_admin_nft_filter_selector(query, target_id, tname)
        return

    if data.startswith("adm_items:"):
        await query.answer()
        _, ftype, fkey, target_id, page = data.split(":")
        await show_admin_nft_items_page(query, ftype, fkey, int(target_id), int(page))
        return

    if data.startswith("adm_give_mode:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        await query.answer()
        _, gift_key, target_id = data.split(":")
        await show_admin_give_mode_selector(query, gift_key, int(target_id))
        return

    if data.startswith("adm_give_std:") or data.startswith("adm_give_do:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        _, gift_key, target_id = data.split(":")
        await execute_admin_give_nft(query, gift_key, int(target_id), context)
        return

    if data.startswith("adm_give_upg_pick:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        await query.answer()
        target_id = int(data.split(":")[1])
        await show_admin_upg_gift_picker(query, target_id)
        return

    if data.startswith("adm_give_upg_models:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        await query.answer()
        _, gift_key, target_id, page = data.split(":")
        await show_admin_upg_models_page(query, gift_key, int(target_id), int(page))
        return

    if data.startswith("adm_give_upg_bgs:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        await query.answer()
        _, gift_key, m_idx, target_id, page = data.split(":")
        await show_admin_upg_backdrops_page(query, gift_key, int(m_idx), int(target_id), int(page))
        return

    if data.startswith("adm_give_upg_confirm:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        await query.answer()
        _, gift_key, m_idx, b_idx, target_id = data.split(":")
        await show_admin_upg_confirm(query, gift_key, int(m_idx), int(b_idx), int(target_id))
        return

    if data.startswith("adm_give_upg_do:"):
        if user.id not in ADMIN_IDS:
            await query.answer("❌ Доступ запрещен!", show_alert=True)
            return
        _, gift_key, m_idx, b_idx, target_id = data.split(":")
        await execute_admin_give_upgraded_nft(query, gift_key, int(m_idx), int(b_idx), int(target_id), context)
        return

    # Улучшения Plush Pepe
    if data == "shop_slots_menu":
        await query.answer()
        await show_shop_slots_menu(query, user.id)
        return

    if data.startswith("upgrade_item:"):
        await query.answer()
        item_id = int(data.split(":")[1])
        await show_gift_upgrade_confirm(query, user.id, item_id)
        return

    if data.startswith("upgrade_confirm:"):
        item_id = int(data.split(":")[1])
        await execute_gift_upgrade(query, user.id, item_id, context)
        return

    # Маркет
    if data == "market_filter_price_menu":
        await query.answer()
        await show_market_filter_price_menu(query)
        return

    if data == "market_filter_rarity_menu":
        await query.answer()
        await show_market_filter_rarity_menu(query)
        return

    if data.startswith("market_filter_model_menu"):
        await query.answer()
        parts = data.split(":")
        if len(parts) >= 3:
            gift_key = parts[1]
            page = int(parts[2])
        elif len(parts) == 2 and parts[1].isdigit():
            gift_key = "pepe_heart"
            page = int(parts[1])
        elif len(parts) == 2:
            gift_key = parts[1]
            page = 1
        else:
            gift_key = "pepe_heart"
            page = 1
        await show_market_filter_model_menu(query, gift_key, page)
        return

    if data.startswith("market_view:"):
        await query.answer()
        _, ftype, fkey, page = data.split(":")
        await show_market_view_page(query, ftype, fkey, int(page))
        return

    if data == "market_create_offer":
        await query.answer()
        await show_market_create_offer_list(query, user.id, 1)
        return

    if data.startswith("market_create_offer_pg:"):
        await query.answer()
        page = int(data.split(":")[1])
        await show_market_create_offer_list(query, user.id, page)
        return

    if data == "market_my_offers":
        await query.answer()
        await show_market_my_offers(query, user.id)
        return

    if data == "market_history":
        await query.answer()
        await show_market_history(query, user.id)
        return

    if data.startswith("market_lot:"):
        await query.answer()
        listing_id = int(data.split(":")[1])
        await show_market_lot_detail(query, listing_id, user.id, context)
        return

    if data.startswith("market_cancel_lot:"):
        listing_id = int(data.split(":")[1])
        ok, msg_txt = cancel_market_listing(user.id, listing_id)
        await query.answer(msg_txt, show_alert=True)
        await show_market_my_offers(query, user.id)
        return

    if data.startswith("market_buy:"):
        listing_id = int(data.split(":")[1])
        ok, msg_txt, info = buy_market_listing(user.id, listing_id)
        if not ok or not info:
            await query.answer(f"❌ {msg_txt}", show_alert=True)
            return

        await query.answer("🎉 Покупка совершена!")
        gift_key = info.get("gift_key") or "pepe_heart"
        g_title = get_upgraded_gift_title(gift_key)
        buyer_name = normalize_telegram_name(user.first_name, user.username, user.id)
        is_unique_scared = (gift_key == "scared_cat" and info.get("backdrop_key") == "limited")
        g_ce = upgraded_gift_tg_emoji(gift_key)

        if is_unique_scared:
            seller_item_lines = f"{g_ce} Подарок: <b>Scared Cat #{info['upgrade_num']}/{SCARED_CAT_MAX_SUPPLY}</b> (Уник.)\n"
            buyer_item_line = f"{g_ce} <b>Scared Cat #{info['upgrade_num']}/{SCARED_CAT_MAX_SUPPLY}</b> (Уникальный коллекционный NFT)\n"
        else:
            m = get_model_def(gift_key, info["model_name"])
            b = BACKDROPS_BY_KEY.get(info["backdrop_key"]) or PLUSHPEPE_BACKDROPS[0]
            seller_item_lines = (
                f"{g_ce} Модель: <b>{clean_html(m.name)}</b>\n"
                f"{ce('sparkles')} Фон: <b>{clean_html(b.name)}</b>\n"
            )
            buyer_item_line = (
                f"{g_ce} {g_title} #{info['upgrade_num']} • <b>{clean_html(m.name)}</b>\n"
                f"{ce('sparkles')} Фон: <b>{clean_html(b.name)}</b> ({b.rarity_label})\n"
            )

        try:
            await context.bot.send_message(
                chat_id=info["seller_id"],
                text=(
                    f"{ce('dollar')} <b>Ваш лот #{info['listing_id']} ({g_title}) продан на NFT Маркете!</b>\n"
                    f"━━━━━━━━━━━━\n"
                    f"{seller_item_lines}"
                    f"{ce('smile')} Покупатель: <b>{clean_html(buyer_name)}</b>\n"
                    f"{ce('star')} Цена лота: <b>{info['price_stars']:,} {ce('star')}</b>\n"
                    f"{ce('chart_down')} Комиссия 15%: <b>-{info['fee_stars']:,} {ce('star')}</b>\n"
                    f"{ce('check')} Зачислено на баланс: <b>+{info['seller_gets']:,} {ce('star')}</b>"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=quick_nav_keyboard(),
            )
        except Exception:
            pass

        cap = (
            f"{ce('boom')} <b>Поздравляем с покупкой на NFT Маркете!</b>\n"
            f"━━━━━━━━━━━━\n"
            f"{buyer_item_line}"
            f"{ce('dollar')} Оплачено: <b>{info['price_stars']:,} {ce('star')}</b>\n"
            f"━━━━━━━━━━━━\n"
            f"Подарок уже добавлен в вашу коллекцию!"
        )
        kb = InlineKeyboardMarkup([
            [make_btn("В коллекцию", emoji_key="bookmark", callback_data="nav_collection_page:1")],
            [make_btn("Вернуться в маркет", emoji_key="bag", callback_data="nav_market")],
        ])
        if query.message.photo:
            await query.edit_message_caption(caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await query.edit_message_text(cap, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    if data == "nav_main":
        await query.answer()
        banner_img = await generate_main_menu_banner()
        if query.message.photo:
            try: await query.message.delete()
            except Exception: pass
        await query.message.reply_photo(
            photo=InputFile(banner_img, filename="menu.png"),
            caption=f"{ce('desktop')} <b>Главное меню New NFT Bot:</b>\nВыберите нужный раздел кнопками ниже:",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(user.id)
        )
        return

    if data == "nav_profile":
        await query.answer()
        get_or_create_user(user.id, user.username or "", user.first_name or "")
        await show_profile_handler(query, user.id, context)
        return

    if data == "nav_info":
        await query.answer()
        await show_info_page(query, context)
        return

    if data == "info_group_guide":
        await query.answer()
        await show_group_guide(query, context)
        return

    if data == "info_privacy":
        await query.answer()
        await show_privacy_policy(query)
        return

    if data == "info_rules":
        await query.answer()
        await show_rules_page(query)
        return

    if data == "nav_market":
        await query.answer()
        await show_market_hub(query)
        return

    if data == "bg_reset":
        await query.answer()
        kb = InlineKeyboardMarkup([
            [
                make_btn("Да, сбросить фон", style="danger", emoji_key="trash", callback_data="bg_reset_confirm"),
                make_btn("Отмена", emoji_key="cross", callback_data="nav_settings"),
            ]
        ])
        confirm_txt = (
            f"{ce('warn')} <b>Сброс кастомного фона профиля</b>\n"
            "━━━━━━━━━━━━\n"
            "Вы уверены, что хотите удалить текущий кастомный фон профиля?\n"
            f"Для повторной установки снова потребуется оплата (<b>{BG_SET_COST:,} ⭐</b>)."
        )
        await safe_edit_or_reply(query, confirm_txt, reply_markup=kb)
        return

    if data == "bg_reset_confirm":
        await bg_reset_handler(query, user.id, context)
        return

    if data == "nav_settings":
        await query.answer()
        await show_settings_page(query, user.id)
        return

    if data == "nav_shop":
        await query.answer()
        await show_shop_page(query, user.id)
        return

    if data.startswith("nav_collection_page:"):
        await query.answer()
        page = int(data.split(":")[1])
        await show_collection_page(query, user.id, page)
        return

    if data.startswith("nav_top_page:"):
        await query.answer()
        page = int(data.split(":")[1])
        await show_top_page(query, page)
        return

    if data.startswith("clan_list:"):
        await query.answer()
        page = int(data.split(":")[1])
        await show_clans_list(query, page)
        return

    if data.startswith("clan_join:"):
        clan_id = int(data.split(":")[1])
        if get_user_clan(user.id):
            await query.answer("Вы уже состоите в клане!", show_alert=True)
            return
        if add_user_to_clan(user.id, clan_id):
            await query.answer("🎉 Вы успешно вступили в клан!", show_alert=True)
            await show_clan_profile_handler(query, clan_id, context)
        else:
            await query.answer("❌ В клане нет свободных мест!", show_alert=True)
        return

    if data.startswith("clan_join_stars:"):
        clan_id = int(data.split(":")[1])
        clan = get_clan_by_id(clan_id)
        if get_user_clan(user.id):
            await query.answer("Вы уже состоите в клане!", show_alert=True)
            return

        if not deduct_user_stars(user.id, clan["entry_fee"]):
            await query.answer(f"❌ Недостаточно Stars! Нужно {clan['entry_fee']} ⭐", show_alert=True)
            return

        add_user_stars(clan["owner_id"], clan["entry_fee"], track_issued=False)
        record_star_flow(spent=int(clan["entry_fee"]))
        add_user_to_clan(user.id, clan_id)
        await query.answer("🎉 Вы вступили в клан за Stars!", show_alert=True)
        await show_clan_profile_handler(query, clan_id, context)
        return

    if data.startswith("clan_apply:"):
        clan_id = int(data.split(":")[1])
        if add_clan_request(clan_id, user.id):
            await query.answer("📩 Заявка отправлена лидеру клана!", show_alert=True)
        else:
            await query.answer("⚠️ Вы уже подавали заявку!", show_alert=True)
        return

    if data.startswith("clan_kick:"):
        target_id = int(data.split(":")[1])
        clan = get_user_clan(user.id)
        if clan and clan["owner_id"] == user.id:
            remove_user_from_clan(target_id)
            await query.answer("Игрок исключён из клана.")
            await show_clan_members_detail(query, clan["id"])
        return

    if data.startswith("clan_leave:"):
        remove_user_from_clan(user.id)
        await query.answer("Вы покинули клан.")
        await show_clans_hub(query, user.id, context)
        return

    if data.startswith("clan_delete_confirm:"):
        await query.answer()
        clan_id = int(data.split(":")[1])
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Да, расформировать", callback_data=f"clan_delete_do:{clan_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data=f"clan_info:{clan_id}")]
        ])
        if query.message.photo:
            await query.message.delete()
            await query.message.reply_text("⚠️ Вы действительно хотите <b>РАСФОРМИРОВАТЬ</b> клан?", parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await query.edit_message_text("⚠️ Вы действительно хотите <b>РАСФОРМИРОВАТЬ</b> клан?", parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    if data.startswith("clan_delete_do:"):
        clan_id = int(data.split(":")[1])
        delete_clan(clan_id)
        await query.answer("Клан расформирован.")
        await show_clans_hub(query, user.id, context)
        return

    if data.startswith("clan_upgrade:"):
        clan_id = int(data.split(":")[1])
        clan = get_clan_by_id(clan_id)
        cost = get_clan_upgrade_cost(clan["max_members"])

        ok, msg_info = upgrade_clan_slots(clan_id, cost)
        if ok:
            await query.answer(f"🎉 Места расширены до {clan['max_members']+15} ({msg_info})!", show_alert=True)
            await show_clan_profile_handler(query, clan_id, context)
        else:
            await query.answer(f"❌ {msg_info}", show_alert=True)
        return

    if data.startswith("clan_requests:"):
        await query.answer()
        clan_id = int(data.split(":")[1])
        reqs = get_clan_requests(clan_id)
        text = f"📩 <b>Заявки в клан ({len(reqs)}):</b>\n\n"
        buttons = []

        for r in reqs:
            name = normalize_telegram_name(r["first_name"], r["username"], r["user_id"])
            buttons.append([
                make_btn(f"✅ Принять {name[:10]}", style="success", callback_data=f"clan_req_accept:{clan_id}:{r['user_id']}"),
                make_btn("❌ Отклонить", style="danger", callback_data=f"clan_req_decline:{clan_id}:{r['user_id']}")
            ])

        buttons.append([InlineKeyboardButton("⬅️ В профиль клана", callback_data=f"clan_info:{clan_id}")])
        kb = InlineKeyboardMarkup(buttons)
        if query.message.photo:
            await query.message.delete()
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    if data.startswith("clan_req_accept:"):
        _, clan_id, req_user_id = data.split(":")
        if add_user_to_clan(int(req_user_id), int(clan_id)):
            await query.answer("Игрок принят в клан!")
        else:
            await query.answer("Нет свободных мест!", show_alert=True)
        await show_clan_profile_handler(query, int(clan_id), context)
        return

    if data.startswith("clan_req_decline:"):
        _, clan_id, req_user_id = data.split(":")
        remove_clan_request(int(clan_id), int(req_user_id))
        await query.answer("Заявка отклонена.")
        await show_clan_profile_handler(query, int(clan_id), context)
        return

    if data.startswith("toggle_set:"):
        await query.answer()
        field = data.split(":", 1)[1]
        toggle_user_setting(user.id, field)
        await show_settings_page(query, user.id)
        return

    if data.startswith("buy_slots:"):
        _, slots_str, cost_str = data.split(":")
        slots, cost = int(slots_str), int(cost_str)
        if upgrade_inventory_capacity(user.id, cost, slots):
            await query.answer(f"✅ Куплено +{slots} слотов!", show_alert=True)
            await show_shop_page(query, user.id)
        else:
            await query.answer("❌ Недостаточно Stars!", show_alert=True)
        return

    if data == "sell_all_confirm":
        await query.answer()
        kb = InlineKeyboardMarkup([
            [
                make_btn("✅ Продать все", style="success", callback_data="sell_all_do"),
                make_btn("❌ Отмена", style="danger", callback_data="nav_collection_page:1"),
            ]
        ])
        await query.edit_message_text("⚠️ <b>Продать все обычные предметы из коллекции?</b>\nИзбранные (⭐) затронуты не будут.", parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    if data == "sell_all_do":
        count, stars = sell_all_non_favorites(user.id)
        await query.answer(f"💰 Продано {count} предметов за {stars:,} Stars!", show_alert=True)
        await show_collection_page(query, user.id, 1)
        return

    if data in ("nav_bonus", "bonus_claim_daily", "bonus_claim_promo"):
        tg_user = user
        full_name = f"{getattr(tg_user, 'first_name', '') or ''} {getattr(tg_user, 'last_name', '') or ''}".strip()
        bio_text = ""
        try:
            chat_info = await context.bot.get_chat(user.id)
            if chat_info:
                c_fn = f"{getattr(chat_info, 'first_name', '') or ''} {getattr(chat_info, 'last_name', '') or ''}".strip()
                if c_fn:
                    full_name = c_fn
                bio_text = (getattr(chat_info, "bio", "") or "").strip()
        except Exception:
            pass

        tag_needle = PROMO_BONUS_BOT_USERNAME.lstrip("@").lower()
        has_name_tag = tag_needle in full_name.lower()
        has_bio_tag = tag_needle in bio_text.lower()

        banner_note = ""
        if data == "bonus_claim_daily":
            rem_daily = claim_daily_bonus(user.id)
            if rem_daily is None:
                await query.answer("🎁 +50 ⭐ и +250 XP начислены!", show_alert=True)
                banner_note = f"{ce('check')} <b>Ежедневный бонус получен:</b> +50 {ce('star')} и +250 {ce('bolt')} XP!\n\n"
            else:
                await query.answer(f"⏳ Доступно через {seconds_to_hms(rem_daily)}", show_alert=True)
                banner_note = f"{ce('hourglass')} Ежедневный бонус уже получен. Следующий через <b>{seconds_to_hms(rem_daily)}</b>.\n\n"
        elif data == "bonus_claim_promo":
            if not has_name_tag and not has_bio_tag:
                await query.answer(
                    f"❌ Добавьте {PROMO_BONUS_BOT_USERNAME} в имя или описание профиля Telegram!",
                    show_alert=True,
                )
                banner_note = (
                    f"{ce('cross')} В вашем профиле пока не найден <code>{PROMO_BONUS_BOT_USERNAME}</code>.\n"
                    f"Поставьте <code>{PROMO_BONUS_BOT_USERNAME}</code> в имя и/или описание Telegram-профиля и нажмите проверку снова!\n\n"
                )
            else:
                res_p = claim_promo_profile_bonus_db(user.id, has_name_tag, has_bio_tag)
                if res_p["awarded_stars"] > 0 or res_p["awarded_cases"] > 0:
                    await query.answer(
                        f"🎉 +{res_p['awarded_stars']:,} ⭐ и +{res_p['awarded_cases']} кейс(а) за 10,000⭐!",
                        show_alert=True,
                    )
                    banner_note = (
                        f"{ce('boom')} <b>Промо-бонус получен!</b> "
                        f"+<b>{res_p['awarded_stars']:,} {ce('star')}</b> и "
                        f"+<b>{res_p['awarded_cases']}</b> бесплатный кейс за 10,000 ⭐!\n\n"
                    )
                else:
                    parts_cd = []
                    if has_name_tag and res_p["name_left"] > 0:
                        parts_cd.append(f"имя: {seconds_to_hms(res_p['name_left'])}")
                    if has_bio_tag and res_p["bio_left"] > 0:
                        parts_cd.append(f"описание: {seconds_to_hms(res_p['bio_left'])}")
                    cd_txt = ", ".join(parts_cd) or "менее 24ч"
                    await query.answer(f"⏳ Бонус за профиль уже забран ({cd_txt})", show_alert=True)
                    banner_note = f"{ce('hourglass')} Бонус за профиль уже получен сегодня ({cd_txt}).\n\n"
        else:
            await query.answer()

        bst = get_bonus_status_db(user.id)
        db_u = get_user_row_raw(user.id)
        st_ts = int(db_u["start_timer_ts"] or 0) if db_u and "start_timer_ts" in db_u.keys() else 0
        lst_ts = int(db_u["last_start_ts"] or 0) if db_u and "last_start_ts" in db_u.keys() else 0
        now_ts = int(time.time())
        if st_ts > 0:
            cycle_left = (24 * 3600) - ((now_ts - st_ts) % (24 * 3600))
            timer_note = (
                f"\n{ce('hourglass')} <b>Таймер /start:</b> синхронизирован "
                f"({seconds_to_hms(max(0, now_ts - lst_ts))} с последнего /start • цикл: {seconds_to_hms(cycle_left)})"
            )
        else:
            timer_note = f"\n{ce('hourglass')} <b>Таймер /start:</b> не синхронизирован (нажмите /start)"

        daily_state = (
            f"{ce('green_dot')} Доступен сейчас!"
            if bst["daily_left"] == 0
            else f"{ce('hourglass')} Через {seconds_to_hms(bst['daily_left'])}"
        )
        name_tag_icon = ce("check") if has_name_tag else ce("cross")
        bio_tag_icon = ce("check") if has_bio_tag else ce("cross")
        name_cd = (
            "готов к получению" if (has_name_tag and bst["name_left"] == 0)
            else (f"через {seconds_to_hms(bst['name_left'])}" if bst["name_left"] > 0 else "не добавлен")
        )
        bio_cd = (
            "готов к получению" if (has_bio_tag and bst["bio_left"] == 0)
            else (f"через {seconds_to_hms(bst['bio_left'])}" if bst["bio_left"] > 0 else "не добавлен")
        )
        free_cases = bst["free_10k_cases"]

        text = (
            f"{ce('fire')} <b>Бонусы и Ежедневные Награды</b>\n"
            "━━━━━━━━━━━━\n"
            f"{banner_note}"
            f"{ce_gift(0)} <b>Ежедневный бонус (24ч):</b> +50 {ce('star')} и +250 XP\n"
            f"• Статус: <b>{daily_state}</b>\n\n"
            f"{ce('sparkles')} <b>Ежедневный бонус за {PROMO_BONUS_BOT_USERNAME}:</b>\n"
            f"• {PROMO_BONUS_BOT_USERNAME} в <b>имени профиля</b>: <b>+50,000 {ce('star')} + 1 кейс за 10,000⭐</b> / день\n"
            f"• {PROMO_BONUS_BOT_USERNAME} в <b>описании (Bio)</b>: <b>+50,000 {ce('star')} + 1 кейс за 10,000⭐</b> / день\n"
            f"• И в <b>имени</b>, и в <b>описании</b>: <b>+100,000 {ce('star')} + 2 кейса за 10,000⭐</b> / день!\n\n"
            f"{ce('gear')} <b>Проверка вашего Telegram-профиля:</b>\n"
            f"• В имени ({name_tag_icon}): <b>{name_cd}</b>\n"
            f"• В описании ({bio_tag_icon}): <b>{bio_cd}</b>\n"
            f"• Бесплатных кейсов за 10,000⭐: <b>{free_cases:,} шт.</b>"
            f"{timer_note}"
        )

        btns = [
            [
                make_btn(
                    "Забрать 24ч (+50⭐)" if bst["daily_left"] == 0 else f"24ч бонус ({seconds_to_hms(bst['daily_left'])})",
                    style="success" if bst["daily_left"] == 0 else None,
                    emoji_key="star",
                    callback_data="bonus_claim_daily",
                )
            ],
            [
                make_btn(
                    f"Забрать бонус за {PROMO_BONUS_BOT_USERNAME}",
                    style="primary",
                    emoji_key="sparkles",
                    callback_data="bonus_claim_promo",
                )
            ],
        ]
        if free_cases > 0:
            btns.append([
                make_btn(
                    f"Открыть бесплатный кейс 10,000⭐ ({free_cases} шт.)",
                    style="success",
                    emoji_key="game",
                    callback_data=f"open_case:{PROMO_BONUS_CASE_KEY}",
                )
            ])
        btns.append([
            make_btn("В коллекцию", emoji_key="bookmark", callback_data="nav_collection_page:1"),
            make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main"),
        ])
        await safe_edit_or_reply(query, text, reply_markup=InlineKeyboardMarkup(btns))
        return

    if data == "nav_cases_hub":
        await query.answer()
        db_user = get_or_create_user(user.id, "", "")
        free_10k = max(0, int(db_user["free_10k_cases"] or 0)) if "free_10k_cases" in db_user.keys() else 0
        tier_lines = []
        tier_buttons = []
        for idx_t, (tkey, tinfo) in enumerate(CASE_TIERS.items(), start=1):
            is_free_tier = (tkey == PROMO_BONUS_CASE_KEY and free_10k > 0)
            price_note = f"<b>БЕСПЛАТНО (доступно {free_10k} шт.)</b>" if is_free_tier else f"<b>{tinfo['price']:,} ⭐</b>"
            tier_lines.append(
                f"{idx_t}. <b>{tinfo['name']}</b> — {price_note}\n"
                f"   <i>{tinfo['desc']}</i>"
            )
            btn_style = "success" if (tinfo.get("rolls_buffs") or is_free_tier) else ("primary" if tinfo["price"] >= 10_000 else None)
            btn_eid = CUSTOM_PEPE_EMOJI_IDS[0] if tkey == "farm_plus" else (CE_IDS["gem"] if tinfo.get("rolls_buffs") else CE_IDS["game"])
            btn_label = f"{tinfo['name']} (БЕСПЛАТНО • {free_10k} шт.)" if is_free_tier else f"{tinfo['name']} ({tinfo['price']:,}⭐)"
            tier_buttons.append([
                make_btn(
                    btn_label,
                    style=btn_style,
                    emoji_id=btn_eid,
                    callback_data=f"open_case:{tkey}",
                )
            ])
        tier_buttons.append([
            make_btn("Коллекция", emoji_key="bookmark", callback_data="nav_collection_page:1"),
            make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")
        ])

        free_line = f"\n{ce('sparkles')} Бесплатных кейсов за 10,000⭐: <b>{free_10k:,} шт.</b>" if free_10k > 0 else ""
        text = (
            f"{ce('game')} <b>Mystery Cases Hub</b>\n"
            "━━━━━━━━━━━━\n"
            f"{ce('dollar')} Ваш баланс: <b>{fmt_stars_rub(db_user['balance_stars'])}</b>{free_line}\n\n"
            + "\n".join(tier_lines)
            + "\n\n<blockquote expandable>"
            f"{ce('sparkles')} <b>О баффах в кейсе 1,000,000 {ce('star')}:</b>\n"
            "• Улучшаемые NFT (<b>Plush Pepe</b>, <b>Heart Locket</b>, <b>Algorithm Cup</b>, <b>Durov's Cap</b> и <b>Bonded Ring</b>), выпавшие из элитного кейса <b>💎 Elite Buff Case</b>, получают <b>1–2 случайных баффа</b>:\n"
            f"  {ce('bulb')} Бафф на шанс редкого фона (+20%..+100%)\n"
            f"  {ce('sparkles')} Бафф на шанс редкой модели (+20%..+100%)\n"
            f"  {ce('gem')} Бафф на стоимость после улучшения (+10%..+50%)"
            "</blockquote>"
        )
        kb = InlineKeyboardMarkup(tier_buttons)
        await safe_edit_or_reply(query, text, reply_markup=kb)
        return

    if data.startswith("open_case:"):
        tier_key = data.split(":")[1]
        tier = CASE_TIERS.get(tier_key)
        if not tier:
            await query.answer()
            return

        db_user = get_or_create_user(user.id, "", "")
        opened_tot, captcha_pending = get_user_case_captcha_state(user.id)
        if captcha_pending:
            await query.answer("🤖 Подтвердите, что вы человек!", show_alert=True)
            cap_kb = InlineKeyboardMarkup([
                [make_btn("Я человек", style="success", emoji_key="check", callback_data=f"case_captcha_ok:{tier_key}")],
                [make_btn("К кейсам", emoji_key="game", callback_data="nav_cases_hub")],
            ])
            await safe_edit_or_reply(
                query,
                (
                    f"{ce('warn')} <b>Проверка активности</b>\n"
                    "━━━━━━━━━━━━\n"
                    f"Вы открыли уже <b>{opened_tot:,}</b> кейсов.\n"
                    "Нажмите кнопку <b>«Я человек»</b> ниже, чтобы продолжить открывать кейсы!"
                ),
                reply_markup=cap_kb,
            )
            return

        used_free_case = False
        if tier_key == PROMO_BONUS_CASE_KEY and use_free_10k_case_db(user.id):
            used_free_case = True
        else:
            if not deduct_user_stars(user.id, tier["price"]):
                await query.answer(f"❌ Недостаточно Stars! Цена: {tier['price']:,}⭐", show_alert=True)
                return
            record_star_flow(spent=int(tier["price"]), burned=int(tier["price"]), purchased=int(tier["price"]))

        await query.answer()
        clan = get_user_clan(user.id)
        clan_bonus_pct = 0.0
        if clan:
            _, _, _, _, clan_bonus_pct = calculate_clan_level_info(clan["xp"])

        won_gift = roll_case_gift(tier, clan_bonus_pct=clan_bonus_pct)

        b_bg, b_mdl, b_val = 0, 0, 0
        if tier.get("rolls_buffs") and won_gift.key in UPGRADABLE_GIFT_KEYS:
            b_bg, b_mdl, b_val = roll_item_buffs()

        if db_user["auto_sell"]:
            add_user_stars(user.id, won_gift.stars)
            res_note = f"{ce('money_wings')} <b>Авто-продажа:</b> +{fmt_stars_rub(won_gift.stars)}!"
        else:
            success = add_to_collection(
                user.id,
                won_gift.key,
                buff_backdrop_pct=b_bg,
                buff_model_pct=b_mdl,
                buff_value_pct=b_val,
            )
            if not success:
                add_user_stars(user.id, won_gift.stars)
                res_note = f"{ce('warn')} Инвентарь переполнен! Авто-продажа за {fmt_stars_rub(won_gift.stars)}."
            else:
                res_note = f"{ce('check')} Сохранено в коллекцию! (+{won_gift.xp} XP)"

        new_total_cases, captcha_triggered = record_case_opened_check_captcha_db(user.id)

        buff_lines = format_buffs_lines({
            "buff_backdrop_pct": b_bg,
            "buff_model_pct": b_mdl,
            "buff_value_pct": b_val,
        })
        buff_note = (
            f"\n\n{ce('bolt')} <b>ВЫПАЛИ БАФФЫ НА УЛУЧШЕНИЕ:</b>\n"
            + "\n".join(f"• {ce('sparkles')} {ln}" for ln in buff_lines)
            if buff_lines else ""
        )
        captcha_note = (
            f"\n\n{ce('warn')} Открыто <b>{new_total_cases:,}</b> кейсов — нажмите <b>«Я человек»</b>, чтобы продолжить!"
            if captcha_triggered else ""
        )

        rem_free_10k = get_bonus_status_db(user.id)["free_10k_cases"] if tier_key == PROMO_BONUS_CASE_KEY else 0
        free_used_note = (
            f"{ce('sparkles')} Использован бесплатный бонусный кейс (осталось: <b>{rem_free_10k} шт.</b>)\n"
            if used_free_case else ""
        )
        g_ce = gift_tg_emoji(won_gift.key)
        cap = (
            f"{ce('game')} <b>Открытие {tier['name']}!</b>\n"
            f"━━━━━━━━━━━━\n"
            f"{free_used_note}"
            f"{g_ce} Выпал: <b>{won_gift.name}</b>!\n"
            f"• Модель: <b>{won_gift.model_name}</b>\n"
            f"• Ценность: <b>{fmt_stars_rub(won_gift.stars)}</b>{buff_note}\n\n"
            f"{res_note}{captcha_note}"
        )

        if captcha_triggered:
            primary_btn = make_btn("Я человек", style="success", emoji_key="check", callback_data=f"case_captcha_ok:{tier_key}")
        elif tier_key == PROMO_BONUS_CASE_KEY and rem_free_10k > 0:
            primary_btn = make_btn(f"Еще раз (Бесплатно • {rem_free_10k} шт.)", style="success", emoji_key="refresh", callback_data=f"open_case:{tier_key}")
        else:
            primary_btn = make_btn(f"Еще раз ({tier['price']:,}⭐)", style="success", emoji_key="refresh", callback_data=f"open_case:{tier_key}")

        kb = InlineKeyboardMarkup([
            [primary_btn],
            [make_btn("К кейсам", emoji_key="game", callback_data="nav_cases_hub")],
            [make_btn("В коллекцию", emoji_key="bookmark", callback_data="nav_collection_page:1")],
            [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")],
        ])

        try:
            card_io = await generate_gift_card_image(won_gift)
            if card_io:
                await query.message.reply_photo(photo=InputFile(card_io, filename=f"gift_{won_gift.key}.png"), caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
                if query.message: await query.message.delete()
                return
        except Exception: pass

        img_p = gift_image_path(won_gift.key)
        if img_p:
            try:
                with open(img_p, "rb") as f:
                    await query.message.reply_photo(photo=InputFile(f, filename=img_p.name), caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
                if query.message: await query.message.delete()
                return
            except Exception: pass

        await query.message.reply_text(cap, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    if ":" in data:
        action, *rest = data.split(":")

        if action in ("keep", "sell"):
            drop_id = int(rest[0])
            drop = get_pending_drop(drop_id)
            if not drop or drop["user_id"] != user.id:
                await query.answer("❌ Это не ваш подарок!", show_alert=True)
                return
            if drop["resolved"]:
                await query.answer("⚠️ Уже обработано!", show_alert=True)
                return

            await query.answer()
            gift = GIFTS_BY_KEY.get(drop["gift_key"])
            resolve_pending_drop(drop_id)

            if action == "keep":
                added = add_to_collection(user.id, gift.key)
                if added:
                    res = f"{ce('check')} <b>{gift.name}</b> сохранён в коллекцию! (+{gift.xp} XP)"
                else:
                    sell_from_pending(user.id, gift.key, gift.stars)
                    res = f"{ce('warn')} Инвентарь переполнен! <b>{gift.name}</b> продан за {fmt_stars_rub(gift.stars)}!"
            else:
                sell_from_pending(user.id, gift.key, gift.stars)
                res = f"{ce('money_wings')} Продано <b>{gift.name}</b> за {fmt_stars_rub(gift.stars)}! (+{gift.xp // 2} XP)"

            kb = quick_nav_keyboard()
            if query.message.photo:
                await query.edit_message_caption(caption=res, parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await query.edit_message_text(res, parse_mode=ParseMode.HTML, reply_markup=kb)
            return

        if action == "view_top_user":
            target_id = int(rest[0])
            back_page = int(rest[1])
            target = get_or_create_user(target_id, "", "")

            if target["hide_top"] and user.id not in ADMIN_IDS:
                await query.answer("🔒 Профиль скрыт настройками приватности игрока.", show_alert=True)
                return

            await query.answer()
            await show_profile_handler(query, target_id, context, back_to_top_page=back_page)
            return

        if action == "view_item":
            item_id = int(rest[0])
            page = int(rest[1]) if len(rest) > 1 else 1
            item = get_collection_item(item_id)
            if not item or item["user_id"] != user.id:
                await query.answer("Предмет не найден.", show_alert=True)
                return

            await query.answer()
            g = GIFTS_BY_KEY.get(item["gift_key"])
            fav_text = "Убрать из Избранного" if item["is_favorite"] else "В избранное"
            fav_emoji = "cross" if item["is_favorite"] else "star"
            val_stars = get_item_display_value(item)
            item_buff_badge = format_buffs_compact(item)
            item_buff_lines = format_buffs_lines(item)
            item_buffs_block = (
                f"\n{ce('bolt')} <b>Баффы предмета:</b>\n" + "\n".join(f"• {ce('sparkles')} {ln}" for ln in item_buff_lines)
                if item_buff_lines else ""
            )

            if item["is_upgraded"]:
                gift_key = item["gift_key"] or "pepe_heart"
                g_title = get_upgraded_gift_title(gift_key)
                g_emoji = get_upgraded_gift_emoji(gift_key)
                m = get_model_def(gift_key, item["model_name"])
                b = BACKDROPS_BY_KEY.get(item["backdrop_key"]) or PLUSHPEPE_BACKDROPS[0]
                is_mono, mono_fam = get_monochrome_combo_info(m.name, b.key)
                card_io = await generate_upgraded_gift_image(
                    m, b, item["upgrade_num"], val_stars, gift_key=gift_key, buff_badge=item_buff_badge
                )

                buttons = []
                if item["is_listed"]:
                    active_lot = get_active_listing_by_collection_id(item_id)
                    if active_lot:
                        bot_username = await get_bot_username(context.bot)
                        lot_link = f"https://t.me/{bot_username}?start=lot_{active_lot['id']}"
                        up_num_val = item["upgrade_num"]
                        lot_price_txt = fmt_stars_compact(active_lot["price_stars"])
                        share_text = f"{g_emoji} {g_title} #{up_num_val} на NFT Маркете за {lot_price_txt} ⭐!"
                        share_url = (
                            f"https://t.me/share/url?url={urllib.parse.quote(lot_link)}"
                            f"&text={urllib.parse.quote(share_text)}"
                        )
                        buttons.append([make_btn(f"Открыть лот #{active_lot['id']}", style="primary", emoji_key="eyes", callback_data=f"market_lot:{active_lot['id']}")])
                        buttons.append([make_btn("Поделиться подарком", style="primary", emoji_key="link", url=share_url)])
                    buttons.append([make_btn("В мои лоты маркета", emoji_key="search", callback_data="market_my_offers")])
                else:
                    buttons.append([make_btn("Выставить на маркет", style="primary", emoji_key="exchange", callback_data=f"market_sell_start:{item_id}")])
                    buttons.append([make_btn("Передать бесплатно", emoji_id=CUSTOM_GIFT_EMOJI_IDS[2], callback_data=f"gift_transfer_start:{item_id}")])
                    buttons.append([make_btn(fav_text, emoji_key=fav_emoji, callback_data=f"toggle_fav:{item_id}:{page}")])
                buttons.append([
                    make_btn("Назад в коллекцию", emoji_key="bookmark", callback_data=f"nav_collection_page:{page}"),
                    make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")
                ])
                kb = InlineKeyboardMarkup(buttons)

                status_str = "Выставлен на маркете" if item["is_listed"] else "В коллекции"
                g_ce = upgraded_gift_tg_emoji(gift_key)
                mono_line = f"\n{ce('rainbow')} Комбо: <b>MONOCHROME x6</b> ({COLOR_FAMILY_RU.get(mono_fam, mono_fam)})" if is_mono else ""
                cap = (
                    f"{ce('sparkles')} <b>{g_title} #{item['upgrade_num']}</b>\n"
                    f"━━━━━━━━━━━━\n"
                    f"{g_ce} Модель: <b>{clean_html(m.name)}</b> (шанс {m.chance_pct}%)\n"
                    f"{ce('sparkles')} Фон: <b>{clean_html(b.name)}</b> • <i>{b.rarity_label}</i> ({b.chance_pct}%){mono_line}{item_buffs_block}\n"
                    f"{ce('gem')} Оценочная ценность: {fmt_stars_rub(val_stars)}\n"
                    f"{ce('pin')} Статус: <b>{status_str}</b>\n"
                    f"{ce('star')} В Избранном: <b>{'Да' if item['is_favorite'] else 'Нет'}</b>\n"
                    f"━━━━━━━━━━━━\n"
                    f"<blockquote expandable>"
                    f"{ce('thought')} <b>Аннотация коллекционного NFT:</b>\n"
                    f"• Улучшенные NFT нельзя продать боту — они доступны только для P2P-торговли на <b>NFT Маркете</b> и бесплатной передачи игрокам."
                    f"</blockquote>"
                )
                try:
                    await query.message.reply_photo(
                        photo=InputFile(card_io, filename=f"upgraded_{gift_key}_{item['upgrade_num']}.png"),
                        caption=cap,
                        parse_mode=ParseMode.HTML,
                        reply_markup=kb,
                    )
                    await query.message.delete()
                    return
                except Exception:
                    pass
                await query.edit_message_text(cap, parse_mode=ParseMode.HTML, reply_markup=kb)
                return

            if item["gift_key"] == "scared_cat":
                ed_n = int(item["edition_num"] or item["id"])
                buttons = []
                if item["is_listed"]:
                    active_lot = get_active_listing_by_collection_id(item_id)
                    if active_lot:
                        bot_username = await get_bot_username(context.bot)
                        lot_link = f"https://t.me/{bot_username}?start=lot_{active_lot['id']}"
                        lot_price_txt = fmt_stars_compact(active_lot["price_stars"])
                        share_text = f"🙀 Scared Cat #{ed_n}/{SCARED_CAT_MAX_SUPPLY} на NFT Маркете за {lot_price_txt} ⭐!"
                        share_url = (
                            f"https://t.me/share/url?url={urllib.parse.quote(lot_link)}"
                            f"&text={urllib.parse.quote(share_text)}"
                        )
                        buttons.append([make_btn(f"Открыть лот #{active_lot['id']}", style="primary", emoji_key="eyes", callback_data=f"market_lot:{active_lot['id']}")])
                        buttons.append([make_btn("Поделиться подарком", style="primary", emoji_key="link", url=share_url)])
                    buttons.append([make_btn("В мои лоты маркета", emoji_key="search", callback_data="market_my_offers")])
                else:
                    buttons.append([make_btn("Выставить на маркет", style="primary", emoji_key="exchange", callback_data=f"market_sell_start:{item_id}")])
                    buttons.append([make_btn("Передать бесплатно", emoji_id=CUSTOM_GIFT_EMOJI_IDS[2], callback_data=f"gift_transfer_start:{item_id}")])
                    buttons.append([make_btn(fav_text, emoji_key=fav_emoji, callback_data=f"toggle_fav:{item_id}:{page}")])
                buttons.append([
                    make_btn("Назад в коллекцию", emoji_key="bookmark", callback_data=f"nav_collection_page:{page}"),
                    make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main"),
                ])
                kb = InlineKeyboardMarkup(buttons)
                status_str = "Выставлен на маркете" if item["is_listed"] else "В коллекции"
                cap = (
                    f"{ce('fire')} <b>Scared Cat #{ed_n}/{SCARED_CAT_MAX_SUPPLY}</b>\n"
                    f"━━━━━━━━━━━━\n"
                    f"• Тип: <b>Уникальный коллекционный NFT</b>\n"
                    f"• {ce('gem')} Базовая ценность: {fmt_stars_rub(SCARED_CAT_DEF.stars)}\n"
                    f"• {ce('pin')} Статус: <b>{status_str}</b>\n"
                    f"• {ce('star')} В Избранном: <b>{'Да' if item['is_favorite'] else 'Нет'}</b>\n"
                    f"━━━━━━━━━━━━\n"
                    f"<blockquote expandable>"
                    f"{ce('thought')} <b>Аннотация лимитированного NFT:</b>\n"
                    f"• Уникальный <b>Scared Cat</b> (всего {SCARED_CAT_MAX_SUPPLY:,} шт.) нельзя продать боту — он доступен для P2P-торговли на <b>NFT Маркете</b> без улучшений и бесплатной передачи игрокам."
                    f"</blockquote>"
                )
                try:
                    card_io = await generate_gift_card_image(SCARED_CAT_DEF)
                    if card_io:
                        await query.message.reply_photo(photo=InputFile(card_io, filename=f"scared_cat_{ed_n}.png"), caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
                        await query.message.delete()
                        return
                except Exception:
                    pass
                img_p = gift_image_path("scared_cat")
                if img_p:
                    try:
                        with open(img_p, "rb") as f:
                            await query.message.reply_photo(photo=InputFile(f, filename=img_p.name), caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
                        await query.message.delete()
                        return
                    except Exception:
                        pass
                await safe_edit_or_reply(query, cap, reply_markup=kb)
                return

            buttons = []
            g_canon = canonical_gift_key(g.key) if g else ""
            if g and g_canon in UPGRADABLE_GIFT_KEYS:
                u_cost = get_upgrade_cost(g_canon)
                if g_canon == "pepe_heart":
                    btn_eid = CUSTOM_PEPE_EMOJI_IDS[0]
                elif g_canon == "cap_tg":
                    btn_eid = CE_IDS["crown"]
                elif g_canon == "trophy_cup":
                    btn_eid = CE_IDS["gold"]
                else:
                    btn_eid = CE_IDS["gem"]
                buttons.append([make_btn(f"Улучшить ({u_cost:,} ⭐)", style="primary", emoji_id=btn_eid, callback_data=f"upgrade_item:{item_id}")])
            buttons.append([make_btn("Передать бесплатно", emoji_id=CUSTOM_GIFT_EMOJI_IDS[3], callback_data=f"gift_transfer_start:{item_id}")])
            buttons.append([make_btn(fav_text, emoji_key=fav_emoji, callback_data=f"toggle_fav:{item_id}:{page}")])
            buttons.append([make_btn(f"Продать за {fmt_stars_compact(g.stars)} Stars", emoji_key="money_wings", callback_data=f"sell_item:{item_id}:{page}")])
            buttons.append([
                make_btn("Назад в коллекцию", emoji_key="bookmark", callback_data=f"nav_collection_page:{page}"),
                make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")
            ])
            kb = InlineKeyboardMarkup(buttons)

            g_ce = gift_tg_emoji(g.key)
            cap = (
                f"{g_ce} <b>{g.name}</b>\n"
                f"━━━━━━━━━━━━\n"
                f"• Модель: <b>{g.model_name}</b>\n"
                f"• {ce('bolt')} Бонус опыта: <b>+{g.xp} XP</b>\n"
                f"• {ce('dollar')} Стоимость: {fmt_stars_rub(g.stars)}\n"
                f"• {ce('star')} В Избранном: <b>{'Да' if item['is_favorite'] else 'Нет'}</b>{item_buffs_block}\n"
                f"━━━━━━━━━━━━"
            )

            try:
                card_io = await generate_gift_card_image(g)
                if card_io:
                    await query.message.reply_photo(photo=InputFile(card_io, filename=f"gift_{g.key}.png"), caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
                    await query.message.delete()
                    return
            except Exception: pass

            img_p = gift_image_path(g.key)
            if img_p:
                try:
                    with open(img_p, "rb") as f:
                        await query.message.reply_photo(photo=InputFile(f, filename=img_p.name), caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
                    await query.message.delete()
                    return
                except Exception: pass

            await query.edit_message_text(cap, parse_mode=ParseMode.HTML, reply_markup=kb)
            return

        if action == "toggle_fav":
            item_id = int(rest[0])
            page = int(rest[1]) if len(rest) > 1 else 1
            if toggle_favorite(item_id, user.id):
                await query.answer("Избранное обновлено!")
                await show_collection_page(query, user.id, page)
            else:
                await query.answer("Максимум 7 предметов в Избранном!", show_alert=True)
            return

        if action == "sell_item":
            item_id = int(rest[0])
            page = int(rest[1]) if len(rest) > 1 else 1
            item = get_collection_item(item_id)
            if not item or item["user_id"] != user.id:
                await query.answer("Ошибка продажи.", show_alert=True)
                return
            if item["is_listed"]:
                await query.answer("❌ Сначала снимите подарок с маркета!", show_alert=True)
                return
            if item["gift_key"] == "scared_cat":
                await query.answer("❌ Уникальный Scared Cat нельзя продать боту — выставьте его на NFT Маркет!", show_alert=True)
                return
            if item["is_upgraded"]:
                await query.answer("❌ Улучшенные NFT нельзя продавать боту — их можно продать только на NFT Маркете!", show_alert=True)
                return

            val_stars = get_item_display_value(item)
            remove_from_collection(item_id, user.id)
            add_user_stars(user.id, val_stars)

            await query.answer(f"💰 Продано за {fmt_stars_compact(val_stars)} Stars!", show_alert=True)
            await show_collection_page(query, user.id, page)
            return

    # Режимы игры и Баттлы (Case Battles)
    if data == "nav_modes":
        await query.answer()
        await show_modes_hub(query, user.id)
        return

    if data.startswith("battles_list:"):
        await query.answer()
        p_s = data.split(":", 1)[1]
        page = int(p_s) if p_s.isdigit() else 1
        await show_battles_list(query, user.id, page=page)
        return

    if data == "btl_create_start":
        await query.answer()
        context.user_data["battle_draft"] = {"cases": [], "max_players": 2}
        await show_battle_create_cases(query, user.id, context)
        return

    if data.startswith("btl_add:"):
        tkey = data.split(":", 1)[1]
        if tkey not in CASE_TIERS:
            await query.answer("❌ Неизвестный кейс.", show_alert=True)
            return
        draft = context.user_data.setdefault("battle_draft", {"cases": [], "max_players": 2})
        if len(draft["cases"]) >= BATTLE_MAX_CASES:
            await query.answer(f"⚠️ Максимум {BATTLE_MAX_CASES} кейсов в одном баттле!", show_alert=True)
            return
        draft["cases"].append(tkey)
        await query.answer(f"➕ {CASE_TIERS[tkey]['name']} ({len(draft['cases'])}/{BATTLE_MAX_CASES})")
        await show_battle_create_cases(query, user.id, context)
        return

    if data == "btl_pop_case":
        draft = context.user_data.setdefault("battle_draft", {"cases": [], "max_players": 2})
        if not draft["cases"]:
            await query.answer("Список кейсов пуст!")
            return
        draft["cases"].pop()
        await query.answer("↩️ Последний кейс убран")
        await show_battle_create_cases(query, user.id, context)
        return

    if data == "btl_clear_cases":
        draft = context.user_data.setdefault("battle_draft", {"cases": [], "max_players": 2})
        draft["cases"].clear()
        await query.answer("🗑 Список кейсов очищен")
        await show_battle_create_cases(query, user.id, context)
        return

    if data == "btl_cases_next":
        draft = context.user_data.get("battle_draft") or {"cases": [], "max_players": 2}
        if not draft.get("cases"):
            await query.answer(f"⚠️ Выберите от {BATTLE_MIN_CASES} до {BATTLE_MAX_CASES} кейсов!", show_alert=True)
            return
        await query.answer()
        await show_battle_create_players(query, user.id, context)
        return

    if data == "btl_edit_cases":
        await query.answer()
        context.user_data.setdefault("battle_draft", {"cases": [], "max_players": 2})
        await show_battle_create_cases(query, user.id, context)
        return

    if data.startswith("btl_players:"):
        n_s = data.split(":", 1)[1]
        if n_s.isdigit():
            n_val = max(BATTLE_MIN_PLAYERS, min(BATTLE_MAX_PLAYERS, int(n_s)))
            draft = context.user_data.setdefault("battle_draft", {"cases": [], "max_players": 2})
            draft["max_players"] = n_val
            await query.answer(f"Участников: {n_val}")
            await show_battle_create_players(query, user.id, context)
        return

    if data == "btl_launch":
        draft = context.user_data.get("battle_draft")
        if not draft or not draft.get("cases"):
            await query.answer("⚠️ Сначала выберите кейсы для баттла!", show_alert=True)
            await show_battle_create_cases(query, user.id, context)
            return
        case_keys = list(draft["cases"])
        max_p = max(BATTLE_MIN_PLAYERS, min(BATTLE_MAX_PLAYERS, int(draft.get("max_players", 2))))
        ok, res_code, detail = create_case_battle_db(user.id, case_keys, max_p)
        if not ok or not detail:
            await query.answer(f"❌ {res_code}", show_alert=True)
            return
        context.user_data.pop("battle_draft", None)
        b_id = int(detail["id"])
        if res_code == "SOLO_COUNTDOWN":
            await query.answer(f"🚀 Соло-баттл #{b_id} создан! Таймер {BATTLE_COUNTDOWN_SECONDS} сек...")
        else:
            await query.answer(f"✅ Баттл #{b_id} создан! Ожидаем игроков...")
        await show_battle_room(query, user.id, b_id, context.bot)
        if res_code == "SOLO_COUNTDOWN":
            _ensure_battle_task(context.bot, b_id)
        return

    if data.startswith("battle_view:"):
        b_s = data.split(":", 1)[1]
        if b_s.isdigit():
            await query.answer()
            await show_battle_room(query, user.id, int(b_s), context.bot)
        return

    if data.startswith("battle_join:"):
        b_s = data.split(":", 1)[1]
        if not b_s.isdigit():
            return
        b_id = int(b_s)
        ok, res_code, detail = join_case_battle_db(b_id, user.id)
        if not ok or not detail:
            await query.answer(f"❌ {res_code}", show_alert=True)
            return
        if res_code == "FULL_COUNTDOWN":
            await query.answer(f"🔥 Лобби заполнено! Старт через {BATTLE_COUNTDOWN_SECONDS} сек!")
        else:
            await query.answer("✅ Вы вступили в баттл!")
        await show_battle_room(query, user.id, b_id, context.bot)
        # Уведомляем остальных участников и запускаем обратный отсчёт, если все места заняты
        await _broadcast_battle_room(context.bot, b_id, skip_user_id=user.id)
        if res_code == "FULL_COUNTDOWN":
            for p in detail["participants"]:
                p_uid = int(p["user_id"])
                if p_uid != user.id and not p.get("ui_message_id"):
                    try:
                        sent = await context.bot.send_message(
                            chat_id=p_uid,
                            text=f"🔥 <b>Баттл #{b_id} заполнен!</b> Таймер: <b>{BATTLE_COUNTDOWN_SECONDS} сек.</b>",
                            parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup([[make_btn(f"Открыть баттл #{b_id}", style="primary", callback_data=f"battle_view:{b_id}")]]),
                        )
                        update_battle_participant_msg_db(b_id, p_uid, p_uid, int(sent.message_id))
                    except Exception:
                        pass
            _ensure_battle_task(context.bot, b_id)
        return

    if data.startswith("battle_leave:"):
        b_s = data.split(":", 1)[1]
        if not b_s.isdigit():
            return
        b_id = int(b_s)
        ok, res_code, refund, refunded_uids = leave_or_cancel_battle_db(b_id, user.id)
        if not ok:
            await query.answer(f"❌ {res_code}", show_alert=True)
            return
        if res_code == "CANCELLED":
            await query.answer(f"🗑 Баттл #{b_id} отменён! Возвращено +{refund:,} ⭐.", show_alert=True)
            for r_uid in refunded_uids:
                if r_uid != user.id:
                    try:
                        await context.bot.send_message(
                            chat_id=r_uid,
                            text=(
                                f"{ce('warn')} <b>Баттл #{b_id} отменён создателем</b>\n"
                                f"Ваш взнос <b>+{refund:,} {ce('star')}</b> полностью возвращён на баланс."
                            ),
                            parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup([[make_btn("К баттлам", emoji_key="game", callback_data="battles_list:1")]]),
                        )
                    except Exception:
                        pass
            await show_battles_list(query, user.id, page=1)
        else:
            await query.answer(f"👋 Вы вышли из баттла! Возвращено +{refund:,} ⭐.", show_alert=True)
            await _broadcast_battle_room(context.bot, b_id, skip_user_id=user.id)
            await show_battles_list(query, user.id, page=1)
        return

    await query.answer()

# ---------------------------------------------------------------------------
# КОМАНДЫ БОТА
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    user = update.effective_user
    if user.is_bot:
        return ConversationHandler.END

    existing_before = get_user_row_raw(user.id)
    get_or_create_user(user.id, user.username or "", user.first_name or "")

    pending_arg = context.args[0].strip() if context.args else ""
    ref_status_note = ""
    is_private = bool(update.effective_chat and update.effective_chat.type == "private")
    if is_private:
        sync_user_start_timer(user.id)

    if pending_arg.startswith("ref_") and len(pending_arg) > 4 and is_private:
        ref_code = pending_arg[4:]
        is_truly_new = (
            existing_before is None
            or (
                not existing_before["privacy_accepted"]
                and not existing_before["bot_started"]
                and existing_before["referred_by"] is None
                and int(existing_before["xp"] or 0) == 0
                and int(existing_before["total_drops"] or 0) == 0
                and int(existing_before["balance_stars"] or 0) == 0
            )
        )
        if is_truly_new:
            ok_bind, reason_bind, _ = bind_pending_referral_db(user.id, ref_code)
            if not ok_bind and reason_bind == "self_referral":
                ref_status_note = f"{ce('warn')} Нельзя стать рефералом по собственной ссылке.\n\n"
        else:
            if existing_before and existing_before["referral_code"] == ref_code:
                ref_status_note = f"{ce('warn')} Вы перешли по собственной реферальной ссылке.\n\n"
            elif existing_before and existing_before["privacy_accepted"]:
                ref_status_note = f"{ce('info')} Вы уже зарегистрированы в боте — реферальный бонус действует только для новых игроков.\n\n"
    elif is_private:
        mark_user_bot_started(user.id)

    if not await ensure_privacy_accepted_private(update, context, pending_arg=pending_arg):
        return ConversationHandler.END

    if context.args:
        arg = context.args[0].strip()
        if arg.startswith("lot_") and arg[4:].isdigit():
            await show_market_lot_detail(update, int(arg[4:]), user.id, context)
            return ConversationHandler.END
        if arg.startswith("profile_") and arg[8:].isdigit():
            target_id = int(arg[8:])
            target_row = get_user_by_target(str(target_id))
            if not target_row:
                try:
                    chat_info = await context.bot.get_chat(target_id)
                    if chat_info:
                        target_row = get_or_create_user(target_id, chat_info.username or "", chat_info.first_name or "")
                except Exception:
                    target_row = None
            if target_row:
                await show_profile_handler(update, target_id, context)
            else:
                await update.message.reply_text("❌ Профиль игрока не найден.", reply_markup=quick_nav_keyboard())
            return ConversationHandler.END
        if arg == "checks":
            await show_checks_hub(update, user.id, context)
            return ConversationHandler.END
        if arg == "referral":
            await show_referral_hub(update, user.id, context)
            return ConversationHandler.END
        if arg.startswith("chk_") and len(arg) > 4:
            code = arg[4:]
            return await _begin_password_check_claim(update.message, user, context, code)
        if arg.startswith("gw_") and len(arg) > 3:
            gw_code = arg[3:]
            await handle_giveaway_join_deeplink(update.effective_chat.id, user, context, gw_code)
            return ConversationHandler.END

    if is_private:
        if await maybe_send_channel_subscribe_prompt(
            context.bot,
            update.effective_chat.id,
            user.id,
            context,
            ref_status_note=ref_status_note,
        ):
            return ConversationHandler.END

    if not has_completed_onboarding(user.id):
        await send_onboarding_step1(context.bot, update.effective_chat.id, user.first_name or "Игрок", context)
        return ConversationHandler.END

    banner_img = await generate_main_menu_banner()
    await update.message.reply_photo(
        photo=InputFile(banner_img, filename="menu.png"),
        caption=(
            f"{ref_status_note}"
            f"{ce('smile')} <b>Привет, {clean_html(user.first_name)}! Добро пожаловать в New NFT Bot!</b>\n\n"
            f"Пишите слово <code>NFT</code> в группах, чтобы выбивать редчайшие Telegram Gifts! {ce_gift(0)}\n\n"
            f"• {ce('shield')} Вступайте в кланы, качайте уровень клана и гербы\n"
            f"• {ce('dollar')} Создавайте чеки на 1 или нескольких игроков (можно с паролем) в <b>«Чеки»</b>\n"
            f"• {ce('megaphone')} Приглашайте друзей в <b>«Реферальная система»</b> и получайте <b>+{REFERRAL_REWARD_STARS:,} {ce('star')}</b>\n"
            f"• {ce_gift(1)} Передавайте подарки и звёзды командой <code>Передать</code> прямо в чате\n"
            f"• {ce_pepe(0)} Улучшайте <b>Plush Pepe</b>, <b>Heart Locket</b>, <b>Algorithm Cup</b>, <b>Durov's Cap</b> и <b>Bonded Ring</b> (с баффами) и торгуйте на <b>NFT Маркете</b>\n"
            f"• {ce('fire')} Забирайте лимитированного <b>Scared Cat</b> в <b>«Акциях»</b> и буст-наборы в <b>«Магазине»</b>\n"
            f"• {ce('game')} Соревнуйтесь в <b>Режимах игры → Баттлы</b> (1–15 кейсов, 1–5 игроков) и забирайте весь дроп!\n"
            f"• {ce('chat')} Поддержка: {SUPPORT_HANDLE}\n\n"
            "Используйте кнопки меню для комфортного управления:"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(user.id)
    )
    return ConversationHandler.END

async def cmd_checks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access_allowed(update):
        return
    if not await ensure_privacy_accepted_private(update, context):
        return
    await show_checks_hub(update, update.effective_user.id, context)

async def cmd_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access_allowed(update):
        return
    if not await ensure_privacy_accepted_private(update, context):
        return
    await show_referral_hub(update, update.effective_user.id, context)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access_allowed(update):
        return
    if not await ensure_privacy_accepted_private(update, context):
        return
    await show_info_page(update, context)

async def cmd_profile_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access_allowed(update):
        return
    if not await ensure_privacy_accepted_private(update, context):
        return
    u = update.effective_user
    get_or_create_user(u.id, u.username or "", u.first_name or "")
    await show_profile_handler(update, u.id, context)

async def cmd_clans(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access_allowed(update):
        return
    if not await ensure_privacy_accepted_private(update, context):
        return
    await show_clans_hub(update, update.effective_user.id, context)

async def cmd_market(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access_allowed(update):
        return
    if not await ensure_privacy_accepted_private(update, context):
        return
    await show_market_hub(update)

async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access_allowed(update):
        return
    if not await ensure_privacy_accepted_private(update, context):
        return
    await show_info_page(update, context)

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in ADMIN_IDS:
        if is_maintenance_mode():
            await update.message.reply_text(MAINTENANCE_MESSAGE, parse_mode=ParseMode.HTML)
            return
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return

    touch_user_activity(update.effective_user.id)
    text, kb = build_admin_panel_view()
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def cmd_pay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access_allowed(update):
        return
    if not await ensure_privacy_accepted_private(update, context):
        return
    sender = update.effective_user
    sender_db = get_or_create_user(sender.id, sender.username or "", sender.first_name or "")
    lvl, _, _, _ = calculate_xp_level_info(sender_db["xp"])
    if lvl < TRANSFER_MIN_LEVEL:
        await update.message.reply_text(f"❌ Переводить звёзды можно только с {TRANSFER_MIN_LEVEL}-го уровня! (Ваш уровень: {lvl})")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ <b>Использование:</b> <code>/pay &lt;ID или @username&gt; &lt;сумма&gt;</code>", parse_mode=ParseMode.HTML)
        return

    target_str, amount_str = args[0], args[1]
    if not amount_str.isdigit() or int(amount_str) <= 0:
        await update.message.reply_text("❌ Введите корректное число.")
        return

    amount = int(amount_str)
    if amount < TRANSFER_MIN_STARS:
        await update.message.reply_text(f"❌ Минимальная сумма перевода — {TRANSFER_MIN_STARS:,} ⭐!")
        return

    target_user = get_user_by_target(target_str)

    if not target_user:
        await update.message.reply_text("❌ Игрок не найден.")
        return

    if target_user["user_id"] == sender.id:
        await update.message.reply_text("❌ Перевод самому себе невозможен.")
        return

    if not deduct_user_stars(sender.id, amount):
        await update.message.reply_text("❌ Недостаточно Stars на балансе.")
        return

    add_user_stars(target_user["user_id"], amount, track_issued=False)
    record_star_flow(spent=amount)
    receiver_name = normalize_telegram_name(target_user["first_name"], target_user["username"], target_user["user_id"])

    try:
        await context.bot.send_message(
            chat_id=target_user["user_id"],
            text=(
                f"💸 <b>Вам поступил перевод!</b>\n\n"
                f"От игрока: <b>{clean_html(sender.first_name)}</b>\n"
                f"Сумма: <b>+{amount:,} ⭐</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard()
        )
    except Exception:
        pass

    await update.message.reply_text(
        f"💸 <b>Перевод выполнен!</b>\nПереведено <b>{amount:,} ⭐</b> игроку <b>{clean_html(receiver_name)}</b>.",
        parse_mode=ParseMode.HTML,
        reply_markup=quick_nav_keyboard()
    )

async def cmd_send_gift(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_access_allowed(update):
        return
    if not await ensure_privacy_accepted_private(update, context):
        return
    sender = update.effective_user
    sender_db = get_or_create_user(sender.id, sender.username or "", sender.first_name or "")

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ <b>Использование:</b> <code>/send_gift &lt;ID_предмета&gt; &lt;ID или @username&gt;</code>", parse_mode=ParseMode.HTML)
        return

    item_id_str, target_str = args[0], args[1]
    if not item_id_str.isdigit():
        await update.message.reply_text("❌ Укажите ID предмета.")
        return

    item_id = int(item_id_str)
    item = get_collection_item(item_id)
    if not item or item["user_id"] != sender.id:
        await update.message.reply_text("❌ Предмет не найден в вашей коллекции.")
        return

    if not item["is_upgraded"]:
        lvl, _, _, _ = calculate_xp_level_info(sender_db["xp"])
        if lvl < TRANSFER_MIN_LEVEL:
            await update.message.reply_text(f"❌ Передавать обычные подарки можно только с {TRANSFER_MIN_LEVEL}-го уровня! (Улучшенные подарки можно передавать на любом уровне)")
            return

    target_user = get_user_by_target(target_str)
    if not target_user or target_user["user_id"] == sender.id:
        await update.message.reply_text("❌ Некорректный получатель.")
        return

    ok, res = transfer_gift_between_users(sender.id, target_user["user_id"], item_id)
    if not ok:
        await update.message.reply_text(f"❌ {res}")
        return

    g = GIFTS_BY_KEY.get(res)
    g_name = f"{get_upgraded_gift_title(item['gift_key'])} #{item['upgrade_num']} ({item['model_name']})" if item["is_upgraded"] else (g.name if g else res)
    receiver_name = normalize_telegram_name(target_user["first_name"], target_user["username"], target_user["user_id"])

    try:
        await context.bot.send_message(
            chat_id=target_user["user_id"],
            text=(
                f"🎁 <b>Вам подарен NFT!</b>\n\n"
                f"От игрока: <b>{clean_html(sender.first_name)}</b>\n"
                f"Предмет: <b>{clean_html(g_name)}</b>!\n"
                f"Предмет уже в вашей коллекции."
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard()
        )
    except Exception:
        pass

    await update.message.reply_text(
        f"🎁 <b>Подарок передан!</b>\nПредмет <b>{clean_html(g_name)}</b> отправлен игроку <b>{clean_html(receiver_name)}</b>!",
        parse_mode=ParseMode.HTML,
        reply_markup=quick_nav_keyboard()
    )

async def cmd_maintenance_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Перехватывает любые неизвестные /команды во время техработ."""
    if not await check_access_allowed(update):
        return

# ---------------------------------------------------------------------------
# ЧЕКИ ВНУТРИ БОТА (МУЛЬТИ-ЧЕКИ, ПАРОЛЬ, ИНЛАЙН-РАССЫЛКА ТОЛЬКО ГОТОВЫХ ЧЕКОВ)
# ---------------------------------------------------------------------------

_CHECK_CARD_FILE_ID_CACHE: Dict[Tuple[int, int, int, int, int, str, str], str] = {}

def _build_shared_check_view(
    chk: sqlite3.Row,
    creator_name: str,
    bot_username: str,
    claimer_name: Optional[str] = None,
) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    code = chk["code"]
    max_claims = max(1, int(chk["max_claims"] or 1))
    claimed_count = int(chk["claimed_count"] or 0)
    per_claim = int(chk["per_claim_stars"] or chk["amount_stars"])
    total_stars = int(chk["amount_stars"])
    has_pwd = bool(chk["has_password"])
    target_lbl = (
        f"@{chk['target_username']}"
        if chk["target_username"]
        else (f"До {max_claims} игроков" if max_claims > 1 else "Любой игрок")
    )

    if chk["status"] == "cancelled":
        cap = (
            f"{ce('cross')} <b>Чек на {fmt_stars_compact(total_stars)} {ce('star')} отменён создателем</b>\n"
            f"{ce('smile')} От: <b>{clean_html(creator_name)}</b>\n\n"
            f"{CHECK_DISCLAIMER_QUOTE}"
        )
        return cap, None

    if claimed_count >= max_claims or chk["status"] == "claimed":
        if max_claims > 1:
            cap = (
                f"{ce('check')} <b>Чек на {fmt_stars_compact(total_stars)} {ce('star')} полностью активирован!</b>\n"
                f"━━━━━━━━━━━━\n"
                f"{ce('smile')} От: <b>{clean_html(creator_name)}</b>\n"
                f"{ce('sparkles')} Активаций: <b>{claimed_count}/{max_claims}</b> (по <b>{fmt_stars_compact(per_claim)} {ce('star')}</b>)\n"
                f"{ce('dollar')} Итого роздано: <b>{fmt_stars_rub(total_stars)}</b>\n\n"
                f"{CHECK_DISCLAIMER_QUOTE}"
            )
            btn_txt = f"Разобрано ({claimed_count}/{max_claims})"
        else:
            cl_disp = claimer_name or "Игрок"
            cap = (
                f"{ce('check')} <b>Чек на {fmt_stars_compact(per_claim)} {ce('star')} активирован!</b>\n"
                f"━━━━━━━━━━━━\n"
                f"{ce('smile')} От: <b>{clean_html(creator_name)}</b>\n"
                f"{ce('boom')} Получил: <b>{clean_html(cl_disp)}</b>\n"
                f"{ce('dollar')} Сумма: <b>{fmt_stars_rub(per_claim)}</b>\n\n"
                f"{CHECK_DISCLAIMER_QUOTE}"
            )
            btn_txt = f"Активирован ({cl_disp[:18]})"
        return cap, InlineKeyboardMarkup([[make_btn(btn_txt, emoji_key="check", callback_data=f"check_done:{code}")]])

    pwd_line = f"\n{ce('lock')} Защита: <b>Требуется пароль</b>" if has_pwd else ""
    slots_line = (
        f"\n{ce('sparkles')} Осталось активаций: <b>{max_claims - claimed_count}/{max_claims}</b> (по <b>{fmt_stars_compact(per_claim)} {ce('star')}</b>)"
        if max_claims > 1
        else ""
    )
    cap = (
        f"{ce('dollar')} <b>Чек на {fmt_stars_compact(per_claim)} {ce('star')}</b>\n"
        f"━━━━━━━━━━━━\n"
        f"{ce('smile')} От: <b>{clean_html(creator_name)}</b>\n"
        f"{ce('pin_loc')} Получатель: <b>{clean_html(target_lbl)}</b>{slots_line}{pwd_line}\n"
        f"{ce('money_wings')} Сумма: <b>{fmt_stars_rub(per_claim)}</b>\n\n"
        f"{CHECK_DISCLAIMER_QUOTE}"
    )
    if has_pwd:
        btn = make_btn(
            f"Ввести пароль и забрать {fmt_stars_compact(per_claim)} ⭐",
            style="success",
            emoji_key="lock",
            url=f"https://t.me/{bot_username}?start=chk_{code}",
        )
    else:
        btn_label = (
            f"Забрать {fmt_stars_compact(per_claim)} ⭐ ({claimed_count}/{max_claims})"
            if max_claims > 1
            else f"Забрать чек ({fmt_stars_compact(per_claim)} ⭐)"
        )
        btn = make_btn(btn_label, style="success", emoji_key="dollar", callback_data=f"claim_check:{code}")
    return cap, InlineKeyboardMarkup([[btn]])

async def _refresh_shared_check_message(
    bot,
    chk: sqlite3.Row,
    creator_name: str,
    bot_username: str,
    claimer_name: Optional[str] = None,
    inline_message_id: Optional[str] = None,
    message=None,
) -> None:
    code = chk["code"]
    max_claims = max(1, int(chk["max_claims"] or 1))
    claimed_count = int(chk["claimed_count"] or 0)
    per_claim = int(chk["per_claim_stars"] or chk["amount_stars"])
    total_stars = int(chk["amount_stars"])
    has_pwd = bool(chk["has_password"])
    target_lbl = (
        f"@{chk['target_username']}"
        if chk["target_username"]
        else (f"До {max_claims} игроков" if max_claims > 1 else "Все игроки")
    )
    cap, kb = _build_shared_check_view(chk, creator_name, bot_username, claimer_name=claimer_name)
    is_final = (claimed_count >= max_claims or chk["status"] == "claimed")

    card_io = await generate_check_card_image(
        amount_stars=total_stars,
        creator_name=creator_name,
        target_label=target_lbl,
        claimed_by=(claimer_name if is_final else None),
        max_claims=max_claims,
        claimed_count=claimed_count,
        per_claim_stars=per_claim,
        has_password=has_pwd,
    )
    target_inline_id = inline_message_id or (chk["inline_message_id"] if "inline_message_id" in chk.keys() else "")

    if target_inline_id:
        try:
            await bot.edit_message_media(
                inline_message_id=target_inline_id,
                media=InputMediaPhoto(
                    media=InputFile(card_io, filename=f"check_{code}.png"),
                    caption=cap,
                    parse_mode=ParseMode.HTML,
                ),
                reply_markup=kb,
            )
            return
        except Exception:
            try:
                await bot.edit_message_caption(
                    inline_message_id=target_inline_id,
                    caption=cap,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                )
                return
            except Exception:
                try:
                    await bot.edit_message_text(
                        inline_message_id=target_inline_id,
                        text=cap,
                        parse_mode=ParseMode.HTML,
                        reply_markup=kb,
                    )
                    return
                except Exception:
                    pass

    if message is not None:
        if getattr(message, "photo", None):
            try:
                await message.edit_media(
                    media=InputMediaPhoto(
                        media=InputFile(card_io, filename=f"check_{code}.png"),
                        caption=cap,
                        parse_mode=ParseMode.HTML,
                    ),
                    reply_markup=kb,
                )
                return
            except Exception:
                try:
                    await message.edit_caption(caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
                    return
                except Exception:
                    pass
        else:
            try:
                await message.edit_text(cap, parse_mode=ParseMode.HTML, reply_markup=kb)
            except Exception:
                pass

async def show_checks_hub(query_or_msg, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_user = get_or_create_user(user_id, "", "")
    active_checks = get_user_active_checks(user_id)

    lines = [
        f"{ce('dollar')} <b>Мои чеки (Stars Vouchers)</b>",
        "━━━━━━━━━━━━",
        f"{ce('star')} Ваш баланс: <b>{fmt_stars_rub(db_user['balance_stars'])}</b>\n",
        "<blockquote expandable>"
        f"{ce('thought')} <b>Как работают чеки:</b>\n"
        "• Можно создать чек для <b>1 игрока</b> или для <b>нескольких человек</b> (сумма делится поровну между всеми).\n"
        "• Можно защитить чек <b>паролем</b> — получатель введёт его приватно в ЛС.\n"
        f"• Делиться готовым чеком можно в любом чате кнопкой <b>«Поделиться»</b>."
        "</blockquote>\n",
    ]
    buttons = [[make_btn("Создать новый чек", style="success", emoji_key="plus", callback_data="check_create_start")]]

    if not active_checks:
        lines.append("<i>У вас сейчас нет активных чеков.</i>")
    else:
        lines.append(f"<b>Активные чеки ({len(active_checks)}):</b>")
        for idx, chk in enumerate(active_checks[:6], start=1):
            code = chk["code"]
            max_c = max(1, int(chk["max_claims"] or 1))
            claimed_c = int(chk["claimed_count"] or 0)
            per_c = int(chk["per_claim_stars"] or chk["amount_stars"])
            rem_c = max(0, max_c - claimed_c)
            pwd_icon = ce("lock") if chk["has_password"] else ce("green_dot")
            tgt = f"@{chk['target_username']}" if chk["target_username"] else (f"{rem_c}/{max_c} чел." if max_c > 1 else "1 любой")
            lines.append(
                f"{idx}. {pwd_icon} <b>{fmt_stars_compact(per_c)} {ce('star')}</b> × <b>{rem_c}</b> ({clean_html(tgt)})"
            )
            buttons.append([
                make_btn(f"Поделиться #{idx} ({fmt_stars_compact(per_c)}⭐)", style="primary", emoji_key="link", switch_inline_query=f"check_{code}"),
                make_btn(f"Отменить #{idx}", style="danger", emoji_key="cross", callback_data=f"check_cancel:{code}"),
            ])

    buttons.append([make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")])
    text = "\n".join(lines)
    kb = InlineKeyboardMarkup(buttons)

    if isinstance(query_or_msg, CallbackQuery):
        if query_or_msg.message and query_or_msg.message.photo:
            await query_or_msg.message.delete()
            await query_or_msg.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        elif query_or_msg.message:
            await query_or_msg.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        target_msg = query_or_msg.effective_message if hasattr(query_or_msg, "effective_message") else query_or_msg
        if target_msg:
            await target_msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_referral_hub(query_or_msg, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_user = get_or_create_user(user_id, "", "")
    is_active = bool(db_user["referral_active"]) and bool((db_user["referral_code"] or "").strip())

    if not is_active:
        text = (
            f"{ce('megaphone')} <b>Реферальная система</b>\n"
            "━━━━━━━━━━━━\n"
            f"{ce('free')} Активация реферальной системы — <b>абсолютно бесплатная</b>!\n\n"
            "<blockquote expandable>"
            f"{ce('thought')} <b>Как это работает:</b>\n"
            "• Нажмите кнопку <b>«Активировать бесплатно»</b> ниже, чтобы получить персональную ссылку.\n"
            "• Отправляйте ссылку друзьям и в чаты с готовым описанием бота или просто копируйте её.\n"
            "• Каждый <b>новый пользователь</b>, который перейдёт по вашей ссылке, нажмёт <b>Старт</b> и примет <b>пользовательское соглашение</b>, засчитается вам как реферал.\n"
            f"• За каждого приглашённого игрока вы мгновенно получите <b>+{REFERRAL_REWARD_STARS:,} {ce('star')}</b> и уведомление в личные сообщения!\n"
            "</blockquote>\n"
            "━━━━━━━━━━━━\n"
            f"{ce('star')} Награда за 1 друга: <b>+{REFERRAL_REWARD_STARS:,} {ce('star')}</b>"
        )
        kb = InlineKeyboardMarkup([
            [make_btn("Активировать бесплатно", style="success", emoji_key="check", callback_data="ref_activate")],
            [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")],
        ])
    else:
        bot_username = await get_bot_username(context.bot)
        ref_code = db_user["referral_code"]
        ref_link = f"https://t.me/{bot_username}?start=ref_{ref_code}"
        share_text = (
            "🎁 Залетай в New NFT Bot!\n\n"
            "✨ Выбивай редкие Telegram NFT-подарки прямо в чатах словом NFT, открывай Mystery Cases, "
            "улучшай Plush Pepe, Heart Locket, Durov's Cap, Algorithm Cup и Bonded Ring, забирай уникального Scared Cat, "
            "торгуй на P2P NFT Маркете, вступай в кланы и отправляй чеки!\n\n"
            "🚀 Переходи по моей ссылке, жми Старт и забирай свой первый NFT-подарок бесплатно!"
        )
        share_url = (
            f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}"
            f"&text={urllib.parse.quote(share_text)}"
        )

        rewarded_cnt, pending_cnt, earned_stars = get_referral_stats_db(user_id)
        recent_rows, total_rows = get_referrals_page_db(user_id, page=1, page_size=5)

        lines = [
            f"{ce('megaphone')} <b>Реферальная система</b>",
            "━━━━━━━━━━━━",
            f"{ce('green_dot')} Статус: <b>Активирована</b>",
            f"{ce('link')} <b>Ваша реферальная ссылка:</b>",
            f"<code>{clean_html(ref_link)}</code>",
            "<i>(Нажмите на ссылку выше, чтобы скопировать, или используйте кнопки ниже)</i>\n",
            f"{ce('chart_bar')} <b>Ваша статистика:</b>",
            f"• {ce('smile')} Приглашено пользователей: <b>{rewarded_cnt:,}</b> чел.",
            f"• {ce('hourglass')} Ожидают принятия соглашения: <b>{pending_cnt:,}</b> чел.",
            f"• {ce('star')} Заработано с рефералов: <b>{fmt_stars_rub(earned_stars)}</b>",
            f"• {ce('dollar')} Награда за 1 друга: <b>+{REFERRAL_REWARD_STARS:,} {ce('star')}</b>",
        ]

        if recent_rows:
            lines.append("\n<blockquote expandable>")
            lines.append(f"{ce('top')} <b>Последние приглашённые ({total_rows}):</b>")
            for idx, r in enumerate(recent_rows, start=1):
                r_name = normalize_telegram_name(r["first_name"], r["username"], r["referred_user_id"])
                ts_val = int(r["rewarded_ts"] or r["created_ts"] or 0)
                dt_str = datetime.datetime.fromtimestamp(ts_val).strftime("%d.%m %H:%M") if ts_val else ""
                if r["status"] == "rewarded":
                    lines.append(
                        f"{idx}. {ce('check')} <b>{clean_html(r_name)}</b> — <b>+{int(r['reward_stars']):,} {ce('star')}</b> ({dt_str})"
                    )
                else:
                    lines.append(
                        f"{idx}. {ce('hourglass')} <b>{clean_html(r_name)}</b> — ожидает соглашения ({dt_str})"
                    )
            lines.append("</blockquote>")

        text = "\n".join(lines)
        buttons = [
            [make_btn("Поделиться", style="success", emoji_key="megaphone", url=share_url)],
            [make_btn("Скопировать ссылку", style="primary", emoji_key="link", callback_data="ref_copy_link")],
        ]
        if total_rows > 0:
            buttons.append([make_btn(f"Все приглашённые ({total_rows})", emoji_key="chart_bar", callback_data="ref_list:1")])
        buttons.append([
            make_btn("Обновить", emoji_key="refresh", callback_data="nav_referral"),
            make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main"),
        ])
        kb = InlineKeyboardMarkup(buttons)

    if isinstance(query_or_msg, CallbackQuery):
        if query_or_msg.message and query_or_msg.message.photo:
            await query_or_msg.message.delete()
            await query_or_msg.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        elif query_or_msg.message:
            await query_or_msg.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        target_msg = query_or_msg.effective_message if hasattr(query_or_msg, "effective_message") else query_or_msg
        if target_msg:
            await target_msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_referral_list_page(query, user_id: int, page: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    page_size = 10
    rows, total = get_referrals_page_db(user_id, page=page, page_size=page_size)
    total_pages = max(1, math.ceil(total / page_size))
    page = max(1, min(page, total_pages))
    if page != 1 and not rows:
        rows, total = get_referrals_page_db(user_id, page=page, page_size=page_size)

    rewarded_cnt, pending_cnt, earned_stars = get_referral_stats_db(user_id)
    lines = [
        f"{ce('chart_bar')} <b>Ваши приглашённые пользователи (стр. {page}/{total_pages})</b>",
        "━━━━━━━━━━━━",
        f"{ce('smile')} Засчитано: <b>{rewarded_cnt:,}</b> чел.  •  {ce('hourglass')} Ожидают: <b>{pending_cnt:,}</b> чел.",
        f"{ce('star')} Всего получено: <b>{fmt_stars_rub(earned_stars)}</b>\n",
    ]

    if not rows:
        lines.append("<i>Вы ещё никого не пригласили.</i>")
    else:
        start_num = (page - 1) * page_size + 1
        for offset, r in enumerate(rows):
            num = start_num + offset
            r_name = normalize_telegram_name(r["first_name"], r["username"], r["referred_user_id"])
            uname_str = f" (@{clean_html(r['username'])})" if r["username"] else ""
            ts_val = int(r["rewarded_ts"] or r["created_ts"] or 0)
            dt_str = datetime.datetime.fromtimestamp(ts_val).strftime("%d.%m.%Y %H:%M") if ts_val else ""
            if r["status"] == "rewarded":
                lines.append(
                    f"{num}. {ce('check')} <b>{clean_html(r_name)}</b>{uname_str}\n"
                    f"    {ce('star')} Начислено: <b>+{int(r['reward_stars']):,} ⭐</b> • {dt_str}"
                )
            else:
                lines.append(
                    f"{num}. {ce('hourglass')} <b>{clean_html(r_name)}</b>{uname_str}\n"
                    f"    Ожидает принятия соглашения • {dt_str}"
                )

    buttons = []
    nav_row = []
    if page > 1:
        nav_row.append(make_btn("Назад", emoji_key="arrow_right", callback_data=f"ref_list:{page - 1}"))
    if page < total_pages:
        nav_row.append(make_btn("Вперёд", emoji_key="arrow_right", callback_data=f"ref_list:{page + 1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([make_btn("К реферальной системе", emoji_key="megaphone", callback_data="nav_referral")])
    buttons.append([make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")])

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def check_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    if not await ensure_privacy_accepted_private(update, context):
        return ConversationHandler.END

    query = update.callback_query
    user = query.from_user
    if query.message and query.message.chat.type != "private":
        await query.answer("⚠️ Создавать чеки можно только в личных сообщениях с ботом!", show_alert=True)
        return ConversationHandler.END

    db_user = get_or_create_user(user.id, user.username or "", user.first_name or "")
    lvl, _, _, _ = calculate_xp_level_info(db_user["xp"])
    if lvl < TRANSFER_MIN_LEVEL:
        await query.answer(f"❌ Создание чеков доступно с {TRANSFER_MIN_LEVEL}-го уровня (у вас {lvl})!", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    context.user_data.pop("new_check_target_username", None)
    context.user_data.pop("new_check_max_claims", None)
    context.user_data.pop("new_check_amount", None)

    text = (
        f"{ce('dollar')} <b>Создание чека — Шаг 1 из 3: Получатели</b>\n"
        "━━━━━━━━━━━━\n"
        "Отправьте одно из значений:\n"
        "• <code>@username</code> — персональный чек для 1 конкретного игрока\n"
        "• <b>Число человек</b> (например: <code>5</code>) — мультиваучер, где общая сумма делится поровну между N разными игроками\n"
        "• Либо нажмите кнопку ниже для <b>1 любого игрока</b>:"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("Для 1 любого игрока", style="primary", emoji_key="smile", callback_data="check_target_anyone")],
        [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="check_create_cancel")],
    ])
    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_CHECK_TARGET

async def _prompt_check_amount_step(msg_or_query, user_id: int, context: ContextTypes.DEFAULT_TYPE, is_edit: bool = False):
    db_user = get_or_create_user(user_id, "", "")
    tgt_uname = context.user_data.get("new_check_target_username", "")
    max_claims = int(context.user_data.get("new_check_max_claims", 1))
    tgt_desc = f"@{tgt_uname}" if tgt_uname else (f"{max_claims} чел. (ровная доля каждому)" if max_claims > 1 else "1 любой игрок")

    text = (
        f"{ce('dollar')} <b>Создание чека — Шаг 2 из 3: Сумма звёзд</b>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('pin_loc')} Получатель: <b>{clean_html(tgt_desc)}</b>\n"
        f"{ce('star')} Ваш баланс: <b>{fmt_stars_rub(db_user['balance_stars'])}</b>\n\n"
        f"Введите общую сумму звёзд (от <b>{CHECK_MIN_STARS:,} {ce('star')}</b>):"
    )
    kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="check_create_cancel")]])
    if is_edit:
        await msg_or_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await msg_or_query.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_CHECK_AMOUNT

async def check_target_anyone_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    context.user_data["new_check_target_username"] = ""
    context.user_data["new_check_max_claims"] = 1
    return await _prompt_check_amount_step(query, query.from_user.id, context, is_edit=True)

async def check_target_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    raw = update.message.text.strip()
    if raw.startswith("@"):
        uname = raw.lstrip("@").strip()
        if len(uname) < 2 or " " in uname:
            await update.message.reply_text(
                f"{ce('cross')} Введите корректный @username (например <code>@durov</code>) или число получателей (от 1 до 1000):",
                parse_mode=ParseMode.HTML,
            )
            return WAIT_CHECK_TARGET
        context.user_data["new_check_target_username"] = uname
        context.user_data["new_check_max_claims"] = 1
        return await _prompt_check_amount_step(update.message, update.effective_user.id, context, is_edit=False)

    clean_num = re.sub(r"[\s,_.]", "", raw)
    if clean_num.isdigit():
        cnt = int(clean_num)
        if cnt < 1 or cnt > 1000:
            await update.message.reply_text(
                f"{ce('cross')} Количество получателей должно быть от 1 до 1000. Попробуйте снова:",
                parse_mode=ParseMode.HTML,
            )
            return WAIT_CHECK_TARGET
        context.user_data["new_check_target_username"] = ""
        context.user_data["new_check_max_claims"] = cnt
        return await _prompt_check_amount_step(update.message, update.effective_user.id, context, is_edit=False)

    await update.message.reply_text(
        f"{ce('cross')} Введите @username (начинается с @) или количество получателей цифрой (например <code>5</code>):",
        parse_mode=ParseMode.HTML,
    )
    return WAIT_CHECK_TARGET

async def check_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    user = update.effective_user
    raw = re.sub(r"[\s,_.]", "", update.message.text.strip())
    if not raw.isdigit():
        await update.message.reply_text(
            f"{ce('cross')} Введите целое число от {CHECK_MIN_STARS:,} {ce('star')} (или /cancel):",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_CHECK_AMOUNT

    amount = int(raw)
    max_claims = max(1, int(context.user_data.get("new_check_max_claims", 1)))
    if amount < CHECK_MIN_STARS:
        await update.message.reply_text(
            f"{ce('cross')} Минимальная сумма чека — <b>{CHECK_MIN_STARS:,} {ce('star')}</b>!",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_CHECK_AMOUNT
    if amount > 10_000_000_000:
        await update.message.reply_text(
            f"{ce('cross')} Слишком большая сумма для одного чека.",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_CHECK_AMOUNT

    per_claim = amount // max_claims
    if per_claim < 1:
        await update.message.reply_text(
            f"{ce('cross')} Сумма слишком мала для такого количества человек!",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_CHECK_AMOUNT

    locked_total = per_claim * max_claims
    db_user = get_or_create_user(user.id, user.username or "", user.first_name or "")
    if db_user["balance_stars"] < locked_total:
        await update.message.reply_text(
            f"{ce('cross')} Недостаточно Stars на балансе! Нужно <b>{locked_total:,} {ce('star')}</b> (у вас <b>{db_user['balance_stars']:,} {ce('star')}</b>).",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_CHECK_AMOUNT

    context.user_data["new_check_amount"] = amount
    rem = amount - locked_total
    split_note = f"\n{ce('sparkles')} Выплата каждому: <b>{per_claim:,} {ce('star')} × {max_claims}</b>" if max_claims > 1 else ""
    rem_note = f"\n{ce('refresh')} Неделимый остаток <b>{rem:,} {ce('star')}</b> останется на вашем балансе." if rem > 0 else ""

    kb = InlineKeyboardMarkup([
        [make_btn("Без пароля", style="primary", emoji_key="check", callback_data="check_skip_password")],
        [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="check_create_cancel")],
    ])
    await update.message.reply_text(
        f"{ce('lock')} <b>Создание чека — Шаг 3 из 3: Пароль (опционально)</b>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('dollar')} Сумма к списанию: <b>{locked_total:,} {ce('star')}</b>{split_note}{rem_note}\n\n"
        "Отправьте секретный <b>пароль</b> текстом (от 1 до 32 символов), чтобы забрать чек можно было только по паролю,\n"
        "или нажмите кнопку <b>«Без пароля»</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAIT_CHECK_PASSWORD

async def _finalize_bot_check_creation(
    reply_target,
    user,
    context: ContextTypes.DEFAULT_TYPE,
    password: str = "",
):
    tgt_uname = context.user_data.pop("new_check_target_username", "")
    max_claims = int(context.user_data.pop("new_check_max_claims", 1))
    amount = int(context.user_data.pop("new_check_amount", 0))

    ok, err_msg, chk, remainder = create_bot_star_check(
        creator_id=user.id,
        total_amount=amount,
        target_username=tgt_uname,
        max_claims=max_claims,
        password=password,
    )
    if not ok or not chk:
        await reply_target.reply_text(f"{ce('cross')} {err_msg}", parse_mode=ParseMode.HTML, reply_markup=quick_nav_keyboard())
        return ConversationHandler.END

    code = chk["code"]
    per_claim = int(chk["per_claim_stars"] or chk["amount_stars"])
    max_c = max(1, int(chk["max_claims"] or 1))
    creator_name = normalize_telegram_name(user.first_name, user.username, user.id)
    target_lbl = f"@{tgt_uname}" if tgt_uname else (f"До {max_c} игроков" if max_c > 1 else "Все игроки")
    has_pwd = bool(chk["has_password"])

    card_io = await generate_check_card_image(
        amount_stars=int(chk["amount_stars"]),
        creator_name=creator_name,
        target_label=target_lbl,
        max_claims=max_c,
        claimed_count=0,
        per_claim_stars=per_claim,
        has_password=has_pwd,
    )
    pwd_line = f"{ce('lock')} Защита: <b>Пароль установлен</b>\n" if has_pwd else f"{ce('check')} Защита: <b>Без пароля</b>\n"
    slots_line = f"{ce('sparkles')} Получателей: <b>{max_c} чел.</b> (по <b>{fmt_stars_compact(per_claim)} {ce('star')}</b> каждому)\n" if max_c > 1 else f"{ce('pin_loc')} Получатель: <b>{clean_html(target_lbl)}</b>\n"
    rem_line = f"{ce('refresh')} Неделимый остаток <b>{remainder:,} {ce('star')}</b> остался на вашем балансе.\n" if remainder > 0 else ""

    cap = (
        f"{ce('check')} <b>Чек успешно создан!</b>\n"
        f"━━━━━━━━━━━━\n"
        f"{ce('dollar')} Номинал: <b>{fmt_stars_rub(per_claim)}</b>" + (f" (итого <b>{fmt_stars_compact(chk['amount_stars'])} {ce('star')}</b>)" if max_c > 1 else "") + "\n"
        f"{slots_line}"
        f"{pwd_line}"
        f"{rem_line}"
        f"━━━━━━━━━━━━\n"
        f"{ce('link')} Нажмите <b>«Отправить чек в чат»</b>, чтобы поделиться им в любом чате или группе!\n\n"
        f"{CHECK_DISCLAIMER_QUOTE}"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("Отправить чек в чат", style="success", emoji_key="link", switch_inline_query=f"check_{code}")],
        [make_btn("Мои чеки", emoji_key="dollar", callback_data="nav_checks")],
        [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")],
    ])
    await context.bot.send_photo(
        chat_id=user.id,
        photo=InputFile(card_io, filename=f"check_{code}.png"),
        caption=cap,
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END

async def check_password_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    pwd = (update.message.text or "").strip()
    if len(pwd) < 1 or len(pwd) > 32:
        await update.message.reply_text(
            f"{ce('cross')} Пароль должен содержать от 1 до 32 символов. Введите заново или нажмите «Без пароля»:",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_CHECK_PASSWORD
    return await _finalize_bot_check_creation(update.message, update.effective_user, context, password=pwd)

async def check_skip_password_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    if query.message:
        try: await query.message.delete()
        except Exception: pass
    return await _finalize_bot_check_creation(query.message, query.from_user, context, password="")

async def check_create_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_check_target_username", None)
    context.user_data.pop("new_check_max_claims", None)
    context.user_data.pop("new_check_amount", None)
    if update.callback_query:
        await update.callback_query.answer("Отменено.")
        await show_checks_hub(update.callback_query, update.callback_query.from_user.id, context)
    elif update.message:
        await update.message.reply_text(
            f"{ce('cross')} Создание чека отменено.",
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard(),
        )
    return ConversationHandler.END

async def _begin_password_check_claim(reply_target, user, context: ContextTypes.DEFAULT_TYPE, code: str):
    chk = get_star_check(code)
    if not chk or chk["status"] != "active":
        await reply_target.reply_text(
            f"{ce('cross')} Этот чек недействителен или уже полностью активирован.",
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard(),
        )
        return ConversationHandler.END

    # Проверим право на получение (без пароля заранее, если нет пароля — сразу активируем)
    if not chk["has_password"]:
        ok, msg_txt, upd_chk = claim_star_check_db(code, user.id, user.username or "")
        if not ok:
            await reply_target.reply_text(
                f"{ce('cross')} {clean_html(msg_txt)}",
                parse_mode=ParseMode.HTML,
                reply_markup=quick_nav_keyboard(),
            )
            return ConversationHandler.END
        per_claim = int(upd_chk["per_claim_stars"] or upd_chk["amount_stars"])
        claimer_name = normalize_telegram_name(user.first_name, user.username, user.id)
        creator_row = get_or_create_user(upd_chk["creator_id"], "", "")
        creator_name = normalize_telegram_name(creator_row["first_name"], creator_row["username"], upd_chk["creator_id"])
        bot_username = await get_bot_username(context.bot)
        await _refresh_shared_check_message(context.bot, upd_chk, creator_name, bot_username, claimer_name=claimer_name)
        await reply_target.reply_text(
            f"{ce('boom')} <b>Вы получили +{fmt_stars_compact(per_claim)} {ce('star')} по чеку!</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard(),
        )
        return ConversationHandler.END

    # Проверяем target_username / duplicate заранее через claim_star_check_db(..., password_attempt=None)
    ok_pre, pre_msg, _ = claim_star_check_db(code, user.id, user.username or "", password_attempt=None)
    if not ok_pre and pre_msg != "NEED_PASSWORD":
        await reply_target.reply_text(
            f"{ce('cross')} {clean_html(pre_msg)}",
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard(),
        )
        return ConversationHandler.END

    context.user_data["claim_pwd_check_code"] = code
    per_claim = int(chk["per_claim_stars"] or chk["amount_stars"])
    creator_row = get_or_create_user(chk["creator_id"], "", "")
    creator_name = normalize_telegram_name(creator_row["first_name"], creator_row["username"], chk["creator_id"])
    kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="check_pwd_claim_cancel")]])
    await reply_target.reply_text(
        f"{ce('lock')} <b>Чек на {fmt_stars_compact(per_claim)} {ce('star')} от {clean_html(creator_name)}</b>\n\n"
        "Этот чек защищён паролем. Введите пароль в ответном сообщении:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAIT_CHECK_CLAIM_PASSWORD

async def claim_check_pwd_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    code = query.data.split(":", 1)[1]
    return await _begin_password_check_claim(query.message, query.from_user, context, code)

async def check_claim_password_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    code = context.user_data.get("claim_pwd_check_code", "")
    if not code:
        await update.message.reply_text(
            f"{ce('cross')} Сессия ввода пароля устарела.",
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard(),
        )
        return ConversationHandler.END

    user = update.effective_user
    get_or_create_user(user.id, user.username or "", user.first_name or "")
    pwd_attempt = (update.message.text or "").strip()
    ok, msg_txt, chk = claim_star_check_db(code, user.id, user.username or "", password_attempt=pwd_attempt)

    if not ok:
        if "Неверный пароль" in msg_txt:
            kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="check_pwd_claim_cancel")]])
            await update.message.reply_text(f"{ce('cross')} {clean_html(msg_txt)}", parse_mode=ParseMode.HTML, reply_markup=kb)
            return WAIT_CHECK_CLAIM_PASSWORD
        context.user_data.pop("claim_pwd_check_code", None)
        await update.message.reply_text(f"{ce('cross')} {clean_html(msg_txt)}", parse_mode=ParseMode.HTML, reply_markup=quick_nav_keyboard())
        return ConversationHandler.END

    context.user_data.pop("claim_pwd_check_code", None)
    per_claim = int(chk["per_claim_stars"] or chk["amount_stars"])
    claimer_name = normalize_telegram_name(user.first_name, user.username, user.id)
    creator_row = get_or_create_user(chk["creator_id"], "", "")
    creator_name = normalize_telegram_name(creator_row["first_name"], creator_row["username"], chk["creator_id"])
    bot_username = await get_bot_username(context.bot)

    await _refresh_shared_check_message(
        bot=context.bot,
        chk=chk,
        creator_name=creator_name,
        bot_username=bot_username,
        claimer_name=claimer_name,
    )

    if chk["creator_id"] != user.id:
        max_claims = max(1, int(chk["max_claims"] or 1))
        claimed_cnt = int(chk["claimed_count"] or 0)
        slots_note = f"\n{ce('sparkles')} Активаций: <b>{claimed_cnt}/{max_claims}</b>" if max_claims > 1 else ""
        try:
            await context.bot.send_message(
                chat_id=chk["creator_id"],
                text=(
                    f"{ce('dollar')} <b>Активация вашего чека (+{fmt_stars_compact(per_claim)} {ce('star')})!</b>\n"
                    f"{ce('smile')} Получатель: <b>{clean_html(claimer_name)}</b>{slots_note}"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=quick_nav_keyboard(),
            )
        except Exception:
            pass

    await update.message.reply_text(
        f"{ce('boom')} <b>Пароль верный!</b>\nВы получили <b>+{fmt_stars_rub(per_claim)}</b> по чеку от <b>{clean_html(creator_name)}</b>!",
        parse_mode=ParseMode.HTML,
        reply_markup=quick_nav_keyboard(),
    )
    return ConversationHandler.END

async def check_pwd_claim_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("claim_pwd_check_code", None)
    if update.callback_query:
        await update.callback_query.answer("Отменено.")
        await update.callback_query.edit_message_text(
            f"{ce('cross')} Ввод пароля отменён.",
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard(),
        )
    elif update.message:
        await update.message.reply_text(
            f"{ce('cross')} Ввод пароля отменён.",
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard(),
        )
    return ConversationHandler.END

async def _upload_temp_check_photo(bot, chat_id: int, img_io: io.BytesIO) -> Optional[str]:
    try:
        img_io.seek(0)
        sent = await bot.send_photo(
            chat_id=chat_id,
            photo=InputFile(img_io, filename="star_check.png"),
            disable_notification=True,
        )
        if sent and sent.photo:
            fid = sent.photo[-1].file_id
            try:
                await sent.delete()
            except Exception:
                pass
            return fid
    except Exception:
        pass
    return None

async def _get_check_photo_file_id(
    bot,
    user_id: int,
    total_stars: int,
    per_claim_stars: int,
    max_claims: int,
    claimed_count: int,
    has_password: bool,
    creator_name: str,
    target_label: str,
) -> Optional[str]:
    """Генерирует и загружает карточку чека с кэшем file_id для быстрого инлайн-шаринга."""
    cache_key = (
        int(user_id),
        int(per_claim_stars),
        int(max_claims),
        int(claimed_count),
        1 if has_password else 0,
        creator_name,
        target_label,
    )
    cached_fid = _CHECK_CARD_FILE_ID_CACHE.get(cache_key)
    if cached_fid:
        return cached_fid

    card_io = await generate_check_card_image(
        amount_stars=total_stars,
        creator_name=creator_name,
        target_label=target_label,
        max_claims=max_claims,
        claimed_count=claimed_count,
        per_claim_stars=per_claim_stars,
        has_password=has_password,
    )
    fid = await _upload_temp_check_photo(bot, user_id, card_io)
    if not fid:
        for adm_id in ADMIN_IDS:
            if adm_id != user_id:
                fid = await _upload_temp_check_photo(bot, adm_id, card_io)
                if fid:
                    break
    if fid:
        if len(_CHECK_CARD_FILE_ID_CACHE) >= 300:
            _CHECK_CARD_FILE_ID_CACHE.clear()
        _CHECK_CARD_FILE_ID_CACHE[cache_key] = fid
        return fid
    return None

async def _ensure_neutral_check_photo_file_id(bot, user_id: int) -> Optional[str]:
    cached = get_bot_setting("check_base_file_id_v3", "")
    if cached:
        return cached
    sample_io = await generate_check_card_image(
        amount_stars=None,
        creator_name="New NFT Bot",
        target_label="Telegram Stars Check",
    )
    fid = await _upload_temp_check_photo(bot, user_id, sample_io)
    if not fid:
        for adm_id in ADMIN_IDS:
            if adm_id != user_id:
                fid = await _upload_temp_check_photo(bot, adm_id, sample_io)
                if fid:
                    break
    if fid:
        set_bot_setting("check_base_file_id_v3", fid)
        return fid
    return None

async def on_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Инлайн-режим ТОЛЬКО делится уже созданными в боте активными чеками (создание в чате отключено)."""
    iq = update.inline_query
    if not iq:
        return
    user = iq.from_user

    if is_maintenance_mode() and user.id not in ADMIN_IDS:
        await iq.answer([
            InlineQueryResultArticle(
                id="maint",
                title="🛠 Бот на техработах",
                description="Отправка чеков временно недоступна.",
                input_message_content=InputTextMessageContent("🛠 Бот сейчас на техработах."),
            )
        ], cache_time=1, is_personal=True)
        return

    is_banned, _, _, _ = is_user_banned(user.id)
    if is_banned and user.id not in ADMIN_IDS:
        await iq.answer([
            InlineQueryResultArticle(
                id="banned",
                title="⛔️ Аккаунт заблокирован",
                description="Вы не можете отправлять чеки.",
                input_message_content=InputTextMessageContent("⛔️ Ваш аккаунт заблокирован."),
            )
        ], cache_time=1, is_personal=True)
        return

    get_or_create_user(user.id, user.username or "", user.first_name or "")
    touch_user_activity(user.id)
    bot_username = await get_bot_username(context.bot)
    q = (iq.query or "").strip()

    active_checks = get_user_active_checks(user.id)
    if q.startswith("check_") and len(q) > 6:
        req_code = q[6:].strip()
        active_checks = [c for c in active_checks if c["code"] == req_code] or active_checks

    if not active_checks:
        create_kb = InlineKeyboardMarkup([[
            make_btn("Создать чек в боте", style="primary", emoji_key="dollar", url=f"https://t.me/{bot_username}?start=checks")
        ]])
        await iq.answer([
            InlineQueryResultArticle(
                id="bot_only_checks",
                title="💳 Чеки создаются только внутри бота",
                description="Откройте бота → «💳 Чеки» (поддержка мульти-чеков и паролей).",
                input_message_content=InputTextMessageContent(
                    f"{ce('dollar')} <b>Чеки создаются только внутри бота!</b>\n"
                    f"Откройте раздел <b>«Чеки»</b> в боте, чтобы создать чек (на 1 или нескольких игроков, с паролем или без).",
                    parse_mode=ParseMode.HTML,
                ),
                reply_markup=create_kb,
            )
        ], cache_time=1, is_personal=True)
        return

    creator_name = normalize_telegram_name(user.first_name, user.username, user.id)
    results = []
    for chk in active_checks[:8]:
        code = chk["code"]
        max_c = max(1, int(chk["max_claims"] or 1))
        claimed_c = int(chk["claimed_count"] or 0)
        per_c = int(chk["per_claim_stars"] or chk["amount_stars"])
        total_s = int(chk["amount_stars"])
        has_pwd = bool(chk["has_password"])
        target_lbl = f"@{chk['target_username']}" if chk["target_username"] else (f"До {max_c} игроков" if max_c > 1 else "Все игроки")

        cap, kb = _build_shared_check_view(chk, creator_name, bot_username)
        photo_fid = await _get_check_photo_file_id(
            context.bot,
            user.id,
            total_s,
            per_c,
            max_c,
            claimed_c,
            has_pwd,
            creator_name,
            target_lbl,
        ) or await _ensure_neutral_check_photo_file_id(context.bot, user.id)

        pwd_badge = "🔐 " if has_pwd else ""
        slots_badge = f" • {max_c - claimed_c}/{max_c} мест" if max_c > 1 else ""
        title_str = f"💳 {pwd_badge}Чек на {fmt_stars_compact(per_c)} ⭐ ({target_lbl}{slots_badge})"
        desc_str = "Нажмите, чтобы отправить чек в этот чат"

        if photo_fid:
            results.append(
                InlineQueryResultCachedPhoto(
                    id=f"chk:{code}",
                    photo_file_id=photo_fid,
                    title=title_str,
                    description=desc_str,
                    caption=cap,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                )
            )
        else:
            results.append(
                InlineQueryResultArticle(
                    id=f"chk:{code}",
                    title=title_str,
                    description=desc_str,
                    input_message_content=InputTextMessageContent(cap, parse_mode=ParseMode.HTML),
                    reply_markup=kb,
                )
            )

    await iq.answer(results, cache_time=1, is_personal=True)

async def on_chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cir = update.chosen_inline_result
    if not cir:
        return
    if cir.from_user:
        touch_user_activity(cir.from_user.id)
    if not cir.result_id or not cir.result_id.startswith("chk:"):
        return

    code = cir.result_id.split(":", 1)[1]
    if not cir.inline_message_id:
        return

    set_star_check_inline_msg_id(code, cir.inline_message_id)
    chk = get_star_check(code)
    if not chk:
        return
    creator_row = get_or_create_user(chk["creator_id"], "", "")
    creator_name = normalize_telegram_name(creator_row["first_name"], creator_row["username"], chk["creator_id"])
    bot_username = await get_bot_username(context.bot)
    cap, kb = _build_shared_check_view(chk, creator_name, bot_username)
    # Редактируем инлайн-сообщение от имени бота сразу после отправки, чтобы кастомные <tg-emoji> рендерились ещё до активации чека
    edited_cap = cap + "\u200b"
    try:
        await context.bot.edit_message_caption(
            inline_message_id=cir.inline_message_id,
            caption=edited_cap,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    except Exception:
        try:
            await context.bot.edit_message_text(
                inline_message_id=cir.inline_message_id,
                text=edited_cap,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
        except Exception:
            pass

# ---------------------------------------------------------------------------
# АВТОРСТВО, ЗАЯВКИ, КАНАЛЫ И СИСТЕМА КОНКУРСОВ / РОЗЫГРЫШЕЙ
# ---------------------------------------------------------------------------

_GW_IN_PROGRESS_IDS: set[int] = set()
_GIVEAWAY_SCHEDULER_TASK: Optional[asyncio.Task] = None

def _parse_giveaway_delay_seconds(raw: str) -> Optional[int]:
    s = (raw or "").strip().lower()
    if not s:
        return None
    m = re.fullmatch(r"(\d+)\s*(м|мин|минут|минуты|m|min|ч|час|часа|часов|h|д|дн|дня|дней|d)?", s)
    if m:
        val = int(m.group(1))
        unit = m.group(2) or "м"
        if unit.startswith(("д", "d")):
            return val * 86400
        if unit.startswith(("ч", "h")):
            return val * 3600
        return val * 60
    return None

def _parse_giveaway_target_timestamp(raw: str) -> Optional[int]:
    """Парсит относительный интервал (30м, 2ч, 1д) или конкретные дату/время (18:30, 15.11 18:30, 15.11.2026 18:30)."""
    delay = _parse_giveaway_delay_seconds(raw)
    now = int(time.time())
    if delay is not None:
        return now + delay if delay > 0 else None

    s = (raw or "").strip()
    now_dt = datetime.datetime.now()
    for fmt in ("%d.%m.%Y %H:%M", "%Y-%m-%d %H:%M", "%d.%m %H:%M", "%H:%M"):
        try:
            parsed = datetime.datetime.strptime(s, fmt)
            if fmt == "%H:%M":
                dt = now_dt.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)
                if int(dt.timestamp()) <= now:
                    dt = dt + datetime.timedelta(days=1)
            elif fmt == "%d.%m %H:%M":
                dt = parsed.replace(year=now_dt.year, second=0, microsecond=0)
                if int(dt.timestamp()) <= now:
                    dt = dt.replace(year=now_dt.year + 1)
            else:
                dt = parsed.replace(second=0, microsecond=0)
            ts = int(dt.timestamp())
            return ts if ts > now else None
        except Exception:
            continue
    return None

def _fmt_dt(ts: int) -> str:
    if not ts:
        return "—"
    return datetime.datetime.fromtimestamp(int(ts)).strftime("%d.%m.%Y %H:%M")

def _style_label_ru(style: str) -> str:
    return {
        "success": "🟢 Зелёная",
        "primary": "🔵 Синяя",
        "danger": "🔴 Красная",
        "default": "⚪️ Обычная",
    }.get(style or "success", "🟢 Зелёная")

def _btn_mode_label_ru(mode: str) -> str:
    return {
        "button": "🔘 Кнопка под постом",
        "in_text": "🔗 В тексте поста",
        "both": "🔘+🔗 Кнопка + в тексте",
    }.get(mode or "button", "🔘 Кнопка под постом")

async def show_author_policy_page(query) -> None:
    text = (
        f"{ce('crown')} <b>Политика и условия Авторства</b>\n"
        "━━━━━━━━━━━━\n"
        "<blockquote expandable>"
        f"{ce('pin')} <b>1. Требования к получению авторства:</b>\n"
        f"• Игровой уровень не ниже <b>{AUTHOR_MIN_LEVEL}-го</b>.\n"
        f"• Текущий баланс на аккаунте не менее <b>{AUTHOR_MIN_BALANCE:,} {ce('star')}</b>.\n"
        "• Заполнение анкеты: указание каналов/чатов, в которых будет работать бот, и вашего возраста.\n"
        "• Заявка проходит обязательную модерацию администраторами бота.\n\n"
        f"{ce('dollar')} <b>2. Авторский баланс:</b>\n"
        "• У каждого автора открывается отдельный <b>Авторский баланс</b>.\n"
        "• Эти звёзды используются <b>исключительно для призовых фондов конкурсов</b>.\n"
        "• Вы можете свободно переводить звёзды между основным балансом и авторским балансом.\n\n"
        f"{ce('megaphone')} <b>3. Каналы, конкурсы и автовыплата:</b>\n"
        "• Перед созданием конкурса подключите нужные каналы/чаты и выдайте боту права (в канале — администратор; в чате — участник/админ).\n"
        "• Для участия каждый игрок обязан запустить бота и быть подписанным на <b>все</b> каналы конкурса.\n"
        "• После завершения конкурса (по таймеру, лимиту участников или кнопкой автора) бот <b>сам выбирает победителей, зачисляет им звёзды и отправляет чеки в ЛС</b>."
        "</blockquote>\n"
        "━━━━━━━━━━━━"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("Назад к Авторству", emoji_key="crown", callback_data="nav_author")],
        [make_btn("В профиль", emoji_key="smile", callback_data="nav_profile")],
        [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")],
    ])
    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_author_hub(query_or_msg, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_user = get_or_create_user(user_id, "", "")
    lvl, _, _, _ = calculate_xp_level_info(db_user["xp"])

    if not db_user["is_author"]:
        latest_app = get_latest_author_application_db(user_id)
        lvl_ok = ce("check") if lvl >= AUTHOR_MIN_LEVEL else ce("cross")
        bal_ok = ce("check") if int(db_user["balance_stars"] or 0) >= AUTHOR_MIN_BALANCE else ce("cross")

        app_status_block = ""
        has_pending = False
        if latest_app:
            st = latest_app["status"]
            if st == "pending":
                has_pending = True
                app_status_block = (
                    f"\n{ce('hourglass')} <b>Статус последней заявки (#{latest_app['id']}):</b> <b>На рассмотрении</b>\n"
                    f"• Каналы: <code>{clean_html(latest_app['channels_text'][:120])}</code>\n"
                    f"• Возраст: <b>{clean_html(latest_app['age_text'])}</b>\n"
                )
            elif st == "rejected":
                r_txt = clean_html(latest_app["reject_reason"]) if latest_app["reject_reason"] else "Не указана"
                app_status_block = (
                    f"\n{ce('cross')} <b>Предыдущая заявка (#{latest_app['id']}) отклонена</b>\n"
                    f"• Причина: <i>{r_txt}</i>\n"
                )

        text = (
            f"{ce('crown')} <b>Авторство в New NFT Bot</b>\n"
            "━━━━━━━━━━━━\n"
            "Статус <b>Автора</b> позволяет проводить официальные розыгрыши звёзд прямо в ваших Telegram-каналах и чатах!\n\n"
            "<blockquote expandable>"
            f"{ce('sparkles')} <b>Что даёт авторство:</b>\n"
            "• Отдельный <b>Авторский баланс</b> только для конкурсов (удобный перевод с основного баланса и обратно).\n"
            "• Поддержка любого форматирования постов: цитаты, таблицы, скрытый текст и <b>кастомные эмодзи</b>, фото.\n"
            "• Гибкая настройка кнопки участия (свой текст, цвет, кнопка под постом или ссылка в тексте).\n"
            "• Автоматическая проверка подписки на все каналы и регистрации участников в боте.\n"
            "• <b>Автовыплата:</b> по итогам конкурса бот сам переводит звёзды и отправляет чек каждому победителю!"
            "</blockquote>\n\n"
            f"{ce('pin')} <b>Условия для подачи заявки:</b>\n"
            f"• {lvl_ok} Уровень: <b>{lvl} / {AUTHOR_MIN_LEVEL}+</b>\n"
            f"• {bal_ok} Баланс: <b>{int(db_user['balance_stars']):,} / {AUTHOR_MIN_BALANCE:,} {ce('star')}</b>\n"
            f"{app_status_block}"
            "━━━━━━━━━━━━"
        )
        buttons = []
        if not has_pending:
            buttons.append([make_btn("Заполнить заявку", style="success", emoji_key="pencil", callback_data="author_apply_start")])
        buttons.append([make_btn("Политика конфиденциальности и правила", emoji_key="clip", callback_data="author_policy")])
        buttons.append([
            make_btn("В профиль", emoji_key="smile", callback_data="nav_profile"),
            make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main"),
        ])
    else:
        channels = get_author_channels_db(user_id)
        gws, total_gws = get_author_giveaways_db(user_id, page=1, page_size=50)
        active_gws = sum(1 for g in gws if g["status"] in ("active", "scheduled"))
        auth_bal = int(db_user["author_balance_stars"] or 0)
        main_bal = int(db_user["balance_stars"] or 0)

        text = (
            f"{ce('crown')} <b>Кабинет Автора</b>\n"
            "━━━━━━━━━━━━\n"
            f"{ce('star')} <b>Авторский баланс:</b> <b>{auth_bal:,} {ce('star')}</b>\n"
            f"<i>(Используется исключительно для проведения розыгрышей)</i>\n"
            f"{ce('dollar')} Основной баланс: <b>{main_bal:,} {ce('star')}</b>\n"
            f"{ce('megaphone')} Подключено каналов/чатов: <b>{len(channels)}</b>\n"
            f"{ce('boom')} Активных/заплан. конкурсов: <b>{active_gws}</b> (всего: <b>{total_gws}</b>)\n"
            "━━━━━━━━━━━━\n"
            "Выберите действие:"
        )
        buttons = [
            [make_btn("Создать конкурс", style="success", emoji_key="boom", callback_data="gw_create_start")],
            [
                make_btn("Пополнить авторский", style="primary", emoji_key="plus", callback_data="author_dep_start"),
                make_btn("Вывести на основной", emoji_key="money_wings", callback_data="author_wd_start"),
            ],
            [
                make_btn("Добавить каналы", style="primary", emoji_key="megaphone", callback_data="author_ch_add_start"),
                make_btn(f"Мои каналы ({len(channels)})", emoji_key="link", callback_data="author_channels"),
            ],
            [make_btn(f"Мои конкурсы ({total_gws})", emoji_key="trophy" if "trophy" in CE_IDS else "chart_bar", callback_data="author_giveaways:1")],
            [make_btn("Политика авторства", emoji_key="clip", callback_data="author_policy")],
            [
                make_btn("В профиль", emoji_key="smile", callback_data="nav_profile"),
                make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main"),
            ],
        ]

    kb = InlineKeyboardMarkup(buttons)
    if isinstance(query_or_msg, CallbackQuery):
        if query_or_msg.message and query_or_msg.message.photo:
            await query_or_msg.message.delete()
            await query_or_msg.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        elif query_or_msg.message:
            await query_or_msg.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        target_msg = query_or_msg.effective_message if hasattr(query_or_msg, "effective_message") else query_or_msg
        if target_msg:
            await target_msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

# --- ПОДАЧА ЗАЯВКИ НА АВТОРСТВО ---

async def author_apply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    if not await ensure_privacy_accepted_private(update, context):
        return ConversationHandler.END

    query = update.callback_query
    user = query.from_user
    if query.message and query.message.chat.type != "private":
        await query.answer("⚠️ Подавать заявку можно только в личных сообщениях с ботом!", show_alert=True)
        return ConversationHandler.END

    db_user = get_or_create_user(user.id, user.username or "", user.first_name or "")
    if db_user["is_author"]:
        await query.answer("✅ Вы уже являетесь автором!", show_alert=True)
        return ConversationHandler.END

    lvl, _, _, _ = calculate_xp_level_info(db_user["xp"])
    if lvl < AUTHOR_MIN_LEVEL:
        await query.answer(
            f"❌ Для подачи заявки на авторство нужен минимум {AUTHOR_MIN_LEVEL}-й уровень! (Ваш уровень: {lvl})",
            show_alert=True,
        )
        return ConversationHandler.END

    if int(db_user["balance_stars"] or 0) < AUTHOR_MIN_BALANCE:
        await query.answer(
            f"❌ Для подачи заявки баланс должен быть не менее {AUTHOR_MIN_BALANCE:,} ⭐! (У вас: {db_user['balance_stars']:,} ⭐)",
            show_alert=True,
        )
        return ConversationHandler.END

    latest_app = get_latest_author_application_db(user.id)
    if latest_app and latest_app["status"] == "pending":
        await query.answer("⏳ Ваша заявка уже отправлена и ожидает проверки!", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    context.user_data.pop("author_app_channels", None)
    context.user_data.pop("author_app_age", None)

    text = (
        f"{ce('crown')} <b>Заявка на Авторство — Шаг 1 из 2</b>\n"
        "━━━━━━━━━━━━\n"
        "Укажите <b>канал(ы) или чат(ы)</b> (ссылки или <code>@username</code>, можно несколько через запятую или с новой строки), "
        "в которых будет добавлен бот для проведения конкурсов или новостей:"
    )
    kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="author_apply_cancel")]])
    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_AUTHOR_APP_CHANNELS

async def author_apply_channels_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    ch_text = (update.message.text or "").strip()
    if len(ch_text) < 3 or len(ch_text) > 500:
        await update.message.reply_text(
            f"{ce('cross')} Укажите корректный список каналов (от 3 до 500 символов):",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_AUTHOR_APP_CHANNELS

    context.user_data["author_app_channels"] = ch_text
    kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="author_apply_cancel")]])
    await update.message.reply_text(
        f"{ce('crown')} <b>Заявка на Авторство — Шаг 2 из 2</b>\n"
        "━━━━━━━━━━━━\n"
        "Сколько вам <b>лет</b>? Напишите число (например: <code>18</code>):",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAIT_AUTHOR_APP_AGE

async def author_apply_age_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    raw_age = (update.message.text or "").strip()
    digits = re.sub(r"\D", "", raw_age)
    if not digits or int(digits) < 10 or int(digits) > 99:
        await update.message.reply_text(
            f"{ce('cross')} Введите корректный возраст числом (от 10 до 99):",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_AUTHOR_APP_AGE

    context.user_data["author_app_age"] = digits
    ch_text = context.user_data.get("author_app_channels", "")
    kb = InlineKeyboardMarkup([
        [make_btn("Подать заявку", style="success", emoji_key="check", callback_data="author_apply_submit")],
        [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="author_apply_cancel")],
    ])
    await update.message.reply_text(
        f"{ce('crown')} <b>Проверьте заявку перед отправкой:</b>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('megaphone')} <b>Каналы/чаты:</b>\n<code>{clean_html(ch_text)}</code>\n"
        f"{ce('smile')} <b>Возраст:</b> <b>{digits}</b>\n"
        "━━━━━━━━━━━━\n"
        "Нажмите <b>«Подать заявку»</b>, чтобы отправить анкету администраторам:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAIT_AUTHOR_APP_CONFIRM

async def author_apply_submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    query = update.callback_query
    user = query.from_user
    ch_text = context.user_data.pop("author_app_channels", "")
    age_text = context.user_data.pop("author_app_age", "")
    if not ch_text or not age_text:
        await query.answer("❌ Сессия анкеты устарела.", show_alert=True)
        return ConversationHandler.END

    ok, err_m, app_row = submit_author_application_db(user.id, ch_text, age_text)
    if not ok or not app_row:
        await query.answer(f"❌ {err_m}", show_alert=True)
        await show_author_hub(query, user.id, context)
        return ConversationHandler.END

    await query.answer("✅ Заявка отправлена администраторам!")
    await show_author_hub(query, user.id, context)

    db_user = get_or_create_user(user.id, user.username or "", user.first_name or "")
    lvl, _, _, _ = calculate_xp_level_info(db_user["xp"])
    disp_name = normalize_telegram_name(db_user["first_name"], db_user["username"], user.id)
    uname_part = f" (@{clean_html(db_user['username'])})" if db_user["username"] else ""
    adm_text = (
        f"{ce('crown')} <b>Новая заявка на Авторство (#{app_row['id']})</b>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('smile')} Игрок: <b>{clean_html(disp_name)}</b>{uname_part} (ID: <code>{user.id}</code>)\n"
        f"{ce('bolt')} Уровень: <b>{lvl}</b> • {ce('dollar')} Баланс: <b>{db_user['balance_stars']:,} {ce('star')}</b>\n"
        f"{ce('megaphone')} Каналы: <code>{clean_html(ch_text)}</code>\n"
        f"{ce('info')} Возраст: <b>{clean_html(age_text)}</b>"
    )
    adm_kb = InlineKeyboardMarkup([
        [make_btn("Открыть заявку", style="primary", emoji_key="eyes", callback_data=f"admin_author_app:{app_row['id']}")],
        [make_btn("Все заявки", emoji_key="crown", callback_data="admin_author_apps:1")],
    ])
    for adm_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=adm_id, text=adm_text, parse_mode=ParseMode.HTML, reply_markup=adm_kb)
        except Exception:
            pass
    return ConversationHandler.END

async def author_apply_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("author_app_channels", None)
    context.user_data.pop("author_app_age", None)
    if update.callback_query:
        await update.callback_query.answer("Отменено.")
        await show_author_hub(update.callback_query, update.callback_query.from_user.id, context)
    elif update.message:
        await update.message.reply_text("❌ Подача заявки отменена.", reply_markup=quick_nav_keyboard())
    return ConversationHandler.END

# --- АДМИН: ПРОВЕРКА ЗАЯВОК И ВЫДАЧА АВТОРСКИХ ЗВЁЗД ---

async def show_admin_author_apps_page(query, page: int = 1) -> None:
    page_size = 8
    rows, total, pending_cnt = list_author_applications_db(page=page, page_size=page_size)
    total_pages = max(1, math.ceil(total / page_size))
    page = max(1, min(page, total_pages))

    lines = [
        f"{ce('crown')} <b>Заявки на Авторство (ожидают: {pending_cnt})</b>",
        "━━━━━━━━━━━━",
    ]
    buttons = []
    if not rows:
        lines.append("<i>Заявок пока нет.</i>")
    else:
        for r in rows:
            st = r["status"]
            st_icon = "⏳" if st == "pending" else ("✅" if st == "approved" else "❌")
            u_name = normalize_telegram_name(r["first_name"], r["username"], r["user_id"])
            dt_s = datetime.datetime.fromtimestamp(int(r["created_ts"])).strftime("%d.%m %H:%M")
            lines.append(f"{st_icon} <b>#{r['id']}</b> — {clean_html(u_name)} ({dt_s})")
            buttons.append([
                make_btn(
                    f"{st_icon} #{r['id']} {u_name[:18]} (возр. {r['age_text']})",
                    style="primary" if st == "pending" else None,
                    callback_data=f"admin_author_app:{r['id']}",
                )
            ])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin_author_apps:{page-1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin_author_apps:{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([make_btn("В админ-панель", emoji_key="crown", callback_data="admin_panel")])

    text = "\n".join(lines)
    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def show_admin_author_app_detail(query, app_id: int) -> None:
    app_row = get_author_application_by_id_db(app_id)
    if not app_row:
        await query.answer("❌ Заявка не найдена.", show_alert=True)
        return
    u_name = normalize_telegram_name(app_row["first_name"], app_row["username"], app_row["user_id"])
    uname_part = f" (@{clean_html(app_row['username'])})" if app_row["username"] else ""
    lvl, _, _, _ = calculate_xp_level_info(app_row["xp"] or 0)
    st_ru = {
        "pending": f"{ce('hourglass')} Ожидает проверки",
        "approved": f"{ce('check')} Одобрена",
        "rejected": f"{ce('cross')} Отклонена",
    }.get(app_row["status"], app_row["status"])
    rej_line = f"\n• Причина отказа: <i>{clean_html(app_row['reject_reason'])}</i>" if app_row["reject_reason"] else ""

    text = (
        f"{ce('crown')} <b>Заявка на Авторство #{app_row['id']}</b>\n"
        "━━━━━━━━━━━━\n"
        f"• Статус: <b>{st_ru}</b>{rej_line}\n"
        f"• Игрок: <b>{clean_html(u_name)}</b>{uname_part}\n"
        f"• Telegram ID: <code>{app_row['user_id']}</code>\n"
        f"• Уровень: <b>{lvl}</b> • Баланс: <b>{int(app_row['balance_stars'] or 0):,} {ce('star')}</b>\n"
        f"• Выбито подарков: <b>{int(app_row['total_drops'] or 0)}</b>\n"
        f"• Возраст: <b>{clean_html(app_row['age_text'])}</b>\n"
        f"• Подана: <code>{_fmt_dt(app_row['created_ts'])}</code>\n\n"
        f"{ce('megaphone')} <b>Указанные каналы/чаты:</b>\n"
        f"<code>{clean_html(app_row['channels_text'])}</code>"
    )
    buttons = []
    if app_row["status"] == "pending":
        buttons.append([
            make_btn("Принять", style="success", emoji_key="check", callback_data=f"admin_app_approve:{app_id}"),
            make_btn("Отклонить", style="danger", emoji_key="cross", callback_data=f"admin_app_reject_start:{app_id}"),
        ])
    buttons.append([InlineKeyboardButton("◀️ К списку заявок", callback_data="admin_author_apps:1")])
    buttons.append([make_btn("В админ-панель", emoji_key="crown", callback_data="admin_panel")])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def execute_admin_approve_author_app(query, admin_id: int, app_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    ok, err_m, app_row = review_author_application_db(app_id, admin_id, approve=True)
    if not ok or not app_row:
        await query.answer(f"❌ {err_m}", show_alert=True)
        return
    await query.answer("✅ Заявка принята! Пользователь стал автором.", show_alert=True)
    await show_admin_author_app_detail(query, app_id)

    try:
        await context.bot.send_message(
            chat_id=app_row["user_id"],
            text=(
                f"{ce('boom')} <b>Поздравляем! Ваша заявка на Авторство (#{app_id}) одобрена!</b>\n"
                "━━━━━━━━━━━━\n"
                f"{ce('crown')} Теперь вам доступен <b>Кабинет Автора</b> в профиле:\n"
                "• Отдельный <b>Авторский баланс</b> для розыгрышей\n"
                "• Подключение своих Telegram-каналов и чатов\n"
                "• Создание конкурсов с автоматическими чеками победителям!"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [make_btn("Открыть Кабинет Автора", style="success", emoji_key="crown", callback_data="nav_author")],
                [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")],
            ]),
        )
    except Exception:
        pass

async def admin_app_reject_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Доступ запрещен!", show_alert=True)
        return ConversationHandler.END
    app_id = int(query.data.split(":")[1])
    app_row = get_author_application_by_id_db(app_id)
    if not app_row or app_row["status"] != "pending":
        await query.answer("❌ Заявка уже рассмотрена.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    context.user_data["admin_reject_app_id"] = app_id
    kb = InlineKeyboardMarkup([
        [make_btn("Отклонить без причины", style="danger", emoji_key="cross", callback_data="admin_app_reject_nomsg")],
        [make_btn("Отмена", emoji_key="cross", callback_data="admin_cancel")],
    ])
    await query.edit_message_text(
        f"{ce('cross')} <b>Отклонение заявки #{app_id}</b>\n\n"
        "Введите причину отказа (она будет отправлена игроку) или нажмите «Отклонить без причины»:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAIT_ADMIN_APP_REJECT_REASON

async def _finish_admin_reject_app(reply_target, admin_id: int, app_id: int, reason: str, context: ContextTypes.DEFAULT_TYPE, is_cb: bool = False):
    ok, err_m, app_row = review_author_application_db(app_id, admin_id, approve=False, reject_reason=reason)
    if not ok or not app_row:
        txt = f"❌ {err_m}"
        if is_cb:
            await reply_target.edit_message_text(txt)
        else:
            await reply_target.reply_text(txt)
        return ConversationHandler.END

    r_note = f"\n• Причина: <i>{clean_html(reason)}</i>" if reason else ""
    try:
        await context.bot.send_message(
            chat_id=app_row["user_id"],
            text=(
                f"{ce('cross')} <b>Ваша заявка на Авторство (#{app_id}) отклонена администрацией.</b>{r_note}\n\n"
                "Вы можете исправить замечания и подать новую заявку из профиля."
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard(),
        )
    except Exception:
        pass

    done_txt = f"{ce('cross')} Заявка <b>#{app_id}</b> отклонена.{r_note}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ К списку заявок", callback_data="admin_author_apps:1")],
        [make_btn("В админ-панель", emoji_key="crown", callback_data="admin_panel")],
    ])
    if is_cb:
        await reply_target.edit_message_text(done_txt, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await reply_target.reply_text(done_txt, parse_mode=ParseMode.HTML, reply_markup=kb)
    return ConversationHandler.END

async def admin_app_reject_reason_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    app_id = int(context.user_data.pop("admin_reject_app_id", 0))
    reason = (update.message.text or "").strip()[:300]
    return await _finish_admin_reject_app(update.message, update.effective_user.id, app_id, reason, context, is_cb=False)

async def admin_app_reject_nomsg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    await query.answer("Заявка отклонена.")
    app_id = int(context.user_data.pop("admin_reject_app_id", 0))
    return await _finish_admin_reject_app(query, query.from_user.id, app_id, "", context, is_cb=True)

async def admin_give_author_stars_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Доступ запрещен!", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    text = f"{ce('crown')} <b>Выдача Авторских Звёзд</b>\n\nВведите Telegram ID или @username автора:"
    kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="admin_cancel")]])
    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_ADMIN_GIVE_AUTH_STARS_USER

async def admin_give_author_stars_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    target = get_user_by_target((update.message.text or "").strip())
    if not target:
        await update.message.reply_text("❌ Пользователь не найден. Попробуйте снова:")
        return WAIT_ADMIN_GIVE_AUTH_STARS_USER
    context.user_data["admin_auth_stars_uid"] = target["user_id"]
    tname = normalize_telegram_name(target["first_name"], target["username"], target["user_id"])
    await update.message.reply_text(
        f"✅ Игрок: <b>{clean_html(tname)}</b> (Авторский баланс: <b>{int(target['author_balance_stars'] or 0):,} ⭐</b>).\n\n"
        "Введите количество Авторских Звёзд для начисления:",
        parse_mode=ParseMode.HTML,
    )
    return WAIT_ADMIN_GIVE_AUTH_STARS_AMOUNT

async def admin_give_author_stars_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    raw = re.sub(r"[\s,_.]", "", (update.message.text or "").strip())
    if not raw.isdigit() or int(raw) <= 0:
        await update.message.reply_text("❌ Введите положительное число звёзд:")
        return WAIT_ADMIN_GIVE_AUTH_STARS_AMOUNT
    amount = int(raw)
    target_id = int(context.user_data.pop("admin_auth_stars_uid", 0))
    ok, new_bal = add_author_balance_admin_db(target_id, amount)
    if not ok:
        await update.message.reply_text("❌ Ошибка начисления.")
        return ConversationHandler.END
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                f"{ce('crown')} <b>На ваш Авторский баланс начислено +{amount:,} {ce('star')} от Администрации!</b>\n"
                f"{ce('dollar')} Текущий авторский баланс: <b>{new_bal:,} {ce('star')}</b>"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[make_btn("Кабинет Автора", style="primary", emoji_key="crown", callback_data="nav_author")]]),
        )
    except Exception:
        pass
    await update.message.reply_text(
        f"✅ Начислено <b>+{amount:,} ⭐</b> на авторский баланс (ID <code>{target_id}</code>). Новый баланс: <b>{new_bal:,} ⭐</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[make_btn("В админ-панель", emoji_key="crown", callback_data="admin_panel")]]),
    )
    return ConversationHandler.END

# --- АВТОРСКИЙ БАЛАНС (ПОПОЛНЕНИЕ / ВЫВОД) ---

async def author_dep_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    db_user = get_or_create_user(user.id, user.username or "", user.first_name or "")
    if not db_user["is_author"]:
        await query.answer("❌ Доступно только авторам!", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="author_bal_cancel")]])
    await query.edit_message_text(
        f"{ce('plus')} <b>Пополнение Авторского баланса</b>\n"
        "━━━━━━━━━━━━\n"
        f"• Основной баланс: <b>{db_user['balance_stars']:,} {ce('star')}</b>\n"
        f"• Авторский баланс: <b>{int(db_user['author_balance_stars'] or 0):,} {ce('star')}</b>\n\n"
        "Введите сумму Stars для перевода с основного баланса на авторский (используются только для конкурсов):",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAIT_AUTHOR_DEP_AMOUNT

async def author_dep_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = re.sub(r"[\s,_.]", "", (update.message.text or "").strip())
    if not raw.isdigit() or int(raw) <= 0:
        await update.message.reply_text("❌ Введите положительное число звёзд (или /cancel):")
        return WAIT_AUTHOR_DEP_AMOUNT
    amount = int(raw)
    ok, msg_err, new_main, new_auth = transfer_author_balance_db(update.effective_user.id, amount, to_author=True)
    if not ok:
        await update.message.reply_text(f"❌ {msg_err}")
        return WAIT_AUTHOR_DEP_AMOUNT
    await update.message.reply_text(
        f"{ce('check')} <b>Переведено +{amount:,} {ce('star')} на Авторский баланс!</b>\n"
        f"• Авторский баланс: <b>{new_auth:,} {ce('star')}</b>\n"
        f"• Основной баланс: <b>{new_main:,} {ce('star')}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[make_btn("Кабинет Автора", style="primary", emoji_key="crown", callback_data="nav_author")]]),
    )
    return ConversationHandler.END

async def author_wd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    db_user = get_or_create_user(user.id, user.username or "", user.first_name or "")
    if not db_user["is_author"]:
        await query.answer("❌ Доступно только авторам!", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="author_bal_cancel")]])
    await query.edit_message_text(
        f"{ce('money_wings')} <b>Вывод с Авторского баланса на основной</b>\n"
        "━━━━━━━━━━━━\n"
        f"• Авторский баланс: <b>{int(db_user['author_balance_stars'] or 0):,} {ce('star')}</b>\n"
        f"• Основной баланс: <b>{db_user['balance_stars']:,} {ce('star')}</b>\n\n"
        "Введите сумму Stars для возврата на основной баланс:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAIT_AUTHOR_WD_AMOUNT

async def author_wd_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = re.sub(r"[\s,_.]", "", (update.message.text or "").strip())
    if not raw.isdigit() or int(raw) <= 0:
        await update.message.reply_text("❌ Введите положительное число звёзд (или /cancel):")
        return WAIT_AUTHOR_WD_AMOUNT
    amount = int(raw)
    ok, msg_err, new_main, new_auth = transfer_author_balance_db(update.effective_user.id, amount, to_author=False)
    if not ok:
        await update.message.reply_text(f"❌ {msg_err}")
        return WAIT_AUTHOR_WD_AMOUNT
    await update.message.reply_text(
        f"{ce('check')} <b>Выведено {amount:,} {ce('star')} на основной баланс!</b>\n"
        f"• Основной баланс: <b>{new_main:,} {ce('star')}</b>\n"
        f"• Авторский баланс: <b>{new_auth:,} {ce('star')}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[make_btn("Кабинет Автора", style="primary", emoji_key="crown", callback_data="nav_author")]]),
    )
    return ConversationHandler.END

async def author_bal_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer("Отменено.")
        await show_author_hub(update.callback_query, update.callback_query.from_user.id, context)
    elif update.message:
        await update.message.reply_text("❌ Операция отменена.", reply_markup=quick_nav_keyboard())
    return ConversationHandler.END

# --- КАНАЛЫ АВТОРА (ДОБАВЛЕНИЕ И ПРОВЕРКА ПРАВ БОТА) ---

async def show_author_channels_page(query, user_id: int) -> None:
    channels = get_author_channels_db(user_id)
    lines = [
        f"{ce('megaphone')} <b>Подключённые каналы и чаты ({len(channels)})</b>",
        "━━━━━━━━━━━━",
    ]
    buttons = [[make_btn("Добавить канал / чат", style="success", emoji_key="plus", callback_data="author_ch_add_start")]]
    if not channels:
        lines.append("<i>У вас пока нет подключённых каналов. Добавьте канал и назначьте туда бота!</i>")
    else:
        for idx, ch in enumerate(channels, start=1):
            uname = f"@{ch['username']}" if ch["username"] else f"ID {ch['chat_id']}"
            lines.append(f"{idx}. {ce('check')} <b>{clean_html(ch['title'] or uname)}</b> (<code>{clean_html(uname)}</code>)")
            buttons.append([
                make_btn(f"Удалить {ch['title'][:18] or uname}", style="danger", emoji_key="trash", callback_data=f"author_ch_del:{ch['id']}")
            ])
    buttons.append([make_btn("Кабинет Автора", emoji_key="crown", callback_data="nav_author")])
    text = "\n".join(lines)
    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def author_ch_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    db_user = get_or_create_user(user.id, user.username or "", user.first_name or "")
    if not db_user["is_author"]:
        await query.answer("❌ Доступно только авторам!", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    bot_username = await get_bot_username(context.bot)
    kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="author_ch_add_cancel")]])
    await query.edit_message_text(
        f"{ce('megaphone')} <b>Подключение канала или чата</b>\n"
        "━━━━━━━━━━━━\n"
        f"Отправьте <code>@username</code> канала/группы (например <code>@mychannel</code>), ссылку <code>https://t.me/...</code>, "
        f"числовой ID (<code>-100...</code>) или просто <b>перешлите сюда любой пост из вашего канала</b>.\n\n"
        f"<i>Важно: бот @{clean_html(bot_username)} должен быть добавлен в канал как администратор (или в группу как участник/админ).</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAIT_AUTHOR_CHANNEL_INPUT

async def _check_bot_in_target_chat(bot, chat_id: int, chat_type: str) -> Tuple[bool, str]:
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id=chat_id, user_id=me.id)
        status = getattr(member, "status", "")
        if chat_type == "channel":
            if status in ("administrator", "creator"):
                return True, "OK"
            return False, "Бот найден в канале, но не назначен администратором с правом публикации сообщений."
        if status in ("member", "administrator", "creator"):
            return True, "OK"
        return False, "Бот пока не состоит в этом чате."
    except Exception as e:
        return False, f"Бот ещё не добавлен в этот канал/чат или не имеет доступа ({e})."

async def author_ch_input_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user
    chat_ref = None

    fwd_origin = getattr(msg, "forward_origin", None)
    if fwd_origin and getattr(fwd_origin, "chat", None):
        chat_ref = fwd_origin.chat.id
    elif getattr(msg, "forward_from_chat", None):
        chat_ref = msg.forward_from_chat.id
    else:
        raw = (msg.text or "").strip()
        m_link = re.search(r"(?:https?://)?t\.me/([A-Za-z0-9_]{4,})", raw)
        if m_link:
            chat_ref = "@" + m_link.group(1)
        elif raw.startswith("@"):
            chat_ref = raw.split()[0]
        elif re.fullmatch(r"-?\d{6,20}", raw):
            chat_ref = int(raw)

    if not chat_ref:
        await msg.reply_text(
            f"{ce('cross')} Не удалось распознать канал. Отправьте <code>@username</code>, ссылку <code>t.me/...</code>, ID <code>-100...</code> или перешлите пост из канала:",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_AUTHOR_CHANNEL_INPUT

    try:
        chat_obj = await context.bot.get_chat(chat_ref)
    except Exception:
        bot_username = await get_bot_username(context.bot)
        await msg.reply_text(
            f"{ce('warn')} Не удалось найти канал/чат <code>{clean_html(str(chat_ref))}</code>.\n"
            f"Убедитесь, что вы уже добавили бота <b>@{clean_html(bot_username)}</b> в этот канал (администратором) или чат, и отправьте <code>@username</code> / перешлите пост ещё раз:",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_AUTHOR_CHANNEL_INPUT

    if chat_obj.type not in ("channel", "group", "supergroup"):
        await msg.reply_text("❌ Можно подключать только Telegram-каналы или группы.")
        return WAIT_AUTHOR_CHANNEL_INPUT

    cand = {
        "chat_id": int(chat_obj.id),
        "username": chat_obj.username or "",
        "title": chat_obj.title or (f"@{chat_obj.username}" if chat_obj.username else str(chat_obj.id)),
        "chat_type": chat_obj.type,
    }
    ok_bot, err_bot = await _check_bot_in_target_chat(context.bot, cand["chat_id"], cand["chat_type"])
    if ok_bot:
        upsert_author_channel_db(user.id, cand["chat_id"], cand["username"], cand["title"], cand["chat_type"])
        context.user_data.pop("pending_author_channel", None)
        await msg.reply_text(
            f"{ce('check')} <b>Канал успешно подключён!</b>\n\n"
            f"{ce('megaphone')} <b>{clean_html(cand['title'])}</b>"
            + (f" (@{clean_html(cand['username'])})" if cand["username"] else ""),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [make_btn("Мои каналы", style="primary", emoji_key="link", callback_data="author_channels")],
                [make_btn("Создать конкурс", style="success", emoji_key="boom", callback_data="gw_create_start")],
                [make_btn("Кабинет Автора", emoji_key="crown", callback_data="nav_author")],
            ]),
        )
        return ConversationHandler.END

    context.user_data["pending_author_channel"] = cand
    bot_username = await get_bot_username(context.bot)
    await msg.reply_text(
        f"{ce('hourglass')} <b>Почти готово: {clean_html(cand['title'])}</b>\n\n"
        f"{clean_html(err_bot)}\n\n"
        f"1️⃣ Добавьте бота <b>@{clean_html(bot_username)}</b> в <b>{clean_html(cand['title'])}</b> "
        f"({'администратором' if cand['chat_type'] == 'channel' else 'участником/админом'}).\n"
        "2️⃣ Нажмите кнопку <b>«Проверить подключение»</b> ниже:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [make_btn("Проверить подключение", style="success", emoji_key="refresh", callback_data="verify_author_channel")],
            [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="author_ch_add_cancel")],
        ]),
    )
    return ConversationHandler.END

async def handle_verify_author_channel(query, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    cand = context.user_data.get("pending_author_channel")
    if not cand:
        await query.answer("❌ Нет канала для проверки. Начните добавление заново.", show_alert=True)
        return
    ok_bot, err_bot = await _check_bot_in_target_chat(context.bot, cand["chat_id"], cand["chat_type"])
    if not ok_bot:
        await query.answer(f"⏳ Пока не подключено: {err_bot[:140]}", show_alert=True)
        return
    upsert_author_channel_db(user_id, cand["chat_id"], cand["username"], cand["title"], cand["chat_type"])
    context.user_data.pop("pending_author_channel", None)
    await query.answer("✅ Канал подтверждён и добавлен!", show_alert=True)
    await show_author_channels_page(query, user_id)

async def author_ch_add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("pending_author_channel", None)
    if update.callback_query:
        await update.callback_query.answer("Отменено.")
        await show_author_hub(update.callback_query, update.callback_query.from_user.id, context)
    elif update.message:
        await update.message.reply_text("❌ Добавление канала отменено.", reply_markup=quick_nav_keyboard())
    return ConversationHandler.END

# --- КОНКУРСЫ: ОТОБРАЖЕНИЕ ПОСТА, ПУБЛИКАЦИЯ, УЧАСТИЕ, ИТОГИ ---

def build_giveaway_post_content(
    gw: sqlite3.Row,
    participants_count: int,
    bot_username: str,
    winners_info: Optional[list[dict]] = None,
) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    code = gw["code"]
    per_w = int(gw["per_winner_stars"] or 0)
    winners_c = max(1, int(gw["winners_count"] or 1))
    btn_text = (gw["btn_text"] or "Участвовать").strip()
    btn_style = gw["btn_style"] or "success"
    btn_mode = gw["btn_mode"] or "button"
    max_p = int(gw["max_participants"] or 0)
    is_finished = (gw["status"] == "finished" or winners_info is not None)

    footer_lines: list[str] = []
    if is_finished:
        parts_lbl = f"{participants_count:,}/{max_p:,}" if max_p > 0 else f"{participants_count:,}"
        footer_lines = [
            "\n\n━━━━━━━━━━━━",
            f"{ce('star')} Приз: <b>{per_w:,} {ce('star')}</b> × <b>{winners_c}</b> побед.",
            f"{ce('smile')} Участников: <b>{parts_lbl}</b>",
            f"{ce('check')} <b>Конкурс завершён!</b>",
        ]
        if winners_info:
            footer_lines.append(f"\n{ce('crown')} <b>Победители (звёзды и чеки выданы автоматически):</b>")
            for idx_w, w in enumerate(winners_info[:15], start=1):
                w_disp = f"@{clean_html(w['username'])}" if w.get("username") else clean_html(w.get("first_name") or f"ID {w['user_id']}")
                footer_lines.append(f"{idx_w}. <b>{w_disp}</b> — <b>+{int(w['amount_stars']):,} {ce('star')}</b>")
        else:
            footer_lines.append("<i>Участников не было — призовой фонд возвращён автору.</i>")
        kb = None
    else:
        # В активном канальном посте НЕ добавляем нижние приписки со статистикой и условиями
        deep_url = f"https://t.me/{bot_username}?start=gw_{code}"
        if btn_mode in ("in_text", "both"):
            footer_lines.append(
                f"\n\n{ce('arrow_right')} <a href=\"{deep_url}\"><b>{clean_html(btn_text)}</b></a>"
            )

        if btn_mode in ("button", "both"):
            style_arg = btn_style if btn_style in ("primary", "success", "danger") else None
            kb = InlineKeyboardMarkup([[
                make_btn(
                    f"{btn_text} ({participants_count})",
                    style=style_arg,
                    emoji_key="sparkles",
                    url=deep_url,
                )
            ]])
        else:
            kb = None

    body = gw["text_html"] or ""
    footer_str = "\n".join(footer_lines)
    full_text = body + footer_str
    # Безопасная защита видимых лимитов Telegram (1024 для caption, 4096 для текста) без подсчёта HTML-тегов <tg-emoji>/<a href> и без разрыва тегов
    limit = 1020 if gw["photo_file_id"] else 4090
    if _telegram_visible_len(full_text) > limit:
        max_body_vis = max(0, limit - _telegram_visible_len(footer_str) - 3)
        tokens = re.findall(
            r"<tg-emoji\b[^>]*>.*?</tg-emoji>|<[^>]+>|&[a-zA-Z0-9#]+;|.",
            body,
            flags=re.DOTALL,
        )
        kept: list[str] = []
        vis_acc = 0
        for tok in tokens:
            if tok.startswith("<tg-emoji"):
                inner = re.sub(r"<[^>]+>", "", tok)
                t_vis = len(html.unescape(inner)) or 1
                if vis_acc + t_vis > max_body_vis:
                    break
                kept.append(tok)
                vis_acc += t_vis
            elif tok.startswith("<"):
                kept.append(tok)
            else:
                if vis_acc + 1 > max_body_vis:
                    break
                kept.append(tok)
                vis_acc += 1

        cut = "".join(kept)
        if body and len(cut) < len(body) and max_body_vis >= 3:
            cut = cut.rstrip() + "..."
        open_tags: list[str] = []
        for m_tag in re.finditer(r"<(/?)([a-zA-Z0-9-]+)(?:\s[^>]*)?>", cut):
            is_close = bool(m_tag.group(1))
            tname = m_tag.group(2).lower()
            if not is_close:
                open_tags.append(tname)
            elif open_tags and tname in open_tags:
                idx_r = len(open_tags) - 1 - open_tags[::-1].index(tname)
                open_tags.pop(idx_r)
        closing = "".join(f"</{t}>" for t in reversed(open_tags))
        full_text = cut + closing + footer_str
    return full_text, kb

async def publish_giveaway_to_channels(bot, gw: sqlite3.Row) -> list[dict]:
    gw_id = int(gw["id"])
    if gw_id in _GW_IN_PROGRESS_IDS:
        return []
    _GW_IN_PROGRESS_IDS.add(gw_id)
    try:
        bot_username = await get_bot_username(bot)
        channels = json.loads(gw["channels_json"] or "[]")
        p_count = get_giveaway_participants_count_db(gw_id)
        post_text, post_kb = build_giveaway_post_content(gw, p_count, bot_username)
        preview_kwargs = _build_link_preview_kwargs(gw["text_html"] or "")
        posted: list[dict] = []
        for ch in channels:
            cid = int(ch["chat_id"])
            try:
                if gw["photo_file_id"]:
                    sent = await bot.send_photo(
                        chat_id=cid,
                        photo=gw["photo_file_id"],
                        caption=post_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=post_kb,
                    )
                else:
                    sent = await bot.send_message(
                        chat_id=cid,
                        text=post_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=post_kb,
                        **preview_kwargs,
                    )
                posted.append({"chat_id": cid, "message_id": int(sent.message_id)})
            except Exception as e:
                log.warning("Не удалось опубликовать конкурс #%s в чат %s: %s", gw_id, cid, e)
        set_giveaway_posted_messages_db(gw_id, posted, new_status="active")
        return posted
    finally:
        _GW_IN_PROGRESS_IDS.discard(gw_id)

async def refresh_giveaway_channel_posts(bot, gw: sqlite3.Row, p_count: int, winners_info: Optional[list[dict]] = None) -> None:
    posted = json.loads(gw["posted_messages_json"] or "[]")
    if not posted:
        return
    bot_username = await get_bot_username(bot)
    is_finished = (gw["status"] == "finished" or winners_info is not None)
    post_text, post_kb = build_giveaway_post_content(gw, p_count, bot_username, winners_info=winners_info)
    preview_kwargs = _build_link_preview_kwargs(gw["text_html"] or "")
    for item in posted:
        cid = int(item["chat_id"])
        mid = int(item["message_id"])
        try:
            if not is_finished:
                await bot.edit_message_reply_markup(
                    chat_id=cid,
                    message_id=mid,
                    reply_markup=post_kb,
                )
            elif gw["photo_file_id"]:
                await bot.edit_message_caption(
                    chat_id=cid,
                    message_id=mid,
                    caption=post_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=post_kb,
                )
            else:
                await bot.edit_message_text(
                    chat_id=cid,
                    message_id=mid,
                    text=post_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=post_kb,
                    **preview_kwargs,
                )
        except Exception:
            pass

async def finalize_giveaway_and_notify(bot, gw_id: int) -> None:
    if gw_id in _GW_IN_PROGRESS_IDS:
        return
    _GW_IN_PROGRESS_IDS.add(gw_id)
    try:
        ok, upd_gw, winners_info, refund = finalize_giveaway_db(gw_id)
        if not ok or not upd_gw:
            return

        p_count = get_giveaway_participants_count_db(gw_id)
        await refresh_giveaway_channel_posts(bot, upd_gw, p_count, winners_info=winners_info)

        author_row = get_or_create_user(upd_gw["author_id"], "", "")
        author_name = normalize_telegram_name(author_row["first_name"], author_row["username"], upd_gw["author_id"])

        for w in winners_info:
            w_uid = int(w["user_id"])
            amt = int(w["amount_stars"])
            chk_code = w["check_code"]
            w_label = f"@{w['username']}" if w.get("username") else (w.get("first_name") or f"ID {w_uid}")
            cap = (
                f"{ce('boom')} <b>Вы победили в конкурсе ({clean_html(upd_gw['code'])})!</b>\n"
                "━━━━━━━━━━━━\n"
                f"{ce('crown')} Организатор: <b>{clean_html(author_name)}</b>\n"
                f"{ce('dollar')} Выигрыш: <b>+{fmt_stars_rub(amt)}</b>\n"
                f"{ce('check')} Официальный чек <code>{chk_code}</code> сформирован и <b>уже автоматически зачислен на ваш баланс</b>!"
            )
            kb = quick_nav_keyboard()
            try:
                card_io = await generate_check_card_image(
                    amount_stars=amt,
                    creator_name=author_name,
                    target_label=w_label,
                    claimed_by=w_label,
                    max_claims=1,
                    claimed_count=1,
                    per_claim_stars=amt,
                    has_password=False,
                )
                await bot.send_photo(
                    chat_id=w_uid,
                    photo=InputFile(card_io, filename=f"winner_check_{chk_code}.png"),
                    caption=cap,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                )
            except Exception:
                try:
                    await bot.send_message(chat_id=w_uid, text=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
                except Exception:
                    pass

        w_lines = []
        for idx_w, w in enumerate(winners_info, start=1):
            wd = f"@{clean_html(w['username'])}" if w.get("username") else clean_html(w.get("first_name") or f"ID {w['user_id']}")
            w_lines.append(f"{idx_w}. <b>{wd}</b> — +{int(w['amount_stars']):,} {ce('star')} (чек <code>{w['check_code']}</code>)")
        refund_note = f"\n{ce('refresh')} Остаток призового фонда <b>+{refund:,} {ce('star')}</b> возвращён на авторский баланс." if refund > 0 else ""
        try:
            await bot.send_message(
                chat_id=upd_gw["author_id"],
                text=(
                    f"{ce('check')} <b>Ваш конкурс #{upd_gw['id']} ({upd_gw['code']}) завершён!</b>\n"
                    "━━━━━━━━━━━━\n"
                    f"{ce('smile')} Всего участников: <b>{p_count}</b>\n"
                    f"{ce('crown')} Выбрано победителей: <b>{len(winners_info)}</b>\n"
                    + ("\n".join(w_lines) if w_lines else "<i>Участников не было.</i>")
                    + f"{refund_note}\n\n"
                    f"{ce('dollar')} Все звёзды и чеки выплачены победителям автоматически!"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[make_btn("Кабинет Автора", emoji_key="crown", callback_data="nav_author")]]),
            )
        except Exception:
            pass
    finally:
        _GW_IN_PROGRESS_IDS.discard(gw_id)

async def _check_user_subscriptions_for_giveaway(bot, user_id: int, channels: list[dict]) -> Tuple[bool, list[dict]]:
    missing: list[dict] = []
    for ch in channels:
        cid = int(ch["chat_id"])
        try:
            m = await bot.get_chat_member(chat_id=cid, user_id=user_id)
            st = getattr(m, "status", "")
            ok = st in ("member", "administrator", "creator") or (st == "restricted" and bool(getattr(m, "is_member", False)))
            if not ok:
                missing.append(ch)
        except Exception:
            missing.append(ch)
    return len(missing) == 0, missing

async def handle_giveaway_join_callback(query, user, context: ContextTypes.DEFAULT_TYPE, gw_id: int) -> None:
    gw = get_giveaway_by_id_db(gw_id)
    if not gw:
        await query.answer("❌ Конкурс не найден.", show_alert=True)
        return
    if gw["status"] != "active":
        await query.answer("🏁 Этот конкурс уже завершён!", show_alert=True)
        return

    bot_username = await get_bot_username(context.bot)
    u_row = get_user_row_raw(user.id)
    if not u_row or not u_row["bot_started"] or not u_row["privacy_accepted"]:
        try:
            await query.answer(url=f"https://t.me/{bot_username}?start=gw_{gw['code']}")
        except Exception:
            await query.answer(
                f"⚠️ Сначала запустите бота @{bot_username} (/start) и примите соглашение!",
                show_alert=True,
            )
        return

    is_banned, _, _, _ = is_user_banned(user.id)
    if is_banned and user.id not in ADMIN_IDS:
        await query.answer("⛔️ Ваш аккаунт заблокирован!", show_alert=True)
        return

    channels = json.loads(gw["channels_json"] or "[]")
    all_sub, missing = await _check_user_subscriptions_for_giveaway(context.bot, user.id, channels)
    if not all_sub:
        miss_names = ", ".join(
            (f"@{m['username']}" if m.get("username") else m.get("title", "канал"))
            for m in missing[:4]
        )
        await query.answer(
            f"❌ Для участия подпишитесь на все каналы конкурса: {miss_names}",
            show_alert=True,
        )
        return

    ok, msg_res, new_cnt, reached_max = join_giveaway_db(gw_id, user.id)
    if not ok:
        await query.answer(f"ℹ️ {msg_res}", show_alert=True)
        return

    await query.answer(f"🎉 Вы участвуете в конкурсе! (Участников: {new_cnt})", show_alert=True)
    if reached_max:
        await finalize_giveaway_and_notify(context.bot, gw_id)
    else:
        await refresh_giveaway_channel_posts(context.bot, gw, new_cnt)

async def handle_giveaway_join_deeplink(chat_id: int, user, context: ContextTypes.DEFAULT_TYPE, gw_code: str) -> None:
    gw = get_giveaway_by_code_db(gw_code)
    if not gw:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{ce('cross')} Конкурс не найден или удалён.",
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard(),
        )
        return
    if gw["status"] != "active":
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{ce('info')} Этот конкурс уже завершён или ещё не начался.",
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard(),
        )
        return

    channels = json.loads(gw["channels_json"] or "[]")
    all_sub, missing = await _check_user_subscriptions_for_giveaway(context.bot, user.id, channels)
    if not all_sub:
        buttons = []
        miss_lines = []
        for ch in missing:
            title = ch.get("title") or (f"@{ch['username']}" if ch.get("username") else "Канал")
            miss_lines.append(f"• <b>{clean_html(title)}</b>" + (f" (@{clean_html(ch['username'])})" if ch.get("username") else ""))
            if ch.get("username"):
                buttons.append([make_btn(f"Подписаться: {title[:26]}", style="primary", emoji_key="megaphone", url=f"https://t.me/{ch['username']}")])
        buttons.append([make_btn("Проверить и участвовать", style="success", emoji_key="check", callback_data=f"gw_join:{gw['id']}")])
        buttons.append([make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")])
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"{ce('warn')} <b>Для участия в конкурсе подпишитесь на каналы:</b>\n"
                + "\n".join(miss_lines)
                + "\n\nПосле подписки нажмите кнопку ниже:"
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    ok, msg_res, new_cnt, reached_max = join_giveaway_db(int(gw["id"]), user.id)
    if not ok:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{ce('info')} {clean_html(msg_res)}",
            parse_mode=ParseMode.HTML,
            reply_markup=quick_nav_keyboard(),
        )
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"{ce('boom')} <b>Вы успешно участвуете в конкурсе!</b>\n"
            f"{ce('star')} Призовой фонд: <b>{int(gw['per_winner_stars']):,} {ce('star')}</b> × <b>{gw['winners_count']}</b> побед.\n"
            f"{ce('smile')} Участников сейчас: <b>{new_cnt}</b>\n\n"
            "В случае победы бот автоматически начислит звёзды и пришлёт чек сюда!"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=quick_nav_keyboard(),
    )
    if reached_max:
        await finalize_giveaway_and_notify(context.bot, int(gw["id"]))
    else:
        await refresh_giveaway_channel_posts(context.bot, gw, new_cnt)

# --- МОИ КОНКУРСЫ АВТОРА ---

async def show_author_giveaways_page(query, user_id: int, page: int = 1) -> None:
    page_size = 6
    rows, total = get_author_giveaways_db(user_id, page=page, page_size=page_size)
    total_pages = max(1, math.ceil(total / page_size))
    page = max(1, min(page, total_pages))

    lines = [
        f"{ce('crown')} <b>Мои конкурсы ({total}) — Стр. {page}/{total_pages}</b>",
        "━━━━━━━━━━━━",
    ]
    buttons = []
    if not rows:
        lines.append("<i>У вас пока нет созданных конкурсов.</i>")
    else:
        for gw in rows:
            st_icon = {"scheduled": "⏰", "active": "🟢", "finished": "🏁", "cancelled": "❌"}.get(gw["status"], "•")
            p_cnt = get_giveaway_participants_count_db(gw["id"])
            lines.append(
                f"{st_icon} <b>#{gw['id']}</b> ({gw['code']}) — <b>{int(gw['total_prize_stars']):,} {ce('star')}</b> • {p_cnt} уч."
            )
            buttons.append([
                make_btn(
                    f"{st_icon} Конкурс #{gw['id']} ({int(gw['total_prize_stars']):,}⭐ • {p_cnt} уч.)",
                    style="primary" if gw["status"] == "active" else None,
                    callback_data=f"author_gw_view:{gw['id']}",
                )
            ])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"author_giveaways:{page-1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"author_giveaways:{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([make_btn("Создать конкурс", style="success", emoji_key="boom", callback_data="gw_create_start")])
    buttons.append([make_btn("Кабинет Автора", emoji_key="crown", callback_data="nav_author")])

    text = "\n".join(lines)
    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def show_author_giveaway_detail(query, user_id: int, gw_id: int) -> None:
    gw = get_giveaway_by_id_db(gw_id)
    if not gw or gw["author_id"] != user_id:
        await query.answer("❌ Конкурс не найден.", show_alert=True)
        return
    p_cnt = get_giveaway_participants_count_db(gw_id)
    channels = json.loads(gw["channels_json"] or "[]")
    ch_names = ", ".join(clean_html(c.get("title") or c.get("username") or str(c["chat_id"])) for c in channels)
    st_ru = {
        "scheduled": f"{ce('hourglass')} Запланирован на {_fmt_dt(gw['publish_ts'])}",
        "active": f"{ce('green_dot')} Активен",
        "finished": f"{ce('check')} Завершён",
        "cancelled": f"{ce('cross')} Отменён",
    }.get(gw["status"], gw["status"])
    end_str = _fmt_dt(gw["end_ts"]) if gw["end_ts"] else "Не задано"
    max_str = f"{gw['max_participants']:,} чел." if gw["max_participants"] else "Без лимита"

    text = (
        f"{ce('crown')} <b>Конкурс #{gw['id']} (<code>{gw['code']}</code>)</b>\n"
        "━━━━━━━━━━━━\n"
        f"• Статус: <b>{st_ru}</b>\n"
        f"• Каналы: <b>{ch_names}</b>\n"
        f"• Приз: <b>{int(gw['per_winner_stars']):,} {ce('star')}</b> × <b>{gw['winners_count']}</b> (всего <b>{int(gw['total_prize_stars']):,} {ce('star')}</b>)\n"
        f"• Участников: <b>{p_cnt:,}</b> (лимит: <b>{max_str}</b>)\n"
        f"• Авто-итоги по времени: <b>{end_str}</b>\n"
        f"• Кнопка: <b>{clean_html(gw['btn_text'])}</b> ({_style_label_ru(gw['btn_style'])}, {_btn_mode_label_ru(gw['btn_mode'])})"
    )
    buttons = []
    if gw["status"] == "active":
        buttons.append([make_btn("Завершить конкурс сейчас (раздать призы)", style="success", emoji_key="check", callback_data=f"author_gw_end:{gw_id}")])
    elif gw["status"] == "scheduled":
        buttons.append([make_btn("Отменить запланированный конкурс", style="danger", emoji_key="cross", callback_data=f"author_gw_cancel:{gw_id}")])
    buttons.append([InlineKeyboardButton("◀️ К моим конкурсам", callback_data="author_giveaways:1")])
    buttons.append([make_btn("Кабинет Автора", emoji_key="crown", callback_data="nav_author")])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

# --- МАСТЕР СОЗДАНИЯ КОНКУРСА ---

def _gw_render_channels_step(channels: list[sqlite3.Row], selected_ids: set[int]) -> Tuple[str, InlineKeyboardMarkup]:
    text = (
        f"{ce('boom')} <b>Создание конкурса — Шаг 1/8: Каналы</b>\n"
        "━━━━━━━━━━━━\n"
        "Выберите канал(ы) или чат(ы), в которых будет опубликован конкурс (можно выбрать несколько):"
    )
    buttons = []
    for ch in channels:
        cid = int(ch["chat_id"])
        checked = "✅ " if cid in selected_ids else "⬜️ "
        lbl = f"{checked}{ch['title'] or ('@' + ch['username'] if ch['username'] else str(cid))}"
        buttons.append([make_btn(lbl[:40], style="success" if cid in selected_ids else None, callback_data=f"gw_tog_ch:{cid}")])
    buttons.append([make_btn("Выбрать все", emoji_key="check", callback_data="gw_all_ch")])
    if selected_ids:
        buttons.append([make_btn(f"Далее ({len(selected_ids)} выбр.) ➡️", style="primary", callback_data="gw_ch_next")])
    buttons.append([make_btn("Отмена", style="danger", emoji_key="cross", callback_data="gw_cancel")])
    return text, InlineKeyboardMarkup(buttons)

async def gw_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access_allowed(update):
        return ConversationHandler.END
    query = update.callback_query
    user = query.from_user
    db_user = get_or_create_user(user.id, user.username or "", user.first_name or "")
    if not db_user["is_author"]:
        await query.answer("❌ Создание конкурсов доступно только авторам!", show_alert=True)
        return ConversationHandler.END
    channels = get_author_channels_db(user.id)
    if not channels:
        await query.answer("⚠️ Сначала подключите хотя бы один канал в «Добавить каналы»!", show_alert=True)
        return ConversationHandler.END
    if int(db_user["author_balance_stars"] or 0) < 1:
        await query.answer("⚠️ Авторский баланс пуст! Сначала пополните Авторский баланс.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    selected = {int(channels[0]["chat_id"])}
    context.user_data["gw_draft"] = {
        "channels_map": {
            int(c["chat_id"]): {
                "chat_id": int(c["chat_id"]),
                "username": c["username"],
                "title": c["title"],
                "chat_type": c["chat_type"],
            }
            for c in channels
        },
        "selected_ids": selected,
        "text_html": "",
        "photo_file_id": "",
        "winners_count": 1,
        "total_prize": 0,
        "btn_text": "Участвовать",
        "btn_style": "success",
        "btn_mode": "button",
        "end_delay_sec": 0,
        "end_ts": 0,
        "max_participants": 0,
        "publish_ts": 0,
    }
    text, kb = _gw_render_channels_step(channels, selected)
    if query.message.photo:
        await query.message.delete()
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_GW_CHANNELS

async def gw_channel_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    draft = context.user_data.get("gw_draft")
    if not draft:
        await query.answer("❌ Сессия создания устарела.", show_alert=True)
        return ConversationHandler.END
    data = query.data
    channels = get_author_channels_db(query.from_user.id)
    selected: set[int] = draft["selected_ids"]
    if data == "gw_all_ch":
        selected.clear()
        selected.update(int(c["chat_id"]) for c in channels)
        await query.answer("Выбраны все каналы!")
    else:
        cid = int(data.split(":")[1])
        if cid in selected:
            selected.discard(cid)
        else:
            selected.add(cid)
        await query.answer()
    text, kb = _gw_render_channels_step(channels, selected)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_GW_CHANNELS

async def gw_channels_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    draft = context.user_data.get("gw_draft")
    if not draft or not draft.get("selected_ids"):
        await query.answer("⚠️ Выберите хотя бы один канал!", show_alert=True)
        return WAIT_GW_CHANNELS
    await query.answer()
    kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="gw_cancel")]])
    await query.edit_message_text(
        f"{ce('pencil')} <b>Создание конкурса — Шаг 2/8: Текст поста</b>\n"
        "━━━━━━━━━━━━\n"
        "Отправьте текст объявления о конкурсе.\n\n"
        f"{ce('sparkles')} <b>Поддерживается любое форматирование Telegram:</b>\n"
        "• Жирный, курсив, подчёркнутый, зачёркнутый, спойлер, ссылки\n"
        "• Цитаты и сворачиваемые цитаты, моноширинные таблицы (<code>&lt;pre&gt;</code>)\n"
        "• <b>Кастомные Telegram-эмодзи</b> (из вашего набора стикеров/эмодзи)!\n\n"
        "<i>(Если сразу прикрепите фото с подписью — мы сохраним и фото, и текст!)</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAIT_GW_TEXT

async def gw_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data.get("gw_draft")
    if not draft:
        return ConversationHandler.END
    msg = update.message
    html_body = extract_message_html_with_custom_emojis(msg).strip()
    if not html_body:
        await msg.reply_text("❌ Отправьте непустой текст поста для конкурса:")
        return WAIT_GW_TEXT

    draft["text_html"] = html_body
    ce_cnt = len(re.findall(r"<tg-emoji\b", html_body))
    has_article_fmt = any(tag in html_body for tag in ("<blockquote", "<pre>", "<b>", "<i>", "<a href="))
    fmt_parts = []
    if ce_cnt:
        fmt_parts.append(f"кастом-эмодзи: <b>{ce_cnt}</b>")
    if has_article_fmt:
        fmt_parts.append("форматирование статьи сохранено")
    fmt_note = (
        f"\n{ce('check')} Определено: " + ", ".join(fmt_parts) + "\n"
        if fmt_parts else ""
    )

    if msg.photo:
        draft["photo_file_id"] = msg.photo[-1].file_id
        return await _prompt_gw_winners(msg, context, is_edit=False)

    kb = InlineKeyboardMarkup([
        [make_btn("Пропустить (без фото)", emoji_key="arrow_right", callback_data="gw_skip_photo")],
        [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="gw_cancel")],
    ])
    await msg.reply_text(
        f"{ce('sparkles')} <b>Создание конкурса — Шаг 3/8: Фото (опционально)</b>\n"
        "━━━━━━━━━━━━\n"
        f"Текст поста сохранён!{fmt_note}\n"
        "Отправьте картинку/баннер для поста конкурса или нажмите <b>«Пропустить»</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAIT_GW_PHOTO

async def gw_photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data.get("gw_draft")
    if not draft:
        return ConversationHandler.END
    if update.message.photo:
        draft["photo_file_id"] = update.message.photo[-1].file_id
    return await _prompt_gw_winners(update.message, context, is_edit=False)

async def gw_skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    draft = context.user_data.get("gw_draft")
    if not draft:
        return ConversationHandler.END
    await query.answer()
    draft["photo_file_id"] = ""
    return await _prompt_gw_winners(query, context, is_edit=True)

async def _prompt_gw_winners(target, context: ContextTypes.DEFAULT_TYPE, is_edit: bool = False):
    text = (
        f"{ce('crown')} <b>Создание конкурса — Шаг 4/8: Количество победителей</b>\n"
        "━━━━━━━━━━━━\n"
        "Введите число победителей (от <b>1</b> до <b>100</b>):"
    )
    kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="gw_cancel")]])
    if is_edit:
        await target.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await target.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_GW_WINNERS

async def gw_winners_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data.get("gw_draft")
    if not draft:
        return ConversationHandler.END
    raw = re.sub(r"[\s,_.]", "", (update.message.text or "").strip())
    if not raw.isdigit() or int(raw) < 1 or int(raw) > 100:
        await update.message.reply_text("❌ Введите целое число победителей от 1 до 100:")
        return WAIT_GW_WINNERS
    draft["winners_count"] = int(raw)
    db_user = get_or_create_user(update.effective_user.id, "", "")
    auth_bal = int(db_user["author_balance_stars"] or 0)
    kb = InlineKeyboardMarkup([[make_btn("Отмена", style="danger", emoji_key="cross", callback_data="gw_cancel")]])
    await update.message.reply_text(
        f"{ce('star')} <b>Создание конкурса — Шаг 5/8: Призовой фонд</b>\n"
        "━━━━━━━━━━━━\n"
        f"• Победителей: <b>{draft['winners_count']}</b>\n"
        f"• Ваш Авторский баланс: <b>{auth_bal:,} {ce('star')}</b>\n\n"
        "Введите <b>общую сумму звёзд</b> на конкурс (например <code>100000</code> — она автоматически поделится поровну между победителями):",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAIT_GW_PRIZE

async def gw_prize_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data.get("gw_draft")
    if not draft:
        return ConversationHandler.END
    raw = re.sub(r"[\s,_.]", "", (update.message.text or "").strip())
    if not raw.isdigit() or int(raw) < 1:
        await update.message.reply_text("❌ Введите корректную сумму звёзд числом:")
        return WAIT_GW_PRIZE
    total = int(raw)
    w_cnt = max(1, int(draft["winners_count"]))
    per_w = total // w_cnt
    if per_w < 1:
        await update.message.reply_text(f"❌ Сумма должна быть не меньше количества победителей ({w_cnt} ⭐):")
        return WAIT_GW_PRIZE
    locked = per_w * w_cnt
    db_user = get_or_create_user(update.effective_user.id, "", "")
    if int(db_user["author_balance_stars"] or 0) < locked:
        await update.message.reply_text(
            f"❌ Недостаточно Stars на Авторском балансе!\n"
            f"Нужно: <b>{locked:,} ⭐</b>, у вас: <b>{int(db_user['author_balance_stars'] or 0):,} ⭐</b>.",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_GW_PRIZE

    draft["total_prize"] = locked
    return await _render_gw_btn_config(update.message, context, is_edit=False)

async def _render_gw_btn_config(target, context: ContextTypes.DEFAULT_TYPE, is_edit: bool = True):
    draft = context.user_data["gw_draft"]
    w_cnt = draft["winners_count"]
    per_w = draft["total_prize"] // w_cnt
    text = (
        f"{ce('game')} <b>Создание конкурса — Шаг 6/8: Настройка кнопки</b>\n"
        "━━━━━━━━━━━━\n"
        f"• Приз: <b>{per_w:,} {ce('star')}</b> × <b>{w_cnt}</b> (итого <b>{draft['total_prize']:,} {ce('star')}</b>)\n"
        f"• Текст кнопки: <b>{clean_html(draft['btn_text'])}</b>\n"
        f"• Цвет кнопки: <b>{_style_label_ru(draft['btn_style'])}</b>\n"
        f"• Размещение: <b>{_btn_mode_label_ru(draft['btn_mode'])}</b>\n"
        "━━━━━━━━━━━━\n"
        "Настройте внешний вид кнопки участия или нажмите «Далее»:"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("Изменить текст кнопки", emoji_key="pencil", callback_data="gw_btn_edit_text")],
        [
            make_btn("🟢", style="success", callback_data="gw_btn_style:success"),
            make_btn("🔵", style="primary", callback_data="gw_btn_style:primary"),
            make_btn("🔴", style="danger", callback_data="gw_btn_style:danger"),
            make_btn("⚪️", callback_data="gw_btn_style:default"),
        ],
        [
            make_btn("Кнопка" + (" ✓" if draft["btn_mode"] == "button" else ""), callback_data="gw_btn_mode:button"),
            make_btn("В тексте" + (" ✓" if draft["btn_mode"] == "in_text" else ""), callback_data="gw_btn_mode:in_text"),
            make_btn("Оба" + (" ✓" if draft["btn_mode"] == "both" else ""), callback_data="gw_btn_mode:both"),
        ],
        [make_btn("Далее (условия окончания) ➡️", style="primary", callback_data="gw_btn_next")],
        [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="gw_cancel")],
    ])
    if is_edit:
        await target.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await target.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_GW_BTN_CONFIG

async def gw_btn_config_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    draft = context.user_data.get("gw_draft")
    if not draft:
        return ConversationHandler.END
    data = query.data
    if data == "gw_btn_edit_text":
        await query.answer()
        await query.edit_message_text(
            f"{ce('pencil')} Введите новый текст кнопки (от 1 до 32 символов, например: <code>Хочу звёзды!</code>):",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_GW_BTN_TEXT
    if data.startswith("gw_btn_style:"):
        draft["btn_style"] = data.split(":")[1]
        await query.answer(f"Цвет: {_style_label_ru(draft['btn_style'])}")
        return await _render_gw_btn_config(query, context, is_edit=True)
    if data.startswith("gw_btn_mode:"):
        draft["btn_mode"] = data.split(":")[1]
        await query.answer(f"Режим: {_btn_mode_label_ru(draft['btn_mode'])}")
        return await _render_gw_btn_config(query, context, is_edit=True)
    if data == "gw_btn_next":
        await query.answer()
        return await _render_gw_end_cond(query, context, is_edit=True)
    return WAIT_GW_BTN_CONFIG

async def gw_btn_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data.get("gw_draft")
    if not draft:
        return ConversationHandler.END
    txt = (update.message.text or "").strip()
    if len(txt) < 1 or len(txt) > 32:
        await update.message.reply_text("❌ Текст кнопки должен быть от 1 до 32 символов:")
        return WAIT_GW_BTN_TEXT
    draft["btn_text"] = txt
    return await _render_gw_btn_config(update.message, context, is_edit=False)

async def _render_gw_end_cond(target, context: ContextTypes.DEFAULT_TYPE, is_edit: bool = True):
    draft = context.user_data["gw_draft"]
    sec = int(draft.get("end_delay_sec") or 0)
    exact_end = int(draft.get("end_ts") or 0)
    if exact_end > 0:
        time_lbl = f"до {_fmt_dt(exact_end)}"
    elif sec > 0:
        time_lbl = f"через {seconds_to_hms(sec)} после публикации"
    else:
        time_lbl = "Без таймера"
    max_p = int(draft.get("max_participants") or 0)
    max_lbl = f"{max_p:,} участников" if max_p > 0 else "Без лимита"

    text = (
        f"{ce('hourglass')} <b>Создание конкурса — Шаг 7/8: Условия окончания</b>\n"
        "━━━━━━━━━━━━\n"
        f"• По времени: <b>{time_lbl}</b>\n"
        f"• Лимит участников: <b>{max_lbl}</b>\n"
        "<i>(Вы также сможете завершить конкурс досрочно в любой момент в «Моих конкурсах».)</i>\n"
        "━━━━━━━━━━━━\n"
        "Выберите параметры окончания:"
    )
    kb = InlineKeyboardMarkup([
        [
            make_btn("15м", callback_data="gw_end_preset:15"),
            make_btn("1ч", callback_data="gw_end_preset:60"),
            make_btn("6ч", callback_data="gw_end_preset:360"),
            make_btn("24ч", callback_data="gw_end_preset:1440"),
            make_btn("Без тайм.", callback_data="gw_end_preset:0"),
        ],
        [
            make_btn("Своё время/дата", emoji_key="calendar", callback_data="gw_end_custom_time"),
            make_btn("Лимит участников", emoji_key="smile", callback_data="gw_end_max_custom"),
        ],
        [make_btn("Сбросить лимит участников", callback_data="gw_end_max_clear")] if max_p > 0 else [],
        [make_btn("Далее (публикация) ➡️", style="primary", callback_data="gw_end_next")],
        [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="gw_cancel")],
    ])
    kb = InlineKeyboardMarkup([row for row in kb.inline_keyboard if row])
    if is_edit:
        await target.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await target.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_GW_END_COND

async def gw_end_cond_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    draft = context.user_data.get("gw_draft")
    if not draft:
        return ConversationHandler.END
    data = query.data
    if data.startswith("gw_end_preset:"):
        mins = int(data.split(":")[1])
        draft["end_delay_sec"] = mins * 60
        draft["end_ts"] = 0
        await query.answer("Установлено!")
        return await _render_gw_end_cond(query, context, is_edit=True)
    if data == "gw_end_custom_time":
        await query.answer()
        await query.edit_message_text(
            f"{ce('calendar')} Введите длительность (например: <code>30м</code>, <code>3ч</code>, <code>2д</code>) "
            "или точную дату/время окончания (например: <code>18:30</code> или <code>20.11 20:00</code>):",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_GW_END_CUSTOM_TIME
    if data == "gw_end_max_custom":
        await query.answer()
        await query.edit_message_text(
            f"{ce('smile')} Введите максимальное количество участников (от <b>1</b> до <b>100000</b>):",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_GW_END_CUSTOM_MAX
    if data == "gw_end_max_clear":
        draft["max_participants"] = 0
        await query.answer("Лимит участников убран.")
        return await _render_gw_end_cond(query, context, is_edit=True)
    if data == "gw_end_next":
        await query.answer()
        return await _render_gw_publish_step(query, context, is_edit=True)
    return WAIT_GW_END_COND

async def gw_end_custom_time_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data.get("gw_draft")
    if not draft:
        return ConversationHandler.END
    raw = (update.message.text or "").strip()
    delay = _parse_giveaway_delay_seconds(raw)
    if delay and delay >= 60:
        draft["end_delay_sec"] = delay
        draft["end_ts"] = 0
        return await _render_gw_end_cond(update.message, context, is_edit=False)
    ts = _parse_giveaway_target_timestamp(raw)
    if ts:
        draft["end_ts"] = ts
        draft["end_delay_sec"] = 0
        return await _render_gw_end_cond(update.message, context, is_edit=False)
    await update.message.reply_text("❌ Неверный формат. Пример: <code>30м</code>, <code>2ч</code>, <code>18:30</code> или <code>20.11 20:00</code>:", parse_mode=ParseMode.HTML)
    return WAIT_GW_END_CUSTOM_TIME

async def gw_end_custom_max_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data.get("gw_draft")
    if not draft:
        return ConversationHandler.END
    raw = re.sub(r"[\s,_.]", "", (update.message.text or "").strip())
    if not raw.isdigit() or int(raw) < 1 or int(raw) > 100_000:
        await update.message.reply_text("❌ Введите число от 1 до 100000:")
        return WAIT_GW_END_CUSTOM_MAX
    draft["max_participants"] = int(raw)
    return await _render_gw_end_cond(update.message, context, is_edit=False)

async def _render_gw_publish_step(target, context: ContextTypes.DEFAULT_TYPE, is_edit: bool = True):
    draft = context.user_data["gw_draft"]
    ch_map = draft["channels_map"]
    ch_names = ", ".join(clean_html(ch_map[cid]["title"]) for cid in draft["selected_ids"] if cid in ch_map)
    w_cnt = draft["winners_count"]
    total_p = draft["total_prize"]
    per_w = total_p // w_cnt

    if draft.get("end_ts"):
        end_lbl = _fmt_dt(draft["end_ts"])
    elif draft.get("end_delay_sec"):
        end_lbl = f"через {seconds_to_hms(draft['end_delay_sec'])} после старта"
    else:
        end_lbl = "Вручную автором"
    max_lbl = f"{draft['max_participants']:,} чел." if draft.get("max_participants") else "Нет"

    text = (
        f"{ce('boom')} <b>Создание конкурса — Шаг 8/8: Публикация</b>\n"
        "━━━━━━━━━━━━\n"
        f"• Каналы: <b>{ch_names}</b>\n"
        f"• Фото: <b>{'Да' if draft['photo_file_id'] else 'Нет'}</b>\n"
        f"• Победителей: <b>{w_cnt}</b> (по <b>{per_w:,} {ce('star')}</b>, итого <b>{total_p:,} {ce('star')}</b>)\n"
        f"• Кнопка: <b>{clean_html(draft['btn_text'])}</b> ({_style_label_ru(draft['btn_style'])}, {_btn_mode_label_ru(draft['btn_mode'])})\n"
        f"• Авто-итоги: <b>{end_lbl}</b> • Лимит: <b>{max_lbl}</b>\n"
        "━━━━━━━━━━━━\n"
        "Опубликовать конкурс сразу или запланировать публикацию по времени?"
    )
    kb = InlineKeyboardMarkup([
        [make_btn(f"Опубликовать сейчас (-{total_p:,}⭐)", style="success", emoji_key="play", callback_data="gw_pub_now")],
        [make_btn("Запланировать по времени", style="primary", emoji_key="calendar", callback_data="gw_pub_sched")],
        [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="gw_cancel")],
    ])
    if is_edit:
        await target.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await target.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WAIT_GW_PUBLISH

async def _finalize_gw_creation(reply_target, user_id: int, context: ContextTypes.DEFAULT_TYPE, publish_ts: int, is_edit: bool = True):
    draft = context.user_data.pop("gw_draft", None)
    if not draft:
        return ConversationHandler.END

    ch_map = draft["channels_map"]
    channels = [ch_map[cid] for cid in draft["selected_ids"] if cid in ch_map]
    now = int(time.time())
    eff_pub_ts = publish_ts if publish_ts > now else 0
    if draft.get("end_ts"):
        eff_end_ts = int(draft["end_ts"])
    elif draft.get("end_delay_sec"):
        base_start = eff_pub_ts if eff_pub_ts > 0 else now
        eff_end_ts = base_start + int(draft["end_delay_sec"])
    else:
        eff_end_ts = 0

    ok, err_m, gw = create_giveaway_db(
        author_id=user_id,
        channels=channels,
        text_html=draft["text_html"],
        photo_file_id=draft["photo_file_id"],
        winners_count=draft["winners_count"],
        total_prize_stars=draft["total_prize"],
        btn_text=draft["btn_text"],
        btn_style=draft["btn_style"],
        btn_mode=draft["btn_mode"],
        max_participants=draft["max_participants"],
        publish_ts=eff_pub_ts,
        end_ts=eff_end_ts,
    )
    if not ok or not gw:
        err_txt = f"{ce('cross')} {clean_html(err_m)}"
        kb = InlineKeyboardMarkup([[make_btn("Кабинет Автора", emoji_key="crown", callback_data="nav_author")]])
        if is_edit:
            await reply_target.edit_message_text(err_txt, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await reply_target.reply_text(err_txt, parse_mode=ParseMode.HTML, reply_markup=kb)
        return ConversationHandler.END

    if gw["status"] == "scheduled":
        done_txt = (
            f"{ce('calendar')} <b>Конкурс #{gw['id']} (<code>{gw['code']}</code>) запланирован!</b>\n"
            f"• Публикация: <b>{_fmt_dt(gw['publish_ts'])}</b>\n"
            f"• Списано с Авторского баланса: <b>{int(gw['total_prize_stars']):,} {ce('star')}</b>"
        )
    else:
        posted = await publish_giveaway_to_channels(context.bot, gw)
        done_txt = (
            f"{ce('boom')} <b>Конкурс #{gw['id']} (<code>{gw['code']}</code>) опубликован!</b>\n"
            f"• Отправлено в каналы: <b>{len(posted)}/{len(channels)}</b>\n"
            f"• Списано с Авторского баланса: <b>{int(gw['total_prize_stars']):,} {ce('star')}</b>"
        )

    kb = InlineKeyboardMarkup([
        [make_btn("Управление конкурсом", style="primary", emoji_key="eyes", callback_data=f"author_gw_view:{gw['id']}")],
        [make_btn("Кабинет Автора", emoji_key="crown", callback_data="nav_author")],
    ])
    if is_edit:
        await reply_target.edit_message_text(done_txt, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await reply_target.reply_text(done_txt, parse_mode=ParseMode.HTML, reply_markup=kb)
    return ConversationHandler.END

async def gw_publish_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    draft = context.user_data.get("gw_draft")
    if not draft:
        return ConversationHandler.END
    data = query.data
    if data == "gw_pub_now":
        await query.answer("🚀 Публикуем конкурс...")
        return await _finalize_gw_creation(query, query.from_user.id, context, publish_ts=0, is_edit=True)
    if data == "gw_pub_sched":
        await query.answer()
        kb = InlineKeyboardMarkup([
            [
                make_btn("Через 10м", callback_data="gw_sched_preset:10"),
                make_btn("Через 1ч", callback_data="gw_sched_preset:60"),
                make_btn("Через 3ч", callback_data="gw_sched_preset:180"),
            ],
            [make_btn("Отмена", style="danger", emoji_key="cross", callback_data="gw_cancel")],
        ])
        await query.edit_message_text(
            f"{ce('calendar')} <b>Планирование публикации</b>\n\n"
            "Выберите кнопку или отправьте время публикации (например: <code>15м</code>, <code>2ч</code>, <code>18:30</code> или <code>20.11 19:00</code>):",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
        return WAIT_GW_SCHED_TIME
    return WAIT_GW_PUBLISH

async def gw_sched_preset_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    mins = int(query.data.split(":")[1])
    await query.answer("⏰ Конкурс запланирован!")
    return await _finalize_gw_creation(query, query.from_user.id, context, publish_ts=int(time.time()) + mins * 60, is_edit=True)

async def gw_sched_time_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ts = _parse_giveaway_target_timestamp((update.message.text or "").strip())
    if not ts:
        await update.message.reply_text(
            "❌ Укажите время в будущем! Например: <code>15м</code>, <code>2ч</code>, <code>18:30</code> или <code>20.11 19:00</code>:",
            parse_mode=ParseMode.HTML,
        )
        return WAIT_GW_SCHED_TIME
    return await _finalize_gw_creation(update.message, update.effective_user.id, context, publish_ts=ts, is_edit=False)

async def gw_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("gw_draft", None)
    if update.callback_query:
        await update.callback_query.answer("Отменено.")
        await show_author_hub(update.callback_query, update.callback_query.from_user.id, context)
    elif update.message:
        await update.message.reply_text("❌ Создание конкурса отменено.", reply_markup=quick_nav_keyboard())
    return ConversationHandler.END

# --- UI И ДВИЖОК «РЕЖИМЫ» -> «БАТТЛЫ» (CASE BATTLES) ---

def _summarize_battle_cases(case_keys: List[str]) -> str:
    counts: Dict[str, int] = {}
    order: List[str] = []
    for k in case_keys:
        if k not in counts:
            order.append(k)
            counts[k] = 0
        counts[k] += 1
    parts = []
    for k in order:
        tier = CASE_TIERS.get(k)
        name = tier["name"] if tier else k
        parts.append(f"{name} ×<b>{counts[k]}</b>" if counts[k] > 1 else name)
    return ", ".join(parts) if parts else "—"

async def show_modes_hub(query, user_id: int) -> None:
    db_user = get_or_create_user(user_id, "", "")
    _, _, active_battles = get_open_case_battles_db(page=1, page_size=1)
    text = (
        f"{ce('game')} <b>Режимы игры</b>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('dollar')} Ваш баланс: <b>{fmt_stars_rub(db_user['balance_stars'])}</b>\n\n"
        f"{ce('bolt')} <b>Баттлы кейсов (Case Battles)</b>\n"
        "• Создайте комнату от <b>1 до 15 кейсов</b> (любые комбинации) на <b>1–5 участников</b>.\n"
        "• Как только все места заняты, запускается <b>15-секундный отсчёт</b> и кейсы открываются по очереди.\n"
        "• <b>Победитель забирает ВЕСЬ дроп</b> всех участников прямо в свою коллекцию!\n\n"
        f"{ce('sparkles')} Активных лобби сейчас: <b>{active_battles}</b>"
    )
    kb = InlineKeyboardMarkup([
        [make_btn(f"Баттлы ({active_battles})", style="primary", emoji_key="bolt", callback_data="battles_list:1")],
        [make_btn("Создать баттл", style="success", emoji_key="plus", callback_data="btl_create_start")],
        [make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")],
    ])
    if query.message and query.message.photo:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    elif query.message:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_battles_list(query, user_id: int, page: int = 1) -> None:
    db_user = get_or_create_user(user_id, "", "")
    battles, total_pages, total = get_open_case_battles_db(page=page, page_size=7)
    lines = [
        f"{ce('bolt')} <b>Баттлы кейсов — Лобби ({total})</b> • Стр. {page}/{total_pages}",
        "━━━━━━━━━━━━",
        f"{ce('dollar')} Баланс: <b>{fmt_stars_rub(db_user['balance_stars'])}</b>\n",
    ]
    buttons = [
        [make_btn("Создать баттл (1–15 кейсов)", style="success", emoji_key="plus", callback_data="btl_create_start")],
    ]
    if not battles:
        lines.append("<i>Активных комнат пока нет — станьте первым и создайте баттл!</i>")
    else:
        for b in battles:
            ckeys = json.loads(b["cases_json"] or "[]")
            j_cnt = int(b.get("joined_count") or 0)
            max_p = int(b["max_players"] or 2)
            st_badge = {
                "waiting": "🟢 Ждёт",
                "countdown": "⏳ Таймер",
                "running": "🔥 Идёт",
            }.get(b["status"], "•")
            cost_val = int(b["total_cost_stars"] or 0)
            lines.append(
                f"{st_badge} <b>#{b['id']}</b> • {len(ckeys)} кейс. • "
                f"<b>{fmt_stars_compact(cost_val)} ⭐</b> • 👥 {j_cnt}/{max_p}"
            )
            btn_label = f"{st_badge} #{b['id']} | {len(ckeys)}к • {fmt_stars_compact(cost_val)}⭐ ({j_cnt}/{max_p})"
            buttons.append([
                make_btn(
                    btn_label[:58],
                    style="primary" if b["status"] == "waiting" else None,
                    callback_data=f"battle_view:{b['id']}",
                )
            ])

    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("◀️", callback_data=f"battles_list:{page - 1}"))
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("▶️", callback_data=f"battles_list:{page + 1}"))
        buttons.append(nav_row)

    buttons.append([
        make_btn("Обновить", emoji_key="refresh", callback_data=f"battles_list:{page}"),
        make_btn("Режимы", emoji_key="game", callback_data="nav_modes"),
    ])
    buttons.append([make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main")])

    text = "\n".join(lines)
    kb = InlineKeyboardMarkup(buttons)
    if query.message and query.message.photo:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    elif query.message:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_battle_create_cases(query, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_user = get_or_create_user(user_id, "", "")
    draft = context.user_data.setdefault("battle_draft", {"cases": [], "max_players": 2})
    sel: List[str] = draft["cases"]
    total_cost = sum(int(CASE_TIERS[k]["price"]) for k in sel if k in CASE_TIERS)

    lines = [
        f"{ce('plus')} <b>Создание баттла — Шаг 1/2: Кейсы ({len(sel)}/{BATTLE_MAX_CASES})</b>",
        "━━━━━━━━━━━━",
        f"{ce('dollar')} Ваш баланс: <b>{fmt_stars_rub(db_user['balance_stars'])}</b>",
        f"{ce('star')} Стоимость входа: <b>{total_cost:,} ⭐</b>",
        f"• Выбрано: {_summarize_battle_cases(sel)}\n",
        "Нажимайте на кейсы ниже, чтобы добавлять их (от 1 до 15 шт., можно повторять или миксовать):",
    ]

    buttons = []
    for tkey, tinfo in CASE_TIERS.items():
        cnt_k = sel.count(tkey)
        mark = f" [{cnt_k}]" if cnt_k > 0 else ""
        buttons.append([
            make_btn(
                f"+ {tinfo['name']} ({fmt_stars_compact(tinfo['price'])}⭐){mark}",
                style="primary" if cnt_k > 0 else None,
                callback_data=f"btl_add:{tkey}",
            )
        ])

    ctrl_row = []
    if sel:
        ctrl_row.append(make_btn("Убрать последний", emoji_key="arrow_left", callback_data="btl_pop_case"))
        ctrl_row.append(make_btn("Очистить", style="danger", emoji_key="cross", callback_data="btl_clear_cases"))
    if ctrl_row:
        buttons.append(ctrl_row)

    if sel:
        buttons.append([
            make_btn(
                f"Далее: игроки ({len(sel)}/{BATTLE_MAX_CASES} • {fmt_stars_compact(total_cost)}⭐) ➡️",
                style="success",
                callback_data="btl_cases_next",
            )
        ])

    buttons.append([
        make_btn("К списку баттлов", emoji_key="game", callback_data="battles_list:1"),
        make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main"),
    ])

    text = "\n".join(lines)
    kb = InlineKeyboardMarkup(buttons)
    if query.message and query.message.photo:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    elif query.message:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

async def show_battle_create_players(query, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    db_user = get_or_create_user(user_id, "", "")
    draft = context.user_data.setdefault("battle_draft", {"cases": [], "max_players": 2})
    sel: List[str] = draft["cases"]
    if not sel:
        await show_battle_create_cases(query, user_id, context)
        return
    max_p = max(BATTLE_MIN_PLAYERS, min(BATTLE_MAX_PLAYERS, int(draft.get("max_players", 2))))
    total_cost = sum(int(CASE_TIERS[k]["price"]) for k in sel if k in CASE_TIERS)
    can_afford = int(db_user["balance_stars"] or 0) >= total_cost

    text = (
        f"{ce('bolt')} <b>Создание баттла — Шаг 2/2: Участники</b>\n"
        "━━━━━━━━━━━━\n"
        f"• Кейсов: <b>{len(sel)}</b> шт. ({_summarize_battle_cases(sel)})\n"
        f"• Ставка на участника: <b>{total_cost:,} {ce('star')}</b>\n"
        f"• Выбрано мест: <b>{max_p} чел.</b> "
        + ("<i>(соло-режим: отсчёт начнётся сразу!)</i>" if max_p == 1 else f"<i>(общий банк: до {total_cost * max_p:,} ⭐)</i>")
        + f"\n• Ваш баланс: <b>{fmt_stars_rub(db_user['balance_stars'])}</b>\n\n"
        "Выберите количество участников (от 1 до 5):"
    )

    p_row = [
        make_btn(
            f"{'✅ ' if max_p == n else ''}{n} чел.",
            style="primary" if max_p == n else None,
            callback_data=f"btl_players:{n}",
        )
        for n in range(BATTLE_MIN_PLAYERS, BATTLE_MAX_PLAYERS + 1)
    ]
    buttons = [p_row]
    if can_afford:
        buttons.append([
            make_btn(
                f"Запустить баттл ({fmt_stars_compact(total_cost)}⭐)",
                style="success",
                emoji_key="bolt",
                callback_data="btl_launch",
            )
        ])
    else:
        buttons.append([make_btn("❌ Недостаточно Stars", style="danger", callback_data="noop")])

    buttons.append([
        make_btn("◀️ Изменить кейсы", callback_data="btl_edit_cases"),
        make_btn("К баттлам", emoji_key="game", callback_data="battles_list:1"),
    ])
    kb = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

def _build_battle_room_view(detail: dict, viewer_id: int) -> Tuple[str, InlineKeyboardMarkup]:
    b_id = int(detail["id"])
    status = detail["status"]
    cases = detail["cases"]
    parts = detail["participants"]
    max_p = int(detail["max_players"] or 2)
    cost = int(detail["total_cost_stars"] or 0)
    is_member = any(int(p["user_id"]) == int(viewer_id) for p in parts)
    is_creator = int(detail["creator_id"]) == int(viewer_id)

    now = int(time.time())
    if status == "waiting":
        st_line = f"🟢 <b>Ожидание игроков ({len(parts)}/{max_p})</b>"
    elif status == "countdown":
        rem = max(0, int(detail["countdown_ends_ts"] or 0) - now)
        st_line = f"{ce('hourglass')} <b>Все места заняты! Старт через {rem} сек...</b>"
    elif status == "running":
        st_line = f"{ce('bolt')} <b>Баттл идёт! Открываем кейсы...</b>"
    elif status == "finished":
        st_line = f"{ce('check')} <b>Баттл завершён!</b>"
    else:
        st_line = f"{ce('cross')} <b>Баттл отменён</b>"

    p_lines = []
    for idx, p in enumerate(parts, start=1):
        pname = normalize_telegram_name(p.get("first_name"), p.get("username"), int(p["user_id"]))
        crown = " 👑" if int(p["user_id"]) == int(detail["creator_id"]) else ""
        p_lines.append(f"  {idx}. <b>{clean_html(pname)}</b>{crown}")
    for slot_idx in range(len(parts) + 1, max_p + 1):
        p_lines.append(f"  {slot_idx}. <i>[ Свободное место ]</i>")

    lines = [
        f"{ce('bolt')} <b>Баттл кейсов #{b_id}</b>",
        "━━━━━━━━━━━━",
        f"• Статус: {st_line}",
        f"• Ставка: <b>{cost:,} {ce('star')}</b> (банк кейсов: <b>{cost * max_p:,} ⭐</b>)",
        f"• Кейсы ({len(cases)} шт.): {_summarize_battle_cases(cases)}\n",
        f"👥 <b>Участники ({len(parts)}/{max_p}):</b>",
        *p_lines,
    ]

    if status == "finished" and detail.get("results"):
        res = detail["results"]
        if isinstance(res, dict) and res.get("players"):
            lines.append("\n📊 <b>Итоговый счёт:</b>")
            w_id = int(detail.get("winner_id") or 0)
            for pl in res["players"]:
                mark = "🏆 " if int(pl["user_id"]) == w_id else "• "
                lines.append(f"{mark}<b>{clean_html(pl['name'])}</b> — <b>{int(pl['total_stars']):,} ⭐</b> ({len(pl['drops'])} шт.)")
            if res.get("tie_break"):
                lines.append("<i>⚔️ Ничья по очкам — победитель определён тай-брейком!</i>")

    buttons = []
    if status == "waiting":
        if not is_member and len(parts) < max_p:
            buttons.append([make_btn(f"Вступить за {cost:,} ⭐", style="success", emoji_key="bolt", callback_data=f"battle_join:{b_id}")])
        if is_member:
            leave_lbl = "Отменить баттл (возврат ⭐)" if is_creator else "Выйти (возврат ⭐)"
            buttons.append([make_btn(leave_lbl, style="danger", emoji_key="cross", callback_data=f"battle_leave:{b_id}")])
        buttons.append([make_btn("Обновить", emoji_key="refresh", callback_data=f"battle_view:{b_id}")])
    elif status in ("countdown", "running"):
        buttons.append([make_btn("Обновить статус", emoji_key="refresh", callback_data=f"battle_view:{b_id}")])

    buttons.append([
        make_btn("Все баттлы", emoji_key="game", callback_data="battles_list:1"),
        make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main"),
    ])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)

async def show_battle_room(query, user_id: int, battle_id: int, bot) -> None:
    detail = get_case_battle_detail_db(battle_id)
    if not detail:
        await query.answer("❌ Баттл не найден.", show_alert=True)
        await show_battles_list(query, user_id, page=1)
        return
    text, kb = _build_battle_room_view(detail, user_id)
    msg_obj = None
    if query.message and query.message.photo:
        try:
            await query.message.delete()
        except Exception:
            pass
        msg_obj = await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    elif query.message:
        try:
            msg_obj = await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception:
            msg_obj = query.message

    if msg_obj and any(int(p["user_id"]) == int(user_id) for p in detail["participants"]):
        update_battle_participant_msg_db(battle_id, user_id, msg_obj.chat_id, msg_obj.message_id)

async def _broadcast_battle_room(bot, battle_id: int, skip_user_id: Optional[int] = None, custom_text: Optional[str] = None, custom_kb: Optional[InlineKeyboardMarkup] = None) -> None:
    detail = get_case_battle_detail_db(battle_id)
    if not detail:
        return
    for p in detail["participants"]:
        p_uid = int(p["user_id"])
        if skip_user_id is not None and p_uid == int(skip_user_id):
            continue
        chat_id = p.get("ui_chat_id")
        msg_id = p.get("ui_message_id")
        if not chat_id or not msg_id:
            continue
        text, kb = (custom_text, custom_kb) if custom_text is not None else _build_battle_room_view(detail, p_uid)
        try:
            await bot.edit_message_text(
                chat_id=int(chat_id),
                message_id=int(msg_id),
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
        except Exception:
            pass

def _ensure_battle_task(bot, battle_id: int) -> None:
    existing = _ACTIVE_BATTLE_TASKS.get(battle_id)
    if existing and not existing.done():
        return
    task = asyncio.create_task(_run_case_battle_task(bot, battle_id))
    _ACTIVE_BATTLE_TASKS[battle_id] = task

async def _run_case_battle_task(bot, battle_id: int) -> None:
    try:
        detail = get_case_battle_detail_db(battle_id)
        if not detail or detail["status"] not in ("countdown", "running"):
            return

        if detail["status"] == "countdown":
            while True:
                detail = get_case_battle_detail_db(battle_id)
                if not detail or detail["status"] != "countdown":
                    break
                rem = int(detail["countdown_ends_ts"] or 0) - int(time.time())
                if rem <= 0:
                    break
                await _broadcast_battle_room(bot, battle_id)
                step = 5 if rem > 5 else (rem if rem <= 3 else rem - 3)
                await asyncio.sleep(max(1, min(step, rem)))

            start_battle_running_db(battle_id)

        detail = get_case_battle_detail_db(battle_id)
        if not detail or detail["status"] != "running":
            return

        cases: List[str] = detail["cases"]
        parts: List[dict] = detail["participants"]
        if not parts or not cases:
            return

        player_states: List[dict] = []
        for p in parts:
            uid = int(p["user_id"])
            pname = normalize_telegram_name(p.get("first_name"), p.get("username"), uid)
            clan = get_user_clan(uid)
            bonus_pct = 0.0
            if clan:
                _, _, _, _, bonus_pct = calculate_clan_level_info(clan["xp"])
            player_states.append({
                "user_id": uid,
                "name": pname,
                "clan_bonus_pct": bonus_pct,
                "drops": [],
                "total_stars": 0,
                "total_xp": 0,
            })

        all_dropped_items: List[dict] = []

        for r_idx, ckey in enumerate(cases, start=1):
            tier = CASE_TIERS.get(ckey) or next(iter(CASE_TIERS.values()))
            round_lines = [
                f"{ce('bolt')} <b>Баттл #{battle_id} — Раунд {r_idx}/{len(cases)}</b>",
                f"📦 Открываем: <b>{tier['name']}</b>",
                "━━━━━━━━━━━━",
            ]
            for st in player_states:
                won = roll_case_gift(tier, clan_bonus_pct=st["clan_bonus_pct"])
                b_bg, b_mdl, b_val = 0, 0, 0
                if tier.get("rolls_buffs") and won.key in UPGRADABLE_GIFT_KEYS:
                    b_bg, b_mdl, b_val = roll_item_buffs()
                drop_rec = {
                    "gift_key": won.key,
                    "gift_name": won.name,
                    "stars": int(won.stars),
                    "xp": int(won.xp),
                    "buff_backdrop_pct": b_bg,
                    "buff_model_pct": b_mdl,
                    "buff_value_pct": b_val,
                }
                st["drops"].append(drop_rec)
                st["total_stars"] += int(won.stars)
                st["total_xp"] += int(won.xp)
                all_dropped_items.append(drop_rec)
                b_note = " ⚡" if (b_bg + b_mdl + b_val) > 0 else ""
                round_lines.append(
                    f"• <b>{clean_html(st['name'])}</b>: {clean_html(won.name)}{b_note} "
                    f"(<b>+{won.stars:,} ⭐</b>) → Итого: <b>{st['total_stars']:,} ⭐</b>"
                )

            await _broadcast_battle_room(
                bot,
                battle_id,
                custom_text="\n".join(round_lines),
                custom_kb=None,
            )
            if r_idx < len(cases):
                await asyncio.sleep(0.8)

        max_stars = max(st["total_stars"] for st in player_states)
        top_players = [st for st in player_states if st["total_stars"] == max_stars]
        tie_break = len(top_players) > 1
        winner = random.choice(top_players)
        winner_id = int(winner["user_id"])

        total_loot_stars = sum(int(d["stars"]) for d in all_dropped_items)
        total_loot_xp = sum(int(d["xp"]) for d in all_dropped_items)

        results_payload = {
            "tie_break": tie_break,
            "total_loot_stars": total_loot_stars,
            "total_loot_items": len(all_dropped_items),
            "players": [
                {
                    "user_id": st["user_id"],
                    "name": st["name"],
                    "total_stars": st["total_stars"],
                    "drops": st["drops"],
                }
                for st in sorted(player_states, key=lambda x: x["total_stars"], reverse=True)
            ],
        }

        ok_fin = finish_case_battle_db(
            battle_id=battle_id,
            winner_id=winner_id,
            winner_total_stars=int(winner["total_stars"]),
            results_payload=results_payload,
            all_dropped_items=all_dropped_items,
        )
        if not ok_fin:
            return

        score_lines = []
        for rank_i, pl in enumerate(results_payload["players"], start=1):
            medal = "🏆" if int(pl["user_id"]) == winner_id else f"{rank_i}."
            score_lines.append(
                f"{medal} <b>{clean_html(pl['name'])}</b> — <b>{int(pl['total_stars']):,} {ce('star')}</b>"
            )
        tie_note = "\n<i>⚔️ Ничья по звёздам — победитель определён тай-брейком!</i>" if tie_break else ""

        top_loot = sorted(all_dropped_items, key=lambda x: x["stars"], reverse=True)[:5]
        loot_preview = "\n".join(
            f"  • {clean_html(d['gift_name'])} (<b>{int(d['stars']):,} ⭐</b>)"
            + (" ⚡" if (d["buff_backdrop_pct"] + d["buff_model_pct"] + d["buff_value_pct"]) > 0 else "")
            for d in top_loot
        )
        if len(all_dropped_items) > 5:
            loot_preview += f"\n  <i>… и ещё {len(all_dropped_items) - 5} предмет(ов)</i>"

        fin_kb = InlineKeyboardMarkup([
            [make_btn("В коллекцию", emoji_key="bookmark", callback_data="nav_collection_page:1")],
            [
                make_btn("Все баттлы", emoji_key="game", callback_data="battles_list:1"),
                make_btn("Главное меню", emoji_key="desktop", callback_data="nav_main"),
            ],
        ])

        for p in parts:
            p_uid = int(p["user_id"])
            is_win = (p_uid == winner_id)
            header = (
                f"{ce('boom')} <b>ВЫ ПОБЕДИЛИ В БАТТЛЕ #{battle_id}!</b>"
                if is_win
                else f"{ce('crown')} <b>Баттл #{battle_id} завершён! Победитель: {clean_html(winner['name'])}</b>"
            )
            loot_status = (
                f"{ce('check')} <b>Весь дроп ({len(all_dropped_items)} шт. на {total_loot_stars:,} ⭐ и +{total_loot_xp:,} XP) добавлен в вашу коллекцию!</b>"
                if is_win
                else f"{ce('bookmark')} Все <b>{len(all_dropped_items)}</b> предметов (<b>{total_loot_stars:,} ⭐</b>) достались победителю."
            )
            fin_text = (
                f"{header}\n"
                "━━━━━━━━━━━━\n"
                + "\n".join(score_lines)
                + f"{tie_note}\n\n"
                f"{ce('sparkles')} <b>Топ дроп баттла:</b>\n{loot_preview}\n\n"
                f"{loot_status}"
            )
            edited = False
            if p.get("ui_chat_id") and p.get("ui_message_id"):
                try:
                    await bot.edit_message_text(
                        chat_id=int(p["ui_chat_id"]),
                        message_id=int(p["ui_message_id"]),
                        text=fin_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=fin_kb,
                    )
                    edited = True
                except Exception:
                    pass
            if not edited:
                try:
                    await bot.send_message(
                        chat_id=p_uid,
                        text=fin_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=fin_kb,
                    )
                except Exception:
                    pass
    except asyncio.CancelledError:
        pass
    except Exception as e:
        log.error("Ошибка баттла #%s: %s", battle_id, e)
    finally:
        _ACTIVE_BATTLE_TASKS.pop(battle_id, None)

# --- ФОНОВЫЙ ПЛАНИРОВЩИК КОНКУРСОВ ---

async def _giveaway_scheduler_loop(app: Application) -> None:
    while True:
        try:
            now = int(time.time())
            due_pub = get_due_scheduled_giveaways_db(now)
            for gw in due_pub:
                try:
                    await publish_giveaway_to_channels(app.bot, gw)
                except Exception as e:
                    log.error("Ошибка автопубликации конкурса #%s: %s", gw["id"], e)

            due_end = get_due_active_giveaways_db(now)
            for gw in due_end:
                try:
                    await finalize_giveaway_and_notify(app.bot, int(gw["id"]))
                except Exception as e:
                    log.error("Ошибка автозавершения конкурса #%s: %s", gw["id"], e)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("Ошибка цикла планировщика конкурсов: %s", e)
        await asyncio.sleep(10)

_SCARED_CAT_PROMO_TASK: Optional[asyncio.Task] = None

async def broadcast_scared_cat_promo_once(bot) -> dict:
    sold, remaining = get_scared_cat_supply_stats()
    if remaining <= 0:
        return {"skipped": True, "remaining": 0, "sent": 0, "blocked": 0, "failed": 0}

    card_io = None
    try:
        card_io = await generate_scared_cat_promo_card_image(sold, remaining)
    except Exception as e:
        log.warning("Ошибка генерации промо-карты Scared Cat: %s", e)
        try:
            card_io = await generate_gift_card_image(SCARED_CAT_DEF)
        except Exception:
            card_io = None

    raw_bytes = card_io.getvalue() if card_io else b""
    pct = min(100, int(round((sold / SCARED_CAT_MAX_SUPPLY) * 100))) if SCARED_CAT_MAX_SUPPLY else 100
    cap = (
        f"{ce('fire')} <b>АКЦИЯ: ЛИМИТИРОВАННЫЙ SCARED CAT!</b>\n"
        "━━━━━━━━━━━━\n"
        f"{ce('gem')} Уникальный красный коллекционный NFT — <b>Scared Cat</b> (всего 1,000 шт. на сервер)!\n"
        f"{ce('green_dot')} Осталось в наличии: <b>{remaining:,} из {SCARED_CAT_MAX_SUPPLY:,}</b> шт. (выкуплено {pct}%)\n"
        f"{ce('star')} Цена в разделе «Акции»: <b>{SCARED_CAT_PROMO_PRICE:,} {ce('star')}</b>\n"
        f"{ce('sparkles')} У каждого кота свой уникальный серийный номер <code>#1..#1000</code>!\n"
        "━━━━━━━━━━━━\n"
        f"Жмите кнопку ниже и успейте забрать своего <b>Scared Cat</b>, пока тираж не закончился {ce('eyes')}"
    )
    kb = InlineKeyboardMarkup([
        [make_btn("Перейти в акции", style="primary", emoji_key="fire", callback_data="nav_promos")]
    ])

    user_ids = get_all_broadcast_user_ids_db()
    sent = 0
    blocked = 0
    failed = 0
    cached_file_id = ""

    async def _send_to_one(uid: int) -> Optional[str]:
        if cached_file_id:
            await bot.send_photo(chat_id=uid, photo=cached_file_id, caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
            return cached_file_id
        if raw_bytes:
            m = await bot.send_photo(
                chat_id=uid,
                photo=InputFile(io.BytesIO(raw_bytes), filename="promo_scared_cat.png"),
                caption=cap,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
            if m and getattr(m, "photo", None):
                return m.photo[-1].file_id
            return ""
        await bot.send_message(chat_id=uid, text=cap, parse_mode=ParseMode.HTML, reply_markup=kb)
        return ""

    for uid in user_ids:
        try:
            fid = await _send_to_one(uid)
            if fid and not cached_file_id:
                cached_file_id = fid
            sent += 1
        except RetryAfter as e:
            await asyncio.sleep(float(getattr(e, "retry_after", 2)) + 0.5)
            try:
                fid = await _send_to_one(uid)
                if fid and not cached_file_id:
                    cached_file_id = fid
                sent += 1
            except Forbidden:
                blocked += 1
            except Exception:
                failed += 1
        except Forbidden:
            blocked += 1
        except BadRequest as e:
            err_l = str(e).lower()
            if "chat not found" in err_l or "blocked" in err_l or "deactivated" in err_l:
                blocked += 1
            else:
                failed += 1
        except TelegramError:
            failed += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.04)

    return {"skipped": False, "remaining": remaining, "sent": sent, "blocked": blocked, "failed": failed}

async def _scared_cat_promo_broadcast_loop(app: Application) -> None:
    try:
        await asyncio.sleep(5)
        while True:
            _, remaining = get_scared_cat_supply_stats()
            if remaining <= 0:
                log.info("Промо-рассылка Scared Cat остановлена: весь тираж (1,000/1,000) распродан.")
                break
            try:
                res = await broadcast_scared_cat_promo_once(app.bot)
                log.info(
                    "Промо-рассылка Scared Cat (осталось %s): отправлено=%s, забл.=%s, ош.=%s",
                    res.get("remaining"), res.get("sent"), res.get("blocked"), res.get("failed"),
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.error("Ошибка промо-рассылки Scared Cat: %s", e)

            _, remaining_after = get_scared_cat_supply_stats()
            if remaining_after <= 0:
                log.info("Промо-рассылка Scared Cat завершена: 1,000/1,000 выкуплено.")
                break
            await asyncio.sleep(SCARED_CAT_PROMO_INTERVAL_SEC)
    except asyncio.CancelledError:
        pass

# ---------------------------------------------------------------------------
# MINI APP HTTP + WEBSOCKET SERVER (PORT 3000) & GAME/EXCHANGE ENGINE
# ---------------------------------------------------------------------------

_MINIAPP_RUNNER = None
_MINIAPP_SITE = None
_ROCKET_TASK: Optional[asyncio.Task] = None
_WS_CLIENTS: set = set()
_BOT_APP_REF: Optional[Application] = None


def verify_telegram_init_data(raw_init_data: str) -> Optional[dict]:
    if not raw_init_data or not BOT_TOKEN:
        return None
    try:
        parsed = dict(urllib.parse.parse_qsl(raw_init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", "")
        if not received_hash:
            return None
        auth_date = int(parsed.get("auth_date", "0") or "0")
        if auth_date <= 0 or abs(int(time.time()) - auth_date) > 86400 * 7:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
        calc_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc_hash, received_hash):
            return None
        user_raw = parsed.get("user", "")
        if not user_raw:
            return None
        user_obj = json.loads(user_raw)
        if not isinstance(user_obj, dict) or not user_obj.get("id"):
            return None
        return user_obj
    except Exception:
        return None


def _item_image_urls(item_row) -> Tuple[str, str]:
    canon_key = canonical_gift_key(item_row["gift_key"])
    base_url = f"/api/assets/gift/{urllib.parse.quote(canon_key)}"
    if int(item_row["is_upgraded"] or 0) == 1 and item_row["model_name"]:
        mdef = get_model_def(canon_key, item_row["model_name"])
        model_url = f"/api/assets/model/{urllib.parse.quote(canon_key)}/{urllib.parse.quote(mdef.filename)}"
        return model_url, base_url
    return base_url, base_url


def serialize_collection_item(row) -> dict:
    canon_key = canonical_gift_key(row["gift_key"])
    g = GIFTS_BY_KEY.get(canon_key)
    bd = BACKDROPS_BY_KEY.get(row["backdrop_key"] or "") if row["backdrop_key"] else None
    image_url, base_image_url = _item_image_urls(row)
    b_bg, b_mdl, b_val = get_item_buffs(row)
    return {
        "id": int(row["id"]),
        "gift_key": canon_key,
        "name": g.name if g else canon_key,
        "base_stars": int(g.stars if g else 0),
        "display_stars": get_item_display_value(row),
        "is_upgraded": bool(int(row["is_upgraded"] or 0)),
        "model_name": row["model_name"],
        "backdrop_key": row["backdrop_key"],
        "backdrop_name": bd.name if bd else None,
        "backdrop_center_hex": bd.center_hex if bd else None,
        "backdrop_edge_hex": bd.edge_hex if bd else None,
        "upgrade_num": int(row["upgrade_num"] or 0),
        "is_listed": int(row["is_listed"] or 0),
        "is_favorite": bool(int(row["is_favorite"] or 0)),
        "image_url": image_url,
        "base_image_url": base_image_url,
        "buff_backdrop_pct": b_bg,
        "buff_model_pct": b_mdl,
        "buff_value_pct": b_val,
    }


def serialize_user_profile(user_row) -> dict:
    total_xp = int(user_row["xp"] or 0)
    level, cur_xp, req_xp, ratio = calculate_xp_level_info(total_xp)
    uid = int(user_row["user_id"])
    return {
        "user_id": uid,
        "id_num": int(user_row["id_num"] or 0),
        "username": user_row["username"] or "",
        "first_name": user_row["first_name"] or f"ID {uid}",
        "avatar_url": f"/api/assets/avatar/{uid}",
        "balance_stars": int(user_row["balance_stars"] or 0),
        "balance_tons": round(float(user_row["balance_tons"] or 0.0), 6),
        "xp": total_xp,
        "level": level,
        "xp_current": cur_xp,
        "xp_required": req_xp,
        "xp_ratio": round(ratio, 4),
        "max_inventory": int(user_row["max_inventory"] or 25),
    }


def get_mini_app_catalog() -> dict:
    upgradable_gifts = []
    for k in UPGRADABLE_GIFT_KEYS:
        g = GIFTS_BY_KEY.get(k)
        if g:
            upgradable_gifts.append({
                "key": k,
                "title": get_upgraded_gift_title(k),
                "name": g.name,
                "base_stars": g.stars,
                "upgrade_cost": get_upgrade_cost(k),
                "image_url": f"/api/assets/gift/{urllib.parse.quote(k)}",
            })
    models_by_gift = {}
    for k in UPGRADABLE_GIFT_KEYS:
        models_by_gift[k] = [
            {
                "name": m.name,
                "filename": m.filename,
                "chance_pct": m.chance_pct,
                "price_mult": m.price_mult,
                "image_url": f"/api/assets/model/{urllib.parse.quote(k)}/{urllib.parse.quote(m.filename)}",
            }
            for m in get_models_for_gift(k)
        ]
    backdrops = [
        {
            "key": b.key,
            "name": b.name,
            "palette": b.palette,
            "center_hex": b.center_hex,
            "edge_hex": b.edge_hex,
            "price_mult": b.price_mult,
            "rarity_label": b.rarity_label,
        }
        for b in PLUSHPEPE_BACKDROPS
    ]
    return {
        "upgradable_gifts": upgradable_gifts,
        "models_by_gift": models_by_gift,
        "backdrops": backdrops,
        "ton_star_rate": TON_STAR_RATE,
        "memecoin_min_level": MEMECOIN_MIN_LEVEL,
        "memecoin_create_ton_cost": MEMECOIN_CREATE_TON_COST,
        "upgrader_chance_factor": UPGRADER_CHANCE_FACTOR,
        "rocket_upgrade_mult_penalty": ROCKET_UPGRADE_MULT_PENALTY,
    }


def compute_upgrader_target_and_chance(
    source_val: int,
    target_gift_key: str,
    target_model_name: Optional[str] = None,
    target_backdrop_key: Optional[str] = None,
    value_buff_pct: int = 0,
) -> Tuple[PlushModelDef, BackdropDef, int, float]:
    canon_target = canonical_gift_key(target_gift_key)
    target_gift = GIFTS_BY_KEY.get(canon_target) or GIFTS_BY_KEY["pepe_heart"]
    model_def = get_model_def(canon_target, target_model_name) if target_model_name else get_models_for_gift(canon_target)[0]
    backdrop_def = BACKDROPS_BY_KEY.get(target_backdrop_key or "") or PLUSHPEPE_BACKDROPS[-1]
    target_stars = calculate_upgraded_stars(
        target_gift.stars,
        model_def,
        backdrop_def,
        canon_target,
        value_buff_pct,
    )
    raw_ratio = max(1, int(source_val)) / max(1, int(target_stars))
    chance_pct = round(max(1.0, min(72.0, raw_ratio * 100.0 * UPGRADER_CHANCE_FACTOR)), 2)
    return model_def, backdrop_def, int(target_stars), chance_pct


def miniapp_upgrade_item_db(
    user_id: int,
    source_item_id: int,
    target_gift_key: str,
    target_model_name: Optional[str] = None,
    target_backdrop_key: Optional[str] = None,
) -> Tuple[bool, str, dict]:
    canon_target = canonical_gift_key(target_gift_key)
    if canon_target not in UPGRADABLE_GIFT_KEYS:
        return False, "Недоступная цель для апгрейда.", {}
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        item = conn.execute("SELECT * FROM collection WHERE id=? AND user_id=?", (source_item_id, user_id)).fetchone()
        if not item:
            conn.rollback()
            return False, "Предмет не найден в коллекции.", {}
        if int(item["is_listed"] or 0) != 0:
            conn.rollback()
            return False, "Предмет сейчас занят (на маркете или в игре).", {}

        source_val = get_item_display_value(item)
        _, _, b_val = get_item_buffs(item)
        model_def, backdrop_def, target_stars, chance_pct = compute_upgrader_target_and_chance(
            source_val, canon_target, target_model_name, target_backdrop_key, b_val
        )
        roll = round(random.random() * 100.0, 2)
        won = roll < chance_pct

        conn.execute("DELETE FROM collection WHERE id=? AND user_id=?", (source_item_id, user_id))
        new_item_dict = None
        if won:
            mx = conn.execute("SELECT COALESCE(MAX(upgrade_num), 0) AS mx FROM collection").fetchone()
            next_num = int(mx["mx"] or 0) + 1
            now_ts = int(time.time())
            cur = conn.execute(
                "INSERT INTO collection "
                "(user_id, gift_key, obtained_ts, is_favorite, is_upgraded, model_name, backdrop_key, upgraded_stars, upgrade_num, is_listed) "
                "VALUES (?, ?, ?, 0, 1, ?, ?, ?, ?, 0)",
                (user_id, canon_target, now_ts, model_def.name, backdrop_def.key, target_stars, next_num),
            )
            conn.execute("UPDATE users SET xp=xp+3500 WHERE user_id=?", (user_id,))
            new_row = conn.execute("SELECT * FROM collection WHERE id=?", (int(cur.lastrowid),)).fetchone()
            new_item_dict = serialize_collection_item(new_row)
        else:
            conn.execute("UPDATE users SET xp=xp+500 WHERE user_id=?", (user_id,))
        conn.commit()
        return True, "OK", {
            "won": won,
            "chance_pct": chance_pct,
            "roll": roll,
            "source_stars": source_val,
            "target_stars": target_stars,
            "new_item": new_item_dict,
        }
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def swap_stars_ton_db(user_id: int, direction: str, amount: float) -> Tuple[bool, str, dict]:
    if amount <= 0:
        return False, "Сумма должна быть больше нуля.", {}
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        u = conn.execute("SELECT balance_stars, balance_tons FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not u:
            conn.rollback()
            return False, "Пользователь не найден.", {}
        cur_stars = int(u["balance_stars"] or 0)
        cur_tons = float(u["balance_tons"] or 0.0)

        if direction == "stars_to_ton":
            stars_in = int(round(amount))
            if stars_in < 100:
                conn.rollback()
                return False, "Минимум для обмена — 100 ⭐.", {}
            if cur_stars < stars_in:
                conn.rollback()
                return False, "Недостаточно Stars на балансе.", {}
            tons_out = round(stars_in / TON_STAR_RATE, 6)
            new_stars = cur_stars - stars_in
            new_tons = round(cur_tons + tons_out, 6)
            conn.execute("UPDATE users SET balance_stars=?, balance_tons=? WHERE user_id=?", (new_stars, new_tons, user_id))
            record_star_flow(spent=stars_in, burned=stars_in, conn=conn)
            conn.commit()
            return True, "OK", {"balance_stars": new_stars, "balance_tons": new_tons, "swapped_tons": tons_out, "swapped_stars": -stars_in}
        elif direction == "ton_to_stars":
            tons_in = round(float(amount), 6)
            if tons_in < 0.1:
                conn.rollback()
                return False, "Минимум для обмена — 0.1 TON.", {}
            if cur_tons + 1e-9 < tons_in:
                conn.rollback()
                return False, "Недостаточно TON на балансе.", {}
            stars_out = int(round(tons_in * TON_STAR_RATE))
            if stars_out <= 0:
                conn.rollback()
                return False, "Слишком маленькая сумма TON.", {}
            new_tons = round(max(0.0, cur_tons - tons_in), 6)
            new_stars = cur_stars + stars_out
            conn.execute("UPDATE users SET balance_stars=?, balance_tons=? WHERE user_id=?", (new_stars, new_tons, user_id))
            record_star_flow(issued=stars_out, conn=conn)
            conn.commit()
            return True, "OK", {"balance_stars": new_stars, "balance_tons": new_tons, "swapped_tons": -tons_in, "swapped_stars": stars_out}
        else:
            conn.rollback()
            return False, "Неверное направление обмена.", {}
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def _validate_memecoin_image(image_b64: str) -> Tuple[bool, str]:
    raw = (image_b64 or "").strip()
    m = re.match(r"^data:image/(png|jpeg|jpg|webp);base64,([A-Za-z0-9+/=\s]+)$", raw, flags=re.IGNORECASE)
    if not m:
        return False, "Загрузите корректное изображение PNG, JPG или WEBP."
    fmt = m.group(1).lower()
    b64_payload = re.sub(r"\s+", "", m.group(2))
    try:
        decoded = base64.b64decode(b64_payload, validate=True)
    except Exception:
        return False, "Повреждённые данные изображения."
    if len(decoded) < 32 or len(decoded) > 850_000:
        return False, "Размер изображения должен быть до 800 КБ."
    if fmt == "png" and not decoded.startswith(b"\x89PNG\r\n\x1a\n"):
        return False, "Неверная сигнатура PNG файла."
    if fmt in ("jpeg", "jpg") and not decoded.startswith(b"\xff\xd8\xff"):
        return False, "Неверная сигнатура JPEG файла."
    if fmt == "webp" and not (decoded[:4] == b"RIFF" and decoded[8:12] == b"WEBP"):
        return False, "Неверная сигнатура WEBP файла."
    norm_fmt = "jpeg" if fmt == "jpg" else fmt
    return True, f"data:image/{norm_fmt};base64,{b64_payload}"


def create_memecoin_db(user_id: int, name: str, ticker: str, image_b64: str) -> Tuple[bool, str, dict]:
    clean_name = re.sub(r"\s+", " ", (name or "").strip())
    if len(clean_name) < 2 or len(clean_name) > 32:
        return False, "Название мемкоина должно быть от 2 до 32 символов.", {}
    raw_ticker = re.sub(r"[^A-Za-zА-Яа-я0-9]", "", (ticker or "").strip()).upper()
    if not raw_ticker:
        raw_ticker = re.sub(r"[^A-Za-z0-9]", "", clean_name).upper()[:6] or "MEME"
    if len(raw_ticker) < 2 or len(raw_ticker) > 8:
        return False, "Тикер должен содержать от 2 до 8 символов.", {}

    ok_img, img_or_err = _validate_memecoin_image(image_b64)
    if not ok_img:
        return False, img_or_err, {}

    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        u = conn.execute("SELECT xp, balance_tons FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not u:
            conn.rollback()
            return False, "Пользователь не найден.", {}
        level, _, _, _ = calculate_xp_level_info(int(u["xp"] or 0))
        if level <= MEMECOIN_MIN_LEVEL:
            conn.rollback()
            return False, f"Для создания мемкоина нужен уровень выше {MEMECOIN_MIN_LEVEL} (ваш: {level}).", {}
        cur_tons = float(u["balance_tons"] or 0.0)
        if cur_tons + 1e-9 < MEMECOIN_CREATE_TON_COST:
            conn.rollback()
            return False, f"Недостаточно TON! Требуется {MEMECOIN_CREATE_TON_COST:,.0f} TON (эквивалент 20,000,000 ⭐).", {}

        new_tons = round(cur_tons - MEMECOIN_CREATE_TON_COST, 6)
        conn.execute("UPDATE users SET balance_tons=? WHERE user_id=?", (new_tons, user_id))

        total_supply = 1_000_000.0
        reserve_ton = 250.0
        reserve_token = 1_000_000.0
        init_price = reserve_ton / reserve_token
        init_mcap = init_price * total_supply
        now_ts = int(time.time())
        bucket_ts = now_ts - (now_ts % 60)

        cur = conn.execute(
            "INSERT INTO memecoins "
            "(creator_id, name, ticker, image_b64, reserve_ton, reserve_token, total_supply, price_ton, market_cap_ton, volume_24h_ton, holders_count, created_ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 1, ?)",
            (user_id, clean_name, raw_ticker, img_or_err, reserve_ton, reserve_token, total_supply, init_price, init_mcap, now_ts),
        )
        coin_id = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO memecoin_candles (coin_id, bucket_ts, open_ton, high_ton, low_ton, close_ton, volume_ton) "
            "VALUES (?, ?, ?, ?, ?, ?, 0.0)",
            (coin_id, bucket_ts, init_price, init_price, init_price, init_price),
        )
        conn.commit()
        coin_row = conn.execute("SELECT * FROM memecoins WHERE id=?", (coin_id,)).fetchone()
        return True, "OK", {"coin": serialize_memecoin_row(coin_row), "balance_tons": new_tons}
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def serialize_memecoin_row(row) -> dict:
    return {
        "id": int(row["id"]),
        "creator_id": int(row["creator_id"]),
        "name": row["name"],
        "ticker": row["ticker"],
        "image_url": row["image_b64"],
        "reserve_ton": round(float(row["reserve_ton"]), 6),
        "reserve_token": round(float(row["reserve_token"]), 4),
        "total_supply": float(row["total_supply"]),
        "price_ton": round(float(row["price_ton"]), 8),
        "price_stars": round(float(row["price_ton"]) * TON_STAR_RATE, 4),
        "market_cap_ton": round(float(row["market_cap_ton"]), 4),
        "volume_24h_ton": round(float(row["volume_24h_ton"] or 0.0), 4),
        "holders_count": int(row["holders_count"] or 1),
        "created_ts": int(row["created_ts"]),
    }


def list_memecoins_db(user_id: int = 0) -> list[dict]:
    conn = db_connect()
    try:
        rows = conn.execute("SELECT * FROM memecoins ORDER BY market_cap_ton DESC, id DESC").fetchall()
        holdings = {}
        if user_id:
            for h in conn.execute("SELECT coin_id, amount FROM memecoin_holdings WHERE user_id=? AND amount > 0", (user_id,)).fetchall():
                holdings[int(h["coin_id"])] = float(h["amount"])
        result = []
        for r in rows:
            d = serialize_memecoin_row(r)
            first_c = conn.execute(
                "SELECT open_ton FROM memecoin_candles WHERE coin_id=? ORDER BY bucket_ts ASC LIMIT 1",
                (d["id"],),
            ).fetchone()
            base_open = float(first_c["open_ton"]) if first_c and float(first_c["open_ton"]) > 0 else d["price_ton"]
            d["change_pct"] = round(((d["price_ton"] - base_open) / base_open) * 100.0, 2) if base_open > 0 else 0.0
            d["my_balance"] = round(holdings.get(d["id"], 0.0), 4)
            result.append(d)
        return result
    finally:
        conn.close()


def get_memecoin_detail_db(coin_id: int, user_id: int = 0) -> Optional[dict]:
    conn = db_connect()
    try:
        r = conn.execute("SELECT * FROM memecoins WHERE id=?", (coin_id,)).fetchone()
        if not r:
            return None
        coin_d = serialize_memecoin_row(r)
        candles = [
            {
                "time": int(c["bucket_ts"]),
                "open": float(c["open_ton"]),
                "high": float(c["high_ton"]),
                "low": float(c["low_ton"]),
                "close": float(c["close_ton"]),
                "volume": round(float(c["volume_ton"] or 0.0), 4),
            }
            for c in conn.execute(
                "SELECT * FROM memecoin_candles WHERE coin_id=? ORDER BY bucket_ts ASC LIMIT 240",
                (coin_id,),
            ).fetchall()
        ]
        trades = [
            {
                "id": int(t["id"]),
                "user_id": int(t["user_id"]),
                "side": t["side"],
                "ton_amount": round(float(t["ton_amount"]), 6),
                "token_amount": round(float(t["token_amount"]), 4),
                "price_ton": round(float(t["price_ton"]), 8),
                "created_ts": int(t["created_ts"]),
            }
            for t in conn.execute(
                "SELECT * FROM memecoin_trades WHERE coin_id=? ORDER BY id DESC LIMIT 30",
                (coin_id,),
            ).fetchall()
        ]
        holding_amt = 0.0
        if user_id:
            h = conn.execute("SELECT amount FROM memecoin_holdings WHERE user_id=? AND coin_id=?", (user_id, coin_id)).fetchone()
            if h:
                holding_amt = float(h["amount"] or 0.0)
        base_open = candles[0]["open"] if candles and candles[0]["open"] > 0 else coin_d["price_ton"]
        coin_d["change_pct"] = round(((coin_d["price_ton"] - base_open) / base_open) * 100.0, 2) if base_open > 0 else 0.0
        coin_d["my_balance"] = round(holding_amt, 4)
        return {"coin": coin_d, "candles": candles, "trades": trades}
    finally:
        conn.close()


def trade_memecoin_db(user_id: int, coin_id: int, side: str, amount: float) -> Tuple[bool, str, dict]:
    if amount <= 0:
        return False, "Укажите сумму больше 0.", {}
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        coin = conn.execute("SELECT * FROM memecoins WHERE id=?", (coin_id,)).fetchone()
        if not coin:
            conn.rollback()
            return False, "Монета не найдена.", {}
        u = conn.execute("SELECT balance_tons FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not u:
            conn.rollback()
            return False, "Пользователь не найден.", {}

        cur_tons = float(u["balance_tons"] or 0.0)
        res_ton = float(coin["reserve_ton"])
        res_tok = float(coin["reserve_token"])
        total_supply = float(coin["total_supply"])
        k_const = res_ton * res_tok
        now_ts = int(time.time())
        bucket_ts = now_ts - (now_ts % 60)

        if side == "buy":
            ton_in = round(float(amount), 6)
            if ton_in < 0.01:
                conn.rollback()
                return False, "Минимальная покупка — 0.01 TON.", {}
            if cur_tons + 1e-9 < ton_in:
                conn.rollback()
                return False, "Недостаточно TON на балансе.", {}
            effective_ton = ton_in * 0.99
            new_res_ton = res_ton + effective_ton
            new_res_tok = k_const / new_res_ton
            tokens_out = max(0.0, res_tok - new_res_tok)
            if tokens_out <= 0:
                conn.rollback()
                return False, "Слишком маленькая покупка.", {}
            new_price = new_res_ton / new_res_tok
            new_mcap = new_price * total_supply
            new_user_tons = round(max(0.0, cur_tons - ton_in), 6)

            conn.execute("UPDATE users SET balance_tons=? WHERE user_id=?", (new_user_tons, user_id))
            conn.execute(
                "INSERT INTO memecoin_holdings (user_id, coin_id, amount, avg_buy_price_ton) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(user_id, coin_id) DO UPDATE SET amount = memecoin_holdings.amount + excluded.amount",
                (user_id, coin_id, tokens_out, new_price),
            )
            ton_vol = ton_in
            tok_delta = tokens_out
        elif side == "sell":
            tokens_in = float(amount)
            h = conn.execute("SELECT amount FROM memecoin_holdings WHERE user_id=? AND coin_id=?", (user_id, coin_id)).fetchone()
            owned = float(h["amount"] or 0.0) if h else 0.0
            if tokens_in <= 0 or owned + 1e-6 < tokens_in:
                conn.rollback()
                return False, "Недостаточно токенов для продажи.", {}
            tokens_in = min(tokens_in, owned)
            new_res_tok = res_tok + tokens_in
            new_res_ton = k_const / new_res_tok
            gross_ton_out = max(0.0, res_ton - new_res_ton)
            ton_out = round(gross_ton_out * 0.99, 6)
            if ton_out <= 0:
                conn.rollback()
                return False, "Слишком маленькое количество для продажи.", {}
            new_price = new_res_ton / new_res_tok
            new_mcap = new_price * total_supply
            new_user_tons = round(cur_tons + ton_out, 6)
            rem_tokens = max(0.0, owned - tokens_in)

            conn.execute("UPDATE users SET balance_tons=? WHERE user_id=?", (new_user_tons, user_id))
            conn.execute("UPDATE memecoin_holdings SET amount=? WHERE user_id=? AND coin_id=?", (rem_tokens, user_id, coin_id))
            ton_vol = ton_out
            tok_delta = tokens_in
        else:
            conn.rollback()
            return False, "Неизвестная операция.", {}

        holders_cnt = int(
            conn.execute("SELECT COUNT(*) AS c FROM memecoin_holdings WHERE coin_id=? AND amount > 0.0001", (coin_id,)).fetchone()["c"] or 0
        )
        conn.execute(
            "UPDATE memecoins SET reserve_ton=?, reserve_token=?, price_ton=?, market_cap_ton=?, volume_24h_ton=volume_24h_ton+?, holders_count=? WHERE id=?",
            (new_res_ton, new_res_tok, new_price, new_mcap, ton_vol, max(1, holders_cnt), coin_id),
        )
        prev_candle = conn.execute(
            "SELECT * FROM memecoin_candles WHERE coin_id=? AND bucket_ts=?",
            (coin_id, bucket_ts),
        ).fetchone()
        if prev_candle:
            conn.execute(
                "UPDATE memecoin_candles SET high_ton=?, low_ton=?, close_ton=?, volume_ton=volume_ton+? WHERE id=?",
                (
                    max(float(prev_candle["high_ton"]), new_price),
                    min(float(prev_candle["low_ton"]), new_price),
                    new_price,
                    ton_vol,
                    int(prev_candle["id"]),
                ),
            )
        else:
            last_c = conn.execute(
                "SELECT close_ton FROM memecoin_candles WHERE coin_id=? ORDER BY bucket_ts DESC LIMIT 1",
                (coin_id,),
            ).fetchone()
            open_p = float(last_c["close_ton"]) if last_c else float(coin["price_ton"])
            conn.execute(
                "INSERT INTO memecoin_candles (coin_id, bucket_ts, open_ton, high_ton, low_ton, close_ton, volume_ton) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (coin_id, bucket_ts, open_p, max(open_p, new_price), min(open_p, new_price), new_price, ton_vol),
            )
        conn.execute(
            "INSERT INTO memecoin_trades (coin_id, user_id, side, ton_amount, token_amount, price_ton, created_ts) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (coin_id, user_id, side, ton_vol, tok_delta, new_price, now_ts),
        )
        conn.commit()
        detail = get_memecoin_detail_db(coin_id, user_id=user_id)
        return True, "OK", {"balance_tons": new_user_tons, **(detail or {})}
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


class _RocketEngine:
    def __init__(self) -> None:
        self.phase: str = "betting"
        self.round_id: int = 0
        self.countdown_sec: float = 10.0
        self.multiplier: float = 1.00
        self.crash_point: float = 2.00
        self.started_ts: float = time.time()
        self.bets: Dict[int, dict] = {}
        self.history: List[dict] = []
        self._lock = asyncio.Lock()

    def _roll_crash_point(self) -> float:
        r = random.random()
        if r < 0.08:
            return 1.00
        val = 0.92 / max(1e-6, 1.0 - r)
        return round(min(100.0, max(1.01, val)), 2)

    def public_state(self) -> dict:
        return {
            "phase": self.phase,
            "round_id": self.round_id,
            "countdown_sec": round(max(0.0, self.countdown_sec), 1),
            "multiplier": round(self.multiplier, 2),
            "crash_point": round(self.crash_point, 2) if self.phase == "crashed" else None,
            "bets": [
                {
                    "user_id": b["user_id"],
                    "name": b["name"],
                    "avatar_url": b["avatar_url"],
                    "stake_type": b["stake_type"],
                    "stake_stars": b["stake_stars"],
                    "item_name": b.get("item_name"),
                    "item_image_url": b.get("item_image_url"),
                    "target_gift_title": b.get("target_gift_title"),
                    "target_mult": b.get("target_mult"),
                    "auto_cashout": b.get("auto_cashout"),
                    "status": b["status"],
                    "cashout_mult": b.get("cashout_mult"),
                    "payout_stars": b.get("payout_stars"),
                }
                for b in self.bets.values()
            ],
            "history": self.history[:16],
        }

    async def broadcast(self, event_type: str = "rocket_state") -> None:
        if not _WS_CLIENTS:
            return
        payload = json.dumps({"type": event_type, "data": self.public_state()}, ensure_ascii=False)
        dead = []
        for ws in list(_WS_CLIENTS):
            try:
                await ws.send_str(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _WS_CLIENTS.discard(ws)

    async def place_bet(
        self,
        user_id: int,
        stake_type: str,
        stake_stars: int = 0,
        collection_item_id: int = 0,
        target_gift_key: str = "pepe_heart",
        target_model_name: Optional[str] = None,
        target_backdrop_key: Optional[str] = None,
        auto_cashout: Optional[float] = None,
    ) -> Tuple[bool, str, dict]:
        async with self._lock:
            if self.phase != "betting":
                return False, "Приём ставок закрыт, дождитесь следующего раунда.", {}
            if user_id in self.bets:
                return False, "Вы уже сделали ставку в этом раунде.", {}

            conn = db_connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                u = conn.execute("SELECT user_id, username, first_name, balance_stars FROM users WHERE user_id=?", (user_id,)).fetchone()
                if not u:
                    conn.rollback()
                    return False, "Пользователь не найден.", {}
                display_name = u["first_name"] or u["username"] or f"ID {user_id}"

                if stake_type == "stars":
                    amt = int(stake_stars or 0)
                    if amt < 50:
                        conn.rollback()
                        return False, "Минимальная ставка — 50 ⭐.", {}
                    if int(u["balance_stars"] or 0) < amt:
                        conn.rollback()
                        return False, "Недостаточно Stars на балансе.", {}
                    conn.execute("UPDATE users SET balance_stars=balance_stars-? WHERE user_id=?", (amt, user_id))
                    record_star_flow(spent=amt, conn=conn)
                    conn.commit()
                    ac = round(float(auto_cashout), 2) if auto_cashout and float(auto_cashout) >= 1.1 else None
                    self.bets[user_id] = {
                        "user_id": user_id,
                        "name": display_name,
                        "avatar_url": f"/api/assets/avatar/{user_id}",
                        "stake_type": "stars",
                        "stake_stars": amt,
                        "auto_cashout": ac,
                        "status": "active",
                        "cashout_mult": None,
                        "payout_stars": 0,
                    }
                elif stake_type == "nft":
                    item = conn.execute("SELECT * FROM collection WHERE id=? AND user_id=?", (collection_item_id, user_id)).fetchone()
                    if not item:
                        conn.rollback()
                        return False, "NFT не найден в коллекции.", {}
                    if int(item["is_listed"] or 0) != 0:
                        conn.rollback()
                        return False, "Этот NFT уже занят.", {}
                    canon_target = canonical_gift_key(target_gift_key)
                    if canon_target not in UPGRADABLE_GIFT_KEYS:
                        conn.rollback()
                        return False, "Выберите доступную цель апгрейда.", {}
                    source_val = get_item_display_value(item)
                    _, _, b_val = get_item_buffs(item)
                    mdef, bdef, target_stars, _ = compute_upgrader_target_and_chance(
                        source_val, canon_target, target_model_name, target_backdrop_key, b_val
                    )
                    req_mult = max(1.35, round((target_stars / max(1, source_val)) * ROCKET_UPGRADE_MULT_PENALTY, 2))
                    conn.execute("UPDATE collection SET is_listed=2 WHERE id=?", (collection_item_id,))
                    conn.commit()
                    img_u, _ = _item_image_urls(item)
                    sg = GIFTS_BY_KEY.get(canonical_gift_key(item["gift_key"]))
                    self.bets[user_id] = {
                        "user_id": user_id,
                        "name": display_name,
                        "avatar_url": f"/api/assets/avatar/{user_id}",
                        "stake_type": "nft",
                        "stake_stars": source_val,
                        "collection_item_id": int(collection_item_id),
                        "item_name": sg.name if sg else item["gift_key"],
                        "item_image_url": img_u,
                        "target_gift_key": canon_target,
                        "target_gift_title": get_upgraded_gift_title(canon_target),
                        "target_model_name": mdef.name,
                        "target_backdrop_key": bdef.key,
                        "target_stars": int(target_stars),
                        "target_mult": req_mult,
                        "auto_cashout": req_mult,
                        "status": "active",
                        "cashout_mult": None,
                        "payout_stars": 0,
                    }
                else:
                    conn.rollback()
                    return False, "Неизвестный тип ставки.", {}
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise
            finally:
                conn.close()

        await self.broadcast("rocket_state")
        return True, "OK", self.public_state()

    def _settle_cashout_sync(self, bet: dict, mult: float) -> dict:
        conn = db_connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if bet["stake_type"] == "stars":
                payout = int(round(bet["stake_stars"] * mult))
                conn.execute("UPDATE users SET balance_stars=balance_stars+?, xp=xp+350 WHERE user_id=?", (payout, bet["user_id"]))
                record_star_flow(issued=payout, conn=conn)
                conn.commit()
                bet["status"] = "won"
                bet["cashout_mult"] = round(mult, 2)
                bet["payout_stars"] = payout
                return {"won": True, "payout_stars": payout, "upgraded": False}
            else:
                item_id = int(bet["collection_item_id"])
                if mult >= float(bet["target_mult"]):
                    mx = conn.execute("SELECT COALESCE(MAX(upgrade_num), 0) AS mx FROM collection").fetchone()
                    next_num = int(mx["mx"] or 0) + 1
                    conn.execute(
                        "UPDATE collection SET gift_key=?, is_upgraded=1, model_name=?, backdrop_key=?, upgraded_stars=?, upgrade_num=?, is_listed=0 WHERE id=?",
                        (
                            bet["target_gift_key"],
                            bet["target_model_name"],
                            bet["target_backdrop_key"],
                            int(bet["target_stars"]),
                            next_num,
                            item_id,
                        ),
                    )
                    conn.execute("UPDATE users SET xp=xp+3500 WHERE user_id=?", (bet["user_id"],))
                    conn.commit()
                    bet["status"] = "won"
                    bet["cashout_mult"] = round(mult, 2)
                    bet["payout_stars"] = int(bet["target_stars"])
                    return {"won": True, "payout_stars": int(bet["target_stars"]), "upgraded": True}
                else:
                    conn.execute("UPDATE collection SET is_listed=0 WHERE id=?", (item_id,))
                    conn.commit()
                    bet["status"] = "won"
                    bet["cashout_mult"] = round(mult, 2)
                    bet["payout_stars"] = int(bet["stake_stars"])
                    return {"won": True, "payout_stars": int(bet["stake_stars"]), "upgraded": False}
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            conn.close()

    async def cashout(self, user_id: int) -> Tuple[bool, str, dict]:
        async with self._lock:
            if self.phase != "flying":
                return False, "Раунд сейчас не в полёте.", {}
            bet = self.bets.get(user_id)
            if not bet or bet["status"] != "active":
                return False, "У вас нет активной ставки в этом раунде.", {}
            if bet["stake_type"] == "nft" and self.multiplier < 1.30:
                return False, "NFT можно забрать начиная с x1.30.", {}
            res = self._settle_cashout_sync(bet, self.multiplier)
        await self.broadcast("rocket_state")
        return True, "OK", res

    def _finalize_crash_sync(self) -> None:
        conn = db_connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for bet in self.bets.values():
                if bet["status"] == "active":
                    bet["status"] = "lost"
                    if bet["stake_type"] == "nft":
                        conn.execute("DELETE FROM collection WHERE id=? AND user_id=?", (int(bet["collection_item_id"]), bet["user_id"]))
            conn.execute(
                "UPDATE rocket_rounds SET status='crashed', crashed_ts=? WHERE id=?",
                (int(time.time()), self.round_id),
            )
            conn.commit()
        finally:
            conn.close()

    def refund_all_active_sync(self) -> None:
        conn = db_connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for bet in self.bets.values():
                if bet["status"] == "active":
                    if bet["stake_type"] == "stars":
                        conn.execute("UPDATE users SET balance_stars=balance_stars+? WHERE user_id=?", (int(bet["stake_stars"]), bet["user_id"]))
                    elif bet["stake_type"] == "nft":
                        conn.execute("UPDATE collection SET is_listed=0 WHERE id=?", (int(bet["collection_item_id"]),))
                    bet["status"] = "refunded"
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()


_ROCKET = _RocketEngine()


async def _rocket_engine_loop() -> None:
    try:
        while True:
            conn = db_connect()
            try:
                cur = conn.execute(
                    "INSERT INTO rocket_rounds (crash_point, status, created_ts) VALUES (1.0, 'betting', ?)",
                    (int(time.time()),),
                )
                round_id = int(cur.lastrowid)
                conn.commit()
            finally:
                conn.close()

            async with _ROCKET._lock:
                _ROCKET.phase = "betting"
                _ROCKET.round_id = round_id
                _ROCKET.countdown_sec = 9.0
                _ROCKET.multiplier = 1.00
                _ROCKET.crash_point = _ROCKET._roll_crash_point()
                _ROCKET.bets = {}

            for step in range(90):
                await _ROCKET.broadcast("rocket_state")
                await asyncio.sleep(0.1)
                async with _ROCKET._lock:
                    _ROCKET.countdown_sec = max(0.0, 9.0 - (step + 1) * 0.1)

            async with _ROCKET._lock:
                _ROCKET.phase = "flying"
                _ROCKET.started_ts = time.time()
                _ROCKET.multiplier = 1.00
            await _ROCKET.broadcast("rocket_state")

            while True:
                await asyncio.sleep(0.1)
                crashed_now = False
                state_changed = False
                async with _ROCKET._lock:
                    elapsed = max(0.0, time.time() - _ROCKET.started_ts)
                    next_mult = round(math.exp(0.075 * elapsed), 2)
                    if next_mult >= _ROCKET.crash_point:
                        _ROCKET.multiplier = _ROCKET.crash_point
                        _ROCKET.phase = "crashed"
                        _ROCKET._finalize_crash_sync()
                        _ROCKET.history.insert(0, {"round_id": _ROCKET.round_id, "crash_point": _ROCKET.crash_point})
                        _ROCKET.history = _ROCKET.history[:20]
                        crashed_now = True
                    else:
                        _ROCKET.multiplier = next_mult
                        for bet in _ROCKET.bets.values():
                            if bet["status"] == "active" and bet.get("auto_cashout") and next_mult >= float(bet["auto_cashout"]):
                                _ROCKET._settle_cashout_sync(bet, float(bet["auto_cashout"]))
                                state_changed = True
                if crashed_now:
                    await _ROCKET.broadcast("rocket_state")
                    break
                await _ROCKET.broadcast("rocket_state" if state_changed else "rocket_tick")

            await asyncio.sleep(3.8)
    except asyncio.CancelledError:
        _ROCKET.refund_all_active_sync()
        raise


def _cors_headers(request) -> dict:
    origin = request.headers.get("Origin", "*")
    return {
        "Access-Control-Allow-Origin": origin or "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-Telegram-Init-Data, X-Dev-User-Id",
        "Vary": "Origin",
    }


async def _auth_user_from_request(request) -> Optional[sqlite3.Row]:
    raw_init = request.headers.get("X-Telegram-Init-Data") or request.query.get("initData") or ""
    tg_user = verify_telegram_init_data(raw_init)
    if tg_user:
        uid = int(tg_user["id"])
        touch_user_activity(uid)
        return get_or_create_user(uid, tg_user.get("username") or "", tg_user.get("first_name") or "")
    if os.environ.get("ALLOW_INSECURE_DEV_AUTH") == "1":
        dev_uid = request.headers.get("X-Dev-User-Id") or request.query.get("devUserId")
        if dev_uid and str(dev_uid).isdigit():
            uid = int(dev_uid)
            touch_user_activity(uid)
            return get_or_create_user(uid, f"dev_{uid}", f"Player {uid}")
    return None


def _json_response(request, data: dict, status: int = 200):
    return aiohttp_web.json_response(data, status=status, headers=_cors_headers(request))


async def _handle_options(request):
    return aiohttp_web.Response(status=204, headers=_cors_headers(request))


async def _api_health(request):
    return _json_response(request, {"ok": True, "service": "new-nft-miniapp", "port": MINI_APP_PORT})


async def _api_me(request):
    u = await _auth_user_from_request(request)
    if not u:
        return _json_response(request, {"ok": False, "error": "Требуется авторизация Telegram Mini App."}, status=401)
    items = [serialize_collection_item(r) for r in get_user_collection(int(u["user_id"]))]
    return _json_response(request, {
        "ok": True,
        "user": serialize_user_profile(u),
        "collection": items,
        "catalog": get_mini_app_catalog(),
    })


async def _api_upgrade(request):
    u = await _auth_user_from_request(request)
    if not u:
        return _json_response(request, {"ok": False, "error": "Unauthorized"}, status=401)
    body = await request.json()
    ok, msg, res = miniapp_upgrade_item_db(
        int(u["user_id"]),
        int(body.get("source_item_id") or 0),
        str(body.get("target_gift_key") or "pepe_heart"),
        body.get("target_model_name"),
        body.get("target_backdrop_key"),
    )
    if not ok:
        return _json_response(request, {"ok": False, "error": msg}, status=400)
    fresh_u = get_or_create_user(int(u["user_id"]), "", "")
    items = [serialize_collection_item(r) for r in get_user_collection(int(u["user_id"]))]
    return _json_response(request, {"ok": True, **res, "user": serialize_user_profile(fresh_u), "collection": items})


async def _api_exchange_swap(request):
    u = await _auth_user_from_request(request)
    if not u:
        return _json_response(request, {"ok": False, "error": "Unauthorized"}, status=401)
    body = await request.json()
    ok, msg, res = swap_stars_ton_db(
        int(u["user_id"]),
        str(body.get("direction") or "stars_to_ton"),
        float(body.get("amount") or 0),
    )
    if not ok:
        return _json_response(request, {"ok": False, "error": msg}, status=400)
    return _json_response(request, {"ok": True, **res})


async def _api_coins_list(request):
    u = await _auth_user_from_request(request)
    uid = int(u["user_id"]) if u else 0
    return _json_response(request, {"ok": True, "coins": list_memecoins_db(uid)})


async def _api_coin_detail(request):
    u = await _auth_user_from_request(request)
    uid = int(u["user_id"]) if u else 0
    coin_id = int(request.match_info["id"])
    detail = get_memecoin_detail_db(coin_id, uid)
    if not detail:
        return _json_response(request, {"ok": False, "error": "Монета не найдена."}, status=404)
    return _json_response(request, {"ok": True, **detail})


async def _api_coins_create(request):
    u = await _auth_user_from_request(request)
    if not u:
        return _json_response(request, {"ok": False, "error": "Unauthorized"}, status=401)
    body = await request.json()
    ok, msg, res = create_memecoin_db(
        int(u["user_id"]),
        str(body.get("name") or ""),
        str(body.get("ticker") or ""),
        str(body.get("image_b64") or ""),
    )
    if not ok:
        return _json_response(request, {"ok": False, "error": msg}, status=400)
    return _json_response(request, {"ok": True, **res})


async def _api_coin_trade(request):
    u = await _auth_user_from_request(request)
    if not u:
        return _json_response(request, {"ok": False, "error": "Unauthorized"}, status=401)
    coin_id = int(request.match_info["id"])
    body = await request.json()
    ok, msg, res = trade_memecoin_db(
        int(u["user_id"]),
        coin_id,
        str(body.get("side") or ""),
        float(body.get("amount") or 0),
    )
    if not ok:
        return _json_response(request, {"ok": False, "error": msg}, status=400)
    if _WS_CLIENTS and res.get("coin"):
        msg_ws = json.dumps({"type": "coin_update", "data": res["coin"]}, ensure_ascii=False)
        for ws in list(_WS_CLIENTS):
            try:
                await ws.send_str(msg_ws)
            except Exception:
                _WS_CLIENTS.discard(ws)
    return _json_response(request, {"ok": True, **res})


async def _api_rocket_state(request):
    return _json_response(request, {"ok": True, "rocket": _ROCKET.public_state()})


async def _api_rocket_bet(request):
    u = await _auth_user_from_request(request)
    if not u:
        return _json_response(request, {"ok": False, "error": "Unauthorized"}, status=401)
    body = await request.json()
    ok, msg, st = await _ROCKET.place_bet(
        int(u["user_id"]),
        stake_type=str(body.get("stake_type") or "stars"),
        stake_stars=int(body.get("stake_stars") or 0),
        collection_item_id=int(body.get("collection_item_id") or 0),
        target_gift_key=str(body.get("target_gift_key") or "pepe_heart"),
        target_model_name=body.get("target_model_name"),
        target_backdrop_key=body.get("target_backdrop_key"),
        auto_cashout=body.get("auto_cashout"),
    )
    if not ok:
        return _json_response(request, {"ok": False, "error": msg}, status=400)
    fresh_u = get_or_create_user(int(u["user_id"]), "", "")
    items = [serialize_collection_item(r) for r in get_user_collection(int(u["user_id"]))]
    return _json_response(request, {"ok": True, "rocket": st, "user": serialize_user_profile(fresh_u), "collection": items})


async def _api_rocket_cashout(request):
    u = await _auth_user_from_request(request)
    if not u:
        return _json_response(request, {"ok": False, "error": "Unauthorized"}, status=401)
    ok, msg, res = await _ROCKET.cashout(int(u["user_id"]))
    if not ok:
        return _json_response(request, {"ok": False, "error": msg}, status=400)
    fresh_u = get_or_create_user(int(u["user_id"]), "", "")
    items = [serialize_collection_item(r) for r in get_user_collection(int(u["user_id"]))]
    return _json_response(request, {"ok": True, **res, "rocket": _ROCKET.public_state(), "user": serialize_user_profile(fresh_u), "collection": items})


async def _api_asset_gift(request):
    key = canonical_gift_key(request.match_info["key"])
    p = gift_image_path(key)
    if not p or not p.exists():
        return aiohttp_web.Response(status=404, headers=_cors_headers(request))
    return aiohttp_web.FileResponse(p, headers=_cors_headers(request))


async def _api_asset_model(request):
    gift_key = canonical_gift_key(request.match_info["gift_key"])
    filename = Path(urllib.parse.unquote(request.match_info["filename"])).name
    p = gift_model_image_path(gift_key, filename)
    if not p or not p.exists():
        p = gift_image_path(gift_key)
    if not p or not p.exists():
        return aiohttp_web.Response(status=404, headers=_cors_headers(request))
    return aiohttp_web.FileResponse(p, headers=_cors_headers(request))


async def _api_asset_avatar(request):
    uid_raw = request.match_info["user_id"]
    if not uid_raw.isdigit():
        return aiohttp_web.Response(status=404, headers=_cors_headers(request))
    uid = int(uid_raw)
    cache_path = AVATARS_CACHE_DIR / f"{uid}.jpg"
    if (not cache_path.exists() or (time.time() - cache_path.stat().st_mtime > 3600)) and _BOT_APP_REF is not None:
        try:
            photos = await _BOT_APP_REF.bot.get_user_profile_photos(uid, limit=1)
            if photos and photos.photos:
                tg_file = await _BOT_APP_REF.bot.get_file(photos.photos[0][-1].file_id)
                buf = io.BytesIO()
                await tg_file.download_to_memory(out=buf)
                cache_path.write_bytes(buf.getvalue())
        except Exception:
            pass
    if cache_path.exists():
        return aiohttp_web.FileResponse(cache_path, headers=_cors_headers(request))
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128">'
        f'<rect width="128" height="128" rx="64" fill="#1C1C1E"/>'
        f'<text x="64" y="76" font-family="sans-serif" font-size="44" font-weight="700" fill="#F5F5F7" text-anchor="middle">{str(uid)[-2:]}</text>'
        f'</svg>'
    )
    return aiohttp_web.Response(text=svg, content_type="image/svg+xml", headers=_cors_headers(request))


async def _ws_handler(request):
    ws = aiohttp_web.WebSocketResponse(heartbeat=25.0)
    await ws.prepare(request)
    _WS_CLIENTS.add(ws)
    try:
        await ws.send_str(json.dumps({"type": "rocket_state", "data": _ROCKET.public_state()}, ensure_ascii=False))
        async for msg in ws:
            if msg.type == WSMsgType.TEXT and msg.data == "ping":
                await ws.send_str("pong")
            elif msg.type == WSMsgType.ERROR:
                break
    finally:
        _WS_CLIENTS.discard(ws)
    return ws


def build_miniapp_web_app():
    web_app = aiohttp_web.Application(client_max_size=2 * 1024 * 1024)
    web_app.router.add_route("OPTIONS", "/{tail:.*}", _handle_options)
    web_app.router.add_get("/api/health", _api_health)
    web_app.router.add_get("/api/me", _api_me)
    web_app.router.add_post("/api/upgrade", _api_upgrade)
    web_app.router.add_post("/api/exchange/swap", _api_exchange_swap)
    web_app.router.add_get("/api/coins", _api_coins_list)
    web_app.router.add_post("/api/coins/create", _api_coins_create)
    web_app.router.add_get(r"/api/coins/{id:\d+}", _api_coin_detail)
    web_app.router.add_post(r"/api/coins/{id:\d+}/trade", _api_coin_trade)
    web_app.router.add_get("/api/rocket/state", _api_rocket_state)
    web_app.router.add_post("/api/rocket/bet", _api_rocket_bet)
    web_app.router.add_post("/api/rocket/cashout", _api_rocket_cashout)
    web_app.router.add_get("/api/assets/gift/{key}", _api_asset_gift)
    web_app.router.add_get("/api/assets/model/{gift_key}/{filename}", _api_asset_model)
    web_app.router.add_get("/api/assets/avatar/{user_id}", _api_asset_avatar)
    web_app.router.add_get("/ws", _ws_handler)
    return web_app


async def start_miniapp_server(app: Optional[Application] = None) -> None:
    global _MINIAPP_RUNNER, _MINIAPP_SITE, _ROCKET_TASK, _BOT_APP_REF
    _BOT_APP_REF = app
    if not AIOHTTP_AVAILABLE:
        log.warning("aiohttp не установлен — Mini App сервер на порту %s не запущен.", MINI_APP_PORT)
        return
    web_app = build_miniapp_web_app()
    _MINIAPP_RUNNER = aiohttp_web.AppRunner(web_app)
    await _MINIAPP_RUNNER.setup()
    _MINIAPP_SITE = aiohttp_web.TCPSite(_MINIAPP_RUNNER, MINI_APP_HOST, MINI_APP_PORT)
    await _MINIAPP_SITE.start()
    _ROCKET_TASK = asyncio.create_task(_rocket_engine_loop())
    log.info("Mini App HTTP + WebSocket сервер запущен на http://%s:%s", MINI_APP_HOST, MINI_APP_PORT)


async def stop_miniapp_server() -> None:
    global _MINIAPP_RUNNER, _MINIAPP_SITE, _ROCKET_TASK
    if _ROCKET_TASK and not _ROCKET_TASK.done():
        _ROCKET_TASK.cancel()
        try:
            await _ROCKET_TASK
        except Exception:
            pass
    _ROCKET.refund_all_active_sync()
    for ws in list(_WS_CLIENTS):
        try:
            await ws.close()
        except Exception:
            pass
    _WS_CLIENTS.clear()
    if _MINIAPP_RUNNER is not None:
        try:
            await _MINIAPP_RUNNER.cleanup()
        except Exception:
            pass
        _MINIAPP_RUNNER = None
        _MINIAPP_SITE = None


async def on_app_post_init(app: Application) -> None:
    global _GIVEAWAY_SCHEDULER_TASK, _SCARED_CAT_PROMO_TASK
    _GIVEAWAY_SCHEDULER_TASK = asyncio.create_task(_giveaway_scheduler_loop(app))
    log.info("Фоновый планировщик конкурсов запущен.")
    _SCARED_CAT_PROMO_TASK = asyncio.create_task(_scared_cat_promo_broadcast_loop(app))
    log.info("Фоновая промо-рассылка Scared Cat (старт + каждые 3 часа) запущена.")
    await start_miniapp_server(app)
    try:
        for stalled_bid in get_stalled_battles_db():
            _ensure_battle_task(app.bot, stalled_bid)
    except Exception as e:
        log.error("Ошибка восстановления незавершённых баттлов: %s", e)

async def on_app_post_shutdown(app: Application) -> None:
    global _GIVEAWAY_SCHEDULER_TASK, _SCARED_CAT_PROMO_TASK
    await stop_miniapp_server()
    if _GIVEAWAY_SCHEDULER_TASK and not _GIVEAWAY_SCHEDULER_TASK.done():
        _GIVEAWAY_SCHEDULER_TASK.cancel()
        try:
            await _GIVEAWAY_SCHEDULER_TASK
        except Exception:
            pass
    if _SCARED_CAT_PROMO_TASK and not _SCARED_CAT_PROMO_TASK.done():
        _SCARED_CAT_PROMO_TASK.cancel()
        try:
            await _SCARED_CAT_PROMO_TASK
        except Exception:
            pass
    if _ADMIN_BROADCAST_TASK and not _ADMIN_BROADCAST_TASK.done():
        _ADMIN_BROADCAST_TASK.cancel()
        try:
            await _ADMIN_BROADCAST_TASK
        except Exception:
            pass
    for b_task in list(_ACTIVE_BATTLE_TASKS.values()):
        if not b_task.done():
            b_task.cancel()
            try:
                await b_task
            except Exception:
                pass

# ---------------------------------------------------------------------------
# ТОЧКА ВХОДА (MAIN)
# ---------------------------------------------------------------------------

def main() -> None:
    db_restored = False
    try:
        db_restored = firebase_manager.download_db_on_startup()
    except Exception as e:
        log.error(f"[Firebase] Ошибка скачивания базы при старте: {e}")

    db_init()

    if not db_restored and firebase_manager._cloud_doc_missing and not firebase_manager._startup_download_error:
        try:
            firebase_manager.upload_db_to_cloud(force=True)
        except Exception as e:
            log.error(f"[Firebase] Ошибка первой выгрузки базы в облако: {e}")
    elif not db_restored and firebase_manager._startup_download_error:
        log.warning("🛡️ [Anti-Wipe] Стартовое скачивание завершилось с ошибкой — пустая база НЕ будет затирать облачный документ.")

    firebase_manager.start_periodic_sync(interval_seconds=60)

    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .post_init(on_app_post_init)
        .post_shutdown(on_app_post_shutdown)
        .build()
    )

    clan_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_clan_creation, pattern="^clan_create_start$"),
            CommandHandler("create_clan", start_clan_creation),
        ],
        states={
            WAIT_CLAN_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, clan_tag_received)],
            WAIT_CLAN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, clan_name_received)],
            WAIT_CLAN_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, clan_desc_received)],
            WAIT_CLAN_TYPE: [CallbackQueryHandler(clan_type_selected, pattern="^ctype:")],
            WAIT_CLAN_FEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, clan_fee_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_clan_creation)],
        per_message=False,
        allow_reentry=True
    )

    admin_give_stars_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_give_stars_start, pattern="^admin_give_stars_start$")],
        states={
            WAIT_ADMIN_GIVE_STARS_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_give_stars_user)],
            WAIT_ADMIN_GIVE_STARS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_give_stars_amount)],
        },
        fallbacks=[
            CommandHandler("cancel", admin_cancel),
            CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$")
        ],
        per_message=False,
        allow_reentry=True
    )

    admin_give_nft_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_give_nft_start, pattern="^admin_give_nft_start$")],
        states={
            WAIT_ADMIN_GIVE_NFT_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_give_nft_user)],
        },
        fallbacks=[
            CommandHandler("cancel", admin_cancel),
            CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$")
        ],
        per_message=False,
        allow_reentry=True
    )

    bg_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(bg_change_start, pattern="^bg_change_start$")],
        states={
            WAIT_PROFILE_BG: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, bg_photo_received),
                CallbackQueryHandler(bg_cancel, pattern="^bg_cancel$")
            ],
        },
        fallbacks=[CommandHandler("cancel", bg_cancel)],
        per_message=False,
        allow_reentry=True
    )

    admin_ban_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_ban_start, pattern="^admin_ban_start$")],
        states={
            WAIT_ADMIN_BAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ban_user_received)],
            WAIT_ADMIN_BAN_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ban_hours_received)],
            WAIT_ADMIN_BAN_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ban_reason_received)],
        },
        fallbacks=[
            CommandHandler("cancel", admin_cancel),
            CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$")
        ],
        per_message=False,
        allow_reentry=True
    )

    admin_unban_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_unban_start, pattern="^admin_unban_start$")],
        states={
            WAIT_ADMIN_UNBAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_unban_user_received)],
        },
        fallbacks=[
            CommandHandler("cancel", admin_cancel),
            CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$")
        ],
        per_message=False,
        allow_reentry=True
    )

    clan_avatar_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(clan_avatar_start, pattern="^clan_avatar_start:")],
        states={
            WAIT_CLAN_AVATAR: [
                MessageHandler(filters.PHOTO, clan_avatar_photo_received),
                CallbackQueryHandler(clan_avatar_cancel, pattern="^clan_avatar_cancel$")
            ]
        },
        fallbacks=[CommandHandler("cancel", clan_avatar_cancel)],
        per_message=False,
        allow_reentry=True
    )

    clan_donate_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(clan_donate_stars_start, pattern="^clan_donate_stars_start:")],
        states={
            WAIT_CLAN_DONATE_STARS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, clan_donate_stars_amount),
                CallbackQueryHandler(clan_donate_cancel, pattern="^clan_donate_cancel$")
            ]
        },
        fallbacks=[CommandHandler("cancel", clan_donate_cancel)],
        per_message=False,
        allow_reentry=True
    )

    admin_firebase_key_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_firebase_upload_key_start, pattern="^admin_firebase_upload_key$")],
        states={
            WAIT_ADMIN_FIREBASE_JSON: [
                MessageHandler(filters.Document.ALL, admin_firebase_json_received),
                CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", admin_cancel),
            CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$")
        ],
        per_message=False,
        allow_reentry=True
    )

    market_offer_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(market_sell_start, pattern="^market_sell_start:")],
        states={
            WAIT_MARKET_OFFER_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, market_sell_price_received),
                CallbackQueryHandler(market_sell_cancel, pattern="^market_sell_cancel$"),
            ]
        },
        fallbacks=[
            CommandHandler("cancel", market_sell_cancel),
            CallbackQueryHandler(market_sell_cancel, pattern="^market_sell_cancel$"),
        ],
        per_message=False,
        allow_reentry=True,
    )

    gift_transfer_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(gift_transfer_start, pattern="^gift_transfer_start:"),
            CallbackQueryHandler(gift_transfer_start, pattern="^chat_gx_pick:"),
        ],
        states={
            WAIT_GIFT_TRANSFER_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, gift_transfer_user_received),
                CallbackQueryHandler(gift_transfer_cancel, pattern="^gift_transfer_cancel$"),
            ]
        },
        fallbacks=[
            CommandHandler("cancel", gift_transfer_cancel),
            CallbackQueryHandler(gift_transfer_cancel, pattern="^gift_transfer_cancel$"),
        ],
        per_message=False,
        allow_reentry=True,
    )

    checks_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(check_create_start, pattern="^check_create_start$")],
        states={
            WAIT_CHECK_TARGET: [
                CallbackQueryHandler(check_target_anyone_selected, pattern="^check_target_anyone$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_target_received),
                CallbackQueryHandler(check_create_cancel, pattern="^check_create_cancel$"),
            ],
            WAIT_CHECK_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_amount_received),
                CallbackQueryHandler(check_create_cancel, pattern="^check_create_cancel$"),
            ],
            WAIT_CHECK_PASSWORD: [
                CallbackQueryHandler(check_skip_password_pressed, pattern="^check_skip_password$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_password_received),
                CallbackQueryHandler(check_create_cancel, pattern="^check_create_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", check_create_cancel),
            CallbackQueryHandler(check_create_cancel, pattern="^check_create_cancel$"),
        ],
        per_message=False,
        allow_reentry=True,
    )

    check_pwd_claim_conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            CallbackQueryHandler(claim_check_pwd_entry, pattern="^claim_check_pwd:"),
        ],
        states={
            WAIT_CHECK_CLAIM_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_claim_password_received),
                CallbackQueryHandler(check_pwd_claim_cancel, pattern="^check_pwd_claim_cancel$"),
            ]
        },
        fallbacks=[
            CommandHandler("cancel", check_pwd_claim_cancel),
            CallbackQueryHandler(check_pwd_claim_cancel, pattern="^check_pwd_claim_cancel$"),
        ],
        per_message=False,
        allow_reentry=True,
    )

    author_apply_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(author_apply_start, pattern="^author_apply_start$")],
        states={
            WAIT_AUTHOR_APP_CHANNELS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, author_apply_channels_received),
                CallbackQueryHandler(author_apply_cancel, pattern="^author_apply_cancel$"),
            ],
            WAIT_AUTHOR_APP_AGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, author_apply_age_received),
                CallbackQueryHandler(author_apply_cancel, pattern="^author_apply_cancel$"),
            ],
            WAIT_AUTHOR_APP_CONFIRM: [
                CallbackQueryHandler(author_apply_submit, pattern="^author_apply_submit$"),
                CallbackQueryHandler(author_apply_cancel, pattern="^author_apply_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", author_apply_cancel),
            CallbackQueryHandler(author_apply_cancel, pattern="^author_apply_cancel$"),
        ],
        per_message=False,
        allow_reentry=True,
    )

    admin_reject_app_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_app_reject_start, pattern="^admin_app_reject_start:")],
        states={
            WAIT_ADMIN_APP_REJECT_REASON: [
                CallbackQueryHandler(admin_app_reject_nomsg, pattern="^admin_app_reject_nomsg$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_app_reject_reason_received),
                CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
            ]
        },
        fallbacks=[
            CommandHandler("cancel", admin_cancel),
            CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
        ],
        per_message=False,
        allow_reentry=True,
    )

    admin_give_auth_stars_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_give_author_stars_start, pattern="^admin_give_author_stars_start$")],
        states={
            WAIT_ADMIN_GIVE_AUTH_STARS_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_give_author_stars_user),
                CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
            ],
            WAIT_ADMIN_GIVE_AUTH_STARS_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_give_author_stars_amount),
                CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", admin_cancel),
            CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
        ],
        per_message=False,
        allow_reentry=True,
    )

    author_balance_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(author_dep_start, pattern="^author_dep_start$"),
            CallbackQueryHandler(author_wd_start, pattern="^author_wd_start$"),
        ],
        states={
            WAIT_AUTHOR_DEP_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, author_dep_amount_received),
                CallbackQueryHandler(author_bal_cancel, pattern="^author_bal_cancel$"),
            ],
            WAIT_AUTHOR_WD_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, author_wd_amount_received),
                CallbackQueryHandler(author_bal_cancel, pattern="^author_bal_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", author_bal_cancel),
            CallbackQueryHandler(author_bal_cancel, pattern="^author_bal_cancel$"),
        ],
        per_message=False,
        allow_reentry=True,
    )

    author_add_channel_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(author_ch_add_start, pattern="^author_ch_add_start$")],
        states={
            WAIT_AUTHOR_CHANNEL_INPUT: [
                MessageHandler((filters.TEXT | getattr(filters, "FORWARDED", filters.PHOTO | filters.CAPTION)) & ~filters.COMMAND, author_ch_input_received),
                CallbackQueryHandler(author_ch_add_cancel, pattern="^author_ch_add_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", author_ch_add_cancel),
            CallbackQueryHandler(author_ch_add_cancel, pattern="^author_ch_add_cancel$"),
        ],
        per_message=False,
        allow_reentry=True,
    )

    giveaway_create_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(gw_create_start, pattern="^gw_create_start$")],
        states={
            WAIT_GW_CHANNELS: [
                CallbackQueryHandler(gw_channel_toggle, pattern="^(gw_tog_ch:|gw_all_ch$)"),
                CallbackQueryHandler(gw_channels_next, pattern="^gw_ch_next$"),
                CallbackQueryHandler(gw_cancel, pattern="^gw_cancel$"),
            ],
            WAIT_GW_TEXT: [
                MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, gw_text_received),
                CallbackQueryHandler(gw_cancel, pattern="^gw_cancel$"),
            ],
            WAIT_GW_PHOTO: [
                MessageHandler(filters.PHOTO, gw_photo_received),
                CallbackQueryHandler(gw_skip_photo, pattern="^gw_skip_photo$"),
                CallbackQueryHandler(gw_cancel, pattern="^gw_cancel$"),
            ],
            WAIT_GW_WINNERS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, gw_winners_received),
                CallbackQueryHandler(gw_cancel, pattern="^gw_cancel$"),
            ],
            WAIT_GW_PRIZE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, gw_prize_received),
                CallbackQueryHandler(gw_cancel, pattern="^gw_cancel$"),
            ],
            WAIT_GW_BTN_CONFIG: [
                CallbackQueryHandler(gw_btn_config_action, pattern="^(gw_btn_edit_text|gw_btn_style:|gw_btn_mode:|gw_btn_next$)"),
                CallbackQueryHandler(gw_cancel, pattern="^gw_cancel$"),
            ],
            WAIT_GW_BTN_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, gw_btn_text_received),
                CallbackQueryHandler(gw_cancel, pattern="^gw_cancel$"),
            ],
            WAIT_GW_END_COND: [
                CallbackQueryHandler(gw_end_cond_action, pattern="^(gw_end_preset:|gw_end_custom_time$|gw_end_max_custom$|gw_end_max_clear$|gw_end_next$)"),
                CallbackQueryHandler(gw_cancel, pattern="^gw_cancel$"),
            ],
            WAIT_GW_END_CUSTOM_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, gw_end_custom_time_received),
                CallbackQueryHandler(gw_cancel, pattern="^gw_cancel$"),
            ],
            WAIT_GW_END_CUSTOM_MAX: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, gw_end_custom_max_received),
                CallbackQueryHandler(gw_cancel, pattern="^gw_cancel$"),
            ],
            WAIT_GW_PUBLISH: [
                CallbackQueryHandler(gw_publish_action, pattern="^(gw_pub_now|gw_pub_sched)$"),
                CallbackQueryHandler(gw_cancel, pattern="^gw_cancel$"),
            ],
            WAIT_GW_SCHED_TIME: [
                CallbackQueryHandler(gw_sched_preset_selected, pattern="^gw_sched_preset:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, gw_sched_time_received),
                CallbackQueryHandler(gw_cancel, pattern="^gw_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", gw_cancel),
            CallbackQueryHandler(gw_cancel, pattern="^gw_cancel$"),
        ],
        per_message=False,
        allow_reentry=True,
    )

    admin_broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast_start, pattern="^admin_broadcast_start$")],
        states={
            WAIT_ADMIN_BROADCAST_MSG: [
                MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, admin_broadcast_msg_received),
                CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
            ],
            WAIT_ADMIN_BROADCAST_CONFIRM: [
                CallbackQueryHandler(admin_broadcast_confirm_pressed, pattern="^admin_broadcast_confirm$"),
                CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", admin_cancel),
            CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
        ],
        per_message=False,
        allow_reentry=True,
    )

    promocode_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(promo_redeem_start, pattern="^nav_promocodes$")],
        states={
            WAIT_PROMO_REDEEM_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, promo_redeem_code_received),
                CallbackQueryHandler(promo_redeem_cancel, pattern="^promo_redeem_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", promo_redeem_cancel),
            CallbackQueryHandler(promo_redeem_cancel, pattern="^promo_redeem_cancel$"),
        ],
        per_message=False,
        allow_reentry=True,
    )

    admin_promo_create_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_promo_create_start, pattern="^admin_promo_create_start$")],
        states={
            WAIT_ADMIN_PROMO_CODE: [
                CallbackQueryHandler(admin_promo_gen_code_pressed, pattern="^admin_promo_gen_code$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_promo_code_received),
                CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
            ],
            WAIT_ADMIN_PROMO_REWARD_TYPE: [
                CallbackQueryHandler(admin_promo_rtype_selected, pattern="^admin_promo_rtype:"),
                CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
            ],
            WAIT_ADMIN_PROMO_STARS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_promo_stars_received),
                CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
            ],
            WAIT_ADMIN_PROMO_GIFT: [
                CallbackQueryHandler(admin_promo_gift_picked, pattern="^admin_promo_pick_gift:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_promo_gift_text_received),
                CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
            ],
            WAIT_ADMIN_PROMO_GIFT_COUNT: [
                CallbackQueryHandler(admin_promo_gcnt_pressed, pattern="^admin_promo_gcnt:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_promo_gcnt_received),
                CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
            ],
            WAIT_ADMIN_PROMO_MAX_USES: [
                CallbackQueryHandler(admin_promo_max_pressed, pattern="^admin_promo_max:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_promo_max_received),
                CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", admin_cancel),
            CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
        ],
        per_message=False,
        allow_reentry=True,
    )

    admin_promo_edit_max_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_promo_edit_max_start, pattern="^admin_promo_edit_max_start:")],
        states={
            WAIT_ADMIN_PROMO_EDIT_MAX: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_promo_edit_max_received),
                CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", admin_cancel),
            CallbackQueryHandler(admin_cancel, pattern="^admin_cancel$"),
        ],
        per_message=False,
        allow_reentry=True,
    )

    app.add_handler(clan_conv)
    app.add_handler(admin_give_stars_conv)
    app.add_handler(admin_give_nft_conv)
    app.add_handler(admin_ban_conv)
    app.add_handler(admin_unban_conv)
    app.add_handler(clan_avatar_conv)
    app.add_handler(clan_donate_conv)
    app.add_handler(admin_firebase_key_conv)
    app.add_handler(bg_conv)
    app.add_handler(market_offer_conv)
    app.add_handler(gift_transfer_conv)
    app.add_handler(checks_conv)
    app.add_handler(check_pwd_claim_conv)
    app.add_handler(author_apply_conv)
    app.add_handler(admin_reject_app_conv)
    app.add_handler(admin_give_auth_stars_conv)
    app.add_handler(author_balance_conv)
    app.add_handler(author_add_channel_conv)
    app.add_handler(giveaway_create_conv)
    app.add_handler(admin_broadcast_conv)
    app.add_handler(promocode_conv)
    app.add_handler(admin_promo_create_conv)
    app.add_handler(admin_promo_edit_max_conv)

    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("profile", cmd_profile_alias))
    app.add_handler(CommandHandler("checks", cmd_checks))
    app.add_handler(CommandHandler("ref", cmd_referral))
    app.add_handler(CommandHandler("referral", cmd_referral))
    app.add_handler(CommandHandler("pay", cmd_pay))
    app.add_handler(CommandHandler("send_gift", cmd_send_gift))
    app.add_handler(CommandHandler("clans", cmd_clans))
    app.add_handler(CommandHandler("market", cmd_market))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("info", cmd_info))
    app.add_handler(MessageHandler(filters.COMMAND, cmd_maintenance_fallback))

    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    app.add_handler(InlineQueryHandler(on_inline_query))
    app.add_handler(ChosenInlineResultHandler(on_chosen_inline_result))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, on_group_message))

    log.info("New NFT Gift Telegram Bot v12.1 запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
