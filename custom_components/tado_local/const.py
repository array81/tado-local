"""Costanti per l'integrazione Tado Local."""

DOMAIN = "tado_local"

CONF_IP_ADDRESS = "ip_address"
CONF_PORT = "port"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_UPDATE_INTERVAL = 30
DEFAULT_PORT = 4407

PLATFORMS = ["climate", "sensor", "binary_sensor"]

# Uniformiamo il produttore per far apparire il logo Tado ufficiale
MANUFACTURER = "Tado"
MASTER_DEVICE = "internet_bridge"

# Mappa per abbellire i nomi dei modelli
MODEL_MAP = {
    "internet_bridge": "Internet Bridge",
    "thermostat": "Smart Thermostat",
    "smart_ac_control": "Smart AC Control",
    "radiator_valve": "Radiator Thermostat",
    "extension_kit": "Extension Kit",
    "zone_control": "Zone Control" # Nome logico per le zone
}

def format_model(raw_model):
    """Formatta il nome del modello (es. smart_ac_control -> Smart AC Control)."""
    if not raw_model:
        return "Unknown Device"
    # Cerca nella mappa, altrimenti sostituisce _ con spazi e mette le maiuscole
    return MODEL_MAP.get(raw_model, raw_model.replace("_", " ").title())