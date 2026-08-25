"""Durable bot state storage.

MongoDB is authoritative when MONGODB_URI is configured. JSON is only a local
fallback; it is never used to overwrite MongoDB after a successful connection.
"""
from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger("DenjiBlast.DB")

MONGODB_URI = os.getenv("MONGODB_URI", os.getenv("MONGO_URI", "")).strip()
MONGODB_DB = os.getenv("MONGODB_DB", "denji_blast")
DATA_FILE = Path(os.getenv("DATA_FILE", "blast_data.json"))

_client = None
_collection = None
_mongo_failed = False


def _collection_handle():
    global _client, _collection, _mongo_failed
    if _collection is not None:
        return _collection
    if _mongo_failed or not MONGODB_URI:
        return None
    try:
        from pymongo import MongoClient
        _client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            retryWrites=True,
        )
        _client.admin.command("ping")
        _collection = _client[MONGODB_DB]["bot_state"]
        _collection.create_index("_id", unique=True)
        log.info("MongoDB connected: %s/%s", MONGODB_DB, "bot_state")
        return _collection
    except Exception as exc:
        _mongo_failed = True
        log.error("MongoDB unavailable; using local fallback only: %s", exc)
        return None


def _json_load() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return {}
    try:
        with DATA_FILE.open("r", encoding="utf-8") as fh:
            value = json.load(fh)
        return value if isinstance(value, dict) else {}
    except Exception as exc:
        # Never delete or silently replace a possibly recoverable state file.
        backup = DATA_FILE.with_name(DATA_FILE.name + ".corrupt")
        try:
            DATA_FILE.replace(backup)
            log.error("Backed up corrupt state to %s: %s", backup, exc)
        except Exception:
            log.error("Could not back up corrupt state: %s", exc)
        return {}


def _json_save(state: dict[str, Any]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=DATA_FILE.name + ".", suffix=".tmp", dir=str(DATA_FILE.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_name, DATA_FILE)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def load() -> dict[str, Any]:
    collection = _collection_handle()
    if collection is not None:
        try:
            document = collection.find_one({"_id": "state"})
            if document:
                document.pop("_id", None)
                return document
            # One-time migration from local JSON, only if Mongo is empty.
            legacy = _json_load()
            if legacy:
                save(legacy)
                log.info("Migrated legacy local state into MongoDB")
                return copy.deepcopy(legacy)
            return {}
        except Exception as exc:
            log.error("MongoDB load failed; retaining local fallback: %s", exc)
    return _json_load()


def save(state: dict[str, Any]) -> None:
    snapshot = copy.deepcopy(state)
    collection = _collection_handle()
    if collection is not None:
        try:
            snapshot["_id"] = "state"
            collection.replace_one({"_id": "state"}, snapshot, upsert=True)
            return
        except Exception as exc:
            log.error("MongoDB save failed; writing local fallback: %s", exc)
    _json_save(state)
