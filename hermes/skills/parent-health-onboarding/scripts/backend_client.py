#!/usr/bin/env python3
"""Thin CLI HTTP client for the parent-health-agent backend.

No onboarding logic lives here — it only serializes CLI arguments into HTTP
requests against the FastAPI backend and prints the raw JSON response to
stdout. All decisions (what to ask, how to phrase it, what language to use)
belong to the Hermes skill that calls this script via the `terminal` tool.

Uses only the Python standard library so it runs regardless of what's
installed in Hermes's own Python environment.

Usage:
    python backend_client.py context --phone "+919876543210"
    python backend_client.py start --family-id <uuid>
    python backend_client.py answer --family-id <uuid> --member-role parent \
        --key preferred_language --value '"Hindi"'
    python backend_client.py answer --family-id <uuid> --member-role child \
        --key conditions --value '["Diabetes", "Thyroid"]'

On success, prints the backend's JSON response to stdout and exits 0.
On an HTTP error response, prints {"error": true, "status": <code>, "detail": ...}
to stdout and exits 1. On a connection failure, prints {"error": true,
"detail": "..."} and exits 2.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def _base_url() -> str:
    return os.environ.get("PARENT_HEALTH_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _request(method: str, path: str, *, params: dict | None = None, body: dict | None = None) -> dict:
    url = f"{_base_url()}{path}"
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"

    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        try:
            detail = json.loads(detail).get("detail", detail)
        except (json.JSONDecodeError, AttributeError):
            pass
        return {"error": True, "status": exc.code, "detail": detail}
    except urllib.error.URLError as exc:
        return {"error": True, "detail": f"Could not reach backend at {url}: {exc.reason}"}


def cmd_context(args: argparse.Namespace) -> dict:
    return _request("GET", "/whatsapp/context", params={"phone": args.phone})


def cmd_resolve(args: argparse.Namespace) -> dict:
    return _request("GET", "/whatsapp/resolve", params={"phone": args.phone})


def cmd_start(args: argparse.Namespace) -> dict:
    return _request("POST", f"/families/{args.family_id}/onboarding/start")


def cmd_answer(args: argparse.Namespace) -> dict:
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        return {
            "error": True,
            "detail": (
                f"--value must be JSON (a quoted string or an array of strings), got: {args.value!r}"
            ),
        }

    return _request(
        "POST",
        f"/families/{args.family_id}/onboarding/answer",
        body={"member_role": args.member_role, "key": args.key, "value": value},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    context_parser = subparsers.add_parser("context", help="GET /whatsapp/context")
    context_parser.add_argument("--phone", required=True)
    context_parser.set_defaults(func=cmd_context)

    resolve_parser = subparsers.add_parser("resolve", help="GET /whatsapp/resolve")
    resolve_parser.add_argument("--phone", required=True)
    resolve_parser.set_defaults(func=cmd_resolve)

    start_parser = subparsers.add_parser("start", help="POST /families/{id}/onboarding/start")
    start_parser.add_argument("--family-id", required=True)
    start_parser.set_defaults(func=cmd_start)

    answer_parser = subparsers.add_parser("answer", help="POST /families/{id}/onboarding/answer")
    answer_parser.add_argument("--family-id", required=True)
    answer_parser.add_argument("--member-role", required=True, choices=["child", "parent"])
    answer_parser.add_argument("--key", required=True)
    answer_parser.add_argument(
        "--value",
        required=True,
        help='JSON value: a quoted string (\'"Hindi"\') or array (\'["Diabetes"]\')',
    )
    answer_parser.set_defaults(func=cmd_answer)

    args = parser.parse_args()
    result = args.func(args)
    print(json.dumps(result, indent=2))
    return 1 if result.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())
