"""실시간 검사 시험 기록 정리 — 시연 전에 검사 대장을 깨끗하게.

검사 대장(records.jsonl)에서 실시간 라인 기록(id 가 live_ 로 시작)만 빼고, 관련 파일은 Windows 휴지통으로 보낸다 (복원 가능).
  - outputs/work/live_*            작업 폴더 (검출 표시·확대 사진·결과 json)
  - outputs/work/_thumbs/live_*    엑셀 썸네일
  - outputs/records/<날짜>/live_*.md
  - outputs/live/captures/         캡처 사진
  - outputs/abnormal|second_inspection/live_*   (작업자가 확정해 만든 보고서가 있으면)
정리 전 records.jsonl 은 outputs/live/backup/ 에 복사해 둔다. 대조 기록(outputs/live/eval_*.csv)은 남긴다.
영상 서버가 켜져 있으면 먼저 일시정지시킨다. 끝나면 엑셀 대장을 다시 만든다.

실행: .venv\\Scripts\\python tools/clear_live_records.py [--dry-run]
"""
import argparse
import ctypes
import json
import shutil
import sys
import time
import urllib.request
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.records import JSONL, _Lock, rebuild_xlsx  # noqa: E402

OUT = ROOT / 'outputs'


def to_recycle_bin(paths):
    """여러 파일·폴더를 한 번에 휴지통으로 (SHFileOperationW + FOF_ALLOWUNDO). 실패하면 False."""
    paths = [str(p) for p in paths if p.exists()]
    if not paths:
        return True

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [('hwnd', wintypes.HWND), ('wFunc', wintypes.UINT), ('pFrom', wintypes.LPCWSTR),
                    ('pTo', wintypes.LPCWSTR), ('fFlags', ctypes.c_ushort), ('fAnyOperationsAborted', wintypes.BOOL),
                    ('hNameMappings', ctypes.c_void_p), ('lpszProgressTitle', wintypes.LPCWSTR)]
    FO_DELETE, FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 3, 0x4, 0x10, 0x40, 0x400
    op = SHFILEOPSTRUCTW(None, FO_DELETE, '\0'.join(paths) + '\0\0', None,
                         FOF_SILENT | FOF_NOCONFIRMATION | FOF_ALLOWUNDO | FOF_NOERRORUI, False, None, None)
    return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0 and not op.fAnyOperationsAborted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='지우지 않고 개수만 보여 준다')
    a = ap.parse_args()

    try:                                      # 정리하는 동안 새 기록이 생기지 않게
        urllib.request.urlopen('http://127.0.0.1:8506/control?cmd=pause', timeout=2).close()
        print('video server paused')
    except OSError:
        pass

    jsonl = OUT / JSONL
    lines = [l for l in jsonl.read_text(encoding='utf-8').splitlines() if l.strip()] if jsonl.exists() else []
    keep = [l for l in lines if not json.loads(l)['id'].startswith('live_')]
    files = (list((OUT / 'work').glob('live_*')) + list((OUT / 'work/_thumbs').glob('live_*'))
             + list((OUT / 'records').glob('*/live_*.md')) + list((OUT / 'abnormal').glob('live_*'))
             + list((OUT / 'second_inspection').glob('live_*')) + [OUT / 'live/captures'])
    files = [f for f in files if f.exists()]
    print(f'ledger lines {len(lines)} → {len(keep)} (remove {len(lines) - len(keep)}), files/folders to recycle: {len(files)}')
    if a.dry_run:
        return

    backup = OUT / 'live/backup' / f'records_{time.strftime("%Y%m%d_%H%M%S")}.jsonl'
    backup.parent.mkdir(parents=True, exist_ok=True)
    if jsonl.exists():
        shutil.copy2(jsonl, backup)
    with _Lock(OUT):
        jsonl.write_text('\n'.join(keep) + ('\n' if keep else ''), encoding='utf-8')
    ok = to_recycle_bin(files)
    for d in (OUT / 'records').glob('*'):     # 비어 버린 날짜 폴더
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    warn = rebuild_xlsx(OUT)
    print(f'done — backup {backup.relative_to(ROOT)}, recycle bin {"ok" if ok else "FAILED (files left in place)"}'
          + (f', {warn}' if warn else ''))


if __name__ == '__main__':
    main()
