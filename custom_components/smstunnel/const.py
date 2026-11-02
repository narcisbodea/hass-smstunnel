"""Constants for the SMSTunnel integration."""

DOMAIN = "smstunnel"

CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_RECIPIENTS = "recipients"
CONF_DEFAULT_COUNTRY_CODE = "default_country_code"
CONF_DEVICE_ID = "device_id"

DEFAULT_BASE_URL = "https://smstunnel.io"
DEFAULT_NAME = "SMSTunnel"

# hass.data[DOMAIN][entry_id]: configuratia intrarii si serviciul notify
# creat din ea (scos la stergerea intrarii, in async_unload_entry).
DATA_CONFIG = "config"
DATA_SERVICE = "service"

# Endpoints ale API-ului public SMSTunnel
PATH_SEND = "/api/v1/sms/send"
PATH_USAGE = "/api/v1/account/usage"

# Limita API-ului: 1600 de caractere (10 SMS-uri concatenate).
# Taiem inainte de trimitere, ca sa nu pierdem mesajul pe o eroare de validare.
MAX_MESSAGE_LENGTH = 1600

REQUEST_TIMEOUT = 20
