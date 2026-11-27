#!/usr/bin/env python3
"""영상/음성 파일 분석: 음성 받아쓰기(Whisper, 무료·로컬) + 주요 장면 캡처.

사용법: python3 local_video.py <파일> [--out DIR] [--lang ko|en|auto] [--frames 12] [--model small]
출력: DIR/<파일명>.md (타임스탬프 대본 + 장면 이미지 목록), DIR/<파일명>_frames/*.jpg
장면 이미지는 Read 도구로 열어서 화면 내용을 직접 확인할 것.
"""
import argparse, json, os, subprocess, sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def duration(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path])
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def has_video(path):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=codec_type", "-of", "csv=p=0", path])
    return "video" in r.stdout


def fmt(sec):
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def frames(path, outdir, n, dur):
    """장면 전환 지점 위주로 캡처, 부족하면 균등 간격으로 채움."""
    os.makedirs(outdir, exist_ok=True)
    r = run(["ffmpeg", "-hide_banner", "-i", path, "-vf", "select='gt(scene,0.3)',showinfo", "-vsync", "vfr", "-f", "null", "-"])
    times = [float(l.split("pts_time:")[1].split()[0]) for l in r.stderr.splitlines() if "pts_time:" in l]
    if len(times) > n:  # 너무 많으면 고르게 솎아냄
        step = len(times) / n
        times = [times[int(i * step)] for i in range(n)]
    if len(times) < n and dur > 0:
        extra = [dur * (i + 0.5) / n for i in range(n)]
        times = sorted(set(round(t, 1) for t in times + extra))
        if len(times) > n:
            step = len(times) / n
            times = [times[int(i * step)] for i in range(n)]
    times = sorted(set([0.5 if dur > 1 else 0.0] + times))[: n + 1]
    out = []
    for t in times:
        f = os.path.join(outdir, f"{int(t):05d}s.jpg")
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", path, "-frames:v", "1", "-vf", "scale=960:-2", "-q:v", "4", f])
        if os.path.exists(f):
            out.append((t, f))
    return out


def transcribe(path, lang, model_name):
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    from faster_whisper import WhisperModel
    import numpy as np
    # 오디오는 ffmpeg로 직접 16kHz 모노로 디코딩 (PyAV 버전 호환 문제 회피)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000",
                          "-f", "f32le", "-"], capture_output=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32)
    if audio.size == 0:
        return [], "-"
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segs, info = model.transcribe(audio, language=None if lang == "auto" else lang, vad_filter=True, beam_size=5,
                                 condition_on_previous_text=False, repetition_penalty=1.1)
    return [(s.start, s.text.strip()) for s in segs if s.text.strip()], info.language


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--out", default=".")
    ap.add_argument("--lang", default="auto")
    ap.add_argument("--frames", type=int, default=12)
    ap.add_argument("--model", default="small", help="tiny/base/small/medium (클수록 정확·느림)")
    ap.add_argument("--no-audio", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(a.file):
        sys.exit(f"파일 없음: {a.file}")
    base = os.path.splitext(os.path.basename(a.file))[0]
    os.makedirs(a.out, exist_ok=True)
    dur = duration(a.file)
    md = [f"# {os.path.basename(a.file)}", f"- 길이: {fmt(dur)}", ""]

    if has_video(a.file) and a.frames > 0:
        shots = frames(a.file, os.path.join(a.out, base + "_frames"), a.frames, dur)
        md += ["## 주요 장면 (Read 도구로 열어 확인)"] + [f"- [{fmt(t)}] {f}" for t, f in shots] + [""]

    if not a.no_audio:
        try:
            lines, lang = transcribe(a.file, a.lang, a.model)
            md.append(f"## 대본 (Whisper {a.model}, 언어 {lang})")
            para, start = [], None
            for t, l in lines:
                if start is None:
                    start = t
                if para and t - start >= 30:
                    md.append(f"[{fmt(start)}] " + " ".join(para))
                    para, start = [], t
                para.append(l)
            if para:
                md.append(f"[{fmt(start)}] " + " ".join(para))
            if not lines:
                md.append("(말소리가 감지되지 않음)")
        except Exception as e:
            md.append(f"## 대본\n(받아쓰기 실패: {e})")

    path = os.path.join(a.out, base + ".md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print(path)


if __name__ == "__main__":
    main()
