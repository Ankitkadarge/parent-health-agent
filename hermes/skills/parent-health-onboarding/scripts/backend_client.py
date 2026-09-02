#!/usr/bin/env python3
"""Thin CLI client for the Parent Health Agent production API.

The script serializes arguments into HTTP requests and prints JSON. On HTTP
errors it prints a safe JSON error and exits 1. On connection errors it exits 2.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 40.0


def _base_url() -> str:
    return os.environ.get(
        "PARENT_HEALTH_API_BASE_URL",
        DEFAULT_BASE_URL,
    ).rstrip("/")


def _timeout_seconds() -> float:
    raw = os.environ.get(
        "PARENT_HEALTH_API_TIMEOUT_SECONDS",
        str(DEFAULT_TIMEOUT_SECONDS),
    )
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return min(max(value, 5.0), 60.0)


def _request(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    body: dict | None = None,
) -> dict:
    url = f"{_base_url()}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", "parent-health-hermes/0.2")
    request.add_header("X-Request-ID", str(uuid.uuid4()))
    if data is not None:
        request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(
            request,
            timeout=_timeout_seconds(),
        ) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw_detail = exc.read().decode("utf-8")
        detail: object = raw_detail or "The backend returned an error."
        try:
            parsed = json.loads(raw_detail)
            if isinstance(parsed, dict):
                detail = parsed.get("detail", detail)
        except (json.JSONDecodeError, TypeError):
            pass
        return {
            "error": True,
            "status": exc.code,
            "detail": detail,
        }
    except (urllib.error.URLError, TimeoutError) as exc:
        reason = getattr(exc, "reason", "connection failed")
        return {
            "error": True,
            "detail": f"Could not reach the Parent Health API: {reason}",
        }
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {
            "error": True,
            "detail": "The Parent Health API returned unreadable JSON.",
        }


def cmd_context(args: argparse.Namespace) -> dict:
    return _request(
        "GET",
        "/whatsapp/context",
        params={"phone": args.phone},
    )


def cmd_resolve(args: argparse.Namespace) -> dict:
    return _request(
        "GET",
        "/whatsapp/resolve",
        params={"phone": args.phone},
    )


def cmd_start(args: argparse.Namespace) -> dict:
    return _request(
        "POST",
        f"/families/{args.family_id}/onboarding/start",
    )


def cmd_answer(args: argparse.Namespace) -> dict:
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        return {
            "error": True,
            "detail": "--value must be valid JSON, such as '\"Yes\"' or '\"7 PM\"'.",
        }

    return _request(
        "POST",
        f"/families/{args.family_id}/onboarding/answer",
        body={
            "member_role": args.member_role,
            "key": args.key,
            "value": value,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    context_parser = subparsers.add_parser(
        "context",
        help="Get the required action for a WhatsApp sender.",
    )
    context_parser.add_argument("--phone", required=True)
    context_parser.set_defaults(func=cmd_context)

    resolve_parser = subparsers.add_parser(
        "resolve",
        help="Resolve a sender's stored identity and onboarding state.",
    )
    resolve_parser.add_argument("--phone", required=True)
    resolve_parser.set_defaults(func=cmd_resolve)

    start_parser = subparsers.add_parser(
        "start",
        help="Start onboarding for a verified family.",
    )
    start_parser.add_argument("--family-id", required=True)
    start_parser.set_defaults(func=cmd_start)

    answer_parser = subparsers.add_parser(
        "answer",
        help="Submit the current onboarding answer.",
    )
    answer_parser.add_argument("--family-id", required=True)
    answer_parser.add_argument(
        "--member-role",
        required=True,
        choices=["child", "parent"],
    )
    answer_parser.add_argument("--key", required=True)
    answer_parser.add_argument(
        "--value",
        required=True,
        help="JSON string, for example '\"Yes\"' or '\"7 PM\"'.",
    )
    answer_parser.set_defaults(func=cmd_answer)

    args = parser.parse_args()
    result = args.func(args)
    print(json.dumps(result, indent=2))
    return 1 if result.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
