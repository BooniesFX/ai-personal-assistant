# A2A Network Testing Guide

This guide covers how to verify the **Butler (Agent Core)** and **Sidecar** connectivity in two scenarios.

## 🟢 Scenario 1: All Local (Local Sidecar + Local Butler)
Use this for development and debugging.

### 1. Start the Butler (Web Server)
Open a terminal and run the Butler's web interface:
```bash
# Terminal 1
uv run run_web.py
```
> The Butler will start at `http://0.0.0.0:8080`.
> It is now listening for agent registrations at `/network/register`.

### 2. Start the Sidecar
Open a **new terminal** and start a Sidecar. We'll use a simple `echo` command for safety:
```bash
# Terminal 2
uv run sidecar/app.py \
    --adapter cli \
    --command "echo [Sidecar-Response]" \
    --port 8001 \
    --butler-url "http://localhost:8080" \
    --name "Local Echo Agent"
```
> You should see logs indicating: `Auto-registration enabled for http://localhost:8080`.

### 3. Verify Registration
Check the Butler logs (Terminal 1). You should see:
`Registered new agent: Local Echo Agent (agent_xxxx...)`

### 4. Test Interaction
You can now test the connection using the verification script:
```bash
# Terminal 3
uv run tests/verify_a2a.py
```
*Note: The verification script defaults to talking to the Sidecar directly. To test the full loop (Butler -> Sidecar), you would typically use the Web UI.*

**To Test via Butler Web UI:**
1. Open `http://localhost:8080`.
2. Type: "Please ask the Local Echo Agent to say hello".
3. The Butler should recognize the intent, call the `dispatch_to_agent` tool, and the Sidecar (Terminal 2) should show activity.

---

## 🔵 Scenario 2: Hybrid (Local Sidecar + Cloud Butler)
Use this to expose your local tools (e.g., local codebase via `ls`/`grep` or local hardware) to a cloud-hosted Butler.

### Prerequisites
- **Cloud Butler**: Running on a public IP (e.g., `1.2.3.4`) or domain (`butler.example.com`).
- **Port 8080**: Must be open on the Cloud instance firewall.

### 1. Start the Sidecar (Locally)
Run the Sidecar on your local machine, pointing to the Cloud URL:
```bash
# Local Terminal
uv run sidecar/app.py \
    --adapter cli \
    --command "claude" \
    --port 8001 \
    --butler-url "http://<CLOUD_IP>:8080" \
    --name "My Local Laptop Agent"
```

### 2. Verify Connection
- **Sidecar Logs**: Should show successful registration (HTTP 200/201 from Cloud).
- **Cloud Logs**: Should show `Registered new agent: My Local Laptop Agent`.

### 3. Test Remote Control
1. Access the Cloud Butler's Web UI (`http://<CLOUD_IP>:8080`).
2. Type: "Ask the Local Laptop Agent to check the time".
3. **Flow**:
   - Cloud Butler -> (HTTP) -> Your Public IP? ❌ **WAIT!**

### ⚠️ Network NAT Warning
If your local laptop is behind a router (NAT), the Cloud Butler **cannot** initiate a connection back to your Sidecar at `http://localhost:8001`.

**Solution: Use a Tunnel Service to expose your local Sidecar to the internet.**

---

## 🟣 Option A: Using Ngrok

[Ngrok](https://ngrok.com/) creates a secure tunnel from a public URL to your local machine.

### Step 1: Install Ngrok
```bash
# macOS (Homebrew)
brew install ngrok

# Or download from https://ngrok.com/download
```

### Step 2: Authenticate (Free Tier)
Create a free account at [ngrok.com](https://ngrok.com/) and get your auth token.
```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

### Step 3: Start the Tunnel
Expose your local Sidecar port (e.g., 8001):
```bash
ngrok http 8001
```
You will see output like:
```
Forwarding   https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:8001
```
Copy the `https://....ngrok-free.app` URL.

### Step 4: Start the Sidecar with Announced URL
```bash
uv run sidecar/app.py \
  --adapter cli \
  --command "echo hello" \
  --port 8001 \
  --butler-url "http://<CLOUD_BUTLER_IP>:8080" \
  --announced-url "https://xxxx-xxxx-xxxx.ngrok-free.app"
```

Now the Cloud Butler knows to reach your Sidecar at the Ngrok URL!

---

## 🟠 Option B: Using Cloudflared (Cloudflare Tunnel)

[Cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) is Cloudflare's tunneling solution. It's free and doesn't require opening ports.

### Step 1: Install Cloudflared
```bash
# macOS (Homebrew)
brew install cloudflare/cloudflare/cloudflared

# Or download from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
```

### Step 2: Quick Tunnel (No Config Needed)
For quick testing without setting up a Cloudflare account:
```bash
cloudflared tunnel --url http://localhost:8001
```
Output will show a temporary URL like:
```
+-------------------------------------------+
| Your quick Tunnel has been created!       |
| https://some-random-words.trycloudflare.com |
+-------------------------------------------+
```
Copy this URL.

### Step 3: Start the Sidecar
```bash
uv run sidecar/app.py \
  --adapter cli \
  --command "claude" \
  --port 8001 \
  --butler-url "http://<CLOUD_BUTLER_IP>:8080" \
  --announced-url "https://some-random-words.trycloudflare.com"
```

### (Optional) Persistent Tunnel via Cloudflare Dashboard
For production, you can create a named tunnel with a stable subdomain:
1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/).
2. Create a Tunnel (e.g., `my-sidecar-tunnel`).
3. Configure the tunnel to point to `http://localhost:8001`.
4. Use the assigned subdomain (e.g., `my-sidecar.example.com`).

---

## 📊 Comparison

| Feature | Ngrok | Cloudflared |
| :--- | :--- | :--- |
| **Free Tier** | Yes (with limits) | Yes (generous) |
| **Custom Domain** | Paid | Yes (with DNS on CF) |
| **Speed** | Good | Excellent (Cloudflare CDN) |
| **Setup** | Easy | Easy |
| **Persistence** | Session-based (free) | Can be persistent |

**Recommendation:** Use **Cloudflared Quick Tunnel** for development (fast, free, no account needed). Use **Ngrok** if you prefer a familiar interface.

---

## 🚀 One-Command Script (Cloudflared)

We provide a convenience script that handles everything automatically:

```bash
./scripts/start_sidecar_with_tunnel.sh \
  --command "echo hello" \
  --butler-url "http://<CLOUD_BUTLER_IP>:8080" \
  --name "My Tunneled Agent"
```

**What it does:**
1. Starts Cloudflared tunnel in the background.
2. Waits for the public URL to be assigned.
3. Starts the Sidecar with the correct `--announced-url`.
4. Cleans up tunnel on exit (Ctrl+C).

**Full Options:**
```
--command      Command for CLI adapter (required for cli)
--butler-url   URL of the Cloud Butler (required)
--port         Local port for Sidecar (default: 8001)
--adapter      cli or openai (default: cli)
--name         Agent display name
```


