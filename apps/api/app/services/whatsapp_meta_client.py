import logging
import time

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 10.0
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 0.5


class WhatsappMetaSendError(Exception):
    """Raised on any outbound-send failure. `error_code` is a stable,
    internal-only label — never the raw Meta error body, which must never
    reach a WhatsApp user or an uncontrolled log line.
    """

    def __init__(self, error_code: str):
        self.error_code = error_code
        super().__init__(error_code)


def _is_retryable(status_code: int) -> bool:
    # Permanent failures (bad token, bad recipient, policy violation, etc.)
    # come back as 4xx and must never be retried. 5xx and 429 are the
    # transport/provider-side hiccups worth one or two retries for.
    return status_code >= 500 or status_code == 429


def send_text_message(to_phone_e164: str, body: str) -> str:
    """Send a text message via the Meta WhatsApp Cloud API.

    Returns the provider message id on success. Raises WhatsappMetaSendError
    on any failure — callers must show the WhatsApp user a generic message,
    never this exception's details.
    """
    settings.assert_whatsapp_meta_configured()

    url = (
        f"https://graph.facebook.com/{settings.whatsapp_meta_graph_api_version}"
        f"/{settings.whatsapp_meta_phone_number_id}/messages"
    )
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_meta_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone_e164.lstrip("+"),
        "type": "text",
        "text": {"body": body},
    }

    last_error_code = "meta_send_failed"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = httpx.post(
                url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT_SECONDS
            )
        except httpx.TimeoutException:
            last_error_code = "meta_send_timeout"
            logger.warning("Meta send attempt %d timed out", attempt)
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                continue
            raise WhatsappMetaSendError(last_error_code) from None
        except httpx.HTTPError:
            last_error_code = "meta_send_transport_error"
            logger.warning("Meta send attempt %d hit a transport error", attempt)
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                continue
            raise WhatsappMetaSendError(last_error_code) from None

        if response.status_code < 300:
            body_json = response.json()
            messages = body_json.get("messages") or []
            provider_message_id = messages[0]["id"] if messages else ""
            return provider_message_id

        # Never log the response body verbatim — it can contain account
        # metadata. Only the status code is safe to record.
        logger.warning(
            "Meta send attempt %d failed with status %d (body redacted)",
            attempt,
            response.status_code,
        )
        if _is_retryable(response.status_code) and attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
            continue

        error_code = (
            "meta_send_rate_limited"
            if response.status_code == 429
            else "meta_send_permanent_failure"
            if response.status_code < 500
            else "meta_send_provider_error"
        )
        raise WhatsappMetaSendError(error_code)

    raise WhatsappMetaSendError(last_error_code)
