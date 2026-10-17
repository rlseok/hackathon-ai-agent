# 제조 품질 불량 사진 분석 AI Agent — 이전 패키지

국립창원대 AI Agent 해커톤 **TOPIC 01 「부품 불량 사진 분석 AI Agent」** 를 위해
데스크톱(GTX 1060)에서 만든 결함 검출 모델, 결과, 작업 기록, 참고자료를 노트북으로 옮기기 위한 패키지입니다.
노트북에서는 이 패키지만 있으면 **Ollama + Qwen 기반 로컬 에이전트** 개발을 이어갈 수 있습니다.

> 이 폴더는 원본을 **복사**해서 만든 것입니다. 데스크톱의 `defect_agent_project\pcb_agent`, `defect_agent_project\msdd_agent`, `PCB_dataset` 원본은 그대로 남아 있습니다.

---

## 처음 읽는 순서

| 순서 | 문서 | 내용 |
|---|---|---|
| 1 | [docs/01_목표와_배경.md](docs/01_목표와_배경.md) | 무엇을 만들려는지, 왜 이렇게 설계했는지 |
| 2 | [docs/02_작업_기록.md](docs/02_작업_기록.md) | 지금까지 한 작업 전체 (단계별 목적, 결정 이유, 겪은 문제) |
| 3 | [docs/03_성능_결과.md](docs/03_성능_결과.md) | 두 모델의 성능 수치, 강점과 약점 |
| 4 | [docs/04_노트북_세팅_가이드.md](docs/04_노트북_세팅_가이드.md) | **아무것도 없는 노트북**에서 실행 환경 만들기 (Python, YOLO, Ollama, Qwen) |
| 5 | [docs/05_에이전트_개발_가이드.md](docs/05_에이전트_개발_가이드.md) | 에이전트 구조, 개발 순서, 코드 뼈대 |
| 6 | [docs/06_에이전트_구현_기록.md](docs/06_에이전트_구현_기록.md) | **노트북에서 실제로 구현한 것** (agent/, app.py, 실행 방법, 판정 규칙) |
| 참고 | [reference/참고자료_정리.md](reference/참고자료_정리.md) | 해커톤 안내서 요약, 데이터셋 출처·라이선스 |

**노트북 세팅을 끝낸 뒤** 아래 명령으로 모든 것이 동작하는지 한 번에 확인할 수 있습니다 (04 문서 참고).

```
python check_setup.py
```

---

## 폴더 구조

```
defect_agent_package/
├─ README.md                  ← 지금 이 문서
├─ check_setup.py             ← 노트북 설치 확인 + 모델 시험 실행 스크립트
├─ requirements.txt           ← 설치할 파이썬 패키지 목록
│
├─ models/                    ← 에이전트가 쓸 학습 완료 모델
│   ├─ pcb_v2_yolo11s.pt          PCB 결함 검출 모델 (8종, 채택 모델)
│   ├─ pcb_v2_data.yaml           PCB 모델 클래스 이름
│   ├─ msdd_v1_yolo11s_seg.pt     금속 표면 결함 세그멘테이션 모델 (6종)
│   └─ msdd_v1_data.yaml          금속 모델 클래스 이름
│
├─ knowledge/
│   └─ defect_taxonomy_pcb.yaml   PCB 결함별 한글명·심각도·원인·조치 + 판정 기준값 (에이전트 지식베이스)
│
├─ results/
│   ├─ pcb/
│   │   ├─ showcase/              케이스(결함 유형)별 우수 사례
│   │   │   ├─ 00_falsecopper/
│   │   │   │   ├─ 01_….jpg           비교 이미지 (왼쪽 정답 / 오른쪽 예측)
│   │   │   │   ├─ overview.jpg       케이스 모아보기
│   │   │   │   └─ originals/         우수 사례의 **원본 이미지(images)와 라벨(labels)**
│   │   │   └─ … (8개 케이스)
│   │   │   └─ summary.csv            케이스별 순위·점수
│   │   ├─ train_v2/              채택 모델 학습 기록 (results.csv, 그래프)
│   │   ├─ test_eval_v2/          채택 모델 test 평가 (혼동 행렬, PR 곡선)
│   │   ├─ train_v3_ft (미채택)/  추가 데이터 재학습 기록 (비교용)
│   │   ├─ test_eval_v3 (미채택)/
│   │   └─ split_groups.csv       원본 사진별 train/val/test 배정표
│   └─ msdd/
│       ├─ showcase/              (구성 동일, 7개 케이스 중 6개 + 정상)
│       ├─ train_v1/  test_eval_v1/
│       └─ meta.csv               이미지별 부품번호·촬영위치·검사자 OK/NG
│
├─ tools/                     ← 데이터 정리·평가에 쓴 스크립트 (재학습 시 사용)
│   └─ ps1/                       데스크톱에서 쓰던 PowerShell 실행 스크립트 (참고용)
│
├─ reference/                 ← 사용자가 제공한 참고자료
│   ├─ 국립창원대 AI Agent 해커톤 주제 안내.pdf
│   ├─ 참고자료_정리.md
│   ├─ datasets/                  원본 데이터셋 3종의 data.yaml, README (출처·라이선스)
│   └─ label_review/              라벨 검수 때 만든 확인용 이미지
│
└─ docs/                      ← 상세 문서 (01~05)
```

**포함하지 않은 것:** 학습 데이터셋 전체(약 2GB). 에이전트 실행에는 필요 없습니다.
노트북에서 재학습이 필요하면 데스크톱의 `defect_agent_project\pcb_agent\data\pcb_v2`, `defect_agent_project\msdd_agent\data\msdd_v1` 폴더를 따로 복사하세요.
