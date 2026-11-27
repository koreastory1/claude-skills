#!/usr/bin/env python3
"""YouTube 영상의 메타데이터 + 자막(대본)을 가져와 읽기 좋은 마크다운으로 저장.

사용법: python3 youtube.py <URL> [--out DIR] [--lang ko]
출력: DIR/<영상ID>.md  (제목·채널·날짜·길이·설명·챕터·타임스탬프 대본)
자막이 없는 영상이면 exit 2 → local_video.py 로 음성 받아쓰기 필요(오디오 다운로드 가능 환경일 때).
"""
import argparse, html, json, os, re, sys

try:
    import yt_dlp
except ImportError:
    sys.exit("yt-dlp 가 없습니다: pip install yt-dlp")


def pick_track(info, want):
    """수동 자막 > 원어 자동자막 > 원하는 언어 자동번역 순으로 고른다."""
    subs, auto = info.get("subtitles") or {}, info.get("automatic_captions") or {}
    orig = info.get("language") or next((k[:-5] for k in auto if k.endswith("-orig")), None)
    order = []
    for lang in [want, orig, "ko", "en"]:
        if lang and lang not in order:
            order.append(lang)
    for lang in order:  # 사람이 만든 자막
        for k in subs:
            if k == lang or k.startswith(lang + "-"):
                return subs[k], k, "manual"
    if orig:  # 원어 자동자막 (가장 정확)
        for k in (f"{orig}-orig", orig):
            if k in auto:
                return auto[k], k, "auto"
    for lang in order:  # 자동 번역 자막
        if lang in auto:
            return auto[lang], lang, "auto-translated"
    return None, None, None


def vtt_to_lines(vtt):
    """VTT → [(초, 문장)]. 자동자막의 롤링 중복을 제거한다."""
    out, last = [], ""
    for block in vtt.split("\n\n"):
        m = re.search(r"(\d+):(\d+):(\d+)\.\d+ -->", block)
        if not m:
            continue
        t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])
        text_lines = [l for l in block.splitlines()[1:] if "-->" not in l]
        for l in text_lines:
            l = html.unescape(re.sub(r"<[^>]+>", "", l)).strip()
            if l and l != last and not (out and l in out[-1][1][-len(l):]):
                out.append((t, l))
                last = l
    return out


def fmt(sec):
    sec = int(sec or 0)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default=".")
    ap.add_argument("--lang", default="ko", help="선호 자막 언어 (기본 ko)")
    a = ap.parse_args()
    opts = {"skip_download": True, "quiet": True, "no_warnings": True,
            "ignore_no_formats_error": True,  # 영상 파일은 필요 없음 → 봇 차단돼도 자막은 시도
            "js_runtimes": {"node": {}, "deno": {}}}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(a.url, download=False)
        fmts, lang, kind = pick_track(info, a.lang)
        lines = []
        if fmts:
            f = next((x for x in fmts if x.get("ext") == "vtt"), fmts[0])
            vtt = ydl.urlopen(f["url"]).read().decode("utf-8", "replace")
            lines = vtt_to_lines(vtt)

    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, f"{info['id']}.md")
    d = info.get("upload_date") or ""
    md = [f"# {info.get('title')}",
          f"- 채널: {info.get('channel') or info.get('uploader')}",
          f"- 업로드: {d[:4]}-{d[4:6]}-{d[6:]}" if d else "- 업로드: ?",
          f"- 길이: {fmt(info.get('duration'))} · 조회수: {info.get('view_count')}",
          f"- 주소: {info.get('webpage_url')}",
          f"- 자막: {lang} ({kind})" if lang else "- 자막: 없음",
          "", "## 설명", (info.get("description") or "").strip()[:4000], ""]
    if info.get("chapters"):
        md += ["## 챕터"] + [f"- [{fmt(c['start_time'])}] {c['title']}" for c in info["chapters"]] + [""]
    if lines:
        md.append("## 대본 (타임스탬프)")
        para, start = [], lines[0][0]
        for t, l in lines:  # 약 30초 단위로 문단 묶기
            if para and t - start >= 30:
                md.append(f"[{fmt(start)}] " + " ".join(para))
                para, start = [], t
            para.append(l)
        if para:
            md.append(f"[{fmt(start)}] " + " ".join(para))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print(path)
    print(f"자막: {lang} ({kind}), {len(lines)}줄" if lines else "자막 없음")
    sys.exit(0 if lines else 2)


if __name__ == "__main__":
    main()
