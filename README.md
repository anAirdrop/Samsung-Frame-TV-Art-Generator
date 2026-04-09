# Samsung Frame TV Art Generator

Generate AI art with your voice and display it on Samsung Frame TVs. Speak a command to **Amazon Alexa** or **Apple Siri/HomePod**, and the system generates an image using AI and sets it as your TV's art.

**"Alexa, tell Frame Art to make an image of a Japanese garden at sunset for the living room TV."**

## Features

- **Voice Control** — Works with both Amazon Alexa and Apple Siri/HomePod
- **Multi-Provider AI** — Choose between OpenAI (gpt-image-1), Google Gemini (Imagen), or xAI Grok
- **Multiple TVs** — Support any number of Samsung Frame TVs across different rooms
- **Push Notifications** — Get notified on your phone when the art is ready (via [ntfy.sh](https://ntfy.sh))
- **Self-Hosted** — Runs on your own hardware (Raspberry Pi, NAS, home server, etc.)
- **Docker Ready** — Single `docker compose up` to deploy
- **Simple REST API** — Easy to integrate with any automation system (Home Assistant, IFTTT, etc.)

## How It Works

```
Voice Command → Alexa/Siri → Webhook → AI Image Generation → Resize to 4K → Upload to Samsung TV → Notification
```

1. You speak a command to Alexa or Siri
2. The voice assistant sends the request to your self-hosted server
3. The server generates an image using your chosen AI provider
4. The image is resized to 3840x2160 (native Frame TV resolution)
5. The image is uploaded to your Samsung Frame TV via WebSocket
6. You get a push notification confirming it's done

## Quick Start

### Prerequisites

- Python 3.11+ or Docker
- A Samsung Frame TV (2019 or newer) on your local network
- An API key for at least one image provider ([OpenAI](https://platform.openai.com/api-keys), [Google AI](https://aistudio.google.com/apikey), or [xAI](https://console.x.ai/))

### 1. Clone and Configure

```bash
git clone https://github.com/anairdrop/samsung-frame-tv-art-generator.git
cd samsung-frame-tv-art-generator

# Copy example configs
cp .env.example .env
cp config.yaml.example config.yaml
```

Edit `.env` with your API keys:
```bash
OPENAI_API_KEY=sk-your-key-here        # If using OpenAI
WEBHOOK_API_KEY=your-random-secret      # Shared secret for Siri Shortcuts
```

Edit `config.yaml` with your TV details:
```yaml
image:
  provider: "openai"                    # openai, gemini, or grok

tvs:
  living_room:
    host: "192.168.1.100"               # Your TV's IP address
    aliases: ["living room", "lounge"]
  bedroom:
    host: "192.168.1.101"
    aliases: ["bedroom"]
```

### 2. Pair Your TVs

Each TV needs a one-time pairing. The TV will show a popup — accept it with your remote.

```bash
# Install dependencies first
pip install -r requirements.txt

# Pair each TV
PYTHONPATH=src python scripts/pair_tv.py --host 192.168.1.100 --token-file tokens/living_room_token.txt
PYTHONPATH=src python scripts/pair_tv.py --host 192.168.1.101 --token-file tokens/bedroom_token.txt
```

### 3. Start the Server

**With Docker (recommended):**
```bash
docker compose up -d
```

**Without Docker:**
```bash
PYTHONPATH=src uvicorn frame_art.main:app --host 0.0.0.0 --port 8000
```

### 4. Test It

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "a serene mountain landscape at golden hour",
    "room": "living room",
    "api_key": "your-webhook-api-key"
  }'
```

### 5. Set Up Voice Assistants

- **Alexa**: See [alexa/README.md](alexa/README.md) for Alexa skill setup
- **Siri/HomePod**: See [shortcuts/README.md](shortcuts/README.md) for Apple Shortcuts setup

## API Reference

### `POST /api/generate`

Generate an image and display it on a TV.

| Field | Type | Required | Description |
|---|---|---|---|
| `description` | string | Yes | Image description (what to generate) |
| `room` | string | Yes | Room name matching a TV alias in config |
| `api_key` | string | Yes | Your `WEBHOOK_API_KEY` |
| `provider` | string | No | Override image provider (openai/gemini/grok) |

**Response:**
```json
{
  "status": "success",
  "message": "Image set on Living Room TV",
  "image_description": "a serene mountain landscape at golden hour",
  "tv": "living_room",
  "duration_seconds": 12.4
}
```

### `POST /api/alexa`

Alexa skill endpoint (handles ASK SDK request format). See [alexa/README.md](alexa/README.md).

### `GET /api/health`

Health check with TV reachability status.

```json
{
  "status": "ok",
  "provider": "openai",
  "tvs": {
    "living_room": "reachable",
    "bedroom": "unreachable"
  }
}
```

## Notifications

The server sends push notifications via [ntfy.sh](https://ntfy.sh) when an image is generated (or if it fails).

1. Install the ntfy app on your phone ([iOS](https://apps.apple.com/us/app/ntfy/id1625396347) / [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy))
2. Subscribe to your topic (default: `frame-tv-art`, set in `.env`)
3. You'll get a notification every time art is updated on your TV

## Exposing Your Server

For Alexa and Siri to reach your server, it needs to be accessible from the internet. See [alexa/README.md](alexa/README.md#exposing-your-server) for options (Cloudflare Tunnel, Tailscale Funnel, etc.).

## Configuration

### Environment Variables (`.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | If using OpenAI | — | OpenAI API key |
| `GEMINI_API_KEY` | If using Gemini | — | Google Gemini API key |
| `GROK_API_KEY` | If using Grok | — | xAI Grok API key |
| `WEBHOOK_API_KEY` | Yes | — | Shared secret for webhook auth |
| `NTFY_TOPIC` | No | `frame-tv-art` | ntfy.sh notification topic |
| `NTFY_SERVER` | No | `https://ntfy.sh` | ntfy server URL |
| `HOST` | No | `0.0.0.0` | Server bind address |
| `PORT` | No | `8000` | Server port |
| `LOG_LEVEL` | No | `info` | Logging level |

### Application Config (`config.yaml`)

See [config.yaml.example](config.yaml.example) for all options with inline documentation.

## Troubleshooting

| Problem | Solution |
|---|---|
| TV not found / unreachable | Ensure TV is powered on, in Art Mode, and on the same network. Run `python scripts/test_tv_connection.py` |
| Pairing failed | Make sure you accept the popup on the TV within 30 seconds |
| Image generation failed | Check your API key and provider settings. Try a different provider |
| Alexa skill not responding | Verify your server is accessible from the internet and the endpoint URL is correct |
| Siri shortcut fails | Check the webhook URL and API key in the shortcut settings |

## License

MIT
