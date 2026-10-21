# results/ — 결과 폴더 구성

`해커톤 AI에이전트/results` 와 같은 설계로 세 개의 검출 도메인(pcb · msdd · mobile)을 같은 형식으로 맞췄습니다.

```
results/
├─ confusion_matrix_test.xlsx      도메인별 시트 (PCB / Metal Surface / Mobile Surface): 혼동 행렬 + True total·Recall·Missed rate (수식), 신뢰도 0.25 이상 검출 기준
├─ model_metrics_test.xlsx         Summary + 도메인별 시트: 클래스별 P / R / F1 / AP50 / AP50-95 (box, segmentation 은 mask 도), 지연 시간
├─ model_benchmark.csv / .json     모델별 test 성능 (정밀도·재현율·F1·mAP)  ← tools/benchmark_models.py
├─ pcb/  msdd/  mobile/
│   ├─ showcase/                   결함 유형(케이스)별 우수 사례
│   │   ├─ 00_<유형>/ …            비교 이미지 (왼쪽 정답 / 오른쪽 예측), overview.jpg, originals/{images,labels}
│   │   └─ summary.csv             case, images_in_case, perfect_images, perfect_rate, rank, image, score, n_defects
│   ├─ test_eval_<버전>/           test 평가: 혼동 행렬, P/R/F1/PR 곡선 (msdd·mobile 은 Mask 곡선도), val_batch0
│   ├─ train_<버전>/               학습 기록 (pcb, msdd 만 있음 — 아래 참고)
│   ├─ splits.csv                  이미지 → train / val / test, 결함 수       (pcb 는 split_groups.csv, msdd 는 meta.csv 도 함께)
├─ data_audit/                     데이터 점검 (audit_*.json: 누수·중복·라벨 점검, clean_*.json: 정제 결과, viz/: 확인용 그림)
├─ experiments/                    모델 개선 실험: experiments.csv (test 성능 한 줄씩) + 실험별 results.csv / args.yaml
├─ router/                         자동 분류(라우터) 비교·평가 (probe_*.json, big_eval.json)
└─ logs/                           실행 로그 (저장소에는 올리지 않음)
```

## 점수 정의 (showcase)
이미지 점수 = 정답과 예측을 **IoU 0.5, 클래스까지 맞춰** 비교한 F1 (신뢰도 0.25 이상 예측). `perfect_images` = 점수가 1.0 인 이미지 수.
각 케이스는 점수가 높은 순(같으면 결함이 많은 순)으로 6장을 보여 준다. `Normal` 케이스는 정답에 결함이 없는 사진이며, 예측이 없어야 1.0.
원래 `해커톤 AI에이전트/results` 의 우수 사례와 같은 형식이지만 **점수 계산과 선정 방식이 다르므로 같은 사진·같은 숫자가 나오지는 않는다.**

## 재생성
```
python tools/make_results.py [pcb msdd mobile]          # test_eval, showcase, splits.csv
python tools/make_result_workbooks.py [pcb msdd mobile] # confusion_matrix_test.xlsx, model_metrics_test.xlsx
```
학습 데이터(`data/…`)가 필요하다 (저장소에는 없다).

## 없는 것
- **mobile 의 `train_*`**: 모델 `mobile_surface_yolo11s_seg.pt` 를 학습한 기록(results.csv, 곡선)이 이 컴퓨터에 남아 있지 않다. 지어내지 않고 비워 두었다.
- pcb · msdd 의 `train_*` 는 `해커톤 AI에이전트/results` 에 있던 학습 기록을 그대로 복사한 것이다.
