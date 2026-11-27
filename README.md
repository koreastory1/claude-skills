# claude-skills

내가 쓰는 Claude 맞춤 스킬 모음.

| 스킬 | 하는 일 |
|---|---|
| [video-intel](skills/video-intel/SKILL.md) | 유튜브 링크·영상 파일에서 대본(자막/Whisper 받아쓰기)과 주요 장면을 뽑아 요약·따라하기 정리 |

## 설치

Claude Code 클라우드 환경의 설치 스크립트가 특정 커밋을 받아 `~/.claude/skills/` 에 복사합니다.
수동 설치:

```bash
git clone https://github.com/koreastory1/claude-skills
cp -r claude-skills/skills/* ~/.claude/skills/
pip install yt-dlp faster-whisper   # video-intel 용 (ffmpeg 필요)
```
