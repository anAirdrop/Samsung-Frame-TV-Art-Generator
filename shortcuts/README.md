# Siri and HomePod Setup

Siri submits a generation job and returns immediately; Frame Art continues on the Raspberry Pi even if the Shortcut closes.

## Before starting

Complete the local Frame Art setup page and save the generated API key. Choose a server URL:

- At home: `http://<your-pi-ip>:8000`
- Away from home: your HTTPS Cloudflare Tunnel hostname

An at-home URL does not expose Frame Art to the internet. iOS may ask for Local Network permission the first time the Shortcut connects.

## Build the Shortcut

1. Open **Shortcuts** and create a shortcut named **Frame Art**.
2. Add **Dictate Text** with the prompt “What should I create?”
3. Add **Choose from Menu**, with one option for each configured room.
4. Under each room option, add **Set Variable** named `room` with the spoken room value, such as `living room`.
5. Add **Get Contents of URL** after the menu:
   - URL: `http://<your-pi-ip>:8000/api/generate`
   - Method: `POST`
   - Header `Authorization`: `Bearer YOUR_FRAME_ART_API_KEY`
   - Header `Content-Type`: `application/json`
   - Request Body: `JSON`
   - `description`: the **Dictated Text** variable
   - `room`: the `room` variable
6. Add **Get Dictionary Value** for `message` from **Contents of URL**.
7. Add **Speak Text** using that message.

Run the Shortcut once from the app to approve microphone and network access. Then say:

> “Hey Siri, Frame Art.”

Siri will ask for the image description and room, then say that creation has started.

## One default TV

For a shorter interaction, omit **Choose from Menu** and put your default room directly in the JSON body. Siri will only ask for the description.

## HomePod

Enable Personal Requests for the HomePod and ensure the paired iPhone and Raspberry Pi are on the same home network. Run the Shortcut successfully on the iPhone before invoking it on HomePod.

## Troubleshooting

- **Invalid bearer token:** Copy the API key exactly and keep the `Bearer ` prefix.
- **Unknown room:** Use a room name or alias from `data/config.yaml`.
- **Could not connect:** Open `http://<your-pi-ip>:8000/healthz` from the iPhone.
- **Works at home but not remotely:** Use an HTTPS tunnel URL rather than the Pi's private address.
- **Job failed later:** Check `docker compose logs frame-art`; public API errors intentionally omit private service details.
