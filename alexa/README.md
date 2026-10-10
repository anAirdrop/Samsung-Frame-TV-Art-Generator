# Alexa Skill Setup

Alexa runs in Amazon's cloud, so it needs a public HTTPS route to the Frame Art agent. Requests are verified using Alexa's request-signing certificates; generation is placed into the same durable queue used by Siri.

## 1. Complete local setup

Install Frame Art, open `http://<your-pi-ip>:8000`, pair the TV, and confirm that the first test image appears.

## 2. Create a stable HTTPS endpoint

The recommended option is a named Cloudflare Tunnel:

1. In Cloudflare Zero Trust, create a tunnel and copy its token.
2. Add the token to `.env` as `CLOUDFLARE_TUNNEL_TOKEN`.
3. Give the tunnel a public hostname and point its service to `http://localhost:8000`.
4. Start the optional Compose profile:

```bash
docker compose --profile tunnel up -d
```

Confirm that `https://your-hostname.example/healthz` returns `{"status":"ok"}`. Keep port 8000 closed on your router; Cloudflare Tunnel makes an outbound connection and does not require port forwarding.

## 3. Create the skill

1. Open the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask).
2. Select **Create Skill**.
3. Name it **Frame Art**.
4. Choose **Custom**, **Provision your own**, and **Start from Scratch**.
5. Under **Interaction Model → JSON Editor**, paste `alexa/skill.json` from this repository.
6. Edit the `ROOM_LIST` values and synonyms to match the rooms in `data/config.yaml`.
7. Select **Save Model**, then **Build Model**.

Copy the Skill ID shown in the console (it starts with `amzn1.ask.skill.`), add
it to the agent's secrets file, and restart the service:

```bash
nano data/.env
# Set ALEXA_SKILL_ID=amzn1.ask.skill.YOUR-SKILL-ID, save, and exit.
docker compose restart frame-art
```

Frame Art rejects Alexa traffic until this ID is configured, and the Alexa SDK
then verifies that signed requests belong to your specific skill.

The interaction is intentionally two turns. Alexa's `AMAZON.SearchQuery` phrase slot cannot appear in the same sample utterance as the room slot.

## 4. Configure the endpoint

1. Open **Endpoint** and select **HTTPS**.
2. Set **Default Region** to `https://your-hostname.example/api/alexa`.
3. Select **My development endpoint has a certificate from a trusted certificate authority**.
4. Save the endpoint.

## 5. Test

Enable **Development** testing and say:

> “Alexa, ask Frame Art to make an image of a mountain lake at sunrise.”

Alexa asks which room. Reply:

> “The living room.”

Alexa confirms that the request is queued. The durable worker continues after the voice session ends and recovers queued work after a service restart.

## Personal use and publishing

A development skill works for Alexa devices linked to the Amazon developer account and does not need certification. Making one shared public skill for unrelated installations requires account linking and a hosted relay that can route each account to its home agent. This repository deliberately keeps the first release self-hosted and does not operate such a relay.

## Troubleshooting

- **Skill build rejects phrase slots:** Re-paste the current `alexa/skill.json`; no sample should contain both `imageDescription` and `roomName`.
- **Endpoint unavailable:** Verify the tunnel container and public `/healthz` URL.
- **Unknown room:** Keep `ROOM_LIST` aligned with `data/config.yaml`.
- **Alexa confirms but no image appears:** Check `docker compose logs frame-art` and the authenticated `/api/jobs` status when available.
- **Signature verification fails:** Confirm the endpoint is exactly `/api/alexa` and that no proxy rewrites the Alexa signature headers.
- **Alexa is not configured:** Check `ALEXA_SKILL_ID` in `data/.env`, then restart the container.
