---
name: video-intel
description: Get transcripts, metadata and key frames from YouTube links or uploaded video/audio files, then summarize and extract how-to steps. Use when the user shares a video or asks about one.
---

# Video Intel

Turn a video into text you can reason over, then deliver insight, not just a transcript.

## 1. Get the content

Scripts live next to this file in `scripts/`. Write outputs to the session scratchpad (or a folder the user named).

**YouTube link**
```bash
python3 scripts/youtube.py "<url>" --out <dir> [--lang ko]
```
- Writes `<dir>/<id>.md`: title, channel, date, length, description, chapters, transcript in ~30s paragraphs with `[mm:ss]` stamps.
- Exit 2 = the video has no captions. Exit with an error mentioning "not a bot" = YouTube blocked this cloud machine.
- Either way, **do not try to get around YouTube's blocks** (no cookie tricks, client switching or other evasion). Instead offer the user these options:
  1. Paste the transcript: on YouTube, open the description, tap "스크립트 표시" (Show transcript), and copy it.
  2. Upload the video file and use the local path below.
  3. If a Gemini API key is set up, Gemini can watch public YouTube videos directly.

**Uploaded video/audio file** (mp4, mov, webm, mp3, m4a, wav...)
```bash
python3 scripts/local_video.py <file> --out <dir> [--lang ko|en|auto] [--frames 12] [--model small]
```
- Writes `<dir>/<name>.md`: key-frame list + Whisper transcript, and `<dir>/<name>_frames/*.jpg`.
- **Open the key frames with the Read tool.** Many videos (screen recordings, reels, tutorials) carry most of their meaning on screen, not in speech.
- `--model medium` is more accurate for hard audio but slower (first use downloads the model, ~1.5GB). `small` (~460MB) is the default.
- Long videos: Whisper on CPU runs at roughly real time for `small`. Warn the user before processing anything over ~30 minutes.

**Instagram / TikTok / other login-walled links**: these can't be fetched. Ask the user to save the video and upload the file, or to share screenshots.

## 2. Analyze

Read the whole transcript (and frames) before writing. Default deliverable, in the user's language:

1. **한 줄 요약**: what the video is and who it's for.
2. **핵심 내용**: 5-10 bullets with timestamps `[mm:ss]` so the user can jump to them.
3. **따라 하기**: if the video shows how to do something, give concrete numbered steps with tools, settings, prompts and commands. Fill gaps the video skipped and mark those additions as such.
4. **검증 메모**: claims that look outdated, exaggerated or wrong, and what's really true now (search the web if needed). Separate what the video says from your own judgment.
5. **나에게 적용**: how this applies to the user's situation, if known.

Adjust to the request. If the user asked one question, answer that question first.

## Rules
- Never invent content that isn't in the transcript or frames. If the audio was unclear, say so.
- Transcripts from auto captions and Whisper contain mis-hearings. Fix obvious ones from context and quote carefully.
- Respect copyright. Summarize and quote briefly; don't reproduce whole transcripts unless the user asks for their own file's transcript.

## Setup (if missing)
```bash
pip install -q yt-dlp faster-whisper
```
Needs `ffmpeg`. Network: `www.youtube.com` for YouTube; `huggingface.co` and `us.aws.cdn.hf.co` for the first Whisper model download. Use `HF_HUB_DISABLE_XET=1`, which `local_video.py` sets itself.
