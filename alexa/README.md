# Alexa Skill Setup

This guide walks you through setting up the "Frame Art" Alexa skill to generate AI art for your Samsung Frame TV.

## Prerequisites

- An [Amazon Developer account](https://developer.amazon.com/)
- Your Frame TV Art Generator server running and accessible from the internet (see [Exposing Your Server](#exposing-your-server))

## Step 1: Create the Skill

1. Go to the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
2. Click **Create Skill**
3. Skill name: `Frame Art`
4. Choose **Custom** model
5. Choose **Provision your own** for backend
6. Click **Create Skill**
7. Choose **Start from Scratch** template

## Step 2: Set Up the Interaction Model

1. In the left sidebar, click **Interaction Model** > **JSON Editor**
2. Paste the contents of `skill.json` from this directory
3. Customize the `ROOM_LIST` slot type to match your actual rooms/TVs
4. Click **Save Model**
5. Click **Build Model** (takes ~30 seconds)

## Step 3: Configure the Endpoint

1. In the left sidebar, click **Endpoint**
2. Select **HTTPS**
3. In the **Default Region** field, enter: `https://your-domain.com/api/alexa`
4. For the SSL certificate type, select:
   - **"My development endpoint has a certificate from a trusted certificate authority"** if you're using Let's Encrypt, Cloudflare, etc.
   - **"My development endpoint is a sub-domain of a domain that has a wildcard certificate"** if applicable
5. Click **Save Endpoints**

## Step 4: Test the Skill

1. Click **Test** in the top navigation
2. Enable testing in **Development** mode
3. Type or say: `ask frame art to make an image of a sunset for the living room TV`
4. Verify you get a response like: "Got it! I'm generating a sunset for your living room TV..."

## Usage

Once configured, you can use the skill like this:

- "Alexa, tell frame art to make an image of a mountain landscape for the living room TV"
- "Alexa, ask frame art to create a sunset over the ocean for the bedroom TV"
- "Alexa, tell frame art to put a Van Gogh style painting on the bedroom TV"

## Notes

- **No need to publish**: For personal use, keep the skill in "Development" mode. It will work on all Alexa devices linked to your Amazon developer account.
- **8-second timeout**: Alexa has an 8-second response timeout. Since image generation can take 10-15 seconds, the skill responds immediately with "I'm working on it" and sends a push notification (via ntfy.sh) when the image is ready.
- **Room customization**: Edit the `ROOM_LIST` values in `skill.json` to match your actual TV locations. Remember to rebuild the model after changes.

## Exposing Your Server

Your server needs to be reachable from Amazon's cloud. Recommended options:

### Cloudflare Tunnel (Recommended, Free)

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared

# Create tunnel
./cloudflared tunnel login
./cloudflared tunnel create frame-art
./cloudflared tunnel route dns frame-art frame-art.yourdomain.com
./cloudflared tunnel run --url http://localhost:8000 frame-art
```

### Tailscale Funnel (If you use Tailscale)

```bash
tailscale funnel 8000
```

### Caddy Reverse Proxy (If you have a static IP)

```
frame-art.yourdomain.com {
    reverse_proxy localhost:8000
}
```
