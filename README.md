# 해커톤 AI 에이전트

국립창원대 AI Agent 해커톤 TOPIC 01 「부품 불량 사진 분석 AI Agent」 프로젝트입니다.
불량 사진 한 장으로 결함 검출(YOLO) → 정상/의심/이상 판정 → 원인 후보 → 보고서 초안(NCR / 재검사 의뢰서)까지 만들고,
작업자가 확인·확정합니다. 노트북 한 대에서 인터넷 없이 동작합니다 (Ollama + Qwen3 8B).

모든 파일은 [`해커톤 AI에이전트/`](해커톤%20AI에이전트/) 폴더에 있습니다.

| 시작점 | 내용 |
|---|---|
| [README.md](해커톤%20AI에이전트/README.md) | 패키지 안내, 문서 읽는 순서 |
| [docs/04_노트북_세팅_가이드.md](해커톤%20AI에이전트/docs/04_노트북_세팅_가이드.md) | 새 노트북 설치 방법 (Python, 가상환경, 패키지, Ollama) |
| [docs/06_에이전트_구현_기록.md](해커톤%20AI에이전트/docs/06_에이전트_구현_기록.md) | 실행 방법과 구현 기록 |
| [docs/07_프로젝트_소개.html](해커톤%20AI에이전트/docs/07_프로젝트_소개.html) | 소개 슬라이드 (한국어 / Tiếng Việt / English) |
| [docs/08_작업_정리와_완성품_트리.md](해커톤%20AI에이전트/docs/08_작업_정리와_완성품_트리.md) | **작업 정리(덩어리별)와 완성품 트리 · 진행 상태** |

## 실시간 검사 (PCB 가상 컨베이어)
컨베이어 영상을 영상 서버가 읽어 YOLO 로 실시간 검출하고, 센싱 구역에서 판정해 보고서 에이전트로 넘깁니다 (docs/06 19~20번).

| 파일 | 내용 |
|---|---|
| [live/server.py](해커톤%20AI에이전트/live/server.py) | 영상 서버 (포트 8506, `--line pcb\|phone`): 영상 읽기 → 미리보기 검출 → 센싱 구역 판정 → 보고 에이전트·라인 감시 에이전트, 전용 뷰어 |
| [app_live.py](해커톤%20AI에이전트/app_live.py) | 실시간 검사 화면 (포트 8505) |
| [tools/make_conveyor_video.py](해커톤%20AI에이전트/tools/make_conveyor_video.py) | PCB 우수 사례 사진으로 컨베이어 영상 만들기 |
| [videos/pcb_conveyor.json](해커톤%20AI에이전트/videos/pcb_conveyor.json) | 영상 속 기판 순서·위치·정답 라벨 |
| [tools/eval_conveyor.py](해커톤%20AI에이전트/tools/eval_conveyor.py) | 영상 정답과 판정 대조 |

**영상 파일 (`pcb_conveyor.mp4`, 약 420MB)** 은 GitHub 파일 크기 한도(100MB)를 넘어서 Release 에 올렸습니다:
[pcb_conveyor.mp4 내려받기](https://github.com/rlseok/hackathon-ai-agent/releases/download/live-video-v1/pcb_conveyor.mp4) →
`해커톤 AI에이전트/videos/` 에 넣고 `launch_demo.ps1 -App live` 로 실행합니다.
(또는 `python tools/make_conveyor_video.py` 로 직접 다시 만들 수 있습니다 — 약 3분.)

## 올리지 않은 것
- `.venv/` 가상환경: `requirements.txt` 로 다시 설치합니다 (docs/04).
- `outputs/`, `check_output/`: 실행하면 생기는 검사 대장·보고서·확인 이미지입니다.
- `videos/pcb_conveyor.mp4`: 위 Release 에서 받습니다.
- 휴대폰 표면 데이터셋·우수 사례 사진·모델: 원본(PKU-Market-Phone) 라이선스를 확인하지 못해 공개 저장소에 올리지 않았습니다.

## 데이터 출처
학습 데이터는 Roboflow 공개 데이터셋(CC BY 4.0)입니다. 자세한 출처는 `reference/datasets/` 의 README 파일에 있습니다.
