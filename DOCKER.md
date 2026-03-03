# 🐳 Tado Local: Docker Setup Guide

This guide provides a step-by-step walkthrough to Dockerize [TadoLocal](https://github.com/ampscm/TadoLocal). It addresses common issues regarding **data persistence** (pairing data) and **web interface loading** (static files) by using a specific volume and execution strategy.

### 📋 Prerequisites
* Docker and Docker Compose installed.
* Tado Bridge **IP Address**.
* Tado Bridge **PIN** (printed on the sticker of the device).
* A Linux host (recommended for `network_mode: host` support).

---

## 1. Get the Code

Clone the repository or download the source code to your machine.

```bash
git clone https://github.com/AmpScm/TadoLocal.git
cd TadoLocal

```

---

## 2. Create the Dockerfile

Create a file named `Dockerfile` in the project root.
This configuration uses the **Editable Install** (`-e`) strategy. This ensures that the Python application can correctly locate the `static` HTML/JS files within the container structure.

**File:** `Dockerfile`

```dockerfile
FROM python:3.11-slim

# Set the source code directory
WORKDIR /app

# --- Data & Configuration Paths ---
# Force the application to treat /data as its home for config/cache
RUN mkdir -p /data
ENV HOME=/data
ENV XDG_CONFIG_HOME=/data
ENV XDG_DATA_HOME=/data
ENV XDG_CACHE_HOME=/data

# Python optimizations
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy source code
COPY . .

# --- Installation ---
# Use the '-e' flag (Editable). This creates a link to the source code 
# in /app, ensuring the 'static' folder is immediately visible to the app.
RUN pip install --no-cache-dir -e .

# Define the volume for persistence
VOLUME ["/data"]

# Entrypoint
ENTRYPOINT ["tado-local"]

```

---

## 3. Build the Image

Build the Docker image locally:

```bash
docker build -t tado-local .
```

---

## 4. Configure Docker Compose

Create a `docker-compose.yml` file.
This configuration solves the "Database vs. Interface" conflict by splitting the **working directory** (where data is written) from the **source directory** (where code is read).

**File:** `docker-compose.yml`

```yaml
services:
  tado-local:
    container_name: tado-local
    image: tado-local
    build: .
    restart: unless-stopped
    
    # ⚠️ CRITICAL: 'host' mode is required for mDNS discovery and Bridge communication
    network_mode: host
    
    # Map a local folder to persist pairing data
    volumes:
      - ./tado_data:/data
    
    # --- FIX FOR PERSISTENCE & UI ---
    # 1. working_dir: Forces the app to write the database file into the mounted /data volume
    working_dir: /data
    
    # 2. PYTHONPATH: Tells Python to look for the source code (and static files) in /app
    environment:
      - PYTHONPATH=/app
      # Replace with your actual Bridge details
      - TADO_BRIDGE_IP=192.168.XXX.XXX
      - TADO_PIN=XXX-XX-XXX
    
    # Startup command
    command: ["--bridge-ip", "192.168.XXX.XXX", "--pin", "XXX-XX-XXX"]

```

> **Note:** Replace `192.168.XXX.XXX` and `XXX-XX-XXX` with your actual Bridge IP and PIN.
---

## 5. First Run & Pairing

### Step 1: Prepare the Data Directory

Create the folder where the database will be stored.

```bash
mkdir -p tado_data
```

### Step 2: Start the Container

Run the container in detached mode.

```bash
docker compose up -d tado-local
```

### Step 3: Authenticate with Tado Cloud

On the very first run, you need to authorize the application:
1. Access the web interface from the address: http://localhost:4407.
2. You will find a link to authorize TadoLocal in the Tado cloud.
3. Authorize with your Tado account.

**NOTE: For reasons unknown to me, after authenticating, you need to stop the Docker container and then restart it**
```bash
docker compose down tado-local
docker compose up -d tado-local
```

---

## 6. Access the Web Interface

Once the pairing is complete, the web interface is available at:

👉 **http://localhost:4407**

**Troubleshooting the UI:**
If you see a blank page or JSON errors after updating, **Force Refresh** your browser to clear the cache:

* **Windows/Linux:** `CTRL` + `SHIFT` + `R`
* **Mac:** `CMD` + `SHIFT` + `R`

---

## 📦 Transferring the Image (Optional)

If you need to move this image to another machine (e.g., a server) without rebuilding it:

**1. Export on Source Machine:**

```bash
docker save -o tado-local.tar tado-local

```

**2. Import on Destination Machine:**

```bash
docker load -i tado-local.tar

```
