# Samsung Frame TV Art Generator

Generate AI art with your voice and display it on Samsung Frame TVs. Speak a command to **Amazon Alexa** or **Apple Siri/HomePod**, and the system generates an image using AI and sets it as your TV's art.

**"Alexa, tell Frame Art to make an image of a Japanese garden at sunset for the living room TV."**

## Features

- **Voice Control** — Works with both Amazon Alexa and Apple Siri/HomePod
- **Configurable fal.ai Models** — Use one fal.ai API key and select the text-to-image model in configuration
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
3. The server generates an image using your selected fal.ai model
4. The image is resized to 3840x2160 (native Frame TV resolution)
5. The image is uploaded to your Samsung Frame TV via WebSocket
6. You get a push notification confirming it's done

## Quick Start

### Prerequisites

- Python 3.11+ or Docker
- A Samsung Frame TV (2019 or newer) on your local network
- A [fal.ai API key](https://fal.ai/dashboard/keys)

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
FAL_KEY=your-fal-key-here
WEBHOOK_API_KEY=your-random-secret      # Shared secret for Siri Shortcuts
```

Edit `config.yaml` with your TV details:
```yaml
image:
  fal:
    model: "fal-ai/nano-banana-2"
    arguments:
      aspect_ratio: "16:9"
      resolution: "4K"
      num_images: 1
      output_format: "jpeg"
      limit_generations: true

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
| `model` | string | No | Override the configured fal.ai model endpoint |

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
  "model": "fal-ai/nano-banana-2",
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
| `FAL_KEY` | Yes | — | fal.ai API key |
| `WEBHOOK_API_KEY` | Yes | — | Shared secret for webhook auth |
| `NTFY_TOPIC` | No | `frame-tv-art` | ntfy.sh notification topic |
| `NTFY_SERVER` | No | `https://ntfy.sh` | ntfy server URL |
| `HOST` | No | `0.0.0.0` | Server bind address |
| `PORT` | No | `8000` | Server port |
| `LOG_LEVEL` | No | `info` | Logging level |

### Application Config (`config.yaml`)

See [config.yaml.example](config.yaml.example) for all options with inline documentation.

### Choosing a fal.ai Model

1. Open the model's API page in the [fal.ai model gallery](https://fal.ai/models).
2. Copy its endpoint ID, such as `fal-ai/nano-banana-2`.
3. Set that value at `image.fal.model` in `config.yaml`.
4. Copy any supported model inputs into `image.fal.arguments`. The application
   always supplies `prompt`, so do not add a second prompt there.

The selected endpoint must be a text-to-image model that returns an `images`
list containing image URLs. You can temporarily override the configured model
with the optional `model` field on `POST /api/generate`; configured arguments
are still sent to the override model, so they must be compatible with it.

## Troubleshooting

| Problem | Solution |
|---|---|
| TV not found / unreachable | Ensure TV is powered on, in Art Mode, and on the same network. Run `python scripts/test_tv_connection.py` |
| Pairing failed | Make sure you accept the popup on the TV within 30 seconds |
| Image generation failed | Check `FAL_KEY`, the model ID, and the arguments supported by that model's fal.ai API page |
| Alexa skill not responding | Verify your server is accessible from the internet and the endpoint URL is correct |
| Siri shortcut fails | Check the webhook URL and API key in the shortcut settings |

## License

MIT
