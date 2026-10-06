# live-diagram · 살아있는 아키텍처 다이어그램

[English](../README.md) | [简体中文](zh-CN.md) | [日本語](ja.md) | **한국어** | [Español](es.md) | [Português](pt-BR.md) | [Русский](ru.md)

> **JSON 설정 파일 하나**로 레이아웃이 고정된 "항상 실행 중인" 아키텍처 다이어그램을 생성: 선을 흐르는 패킷, 스크롤되는 로그, 바뀌는 게이지, 차례로 점등되는 알람. **H.264 mp4**(X / 샤오홍슈 / 틱톡 / 빌리빌리) 또는 **브라우저에서 바로 열리는 라이브 웹 페이지**로 출력합니다. [AI 에이전트 스킬](../SKILL.md)로도 사용 가능.

![preview](../docs/media/memory-vault-panel.webp)

*루프 재생: 이 스킬로 렌더링한 AI Memory Vault 라이브 패널(GitHub 다크 테마, 수치는 예시).*

## 핵심 개념

[ythx-101/live-panel-skill](https://github.com/ythx-101/live-panel-skill)의 **방법론**을 참고해 코드는 모두 독자 구현:

- **레이아웃은 움직이지 않고, 움직이는 것은 시스템 상태** — 어떤 프레임을 잘라도 완성된 다이어그램.
- **결정론적 렌더링** — `window.seek(t)`; 모든 변화는 `t`의 순수 함수(시계·난수·CSS 애니메이션 미사용). 프레임 재현·검증 가능.
- **모든 곳에서 하나의 진실** — 로그는 상태 머신이 자동 생성, 화면의 숫자는 서로 일치.
- **실데이터가 없으면 "예시"로 표기**.

## 테마 (`theme.preset`)

`github-dark` / `github-light`(GitHub 공식 팔레트) · `blueprint`(청사진 스타일) · `terminal-dark`(터미널 스타일) · `light-pastel`(파스텔 인포그래픽). 캔버스: `4:5` / `3:4` / `1:1` / `9:16` / `16:9`.

## 사용법

필요 환경: Python 3.8+(표준 라이브러리만), Chrome/Chromium/Edge, ffmpeg.

```bash
python scripts/livediagram.py render --config my.json --out my.mp4 --html-out my.html --crf 10 --preset slow
python scripts/livediagram.py check  --config my.json --out-dir frames --repeat
python scripts/livediagram.py build  --config my.json --out page.html
```

AI 스킬로 사용: 이 폴더를 에이전트의 skills 디렉터리(`~/.zcode/skills/` 등)에 넣기만 하면 됩니다.

## 문서

[SKILL.md](../SKILL.md)(워크플로) · [motion-grammar.md](../references/motion-grammar.md)(모션 문법) · [config-schema.md](../references/config-schema.md)(설정 레퍼런스) · [예제](../examples/rag-pipeline/). 자세한 내용은 [영어 README](../README.md)와 [중국어 README](zh-CN.md)를 참고.

## 라이선스

[MIT](../LICENSE) · 모션 문법 출처: [@thedelost](https://x.com/thedelost) 클립(독자 구현, 코드 미사용).
