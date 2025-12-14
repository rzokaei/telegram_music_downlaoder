#!/usr/bin/env python3
"""
Telegram Music Downloader
Downloads all music files from a specified Telegram channel.
Implements sync-based downloading (skips files that already exist).
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient

# Load environment variables
load_dotenv()

# Configuration
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')  # e.g., '@channelname' or channel ID
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', './downloads')
SESSION_NAME = os.getenv('SESSION_NAME', 'telegram_music_downloader')

# Supported audio file extensions
AUDIO_EXTENSIONS = {'.mp3', '.m4a', '.flac', '.wav', '.ogg', '.opus', '.aac', '.wma'}


def is_audio_file(filename):
    """Check if a file is an audio file based on extension."""
    if not filename:
        return False
    ext = Path(filename).suffix.lower()
    return ext in AUDIO_EXTENSIONS


def get_file_extension_from_mime(mime_type):
    """Map MIME type to file extension."""
    mime_to_ext = {
        'audio/mpeg': '.mp3',
        'audio/mp4': '.m4a',
        'audio/x-m4a': '.m4a',
        'audio/flac': '.flac',
        'audio/wav': '.wav',
        'audio/ogg': '.ogg',
        'audio/opus': '.opus',
        'audio/aac': '.aac',
        'audio/x-ms-wma': '.wma',
    }
    return mime_to_ext.get(mime_type, '.mp3')


def get_filename_from_document(doc):
    """Extract original filename from document attributes."""
    if hasattr(doc, 'attributes') and doc.attributes:
        for attr in doc.attributes:
            # Check for DocumentAttributeFilename
            if hasattr(attr, 'file_name') and attr.file_name:
                return attr.file_name
    return None


async def download_music_files(client, channel_username, download_dir):
    """
    Download all music files from the specified Telegram channel.
    
    Args:
        client: TelegramClient instance
        channel_username: Channel username or ID
        download_dir: Directory to save downloaded files
    """
    # Create download directory if it doesn't exist
    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)
    
    print("Connecting to Telegram...")
    await client.start()
    print("Connected successfully!")
    
    print(f"Fetching messages from channel: {channel_username}")
    
    # Get channel entity
    try:
        entity = await client.get_entity(channel_username)
        print(f"Channel found: {entity.title}")
    except (ValueError, TypeError) as e:
        print(f"Error: Could not find channel '{channel_username}'. Make sure you have access to it.")
        print(f"Error details: {e}")
        sys.exit(1)
    
    downloaded_count = 0
    skipped_count = 0
    ignored_count = 0
    error_count = 0
    
    # Load ignore list (from project root, not downloads directory)
    script_dir = Path(__file__).parent.absolute()
    ignore_list = load_ignore_list(script_dir)
    
    # Iterate through all messages in the channel
    async for message in client.iter_messages(entity):
        if not message.media:
            continue
        
        # Check if message contains audio
        is_audio = False
        filename = None
        
        # Check for audio message (message.audio property)
        if message.audio:
            is_audio = True
            audio = message.audio
            # Try to get original filename from document attributes first
            filename = get_filename_from_document(audio)
            
            # If no filename found, try to construct from metadata
            if not filename:
                performer = getattr(audio, 'performer', None)
                title = getattr(audio, 'title', None)
                if performer and title:
                    filename = f"{performer} - {title}.mp3"
                elif title:
                    filename = f"{title}.mp3"
                else:
                    # Last resort: use message ID
                    filename = f"audio_{message.id}.mp3"
        
        # Check for voice message (message.voice property)
        elif message.voice:
            is_audio = True
            # Try to get original filename from document attributes
            filename = get_filename_from_document(message.voice)
            if not filename:
                filename = f"voice_{message.id}.ogg"
        
        # Check for document that might be audio
        elif message.document:
            doc = message.document
            # Check if document has audio mime type
            is_audio_mime = hasattr(doc, 'mime_type') and doc.mime_type and doc.mime_type.startswith('audio/')
            
            # Get original filename from document attributes
            filename = get_filename_from_document(doc)
            
            # Check if it's an audio file by extension or mime type
            if filename and (is_audio_file(filename) or is_audio_mime):
                is_audio = True
            elif is_audio_mime:
                # Audio mime type but no filename - generate one
                is_audio = True
                ext = get_file_extension_from_mime(doc.mime_type)
                filename = f"audio_{message.id}{ext}"
            elif filename and is_audio_file(filename):
                # Has filename with audio extension
                is_audio = True
            else:
                # Not an audio file
                filename = None
        
        if not is_audio or not filename:
            continue
        
        # Sanitize filename
        filename = sanitize_filename(filename)
        file_path = download_path / filename
        
        # Check if file is in ignore list (case-insensitive)
        if filename.lower() in ignore_list:
            original_ignore_name = ignore_list.get(filename.lower(), filename)
            print(f"🚫 Skipping (in ignore list): {original_ignore_name}")
            ignored_count += 1
            continue
        
        # Check if file already exists (sync-based download)
        if file_path.exists():
            print(f"⏭️  Skipping (already exists): {filename}")
            skipped_count += 1
            continue
        
        # Download the file
        try:
            print(f"⬇️  Downloading: {filename}")
            # Download with the specified filename to preserve original name
            await client.download_media(message, file=str(file_path))
            
            # Verify file was downloaded
            if file_path.exists() and file_path.stat().st_size > 0:
                print(f"✅ Downloaded: {filename}")
                downloaded_count += 1
            else:
                print(f"❌ Download failed (empty file): {filename}")
                if file_path.exists():
                    file_path.unlink()  # Remove empty file
                error_count += 1
        except (OSError, IOError, asyncio.TimeoutError) as e:
            print(f"❌ Error downloading {filename}: {e}")
            error_count += 1
            # Remove partial download if exists
            if file_path.exists():
                file_path.unlink()
    
    # Print summary
    print("\n" + "="*50)
    print("Download Summary:")
    print(f"  ✅ Downloaded: {downloaded_count}")
    print(f"  ⏭️  Skipped (already exists): {skipped_count}")
    print(f"  🚫 Ignored (in ignore list): {ignored_count}")
    print(f"  ❌ Errors: {error_count}")
    print(f"  📁 Total files in directory: {downloaded_count + skipped_count}")
    print("="*50)


def sanitize_filename(filename):
    """Remove invalid characters from filename."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    return filename


def load_ignore_list(base_dir):
    """
    Load the list of files to ignore from ignore_list.txt.
    
    Args:
        base_dir: Directory where ignore_list.txt should be located (project root)
        
    Returns:
        dict: Dictionary mapping lowercase filenames to original filenames for case-insensitive matching
    """
    # Ensure base_dir is a Path object
    if isinstance(base_dir, str):
        base_dir = Path(base_dir)
    ignore_list_path = base_dir / 'ignore_list.txt'
    ignore_dict = {}  # Maps lowercase to original for case-insensitive matching
    
    if ignore_list_path.exists():
        try:
            with open(ignore_list_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # Strip whitespace and skip empty lines and comments
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ignore_dict[line.lower()] = line
            if ignore_dict:
                print(f"📋 Loaded {len(ignore_dict)} file(s) from ignore list")
        except (IOError, OSError) as e:
            print(f"⚠️  Warning: Could not read ignore_list.txt: {e}")
    else:
        # Create an empty ignore_list.txt file if it doesn't exist
        try:
            ignore_list_path.touch()
            print(f"📋 Created empty ignore_list.txt at {ignore_list_path}")
        except (IOError, OSError) as e:
            print(f"⚠️  Warning: Could not create ignore_list.txt: {e}")
    
    return ignore_dict


async def main():
    """Main function to run the downloader."""
    # Validate configuration
    if not API_ID or not API_HASH:
        print("Error: API_ID and API_HASH must be set in .env file or environment variables.")
        print("Get them from https://my.telegram.org/apps")
        sys.exit(1)
    
    if not CHANNEL_USERNAME:
        print("Error: CHANNEL_USERNAME must be set in .env file or environment variables.")
        print("Format: '@channelname' or channel ID")
        sys.exit(1)
    
    # Create Telegram client
    client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)
    
    try:
        await download_music_files(client, CHANNEL_USERNAME, DOWNLOAD_DIR)
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user.")
    except (ValueError, TypeError, ConnectionError) as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

