# 보고서 문장 모델 비교

모델: qwen3:8b vs qwen3-defect · 사례 6개 × 언어 3개 (같은 검출 결과, temperature 0.2)

| 모델 | 평균 시간(초) | JSON 실패 | 한국어 섞임(칸) | 영문 코드 노출 | 근거 없는 인용 | 평균 길이(자) |
|---|---|---|---|---|---|---|
| qwen3:8b | 3.7 | 0 | 0 | 0 | 0 | 473 |
| qwen3-defect | 4.3 | 0 | 0 | 0 | 0 | 612 |

## pcb/01_missinghole — 판정 reject

### ko

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | 홀 누락이 5곳에서 검출되었습니다. 상단 중앙, 중앙, 중앙 좌측, 하단 우측, 하단 중앙 위치에 발생하며, 홀 크기의 길이가 24~33px 범위입니다. | 이상 수준의 결함 5건이 확인되었습니다. 대표 유형은 홀 누락이며, 격리 후 부적합 보고서(NCR) 작성이 필요합니다. |
| cause_text | 드릴 프로그램(NC 데이터) 누락·오류, 드릴 비트 파손 또는 공구 교환 누락, 드릴 비트 수명 초과 등의 원인 후보가 있습니다. | 원인 후보: 드릴 프로그램(NC 데이터) 누락·오류; 드릴 비트 파손 또는 공구 교환 누락; 드릴 비트 수명 초과 (후보일 뿐 단정하지 않습니다). |
| action_immediate | 해당 로트 전수 홀 검사. 위치 정확도가 확보되면 재드릴, 아니면 폐기. 작업자 확인 후 실시. | [작업자 확인 후 실시] 해당 로트 전수 홀 검사. 위치 정확도가 확보되면 재드릴, 아니면 폐기. |
| action_prevent | 드릴 비트 수명 관리, 파손 감지 장치 점검, 드릴 후 홀 카운트 검사. | NC 데이터와 설계 데이터 대조, 드릴 비트 파손 이력 확인. 드릴 비트 수명 관리, 파손 감지 장치 점검, 드릴 후 홀 카운트 검사 |

### vi

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Có 5 lỗ thiếu được phát hiện ở vị trí giữa, dưới phải và trên giữa, kích thước lỗ khoảng 24~33 pixel. | Phát hiện 5 lỗi vượt tiêu chuẩn nên kết luận là bất thường. Loại đại diện là Thiếu lỗ. Cách ly sản phẩm và lập báo cáo không phù hợp (NCR). |
| cause_text | Nguyên nhân có thể do thiếu hoặc sai chương trình khoan, mũi khoan gãy hoặc quên thay dụng cụ, mũi khoan quá tuổi thọ. | Nguyên nhân có thể gồm: Thiếu hoặc sai chương trình khoan (dữ liệu NC); Mũi khoan gãy hoặc quên thay dụng cụ; Mũi khoan quá tuổi thọ (chỉ là ứng viên, chưa kết luận). |
| action_immediate | [Thực hiện sau khi công nhân xác nhận] Kiểm tra toàn bộ lỗ của lô. Nếu độ chính xác vị trí đảm bảo thì khoan lại, nếu không thì loại bỏ. | [Thực hiện sau khi công nhân xác nhận] Kiểm tra toàn bộ lỗ của lô. Nếu độ chính xác vị trí đảm bảo thì khoan lại, nếu không thì loại bỏ. |
| action_prevent | Quản lý tuổi thọ mũi khoan, kiểm tra thiết bị phát hiện gãy mũi, kiểm tra đếm lỗ sau khi khoan. | Đối chiếu dữ liệu NC với dữ liệu thiết kế, kiểm tra lịch sử gãy mũi khoan. Quản lý tuổi thọ mũi khoan, kiểm tra thiết bị phát hiện gãy mũi, kiểm tra đếm lỗ sau khi khoan. |

### en

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Missing hole defects were detected in multiple positions with high confidence. | 5 defect(s) above the criteria were detected, so the result is Abnormal. The representative type is Missing hole. Isolate the product and issue a nonconformance report (NCR). |
| cause_text | The missing holes may be caused by missing or wrong drill program (NC data), broken drill bit or missed tool change, or drill bit life exceeded. | Possible causes: Missing or wrong drill program (NC data); Broken drill bit or a missed tool change; Drill bit life exceeded (candidates only, not conclusions). |
| action_immediate | [After worker confirmation] Inspect all holes in the lot. Re-drill if position accuracy can be ensured, otherwise scrap. | [After worker confirmation] Inspect all holes in the lot. Re-drill if position accuracy can be ensured, otherwise scrap. |
| action_prevent | Manage drill-bit life, check the breakage-detection device, and run a hole-count check after drilling. | Compare the NC data with the design data and check the drill-bit breakage history. Manage drill-bit life, check the breakage-detection device, and run a hole-count check after drilling. |

## pcb/05_scratch — 판정 review

### ko

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | 스크래치가 상단 좌측에 1개 검출되었으며, 신뢰도 0.94로 의심됨. | 의심 영역 1곳이 검출되어 재검사가 필요합니다. 결함으로 단정하지 않습니다. |
| cause_text | 스크래치의 주요 원인 후보로는 취급 부주의, 이송 롤러·컨베이어 마찰, 적재 시 보드 간 마찰이 있음. | 원인 후보: 취급 부주의; 이송 롤러·컨베이어 마찰; 적재 시 보드 간 마찰 (후보일 뿐 단정하지 않습니다). |
| action_immediate | [작업자 확인 후 실시] 동박 노출이나 배선 손상이 없으면 외관 기준 내 허용. 배선을 끊었으면 단선으로 재판정. | [작업자 확인 후 실시] 동박 노출이나 배선 손상이 없으면 외관 기준 내 허용. 배선을 끊었으면 단선으로 재판정. |
| action_prevent | 보드 간 간지 사용, 이송 장비 정기 점검, 취급 교육을 통해 재발을 방지해야 함. | 발생 위치로 공정 추적 (이송 방향 긁힘이면 롤러 점검). 보드 간 간지 사용, 이송 장비 정기 점검, 취급 교육 |

### vi

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Phát hiện vết xước trên bề mặt, cần đánh giá lại để xác định mức độ ảnh hưởng. | Phát hiện 1 vị trí nghi ngờ cần kiểm tra lại; chưa kết luận là lỗi. Loại đại diện là Vết xước. |
| cause_text | Vết xước có thể do thao tác bất cẩn, ma sát với con lăn vận chuyển hoặc băng tải, hoặc ma sát giữa các bo mạch khi xếp chồng. | Nguyên nhân có thể gồm: Thao tác bất cẩn; Ma sát với con lăn vận chuyển hoặc băng tải; Ma sát giữa các bo mạch khi xếp chồng (chỉ là ứng viên, chưa kết luận). |
| action_immediate | [Thực hiện sau khi công nhân xác nhận] Nếu vết xước không lộ đồng hoặc không làm hỏng đường mạch thì chấp nhận trong tiêu chuẩn ngoại quan. Nếu làm đứt đường mạch thì đánh giá lại là hở mạch. | [Thực hiện sau khi công nhân xác nhận] Nếu không lộ đồng hoặc không làm hỏng đường mạch thì chấp nhận trong tiêu chuẩn ngoại quan. Nếu làm đứt đường mạch thì đánh giá lại là hở mạch. |
| action_prevent | Dùng giấy lót giữa các bo mạch, bảo dưỡng thiết bị vận chuyển định kỳ, đào tạo thao tác. | Truy vết công đoạn theo vị trí xước (xước theo hướng vận chuyển thì kiểm tra con lăn). Dùng giấy lót giữa các bo mạch, bảo dưỡng thiết bị vận chuyển định kỳ, đào tạo thao tác. |

### en

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | A scratch is suspected on the top left area of the product. | There are 1 suspected detection(s), so the part is put on hold and re-inspected. The representative type is Scratch. |
| cause_text | The scratch may be caused by careless handling, friction with transfer rollers or conveyors, or friction between boards when stacked. | Possible causes: Careless handling; Friction with transfer rollers or conveyors; Friction between boards when stacked (candidates only, not conclusions). |
| action_immediate | [After worker confirmation] If no copper is exposed and no trace is damaged, accept within the appearance standard. If a trace is cut, re-judge it as an open circuit. | [After worker confirmation] If no copper is exposed and no trace is damaged, accept within the appearance standard. If a trace is cut, re-judge it as an open circuit. |
| action_prevent | Use interleaving paper between boards, service transfer equipment regularly, and train operators in handling. | Trace the process from the scratch position (if the scratch follows the transfer direction, check the rollers). Use interleaving paper between boards, service transfer equipment regularly, and train operators in handling. |

## msdd/03_Porosity — 판정 reject

### ko

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | 전면 분포된 기공으로, 가공면 전체에 퍼져 있는 것으로 보여 개별 부품이 아니라 원소재 로트 문제일 가능성이 있다. | 이상 수준의 결함 1건이 확인되었습니다. 대표 유형은 기공이며, 격리 후 부적합 보고서(NCR) 작성이 필요합니다. 결함이 가공면 전체에 퍼져 있어 가공·소재 조건 이상 가능성이 있으므로 같은 로트의 다른 부품도 확인합니다. |
| cause_text | 주조·소결 시 가스 혼입 또는 탈가스 부족, 원소재 내부 결함, 용탕 또는 분말의 수분·오염 등이 원인 후보로 생각됨. | 원인 후보: 주조·소결 시 가스 혼입 또는 탈가스 부족; 원소재 내부 결함; 용탕 또는 분말의 수분·오염 (후보일 뿐 단정하지 않습니다). |
| action_immediate | [작업자 확인 후 실시] 구멍 크기·개수를 기준과 비교. 실링면·나사부 등 기능면에 있으면 불량으로 판단. | [작업자 확인 후 실시] 구멍 크기·개수를 기준과 비교. 실링면·나사부 등 기능면에 있으면 불량. |
| action_prevent | 탈가스·건조 조건 관리, 원소재 입고 검사(단면·밀도) 강화 및 원소재 로트 이력, 주조·소결 조건 기록 확인. | 원소재 로트 이력, 주조·소결 조건 기록 확인. 탈가스·건조 조건 관리, 원소재 입고 검사(단면·밀도) 강화 |

### vi

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Phát hiện lỗi rỗ khí trên bề mặt gia công, phân bố toàn bộ bề mặt. | Phát hiện 1 lỗi vượt tiêu chuẩn nên kết luận là bất thường. Loại đại diện là Rỗ khí. Cách ly sản phẩm và lập báo cáo không phù hợp (NCR). Lỗi lan rộng trên bề mặt gia công, có thể do điều kiện gia công hoặc vật liệu, nên kiểm tra các chi tiết khác trong cùng lô. |
| cause_text | Nguyên nhân có thể bao gồm lẫn khí khi đúc hoặc thiêu kết, khử khí chưa đủ, khuyết tật bên trong vật liệu gốc, hoặc hơi ẩm, tạp chất trong kim loại nóng chảy hoặc bột. | Nguyên nhân có thể gồm: Lẫn khí khi đúc hoặc thiêu kết, hoặc khử khí chưa đủ; Khuyết tật bên trong vật liệu gốc; Hơi ẩm hoặc tạp chất trong kim loại nóng chảy hoặc bột (chỉ là ứng viên, chưa kết luận). |
| action_immediate | [Thực hiện sau khi công nhân xác nhận] So sánh kích thước và số lượng lỗ với tiêu chuẩn. Nếu nằm ở bề mặt chức năng như mặt làm kín hoặc phần ren thì là lỗi. | [Thực hiện sau khi công nhân xác nhận] So sánh kích thước và số lượng lỗ với tiêu chuẩn. Nếu nằm ở bề mặt chức năng như mặt làm kín hoặc phần ren thì là lỗi. |
| action_prevent | Quản lý điều kiện khử khí và sấy khô, tăng cường kiểm tra đầu vào vật liệu gốc (mặt cắt, khối lượng riêng). | Kiểm tra lịch sử lô vật liệu gốc và hồ sơ điều kiện đúc hoặc thiêu kết. Quản lý điều kiện khử khí và sấy khô, tăng cường kiểm tra đầu vào vật liệu gốc (mặt cắt, khối lượng riêng). |

### en

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Porosity is detected across the entire surface, indicating potential issues with the material or processing conditions. | 1 defect(s) were confirmed at the abnormal level; the representative type is Porosity. Isolate the product and write an NCR. The defect spreads over the whole machined surface, which suggests a machining or material problem, so check other parts of the same lot. |
| cause_text | Possible causes include gas entrapment or insufficient degassing during casting or sintering, internal defects of the raw material, or moisture or contamination in the melt or powder. | Possible causes: Gas entrapment or insufficient degassing during casting or sintering; Internal defects of the raw material; Moisture or contamination in the melt or powder (candidates only, not conclusions). |
| action_immediate | [After worker confirmation] Compare hole size and count with the standard. It is a defect if it lies on a functional surface such as a sealing face or thread. | [After worker confirmation] Compare hole size and count with the standard. It is a defect if it lies on a functional surface such as a sealing face or thread. |
| action_prevent | Control degassing and drying conditions and strengthen incoming inspection of raw material (cross-section, density). Check the raw-material lot history and the casting or sintering condition records. | Check the raw-material lot history and the casting or sintering condition records. Control degassing and drying conditions and strengthen incoming inspection of raw material (cross-section, density). |

## msdd/05_Stain — 판정 review

### ko

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | 얼룩이 중앙에 의심되어 재검사 필요 | 의심 수준의 검출 1건이 있어 보류(Hold) 후 재검사합니다. 대표 유형은 얼룩입니다. |
| cause_text | 세척액·절삭유 잔류 후 자연 건조, 헹굼 또는 건조 공정 불충분, 맨손 취급(지문) 등이 원인 후보입니다. | 원인 후보: 세척액·절삭유 잔류 후 자연 건조; 헹굼 또는 건조 공정 불충분; 맨손 취급(지문) (후보일 뿐 단정하지 않습니다). |
| action_immediate | [작업자 확인 후 실시] 재세척으로 제거되는지 확인. 제거되면 재세척 후 합격 처리. | [작업자 확인 후 실시] 재세척으로 제거되는지 확인. 제거되면 재세척 후 합격 처리. |
| action_prevent | 헹굼·에어 블로우·건조 조건 관리, 장갑 착용 취급 | 세척액 농도·교체 주기, 건조 온도·시간 확인. 헹굼·에어 블로우·건조 조건 관리, 장갑 착용 취급 |

### vi

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Phát hiện vết ố trên bề mặt, cần đánh giá mức độ cho phép. | Có 1 phát hiện ở mức nghi ngờ nên giữ lại và kiểm tra lại. Loại đại diện là Vết ố. |
| cause_text | Vết ố có thể do dung dịch rửa hoặc dầu cắt gọt còn sót lại và khô tự nhiên, hoặc do xả nước và sấy khô chưa đủ, cũng có thể do cầm bằng tay trần để lại dấu vân tay. | Nguyên nhân có thể gồm: Dung dịch rửa hoặc dầu cắt gọt còn sót rồi khô tự nhiên; Xả nước hoặc sấy khô chưa đủ; Cầm bằng tay trần (dấu vân tay) (chỉ là ứng viên, chưa kết luận). |
| action_immediate | [Thực hiện sau khi công nhân xác nhận] Kiểm tra xem rửa lại có làm sạch không. Nếu sạch thì rửa lại rồi cho đạt. | [Thực hiện sau khi công nhân xác nhận] Kiểm tra xem rửa lại có làm sạch không. Nếu sạch thì rửa lại rồi cho đạt. |
| action_prevent | Quản lý điều kiện xả nước, thổi khí và sấy khô; thao tác khi đeo găng tay. | Kiểm tra nồng độ và chu kỳ thay dung dịch rửa, nhiệt độ và thời gian sấy. Quản lý điều kiện xả nước, thổi khí và sấy khô; thao tác khi đeo găng tay. |

### en

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | A stain is suspected in the center of the image. | There are 1 suspected detection(s), so the part is put on hold and re-inspected. The representative type is Stain. |
| cause_text | The stain may be caused by washing liquid or cutting fluid left and dried naturally, insufficient rinsing or drying, or handling with bare hands (fingerprints). | Possible causes: Washing liquid or cutting fluid left and dried naturally; Insufficient rinsing or drying; Handling with bare hands (fingerprints) (candidates only, not conclusions). |
| action_immediate | [After worker confirmation] Check whether re-washing removes the stain. If it does, re-wash and accept. | [After worker confirmation] Check whether re-washing removes it. If it does, re-wash and accept. |
| action_prevent | Control rinsing, air-blow and drying conditions, and handle with gloves. | Check the washing-liquid concentration and change interval, and the drying temperature and time. Control rinsing, air-blow and drying conditions, and handle with gloves. |

## mobile/00_oil — 판정 reject

### ko

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | 오일 오염이 중앙 우측에 1개 검출되었습니다. 신뢰도 0.97로 이상 기준을 초과했습니다. | 이상 수준의 결함 1건이 확인되었습니다. 대표 유형은 오일 오염이며, 격리 후 부적합 보고서(NCR) 작성이 필요합니다. |
| cause_text | 장비 또는 지그의 오일 누유, 장갑·공구·트레이 오염, 세척 및 건조 불량 등이 원인 후보입니다. | 원인 후보: 장비 또는 지그의 오일 누유; 장갑·공구·트레이 오염; 세척 및 건조 불량 (후보일 뿐 단정하지 않습니다). |
| action_immediate | [작업자 확인 후 실시] 해당 제품을 격리하고 승인된 방법으로 세척 후 재검사한다. | [작업자 확인 후 실시] 해당 제품을 격리하고 승인된 방법으로 세척 후 재검사한다. |
| action_prevent | 누유 점검과 세척·건조 조건을 표준화한다. | 장비 누유, 지그, 장갑 및 세척액 상태를 확인한다. 누유 점검과 세척·건조 조건을 표준화한다. |

### vi

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Sản phẩm có hiện tượng dính dầu trên bề mặt, cần kiểm tra và xử lý ngay. | Phát hiện 1 lỗi vượt tiêu chuẩn nên kết luận là bất thường. Loại đại diện là Dính dầu. Cách ly sản phẩm và lập báo cáo không phù hợp (NCR). |
| cause_text | Nguyên nhân có thể do rò rỉ dầu từ thiết bị hoặc đồ gá, găng tay, dụng cụ hoặc khay bị bẩn, hoặc quá trình rửa và sấy khô kém. | Nguyên nhân có thể gồm: Rò rỉ dầu từ thiết bị hoặc đồ gá; Găng tay, dụng cụ hoặc khay bị bẩn; Rửa và sấy khô kém (chỉ là ứng viên, chưa kết luận). |
| action_immediate | [Thực hiện sau khi công nhân xác nhận] Cách ly sản phẩm, làm sạch bằng phương pháp được phê duyệt rồi kiểm tra lại. | [Thực hiện sau khi công nhân xác nhận] Cách ly sản phẩm, làm sạch bằng phương pháp được phê duyệt rồi kiểm tra lại. |
| action_prevent | Kiểm tra rò rỉ và chuẩn hóa điều kiện rửa, sấy khô. | Kiểm tra rò rỉ dầu của thiết bị, đồ gá, găng tay và tình trạng dung dịch rửa. Kiểm tra rò rỉ và chuẩn hóa điều kiện rửa, sấy khô. |

### en

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Oil contamination detected in the center right area of the product. | 1 defect(s) were confirmed at the abnormal level; the representative type is Oil contamination. Isolate the product and write an NCR. |
| cause_text | Possible causes include oil leaking from equipment or a jig, contaminated gloves, tools or trays, or poor washing and drying conditions. | Possible causes: Oil leaking from equipment or a jig; Contaminated gloves, tools or trays; Poor washing and drying (candidates only, not conclusions). |
| action_immediate | [After worker confirmation] Isolate the product, clean it with an approved method and re-inspect. | [After worker confirmation] Isolate the product, clean it with an approved method and re-inspect. |
| action_prevent | Check equipment leaks, jigs, gloves and the condition of the washing liquid. Inspect for leaks and standardise washing and drying conditions. | Check equipment leaks, jigs, gloves and the condition of the washing liquid. Inspect for leaks and standardise washing and drying conditions. |

## mobile/01_scratch — 판정 review

### ko

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | 스크래치가 의심되며, 중앙 및 주변 위치에 4개 발생했습니다. | 의심 수준의 검출 4건이 있어 보류(Hold) 후 재검사합니다. 대표 유형은 스크래치입니다. |
| cause_text | 스크래치는 취급·적재 중 부품 간 접촉, 지그·트레이·컨베이어 마찰, 조립 중 공구 또는 이물 접촉 등이 원인일 수 있습니다. | 원인 후보: 취급·적재 중 부품 간 접촉; 지그·트레이·컨베이어 마찰; 조립 중 공구 또는 이물 접촉 (후보일 뿐 단정하지 않습니다). |
| action_immediate | [작업자 확인 후 실시] 제품을 격리하고 길이·폭·깊이를 외관 기준과 비교합니다. | [작업자 확인 후 실시] 제품을 격리하고 길이·폭·깊이를 외관 기준과 비교한다. |
| action_prevent | 보호재를 사용하고 취급 공정을 점검하며, 지그와 이송 경로의 접촉·이물을 확인합니다. | 지그와 이송 경로의 접촉·이물을 확인한다. 보호재를 사용하고 취급 공정을 점검한다. |

### vi

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Có 4 vết xước được phát hiện ở vị trí dưới phải, dưới trái, giữa và giữa phải, với độ tin cậy cao. | Có 4 phát hiện ở mức nghi ngờ nên giữ lại (Hold) và kiểm tra lại. Loại đại diện là Vết xước. |
| cause_text | Vết xước có thể do các chi tiết va chạm nhau khi thao tác hoặc xếp chồng, ma sát với đồ gá, khay hoặc băng tải, hoặc dụng cụ hoặc dị vật chạm vào khi lắp ráp. | Nguyên nhân có thể gồm: Các chi tiết va chạm nhau khi thao tác hoặc xếp chồng; Ma sát với đồ gá, khay hoặc băng tải; Dụng cụ hoặc dị vật chạm vào khi lắp ráp (chỉ là ứng viên, chưa kết luận). |
| action_immediate | [Thực hiện sau khi công nhân xác nhận] Cách ly sản phẩm và so sánh chiều dài, chiều rộng, độ sâu với tiêu chuẩn ngoại quan. | [Thực hiện sau khi công nhân xác nhận] Cách ly sản phẩm và so sánh chiều dài, chiều rộng, độ sâu với tiêu chuẩn ngoại quan. |
| action_prevent | Sử dụng vật liệu bảo vệ và rà soát công đoạn thao tác. | Kiểm tra điểm tiếp xúc và dị vật trên đồ gá và đường vận chuyển. Sử dụng vật liệu bảo vệ và rà soát công đoạn thao tác. |

### en

| 항목 | qwen3:8b | qwen3-defect |
|---|---|---|
| summary | Scratch defects are suspected based on confidence levels and require human acceptance decision. | 4 suspected area(s) were detected and need re-inspection; they are not asserted as defects. The representative type is Scratch. |
| cause_text | Potential causes include contact between parts during handling or stacking, friction with jigs, trays or conveyors, and contact with tools or foreign objects during assembly. | Possible causes: Contact between parts during handling or stacking; Friction with jigs, trays or conveyors; Contact with tools or foreign objects during assembly (candidates only, not conclusions). |
| action_immediate | [After worker confirmation] Isolate the product and compare length, width and depth with the appearance standard. | [After worker confirmation] Isolate the product and compare length, width and depth with the appearance standard. |
| action_prevent | Check contact points and foreign matter on the jigs and the transfer path. Use protective material and review the handling process. | Check contact points and foreign matter on the jigs and the transfer path. Use protective material and review the handling process. |
