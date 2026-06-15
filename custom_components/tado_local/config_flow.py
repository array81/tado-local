import voluptuous as vol
import aiohttp
import async_timeout
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_IP_ADDRESS,
    CONF_PORT,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_PORT,
)

async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> None:
    """Valida l'input utente tentando una connessione."""
    ip = data[CONF_IP_ADDRESS]
    port = data[CONF_PORT]
    # Usa un endpoint leggero per il test
    url = f"http://{ip}:{port}/api" 
    
    async with aiohttp.ClientSession() as session:
        async with async_timeout.timeout(5):
            # Endpoint generico (visto nel PDF pagina 1)
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception("Status code not 200")
                js = await response.json()
                if js.get("service") != "Tado Local":
                    raise Exception("not_tado_local")


class TadoLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestisce il flusso di configurazione per Tado Local."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Ottiene il flusso delle opzioni."""
        # Passiamo la config_entry al costruttore
        return TadoLocalOptionsFlowHandler(config_entry)

    # -------------------------------------------------------------------------
    # USER STEP (manual setup)
    # -------------------------------------------------------------------------
    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Gestisce il passo iniziale dell'utente."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id("tado_local_server")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Tado Local ({user_input[CONF_IP_ADDRESS]})",  
                    data=user_input
                )

        data_schema = vol.Schema({
            vol.Required(CONF_IP_ADDRESS): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Required(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): int,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    # -------------------------------------------------------------------------
    # ZEROCONF DISCOVERY STEP
    # -------------------------------------------------------------------------
    async def async_step_zeroconf(self, discovery_info) -> FlowResult:
        """Handle mDNS discovery of tado-local."""
        host = discovery_info.host
        port = discovery_info.port or 4407

        # Validate the discovered server
        try:
            url = f"http://{host}:{port}/api"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status != 200:
                        return self.async_abort(reason="cannot_connect")
                    data = await resp.json()
                    if data.get("service") != "Tado Local":
                        return self.async_abort(reason="not_tado_local")
        except Exception:
            return self.async_abort(reason="cannot_connect")

        # Prevent duplicates
        await self.async_set_unique_id("tado_local_server")
        self._abort_if_unique_id_configured()

        # Store discovery info for confirm step
        self._discovered_host = host
        self._discovered_port = port

        return await self.async_step_confirm()

    # -------------------------------------------------------------------------
    # CONFIRMATION STEP
    # -------------------------------------------------------------------------
    async def async_step_confirm(self, user_input=None) -> FlowResult:
        def _is_local_address(ip: str) -> bool:
            import socket
            try:
                host_ips = socket.gethostbyname_ex(socket.gethostname())[2]
                return ip in host_ips
            except Exception:
                return False
        
        display_ip = "localhost" if _is_local_address(self._discovered_host) else self._discovered_host

        """Ask user to confirm adding the discovered server."""
        if user_input is not None:
            return self.async_create_entry(
                title=f"Tado Local ({display_ip})",
                data={
                    CONF_IP_ADDRESS: self._discovered_host,  # keep real IP internally
                    CONF_PORT: self._discovered_port,
                    CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                }
            )

        return self.async_show_form(
                step_id="confirm",
                description_placeholders={
                    "ip": display_ip,
                    "port": self._discovered_port,
                }
            )

# -----------------------------------------------------------------------------
# OPTIONS FLOW
# -----------------------------------------------------------------------------
class TadoLocalOptionsFlowHandler(config_entries.OptionsFlow):
    """Gestisce la riconfigurazione delle opzioni."""

    def __init__(self, config_entry) -> None:
        """Inizializza l'handler delle opzioni."""
        # Usiamo un nome variabile con underscore per evitare conflitti con proprietà interne di HA
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Gestisce le opzioni."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Validiamo anche le modifiche
                await validate_input(self.hass, user_input)
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                # Aggiorna la configurazione esistente
                return self.async_create_entry(title="", data=user_input)

        # Pre-compila i campi con i valori attuali
        # NOTA: Usiamo self._config_entry qui
        current_data = self._config_entry.data
        current_options = self._config_entry.options

        current_ip = current_options.get(CONF_IP_ADDRESS, current_data.get(CONF_IP_ADDRESS))
        current_port = current_options.get(CONF_PORT, current_data.get(CONF_PORT))
        current_interval = current_options.get(CONF_UPDATE_INTERVAL, current_data.get(CONF_UPDATE_INTERVAL))

        options_schema = vol.Schema({
            vol.Required(CONF_IP_ADDRESS, default=current_ip): str,
            vol.Required(CONF_PORT, default=current_port): int,
            vol.Required(CONF_UPDATE_INTERVAL, default=current_interval): int,
        })

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )