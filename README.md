# Tado Local - Home Assistant Integration

![Tado Local](https://img.shields.io/badge/Tado-Local_Control-blue.svg)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Compatible-green.svg)
![IoT Class](https://img.shields.io/badge/IoT_Class-Local_Push-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🚀 Introduction
This custom integration for **Home Assistant** allows you to interface completely locally with your Tado devices via the [TadoLocal](https://github.com/ampscm/TadoLocal) bridge.

Unlike the standard integration, **this component does not rely on Tado Cloud**. It communicates directly with the local bridge service to retrieve status and send commands. This ensures instant updates, works without an internet connection, and avoids any API rate limits.

## ✨ Features
- **100% Local Control**: No cloud dependency, no API polling limits.
- **Instant Updates (Local Push)**: Uses Server-Sent Events (SSE) to update Home Assistant the moment a change occurs (e.g., window open, manual adjustment).
- **Smart Defaults**:
  - `OFF` (0°C): Turns off the heating.
  - `AUTO` (-1°C): Returns to the Tado smart schedule.
  - `HEAT`: Sets a manual target temperature.
- **Detailed Sensors**:
  - **Climate**: Thermostat control for every zone.
  - **Sensors**: Humidity levels and Serial Numbers for devices.
  - **Binary Sensors**: Heating Active status and Low Battery warnings.
- **Device Discovery**: Automatically maps physical devices (Thermostats, Valves) and logical Zones.
- **Multi-Language**: Fully localized in English and Italian.

## 🛠 Prerequisites
Before installing this integration, you **must** have the **TadoLocal** service running on your network (e.g., via Docker).
If you want to use Docker here you can find a simple guide: [DOCKER GUIDE](/DOCKER.md).
This integration connects to the TadoLocal API (usually on port `4407`).

## 🛠 Installation

### 1️⃣ Install via HACS (Recommended)
1. Open Home Assistant and install [HACS](https://hacs.xyz/).
2. Go to **HACS** → **Integrations** → **Add Custom Repository**.
3. Enter the repository URL: `https://github.com/array81/tado-local`.
4. Click **Install** and restart Home Assistant.
5. Navigate to **Settings** → **Devices & Services** → **Add Integration** → Search for **Tado Local**.
6. Enter your TadoLocal ip and port.

### 2️⃣ Manual Installation
1. Download the latest release from [GitHub Releases](https://github.com/array81/tado-local/releases).
2. Extract the `tado_local` folder into `config/custom_components/` in your Home Assistant directory.
3. Restart Home Assistant.
4. Add the integration via **Settings** → **Devices & Services**.

## ⚙️ Configuration
During the setup, you will be asked for:

- **IP Address**: The IP address where the `ampscm/TadoLocal` service is running.
- **Port**: The port of the service (Default: **4407**).
- **Update Interval**: Fallback polling interval in seconds (Default: **30s**). *Note: The integration primarily uses Push updates, so this is just a backup.*

## 📚 Entities & Attributes

| Entity Type | Name Example | Description |
|:---|:---|:---|
| **Climate** | `climate.ground_floor` | Controls target temperature and mode (Heat/Off/Auto). |
| **Sensor** | `sensor.ground_floor_humidity` | Current humidity percentage in the room. |
| **Sensor** | `sensor.tado_ru123456...` | Displays the device serial number. |
| **Binary Sensor** | `binary_sensor.ground_floor_heating_active` | `On` when the valve is open/requesting heat. |
| **Binary Sensor** | `binary_sensor.tado_ru123456_battery` | `On` when the device battery is **Low**. |

### Smart Control Logic
The integration implements specific logic to map Home Assistant modes to Tado API:
- **Set to OFF**: Sends `0` to the API (Valve closed).
- **Set to AUTO**: Sends `-1` to the API (Resumes Schedule).
- **Set Temperature**: Sends the target temperature and switches to Manual Mode.

## 🤝 Contributing
Contributions are welcome!
- **Bug Reports**: Please include logs from Home Assistant.
- **Translations**: Help us translate `strings.json` into more languages.

## ☕ Support & Credits
This integration is a frontend for the amazing work done by [ampscm](https://github.com/ampscm/TadoLocal).

## 📜 License
This project is licensed under the MIT License.

## 📌 Changelog

### v1.0.3
- **New**: Change settings after first configuration.
- **Improved**: Added temperature and target temperature sensors.

### v1.0.2
- **Fixed**: Correct parsing of Serial Numbers and Battery status from `/devices` endpoint.
- **Improved**: Added correct manufacturer icons and standardized model names.

### v1.0.1
- **New**: Added support for Humidity, Battery, and Heating Active sensors.
- **New**: Multi-language support (IT/EN).

### v1.0.0
- Initial Release with Local Push (SSE) support.
