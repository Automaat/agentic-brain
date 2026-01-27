"""Constants for Brain Interface integration."""

DOMAIN = "brain_interface"

# Config flow
CONF_BRAIN_URL = "brain_url"
CONF_USER_ID = "user_id"
CONF_SESSION_PREFIX = "session_prefix"
CONF_LANGUAGE = "language"

# Defaults
DEFAULT_BRAIN_URL = "http://100.64.0.1:8000"
DEFAULT_SESSION_PREFIX = "ha"
DEFAULT_LANGUAGE = "pl"

# Supported languages
SUPPORTED_LANGUAGES = ["en", "pl"]
