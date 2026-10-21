"""화면·보고서 문구 (한국어 / 베트남어 / 영어). 키가 없으면 한국어로 대신한다."""

LANGS = {'ko': '한국어', 'vi': 'Tiếng Việt', 'en': 'English'}

VERDICT = {
    'ko': {'normal': '정상', 'review': '의심', 'reject': '이상'},
    'vi': {'normal': 'Bình thường', 'review': 'Nghi ngờ', 'reject': 'Bất thường'},
    'en': {'normal': 'Normal', 'review': 'Suspect', 'reject': 'Abnormal'},
}
LEVEL = {
    'ko': {'reject': '이상', 'review': '의심', 'exclude': '제외(오탐)'},
    'vi': {'reject': 'Bất thường', 'review': 'Nghi ngờ', 'exclude': 'Loại bỏ (báo nhầm)'},
    'en': {'reject': 'Abnormal', 'review': 'Suspect', 'exclude': 'Exclude (false alarm)'},
}

# ── 화면 문구 ─────────────────────────────────────────────────────
TEXT = {
    'ko': {
        'title': '부품 불량 사진 분석 에이전트',
        'input': '검사 입력',
        'domain': '검사 대상', 'domain_pcb': 'PCB', 'domain_msdd': '금속 부품', 'domain_mobile': '휴대폰 표면', 'domain_mixed': '혼합 라인',
        'source': '사진', 'source_example': '예시 사진', 'source_upload': '업로드', 'source_inbox': '대기함',
        'part_info': '부품 정보 (품번 · 공정 · 로트)',
        'm_part_no': '품번', 'm_process': '공정', 'm_lot': '로트',
        'case': '케이스', 'image': '사진',
        'whole_part': '같은 부품의 다른 방향 사진도 함께 (부품 단위 판정)',
        'upload_help': '사진 선택 (여러 장이면 한 부품의 여러 방향 사진으로 보고 부품 단위로 판정)',
        'n_files': '{n}장 선택됨',
        'run': '검사 시작',
        'analyzing': '검출 → 판정 → 지식 조회 → 보고서 문장 작성 (Qwen) 중…',
        'writing': 'Qwen 이 문장을 다시 쓰는 중…',
        'writing_on_open': '실시간 라인 기록입니다 — Qwen 이 보고서 문장을 작성하는 중… (몇 초)', 'write_failed': '보고서 문장을 쓰지 못했습니다 ([문장 다시 생성]으로 다시 시도)',
        'guide': '위 [검사 입력]에서 검사 대상과 사진을 고른 뒤 [검사 시작]을 누르세요. 지난 검사는 왼쪽 검사 대장에서 열 수 있습니다. '
                 'AI 가 결함을 찾아 정상 / 의심 / 이상으로 판정하고, 작업자가 확인한 뒤 보고서를 만듭니다.',
        'inbox_help': '{path}/pcb, {path}/msdd 폴더에 사진을 넣고 일괄 검사합니다. 정상은 자동 통과, 의심·이상은 확인 대기 목록에 올라갑니다.',
        'inbox_empty': '대기함이 비어 있습니다',
        'inbox_run': '일괄 검사',
        'inbox_done': '{n}건 검사: 이상 {r} · 의심 {s} · 정상 {o}',
        'inbox_next': '왼쪽 검사 대장에서 확인 대기 건을 열어 확인하세요.',
        'inbox_next_chat': '이상·의심 건은 아래 카드나 왼쪽 검사 대장에서 열어 확인하세요.',
        'part_short': '부품 정보', 'work_panel': '작업 패널',
        'work_panel_empty': '대화에서 사진을 첨부하거나 📷 예시로 검사하면, 결과가 여기 열립니다. 결함 표 수정·문장 편집·확정은 이 패널에서 합니다.',
        'chat_welcome': '안녕하세요. 부품 불량 사진 분석 에이전트입니다.\n\n'
                        '- 📎 로 사진을 첨부하면 검사합니다 (여러 장이면 한 부품의 여러 방향으로 보고 부품 단위 판정)\n'
                        '- 📷 예시 사진, 📥 대기함 일괄 검사도 쓸 수 있습니다\n'
                        '- 검사 후에는 결과에 대해 무엇이든 물어보세요. 판정 수정과 확정은 오른쪽 작업 패널에서 합니다.',
        'chat_ph2': '메시지를 입력하거나 📎 로 사진을 첨부하세요',
        'chat_inspect_default': '이 사진 검사해 줘',
        'chat_example_msg': '예시 사진 검사: {name} ({n}장)',
        'chat_no_result': '아직 열린 검사가 없습니다. 사진을 첨부하거나 📷 예시로 먼저 검사해 주세요.',
        'card_hint': '오른쪽 작업 패널에서 확인·수정한 뒤 확정하세요.',
        'open_panel': '작업 패널에서 열기', 'opened_panel': '작업 패널에 열림',
        'opened_from_ledger': '검사 대장에서 연 기록입니다.',
        'opened_from_live': '실시간 라인에서 연 기록입니다. 오른쪽 작업 패널에서 확인·수정하고 보고서 탭에서 저장하세요.',
        'live_not_found': '실시간 기록 {id} 을(를) 검사 대장에서 아직 찾지 못했습니다. 잠시 후 실시간 화면에서 다시 눌러 주세요.',
        'n_items_ui': '결함 {n}건',
        'panel_show': '작업 패널 열기', 'panel_hide': '작업 패널 닫기', 'panel_close': '작업 패널 닫기',
        'panel_wide_help': '작업 패널 넓게 / 좁게',
        'card_hint_panel': '오른쪽 작업 패널에서 보고서를 확인하고, 고칠 부분은 여기서 요청하세요.',
        'chat_welcome_panel': '안녕하세요. 부품 불량 사진 분석 에이전트입니다.\n\n'
                              '- 📎 로 사진을 첨부하면 검사합니다 (여러 장이면 한 부품의 여러 방향으로 보고 부품 단위 판정)\n'
                              '- 📷 예시 사진, 📥 대기함 일괄 검사도 쓸 수 있습니다\n'
                              '- 결과는 오른쪽 **🛠 작업 패널**에 열립니다. 보고서를 보면서 수정·확정할 수 있습니다\n'
                              '- 보고서 문장을 복사해 붙여 넣고 "이렇게 고쳐줘"라고 하면 수정안을 드립니다',
        'chat_ph_panel': '질문하거나, 보고서 문장을 붙여 넣고 수정을 요청하거나, 📎 로 사진을 첨부하세요',
        'edit_mode': '✏️ 수정 요청', 'edit_mode_help': '켜면 모든 메시지를 보고서 문장 수정 요청으로 처리합니다 (끄면 "고쳐줘" 같은 말로 자동 판단).',
        'edit_thinking': 'Qwen 이 수정안을 만드는 중…', 'edit_proposed': '이렇게 고치면 어떨까요?',
        'edit_none': '바꿀 부분을 찾지 못했습니다. 고칠 문장을 붙여 넣고 어떻게 바꿀지 말해 주세요.',
        'edit_apply': '적용', 'edit_cancel': '취소', 'edit_applied': '✅ 적용됨 — 작업 패널에 반영되었습니다',
        'edit_dismissed': '취소됨',
        'tab_report': '보고서', 'tab_edit': '편집 · 확정',
        'copy_help': '저장될 보고서 그대로입니다. 고칠 문장을 드래그해 복사(Ctrl+C)한 뒤 대화창에 붙여 넣고 수정을 요청하세요.',
        'ledger': '검사 대장 · 기록', 'ledger_filter': '보기', 'f_pending': '작업자 확인 대기', 'f_all': '전체',
        'ledger_search': '검색', 'ledger_search_ph': '파일·부품번호·품번·로트',
        'c_time': '일시', 'c_verdict': '판정', 'c_target': '대상', 'c_status': '처리 상태',
        'ledger_pick': '🔴 이상 · 🟠 의심 · 🟢 정상 · ⏳ 확인 대기 — 누르면 본문에 열립니다.', 'ledger_empty': '기록이 없습니다.',
        'download_md': '기록(md)', 'download_report': '보고서', 'open': '열기',
        'verdict': '판정', 'n_reject': '이상', 'n_review': '의심', 'representative': '대표 유형',
        'original': '원본', 'marked': '결함 위치 표시',
        'tiled': '큰 사진이라 {n}조각으로 나눠 검사했습니다 (타일링).',
        'defects': '검출 결함 — 유형과 판정을 수정할 수 있습니다',
        'col_view': '사진', 'col_type': '유형', 'col_name': '이름', 'col_level': '판정', 'col_conf': '신뢰도',
        'col_pos': '위치', 'col_size': '크기(px)', 'col_reason': '판정 근거',
        'apply_edits': '수정 반영', 'rewrite': '문장 다시 생성 (Qwen)',
        'crops': '결함 확대 이미지 (판정 근거)',
        'no_defects': '기준 이상의 결함이 검출되지 않았습니다.',
        'text': '보고서 문장 — 직접 고칠 수 있습니다',
        'summary': '요약', 'feature': '특징', 'causes': '원인 후보', 'act_now': '즉시 조치', 'act_prevent': '재발 방지',
        'lang_mismatch': '보고서 문장은 {name}로 작성돼 있습니다. 바꾸려면 [문장 다시 생성]을 누르세요.',
        'decision': '처리',
        'next_reject': '누르면 부적합 보고서(NCR)를 미리보기 창에 띄웁니다. 확인 후 [저장]하면 outputs/abnormal/ 에 저장하고 검사 대장에 기록합니다.',
        'next_review': '누르면 재검사 의뢰서(Hold)를 미리보기 창에 띄웁니다. 확인 후 [저장]하면 outputs/second_inspection/ 에 저장합니다. '
                       '지금 실물을 확인했다면 위 표에서 판정을 이상/제외로 바꾸고 [수정 반영]을 누르세요.',
        'next_normal': '누르면 확인 창이 뜨고, [저장]하면 정상으로 검사 대장에만 기록합니다.',
        'confirm_reject': 'NCR 미리보기', 'confirm_review': '재검사 의뢰서 미리보기',
        'confirm_normal': '정상 처리', 'false_positive': '오탐 기각 (정상 처리)',
        'preview_title': '보고서 미리보기', 'preview_making': '보고서를 만드는 중…',
        'preview_help': '저장될 문서 그대로입니다. 고칠 곳이 있으면 [돌아가서 수정]을 눌러 결함 표나 문장을 고친 뒤 다시 여세요.',
        'preview_normal': '보고서 없이 정상으로 검사 대장에 기록합니다.',
        'preview_save': '저장', 'preview_back': '돌아가서 수정',
        'processed': '처리 완료', 'saved_to': '저장 위치', 'download': '보고서 다운로드 (.docx)',
        'history': '검사 대장 ({n}건)', 'download_xlsx': '검사 대장 엑셀 다운로드',
        'records_help': '모든 검사는 outputs/inspection_ledger.xlsx (영어) 와 outputs/records/<날짜>/*.md 에 저장됩니다.',
        'chat': '에이전트에게 질문',
        'chat_help': '지금 검사 결과와 지식베이스를 근거로 답합니다. 판정은 바꾸지 않습니다.',
        'chat_ph': '예: 흑점은 세척하면 없어져?',
        'chat_error': 'Qwen 응답 실패 — Ollama 가 실행 중인지 확인하세요',
        'q_why': '왜 이 판정이야?', 'q_cause': '대표 결함 원인은?', 'q_check': '지금 뭘 확인해야 해?', 'quick_q': '빠른 질문',
        'guide_title': '이렇게 물어보세요',
        'guide_intro': '지금 열린 검사 결과와 지식베이스를 근거로 답합니다. 예시를 누르면 바로 질문이 보내집니다.',
        'g_verdict': '🔎 판정 이유', 'g_defects': '📍 결함 내용', 'g_cause': '🧪 원인', 'g_action': '🛠 조치·확인',
        'g_lang': '🌐 다른 언어로', 'g_edit': '✏️ 보고서 문장 수정', 'g_this_defect': '이 결함',
        'ex_why': '왜 이 판정이 나왔어?', 'ex_where': '결함이 어디에 몇 개 있어?', 'ex_cause': '{name}은(는) 왜 생겨?',
        'ex_check': '지금 작업자가 뭘 확인해야 해?', 'ex_lang': '이 결과를 베트남어로 설명해 줘',
        'ex_edit': '요약을 한 문장으로 짧게 고쳐줘',
        'guide_cannot': '⚠ 판정 변경은 대화로 할 수 없습니다 (작업 패널의 결함 표에서). 다른 검사·과거 기록 조회, 지식베이스 밖의 내용은 아직 답하지 못합니다.',
        'guide_close': '알겠어요 (닫기)', 'guide_never': '다시 보지 않기',
    },
    'vi': {
        'title': 'Tác tử AI phân tích ảnh lỗi linh kiện',
        'input': 'Thông tin kiểm tra',
        'domain': 'Đối tượng kiểm tra', 'domain_pcb': 'PCB', 'domain_msdd': 'Linh kiện kim loại', 'domain_mobile': 'Bề mặt điện thoại', 'domain_mixed': 'dây chuyền hỗn hợp',
        'source': 'Ảnh', 'source_example': 'Ảnh mẫu', 'source_upload': 'Tải lên', 'source_inbox': 'Hộp chờ',
        'part_info': 'Thông tin linh kiện (mã · công đoạn · lô)',
        'm_part_no': 'Mã sản phẩm', 'm_process': 'Công đoạn', 'm_lot': 'Lô',
        'case': 'Trường hợp', 'image': 'Ảnh',
        'whole_part': 'Kèm ảnh các hướng khác của cùng linh kiện (đánh giá theo linh kiện)',
        'upload_help': 'Chọn ảnh (nhiều ảnh = các hướng của một linh kiện, đánh giá theo linh kiện)',
        'n_files': 'Đã chọn {n} ảnh',
        'run': 'Bắt đầu kiểm tra',
        'analyzing': 'Đang phát hiện → đánh giá → tra cứu → viết báo cáo (Qwen)…',
        'writing': 'Qwen đang viết lại…',
        'writing_on_open': 'Bản ghi từ dây chuyền — Qwen đang viết nội dung báo cáo… (vài giây)', 'write_failed': 'Không viết được nội dung báo cáo (thử lại bằng [Viết lại])',
        'guide': 'Chọn đối tượng và ảnh ở [Thông tin kiểm tra] phía trên rồi nhấn [Bắt đầu kiểm tra]. Các lần kiểm tra trước có thể mở từ sổ kiểm tra bên trái. '
                 'AI tìm lỗi và đánh giá Bình thường / Nghi ngờ / Bất thường; công nhân xác nhận rồi tạo báo cáo.',
        'inbox_help': 'Đặt ảnh vào thư mục {path}/pcb, {path}/msdd rồi kiểm tra hàng loạt. Bình thường tự động cho qua, Nghi ngờ/Bất thường vào danh sách chờ xác nhận.',
        'inbox_empty': 'Hộp chờ trống',
        'inbox_run': 'Kiểm tra hàng loạt',
        'inbox_done': 'Đã kiểm tra {n}: Bất thường {r} · Nghi ngờ {s} · Bình thường {o}',
        'inbox_next': 'Mở các mục chờ xác nhận trong sổ kiểm tra bên trái.',
        'inbox_next_chat': 'Mở các mục Bất thường/Nghi ngờ từ thẻ bên dưới hoặc sổ kiểm tra bên trái.',
        'part_short': 'Thông tin linh kiện', 'work_panel': 'Bảng làm việc',
        'work_panel_empty': 'Đính kèm ảnh trong hội thoại hoặc kiểm tra bằng 📷 ảnh mẫu, kết quả sẽ mở ở đây. Sửa bảng lỗi, chỉnh nội dung và xác nhận tại bảng này.',
        'chat_welcome': 'Xin chào. Tôi là tác tử AI phân tích ảnh lỗi linh kiện.\n\n'
                        '- Đính kèm ảnh bằng 📎 để kiểm tra (nhiều ảnh = các hướng của một linh kiện)\n'
                        '- Có thể dùng 📷 ảnh mẫu và 📥 kiểm tra hàng loạt\n'
                        '- Sau khi kiểm tra, hãy hỏi bất cứ điều gì về kết quả. Sửa và xác nhận ở bảng làm việc bên phải.',
        'chat_ph2': 'Nhập tin nhắn hoặc đính kèm ảnh bằng 📎',
        'chat_inspect_default': 'Hãy kiểm tra ảnh này',
        'chat_example_msg': 'Kiểm tra ảnh mẫu: {name} ({n} ảnh)',
        'chat_no_result': 'Chưa có kết quả kiểm tra nào được mở. Hãy đính kèm ảnh hoặc dùng 📷 ảnh mẫu trước.',
        'card_hint': 'Kiểm tra, chỉnh sửa rồi xác nhận ở bảng làm việc bên phải.',
        'open_panel': 'Mở trong bảng làm việc', 'opened_panel': 'Đang mở',
        'opened_from_ledger': 'Hồ sơ được mở từ sổ kiểm tra.',
        'opened_from_live': 'Hồ sơ được mở từ dây chuyền thời gian thực. Kiểm tra và sửa ở bảng làm việc bên phải, rồi lưu ở thẻ Báo cáo.',
        'live_not_found': 'Chưa tìm thấy hồ sơ {id} trong sổ kiểm tra. Hãy nhấn lại trên màn hình thời gian thực sau giây lát.',
        'n_items_ui': '{n} lỗi',
        'panel_show': 'Mở bảng làm việc', 'panel_hide': 'Đóng bảng làm việc', 'panel_close': 'Đóng bảng làm việc',
        'panel_wide_help': 'Bảng làm việc rộng / hẹp',
        'card_hint_panel': 'Xem báo cáo ở bảng làm việc bên phải, yêu cầu chỉnh sửa tại đây.',
        'chat_welcome_panel': 'Xin chào. Tôi là tác tử AI phân tích ảnh lỗi linh kiện.\n\n'
                              '- Đính kèm ảnh bằng 📎 để kiểm tra (nhiều ảnh = các hướng của một linh kiện)\n'
                              '- Có thể dùng 📷 ảnh mẫu và 📥 kiểm tra hàng loạt\n'
                              '- Kết quả mở ở **🛠 bảng làm việc** bên phải để xem báo cáo, chỉnh sửa và xác nhận\n'
                              '- Dán câu trong báo cáo và nói "hãy sửa thế này", tôi sẽ đề xuất bản sửa',
        'chat_ph_panel': 'Đặt câu hỏi, dán câu trong báo cáo để yêu cầu sửa, hoặc đính kèm ảnh bằng 📎',
        'edit_mode': '✏️ Yêu cầu sửa', 'edit_mode_help': 'Bật: mọi tin nhắn được xử lý như yêu cầu sửa báo cáo (tắt: tự nhận biết từ "sửa", "đổi"...).',
        'edit_thinking': 'Qwen đang soạn bản sửa…', 'edit_proposed': 'Sửa như sau được không?',
        'edit_none': 'Không tìm thấy phần cần sửa. Hãy dán câu cần sửa và nói muốn sửa thế nào.',
        'edit_apply': 'Áp dụng', 'edit_cancel': 'Hủy', 'edit_applied': '✅ Đã áp dụng — đã cập nhật bảng làm việc',
        'edit_dismissed': 'Đã hủy',
        'tab_report': 'Báo cáo', 'tab_edit': 'Chỉnh sửa · Xác nhận',
        'copy_help': 'Đây là báo cáo sẽ được lưu. Kéo chọn câu cần sửa, sao chép (Ctrl+C), dán vào ô hội thoại và yêu cầu sửa.',
        'ledger': 'Sổ kiểm tra · Hồ sơ', 'ledger_filter': 'Hiển thị', 'f_pending': 'Chờ công nhân xác nhận',
        'f_all': 'Tất cả', 'ledger_search': 'Tìm kiếm', 'ledger_search_ph': 'Tệp · mã linh kiện · mã SP · lô',
        'c_time': 'Thời gian', 'c_verdict': 'Kết quả', 'c_target': 'Đối tượng', 'c_status': 'Trạng thái',
        'ledger_pick': '🔴 Bất thường · 🟠 Nghi ngờ · 🟢 Bình thường · ⏳ Chờ xác nhận — nhấn để mở.', 'ledger_empty': 'Chưa có hồ sơ.',
        'download_md': 'Hồ sơ (md)', 'download_report': 'Báo cáo', 'open': 'Mở',
        'verdict': 'Kết quả', 'n_reject': 'Bất thường', 'n_review': 'Nghi ngờ', 'representative': 'Loại lỗi chính',
        'original': 'Ảnh gốc', 'marked': 'Vị trí lỗi',
        'tiled': 'Ảnh lớn nên được chia thành {n} phần để kiểm tra.',
        'defects': 'Lỗi phát hiện — có thể sửa loại lỗi và kết quả',
        'col_view': 'Ảnh', 'col_type': 'Loại', 'col_name': 'Tên', 'col_level': 'Kết quả', 'col_conf': 'Độ tin cậy',
        'col_pos': 'Vị trí', 'col_size': 'Kích thước (px)', 'col_reason': 'Căn cứ',
        'apply_edits': 'Áp dụng chỉnh sửa', 'rewrite': 'Viết lại nội dung (Qwen)',
        'crops': 'Ảnh phóng to vùng lỗi (căn cứ đánh giá)',
        'no_defects': 'Không phát hiện lỗi vượt ngưỡng.',
        'text': 'Nội dung báo cáo — có thể chỉnh sửa trực tiếp',
        'summary': 'Tóm tắt', 'feature': 'Đặc điểm', 'causes': 'Nguyên nhân có thể', 'act_now': 'Xử lý ngay',
        'act_prevent': 'Phòng ngừa tái phát',
        'lang_mismatch': 'Nội dung báo cáo đang viết bằng {name}. Nhấn [Viết lại nội dung] để đổi ngôn ngữ.',
        'decision': 'Xử lý',
        'next_reject': 'Nhấn để xem trước báo cáo không phù hợp (NCR). Sau khi kiểm tra, nhấn [Lưu] để lưu vào outputs/abnormal/ và ghi vào sổ kiểm tra.',
        'next_review': 'Nhấn để xem trước phiếu yêu cầu tái kiểm (Hold). Nhấn [Lưu] để lưu vào outputs/second_inspection/. '
                       'Nếu đã kiểm tra thực tế, hãy đổi kết quả trong bảng rồi nhấn [Áp dụng chỉnh sửa].',
        'next_normal': 'Nhấn để mở cửa sổ xác nhận; [Lưu] sẽ chỉ ghi vào sổ kiểm tra là Bình thường.',
        'confirm_reject': 'Xem trước NCR', 'confirm_review': 'Xem trước phiếu tái kiểm',
        'confirm_normal': 'Xử lý Bình thường', 'false_positive': 'Báo nhầm (xử lý Bình thường)',
        'preview_title': 'Xem trước báo cáo', 'preview_making': 'Đang tạo báo cáo…',
        'preview_help': 'Đây chính là tài liệu sẽ được lưu. Nếu cần sửa, nhấn [Quay lại sửa], sửa bảng lỗi hoặc nội dung rồi mở lại.',
        'preview_normal': 'Ghi vào sổ kiểm tra là Bình thường, không tạo báo cáo.',
        'preview_save': 'Lưu', 'preview_back': 'Quay lại sửa',
        'processed': 'Đã xử lý', 'saved_to': 'Lưu tại', 'download': 'Tải báo cáo (.docx)',
        'history': 'Sổ kiểm tra ({n})', 'download_xlsx': 'Tải sổ kiểm tra (Excel)',
        'records_help': 'Mọi lần kiểm tra được lưu tại outputs/inspection_ledger.xlsx (tiếng Anh) và outputs/records/<ngày>/*.md.',
        'chat': 'Hỏi tác tử AI',
        'chat_help': 'Trả lời dựa trên kết quả kiểm tra hiện tại và cơ sở tri thức. Không thay đổi kết quả đánh giá.',
        'chat_ph': 'VD: Đốm đen có rửa sạch được không?',
        'chat_error': 'Qwen không phản hồi — hãy kiểm tra Ollama đang chạy',
        'q_why': 'Vì sao có kết quả này?', 'q_cause': 'Nguyên nhân lỗi chính?', 'q_check': 'Cần kiểm tra gì bây giờ?',
        'quick_q': 'Câu hỏi nhanh',
        'guide_title': 'Bạn có thể hỏi như sau',
        'guide_intro': 'Trả lời dựa trên kết quả kiểm tra đang mở và cơ sở tri thức. Nhấn vào ví dụ để gửi ngay.',
        'g_verdict': '🔎 Lý do đánh giá', 'g_defects': '📍 Nội dung lỗi', 'g_cause': '🧪 Nguyên nhân', 'g_action': '🛠 Xử lý · kiểm tra',
        'g_lang': '🌐 Ngôn ngữ khác', 'g_edit': '✏️ Sửa câu trong báo cáo', 'g_this_defect': 'lỗi này',
        'ex_why': 'Vì sao có kết quả đánh giá này?', 'ex_where': 'Lỗi ở đâu và có bao nhiêu?', 'ex_cause': 'Vì sao xảy ra {name}?',
        'ex_check': 'Công nhân cần kiểm tra gì bây giờ?', 'ex_lang': 'Hãy giải thích kết quả này bằng tiếng Anh',
        'ex_edit': 'Hãy sửa phần tóm tắt thành một câu ngắn',
        'guide_cannot': '⚠ Không thể đổi kết quả đánh giá qua hội thoại (hãy dùng bảng lỗi trong bảng làm việc). Chưa hỗ trợ tra cứu kiểm tra khác/lịch sử và nội dung ngoài cơ sở tri thức.',
        'guide_close': 'Đã hiểu (đóng)', 'guide_never': 'Không hiện lại',
    },
    'en': {
        'title': 'Part Defect Photo Analysis Agent',
        'input': 'Inspection input',
        'domain': 'Inspection target', 'domain_pcb': 'PCB', 'domain_msdd': 'Metal part', 'domain_mobile': 'Phone surface', 'domain_mixed': 'Mixed Line',
        'source': 'Photo', 'source_example': 'Examples', 'source_upload': 'Upload', 'source_inbox': 'Inbox',
        'part_info': 'Part info (part no. · process · lot)',
        'm_part_no': 'Part no.', 'm_process': 'Process', 'm_lot': 'Lot',
        'case': 'Case', 'image': 'Photo',
        'whole_part': 'Include other views of the same part (part-level judgment)',
        'upload_help': 'Select photos (multiple photos = views of one part, judged per part)',
        'n_files': '{n} selected',
        'run': 'Start inspection',
        'analyzing': 'Detecting → judging → looking up knowledge → writing report (Qwen)…',
        'writing': 'Qwen is rewriting…',
        'writing_on_open': 'Live line record — Qwen is writing the report text… (a few seconds)', 'write_failed': 'Could not write the report text (try [Rewrite] again)',
        'guide': 'Choose a target and a photo in [Inspection input] above, then press [Start inspection]. Past inspections can be opened from the ledger on the left. '
                 'The AI finds defects and judges Normal / Suspect / Abnormal; a worker confirms before the report is made.',
        'inbox_help': 'Put photos into {path}/pcb and {path}/msdd, then run a batch inspection. Normal passes automatically; Suspect/Abnormal go to the confirmation queue.',
        'inbox_empty': 'Inbox is empty',
        'inbox_run': 'Batch inspection',
        'inbox_done': '{n} inspected: Abnormal {r} · Suspect {s} · Normal {o}',
        'inbox_next': 'Open the waiting items from the ledger on the left.',
        'inbox_next_chat': 'Open Abnormal/Suspect items from the cards below or the ledger on the left.',
        'part_short': 'Part info', 'work_panel': 'Work panel',
        'work_panel_empty': 'Attach a photo in the chat or inspect a 📷 example; the result opens here. Edit the defect table, edit text and confirm in this panel.',
        'chat_welcome': 'Hello. I am the part defect photo analysis agent.\n\n'
                        '- Attach photos with 📎 to inspect (multiple photos = views of one part)\n'
                        '- You can also use 📷 examples and 📥 batch inspection\n'
                        '- After an inspection, ask me anything about the result. Edits and confirmation happen in the work panel on the right.',
        'chat_ph2': 'Type a message or attach photos with 📎',
        'chat_inspect_default': 'Please inspect this photo',
        'chat_example_msg': 'Inspect example: {name} ({n} photo(s))',
        'chat_no_result': 'No inspection is open yet. Attach a photo or inspect a 📷 example first.',
        'card_hint': 'Check, edit and confirm in the work panel on the right.',
        'open_panel': 'Open in work panel', 'opened_panel': 'Open now',
        'opened_from_ledger': 'Record opened from the ledger.',
        'opened_from_live': 'Record opened from the live line. Check and correct it in the work panel on the right, then save it from the Report tab.',
        'live_not_found': 'Record {id} is not in the ledger yet. Click it again on the live screen in a moment.',
        'n_items_ui': '{n} defect(s)',
        'panel_show': 'Open work panel', 'panel_hide': 'Close work panel', 'panel_close': 'Close work panel',
        'panel_wide_help': 'Wider / narrower work panel',
        'card_hint_panel': 'Check the report in the work panel on the right and ask for changes here.',
        'chat_welcome_panel': 'Hello. I am the part defect photo analysis agent.\n\n'
                              '- Attach photos with 📎 to inspect (multiple photos = views of one part)\n'
                              '- You can also use 📷 examples and 📥 batch inspection\n'
                              '- Results open in the **🛠 work panel** on the right — read the report, edit and confirm\n'
                              '- Paste a sentence from the report and say how to change it — I will propose an edit',
        'chat_ph_panel': 'Ask a question, paste report text to request an edit, or attach photos with 📎',
        'edit_mode': '✏️ Edit request', 'edit_mode_help': 'On: every message is treated as a report edit request (off: detected from words like "change", "rewrite").',
        'edit_thinking': 'Qwen is drafting an edit…', 'edit_proposed': 'How about this change?',
        'edit_none': 'Could not find what to change. Paste the sentence and say how to change it.',
        'edit_apply': 'Apply', 'edit_cancel': 'Cancel', 'edit_applied': '✅ Applied — the work panel is updated',
        'edit_dismissed': 'Cancelled',
        'tab_report': 'Report', 'tab_edit': 'Edit · Confirm',
        'copy_help': 'This is the report as it will be saved. Select a sentence, copy it (Ctrl+C), paste it into the chat and ask for a change.',
        'ledger': 'Ledger · Records', 'ledger_filter': 'Show', 'f_pending': 'Waiting for worker', 'f_all': 'All',
        'ledger_search': 'Search', 'ledger_search_ph': 'File · part ID · part no. · lot',
        'c_time': 'Time', 'c_verdict': 'Verdict', 'c_target': 'Target', 'c_status': 'Status',
        'ledger_pick': '🔴 Abnormal · 🟠 Suspect · 🟢 Normal · ⏳ Waiting — click to open.', 'ledger_empty': 'No records yet.',
        'download_md': 'Record (md)', 'download_report': 'Report', 'open': 'Open',
        'verdict': 'Verdict', 'n_reject': 'Abnormal', 'n_review': 'Suspect', 'representative': 'Main defect',
        'original': 'Original', 'marked': 'Defect locations',
        'tiled': 'Large photo: inspected in {n} tiles.',
        'defects': 'Detected defects — type and verdict can be edited',
        'col_view': 'View', 'col_type': 'Class', 'col_name': 'Name', 'col_level': 'Verdict', 'col_conf': 'Confidence',
        'col_pos': 'Position', 'col_size': 'Size (px)', 'col_reason': 'Basis',
        'apply_edits': 'Apply edits', 'rewrite': 'Rewrite text (Qwen)',
        'crops': 'Defect close-ups (evidence)',
        'no_defects': 'No defects above the threshold.',
        'text': 'Report text — editable',
        'summary': 'Summary', 'feature': 'Description', 'causes': 'Possible causes', 'act_now': 'Immediate action',
        'act_prevent': 'Prevention',
        'lang_mismatch': 'Report text is written in {name}. Press [Rewrite text] to change the language.',
        'decision': 'Action',
        'next_reject': 'Opens a preview of the nonconformance report (NCR). After checking, [Save] stores it in outputs/abnormal/ and logs it in the ledger.',
        'next_review': 'Opens a preview of the re-inspection request (Hold). [Save] stores it in outputs/second_inspection/. '
                       'If you already checked the part, change the verdict in the table and press [Apply edits].',
        'next_normal': 'Opens a confirmation window; [Save] logs it as Normal in the ledger only.',
        'confirm_reject': 'Preview NCR', 'confirm_review': 'Preview re-inspection request',
        'confirm_normal': 'Mark as Normal', 'false_positive': 'False alarm (treat as Normal)',
        'preview_title': 'Report preview', 'preview_making': 'Creating the report…',
        'preview_help': 'This is exactly the document that will be saved. To change something, press [Back to edit], edit the table or text, and open it again.',
        'preview_normal': 'Logged as Normal in the ledger; no report is created.',
        'preview_save': 'Save', 'preview_back': 'Back to edit',
        'processed': 'Done', 'saved_to': 'Saved to', 'download': 'Download report (.docx)',
        'history': 'Inspection ledger ({n})', 'download_xlsx': 'Download ledger (Excel)',
        'records_help': 'Every inspection is saved to outputs/inspection_ledger.xlsx and outputs/records/<date>/*.md.',
        'chat': 'Ask the agent',
        'chat_help': 'Answers from the current inspection result and knowledge base. It cannot change the verdict.',
        'chat_ph': 'e.g. Will the dark spot wash off?',
        'chat_error': 'Qwen did not respond — check that Ollama is running',
        'q_why': 'Why this verdict?', 'q_cause': 'Main cause?', 'q_check': 'What should I check now?',
        'quick_q': 'Quick questions',
        'guide_title': 'What you can ask',
        'guide_intro': 'Answers are based on the open inspection result and the knowledge base. Click an example to send it.',
        'g_verdict': '🔎 Verdict reason', 'g_defects': '📍 Defect details', 'g_cause': '🧪 Causes', 'g_action': '🛠 Actions · checks',
        'g_lang': '🌐 Other language', 'g_edit': '✏️ Edit report text', 'g_this_defect': 'this defect',
        'ex_why': 'Why did it get this verdict?', 'ex_where': 'Where are the defects and how many?', 'ex_cause': 'Why does {name} happen?',
        'ex_check': 'What should the worker check now?', 'ex_lang': 'Explain this result in Vietnamese',
        'ex_edit': 'Rewrite the summary as one short sentence',
        'guide_cannot': '⚠ The verdict cannot be changed by chat (use the defect table in the work panel). Other inspections, past records and topics outside the knowledge base are not supported yet.',
        'guide_close': 'Got it (close)', 'guide_never': "Don't show again",
    },
}

STATUS = {   # 처리 상태 (키는 records.jsonl 에 저장)
    'ko': {'pending': '작업자 확인 대기', 'sent_wait': '작업자 확인 완료 → 관리자 전송 대기',
           'auto_reject': '관리자 전송 대기 (작업자 미확인)', 'review_wait': '재검사 대기 (Hold)',
           'normal': '정상 통과', 'normal_auto': '정상 통과 (일괄 자동)',
           'fp': '오탐 기각 → 정상 처리 (재학습 샘플 보관)'},
    'vi': {'pending': 'Chờ công nhân xác nhận', 'sent_wait': 'Công nhân đã xác nhận → chờ gửi quản lý',
           'auto_reject': 'Chờ gửi quản lý (chưa xác nhận)', 'review_wait': 'Chờ tái kiểm (Hold)',
           'normal': 'Bình thường', 'normal_auto': 'Bình thường (tự động hàng loạt)',
           'fp': 'Báo nhầm → xử lý Bình thường (lưu mẫu huấn luyện)'},
    'en': {'pending': 'Waiting for worker', 'sent_wait': 'Worker confirmed → waiting to send to manager',
           'auto_reject': 'Waiting to send to manager (not confirmed)', 'review_wait': 'On hold (re-inspection)',
           'normal': 'Passed (normal)', 'normal_auto': 'Passed (batch, automatic)',
           'fp': 'False alarm → treated as normal (kept for retraining)'},
}
PROCESS = ['', 'machining', 'heat', 'surface', 'cleaning', 'etching', 'plating', 'drilling', 'assembly', 'packing', 'other']
PROCESS_NAME = {
    'ko': {'': '-', 'machining': '가공', 'heat': '열처리', 'surface': '표면처리', 'cleaning': '세척', 'etching': '식각',
           'plating': '도금', 'drilling': '드릴', 'assembly': '조립', 'packing': '포장', 'other': '기타'},
    'vi': {'': '-', 'machining': 'Gia công', 'heat': 'Nhiệt luyện', 'surface': 'Xử lý bề mặt', 'cleaning': 'Rửa',
           'etching': 'Ăn mòn', 'plating': 'Mạ', 'drilling': 'Khoan', 'assembly': 'Lắp ráp', 'packing': 'Đóng gói',
           'other': 'Khác'},
    'en': {'': '-', 'machining': 'Machining', 'heat': 'Heat treatment', 'surface': 'Surface treatment',
           'cleaning': 'Cleaning', 'etching': 'Etching', 'plating': 'Plating', 'drilling': 'Drilling',
           'assembly': 'Assembly', 'packing': 'Packing', 'other': 'Other'},
}

# ── 보고서·기록 문구 ───────────────────────────────────────────────
REPORT = {
    'ko': {
        'manager_title': '부적합 보고서 (NCR)',
        'manager_note': '※ AI 에이전트가 작성한 초안입니다. 작업자 확인 후 품질 담당자에게 전송합니다. '
                        '1·4·6·7항은 8D 의 D2·D3·D4·D5/D7 입력으로 그대로 쓸 수 있습니다.',
        'inspect_title': '재검사 의뢰서 (Hold)',
        'inspect_note': '※ AI 가 의심 영역을 찾았습니다. 재검사 결과가 나올 때까지 부품을 보류(Hold)하고, 실물을 확인해 합격 / 불합격을 판정해 주세요.',
        'h_info': '1. 검사 정보 및 판정', 'h_info2': '1. 검사 정보',
        'h_photo': '2. 불량 사진', 'h_photo2': '2. 의심 영역 사진',
        'h_defects': '3. 검출 결함', 'h_items': '3. 검수 항목',
        'h_feature': '4. 결함 특징', 'h_ai': '4. AI 설명',
        'h_causes': '5. 원인 후보', 'h_actions': '6. 조치 방법',
        'h_process': '7. 처리 안내 · 확인 · 전송', 'h_result': '5. 검수 결과',
        'date': '작성 일시', 'part_info': '부품 정보 (품번·공정·로트)', 'target': '검사 대상', 'part_no': '부품 번호',
        'photos': '검사 사진', 'file': '원본 파일', 'inference': '추론 방식', 'tiled': '타일링 ({n}조각)',
        'verdict': '판정', 'representative': '대표 유형', 'count': '검출 수',
        'count_val': '{n}건 (이상 {r} / 의심 {s})', 'n_items': '{n}건',
        'c_no': 'No', 'c_view': '사진', 'c_type': '유형', 'c_sev': '심각도', 'c_pos': '위치', 'c_size': '크기(px)',
        'c_conf': '신뢰도', 'c_level': '판정', 'c_reason': '판정 근거',
        'c_stype': '의심 유형', 'c_sreason': '의심 사유', 'c_how': '확인 방법', 'c_check': '검수 결과',
        'check_box': '□ 합격  □ 불합격', 'how_default': '육안 확인',
        'original': '원본', 'marked': '결함 위치 표시',
        'crops': '결함 확대 이미지 (판정 근거)', 'crops2': '의심 영역 확대 이미지',
        'a_kind': '구분', 'a_content': '내용', 'a_now': '즉시 조치', 'a_prevent': '재발 방지', 'a_ref': '[기준]',
        'a_ref_now': '즉시', 'a_ref_check': '점검', 'a_ref_prevent': '방지',
        'w_confirm': '작업자 확인', 'w_confirm_v': '□ 확정    □ 유형 수정    □ 오탐 기각',
        'w_edit': '수정 내용', 'w_sign': '확인자 / 서명 / 일시', 'w_send': '관리자 전송 (수신자 / 일시)',
        'f_final': '최종 판정',
        'f_final_v': '□ 합격 (오탐) → Hold 해제, 정상 처리, 재학습용 정상 샘플로 보관\n□ 불합격 → 부적합 보고서(NCR) 발행',
        'f_memo': '재검사 메모', 'f_sign': '재검사자 / 서명 / 일시', 'applies_to': '해당',
        'm_part_no': '품번', 'm_process': '공정', 'm_lot': '로트',
        # NCR (이상)
        'ncr_no': 'NCR 번호', 'ncr_status': '상태', 'ncr_status_v': '■ Open  □ Closed',
        'n_h_problem': '1. 부적합 내용 (5W2H · 8D D2)', 'n_h_photo': '2. 증거 사진', 'n_h_defects': '3. 결함 상세',
        'n_h_contain': '4. 긴급 조치 (봉쇄 · 8D D3)', 'n_h_dispo': '5. 처리 결정 (Disposition)',
        'n_h_cause': '6. 원인 후보 (8D D4 입력)', 'n_h_corrective': '7. 시정 및 재발 방지 (8D D5 · D7 제안)',
        'n_h_8d': '8. 8D 연계', 'n_h_sign': '9. 확인 및 승인',
        'w_what': '무엇 (What)', 'w_where': '어디 (Where)', 'w_when': '언제 (When)', 'w_who': '누가 발견 (Who)',
        'w_who_v': 'AI 외관 검사 에이전트 → 작업자 확인', 'w_how': '어떻게 발견 (How)',
        'w_how_v': '사진 검사 (YOLO 검출 모델, 최고 신뢰도 {conf:.2f})', 'w_howmany': '얼마나 (How many)',
        'w_req': '기준 (Requirement)',
        'w_req_v': '신뢰도 {reject} 이상 검출 = 이상(부적합), {review}–{reject} = 의심 (유형별 규칙은 지식 파일 기준)',
        't_action': '조치 항목', 't_owner': '담당', 't_date': '완료일',
        'contain_1': '□ 해당 부품 격리, 부적합 식별표 부착', 'contain_2': '□ 같은 로트 재고·진행품 확인 및 선별',
        'contain_3': '□ 해당 공정 설비·조건 점검',
        'dispo': '처리 방법',
        'dispo_v': '□ 특채 (Use as is)   □ 재작업 (Rework)   □ 수리 (Repair)\n□ 폐기 (Scrap)   □ 반품 (Return to supplier)',
        'dispo_qty': '대상 수량', 'dispo_by': '결정자 / 일자',
        'cause_note': '※ AI 가 결함 유형으로 추정한 후보입니다. 근본 원인은 8D D4 (5 Why, 4M 분석)에서 확정합니다.',
        'd8_yes': '8D 발행 권고 — 사유: {why}', 'd8_no': '8D 발행 권고 없음 (같은 결함이 반복되면 발행)',
        'd8_why_critical': '치명 결함', 'd8_why_multi': '여러 유형 동시 발생', 'd8_why_surface': '표면 전체에 분포',
        'd8_step': '8D 단계', 'd8_state': '이 보고서와의 연결',
        'd8_d1': '팀 구성', 'd8_d2': '문제 기술', 'd8_d3': '봉쇄 조치', 'd8_d4': '근본 원인', 'd8_d5': '시정 조치 선정',
        'd8_d6': '시정 조치 실행·효과 확인', 'd8_d7': '재발 방지', 'd8_d8': '종결·팀 인정',
        'd8_todo': '□ 8D 에서 진행', 'd8_done': '■ 완료 — {sec}항', 'd8_partial': '◐ 진행 중 — {sec}항 확인',
        'd8_input': '◐ 후보·제안 — {sec}항',
        'd8_issue': '8D 발행', 'd8_issue_v': '□ 발행 (8D 번호: ____________)   □ 미발행',
        's_role': '구분', 's_name': '이름', 's_sign': '서명', 's_date': '일자', 's_author': '작성 (작업자 확인)',
        's_review': '검토 (품질 담당)', 's_approve': '승인 (관리자)', 's_close': '종결 확인',
        # 재검사 의뢰서 (의심)
        'rir_no': '의뢰 번호', 'hold_status': 'Hold 상태', 'hold_status_v': '■ 보류 (Hold)  □ 해제 (Release)',
        'hold_banner': 'HOLD — 재검사 결과가 나올 때까지 다음 공정으로 보내지 마세요.',
        'hold_rule': 'AI 판정 기준: 신뢰도 {review}–{reject} 구간의 검출이거나, 유형별 규칙(크기·분포 등)으로 확정하기 어려운 검출은 의심으로 분류합니다.',
        'r_h_reason': '1. 의뢰 사유', 'r_h_photo': '2. 의심 영역 사진', 'r_h_items': '3. 재검사 항목', 'r_h_ai': '4. AI 설명',
        'r_h_result': '5. 재검사 결과 및 Hold 처리',
        'r_method': '재검사 방법', 'r_method_v': '□ 육안   □ 확대경·현미경   □ 측정   □ 기타 (        )',
        'r_release': 'Hold 해제 승인 (이름 / 서명 / 일시)',
    },
    'vi': {
        'manager_title': 'Báo cáo không phù hợp (NCR)',
        'manager_note': '※ Bản nháp do tác tử AI soạn. Gửi cho bộ phận chất lượng sau khi công nhân xác nhận. '
                        'Mục 1, 4, 6, 7 dùng trực tiếp làm đầu vào D2, D3, D4, D5/D7 của 8D.',
        'inspect_title': 'Phiếu yêu cầu tái kiểm (Hold)',
        'inspect_note': '※ AI đã tìm thấy vùng nghi ngờ. Giữ linh kiện lại (Hold) cho đến khi có kết quả tái kiểm, kiểm tra thực tế rồi đánh giá Đạt / Không đạt.',
        'h_info': '1. Thông tin kiểm tra và kết quả', 'h_info2': '1. Thông tin kiểm tra',
        'h_photo': '2. Ảnh lỗi', 'h_photo2': '2. Ảnh vùng nghi ngờ',
        'h_defects': '3. Lỗi phát hiện', 'h_items': '3. Hạng mục kiểm tra',
        'h_feature': '4. Đặc điểm lỗi', 'h_ai': '4. Giải thích của AI',
        'h_causes': '5. Nguyên nhân có thể', 'h_actions': '6. Biện pháp xử lý',
        'h_process': '7. Hướng dẫn xử lý · Xác nhận · Gửi', 'h_result': '5. Kết quả kiểm tra',
        'date': 'Thời gian lập', 'part_info': 'Thông tin linh kiện (mã · công đoạn · lô)', 'target': 'Đối tượng',
        'part_no': 'Mã linh kiện', 'photos': 'Ảnh kiểm tra', 'file': 'Tệp gốc', 'inference': 'Cách suy luận',
        'tiled': 'Chia ảnh ({n} phần)', 'verdict': 'Kết quả', 'representative': 'Loại lỗi chính', 'count': 'Số lỗi',
        'count_val': '{n} (Bất thường {r} / Nghi ngờ {s})', 'n_items': '{n} lỗi',
        'c_no': 'STT', 'c_view': 'Ảnh', 'c_type': 'Loại', 'c_sev': 'Mức độ', 'c_pos': 'Vị trí', 'c_size': 'Kích thước (px)',
        'c_conf': 'Độ tin cậy', 'c_level': 'Kết quả', 'c_reason': 'Căn cứ',
        'c_stype': 'Loại nghi ngờ', 'c_sreason': 'Lý do nghi ngờ', 'c_how': 'Cách kiểm tra', 'c_check': 'Kết quả',
        'check_box': '□ Đạt  □ Không đạt', 'how_default': 'Kiểm tra bằng mắt',
        'original': 'Ảnh gốc', 'marked': 'Vị trí lỗi',
        'crops': 'Ảnh phóng to vùng lỗi (căn cứ)', 'crops2': 'Ảnh phóng to vùng nghi ngờ',
        'a_kind': 'Mục', 'a_content': 'Nội dung', 'a_now': 'Xử lý ngay', 'a_prevent': 'Phòng ngừa tái phát',
        'a_ref': '[Tiêu chuẩn]', 'a_ref_now': 'Ngay', 'a_ref_check': 'Kiểm tra', 'a_ref_prevent': 'Phòng ngừa',
        'w_confirm': 'Công nhân xác nhận', 'w_confirm_v': '□ Xác nhận    □ Sửa loại lỗi    □ Báo nhầm',
        'w_edit': 'Nội dung chỉnh sửa', 'w_sign': 'Người xác nhận / Chữ ký / Thời gian',
        'w_send': 'Gửi quản lý (người nhận / thời gian)',
        'f_final': 'Kết luận',
        'f_final_v': '□ Đạt (báo nhầm) → giải phóng Hold, xử lý bình thường, lưu làm mẫu huấn luyện\n□ Không đạt → phát hành báo cáo không phù hợp (NCR)',
        'f_memo': 'Ghi chú tái kiểm', 'f_sign': 'Người tái kiểm / Chữ ký / Thời gian', 'applies_to': 'áp dụng',
        'm_part_no': 'Mã', 'm_process': 'Công đoạn', 'm_lot': 'Lô',
        # NCR
        'ncr_no': 'Số NCR', 'ncr_status': 'Trạng thái', 'ncr_status_v': '■ Open  □ Closed',
        'n_h_problem': '1. Nội dung không phù hợp (5W2H · 8D D2)', 'n_h_photo': '2. Ảnh bằng chứng', 'n_h_defects': '3. Chi tiết lỗi',
        'n_h_contain': '4. Biện pháp khẩn cấp (ngăn chặn · 8D D3)', 'n_h_dispo': '5. Quyết định xử lý (Disposition)',
        'n_h_cause': '6. Nguyên nhân khả dĩ (đầu vào 8D D4)',
        'n_h_corrective': '7. Khắc phục và phòng ngừa tái phát (đề xuất 8D D5 · D7)',
        'n_h_8d': '8. Liên kết 8D', 'n_h_sign': '9. Xác nhận và phê duyệt',
        'w_what': 'Cái gì (What)', 'w_where': 'Ở đâu (Where)', 'w_when': 'Khi nào (When)', 'w_who': 'Ai phát hiện (Who)',
        'w_who_v': 'AI agent kiểm tra ngoại quan → công nhân xác nhận', 'w_how': 'Phát hiện thế nào (How)',
        'w_how_v': 'Kiểm tra bằng ảnh (mô hình YOLO, độ tin cậy cao nhất {conf:.2f})', 'w_howmany': 'Bao nhiêu (How many)',
        'w_req': 'Tiêu chuẩn (Requirement)',
        'w_req_v': 'Phát hiện có độ tin cậy từ {reject} = Bất thường (không phù hợp), {review}–{reject} = Nghi ngờ (quy tắc riêng theo tệp tri thức)',
        't_action': 'Hạng mục', 't_owner': 'Phụ trách', 't_date': 'Ngày hoàn thành',
        'contain_1': '□ Cách ly linh kiện, dán nhãn không phù hợp',
        'contain_2': '□ Kiểm tra và phân loại hàng tồn, hàng đang sản xuất cùng lô',
        'contain_3': '□ Kiểm tra thiết bị và điều kiện của công đoạn liên quan',
        'dispo': 'Cách xử lý',
        'dispo_v': '□ Chấp nhận đặc cách (Use as is)   □ Làm lại (Rework)   □ Sửa chữa (Repair)\n□ Hủy bỏ (Scrap)   □ Trả nhà cung cấp (Return)',
        'dispo_qty': 'Số lượng', 'dispo_by': 'Người quyết định / Ngày',
        'cause_note': '※ Đây là các nguyên nhân khả dĩ AI suy ra từ loại lỗi. Nguyên nhân gốc được xác định ở 8D D4 (5 Why, phân tích 4M).',
        'd8_yes': 'Khuyến nghị phát hành 8D — lý do: {why}', 'd8_no': 'Chưa cần 8D (phát hành nếu lỗi lặp lại)',
        'd8_why_critical': 'lỗi nghiêm trọng', 'd8_why_multi': 'nhiều loại lỗi cùng lúc', 'd8_why_surface': 'phân bố trên toàn bề mặt',
        'd8_step': 'Bước 8D', 'd8_state': 'Liên kết với báo cáo này',
        'd8_d1': 'Lập nhóm', 'd8_d2': 'Mô tả vấn đề', 'd8_d3': 'Biện pháp ngăn chặn', 'd8_d4': 'Nguyên nhân gốc',
        'd8_d5': 'Chọn biện pháp khắc phục', 'd8_d6': 'Thực hiện và xác nhận hiệu quả', 'd8_d7': 'Phòng ngừa tái phát',
        'd8_d8': 'Kết thúc, ghi nhận nhóm',
        'd8_todo': '□ Thực hiện trong 8D', 'd8_done': '■ Xong — mục {sec}', 'd8_partial': '◐ Đang thực hiện — xem mục {sec}',
        'd8_input': '◐ Ứng viên / đề xuất — mục {sec}',
        'd8_issue': 'Phát hành 8D', 'd8_issue_v': '□ Phát hành (số 8D: ____________)   □ Không phát hành',
        's_role': 'Vai trò', 's_name': 'Họ tên', 's_sign': 'Chữ ký', 's_date': 'Ngày', 's_author': 'Lập (công nhân xác nhận)',
        's_review': 'Xem xét (chất lượng)', 's_approve': 'Phê duyệt (quản lý)', 's_close': 'Xác nhận đóng',
        # Phiếu yêu cầu tái kiểm
        'rir_no': 'Số phiếu', 'hold_status': 'Trạng thái Hold', 'hold_status_v': '■ Đang giữ (Hold)  □ Giải phóng (Release)',
        'hold_banner': 'HOLD — Không chuyển sang công đoạn tiếp theo cho đến khi có kết quả tái kiểm.',
        'hold_rule': 'Tiêu chí của AI: phát hiện có độ tin cậy trong khoảng {review}–{reject}, hoặc khó kết luận theo quy tắc riêng của từng loại lỗi (kích thước, phân bố…), được xếp vào Nghi ngờ.',
        'r_h_reason': '1. Lý do yêu cầu', 'r_h_photo': '2. Ảnh vùng nghi ngờ', 'r_h_items': '3. Hạng mục tái kiểm',
        'r_h_ai': '4. Giải thích của AI', 'r_h_result': '5. Kết quả tái kiểm và xử lý Hold',
        'r_method': 'Phương pháp tái kiểm', 'r_method_v': '□ Bằng mắt   □ Kính lúp / kính hiển vi   □ Đo   □ Khác (        )',
        'r_release': 'Phê duyệt giải phóng Hold (họ tên / chữ ký / thời gian)',
    },
    'en': {
        'manager_title': 'Nonconformance Report (NCR)',
        'manager_note': '※ Draft written by the AI agent. Sent to quality after worker confirmation. '
                        'Sections 1, 4, 6 and 7 feed directly into 8D D2, D3, D4 and D5/D7.',
        'inspect_title': 'Re-inspection Request (Hold)',
        'inspect_note': '※ The AI found suspect areas. Hold the part until re-inspection is done, check the actual part and judge Pass / Fail.',
        'h_info': '1. Inspection info and verdict', 'h_info2': '1. Inspection info',
        'h_photo': '2. Defect photos', 'h_photo2': '2. Suspect area photos',
        'h_defects': '3. Detected defects', 'h_items': '3. Items to check',
        'h_feature': '4. Defect description', 'h_ai': '4. AI explanation',
        'h_causes': '5. Possible causes', 'h_actions': '6. Actions',
        'h_process': '7. Handling · confirmation · sending', 'h_result': '5. Inspection result',
        'date': 'Created', 'part_info': 'Part info (part no. · process · lot)', 'target': 'Target',
        'part_no': 'Part ID', 'photos': 'Photos', 'file': 'Original file', 'inference': 'Inference',
        'tiled': 'Tiled ({n} tiles)', 'verdict': 'Verdict', 'representative': 'Main defect', 'count': 'Detections',
        'count_val': '{n} (Abnormal {r} / Suspect {s})', 'n_items': '{n}',
        'c_no': 'No', 'c_view': 'View', 'c_type': 'Type', 'c_sev': 'Severity', 'c_pos': 'Position', 'c_size': 'Size (px)',
        'c_conf': 'Confidence', 'c_level': 'Verdict', 'c_reason': 'Basis',
        'c_stype': 'Suspected type', 'c_sreason': 'Reason', 'c_how': 'How to check', 'c_check': 'Result',
        'check_box': '□ Pass  □ Fail', 'how_default': 'Visual check',
        'original': 'Original', 'marked': 'Defect locations',
        'crops': 'Defect close-ups (evidence)', 'crops2': 'Suspect area close-ups',
        'a_kind': 'Item', 'a_content': 'Details', 'a_now': 'Immediate action', 'a_prevent': 'Prevention',
        'a_ref': '[Reference]', 'a_ref_now': 'Now', 'a_ref_check': 'Check', 'a_ref_prevent': 'Prevent',
        'w_confirm': 'Worker confirmation', 'w_confirm_v': '□ Confirm    □ Change type    □ False alarm',
        'w_edit': 'Changes', 'w_sign': 'Confirmed by / signature / date', 'w_send': 'Sent to manager (to / date)',
        'f_final': 'Final verdict',
        'f_final_v': '□ Pass (false alarm) → release hold, treat as normal, keep as retraining sample\n□ Fail → issue a Nonconformance Report (NCR)',
        'f_memo': 'Re-inspection notes', 'f_sign': 'Re-inspected by / signature / date', 'applies_to': 'applies to',
        'm_part_no': 'Part no.', 'm_process': 'Process', 'm_lot': 'Lot',
        # NCR
        'ncr_no': 'NCR No.', 'ncr_status': 'Status', 'ncr_status_v': '■ Open  □ Closed',
        'n_h_problem': '1. Nonconformance (5W2H · 8D D2)', 'n_h_photo': '2. Evidence photos', 'n_h_defects': '3. Defect details',
        'n_h_contain': '4. Containment (8D D3)', 'n_h_dispo': '5. Disposition',
        'n_h_cause': '6. Possible causes (8D D4 input)',
        'n_h_corrective': '7. Corrective and preventive action (8D D5 · D7 proposal)',
        'n_h_8d': '8. 8D link', 'n_h_sign': '9. Confirmation and approval',
        'w_what': 'What', 'w_where': 'Where', 'w_when': 'When', 'w_who': 'Found by (Who)',
        'w_who_v': 'AI visual inspection agent → worker confirmation', 'w_how': 'How found',
        'w_how_v': 'Photo inspection (YOLO detection model, top confidence {conf:.2f})', 'w_howmany': 'How many',
        'w_req': 'Requirement',
        'w_req_v': 'Detection at confidence {reject}+ = Abnormal (nonconforming), {review}–{reject} = Suspect (per-type rules from the knowledge file)',
        't_action': 'Action', 't_owner': 'Owner', 't_date': 'Done',
        'contain_1': '□ Quarantine the part and tag it as nonconforming',
        'contain_2': '□ Check and sort stock and WIP from the same lot',
        'contain_3': '□ Check equipment and settings of the related process',
        'dispo': 'Disposition', 'dispo_v': '□ Use as is   □ Rework   □ Repair\n□ Scrap   □ Return to supplier',
        'dispo_qty': 'Quantity', 'dispo_by': 'Decided by / date',
        'cause_note': '※ Candidates the AI inferred from the defect type. The root cause is confirmed in 8D D4 (5 Why, 4M analysis).',
        'd8_yes': '8D recommended — reason: {why}', 'd8_no': 'No 8D recommended (issue one if the defect repeats)',
        'd8_why_critical': 'critical defect', 'd8_why_multi': 'several defect types at once',
        'd8_why_surface': 'spread over the whole surface',
        'd8_step': '8D step', 'd8_state': 'Link to this report',
        'd8_d1': 'Team', 'd8_d2': 'Problem description', 'd8_d3': 'Containment', 'd8_d4': 'Root cause',
        'd8_d5': 'Choose corrective action', 'd8_d6': 'Implement and verify', 'd8_d7': 'Prevent recurrence',
        'd8_d8': 'Close and recognize the team',
        'd8_todo': '□ Done in the 8D', 'd8_done': '■ Done — section {sec}', 'd8_partial': '◐ In progress — see section {sec}',
        'd8_input': '◐ Candidates / proposal — section {sec}',
        'd8_issue': '8D issued', 'd8_issue_v': '□ Issued (8D no.: ____________)   □ Not issued',
        's_role': 'Role', 's_name': 'Name', 's_sign': 'Signature', 's_date': 'Date', 's_author': 'Prepared (worker confirmed)',
        's_review': 'Reviewed (quality)', 's_approve': 'Approved (manager)', 's_close': 'Closure confirmed',
        # Re-inspection request
        'rir_no': 'Request No.', 'hold_status': 'Hold status', 'hold_status_v': '■ On hold  □ Released',
        'hold_banner': 'HOLD — Do not send to the next process until re-inspection is complete.',
        'hold_rule': "AI criteria: detections with confidence between {review} and {reject}, or ones the per-type rules (size, spread, etc.) can't settle, are classed as Suspect.",
        'r_h_reason': '1. Reason for request', 'r_h_photo': '2. Suspect area photos', 'r_h_items': '3. Re-inspection items',
        'r_h_ai': '4. AI explanation', 'r_h_result': '5. Re-inspection result and hold decision',
        'r_method': 'Method', 'r_method_v': '□ Visual   □ Loupe / microscope   □ Measurement   □ Other (        )',
        'r_release': 'Hold release approved (name / signature / date)',
    },
}
DOMAIN = {'ko': {'pcb': 'PCB', 'msdd': '금속 부품 표면', 'mobile': '휴대폰 표면 (화면·외관)'},
          'vi': {'pcb': 'PCB', 'msdd': 'Bề mặt linh kiện kim loại', 'mobile': 'Bề mặt điện thoại (màn hình, vỏ)'},
          'en': {'pcb': 'PCB', 'msdd': 'Metal part surface', 'mobile': 'Phone surface (screen, housing)'}}
SEVERITY = {'ko': {'critical': '치명', 'major': '중', 'minor': '경'},
            'vi': {'critical': 'Nghiêm trọng', 'major': 'Nặng', 'minor': 'Nhẹ'},
            'en': {'critical': 'Critical', 'major': 'Major', 'minor': 'Minor'}}
SITUATION_TR = {   # taxonomy 의 situations 는 한국어 → 다른 언어 화면·보고서용
    'vi': {
        'normal': {'label': 'Bình thường', 'action': 'Cho qua. Chỉ ghi lịch sử kiểm tra.'},
        'review': {'label': 'Nghi ngờ', 'output': 'Phiếu yêu cầu tái kiểm (Hold)',
                   'action': 'Giữ linh kiện (Hold), đánh dấu vùng nghi ngờ và yêu cầu tái kiểm. Không đạt thì phát hành NCR, đạt (báo nhầm) thì giải phóng Hold.',
                   'note': 'Ảnh bị loại bỏ được lưu làm mẫu bình thường, ảnh xác nhận lỗi được lưu làm mẫu lỗi để huấn luyện lại.'},
        'reject': {'label': 'Bất thường', 'output': 'Báo cáo không phù hợp (NCR)',
                   'action': 'Lập báo cáo không phù hợp (NCR) kèm nguyên nhân và biện pháp theo loại lỗi, gửi bộ phận chất lượng sau khi công nhân xác nhận. Lỗi nghiêm trọng hoặc nhiều loại thì khuyến nghị 8D.'},
        'multi_type': {'label': 'Nhiều loại lỗi',
                       'action': 'Lấy loại lỗi nghiêm trọng nhất làm kết quả chính, ghi đầy đủ các loại còn lại trong báo cáo.'},
        'part': {'label': 'Đánh giá theo linh kiện',
                 'action': 'Nếu một trong các ảnh của linh kiện là Bất thường thì linh kiện Bất thường; nếu không có Bất thường nhưng có Nghi ngờ thì Nghi ngờ.'},
        'surface_wide': {'label': 'Phân bố toàn bề mặt',
                         'action': 'Lỗi trải khắp bề mặt gia công: nghi ngờ bất thường điều kiện gia công/vật liệu, khuyến nghị kiểm tra các linh kiện khác cùng lô.'},
        'repeated_location': {'label': 'Lặp lại cùng vị trí',
                              'action': 'Lỗi lặp lại ở cùng tọa độ trên nhiều bo mạch: ưu tiên kiểm tra công đoạn.'},
    },
    'en': {
        'normal': {'label': 'Normal', 'action': 'Pass. Only the inspection history is recorded.'},
        'review': {'label': 'Suspect', 'output': 'Re-inspection request (Hold)',
                   'action': 'Put the part on hold, mark the suspect areas and request re-inspection. A fail issues an NCR; a pass (false alarm) releases the hold.',
                   'note': 'Dismissed photos are kept as normal samples and confirmed ones as defect samples for retraining.'},
        'reject': {'label': 'Abnormal', 'output': 'Nonconformance report (NCR)',
                   'action': 'Create a nonconformance report (NCR) with possible causes and actions per defect type, and send it to quality after worker confirmation. An 8D is recommended for critical or multi-type defects.'},
        'multi_type': {'label': 'Multiple defect types',
                       'action': 'The most severe type is the main verdict; all other types are listed in the report.'},
        'part': {'label': 'Part-level judgment',
                 'action': 'If any view of the part is Abnormal, the part is Abnormal; if none is Abnormal but some are Suspect, the part is Suspect.'},
        'surface_wide': {'label': 'Surface-wide',
                         'action': 'The defect covers the whole machined surface: suspect a machining/material condition and check other parts of the same lot.'},
        'repeated_location': {'label': 'Repeated location',
                              'action': 'The same defect repeats at the same position on many boards: check the process first.'},
    },
}

REASON = {
    'ko': {
        'below_cut': '신뢰도 {conf:.2f} < 이상 기준 {cut:.2f}',
        'max_review': '신뢰도 {conf:.2f}이지만 허용 여부를 사람이 판단해야 하는 유형이라 최대 의심',
        'local_only': '신뢰도 {conf:.2f}이지만 국부 결함 (전면 분포일 때만 이상)',
        'small_area': '신뢰도 {conf:.2f}이지만 면적 {area:.2f}% < 이상 기준 {min:.1f}%',
        'above_cut': '신뢰도 {conf:.2f} ≥ 이상 기준 {cut:.2f}',
        'lowered': ' (치명 유형이라 기준을 낮춤)',
        'surface': ', 전면 분포',
        'edited': '작업자 수정',
    },
    'vi': {
        'below_cut': 'Độ tin cậy {conf:.2f} < ngưỡng bất thường {cut:.2f}',
        'max_review': 'Độ tin cậy {conf:.2f} nhưng là loại lỗi cần người đánh giá mức cho phép nên tối đa Nghi ngờ',
        'local_only': 'Độ tin cậy {conf:.2f} nhưng là lỗi cục bộ (chỉ bất thường khi phân bố toàn bề mặt)',
        'small_area': 'Độ tin cậy {conf:.2f} nhưng diện tích {area:.2f}% < ngưỡng bất thường {min:.1f}%',
        'above_cut': 'Độ tin cậy {conf:.2f} ≥ ngưỡng bất thường {cut:.2f}',
        'lowered': ' (lỗi nghiêm trọng nên hạ ngưỡng)',
        'surface': ', phân bố toàn bề mặt',
        'edited': 'Công nhân chỉnh sửa',
    },
    'en': {
        'below_cut': 'Confidence {conf:.2f} < abnormal threshold {cut:.2f}',
        'max_review': 'Confidence {conf:.2f}, but this type needs a human acceptance decision, so at most Suspect',
        'local_only': 'Confidence {conf:.2f}, but a local defect (abnormal only when surface-wide)',
        'small_area': 'Confidence {conf:.2f}, but area {area:.2f}% < abnormal threshold {min:.1f}%',
        'above_cut': 'Confidence {conf:.2f} ≥ abnormal threshold {cut:.2f}',
        'lowered': ' (critical type, lowered threshold)',
        'surface': ', surface-wide',
        'edited': 'Edited by worker',
    },
}
_POS = {
    'vi': {'상단': 'trên', '중앙': 'giữa', '하단': 'dưới', '좌측': 'trái', '우측': 'phải'},
    'en': {'상단': 'top', '중앙': 'center', '하단': 'bottom', '좌측': 'left', '우측': 'right'},
}


# ── 화면 안내(투어) 문구 ─────────────────────────────────────────────
TOUR = {
    'ko': {
        'tour_btn': '가이드', 'tour_btn_help': '화면 안내를 처음부터 다시 봅니다',
        'tour_step': '안내', 'tour_prev': '◀ 이전', 'tour_next': '다음 ▶', 'tour_finish': '시작하기', 'tour_skip': '건너뛰기',
        'tour_demo_note': '설명을 위해 검사 대장의 최근 기록을 예시로 열었습니다.',
        'tour_no_result': '아직 검사 기록이 없어 예시를 보여드릴 수 없습니다. 검사를 하면 이 영역이 나타납니다.',
        'tour_welcome_t': '👋 부품 불량 사진 분석 에이전트',
        'tour_welcome_b': '사진을 넣으면 AI 가 결함을 찾아 **정상 / 의심 / 이상**으로 판정하고, 원인·조치를 붙여 보고서 초안을 만듭니다. '
                          '**최종 판정과 저장은 작업자가 확인한 뒤** 합니다. 화면 구성을 차례로 안내할게요.',
        'tour_lang_t': '🌐 언어 · 🧭 가이드',
        'tour_lang_b': '화면 언어를 **한국어 / 베트남어 / 영어**로 바꿉니다. 검사할 때의 언어로 보고서도 작성됩니다. '
                       '이 안내는 옆의 **🧭 가이드** 버튼으로 언제든 다시 볼 수 있습니다.',
        'tour_ledger_t': '📒 검사 대장 · 기록',
        'tour_ledger_b': '지금까지의 모든 검사가 쌓입니다. 🔴 이상 · 🟠 의심 · 🟢 정상, **⏳ 는 작업자 확인 대기**. '
                         '누르면 그 검사가 열리고, 보기·검색으로 걸러 볼 수 있습니다. 아래에서 **영어 엑셀 대장**을 내려받습니다.',
        'tour_input_t': '📷 검사 입력',
        'tour_input_b': '검사 대상(PCB / 금속 / 휴대폰)을 고르고 사진을 넣습니다. **예시 사진**, **업로드**(여러 장이면 부품 단위 판정), '
                        '**대기함**(inbox 폴더의 사진을 일괄 검사) 중 하나를 쓰세요. 품번·공정·로트는 보고서와 대장에 기록됩니다.',
        'tour_verdict_t': '⚖ 판정',
        'tour_verdict_b': '사진 전체의 판정입니다. **이상**은 부적합 보고서(NCR), **의심**은 재검사 의뢰서(Hold), **정상**은 기록만 합니다. '
                          '이상·의심 개수와 대표 결함 유형, AI 요약이 함께 나옵니다.',
        'tour_photos_t': '🖼 원본 · 결함 위치',
        'tour_photos_b': '왼쪽이 원본, 오른쪽이 AI 가 찾은 결함 위치입니다. 부품 단위 검사면 방향별 사진이 나란히 나옵니다.',
        'tour_table_t': '📋 결함 표 (수정 가능)',
        'tour_table_b': '결함마다 유형·위치·크기·신뢰도와 **판정 근거**가 나옵니다. 실물을 보고 **유형**이나 **판정**(이상/의심/제외)을 '
                        '바꾼 뒤 [수정 반영]을 누르면 전체 판정이 다시 계산됩니다.',
        'tour_text_t': '✍ 보고서 문장',
        'tour_text_b': 'AI(Qwen)가 쓴 요약·특징·원인·조치 문장입니다. 직접 고칠 수 있고, 고친 내용은 바로 저장됩니다.',
        'tour_decision_t': '✅ 처리',
        'tour_decision_b': '[미리보기]를 누르면 저장될 보고서가 창으로 뜨고, **[저장]해야** 파일이 만들어집니다. '
                           '오탐이면 [오탐 기각]으로 정상 처리하고 사진은 재학습용으로 보관합니다.',
        'tour_chat_dash_t': '💬 에이전트에게 질문',
        'tour_chat_dash_b': '지금 검사에 대해 물어보세요. 판정 이유, 원인, 확인할 점을 검사 결과와 지식베이스를 근거로 답합니다. '
                            '판정은 대화로 바뀌지 않습니다.',
        'tour_done_t': '🎉 준비 끝',
        'tour_done_b': '위의 **[검사 입력]**에서 예시 사진으로 먼저 검사해 보세요. 채팅 중심으로 쓰고 싶으면 채팅형 화면(8503)도 있습니다.',
        'tour_welcome_chat_t': '👋 채팅형 에이전트',
        'tour_welcome_chat_b': '대화하듯 검사하는 화면입니다. 사진을 첨부하면 AI 가 판정하고, 결과는 오른쪽 **작업 패널**에서 확인·수정·저장합니다. '
                               '화면 구성을 차례로 안내할게요.',
        'tour_toolbar_t': '🧰 도구',
        'tour_toolbar_b': '**⚙** 검사 대상과 품번·공정·로트 / **📷** 예시 사진으로 검사 / **📥** 대기함 일괄 검사 / **🛠** 작업 패널 열기·닫기.',
        'tour_chatbox_t': '💬 대화',
        'tour_chatbox_b': '검사 결과가 **카드**로 남습니다. 카드를 누르면 작업 패널에 열립니다. 수정 제안도 여기에 나오고 [적용]해야 반영됩니다.',
        'tour_inputrow_t': '⌨ 입력창',
        'tour_inputrow_b': '**📎** 로 사진을 첨부하면 검사, 글을 쓰면 질문입니다. 보고서 문장을 붙여 넣고 "이렇게 고쳐줘"라고 하면 수정안을 줍니다. '
                           '**❓** 는 질문 예시, **✏️ 수정 요청**을 켜면 모든 메시지를 수정 요청으로 처리합니다.',
        'tour_panel_t': '🛠 작업 패널',
        'tour_panel_b': '화면 오른쪽에 붙어 **따로 스크롤**됩니다. ⇔ 로 넓게/좁게, ✕ 로 닫고, 위의 🛠 로 다시 엽니다.',
        'tour_panel_report_t': '📄 보고서 탭',
        'tour_panel_report_b': '저장될 보고서 그대로입니다. 고칠 문장을 **드래그해 복사**한 뒤 대화창에 붙여 넣고 수정을 요청하세요.',
        'tour_panel_edit_t': '🛠 편집 · 확정 탭',
        'tour_panel_edit_b': '결함 표에서 유형·판정을 고치고, 문장을 편집하고, [미리보기 → 저장] 또는 [오탐 기각]으로 처리합니다. '
                             '**판정은 이 탭에서만** 바뀝니다.',
        'tour_done_chat_t': '🎉 준비 끝',
        'tour_done_chat_b': '**📷 예시**로 먼저 검사해 보거나 📎 로 사진을 첨부해 보세요. 작업 화면 위주로 쓰고 싶으면 대시보드형 화면(8501)도 있습니다.',
    },
    'vi': {
        'tour_btn': 'Hướng dẫn', 'tour_btn_help': 'Xem lại hướng dẫn màn hình từ đầu',
        'tour_step': 'Hướng dẫn', 'tour_prev': '◀ Trước', 'tour_next': 'Tiếp ▶', 'tour_finish': 'Bắt đầu', 'tour_skip': 'Bỏ qua',
        'tour_demo_note': 'Để minh họa, hồ sơ gần nhất trong sổ kiểm tra đã được mở.',
        'tour_no_result': 'Chưa có hồ sơ kiểm tra để minh họa. Vùng này sẽ xuất hiện sau khi kiểm tra.',
        'tour_welcome_t': '👋 Tác tử AI phân tích ảnh lỗi linh kiện',
        'tour_welcome_b': 'Đưa ảnh vào, AI tìm lỗi và đánh giá **Bình thường / Nghi ngờ / Bất thường**, kèm nguyên nhân và biện pháp để soạn báo cáo nháp. '
                          '**Kết luận cuối và việc lưu do công nhân xác nhận.** Sau đây là các phần của màn hình.',
        'tour_lang_t': '🌐 Ngôn ngữ · 🧭 Hướng dẫn',
        'tour_lang_b': 'Đổi ngôn ngữ **Hàn / Việt / Anh**. Báo cáo được viết theo ngôn ngữ khi kiểm tra. '
                       'Có thể xem lại hướng dẫn bằng nút **🧭 Hướng dẫn** bên cạnh.',
        'tour_ledger_t': '📒 Sổ kiểm tra · Hồ sơ',
        'tour_ledger_b': 'Mọi lần kiểm tra được lưu ở đây. 🔴 Bất thường · 🟠 Nghi ngờ · 🟢 Bình thường, **⏳ chờ công nhân xác nhận**. '
                         'Nhấn để mở; lọc và tìm kiếm được. Phía dưới có thể tải **sổ kiểm tra Excel (tiếng Anh)**.',
        'tour_input_t': '📷 Thông tin kiểm tra',
        'tour_input_b': 'Chọn đối tượng (PCB / kim loại / điện thoại) và đưa ảnh vào: **Ảnh mẫu**, **Tải lên** (nhiều ảnh = đánh giá theo linh kiện) '
                        'hoặc **Hộp chờ** (kiểm tra hàng loạt ảnh trong thư mục inbox). Mã SP · công đoạn · lô được ghi vào báo cáo và sổ.',
        'tour_verdict_t': '⚖ Kết quả',
        'tour_verdict_b': 'Kết quả của cả ảnh. **Bất thường** → báo cáo không phù hợp (NCR), **Nghi ngờ** → phiếu tái kiểm (Hold), **Bình thường** → chỉ ghi sổ. '
                          'Kèm số lỗi, loại lỗi chính và tóm tắt của AI.',
        'tour_photos_t': '🖼 Ảnh gốc · Vị trí lỗi',
        'tour_photos_b': 'Bên trái là ảnh gốc, bên phải là vị trí lỗi AI tìm thấy. Kiểm tra theo linh kiện sẽ hiện ảnh theo từng hướng.',
        'tour_table_t': '📋 Bảng lỗi (có thể sửa)',
        'tour_table_b': 'Mỗi lỗi có loại, vị trí, kích thước, độ tin cậy và **căn cứ đánh giá**. Sau khi xem thực tế, đổi **loại** hoặc **kết quả** '
                        '(Bất thường/Nghi ngờ/Loại bỏ) rồi nhấn [Áp dụng chỉnh sửa] để tính lại.',
        'tour_text_t': '✍ Nội dung báo cáo',
        'tour_text_b': 'Tóm tắt, đặc điểm, nguyên nhân, biện pháp do AI (Qwen) viết. Có thể sửa trực tiếp và được lưu ngay.',
        'tour_decision_t': '✅ Xử lý',
        'tour_decision_b': 'Nhấn [Xem trước] để mở báo cáo sẽ lưu; **phải nhấn [Lưu]** mới tạo tệp. '
                           'Nếu báo nhầm, nhấn [Báo nhầm] để xử lý Bình thường và lưu ảnh làm mẫu huấn luyện.',
        'tour_chat_dash_t': '💬 Hỏi tác tử AI',
        'tour_chat_dash_b': 'Hỏi về kiểm tra hiện tại: lý do đánh giá, nguyên nhân, việc cần kiểm tra. Trả lời dựa trên kết quả và cơ sở tri thức. '
                            'Không thể đổi kết quả qua hội thoại.',
        'tour_done_t': '🎉 Sẵn sàng',
        'tour_done_b': 'Hãy thử kiểm tra một ảnh mẫu ở **[Thông tin kiểm tra]** phía trên. Muốn dùng kiểu hội thoại thì có màn hình hội thoại (8503).',
        'tour_welcome_chat_t': '👋 Tác tử dạng hội thoại',
        'tour_welcome_chat_b': 'Kiểm tra như đang trò chuyện. Đính kèm ảnh để AI đánh giá; kết quả được xem, sửa và lưu ở **bảng làm việc** bên phải. '
                               'Sau đây là các phần của màn hình.',
        'tour_toolbar_t': '🧰 Công cụ',
        'tour_toolbar_b': '**⚙** đối tượng và mã SP · công đoạn · lô / **📷** kiểm tra ảnh mẫu / **📥** kiểm tra hàng loạt / **🛠** mở · đóng bảng làm việc.',
        'tour_chatbox_t': '💬 Hội thoại',
        'tour_chatbox_b': 'Kết quả được lưu thành **thẻ**; nhấn thẻ để mở trong bảng làm việc. Đề xuất sửa cũng hiện ở đây và chỉ áp dụng khi nhấn [Áp dụng].',
        'tour_inputrow_t': '⌨ Ô nhập',
        'tour_inputrow_b': 'Đính kèm ảnh bằng **📎** để kiểm tra, nhập chữ để hỏi. Dán câu trong báo cáo và nói "hãy sửa thế này" để nhận đề xuất. '
                           '**❓** là ví dụ câu hỏi; bật **✏️ Yêu cầu sửa** để mọi tin nhắn là yêu cầu sửa.',
        'tour_panel_t': '🛠 Bảng làm việc',
        'tour_panel_b': 'Gắn ở bên phải và **cuộn riêng**. ⇔ để rộng/hẹp, ✕ để đóng, 🛠 phía trên để mở lại.',
        'tour_panel_report_t': '📄 Thẻ Báo cáo',
        'tour_panel_report_b': 'Đúng như báo cáo sẽ lưu. **Kéo chọn và sao chép** câu cần sửa, dán vào ô hội thoại và yêu cầu sửa.',
        'tour_panel_edit_t': '🛠 Thẻ Chỉnh sửa · Xác nhận',
        'tour_panel_edit_b': 'Sửa loại và kết quả trong bảng lỗi, chỉnh nội dung, rồi [Xem trước → Lưu] hoặc [Báo nhầm]. '
                             '**Kết quả chỉ thay đổi ở thẻ này.**',
        'tour_done_chat_t': '🎉 Sẵn sàng',
        'tour_done_chat_b': 'Hãy thử **📷 ảnh mẫu** hoặc đính kèm ảnh bằng 📎. Muốn màn hình làm việc thì có màn hình dạng bảng (8501).',
    },
    'en': {
        'tour_btn': 'Guide', 'tour_btn_help': 'Replay the screen guide from the start',
        'tour_step': 'Guide', 'tour_prev': '◀ Back', 'tour_next': 'Next ▶', 'tour_finish': 'Get started', 'tour_skip': 'Skip',
        'tour_demo_note': 'For this guide, the latest record in the ledger was opened as an example.',
        'tour_no_result': 'There is no inspection record to show yet. This area appears after an inspection.',
        'tour_welcome_t': '👋 Part Defect Photo Analysis Agent',
        'tour_welcome_b': 'Add a photo and the AI finds defects, judges **Normal / Suspect / Abnormal**, and drafts a report with causes and actions. '
                          '**The worker confirms the final verdict and saves.** Here is a quick tour of the screen.',
        'tour_lang_t': '🌐 Language · 🧭 Guide',
        'tour_lang_b': 'Switch the screen between **Korean / Vietnamese / English**. Reports are written in the language used for the inspection. '
                       'Replay this tour any time with the **🧭 Guide** button.',
        'tour_ledger_t': '📒 Ledger · Records',
        'tour_ledger_b': 'Every inspection is listed here. 🔴 Abnormal · 🟠 Suspect · 🟢 Normal, **⏳ waiting for the worker**. '
                         'Click to open; filter and search. Download the **English Excel ledger** at the bottom.',
        'tour_input_t': '📷 Inspection input',
        'tour_input_b': 'Pick the target (PCB / metal / phone) and add photos: **Examples**, **Upload** (several photos = part-level judgment) '
                        'or **Inbox** (batch-inspect photos in the inbox folder). Part no. · process · lot go into the report and ledger.',
        'tour_verdict_t': '⚖ Verdict',
        'tour_verdict_b': 'The verdict for the whole photo. **Abnormal** → nonconformance report (NCR), **Suspect** → re-inspection request (Hold), **Normal** → logged only. '
                          'Also shows counts, the main defect type and the AI summary.',
        'tour_photos_t': '🖼 Original · defect locations',
        'tour_photos_b': 'Left is the original, right shows where the AI found defects. Part-level inspections show each view side by side.',
        'tour_table_t': '📋 Defect table (editable)',
        'tour_table_b': 'Each defect has type, position, size, confidence and the **basis** for its verdict. After checking the part, change the **type** or '
                        '**verdict** (Abnormal/Suspect/Exclude) and press [Apply edits] to recalculate.',
        'tour_text_t': '✍ Report text',
        'tour_text_b': 'Summary, description, causes and actions written by the AI (Qwen). Edit them directly; changes are saved immediately.',
        'tour_decision_t': '✅ Action',
        'tour_decision_b': '[Preview] opens the report as it will be saved; **a file is created only when you press [Save]**. '
                           'For a false alarm, [False alarm] treats it as normal and keeps the photo for retraining.',
        'tour_chat_dash_t': '💬 Ask the agent',
        'tour_chat_dash_b': 'Ask about the current inspection: why this verdict, causes, what to check. Answers use the result and the knowledge base. '
                            'The verdict cannot be changed by chat.',
        'tour_done_t': '🎉 All set',
        'tour_done_b': 'Try an example photo in **[Inspection input]** above. For a chat-first experience, use the chat screen (8503).',
        'tour_welcome_chat_t': '👋 Chat agent',
        'tour_welcome_chat_b': 'Inspect as if chatting. Attach a photo and the AI judges it; check, edit and save the result in the **work panel** on the right. '
                               'Here is a quick tour.',
        'tour_toolbar_t': '🧰 Tools',
        'tour_toolbar_b': '**⚙** target and part no. · process · lot / **📷** inspect an example / **📥** batch inspection / **🛠** open · close the work panel.',
        'tour_chatbox_t': '💬 Conversation',
        'tour_chatbox_b': 'Results stay here as **cards**; click a card to open it in the work panel. Edit proposals appear here too and apply only when you press [Apply].',
        'tour_inputrow_t': '⌨ Input',
        'tour_inputrow_b': 'Attach photos with **📎** to inspect, type to ask. Paste report text and say how to change it to get a proposal. '
                           '**❓** shows example questions; turn on **✏️ Edit request** to treat every message as an edit.',
        'tour_panel_t': '🛠 Work panel',
        'tour_panel_b': 'Docked on the right and **scrolls separately**. ⇔ wider/narrower, ✕ close, 🛠 above to reopen.',
        'tour_panel_report_t': '📄 Report tab',
        'tour_panel_report_b': 'Exactly the report that will be saved. **Select and copy** a sentence, paste it into the chat and ask for a change.',
        'tour_panel_edit_t': '🛠 Edit · Confirm tab',
        'tour_panel_edit_b': 'Change type and verdict in the defect table, edit text, then [Preview → Save] or [False alarm]. '
                             '**The verdict changes only here.**',
        'tour_done_chat_t': '🎉 All set',
        'tour_done_chat_b': 'Try a **📷 example** or attach a photo with 📎. For a work-focused screen, use the dashboard (8501).',
    },
}
for _lang, _texts in TOUR.items():
    TEXT[_lang].update(_texts)


# ── 함수 ─────────────────────────────────────────────────────────
def T(key, lang='ko', **kw):
    s = TEXT.get(lang, {}).get(key) or TEXT['ko'].get(key, key)
    return s.format(**kw) if kw else s


def R(key, lang='ko', **kw):
    s = REPORT.get(lang, {}).get(key) or REPORT['ko'].get(key, key)
    return s.format(**kw) if kw else s


def verdict_name(v, lang='ko'):
    return VERDICT.get(lang, VERDICT['ko'])[v]


def level_name(v, lang='ko'):
    return LEVEL.get(lang, LEVEL['ko'])[v]


def type_name(t, kb_entry=None, lang='ko'):
    """결함 유형 표시 이름 (지식베이스의 name_ko / name_vi / name_en, 없으면 클래스명)."""
    kb_entry = kb_entry or {}
    return kb_entry.get(f'name_{lang}') or kb_entry.get('name_ko' if lang == 'ko' else '') or t


def pos_text(p, lang='ko'):
    """detect 의 한국어 위치(예: '상단 좌측') → 해당 언어."""
    if lang not in _POS:
        return p
    s = ' '.join(_POS[lang].get(w, w) for w in p.split())
    return s[:1].upper() + s[1:]


def situation_text(sit_entry, key, lang='ko'):
    """situation 항목(label/action/note/output)의 해당 언어 문구."""
    tr = SITUATION_TR.get(lang, {}).get(key)
    return {**sit_entry, **tr} if tr else sit_entry


def reason_text(d, lang='ko'):
    """결함의 판정 근거(reason_key + reason_args) → 해당 언어 문장."""
    rs = REASON.get(lang, REASON['ko'])
    key, args = d.get('reason_key'), d.get('reason_args', {})
    if key not in rs:
        return d.get('reason', '')
    s = rs[key].format(**args)
    if key == 'above_cut':
        s += (rs['lowered'] if args.get('lowered') else '') + (rs['surface'] if args.get('surface') else '')
    return s


def process_name(code, lang='ko'):
    return PROCESS_NAME.get(lang, PROCESS_NAME['ko']).get(code or '', code or '')


def format_meta(meta, lang='ko'):
    """품번·공정·로트 → 한 줄 (보고서·Qwen 프롬프트용)."""
    meta = meta or {}
    parts = [(R('m_part_no', lang), meta.get('part_no')),
             (R('m_process', lang), process_name(meta.get('process'), lang) if meta.get('process') else ''),
             (R('m_lot', lang), meta.get('lot'))]
    return ' / '.join(f'{k} {v}' for k, v in parts if v)
