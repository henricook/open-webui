import json
import logging
import os

import requests
from open_webui.config import WEBUI_FAVICON_URL
from open_webui.env import SRC_LOG_LEVELS, VERSION

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["WEBHOOK"])


def post_webhook(name: str, url: str, message: str, event_data: dict) -> bool:
    try:
        log.debug(f"post_webhook: {url}, {message}, {event_data}")
        payload = {}

        # Slack and Google Chat Webhooks
        if "https://hooks.slack.com" in url or "https://chat.googleapis.com" in url:
            payload["text"] = message
        # Discord Webhooks
        elif "https://discord.com/api/webhooks" in url:
            payload["content"] = (
                message
                if len(message) < 2000
                else f"{message[: 2000 - 20]}... (truncated)"
            )
        # Microsoft Teams Webhooks
        elif "webhook.office.com" in url:
            action = event_data.get("action", "undefined")
            facts = [
                {"name": name, "value": value}
                for name, value in json.loads(event_data.get("user", {})).items()
            ]
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "0076D7",
                "summary": message,
                "sections": [
                    {
                        "activityTitle": message,
                        "activitySubtitle": f"{name} ({VERSION}) - {action}",
                        "activityImage": WEBUI_FAVICON_URL,
                        "facts": facts,
                        "markdown": True,
                    }
                ],
            }
        # Default Payload
        else:
            payload = {**event_data}

        log.debug(f"payload: {payload}")
        r = requests.post(url, json=payload)
        r.raise_for_status()
        log.debug(f"r.text: {r.text}")
        return True
    except Exception as e:
        log.exception(e)
        return False


def notify_system_prompt_change(model_id: str, model_name: str, old_prompt: str, new_prompt: str, user_id: str, user_name: str) -> bool:
    """
    Send a notification when a model's system prompt is changed.
    
    Args:
        model_id: The ID of the model being updated
        model_name: The name of the model being updated
        old_prompt: The previous system prompt (or None if there wasn't one)
        new_prompt: The new system prompt
        user_id: ID of the user making the change
        user_name: Name of the user making the change
        
    Returns:
        bool: Whether the notification was sent successfully
    """
    webhook_url = os.environ.get("SYSTEM_PROMPT_CHANGE_WEBHOOK_URL")
    if not webhook_url:
        return False
    
    if old_prompt == new_prompt:
        return False  # No change, no notification needed
    
    # Create a message that shows what changed
    if old_prompt:
        message = f"*System Prompt Changed* for model `{model_name}` (`{model_id}`) by {user_name} ({user_id})\n\n"
        message += "*Previous prompt:*\n```\n" + old_prompt + "\n```\n\n"
        message += "*New prompt:*\n```\n" + new_prompt + "\n```"
    else:
        message = f"*System Prompt Added* to model `{model_name}` (`{model_id}`) by {user_name} ({user_id})\n\n"
        message += "*New prompt:*\n```\n" + new_prompt + "\n```"
    
    event_data = {
        "model_id": model_id,
        "model_name": model_name,
        "user_id": user_id,
        "user_name": user_name,
        "action": "system_prompt_change",
        "old_prompt": old_prompt,
        "new_prompt": new_prompt
    }
    
    return post_webhook("Open WebUI", webhook_url, message, event_data)
