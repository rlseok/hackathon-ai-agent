# 보고서 문장 모델 비교

모델: qwen3:8b vs qwen3-defect · 사례 6개 × 언어 3개 (같은 검출 결과, temperature 0.2)

| 모델 | 평균 시간(초) | JSON 실패 | 한국어 섞임(칸) | 영문 코드 노출 | 근거 없는 인용 | 평균 길이(자) |
|---|---|---|---|---|---|---|
| qwen3:8b | 3.7 | 0 | 0 | 0 | 0 | 504 |
| qwen3-defect | 4.4 | 0 | 7 | 0 | 0 | 590 |

## pcb/01_missinghole — 판정 reject

### ko

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | 홀 누락이 검출되었습니다. 5개의 위치에서 누락된 홀이 확인되었습니다. | 이상 수준의 결함 5건이 확인되었습니다. 대표 유형은 홀 누락이며, 격리 후 부적합 보고서(NCR) 작성이 필요합니다. |
| cause_text | 드릴 프로그램(NC 데이터) 누락·오류, 드릴 비트 파손 또는 공구 교환 누락, 드릴 비트 수명 초과 등의 원인 후보가 있습니다. | 원인 후보: 드릴 프로그램(NC 데이터) 누락·오류; 드릴 비트 파손 또는 공구 교환 누락; 드릴 비트 수명 초과 (후보일 뿐 단정하지 않습니다). |
| action_immediate | [작업자 확인 후 실시] 해당 로트 전수 홀 검사. 위치 정확도가 확보되면 재드릴, 아니면 폐기. | [작업자 확인 후 실시] 해당 로트 전수 홀 검사. 위치 정확도가 확보되면 재드릴, 아니면 폐기. |
| action_prevent | 드릴 비트 수명 관리, 파손 감지 장치 점검, 드릴 후 홀 카운트 검사. | NC 데이터와 설계 데이터 대조, 드릴 비트 파손 이력 확인. 드릴 비트 수명 관리, 파손 감지 장치 점검, 드릴 후 홀 카운트 검사 |

### vi

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Phát hiện thiếu lỗ nghiêm trọng tại 5 vị trí, cần kiểm tra và xử lý ngay. | Phát hiện 5 lỗi vượt tiêu chuẩn nên kết luận là bất thường. Loại đại diện là Thiếu lỗ. Cách ly sản phẩm và lập báo cáo không phù hợp (NCR). |
| cause_text | Nguyên nhân có thể do chương trình khoan (NC dữ liệu) bị thiếu hoặc sai, đầu khoan bị hỏng hoặc quên thay, hoặc đầu khoan đã hết tuổi thọ. | Nguyên nhân có thể gồm: Drilling program (NC data) bị thiếu hoặc lỗi; Drilling bit bị mòn hoặc quên thay bit; Drilling bit quá tuổi sử dụng (chỉ là ứng viên, chưa kết luận). |
| action_immediate | [Thực hiện sau khi công nhân xác nhận] Kiểm tra toàn bộ lô sản phẩm tại vị trí thiếu lỗ. Nếu độ chính xác vị trí đảm bảo, tiến hành khoan lại, nếu không thì phải loại bỏ. | [Thực hiện sau khi công nhân xác nhận] Cách ly sản phẩm có lỗi. Kiểm tra lại toàn bộ lỗ ở vị trí chính xác, nếu không sửa được thì loại bỏ. |
| action_prevent | Quản lý tuổi thọ đầu khoan, kiểm tra thiết bị phát hiện hỏng đầu khoan, và kiểm tra số lượng lỗ sau khi khoan. | Kiểm tra sự trùng khớp giữa NC data và dữ liệu thiết kế, xác nhận lịch sử hỏng hóc của bit khoan. Quản lý tuổi thọ bit khoan, kiểm tra thiết bị phát hiện sự mòn và kiểm tra số lượng lỗ sau khi khoan. |

### en

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Missing hole defects were detected in critical areas with high confidence. | 5 defect(s) above the criteria were detected, so the result is Abnormal. The representative type is Missing hole. Isolate the product and issue a nonconformance report (NCR). |
| cause_text | Possible causes include missing or incorrect drill program (NC data), drill bit damage or tool change omission, and drill bit life expiration. | Possible causes: 드릴 프로그램(NC 데이터) 누락·오류; 드릴 비트 파손 또는 공구 교환 누락; 드릴 비트 수명 초과 (candidates only, not conclusions). |
| action_immediate | [After worker confirmation] A full hole inspection of the affected lot is required. Re-drilling should be performed if position accuracy is confirmed, otherwise the product should be scrapped. | [After worker confirmation] Inspect the whole lot at the affected position. Re-drill if the position accuracy is confirmed; otherwise, scrap. |
| action_prevent | Implement drill bit life management, check for damage detection devices, and perform hole count verification after drilling. | Check: NC data and design data comparison, drill-bit damage history confirmation. Prevention: Drill-bit life management, damage detection device inspection, hole count inspection after drilling. |

## pcb/05_scratch — 판정 review

### ko

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | 스크래치가 상단 좌측에 1개 검출되었으며, 신뢰도 0.94로 의심됨. | 의심 수준의 검출 1건이 있어 보류(Hold) 후 재검사합니다. 대표 유형은 스크래치입니다. |
| cause_text | 스크래치의 원인으로는 취급 부주의, 이송 롤러·컨베이어 마찰, 적재 시 보드 간 마찰 등이 의심됨. | 원인 후보: 취급 부주의; 이송 롤러·컨베이어 마찰; 적재 시 보드 간 마찰 (후보일 뿐 단정하지 않습니다). |
| action_immediate | [작업자 확인 후 실시] 동박 노출이나 배선 손상이 없으면 외관 기준 내 허용. 배선을 끊었으면 단선으로 재판정. | [작업자 확인 후 실시] 동박 노출이나 배선 손상이 없으면 외관 기준 내 허용. 배선을 끊었으면 단선으로 재판정. |
| action_prevent | 보드 간 간지 사용, 이송 장비 정기 점검, 취급 교육을 통해 재발을 방지해야 함. | 발생 위치로 공정 추적 (이송 방향 긁힘이면 롤러 점검). 보드 간 간지 사용, 이송 장비 정기 점검, 취급 교육 |

### vi

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Phát hiện vết xước trên trái, cần đánh giá mức độ cho phép. | Có 1 phát hiện ở mức nghi ngờ nên giữ lại (Hold) và kiểm tra lại. Loại đại diện là Vết xước. |
| cause_text | Vết xước có thể do xử lý không cẩn thận, ma sát giữa các tấm hoặc ma sát với роллер và băng chuyền trong quá trình vận chuyển. | Nguyên nhân có thể gồm: Thiếu kiểm soát việc xử lý; Ma sát của роллер输送带·cần trục; Ma sát giữa các board khi xếp đặt (chỉ là ứng viên, chưa kết luận). |
| action_immediate | [Thực hiện sau khi công nhân xác nhận] Nếu đồng bạc không bị phơi sáng hoặc đường mạch không bị đứt, thì vết xước được coi là chấp nhận trong tiêu chuẩn ngoại quan. Nếu đường mạch bị đứt, cần đánh giá lại như là sự cố đơn dây. | [Thực hiện sau khi công nhân xác nhận] Nếu không có phơi sáng hoặc hư hỏng bề mặt thì giữ lại (Hold) và kiểm tra lại. Nếu cắt đường mạch thì đánh giá lại là đứt mạch. |
| action_prevent | Sử dụng vật liệu ngăn cách giữa các tấm, kiểm tra định kỳ thiết bị vận chuyển và thực hiện đào tạo xử lý cẩn thận. | Kiểm tra theo hướng sản xuất tại vị trí xảy ra lỗi (nếu là ma sát theo hướng chuyển vận thì kiểm tra роллер). Dùng đệm ngăn cách các board, kiểm tra thiết bị vận chuyển định kỳ, đào tạo xử lý sản phẩm. |

### en

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | A scratch is suspected on the top left area of the product. | 1 suspected area(s) were detected and need re-inspection; they are not asserted as defects. The representative type is Scratch. |
| cause_text | The scratch may be caused by mishandling, friction from transport rollers or conveyors, or friction between boards during loading. | Possible causes: 취급 부주의; 이송 롤러·컨베이어 마찰; 적재 시 보드 간 마찰 (candidates only, not conclusions). |
| action_immediate | [After worker confirmation] If there is no exposure of the adhesive or wiring damage, it is acceptable according to the appearance standard. If the wiring is broken, reclassify as an open circuit. | [After worker confirmation] If there is no coating exposure or wire break, it is acceptable according to the appearance standard. If the wire is broken, rejudge as a single break. |
| action_prevent | Use board separators, conduct regular maintenance of transport equipment, and provide handling training. | Check the process trace at the occurrence position (inspect the roller if it is a conveyance-direction scratch). Use a board spacer between boards, perform regular maintenance of the conveyor, and provide handling training. |

## msdd/03_Porosity — 판정 reject

### ko

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | 전면 분포된 기공으로 가공면 전체에 이상이 나타났습니다. | 이상 수준의 결함 1건이 확인되었습니다. 대표 유형은 기공이며, 격리 후 부적합 보고서(NCR) 작성이 필요합니다. 결함이 가공면 전체에 퍼져 있어 가공·소재 조건 이상 가능성이 있으므로 같은 로트의 다른 부품도 확인합니다. |
| cause_text | 주조·소결 시 가스 혼입 또는 탈가스 부족, 원소재 내부 결함, 용탕 또는 분말의 수분·오염 등이 원인 후보입니다. | 원인 후보: 주조·소결 시 가스 혼입 또는 탈가스 부족; 원소재 내부 결함; 용탕 또는 분말의 수분·오염 (후보일 뿐 단정하지 않습니다). |
| action_immediate | [작업자 확인 후 실시] 구멍 크기·개수를 기준과 비교하고, 실링면·나사부 등 기능면에 있으면 불량으로 판단합니다. | [작업자 확인 후 실시] 구멍 크기·개수를 기준과 비교. 실링면·나사부 등 기능면에 있으면 불량. |
| action_prevent | 탈가스·건조 조건 관리와 원소재 입고 검사(단면·밀도)를 강화하여 재발을 방지해야 합니다. | 원소재 로트 이력, 주조·소결 조건 기록 확인. 탈가스·건조 조건 관리, 원소재 입고 검사(단면·밀도) 강화 |

### vi

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Phát hiện hiện tượng rỗ khí trên bề mặt gia công, phân bố toàn bộ bề mặt. | Có 1 lỗi ở mức bất thường, loại đại diện là Rỗ khí; cần cách ly và lập báo cáo không phù hợp (NCR). Lỗi lan rộng trên bề mặt gia công, có thể do điều kiện gia công hoặc vật liệu, nên kiểm tra các chi tiết khác trong cùng lô. |
| cause_text | Nguyên nhân có thể bao gồm khí trộn vào trong quá trình đúc hoặc sintering, thiếu thoát khí, hoặc khuyết tật bên trong nguyên vật liệu. Ngoài ra, độ ẩm hoặc ô nhiễm trong dung dịch nấu chảy hoặc bột cũng có thể gây ra hiện tượng này. | Nguyên nhân có thể gồm: Chủ vào hoặc nén khuôn có khí gas hoặc thiếu thoát khí; lỗi bên trong vật liệu nguyên sinh; độ ẩm hoặc nhiễm bẩn của hợp kim hoặc bột. Đây chỉ là ứng viên, chưa kết luận. |
| action_immediate | [Thực hiện sau khi công nhân xác nhận] So sánh kích thước và số lượng lỗ với tiêu chuẩn. Nếu lỗ xuất hiện trên bề mặt chức năng như mặt phẳng hoặc ren thì coi là lỗi. | [Thực hiện sau khi công nhân xác nhận] So sánh kích thước và số lượng lỗi với tiêu chuẩn. Lỗi ở mặt chức năng (mặt Sealing, ren) được coi là lỗi. |
| action_prevent | Cần kiểm tra lịch sử lô nguyên vật liệu, ghi chép điều kiện đúc và sintering. Đồng thời quản lý tốt điều kiện thoát khí và sấy khô, tăng cường kiểm tra nguyên vật liệu nhập kho (đặc biệt là mặt cắt ngang và mật độ). | Kiểm tra lịch sử lô vật liệu nguyên sinh, ghi nhận điều kiện casting và nén khuôn. Kiểm soát điều kiện thoát khí và sấy; tăng cường kiểm tra nhập liệu (cắt lát, mật độ). |

### en

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Porosity is detected across the entire surface, indicating a potential issue with the raw material or processing conditions. | 1 defect(s) were confirmed at the abnormal level; the representative type is Porosity. Isolate the product and write an NCR. The defect spreads over the whole machined surface, which suggests a machining or material problem, so check other parts of the same lot. |
| cause_text | The cause may include gas inclusion during casting or sintering, insufficient degassing, or internal defects in the raw material. Moisture or contamination in the molten material or powder may also be a factor. | Possible causes: 주조·소결 시 가스 혼입 또는 탈가스 부족; 원소재 내부 결함; 용탕 또는 분말의 수분·오염 (candidates only, not conclusions). |
| action_immediate | [After worker confirmation] Compare the hole size and count with the criteria. Reject the part if the porosity is located on functional surfaces such as sealing faces or threaded areas. | [After worker confirmation] Compare hole size and count with the criteria. Reject if it is on the sealing face, thread or other functional surface. |
| action_prevent | Check the raw material lot history and casting/sintering conditions. Strengthen incoming inspection of raw materials, including cross-sectional and density checks. | Check the raw material lot history, casting and sintering conditions. Manage degassing and drying conditions; strengthen incoming inspection of the raw material (cross-section, density). |

## msdd/05_Stain — 판정 review

### ko

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | 의심 얼룩이 중앙에 1개 검출됨. 크기 5.03%로 상대적으로 크지만 신뢰도 0.88로 사람 판단이 필요함. | 의심 수준의 검출 1건이 있어 보류(Hold) 후 재검사합니다. 대표 유형은 얼룩입니다. |
| cause_text | 세척액·절삭유 잔류 후 자연 건조, 헹굼 또는 건조 공정 불충분, 맨손 취급(지문) 등이 원인 후보로 의심됨. | 원인 후보: 세척액·절삭유 잔류 후 자연 건조; 헹굼 또는 건조 공정 불충분; 맨손 취급(지문) (후보일 뿐 단정하지 않습니다). |
| action_immediate | [작업자 확인 후 실시] 재세척으로 제거되는지 확인. 제거되면 재세척 후 합격 처리. | [작업자 확인 후 실시] 재세척으로 제거되는지 확인. 제거되면 재세척 후 합격 처리. |
| action_prevent | 헹굼·에어 블로우·건조 조건 관리, 장갑 착용 취급을 통해 재발 방지. | 세척액 농도·교체 주기, 건조 온도·시간 확인. 헹굼·에어 블로우·건조 조건 관리, 장갑 착용 취급 |

### vi

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Phát hiện vết ố trên bề mặt, cần đánh giá thêm. | Có 1 phát hiện ở mức nghi ngờ nên giữ lại (Hold) và kiểm tra lại. Loại đại diện là Vết ố. |
| cause_text | Vết ố có thể do dư lượng dung dịch rửa hoặc dầu cắt sau khi khô tự nhiên, quá trình rửa hoặc sấy không đủ, hoặc tiếp xúc bằng tay. | Nguyên nhân có thể gồm: Rỗng sấy dư nước rửa hoặc dầu tuốt; Sấy hoặc công đoạn làm khô không đủ; Lấy mẫu bằng tay (dấu vân tay). Đây chỉ là ứng viên, chưa kết luận. |
| action_immediate | [Thực hiện sau khi công nhân xác nhận] Kiểm tra xem có thể loại bỏ vết ố bằng cách rửa lại. Nếu loại bỏ được, tiến hành rửa lại và chấp nhận. | [Thực hiện sau khi công nhân xác nhận] Kiểm tra whether làm sạch lại có loại bỏ lỗi. Xử lý là chấp nhận nếu loại bỏ được sau khi làm sạch lại. |
| action_prevent | Kiểm tra nồng độ dung dịch rửa và chu kỳ thay thế, kiểm soát nhiệt độ và thời gian sấy, đồng thời sử dụng găng tay khi xử lý. | Kiểm tra nồng độ dung dịch rửa, chu kỳ thay thế, nhiệt độ và thời gian sấy. Quản lý điều kiện rửa sạch, sấy và làm khô; xử lý bằng găng tay. |

### en

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | A stain is suspected in the center of the image. | 1 suspected area(s) were detected and need re-inspection; they are not asserted as defects. The representative type is Stain. |
| cause_text | The stain may be caused by residual cleaning solution or cutting oil left after drying, insufficient rinsing or drying process, or manual handling (fingerprints). | Possible causes: 세척액·절삭유 잔류 후 자연 건조; 헹굼 또는 건조 공정 불충분; 맨손 취급(지문) (candidates only, not conclusions). |
| action_immediate | [After worker confirmation] Check if the stain can be removed by re-cleaning. If removed, pass after re-cleaning. | [After worker confirmation] Check whether it can be removed by re-washing. If removed, re-wash and release as good. |
| action_prevent | Review and manage rinsing, air blowing, and drying conditions. Ensure the use of gloves during handling. | Check: 세척액 농도·교체 주기, 건조 온도·시간 확인. Prevent: 헹굼·에어 블로우·건조 조건 관리, 장갑 착용 취급 |

## mobile/00_oil — 판정 reject

### ko

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | 오일 오염이 검출되었습니다. 중앙 우측 위치에 오일 오염이 확인되었습니다. | 이상 수준의 결함 1건이 확인되었습니다. 대표 유형은 오일 오염이며, 격리 후 부적합 보고서(NCR) 작성이 필요합니다. |
| cause_text | 장비 또는 지그의 오일 누유, 장갑·공구·트레이 오염, 세척 및 건조 불량 등이 원인 후보입니다. | 원인 후보: 장비 또는 지그의 오일 누유; 장갑·공구·트레이 오염; 세척 및 건조 불량 (후보일 뿐 단정하지 않습니다). |
| action_immediate | [작업자 확인 후 실시] 해당 제품을 격리하고 승인된 방법으로 세척 후 재검사한다. | [작업자 확인 후 실시] 해당 제품을 격리하고 승인된 방법으로 세척 후 재검사한다. |
| action_prevent | 누유 점검과 세척·건조 조건을 표준화한다. | 장비 누유, 지그, 장갑 및 세척액 상태를 확인한다. 누유 점검과 세척·건조 조건을 표준화한다. |

### vi

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Sản phẩm có hiện tượng dính dầu trên bề mặt, cần kiểm tra và xử lý ngay. | Phát hiện 1 lỗi vượt tiêu chuẩn nên kết luận là bất thường. Loại đại diện là Dính dầu. Cách ly sản phẩm và lập báo cáo không phù hợp (NCR). |
| cause_text | Nguyên nhân có thể do thiết bị hoặc kẹp dầu rò rỉ, găng tay hoặc dụng cụ bị nhiễm dầu, hoặc quá trình rửa và sấy không đạt yêu cầu. | Nguyên nhân có thể gồm: Sự rò rỉ dầu của thiết bị hoặc giá đỡ; Vật tư (găng tay, dụng cụ, thùng) bị nhiễm dầu; Vệ sinh và sấy kém. Đây chỉ là ứng viên, chưa kết luận. |
| action_immediate | [Thực hiện sau khi công nhân xác nhận] Cách ly sản phẩm, tiến hành rửa theo phương pháp đã được phê duyệt và kiểm tra lại. | [Thực hiện sau khi công nhân xác nhận] Cách ly sản phẩm và kiểm tra lại sau khi rửa theo phương pháp đã được phê duyệt. |
| action_prevent | Kiểm tra tình trạng rò rỉ của thiết bị và kẹp, đồng thời chuẩn hóa quy trình rửa và sấy. | Kiểm tra sự rò rỉ của thiết bị, giá đỡ, găng tay và trạng thái dung dịch rửa. Tiêu chuẩn hóa kiểm tra sự rò rỉ và điều kiện vệ sinh – sấy. |

### en

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Oil contamination detected in the center right area of the image. | 1 defect(s) above the criteria were detected, so the result is Abnormal. The representative type is Oil contamination. Isolate the product and issue a nonconformance report (NCR). |
| cause_text | Potential causes include oil leakage from equipment or fixtures, contamination from gloves, tools, or trays, or inadequate cleaning and drying processes. | Possible causes: 장비 또는 지그의 오일 누유; 장갑·공구·트레이 오염; 세척 및 건조 불량 (candidates only, not conclusions). |
| action_immediate | [After worker confirmation] Isolate the product and clean it using an approved method before re-inspection. | [After worker confirmation] Isolate the product and clean it with the approved method, then re-inspect. |
| action_prevent | Check for oil leakage and standardize cleaning and drying conditions to prevent recurrence. | Check equipment leakage, the jig, gloves and the cleaner state. Standardize leakage checks and cleaning and drying conditions. |

## mobile/01_scratch — 판정 review

### ko

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | 스크래치가 의심되어 재검사가 필요합니다. | 의심 수준의 검출 4건이 있어 보류(Hold) 후 재검사합니다. 대표 유형은 스크래치입니다. |
| cause_text | 스크래치의 원인으로는 취급·적재 중 부품 간 접촉, 지그·트레이·컨베이어 마찰, 조립 중 공구 또는 이물 접촉 등이 의심됩니다. | 원인 후보: 취급·적재 중 부품 간 접촉; 지그·트레이·컨베이어 마찰; 조립 중 공구 또는 이물 접촉 (후보일 뿐 단정하지 않습니다). |
| action_immediate | [작업자 확인 후 실시] 제품을 격리하고 길이·폭·깊이를 외관 기준과 비교합니다. | [작업자 확인 후 실시] 제품을 격리하고 길이·폭·깊이를 외관 기준과 비교한다. |
| action_prevent | 보호재를 사용하고 취급 공정을 점검하여 재발을 방지합니다. | 지그와 이송 경로의 접촉·이물을 확인한다. 보호재를 사용하고 취급 공정을 점검한다. |

### vi

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Phát hiện 4 vết xước trên bề mặt, cần đánh giá mức độ và xác nhận lại. | Có 4 phát hiện ở mức nghi ngờ nên giữ lại (Hold) và kiểm tra lại. Loại đại diện là Vết xước. |
| cause_text | Vết xước có thể do tiếp xúc giữa các bộ phận trong quá trình vận chuyển, ma sát với kẹp, băng chuyền hoặc tiếp xúc với dụng cụ, vật lạ trong quá trình lắp ráp. | Nguyên nhân có thể gồm: Lỗi do tiếp xúc giữa chi tiết khi vận hành; Ma sát của jig, thùng, băng tải; Tiếp xúc của dụng cụ hoặc vật lạ trong khi lắp ráp (chỉ là ứng viên, chưa kết luận). |
| action_immediate | [Thực hiện sau khi công nhân xác nhận] Cách ly sản phẩm và kiểm tra chiều dài, chiều rộng, độ sâu theo tiêu chuẩn ngoại quan. | [Thực hiện sau khi công nhân xác nhận] Cách ly sản phẩm và so sánh chiều dài, chiều rộng, chiều sâu với tiêu chuẩn ngoại quan. |
| action_prevent | Sử dụng vật liệu bảo vệ và kiểm tra quy trình vận chuyển, lắp ráp. | Kiểm tra sự tiếp xúc và vật lạ của jig và đường truyền. Sử dụng vật liệu bảo vệ và kiểm tra công đoạn xử lý. |

### en

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Scratch defects are suspected based on high confidence levels and require human acceptance decision. | 4 suspected area(s) were detected and need re-inspection; they are not asserted as defects. The representative type is Scratch. |
| cause_text | Potential causes for the scratch defects include contact between components during handling or transportation, friction from jigs, trays, or conveyors, and contact with tools or foreign objects during assembly. | Possible causes: 취급·적재 중 부품 간 접촉; 지그·트레이·컨베이어 마찰; 조립 중 공구 또는 이물 접촉 (candidates only, not conclusions). |
| action_immediate | [After worker confirmation] Isolate the product and compare the length, width, and depth of the scratches against the appearance standards. Confirm the position and size of the scratches. | [After worker confirmation] Isolate the product and compare the length, width and depth with the appearance criteria. |
| action_prevent | Use protective materials and inspect the handling process to prevent future occurrences. | Check the jig and conveying path for contact and foreign matter. Use a protective coating and inspect the handling process. |
