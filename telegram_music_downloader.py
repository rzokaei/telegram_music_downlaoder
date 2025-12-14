#!/usr/bin/env python3
"""
Telegram Music Downloader
Downloads all music files from a specified Telegram channel.
Implements sync-based downloading (skips files that already exist).
"""

import os
import sys
import asyncio
import unicodedata
from datetime import datetime
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


def get_timestamp():
    """Get formatted timestamp for log messages."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_print(message):
    """Print message with timestamp."""
    print(f"[{get_timestamp()}] {message}")


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
    # Create base download directory if it doesn't exist
    base_download_path = Path(download_dir)
    base_download_path.mkdir(parents=True, exist_ok=True)
    
    log_print("Connecting to Telegram...")
    await client.start()
    log_print("Connected successfully!")
    
    log_print(f"Fetching messages from channel: {channel_username}")
    
    # Get channel entity
    try:
        entity = await client.get_entity(channel_username)
        channel_title = entity.title
        log_print(f"Channel found: {channel_title}")
    except (ValueError, TypeError) as e:
        log_print(f"Error: Could not find channel '{channel_username}'. Make sure you have access to it.")
        log_print(f"Error details: {e}")
        sys.exit(1)
    
    # Create channel-specific subfolder
    sanitized_channel_name = sanitize_filename(channel_title)
    download_path = base_download_path / sanitized_channel_name
    download_path.mkdir(parents=True, exist_ok=True)
    log_print(f"📁 Download directory: {download_path}")
    
    downloaded_count = 0
    skipped_count = 0
    ignored_count = 0
    error_count = 0
    processed_count = 0
    
    # Load ignore list (from project root, not downloads directory)
    script_dir = Path(__file__).parent.absolute()
    ignore_list = load_ignore_list(script_dir)
    
    # First pass: Count total audio files for progress tracking
    log_print("📊 Counting audio files in channel...")
    total_audio_files = 0
    async for message in client.iter_messages(entity):
        if not message.media:
            continue
        
        # Check if message contains audio (same logic as below)
        is_audio = False
        if message.audio or message.voice:
            is_audio = True
        elif message.document:
            doc = message.document
            is_audio_mime = hasattr(doc, 'mime_type') and doc.mime_type and doc.mime_type.startswith('audio/')
            filename = get_filename_from_document(doc)
            if is_audio_mime or (filename and is_audio_file(filename)):
                is_audio = True
        
        if is_audio:
            total_audio_files += 1
    
    log_print(f"📊 Found {total_audio_files} audio file(s) in channel")
    log_print("="*50)
    
    # Second pass: Download files with progress tracking
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
        
        # Increment processed count and show progress
        processed_count += 1
        progress_pct = (processed_count / total_audio_files * 100) if total_audio_files > 0 else 0
        
        # Sanitize filename
        filename = sanitize_filename(filename)
        file_path = download_path / filename
        
        # Check if file is in ignore list (case-insensitive)
        if filename.lower() in ignore_list:
            original_ignore_name = ignore_list.get(filename.lower(), filename)
            log_print(f"🚫 [{processed_count}/{total_audio_files} ({progress_pct:.1f}%)] Skipping (in ignore list): {original_ignore_name}")
            ignored_count += 1
            continue
        
        # Check if file already exists in channel directory or any subfolder (sync-based download)
        existing_file = file_exists_in_directory(filename, download_path)
        if existing_file:
            # Show relative path if file is in a subfolder
            relative_path = existing_file.relative_to(download_path)
            if str(relative_path) != filename:
                log_print(f"⏭️  [{processed_count}/{total_audio_files} ({progress_pct:.1f}%)] Skipping (already exists in subfolder): {relative_path}")
            else:
                log_print(f"⏭️  [{processed_count}/{total_audio_files} ({progress_pct:.1f}%)] Skipping (already exists): {filename}")
            skipped_count += 1
            continue
        
        # Download the file
        try:
            log_print(f"⬇️  [{processed_count}/{total_audio_files} ({progress_pct:.1f}%)] Downloading: {filename}")
            # Download with the specified filename to preserve original name
            await client.download_media(message, file=str(file_path))
            
            # Verify file was downloaded
            if file_path.exists() and file_path.stat().st_size > 0:
                log_print(f"✅ [{processed_count}/{total_audio_files} ({progress_pct:.1f}%)] Downloaded: {filename}")
                downloaded_count += 1
            else:
                log_print(f"❌ [{processed_count}/{total_audio_files} ({progress_pct:.1f}%)] Download failed (empty file): {filename}")
                if file_path.exists():
                    file_path.unlink()  # Remove empty file
                error_count += 1
        except (OSError, IOError, asyncio.TimeoutError) as e:
            log_print(f"❌ [{processed_count}/{total_audio_files} ({progress_pct:.1f}%)] Error downloading {filename}: {e}")
            error_count += 1
            # Remove partial download if exists
            if file_path.exists():
                file_path.unlink()
    
    # Print summary
    log_print("\n" + "="*50)
    log_print("Download Summary:")
    log_print(f"  📊 Total audio files found: {total_audio_files}")
    log_print(f"  ✅ Downloaded: {downloaded_count}")
    log_print(f"  ⏭️  Skipped (already exists): {skipped_count}")
    log_print(f"  🚫 Ignored (in ignore list): {ignored_count}")
    log_print(f"  ❌ Errors: {error_count}")
    log_print(f"  📁 Total files in directory: {downloaded_count + skipped_count}")
    if total_audio_files > 0:
        completion_pct = ((downloaded_count + skipped_count + ignored_count) / total_audio_files * 100)
        log_print(f"  📈 Completion: {completion_pct:.1f}%")
    log_print("="*50)


def sanitize_filename(filename):
    """Remove invalid characters from filename."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    return filename


def normalize_filename(filename):
    """
    Normalize filename for comparison by:
    1. Converting to lowercase
    2. Normalizing Unicode characters (handles composed/decomposed forms)
    3. Normalizing whitespace
    
    Args:
        filename: Filename to normalize
        
    Returns:
        str: Normalized filename
    """
    # Normalize Unicode to NFC (Canonical Composition) form
    # This handles cases like "é" vs "e" + combining accent
    normalized = unicodedata.normalize('NFC', filename)
    # Convert to lowercase for case-insensitive comparison
    normalized = normalized.lower()
    # Normalize whitespace (replace multiple spaces with single space)
    normalized = ' '.join(normalized.split())
    return normalized


def file_exists_in_directory(filename, directory):
    """
    Check if a file exists in the directory or any of its subdirectories.
    Uses Unicode normalization and case-insensitive comparison to handle special characters.
    
    Args:
        filename: Name of the file to search for
        directory: Directory to search in (Path object)
        
    Returns:
        Path or None: Path to the existing file if found, None otherwise
    """
    if not directory.exists() or not directory.is_dir():
        return None
    
    # Normalize the search filename
    normalized_search = normalize_filename(filename)
    
    # Search recursively in all subdirectories
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            # Try exact match first (faster)
            if file_path.name == filename:
                return file_path
            # Try normalized comparison for special characters
            normalized_existing = normalize_filename(file_path.name)
            if normalized_existing == normalized_search:
                return file_path
    
    return None


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
                log_print(f"📋 Loaded {len(ignore_dict)} file(s) from ignore list")
        except (IOError, OSError) as e:
            log_print(f"⚠️  Warning: Could not read ignore_list.txt: {e}")
    else:
        # Create an empty ignore_list.txt file if it doesn't exist
        try:
            ignore_list_path.touch()
            log_print(f"📋 Created empty ignore_list.txt at {ignore_list_path}")
        except (IOError, OSError) as e:
            log_print(f"⚠️  Warning: Could not create ignore_list.txt: {e}")
    
    return ignore_dict


async def main():
    """Main function to run the downloader."""
    # Validate configuration
    if not API_ID or not API_HASH:
        log_print("Error: API_ID and API_HASH must be set in .env file or environment variables.")
        log_print("Get them from https://my.telegram.org/apps")
        sys.exit(1)
    
    if not CHANNEL_USERNAME:
        log_print("Error: CHANNEL_USERNAME must be set in .env file or environment variables.")
        log_print("Format: '@channelname' or channel ID")
        sys.exit(1)
    
    # Create Telegram client
    client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)
    
    try:
        await download_music_files(client, CHANNEL_USERNAME, DOWNLOAD_DIR)
    except KeyboardInterrupt:
        log_print("\n\nDownload interrupted by user.")
    except (ValueError, TypeError, ConnectionError) as e:
        log_print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

