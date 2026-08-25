"""Authoritative durable storage for the bot.

Production rule: when MONGODB_URI is configured, MongoDB is mandatory. The
Render filesystem is never used as a silent fallback, so a database outage
stops the process instead of pretending to save data that will vanish.
"""
from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("DenjiBlast.DB")
MONGODB_URI = os.getenv("MONGODB_URI", os.getenv("MONGO_URI", "")).strip()
MONGODB_DB = os.getenv("MONGODB_DB", "denji_blast").strip() or "denji_blast"
DATA_FILE = Path(os.getenv("DATA_FILE", "blast_data.json"))
REQUIRE_MONGO = os.getenv("REQUIRE_MONGODB", "true").lower() not in {"0", "false", "no"}
_client = None
_collection = None
_last_error: str | None = None
_last_attempt = 0.0
_RETRY_AFTER = 30.0


def _mongo():
    global _client, _collection, _last_error, _last_attempt
    if _collection is not None:
        try:
            _client.admin.command("ping")
            return _collection
        except Exception:
            _collection = None
    if _last_attempt and time.time() - _last_attempt < _RETRY_AFTER:
        if REQUIRE_MONGO:
            raise RuntimeError(f"MongoDB temporarily unavailable: {_last_error or 'connection retry pending'}")
        return None
    _last_attempt = time.time()
    if not MONGODB_URI:
        _last_error = "MONGODB_URI is not configured"
        if REQUIRE_MONGO:
            raise RuntimeError(_last_error)
        return None
    try:
        from pymongo import MongoClient
        _client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=8000,
            connectTimeoutMS=8000,
            socketTimeoutMS=15000,
            retryWrites=True,
        )
        _client.admin.command("ping")
        _collection = _client[MONGODB_DB]["bot_state"]
        _last_error = None
        log.info("MongoDB connected: database=%s collection=bot_state", MONGODB_DB)
        return _collection
    except Exception as exc:
        _last_error = str(exc)
        log.exception("MongoDB connection failed")
        if REQUIRE_MONGO:
            raise RuntimeError(f"MongoDB is required but unavailable: {exc}") from exc
        return None


def health() -> dict[str, Any]:
    try:
        collection = _mongo()
        if collection is None:
            return {"connected": False, "required": REQUIRE_MONGO, "error": _last_error}
        collection.database.client.admin.command("ping")
        doc = collection.find_one({"_id": "state"}, {"version": 1, "updated_at": 1}) or {}
        return {"connected": True, "required": REQUIRE_MONGO, "version": doc.get("version", 0), "updated_at": doc.get("updated_at")}
    except Exception as exc:
        return {"connected": False, "required": REQUIRE_MONGO, "error": str(exc)}


def _json_load() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return {}
    try:
        with DATA_FILE.open("r", encoding="utf-8") as fh:
            value = json.load(fh)
        return value if isinstance(value, dict) else {}
    except Exception as exc:
        backup = DATA_FILE.with_name(DATA_FILE.name + f".corrupt.{int(time.time())}")
        try:
            DATA_FILE.replace(backup)
            log.error("Corrupt local state backed up to %s: %s", backup, exc)
        except Exception:
            log.exception("Could not back up corrupt local state")
        return {}


def _json_save(state: dict[str, Any]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=DATA_FILE.name + ".", suffix=".tmp", dir=str(DATA_FILE.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_name, DATA_FILE)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _migrate_legacy(collection) -> dict[str, Any]:
    legacy = _json_load()
    if not legacy:
        return {}
    snapshot = copy.deepcopy(legacy)
    snapshot.update({"_id": "state", "version": 1, "updated_at": int(time.time())})
    try:
        collection.insert_one(snapshot)
        log.info("Migrated legacy local state into MongoDB")
    except Exception:
        pass
    current = collection.find_one({"_id": "state"}) or {}
    for key in ("_id", "updated_at", "version"):
        current.pop(key, None)
    return current


def load() -> dict[str, Any]:
    collection = _mongo()
    if collection is None:
        return _json_load()
    try:
        document = collection.find_one({"_id": "state"})
        if not document:
            return _migrate_legacy(collection)
        for key in ("_id", "updated_at", "version"):
            document.pop(key, None)
        return document
    except Exception as exc:
        log.exception("MongoDB load failed")
        if REQUIRE_MONGO:
            raise RuntimeError(f"MongoDB load failed: {exc}") from exc
        return _json_load()


def save(state: dict[str, Any]) -> None:
    """Write state with an atomic compare-and-swap version check."""
    collection = _mongo()
    if collection is None:
        _json_save(state)
        return
    snapshot = copy.deepcopy(state)
    try:
        current = collection.find_one({"_id": "state"}, {"version": 1})
        expected = int((current or {}).get("version", 0))
        snapshot.update({"_id": "state", "version": expected + 1, "updated_at": int(time.time())})
        if current is None:
            result = collection.update_one({"_id": {"$exists": False}}, {"$setOnInsert": snapshot}, upsert=True)
            # If another writer inserted first, do not overwrite it.
            if result.upserted_id is None:
                raise RuntimeError("concurrent initialization rejected")
        else:
            result = collection.replace_one({"_id": "state", "version": expected}, snapshot, upsert=False)
            if result.modified_count != 1:
                # A concurrent whole-state writer won. Retry from its latest
                # version rather than turning the Telegram update into HTTP 500.
                latest = collection.find_one({"_id": "state"}, {"version": 1}) or {}
                latest_version = int(latest.get("version", expected))
                snapshot["version"] = latest_version + 1
                retry = collection.replace_one({"_id": "state", "version": latest_version}, snapshot, upsert=False)
                if retry.modified_count != 1:
                    raise RuntimeError("concurrent state update failed")
    except Exception as exc:
        log.exception("MongoDB save failed")
        if REQUIRE_MONGO:
            raise RuntimeError(f"MongoDB save failed: {exc}") from exc
        _json_save(state)
