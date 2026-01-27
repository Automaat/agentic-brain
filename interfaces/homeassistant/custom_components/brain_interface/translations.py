"""Translation utilities for Brain Interface."""

FALLBACK_MESSAGES = {
    "en": {
        "no_response": "Sorry, I couldn't process that.",
        "connection_error": "Sorry, I'm having trouble connecting to the brain service.",
    },
    "pl": {
        "no_response": "Przepraszam, nie mogłem przetworzyć tego.",
        "connection_error": "Przepraszam, mam problem z połączeniem do usługi brain.",
    },
}


def get_message(language: str, key: str) -> str:
    """Get translated message for given language and key."""
    lang = language if language in FALLBACK_MESSAGES else "en"
    return FALLBACK_MESSAGES[lang][key]
