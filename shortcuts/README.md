# Apple Siri Shortcuts Setup

This guide walks you through creating an Apple Shortcut to generate AI art for your Samsung Frame TV via Siri or HomePod.

## Prerequisites

- iPhone or iPad with the Shortcuts app
- Your Frame TV Art Generator server running and accessible (see the Alexa README for server exposure options)
- Your server's URL and webhook API key (from your `.env` file)

## Creating the Shortcut

### Option A: Two-Step Shortcut (Recommended)

This shortcut asks for the image description and room separately for more reliable results.

1. Open the **Shortcuts** app on your iPhone/iPad
2. Tap **+** to create a new shortcut
3. Name it: **Frame Art**

Add these actions in order:

#### Action 1: Dictate Text
- Search for **"Dictate Text"** and add it
- This captures what you say as the image description

#### Action 2: Choose from Menu
- Search for **"Choose from Menu"** and add it
- Add your rooms as options: `Living Room`, `Bedroom` (match your config.yaml)
- Under each menu item, add a **"Set Variable"** action:
  - Variable name: `room`
  - Value: the room name (e.g., "living room")

#### Action 3: Get Contents of URL
- Search for **"Get Contents of URL"** and add it
- URL: `https://your-domain.com/api/generate`
- Method: **POST**
- Headers: Add `Content-Type` = `application/json`
- Request Body: **JSON**
  - `description`: Select **"Dictated Text"** variable
  - `room`: Select **"room"** variable
  - `api_key`: Enter your webhook API key from `.env`

#### Action 4: Get Dictionary Value
- Search for **"Get Dictionary Value"** and add it
- Key: `message`
- Dictionary: **"Contents of URL"**

#### Action 5: Show Result
- Search for **"Show Result"** and add it
- Input: **"Dictionary Value"**

### Option B: Single Voice Command Shortcut

For a more natural experience where you say everything at once:

1. Create a new shortcut named **Frame Art**
2. Add **"Dictate Text"** action
3. Add **"Get Contents of URL"** action:
   - URL: `https://your-domain.com/api/generate`
   - Method: **POST**
   - Request Body (JSON):
     - `description`: **"Dictated Text"**
     - `room`: Hardcode your default room (e.g., "living room")
     - `api_key`: Your webhook API key
4. Add **"Get Dictionary Value"** (key: `message`)
5. Add **"Show Result"**

To support multiple rooms with a single command, you could add a **"Match Text"** action to parse the room name from the dictated text.

## Usage

Once created, trigger the shortcut by saying:

- **"Hey Siri, Frame Art"** — then follow the prompts
- You can also run it from the Shortcuts app or add it to your Home Screen

### HomePod

The shortcut automatically becomes available on all HomePod devices signed into the same iCloud account. Just say:

- **"Hey Siri, Frame Art"**

## Tips

- **Rename for easier activation**: Name the shortcut something short and distinct, like "Frame Art" or "TV Art"
- **Add to Home Screen**: Long-press the shortcut in the Shortcuts app > Add to Home Screen for quick access
- **Automation**: You can create a time-based automation to change your TV art automatically (e.g., every morning at 8 AM)
- **Widget**: Add the Shortcuts widget to your home screen for one-tap access

## Troubleshooting

- **"Couldn't connect to the server"**: Make sure your server is running and accessible from the internet
- **"Invalid API key"**: Double-check the `api_key` in your shortcut matches `WEBHOOK_API_KEY` in your `.env`
- **"Unknown room"**: Make sure the room name matches an alias in your `config.yaml`
- **Siri doesn't respond**: Try renaming the shortcut to something Siri won't confuse with a built-in command
