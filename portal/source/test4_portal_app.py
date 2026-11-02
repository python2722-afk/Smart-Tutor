#!/usr/bin/env python3
"""Authenticated phone and hardware gateway for the Test4 search machine."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
from io import BytesIO
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import (
    HTTPRedirectHandler,
    ProxyHandler,
    Request as UrlRequest,
    build_opener,
)

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from PIL import Image, UnidentifiedImageError


SOURCE_DIR = Path(__file__).resolve().parent
STATIC_DIR = SOURCE_DIR / "static"

def _loopback_backend(setting: str, default: str) -> str:
    """Allow deployment-specific ports while rejecting non-loopback targets."""

    raw = os.environ.get(setting, "").strip() or default
    parsed = urlparse(raw)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.port is None
    ):
        raise RuntimeError(f"{setting} 必须是带端口的HTTP回环地址")
    return f"http://127.0.0.1:{parsed.port}"


# No request field is ever accepted as a host or port, so this proxy cannot be
# used as a generic network relay.
BACKENDS = {
    "physics": _loopback_backend(
        "TEST4_PHYSICS_BACKEND_URL", "http://127.0.0.1:8010"
    ),
    "math": _loopback_backend("TEST4_MATH_BACKEND_URL", "http://127.0.0.1:8020"),
}
SUBJECT_LABELS = {"physics": "物理", "math": "数学"}
EXPECTED_BACKEND_SERVICES = {
    "physics": "test4-physics-search-machine",
    "math": "test4-math-search-machine",
}

API_VERSION = "v1"
SERVICE_VERSION = "4.0.0"
ACCESS_TOKEN = os.environ.get("TEST4_ACCESS_TOKEN", "").strip()
RAW_DEVICE_TOKEN_HASHES = [
    item.strip().lower()
    for item in os.environ.get("TEST4_DEVICE_TOKEN_HASHES", "").split(",")
    if item.strip()
]
if any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in RAW_DEVICE_TOKEN_HASHES):
    raise RuntimeError("TEST4_DEVICE_TOKEN_HASHES 必须是逗号分隔的SHA-256十六进制值")
DEVICE_TOKEN_HASHES = tuple(RAW_DEVICE_TOKEN_HASHES)
ALLOW_INSECURE_NO_AUTH = os.environ.get(
    "TEST4_ALLOW_INSECURE_NO_AUTH", ""
).strip().lower() in {"1", "true", "yes"}
COOKIE_SECURE = os.environ.get("TEST4_COOKIE_SECURE", "1").strip().lower() not in {
    "0",
    "false",
    "no",
}
COOKIE_NAME = "__Host-test4_session" if COOKIE_SECURE else "test4_session"
SESSION_TTL_SECONDS = max(
    300,
    min(30 * 24 * 3600, int(os.environ.get("TEST4_SESSION_TTL_SECONDS", "604800"))),
)
if not ACCESS_TOKEN and not ALLOW_INSECURE_NO_AUTH:
    raise RuntimeError(
        "TEST4_ACCESS_TOKEN 未配置；公网部署必须设置至少24位随机访问令牌"
    )
if ACCESS_TOKEN.startswith("replace_"):
    raise RuntimeError("TEST4_ACCESS_TOKEN 仍是示例值")
if ACCESS_TOKEN and len(ACCESS_TOKEN) < 24:
    raise RuntimeError("TEST4_ACCESS_TOKEN 至少需要24个字符")


def _session_signature(payload: str) -> str:
    return hmac.new(
        ACCESS_TOKEN.encode("utf-8"),
        ("test4-browser-session-v1:" + payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _encode_session(expires_at: int, nonce: str) -> str:
    payload = f"{expires_at}.{nonce}"
    return f"{payload}.{_session_signature(payload)}"


def _new_session_value() -> str:
    return _encode_session(
        int(time.time()) + SESSION_TTL_SECONDS,
        secrets.token_hex(16),
    )


def _valid_session(value: str) -> bool:
    if not value or len(value) > 256:
        return False
    try:
        expires_raw, nonce, signature = value.split(".", 2)
        expires_at = int(expires_raw)
    except (TypeError, ValueError):
        return False
    if expires_at < int(time.time()) or not re.fullmatch(r"[0-9a-f]{32}", nonce):
        return False
    payload = f"{expires_at}.{nonce}"
    return secrets.compare_digest(signature, _session_signature(payload))

DEVICE_IMAGE_NAMES = (
    "01_question_knowledge.png",
    "02_guidance_advanced.png",
    "03_guidance_standard.png",
    "04_guidance_foundation.png",
)
DEVICE_IMAGE_KINDS = (
    "question_knowledge",
    "advanced",
    "standard",
    "foundation",
)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_JSON_BYTES = 1024 * 1024
MAX_RESULT_BYTES = 20 * 1024 * 1024
MAX_MULTIPART_BYTES = MAX_UPLOAD_BYTES + 1024 * 1024
UPSTREAM_TIMEOUT_SECONDS = 20
JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
IMAGE_MEDIA_TYPE_PATTERN = re.compile(r"^image/[a-z0-9][a-z0-9.+-]{0,63}$")
IDEMPOTENCY_KEY_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._~-]{7,127}$",
    re.ASCII,
)
IDEMPOTENCY_PENDING_LEASE_SECONDS = UPSTREAM_TIMEOUT_SECONDS + 15
IDEMPOTENCY_WAIT_SECONDS = UPSTREAM_TIMEOUT_SECONDS + 20
IDEMPOTENCY_RETENTION_SECONDS = 7 * 24 * 3600
_state_db_raw = os.environ.get("TEST4_PORTAL_STATE_DB", "").strip()
PORTAL_STATE_DB = Path(_state_db_raw) if _state_db_raw else (
    SOURCE_DIR / ".state" / "gateway.sqlite3"
)
if not PORTAL_STATE_DB.is_absolute():
    raise RuntimeError("TEST4_PORTAL_STATE_DB must be an absolute path")
ALLOWED_UPLOAD_MEDIA_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)
ALLOWED_STATUSES = {
    "queued",
    "preprocessing",
    "solving",
    "rendering",
    "completed",
    "failed",
}


class UpstreamFailure(Exception):
    """A safe, user-facing representation of an upstream failure."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class UploadBodyTooLarge(Exception):
    """Raised before multipart parsing can spool an oversized request."""


class IdempotencyConflict(Exception):
    """The same principal/subject/key was already used for another image."""


class IdempotencyStoreFailure(Exception):
    """The durable idempotency state could not be read or updated safely."""


def _open_idempotency_db() -> sqlite3.Connection:
    connection = sqlite3.connect(
        str(PORTAL_STATE_DB),
        timeout=5,
        isolation_level=None,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=5000")
    connection.execute("PRAGMA synchronous=FULL")
    return connection


def _initialize_idempotency_db() -> None:
    connection: sqlite3.Connection | None = None
    try:
        PORTAL_STATE_DB.parent.mkdir(parents=True, exist_ok=True)
        connection = _open_idempotency_db()
        journal_mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if str(journal_mode).lower() != "wal":
            raise IdempotencyStoreFailure("SQLite WAL mode is unavailable")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS idempotency_jobs (
                principal_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                key_sha256 TEXT NOT NULL,
                image_sha256 TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state IN ('pending', 'ready')),
                owner_nonce TEXT,
                lease_expires REAL,
                response_json TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (principal_id, subject, key_sha256)
            ) WITHOUT ROWID
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idempotency_jobs_updated_at
            ON idempotency_jobs(updated_at)
            """
        )
    except (IdempotencyStoreFailure, OSError, sqlite3.Error) as exc:
        raise RuntimeError(
            "TEST4_PORTAL_STATE_DB could not be initialized"
        ) from exc
    finally:
        if connection is not None:
            connection.close()


_initialize_idempotency_db()


class UploadBodyLimitMiddleware:
    """Enforce the upload limit while ASGI request chunks are arriving."""

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        path = str(scope.get("path") or "")
        limited = (
            scope.get("type") == "http"
            and scope.get("method") == "POST"
            and re.fullmatch(
                r"/api/v1/(?:physics|math)/jobs(?:/raw)?", path
            )
            is not None
        )
        if not limited:
            await self.app(scope, receive, send)
            return
        headers = {
            key.lower(): value
            for key, value in scope.get("headers") or []
        }
        raw_length = headers.get(b"content-length", b"")
        if raw_length.isdigit() and int(raw_length) > MAX_MULTIPART_BYTES:
            response = JSONResponse(
                status_code=413,
                content={"detail": "图片不能超过 20 MB"},
                headers={"Cache-Control": "no-store", "Connection": "close"},
            )
            await response(scope, receive, send)
            return
        received = 0

        async def limited_receive() -> dict[str, Any]:
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body") or b"")
                if received > MAX_MULTIPART_BYTES:
                    raise UploadBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except UploadBodyTooLarge:
            response = JSONResponse(
                status_code=413,
                content={"detail": "图片不能超过 20 MB"},
                headers={"Cache-Control": "no-store", "Connection": "close"},
            )
            await response(scope, receive, send)


class _NoRedirectHandler(HTTPRedirectHandler):
    """Keep every upstream request on its allow-listed loopback origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


# Disable environment-configured proxies and HTTP redirects.  This is stronger
# than checking only the initial URL: every network hop stays on the two fixed
# loopback services above.
_UPSTREAM_OPENER = build_opener(ProxyHandler({}), _NoRedirectHandler())


def backend_for_subject(subject: str) -> str:
    """Resolve a subject through the fixed backend allow-list."""

    backend = BACKENDS.get(subject)
    if backend is None:
        raise HTTPException(404, "请选择物理或数学")
    return backend


def validate_job_id(job_id: str) -> str:
    if not JOB_ID_PATTERN.fullmatch(job_id):
        raise HTTPException(400, "任务编号格式不正确")
    return job_id


def validate_result_filename(filename: str) -> str:
    if filename not in DEVICE_IMAGE_NAMES:
        raise HTTPException(404, "结果图不存在")
    return filename


def validate_upload(data: bytes, content_type: str | None) -> str:
    media_type = (content_type or "").split(";", 1)[0].strip().lower()
    if (
        not IMAGE_MEDIA_TYPE_PATTERN.fullmatch(media_type)
        or media_type not in ALLOWED_UPLOAD_MEDIA_TYPES
    ):
        raise HTTPException(415, "仅支持 JPEG、PNG 或 WebP 图片")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "图片不能超过 20 MB")
    if not data:
        raise HTTPException(400, "请选择一张题目图片")
    return media_type


def idempotency_key_digest(request: Request) -> str | None:
    """Validate and hash the optional header without persisting its raw value."""

    values = request.headers.getlist("idempotency-key")
    if not values:
        return None
    if len(values) != 1 or IDEMPOTENCY_KEY_PATTERN.fullmatch(values[0]) is None:
        raise HTTPException(
            400,
            "Idempotency-Key 必须是 8-128 位 ASCII 字母、数字或 . _ ~ -",
        )
    return hashlib.sha256(values[0].encode("ascii")).hexdigest()


def _stored_idempotency_response(raw: str | None, subject: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw or "")
    except json.JSONDecodeError as exc:
        raise IdempotencyStoreFailure("stored response is invalid") from exc
    if not isinstance(payload, dict):
        raise IdempotencyStoreFailure("stored response is invalid")
    job_id = payload.get("job_id")
    expected_poll = f"/api/v1/{subject}/jobs/{quote(str(job_id or ''), safe='')}"
    if (
        payload.get("subject") != subject
        or not isinstance(job_id, str)
        or JOB_ID_PATTERN.fullmatch(job_id) is None
        or payload.get("poll_url") != expected_poll
    ):
        raise IdempotencyStoreFailure("stored response is invalid")
    return payload


def _claim_idempotency(
    principal_id: str,
    subject: str,
    key_sha256: str,
    image_sha256: str,
) -> tuple[str, str | None, dict[str, Any] | None]:
    """Atomically claim a key, observe a pending owner, or replay a result."""

    now = time.time()
    owner_nonce = secrets.token_hex(16)
    connection: sqlite3.Connection | None = None
    try:
        connection = _open_idempotency_db()
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "DELETE FROM idempotency_jobs WHERE updated_at < ?",
            (now - IDEMPOTENCY_RETENTION_SECONDS,),
        )
        row = connection.execute(
            """
            SELECT image_sha256, state, owner_nonce, lease_expires, response_json
            FROM idempotency_jobs
            WHERE principal_id = ? AND subject = ? AND key_sha256 = ?
            """,
            (principal_id, subject, key_sha256),
        ).fetchone()
        if row is None:
            connection.execute(
                """
                INSERT INTO idempotency_jobs (
                    principal_id, subject, key_sha256, image_sha256, state,
                    owner_nonce, lease_expires, response_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'pending', ?, ?, NULL, ?, ?)
                """,
                (
                    principal_id,
                    subject,
                    key_sha256,
                    image_sha256,
                    owner_nonce,
                    now + IDEMPOTENCY_PENDING_LEASE_SECONDS,
                    now,
                    now,
                ),
            )
            connection.commit()
            return "owner", owner_nonce, None

        if not secrets.compare_digest(str(row["image_sha256"]), image_sha256):
            raise IdempotencyConflict
        if row["state"] == "ready":
            payload = _stored_idempotency_response(row["response_json"], subject)
            connection.commit()
            return "ready", None, payload
        lease_expires = float(row["lease_expires"] or 0)
        if lease_expires > now:
            connection.commit()
            return "pending", None, None
        connection.execute(
            """
            UPDATE idempotency_jobs
            SET owner_nonce = ?, lease_expires = ?, updated_at = ?
            WHERE principal_id = ? AND subject = ? AND key_sha256 = ?
              AND state = 'pending'
            """,
            (
                owner_nonce,
                now + IDEMPOTENCY_PENDING_LEASE_SECONDS,
                now,
                principal_id,
                subject,
                key_sha256,
            ),
        )
        connection.commit()
        return "owner", owner_nonce, None
    except IdempotencyConflict:
        if connection is not None and connection.in_transaction:
            connection.rollback()
        raise
    except (IdempotencyStoreFailure, OSError, sqlite3.Error, TypeError, ValueError) as exc:
        if connection is not None and connection.in_transaction:
            connection.rollback()
        if isinstance(exc, IdempotencyStoreFailure):
            raise
        raise IdempotencyStoreFailure("idempotency state is unavailable") from exc
    finally:
        if connection is not None:
            connection.close()


def _complete_idempotency(
    principal_id: str,
    subject: str,
    key_sha256: str,
    image_sha256: str,
    owner_nonce: str,
    response: dict[str, Any],
) -> None:
    now = time.time()
    encoded = json.dumps(
        response,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    connection: sqlite3.Connection | None = None
    try:
        connection = _open_idempotency_db()
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """
            UPDATE idempotency_jobs
            SET state = 'ready', owner_nonce = NULL, lease_expires = NULL,
                response_json = ?, updated_at = ?
            WHERE principal_id = ? AND subject = ? AND key_sha256 = ?
              AND image_sha256 = ? AND state = 'pending' AND owner_nonce = ?
            """,
            (
                encoded,
                now,
                principal_id,
                subject,
                key_sha256,
                image_sha256,
                owner_nonce,
            ),
        )
        if cursor.rowcount != 1:
            raise IdempotencyStoreFailure("idempotency owner changed unexpectedly")
        connection.commit()
    except (IdempotencyStoreFailure, OSError, sqlite3.Error) as exc:
        if connection is not None and connection.in_transaction:
            connection.rollback()
        if isinstance(exc, IdempotencyStoreFailure):
            raise
        raise IdempotencyStoreFailure("idempotency state is unavailable") from exc
    finally:
        if connection is not None:
            connection.close()


def _release_idempotency(
    principal_id: str,
    subject: str,
    key_sha256: str,
    image_sha256: str,
    owner_nonce: str,
) -> None:
    """Release only this request's pending claim after upstream rejection."""

    connection: sqlite3.Connection | None = None
    try:
        connection = _open_idempotency_db()
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            DELETE FROM idempotency_jobs
            WHERE principal_id = ? AND subject = ? AND key_sha256 = ?
              AND image_sha256 = ? AND state = 'pending' AND owner_nonce = ?
            """,
            (principal_id, subject, key_sha256, image_sha256, owner_nonce),
        )
        connection.commit()
    except (OSError, sqlite3.Error) as exc:
        if connection is not None and connection.in_transaction:
            connection.rollback()
        raise IdempotencyStoreFailure("idempotency state is unavailable") from exc
    finally:
        if connection is not None:
            connection.close()


def _friendly_upstream_error(status_code: int, subject: str) -> str:
    label = SUBJECT_LABELS[subject]
    messages = {
        400: "题图无法识别，请换一张清晰、完整的照片",
        404: "任务或结果不存在，可能已被清理",
        413: "图片不能超过 20 MB",
        415: "仅支持图片文件",
        429: f"{label}任务较多，请稍后重试",
        503: f"{label}处理服务暂时不可用，请稍后重试",
    }
    return messages.get(status_code, f"{label}处理服务暂时无法完成请求，请稍后重试")


def _read_limited(stream: Any, limit: int, too_large_message: str) -> bytes:
    data = stream.read(limit + 1)
    if len(data) > limit:
        raise UpstreamFailure(502, too_large_message)
    return data


def _request_json(
    subject: str,
    path: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Make a bounded JSON request to one fixed upstream service."""

    url = backend_for_subject(subject) + path
    request = UrlRequest(url, data=data, headers=headers or {}, method=method)
    try:
        with _UPSTREAM_OPENER.open(
            request, timeout=UPSTREAM_TIMEOUT_SECONDS
        ) as response:
            raw = _read_limited(
                response,
                MAX_JSON_BYTES,
                "处理服务返回的数据异常，请稍后重试",
            )
    except HTTPError as exc:
        try:
            exc.close()
        finally:
            raise UpstreamFailure(
                exc.code,
                _friendly_upstream_error(exc.code, subject),
            ) from None
    except (URLError, TimeoutError, OSError):
        raise UpstreamFailure(
            503,
            f"{SUBJECT_LABELS[subject]}处理服务暂时无法连接，请稍后重试",
        ) from None

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise UpstreamFailure(502, "处理服务返回的数据无法识别，请稍后重试") from None
    if not isinstance(payload, dict):
        raise UpstreamFailure(502, "处理服务返回的数据格式不正确，请稍后重试")
    return payload


def _multipart_upload(data: bytes, content_type: str) -> tuple[bytes, str]:
    boundary = "----test4-" + secrets.token_hex(18)
    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }[content_type.lower()]
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="camera.{extension}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("ascii")
    suffix = f"\r\n--{boundary}--\r\n".encode("ascii")
    return prefix + data + suffix, boundary


def _submit_job_sync(subject: str, data: bytes, content_type: str) -> dict[str, Any]:
    body, boundary = _multipart_upload(data, content_type)
    return _request_json(
        subject,
        "/api/jobs",
        method="POST",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
    )


def _fetch_job_sync(subject: str, job_id: str) -> dict[str, Any]:
    safe_job_id = quote(validate_job_id(job_id), safe="")
    return _request_json(subject, f"/api/jobs/{safe_job_id}")


def _validated_result_metadata(item: dict[str, Any]) -> dict[str, Any]:
    """Enforce metadata required by hardware before declaring a job complete."""

    width = item.get("width")
    height = item.get("height")
    mode = item.get("mode")
    image_format = item.get("format")
    byte_count = item.get("bytes")
    digest = item.get("sha256")
    display_width = item.get("display_width_cm")
    valid = (
        isinstance(width, int)
        and not isinstance(width, bool)
        and width == 800
        and isinstance(height, int)
        and not isinstance(height, bool)
        and height > 0
        and mode == "L"
        and image_format == "PNG"
        and isinstance(byte_count, int)
        and not isinstance(byte_count, bool)
        and byte_count > 0
        and isinstance(digest, str)
        and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
        and isinstance(display_width, (int, float))
        and not isinstance(display_width, bool)
        and abs(float(display_width) - 9.0) <= 0.001
    )
    if not valid:
        raise UpstreamFailure(502, "结果图元数据不符合 Test3 四图合同，请重新提交")
    return {
        "width": width,
        "height": height,
        "mode": mode,
        "bytes": byte_count,
        "sha256": digest,
        "display_width_cm": float(display_width),
    }


def sanitize_job(
    subject: str,
    payload: dict[str, Any],
    *,
    expected_job_id: str | None = None,
) -> dict[str, Any]:
    """Return only public state and rewrite every image to this origin."""

    backend_for_subject(subject)
    job_id = str(payload.get("job_id") or "")
    if not JOB_ID_PATTERN.fullmatch(job_id):
        raise UpstreamFailure(502, "处理服务返回的任务编号不正确，请重新提交")
    if expected_job_id is not None and job_id != expected_job_id:
        raise UpstreamFailure(502, "处理服务返回了不匹配的任务，请重新提交")

    status = str(payload.get("status") or "")
    if status not in ALLOWED_STATUSES:
        raise UpstreamFailure(502, "处理服务返回的任务状态不正确，请稍后重试")

    public: dict[str, Any] = {
        "api_version": API_VERSION,
        "subject": subject,
        "subject_label": SUBJECT_LABELS[subject],
        "job_id": job_id,
        "status": status,
        "created_at": payload.get("created_at"),
        "updated_at": payload.get("updated_at"),
        "elapsed_seconds": payload.get("elapsed_seconds"),
        "error": None,
        "images": [],
        "retry_after_seconds": 2,
        "poll_url": f"/api/v1/{subject}/jobs/{quote(job_id, safe='')}",
        "result_contract": {
            "name": "test3-four-png",
            "version": "1",
            "complete": status == "completed",
        },
    }

    if status == "failed":
        public["error"] = {
            "message": "处理没有完成，请检查题图是否清晰、完整后重新拍照提交"
        }

    if status == "completed":
        upstream_images = payload.get("images")
        if not isinstance(upstream_images, list):
            raise UpstreamFailure(502, "四张结果图尚未完整生成，请重新提交")
        observed: list[str] = []
        for item in upstream_images:
            if not isinstance(item, dict):
                raise UpstreamFailure(502, "四张结果图的数据不完整，请重新提交")
            filename = str(item.get("filename") or "")
            if filename not in DEVICE_IMAGE_NAMES or filename in observed:
                raise UpstreamFailure(502, "结果图格式不符合四图要求，请重新提交")
            observed.append(filename)
        if set(observed) != set(DEVICE_IMAGE_NAMES) or len(observed) != 4:
            raise UpstreamFailure(502, "四张结果图尚未完整生成，请重新提交")

        safe_job_id = quote(job_id, safe="")
        upstream_by_name = {
            str(item.get("filename") or ""): item for item in upstream_images
        }
        public_images: list[dict[str, Any]] = []
        for index, (filename, kind) in enumerate(
            zip(DEVICE_IMAGE_NAMES, DEVICE_IMAGE_KINDS), start=1
        ):
            upstream = upstream_by_name[filename]
            metadata = _validated_result_metadata(upstream)
            current: dict[str, Any] = {
                "sequence": index,
                "kind": kind,
                "filename": filename,
                "media_type": "image/png",
                "url": (
                    f"/api/v1/{subject}/jobs/{safe_job_id}/images/"
                    f"{quote(filename, safe='')}"
                ),
                **metadata,
            }
            public_images.append(current)
        public["images"] = public_images
    return public


def _fetch_png_sync(subject: str, job_id: str, filename: str) -> bytes:
    safe_job_id = quote(validate_job_id(job_id), safe="")
    safe_filename = quote(validate_result_filename(filename), safe="")
    url = backend_for_subject(subject) + f"/jobs/{safe_job_id}/{safe_filename}"
    request = UrlRequest(url, method="GET", headers={"Accept": "image/png"})
    try:
        with _UPSTREAM_OPENER.open(
            request, timeout=UPSTREAM_TIMEOUT_SECONDS
        ) as response:
            content_type = response.headers.get_content_type()
            data = _read_limited(
                response,
                MAX_RESULT_BYTES,
                "结果图过大，请重新提交题图",
            )
    except HTTPError as exc:
        try:
            exc.close()
        finally:
            raise UpstreamFailure(
                exc.code,
                _friendly_upstream_error(exc.code, subject),
            ) from None
    except (URLError, TimeoutError, OSError):
        raise UpstreamFailure(
            503,
            f"{SUBJECT_LABELS[subject]}结果图暂时无法读取，请稍后重试",
        ) from None

    if content_type != "image/png":
        raise UpstreamFailure(502, "处理服务返回的结果不是有效 PNG 图片")
    validate_device_png(data)
    return data


def validate_device_png(data: bytes) -> None:
    """Decode the trusted result fully and enforce the shared test3 geometry."""

    try:
        with Image.open(BytesIO(data)) as image:
            image_format = image.format
            width, height = image.size
            mode = image.mode
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise UpstreamFailure(502, "处理服务返回的结果不是有效 PNG 图片") from None
    if image_format != "PNG" or width != 800 or height <= 0 or mode != "L":
        raise UpstreamFailure(502, "结果图不符合 test3 的 PNG 显示规格")


def _subject_health_sync(subject: str) -> dict[str, Any]:
    try:
        payload = _request_json(subject, "/health")
    except UpstreamFailure:
        return {"available": False, "status": "unavailable"}
    healthy = (
        payload.get("status") == "ok"
        and payload.get("worker_alive") is True
        and payload.get("service") == EXPECTED_BACKEND_SERVICES[subject]
    )
    return {
        "available": healthy,
        "status": "ok" if healthy else "unavailable",
    }


def _upstream_http_exception(exc: UpstreamFailure) -> HTTPException:
    # Upstream 5xx responses become a gateway error, except a genuine service
    # outage, while expected client/queue errors keep their useful status.
    status_code = exc.status_code
    if status_code >= 500 and status_code != 503:
        status_code = 502
    headers = {"Retry-After": "2"} if status_code == 429 else None
    return HTTPException(status_code, exc.detail, headers=headers)


def _principal_id(kind: str, material: str) -> str:
    """Return a stable opaque identity; credentials are never stored in SQLite."""

    message = f"test4-auth-principal-v1:{kind}:{material}".encode("utf-8")
    return hashlib.sha256(message).hexdigest()


def _authenticated_principal(request: Request) -> str | None:
    """Authenticate and identify a Bearer credential or browser session."""

    if ALLOW_INSECURE_NO_AUTH and not ACCESS_TOKEN:
        return _principal_id("insecure", "local")
    authorization = request.headers.get("authorization", "")
    if authorization:
        if not authorization.lower().startswith("bearer "):
            return None
        candidate = authorization[7:].strip()
        if not candidate or len(candidate) > 1024:
            return None
        if secrets.compare_digest(candidate, ACCESS_TOKEN):
            return _principal_id("primary", ACCESS_TOKEN)
        candidate_hash = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        for expected in DEVICE_TOKEN_HASHES:
            if secrets.compare_digest(candidate_hash, expected):
                return _principal_id("device", candidate_hash)
        return None
    session = request.cookies.get(COOKIE_NAME, "")
    if _valid_session(session):
        return _principal_id("primary", ACCESS_TOKEN)
    return None


def _authorized(request: Request) -> bool:
    return _authenticated_principal(request) is not None


def require_access(request: Request) -> str:
    principal_id = _authenticated_principal(request)
    if principal_id is None:
        raise HTTPException(
            401,
            "需要有效的设备访问令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal_id


app = FastAPI(
    title="Test4 物理数学统一搜题机",
    version=SERVICE_VERSION,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(UploadBodyLimitMiddleware)


def public_json(content: dict[str, Any], *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


def accepted_job(
    content: dict[str, Any],
    *,
    idempotency_replayed: bool | None = None,
) -> JSONResponse:
    response = public_json(content, status_code=202)
    response.headers["Location"] = str(content["poll_url"])
    response.headers["Retry-After"] = str(content["retry_after_seconds"])
    if idempotency_replayed is not None:
        response.headers["Idempotency-Replayed"] = (
            "true" if idempotency_replayed else "false"
        )
    return response


def _idempotency_unavailable() -> HTTPException:
    return HTTPException(
        503,
        "暂时无法安全确认该请求是否已经创建，请保留相同 Idempotency-Key 后重试",
        headers={"Retry-After": "2"},
    )


async def _create_job_from_bytes(
    subject: str,
    request: Request,
    principal_id: str,
    data: bytes,
    media_type: str,
) -> JSONResponse:
    key_sha256 = idempotency_key_digest(request)
    if key_sha256 is None:
        try:
            payload = await asyncio.to_thread(
                _submit_job_sync,
                subject,
                data,
                media_type,
            )
            return accepted_job(sanitize_job(subject, payload))
        except UpstreamFailure as exc:
            raise _upstream_http_exception(exc) from exc

    image_sha256 = hashlib.sha256(data).hexdigest()
    deadline = time.monotonic() + IDEMPOTENCY_WAIT_SECONDS
    while True:
        try:
            action, owner_nonce, replay = await asyncio.to_thread(
                _claim_idempotency,
                principal_id,
                subject,
                key_sha256,
                image_sha256,
            )
        except IdempotencyConflict as exc:
            raise HTTPException(
                409,
                "该 Idempotency-Key 已用于同一学科的另一张图片，请生成新 key",
            ) from exc
        except IdempotencyStoreFailure as exc:
            raise _idempotency_unavailable() from exc

        if action == "ready":
            assert replay is not None
            return accepted_job(replay, idempotency_replayed=True)
        if action == "pending":
            if time.monotonic() >= deadline:
                raise _idempotency_unavailable()
            await asyncio.sleep(0.05)
            continue

        assert action == "owner" and owner_nonce is not None
        try:
            payload = await asyncio.to_thread(
                _submit_job_sync,
                subject,
                data,
                media_type,
            )
            public = sanitize_job(subject, payload)
        except UpstreamFailure as exc:
            try:
                await asyncio.to_thread(
                    _release_idempotency,
                    principal_id,
                    subject,
                    key_sha256,
                    image_sha256,
                    owner_nonce,
                )
            except IdempotencyStoreFailure as store_exc:
                raise _idempotency_unavailable() from store_exc
            raise _upstream_http_exception(exc) from exc

        # A transient SQLite lock after upstream accepted the job must not make
        # the gateway immediately create a duplicate. Retry the durable commit.
        for attempt in range(3):
            try:
                await asyncio.to_thread(
                    _complete_idempotency,
                    principal_id,
                    subject,
                    key_sha256,
                    image_sha256,
                    owner_nonce,
                    public,
                )
                return accepted_job(public, idempotency_replayed=False)
            except IdempotencyStoreFailure as exc:
                if attempt == 2:
                    raise _idempotency_unavailable() from exc
                await asyncio.sleep(0.05 * (attempt + 1))


@app.post("/api/v1/auth/login", include_in_schema=False)
async def create_browser_session(request: Request) -> JSONResponse:
    if ALLOW_INSECURE_NO_AUTH and not ACCESS_TOKEN:
        return public_json({"authenticated": True, "mode": "insecure-local"})
    if (request.headers.get("content-type") or "").split(";", 1)[0].strip() != "application/json":
        raise HTTPException(415, "登录请求必须使用JSON")
    raw = await request.body()
    if len(raw) > 4096:
        raise HTTPException(413, "访问令牌过长")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(400, "登录请求格式不正确") from None
    candidate = str(payload.get("token") or "") if isinstance(payload, dict) else ""
    if not candidate or not secrets.compare_digest(candidate, ACCESS_TOKEN):
        raise HTTPException(401, "访问令牌不正确")
    response = public_json({"authenticated": True})
    response.set_cookie(
        COOKIE_NAME,
        _new_session_value(),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return response


@app.get("/api/v1/auth/session", include_in_schema=False)
def browser_session(request: Request) -> JSONResponse:
    return public_json({"authenticated": _authorized(request)})


@app.delete("/api/v1/auth/logout", include_in_schema=False)
def delete_browser_session() -> JSONResponse:
    response = public_json({"authenticated": False})
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="strict",
    )
    return response


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": (
                "default-src 'self'; img-src 'self' data: blob:; "
                "connect-src 'self'; style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; object-src 'none'; "
                "base-uri 'none'; form-action 'self'"
            ),
            "Referrer-Policy": "no-referrer",
            "X-Frame-Options": "DENY",
        },
    )


@app.get("/api/v1/capabilities")
def capabilities(_principal_id: str = Depends(require_access)) -> JSONResponse:
    return public_json(
        {
            "api_version": API_VERSION,
            "service_version": SERVICE_VERSION,
            "subjects": [
                {"id": subject, "label": SUBJECT_LABELS[subject]}
                for subject in ("physics", "math")
            ],
            "upload": {
                "multipart_field": "image",
                "raw_endpoint_suffix": "/raw",
                "media_types": ["image/jpeg", "image/png", "image/webp"],
                "max_bytes": MAX_UPLOAD_BYTES,
                "idempotency": {
                    "header": "Idempotency-Key",
                    "optional": True,
                    "min_length": 8,
                    "max_length": 128,
                    "retention_seconds": IDEMPOTENCY_RETENTION_SECONDS,
                },
            },
            "workflow": "asynchronous",
            "poll_after_ms": 1200,
            "results": [
                {"sequence": index, "kind": kind, "filename": filename}
                for index, (kind, filename) in enumerate(
                    zip(DEVICE_IMAGE_KINDS, DEVICE_IMAGE_NAMES), start=1
                )
            ],
        }
    )


@app.get("/health")
async def health() -> JSONResponse:
    subjects = tuple(BACKENDS)
    checks = await asyncio.gather(
        *(asyncio.to_thread(_subject_health_sync, subject) for subject in subjects)
    )
    subject_state = dict(zip(subjects, checks))
    available_count = sum(bool(item["available"]) for item in checks)
    if available_count == len(subjects):
        status, status_code = "ok", 200
    elif available_count:
        # Keep the portal available when one subject can still serve users.
        status, status_code = "degraded", 200
    else:
        status, status_code = "unavailable", 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "service": "test4-unified-search-portal",
            "version": SERVICE_VERSION,
            "subjects": subject_state,
        },
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/v1/{subject}/jobs", status_code=202)
async def create_job(
    subject: str,
    request: Request,
    image: UploadFile = File(...),
    principal_id: str = Depends(require_access),
) -> JSONResponse:
    backend_for_subject(subject)
    try:
        data = await image.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await image.close()
    media_type = validate_upload(data, image.content_type)
    return await _create_job_from_bytes(
        subject,
        request,
        principal_id,
        data,
        media_type,
    )


@app.post("/api/v1/{subject}/jobs/raw", status_code=202)
async def create_raw_job(
    subject: str,
    request: Request,
    principal_id: str = Depends(require_access),
) -> JSONResponse:
    """Hardware-friendly upload accepting the encoded image as the raw body."""

    backend_for_subject(subject)
    content_type = request.headers.get("content-type")
    data = await request.body()
    media_type = validate_upload(data, content_type)
    return await _create_job_from_bytes(
        subject,
        request,
        principal_id,
        data,
        media_type,
    )


@app.get("/api/v1/{subject}/jobs/{job_id}")
async def get_job(
    subject: str,
    job_id: str,
    _principal_id: str = Depends(require_access),
) -> JSONResponse:
    backend_for_subject(subject)
    validate_job_id(job_id)
    try:
        payload = await asyncio.to_thread(_fetch_job_sync, subject, job_id)
        content = sanitize_job(subject, payload, expected_job_id=job_id)
        response = public_json(content)
        if content["status"] not in {"completed", "failed"}:
            response.headers["Retry-After"] = str(content["retry_after_seconds"])
        return response
    except UpstreamFailure as exc:
        raise _upstream_http_exception(exc) from exc


@app.get(
    "/api/v1/{subject}/jobs/{job_id}/images/{filename}",
    include_in_schema=False,
)
async def get_result_image(
    subject: str,
    job_id: str,
    filename: str,
    _principal_id: str = Depends(require_access),
) -> Response:
    backend_for_subject(subject)
    validate_job_id(job_id)
    validate_result_filename(filename)
    try:
        data = await asyncio.to_thread(_fetch_png_sync, subject, job_id, filename)
    except UpstreamFailure as exc:
        raise _upstream_http_exception(exc) from exc
    return Response(
        content=data,
        media_type="image/png",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'inline; filename="{filename}"',
        },
    )

