"""
Alerting v1: posts a Slack message via an incoming webhook when the
detector finds a new anomaly.

Deliberately fails soft: a broken/missing webhook should never take down
the detection loop itself - detecting anomalies matters more than
notifying about them, so a notification failure is logged and swallowed,
not raised.
"""

import logging
import os

import requests

log = logging.getLogger("alerts")

SEVERITY_EMOJI = {"medium": ":warning:", "high": ":rotating_light:"}
REQUEST_TIMEOUT_SECONDS = 5


def _format_message(anomaly) -> dict:
    direction = "dropped" if anomaly.actual_value < anomaly.expected_value else "spiked"
    category_label = anomaly.category if anomaly.category else "site-wide"
    emoji = SEVERITY_EMOJI.get(anomaly.severity, ":large_orange_diamond:")

    text = (
        f"{emoji} *{anomaly.severity.upper()} anomaly* on `{anomaly.metric}` ({category_label})\n"
        f"{direction.capitalize()} to *{anomaly.actual_value}* "
        f"(expected ~{anomaly.expected_value}, z-score {anomaly.z_score})\n"
        f"Window: {anomaly.window_start.strftime('%Y-%m-%d %H:%M')} \u2192 "
        f"{anomaly.window_end.strftime('%H:%M')} UTC"
    )
    return {"text": text}


def send_slack_alert(anomaly) -> bool:
    """
    Returns True if the alert was sent successfully, False otherwise
    (including when no webhook is configured at all - that's a valid,
    silent no-op, not an error).
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return False

    payload = _format_message(anomaly)

    try:
        response = requests.post(webhook_url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return True
    except requests.RequestException:
        log.exception("Failed to send Slack alert for %s/%s", anomaly.metric, anomaly.category)
        return False