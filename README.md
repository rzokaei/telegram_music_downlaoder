# Telegram Music Downloader

A Python script that downloads all music files from a specified Telegram channel. The script implements sync-based downloading, meaning it will skip files that already exist in the download directory.

## Features

- Downloads all audio files from a Telegram channel
- Supports multiple audio formats (MP3, M4A, FLAC, WAV, OGG, Opus, AAC, WMA)
- Sync-based downloading (skips existing files)
- Handles audio messages, voice messages, and audio documents
- Progress tracking with download summary

## Prerequisites

- Python 3.7 or higher
- A Telegram account
- Telegram API credentials (API ID and API Hash)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get Telegram API credentials:**
   - Go to https://my.telegram.org/apps
   - Log in with your phone number
   - Create a new application
   - Copy your `api_id` and `api_hash`

3. **Create and configure the `.env` file:**
   
   The `.env` file is required to store your configuration securely. It keeps sensitive credentials (like your API keys) separate from your code and prevents them from being accidentally committed to version control.
   
   **Why use a `.env` file?**
   - **Security**: Keeps your API credentials out of the source code
   - **Convenience**: Easy to update configuration without modifying code
   - **Privacy**: The `.env` file is excluded from git (see `.gitignore`)
   
   **How to create it:**
   
   Option 1: Copy the example file (if available):
   ```bash
   cp .env.example .env
   ```
   
   Option 2: Create it manually:
   ```bash
   touch .env
   ```
   
   Then edit the `.env` file and add your configuration:
   ```env
   # Telegram API credentials (required)
   # Get these from https://my.telegram.org/apps
   API_ID=your_api_id_here
   API_HASH=your_api_hash_here
   
   # Telegram channel to download from (required)
   # Format: '@channelname' or channel ID (e.g., -1001234567890)
   CHANNEL_USERNAME=@your_channel_name
   
   # Download directory (optional, default: ./downloads)
   DOWNLOAD_DIR=./downloads
   
   # Session file name (optional, default: telegram_music_downloader)
   SESSION_NAME=telegram_music_downloader
   ```
   
   **Important Notes:**
   - Replace `your_api_id_here` with your actual API ID (a number)
   - Replace `your_api_hash_here` with your actual API hash (a string)
   - Replace `@your_channel_name` with the actual channel username (include the `@` symbol) or use the channel ID
   - Do NOT share your `.env` file or commit it to version control
   - The `.env` file is already excluded in `.gitignore` for your safety

## Usage

Run the script:
```bash
python telegram_music_downloader.py
```

On first run, you'll be prompted to:
1. Enter your phone number
2. Enter the verification code sent to your Telegram account
3. Enter your 2FA password (if enabled)

After authentication, a session file will be created, so you won't need to authenticate again on subsequent runs.

## Configuration Options

All configuration is done through the `.env` file. Here's what each variable means:

- **`API_ID`** (required): Your Telegram API ID - a numeric identifier obtained from https://my.telegram.org/apps
- **`API_HASH`** (required): Your Telegram API Hash - a secret string obtained from https://my.telegram.org/apps
- **`CHANNEL_USERNAME`** (required): The channel to download from. Can be:
  - Channel username: `@channelname` (include the `@` symbol)
  - Channel ID: `-1001234567890` (use this if username doesn't work)
- **`DOWNLOAD_DIR`** (optional): Directory where files will be downloaded. Default: `./downloads`
- **`SESSION_NAME`** (optional): Name for the Telegram session file. Default: `telegram_music_downloader`

**Example `.env` file:**
```env
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890
CHANNEL_USERNAME=@music_channel
DOWNLOAD_DIR=./downloads
SESSION_NAME=telegram_music_downloader
```

## How It Works

1. The script connects to Telegram using your credentials
2. It fetches all messages from the specified channel
3. It identifies audio files (audio messages, voice messages, and audio documents)
4. For each audio file:
   - Checks if the file already exists in the download directory
   - If it exists, skips the download
   - If it doesn't exist, downloads the file
5. Displays a summary of downloaded, skipped, and error files

## Supported Audio Formats

- MP3
- M4A
- FLAC
- WAV
- OGG
- Opus
- AAC
- WMA

## Notes

- Make sure you have access to the channel you want to download from
- The script preserves original filenames when available
- Files are saved in the directory specified by `DOWNLOAD_DIR`
- The session file allows you to stay logged in between runs

## Troubleshooting

**Error: Could not find channel**
- Make sure you have access to the channel
- Verify the channel username is correct (include the `@` symbol)
- Try using the channel ID instead of username

**Authentication issues**
- Make sure your API credentials are correct in the `.env` file
- Verify that `API_ID` is a number and `API_HASH` is a string
- Delete the session file (`.session` file) and try again if authentication fails

**Missing `.env` file error**
- Make sure you've created a `.env` file in the project directory
- Verify the file is named exactly `.env` (not `.env.txt` or `env`)
- Check that all required variables (`API_ID`, `API_HASH`, `CHANNEL_USERNAME`) are set

**Download errors**
- Check your internet connection
- Ensure you have enough disk space
- Verify you have permission to write to the download directory

