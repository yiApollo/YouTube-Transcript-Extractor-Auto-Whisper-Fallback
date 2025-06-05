import os
import re
import subprocess
import whisper
import glob
import requests
from tqdm import tqdm
from dotenv import load_dotenv
from urllib.parse import parse_qs, urlparse
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript
from deep_translator import GoogleTranslator

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    print("\u26a0\ufe0f Missing API key. Please check your .env file.")
else:
    print("\u2705 YouTube API key loaded successfully.")

COMBINED_FOLDER = "all_transcripts"
INDIVIDUAL_FOLDER = "individual_transcripts"
SKIPPED_LOG = "skipped.log"
VIDEOS_FOLDER = "video_files"

os.makedirs(COMBINED_FOLDER, exist_ok=True)
os.makedirs(INDIVIDUAL_FOLDER, exist_ok=True)
os.makedirs(VIDEOS_FOLDER, exist_ok=True)

def sanitize_filename(title):
    return re.sub(r'[<>:"/\\|?*]', '', title).strip()

def log_skipped(url, reason):
    with open(SKIPPED_LOG, 'a', encoding='utf-8') as log:
        log.write(f"{url} - {reason}\n")

def get_video_info_from_api(video_id):
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={YOUTUBE_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        items = response.json().get("items", [])
        if items:
            title = items[0]["snippet"]["title"]
            channel_name = items[0]["snippet"]["channelTitle"]
            return title, channel_name
    return None, None

def fetch_video_ids(playlist_url):
    parsed_url = urlparse(playlist_url)
    query_params = parse_qs(parsed_url.query)
    playlist_id = query_params.get("list", [None])[0]
    if not playlist_id:
        raise ValueError("Invalid playlist URL")

    base_url = "https://www.googleapis.com/youtube/v3/playlistItems"
    video_entries = []
    next_page_token = ""
    index = 1

    while next_page_token is not None:
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": 50,
            "pageToken": next_page_token,
            "key": YOUTUBE_API_KEY,
        }
        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch playlist videos: {response.text}")
        data = response.json()
        for item in data["items"]:
            snippet = item["snippet"]
            video_id = snippet["resourceId"]["videoId"]
            title = snippet["title"]
            channel_name = snippet.get("videoOwnerChannelTitle", snippet.get("channelTitle", "Unknown"))
            video_entries.append((video_id, title, channel_name))
            index += 1
        next_page_token = data.get("nextPageToken")
    return video_entries

def generate_transcript_with_whisper(video_id, title, language=None):
    safe_title = sanitize_filename(title)
    output_path_pattern = os.path.join(VIDEOS_FOLDER, f"{safe_title}.*")

    print(f"Downloading '{title}' for transcription...")
    subprocess.run([
        "yt-dlp", f"https://www.youtube.com/watch?v={video_id}",
        "-o", os.path.join(VIDEOS_FOLDER, f"{safe_title}.%(ext)s")
    ])

    matches = glob.glob(output_path_pattern)
    if not matches:
        raise FileNotFoundError(f"Downloaded file for {title} not found.")

    downloaded_file = matches[0]

    print("Generating transcript using Whisper...")
    model = whisper.load_model("base")
    result = model.transcribe(downloaded_file, language=language if language else None, verbose=False)
    os.remove(downloaded_file)

    text = result["text"]
    print("\n\u2705 Whisper transcription complete.")
    return text

def generate_transcript_placeholder(video_id, title):
    print(f"'{title}' does not have a transcript on YouTube.")
    print("Do you want to generate transcription using Whisper? (Y=Yes, A=Yes to all, N=No): ", end='')
    try:
        choice = input().strip().lower()
    except EOFError:
        choice = 'y'

    if not hasattr(generate_transcript_placeholder, "always_use_whisper"):
        generate_transcript_placeholder.always_use_whisper = False

    if choice == 'a':
        generate_transcript_placeholder.always_use_whisper = True
        choice = 'y'

    if choice in ['', 'y', 'yes', 'sim'] or generate_transcript_placeholder.always_use_whisper:
        print("Which language is the video spoken in? (e.g., 'pt', 'en', press Enter to use the original language): ", end='')
        language = input().strip().replace('-', '_').lower() or None
        return generate_transcript_with_whisper(video_id, title, language)
    return "Transcript not available for this video."

def fetch_transcript(video_id, title):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'en'])
        if not transcript:
            raise ValueError("Transcript data is empty")
        text = "\n".join([item['text'] for item in transcript])
        return text
    except TranscriptsDisabled:
        print(f"⚠️ Transcripts are disabled for '{title}'")
    except NoTranscriptFound:
        print(f"⚠️ No transcript found for '{title}' in requested languages (pt, en)")
    except CouldNotRetrieveTranscript:
        print(f"⚠️ Could not retrieve transcript for '{title}'; may be blocked or private")
    except Exception as e:
        print(f"⚠️ Unexpected error fetching transcript for '{title}': {e}")
    return generate_transcript_placeholder(video_id, title)

def save_markdown(title, content, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n{content}\n")

def process_playlist(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    if "list" in query_params:
        video_entries = fetch_video_ids(url)
    elif "v" in query_params:
        video_id = query_params["v"][0]
        title, channel_name = get_video_info_from_api(video_id)
        if not title:
            raise Exception(f"Could not retrieve title for video {video_id}")
        video_entries = [(video_id, title, channel_name)]
    else:
        raise ValueError("Invalid YouTube URL: missing 'v' or 'list' parameter")

    combined_md_path = os.path.join(COMBINED_FOLDER, "transcripts.md")
    with open(combined_md_path, 'w', encoding='utf-8') as combined_file:
        for idx, (video_id, title, channel_name) in enumerate(tqdm(video_entries, desc="Processing videos", unit="video", dynamic_ncols=True), 1):
            content = fetch_transcript(video_id, title)
            indexed_title = f"{idx}. {title} - {channel_name}"
            combined_file.write(f"# \"{indexed_title}\"\n\n{content}\n\n")

            filename = f"{indexed_title}.md"
            filename = sanitize_filename(filename)
            save_markdown(indexed_title, content, os.path.join(INDIVIDUAL_FOLDER, filename))

            # Translate content
            if global_target_lang:
                try:
                    translated = GoogleTranslator(source='auto', target=global_target_lang).translate(text=content)
                    # Replace original content with translated content
                    translated_title = f"{indexed_title} ({global_target_lang})"
                    save_markdown(translated_title, translated, os.path.join(INDIVIDUAL_FOLDER, filename))
                except Exception as e:
                    print(f"⚠️ Failed to translate transcript for {title}: {e}")

if __name__ == "__main__":
    print("Which language do you want the final transcript translated to? (e.g., 'en', 'pt', etc.) or press Enter to use the original language: ", end='')
    global_target_lang = input().strip().lower()
    url = input("Enter the YouTube playlist or video URL: ")
    process_playlist(url)
    print("\u2705 Transcripts saved successfully.")
