# Những thay đổi so với nhánh `main`

Nhánh: `feat/auto-router-rag-data-audit`. Mọi thay đổi đều **tương thích ngược**: các lệnh và tham số cũ (`--domain pcb|msdd`, `analyze()`, giao diện cũ) vẫn chạy như trước; tính năng mới là mặc định mới hoặc tùy chọn.
Dữ liệu huấn luyện (`data/`), log, thư mục chạy huấn luyện (`runs/`) và môi trường ảo **không** được đẩy lên (xem `.gitignore`).
Các domain hiện có: **pcb, msdd (kim loại), mobile (bề mặt điện thoại)**. Domain "dent" (vết lõm thân xe) từng được thử rồi đã **gỡ hoàn toàn** vì là ô tô chứ không phải linh kiện.

## 1. Agent điều phối — tự nhận diện loại linh kiện (`agent/router.py`)
- Gộp ảnh của 3 dataset (pcb, msdd, mobile) thành một bộ phân loại: **DINOv2-small đóng băng + hồi quy logistic**, có ngưỡng từ chối cho ảnh lạ.
- Không tìm được bài báo SOTA riêng cho bài toán này, nên so sánh DINOv2-small/base, CLIP-B/16 và ResNet50 fine-tune (`tools/router_probe.py`, `tools/train_router.py`, `results/router/probe_*.json`). Cả bốn đạt 100% trên tập test và AUROC ≈ 1,0 với ảnh ngoài miền, nên không phân biệt rõ; DINOv2-small được chọn vì nhỏ nhất và chịu được ảnh bị cắt (độ chính xác 1,0 với ảnh cắt giữa).
- Đánh giá lớn hơn (`tools/router_eval_big.py`, `results/router/big_eval.json`):
  - 8.588 ảnh bộ điều phối chưa từng thấy: 0,2% chuyển cho người chọn tay, 99,8% tự đúng, **0 ca sai khi hệ thống tự quyết**.
  - Kiểm tra chéo 5 phần theo nhóm trên 12.381 ảnh: 97,7% tự đúng, 2,3% chuyển người, **0 ca sai**. Theo miền: pcb 99,9%, msdd 91,7%, mobile 88,0%.
  - Ảnh ngoài miền (màn hình giao diện, ảnh kim loại tổng hợp) bị chấp nhận nhầm: 0% và 0%.
- Nối vào pipeline: `domain='auto'` là mặc định (`agent/pipeline.py: pick_domain`). Không chắc → `DomainUncertain` → giao diện hiện hộp hỏi người dùng chọn. Thiếu file router → tự về PCB như cũ. Ảnh để thẳng trong `inbox/` được tự định tuyến, ảnh không chắc chuyển sang `inbox/_unsure/`.
- Giao diện (`ui.py`, `app.py`, `app_chat.py`): thêm lựa chọn "Tự động nhận diện" và mobile (trước đây chỉ có pcb và msdd).
- File: `models/router.joblib`, `models/router_backbone.pt` (≈83 MB), `tools/build_router.py`, `tools/router_data.py`, `해커톤 AI에이전트/tools/router_check.py`.
- **Hạn chế:** mỗi miền chỉ đến từ một dataset; mobile không có thông tin nhóm nên kiểm tra chéo có thể hơi lạc quan; chưa thử ảnh chụp thật ở nhà máy.

## 2. Chọn thiết bị: GPU trước, CPU khi GPU bận (`agent/device.py`)
- Mặc định chạy trên GPU; chỉ lùi về CPU khi GPU hết bộ nhớ trống hoặc đang bị tiến trình khác dùng ≥ 90% công suất. Ép bằng biến môi trường `DEFECT_DEVICE=cpu|cuda`.
- Áp dụng cho bộ điều phối, YOLO trong pipeline (chọn một lần khi nạp mô hình) và RAG. Ollama tự quyết định giữa GPU và CPU.
- Bộ điều phối trên GPU: 5 ms/ảnh so với 42 ms/ảnh trên CPU (≈ 8 lần). Phần đọc ảnh chạy song song để GPU không phải chờ.

## 3. Cắt mảnh (tiling) cho mọi domain (`agent/detect.py`)
- Trước đây chỉ PCB. Nay cửa sổ cắt = kích thước ảnh gốc model đã thấy khi huấn luyện (`NATIVE`: pcb 640, msdd 512, mobile 1920×1080), có hỗ trợ mặt nạ cho model segmentation.
- Kiểm chứng trên ảnh ghép lớn (`tools/tile_eval.py`): mobile 3840×2160 F1 **0,804 → 0,985**.

## 4. RAG: kho tài liệu và truy xuất (`agent/rag.py`, `knowledge/rag/`)
- 6 tài liệu thu thập từ web (Wikipedia CC BY-SA, trang kỹ thuật dạng tóm tắt) cho các lỗi PCB/hàn, kim loại, điện thoại, quy trình NCR/8D. Mỗi file ghi URL, giấy phép; phần kiến thức chung không có trong nguồn được đánh dấu `[general practice]`.
- Embedding đa ngôn ngữ (paraphrase-multilingual-mpnet); nối vào chat (`agent/chat.py`) và vào prompt viết báo cáo (`agent/writer.py`, câu trích dẫn `[S#]`, danh sách nguồn trong báo cáo `agent/report.py`).
- `knowledge/rag/cards.yaml`: thẻ tri thức ngắn ko/vi/en rút từ kho, dùng làm dữ liệu fine-tune.
- **Hạn chế:** mới 6 tài liệu — là bộ khởi đầu, chưa phải kho đầy đủ.

## 5. Chức năng còn thiếu đã bổ sung
- `agent/history.py`: hỏi đáp tra cứu lịch sử kiểm tra bằng tool calling của Qwen (đếm theo ngày/phán định/lô, liệt kê ca đang chờ, tìm ca tương tự). Hàm công cụ đã chạy trên dữ liệu thật trong kiểm thử; **chưa thử với Ollama**.
- `agent/notify.py`: thông báo khi có ca bất thường/nghi ngờ (`outputs/notifications.jsonl`, webhook qua biến môi trường `NOTIFY_WEBHOOK`), gọi từ `pipeline.finalize/register_pending`.
- `tools/autolabel.py` (dán nhãn trước bằng model hiện tại) và `tools/quick_train.py` (huấn luyện nhanh từ ảnh hiện trường, chỉ thay model khi tốt hơn): **chưa chạy thật**.

## 6. Đa ngôn ngữ và fine-tune LLM (chưa hoàn tất)
- `knowledge/translations_vi.yaml`, `translations_en.yaml`: bản dịch nguyên nhân/biện pháp của 17 loại lỗi; `knowledge.localize()` và báo cáo vi/en dùng bản dịch thay vì để Qwen tự dịch. **Chưa được người trong ngành rà soát.**
- `tools/make_sft_data.py`: sinh dữ liệu SFT ko/vi/en (báo cáo JSON + hỏi đáp có trích dẫn nguồn RAG + từ chối): 1.836 mẫu huấn luyện, trong đó 1.809 mẫu đủ ngắn (≤ 2560 token) được dùng. `tools/llm_ft/` (QLoRA Qwen3-8B, gộp trọng số, tạo model Ollama, đánh giá `eval_llm.py`); `tools/queues/*.sh` là các hàng đợi chạy bằng PM2.
- **Trạng thái:** huấn luyện đang chạy lại từ đầu (đã sửa lỗi hết bộ nhớ GPU bằng cách chỉ tính loss ở phần câu trả lời và bỏ việc nâng embedding lên fp32). **Chưa có model fine-tune nào và chưa có số đánh giá.** `writer.MODEL` đọc biến môi trường `DEFECT_LLM` (mặc định vẫn `qwen3:8b`).

## 7. Kiểm toán dữ liệu (`tools/audit_dataset.py`, `tools/clean_dataset.py`) — msdd
- **msdd không rò rỉ giữa các tập** (0% ảnh test có bản sao gần như hệt trong train ở ngưỡng cosine 0,99; phép băm ảnh báo nhầm 55%). Bản sạch (loại nhãn lỗi/trùng): train 1167 / val 143 / test 148.
- Điểm yếu nằm ở nhãn: 37% nhãn Porosity, 24% Oxidation, 19% Fold trong train phủ trên 40% ảnh (trạng thái cả bề mặt chứ không phải một đối tượng). AP50 theo lớp: Stain 0,995, Dark Spot 0,79, Porosity 0,57, Scratch 0,39, Oxidation 0,39, Fold 0,33. Cách gán nhãn được giữ nguyên.
- Tiền xử lý CLAHE (`agent/preprocess.py`, `tools/preprocess_dataset.py`) có sẵn nhưng **không bật** trong pipeline vì không cải thiện rõ.

## 8. Thí nghiệm cải thiện model msdd (kết quả âm — ghi lại để khỏi lặp lại)
Chấm trên test (`results/experiments/experiments.csv`, chạy bằng `tools/train_exp.py`):

| Thí nghiệm | F1 hộp | mAP50 hộp |
|---|---|---|
| model đang dùng (test sạch 148 ảnh) | 0,608 | 0,577 |
| YOLO11m 640px + copy-paste (chấm trên test gốc 150 ảnh, mốc cùng tập: 0,604 / 0,576) | 0,612 | 0,593 |
| dữ liệu sạch (11s) | 0,580 | 0,576 |
| dữ liệu sạch + CLAHE | 0,616 | 0,575 |

Mọi chênh lệch nằm trong khoảng nhiễu (test chỉ ~150 ảnh). **Không thay model nào trong `models/`.** mobile (F1 0,98) và pcb (0,89) giữ nguyên.

## 9. Thư mục `results/` được sắp xếp lại giống `해커톤 AI에이전트/results`
Mỗi domain (pcb, msdd, mobile) có `showcase/` (ảnh so sánh nhãn thật / dự đoán + `summary.csv`), `test_eval_<ver>/` (ma trận nhầm lẫn, đường PR/F1), `splits.csv`; `train_*` có cho pcb và msdd (chép từ gói gốc). Ở trên cùng: `confusion_matrix_test.xlsx` (mỗi domain một sheet), `model_benchmark.*`. Các kết quả mới nằm ở `experiments/`, `data_audit/`, `router/`. Chi tiết: `results/README.md`. Sinh lại bằng `tools/make_results.py`. **mobile không có `train_*`** vì hồ sơ huấn luyện không còn trên máy.

## 10. Kiểm thử
- `해커톤 AI에이전트/tools/smoke_test.py` (không cần Ollama): 19/19 mục qua — cả 3 miền với chỉ định miền trực tiếp (cách cũ) và `auto`, báo cáo ko/vi/en, sổ kiểm tra, thông báo, kiểm tra hàng loạt có tự phân loại, tra cứu lịch sử, RAG.
- `해커톤 AI에이전트/tools/ui_smoke_test.py`: cả `app.py` và `app_chat.py` mở không lỗi, màn hình kết quả vẽ được sau khi phân tích (có hiển thị kết quả tự phân loại), hộp hỏi chọn miền hiện đúng khi bộ điều phối không chắc.
- Chưa thử trên trình duyệt thật và chưa thử đính kèm ảnh qua giao diện chat.

## 11. Tài liệu và môi trường
- `해커톤 AI에이전트/README.md` thêm tóm tắt tính năng mới; file này (`CHANGES.md`).
- Đã có từ trước nhưng chưa được commit ở main: `knowledge/defect_taxonomy_mobile.yaml`, model `mobile_surface_yolo11s_seg.pt`, `tools/benchmark_models.py`, `prepare_mobile_surface.py` (thư mục `tools/` gốc), `results/model_benchmark.*` (benchmark: pcb 0,888 / mobile 0,979 / msdd 0,604 F1 trên test gốc).
- `requirements.txt` thêm `timm`, `scikit-learn`, `joblib`, `sentence-transformers==3.3.1`, `transformers==4.46.3`, `opencv-python` (cố định để chạy được với torch 2.5; transformers 5.x cần torch ≥ 2.6). Giao diện cần `streamlit` và `mammoth` (đã có trong `requirements.txt` của gói). Fine-tune LLM dùng môi trường riêng `tools/llm_ft/.venv` (torch 2.6) — không nằm trong repo.

## 12. Chưa làm / cần người kiểm tra
- Hiệu chỉnh ngưỡng tin cậy theo F1 tối ưu cho từng model; các ngưỡng hiện vẫn là giá trị ước lượng.
- Rà soát bản dịch vi/en và nội dung RAG bởi người trong ngành; thử ảnh chụp thật tại nhà máy cho bộ điều phối.
- Đánh giá fine-tune LLM, thử lịch sử/RAG với Ollama thật, thử trình duyệt thật.
