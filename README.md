# YouTube-Transcript-Extractor-Auto-Whisper-Fallback
Automatically extract transcripts from YouTube videos or playlists. Uses official captions when available, and falls back to Whisper AI with interactive Y / A / N prompt support. Saves everything as organized .md files.

````markdown
# YouTube Transcript Extractor 📼📝

Extract transcripts from YouTube videos or playlists in Markdown format, with automatic fallback to Whisper AI when subtitles are unavailable.

## 🚀 Features
- Supports YouTube video or playlist URLs
- Uses YouTube's public API for native subtitles
- Falls back to [Whisper](https://github.com/openai/whisper) transcription when needed
- Interactive prompt for Whisper **(Y=Yes, A=Yes to all, N=No)**
- Generates per-video Markdown + consolidated transcript file
- Organized folders: `individual_transcripts`, `all_transcripts`, `video_files`

## ⚙️ Requirements

- Python 3.8+
- `yt-dlp`
- `whisper`
- `youtube_transcript_api`
- `python-dotenv`
- `ffmpeg`

Install dependencies:

```bash
pip install -r requirements.txt
````

Create a `.env` file with your YouTube API key:

```env
YOUTUBE_API_KEY=YOUR_API_KEY
```

## ▶️ Usage

```bash
python extract_transcripts.py
```

Paste a video or playlist link and follow the prompts.

## 📂 Output Structure

* `individual_transcripts/`: `.md` files per video
* `all_transcripts/transcripts.md`: consolidated transcript
* `skipped.log`: videos with no transcription
* `video_files/`: temporary files used by Whisper


