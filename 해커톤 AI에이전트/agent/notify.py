"""담당자 알림: 이상(reject) 확정·의심(review) 대기 시 알림을 남긴다.

- outputs/notifications.jsonl  알림 기록 (화면·엑셀과 별개로 항상 남는다)
- 환경변수 NOTIFY_WEBHOOK 가 있으면 같은 내용을 JSON 으로 POST (Slack/Teams/사내 메신저 웹훅). 인터넷이 없으면 조용히 건너뛴다.
"""
import json
import os
import time
import urllib.request
from pathlib import Path

LEVEL = {'reject': 'critical', 'review': 'warning'}


def notify(result, out_root, status):
    det = result['detection']
    if det['verdict'] not in LEVEL:
        return None
    meta = result.get('meta') or {}
    note = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'level': LEVEL[det['verdict']], 'id': result['name'],
            'domain': det['domain'], 'verdict': det['verdict'], 'status': status,
            'representative': result['situation'].get('representative'),
            'part_no': meta.get('part_no', ''), 'lot': meta.get('lot', ''),
            'report': str(result.get('report') or '')}
    path = Path(out_root) / 'notifications.jsonl'
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(note, ensure_ascii=False) + '\n')
    url = os.environ.get('NOTIFY_WEBHOOK')
    if url:
        text = (f'[{note["level"].upper()}] {note["id"]} ({note["domain"]}) {note["verdict"]} '
                f'{note["representative"] or ""} — {note["status"]}')
        try:
            req = urllib.request.Request(url, data=json.dumps({**note, 'text': text}).encode('utf-8'),
                                         headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=5).close()
        except OSError:
            pass
    return note
