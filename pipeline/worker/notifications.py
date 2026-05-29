"""Notification dispatch: email, webhook, browser push."""
from __future__ import annotations

import json
import logging
import smtplib
import os
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def evaluate_and_dispatch(
    session: Session,
    redis_client,
    project_id: str,
    stream_id: str,
    stream_name: str,
    detections: list[dict],
) -> None:
    """Check notification rules and dispatch matching ones."""
    if not detections:
        return

    rules = session.execute(
        text("""
            SELECT id, stream_id, species_filter, min_confidence, channel,
                   destination, cooldown_seconds, last_triggered_at
            FROM notification_rules
            WHERE project_id = :pid AND is_active = true
              AND (stream_id IS NULL OR stream_id = :sid)
        """),
        {"pid": project_id, "sid": stream_id},
    ).fetchall()

    now = datetime.now(timezone.utc)

    for rule in rules:
        if rule.last_triggered_at:
            elapsed = (now - rule.last_triggered_at).total_seconds()
            if elapsed < rule.cooldown_seconds:
                continue

        species_filter = rule.species_filter or []
        min_conf = rule.min_confidence or 0.0

        matching = []
        for det in detections:
            if det["confidence"] < min_conf:
                continue
            if species_filter and det["class_name"] not in species_filter:
                continue
            matching.append(det)

        if not matching:
            continue

        try:
            if rule.channel == "email":
                _send_email(rule.destination, stream_name, matching)
            elif rule.channel == "webhook":
                _send_webhook(rule.destination, stream_id, stream_name, matching)
            elif rule.channel == "browser":
                _send_browser_push(redis_client, project_id, stream_name, matching)

            session.execute(
                text("UPDATE notification_rules SET last_triggered_at = :now WHERE id = :id"),
                {"now": now.isoformat(), "id": rule.id},
            )
            session.commit()
            logger.info("Notification sent: %s → %s (%d detections)", rule.channel, rule.destination, len(matching))
        except Exception:
            logger.exception("Failed to send %s notification to %s", rule.channel, rule.destination)


def _send_email(to_address: str, stream_name: str, detections: list[dict]) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        logger.warning("SMTP not configured, skipping email notification")
        return

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("SMTP_FROM_ADDRESS", smtp_user)

    species_list = ", ".join(set(d["class_name"] for d in detections))
    top = detections[0]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"WildSight Detection: {species_list} on {stream_name}"
    msg["From"] = from_addr
    msg["To"] = to_address

    text_body = f"""WildSight Detection Alert

Stream: {stream_name}
Species: {species_list}
Top confidence: {top['confidence']:.0%}
Detections: {len(detections)}
Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
"""

    html_body = f"""<html><body style="font-family:sans-serif;color:#1a1a1a;">
<h2 style="color:#2d7d2d;">WildSight Detection Alert</h2>
<table style="border-collapse:collapse;">
<tr><td style="padding:4px 12px 4px 0;color:#6b7280;">Stream</td><td><b>{stream_name}</b></td></tr>
<tr><td style="padding:4px 12px 4px 0;color:#6b7280;">Species</td><td><b>{species_list}</b></td></tr>
<tr><td style="padding:4px 12px 4px 0;color:#6b7280;">Confidence</td><td>{top['confidence']:.0%}</td></tr>
<tr><td style="padding:4px 12px 4px 0;color:#6b7280;">Count</td><td>{len(detections)}</td></tr>
</table>
</body></html>"""

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        if smtp_user:
            server.login(smtp_user, smtp_pass)
        server.sendmail(from_addr, to_address, msg.as_string())


def _send_webhook(url: str, stream_id: str, stream_name: str, detections: list[dict]) -> None:
    payload = {
        "event": "detection",
        "stream_id": stream_id,
        "stream_name": stream_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "detections": [
            {"species": d["class_name"], "confidence": d["confidence"]}
            for d in detections
        ],
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()


def _send_browser_push(redis_client, project_id: str, stream_name: str, detections: list[dict]) -> None:
    if not redis_client:
        return
    species_list = ", ".join(set(d["class_name"] for d in detections))
    event = {
        "type": "notification",
        "project_id": project_id,
        "title": f"Detection: {species_list}",
        "body": f"{len(detections)} detection(s) on {stream_name}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    redis_client.publish(f"notifications:{project_id}", json.dumps(event))
