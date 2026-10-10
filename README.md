# Frame Art

Create AI artwork with your voice and display it in Art Mode on a Samsung Frame TV.

Frame Art runs on a Raspberry Pi, NAS, or other always-on Docker host on the same network as the TV. Siri Shortcuts and Alexa submit a description, fal.ai generates a 16:9 image, and the local agent prepares and uploads it to the TV.

> Samsung's private Art Mode API varies by model year and firmware. Please report successful and unsuccessful models so the compatibility matrix can grow from verified results.

## What you need

- A Samsung Frame TV with local Art Mode API support
- An always-on Linux Docker host on the same LAN as the TV
- A [fal.ai API key](https://fal.ai/dashboard/keys)
- Siri, Alexa, or the authenticated HTTP API

The default generator is `fal-ai/nano-banana-2` at 4K, 16:9, with JPEG output.

## Install on a Raspberry Pi or Linux server

```bash
mkdir frame-art
cd frame-art
curl -O https://raw.githubusercontent.com/anAirdrop/Samsung-Frame-TV-Art-Generator/main/docker-compose.yml
mkdir data
docker compose up -d
```

The published container supports both `linux/arm64` and `linux/amd64`.

Open `http://<your-pi-ip>:8000` on a device on your home network. The setup page can search for the TV or accept its IP address manually. It will:

1. Ask you to accept Samsung's pairing prompt on the TV.
2. Store the TV token under `./data/tokens`.
3. Store your fal.ai key locally under `./data/.env`.
4. Generate a random API bearer token.
5. Queue a first test image.

The container restarts automatically after a Pi reboot. All durable state is under `./data`, including configuration, pairing tokens, jobs, and IDs of artwork managed by Frame Art.

## Voice assistants

### Siri and HomePod

Siri uses an Apple Shortcut and the authenticated generation API. Follow [the Siri setup guide](shortcuts/README.md).

### Alexa

Alexa requires a custom skill and a public HTTPS endpoint because Alexa runs in Amazon's cloud. Follow [the Alexa setup guide](alexa/README.md).

Alexa is currently the advanced setup path. A single consumer-facing Alexa skill would require a separately operated hosted relay and account-linking service; the open-source agent does not send credentials through a project-owned service.

## Optional Cloudflare Tunnel

Create a named tunnel in Cloudflare Zero Trust and copy its token. Set the token in a local `.env` file:

```bash
cp .env.example .env
# Edit CLOUDFLARE_TUNNEL_TOKEN in .env
docker compose --profile tunnel up -d
```

Configure the tunnel's public hostname to forward to `http://localhost:8000`, then use `https://your-hostname.example/api/alexa` for Alexa and `https://your-hostname.example/api/generate` for remote Siri use.

Do not expose port 8000 directly through router port forwarding. Initial setup only accepts local clients and disables itself after configuration. API documentation is disabled by default.

## API

Frame Art accepts bearer authentication instead of credentials in request bodies.

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Authorization: Bearer YOUR_FRAME_ART_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "a serene mountain landscape at golden hour",
    "room": "living room"
  }'
```

The server immediately returns `202 Accepted`:

```json
{
  "job_id": "9e9225c2-7c33-47a4-b72a-870c21130bf7",
  "status": "queued",
  "message": "Creating art for the living room TV. You can close this shortcut."
}
```

Check durable status with:

```bash
curl -H "Authorization: Bearer YOUR_FRAME_ART_API_KEY" \
  http://localhost:8000/api/jobs/JOB_ID
```

Other routes:

| Route | Authentication | Purpose |
|---|---|---|
| `GET /healthz` | None | Container liveness only |
| `GET /api/status` | Bearer token | Model and TV reachability |
| `POST /api/alexa` | Alexa request signatures | Custom skill endpoint |

Generation is rate-limited per source address. Jobs survive service restarts. Frame Art records content IDs that it uploads and retains the newest 20 per TV by default; it never deletes artwork it did not create.

## Configuration

The setup page writes `data/config.yaml`. Advanced users may edit it while the service is stopped:

```yaml
image:
  fal:
    model: fal-ai/nano-banana-2
    arguments:
      aspect_ratio: "16:9"
      resolution: 4K
      num_images: 1
      output_format: jpeg
      limit_generations: true
  output:
    width: 3840
    height: 2160
    format: JPEG
    jpeg_quality: 95
tvs:
  living_room:
    host: 192.168.1.100
    port: 8002
    token_file: /data/tokens/living_room_token.txt
    aliases: [living room, lounge]
    matte: none
```

Optional Compose settings are documented in `.env.example`. Notifications are disabled by default. If enabling ntfy, use a private, unguessable topic or an authenticated self-hosted server; prompts and errors are included in notifications.

## Updating and backup

```bash
docker compose pull
docker compose up -d
```

Back up the `data` directory. It contains secrets and must not be published or committed.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for compatibility reports and pull requests. Security problems should be reported privately as described in [SECURITY.md](SECURITY.md).

## License

MIT
