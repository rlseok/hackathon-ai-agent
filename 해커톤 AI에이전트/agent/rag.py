"""RAG: 웹에서 모은 결함·대처 문서(knowledge/rag/corpus/*.md)에서 질문과 관련된 근거를 찾는다.

- 문서는 '# 제목' 단위로 쪼개 조각(chunk)으로 만들고, 다국어 임베딩(paraphrase-multilingual-mpnet)으로 한국어·베트남어·영어 질문을 모두 검색한다.
- 각 조각은 출처 URL·라이선스를 함께 돌려줘서 답변과 보고서에 출처를 달 수 있다.
- 지식베이스 YAML(원인·조치 원문)이 1순위 근거이고, RAG 는 보충 설명·출처용이다. 판정에는 쓰지 않는다.
"""
import re
from pathlib import Path

import numpy as np

from agent.device import pick_device

CORPUS = Path(__file__).resolve().parents[1] / 'knowledge/rag/corpus'
EMBED_MODEL = 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
_index = {}


def _parse(path):
    text = path.read_text(encoding='utf-8')
    m = re.match(r'---\n(.*?)\n---\n(.*)', text, re.S)
    meta, body = {}, text
    if m:
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                meta[k.strip()] = v.strip()
        body = m.group(2)
    domains = [d.strip() for d in meta.get('domains', '').strip('[]').split(',') if d.strip()]
    chunks = []
    for part in re.split(r'\n(?=# )', body.strip()):
        head, _, rest = part.partition('\n')
        if rest.strip():
            chunks.append({'doc': path.name, 'title': meta.get('title', path.stem), 'section': head.lstrip('# ').strip(),
                           'text': rest.strip(), 'source': meta.get('source', ''), 'license': meta.get('license', ''),
                           'domains': domains})
    return chunks


def _build():
    if _index:
        return _index
    from sentence_transformers import SentenceTransformer
    chunks = [c for p in sorted(CORPUS.glob('*.md')) for c in _parse(p)]
    model = SentenceTransformer(EMBED_MODEL, device=pick_device(need_mb=800))     # GPU 우선, 바쁠 때만 CPU
    emb = model.encode([f'{c["title"]}. {c["section"]}. {c["text"]}' for c in chunks], normalize_embeddings=True)
    _index.update(chunks=chunks, emb=np.asarray(emb), model=model)
    return _index


def search(query, domain=None, k=3, min_score=0.30):
    """질문과 가장 가까운 조각 k 개 (domain 이 있으면 그 도메인 문서 + 공통 문서만). 점수가 낮으면 돌려주지 않는다."""
    idx = _build()
    q = idx['model'].encode([query], normalize_embeddings=True)[0]
    scores = idx['emb'] @ q
    out = []
    for i in np.argsort(-scores):
        c = idx['chunks'][i]
        if domain and c['domains'] and domain not in c['domains']:
            continue
        if scores[i] < min_score:
            break
        out.append({**c, 'score': float(scores[i])})
        if len(out) == k:
            break
    return out


def chunk(doc, section):
    """문서 파일명 + 절 제목으로 조각 하나 (fine-tune 데이터가 '정답 조각' 을 지정할 때 쓴다)."""
    return next((c for c in _build()['chunks'] if c['doc'] == doc and c['section'] == section), None)


def refs_for(knowledge, situation, domain, k=2):
    """검사 결과(대표 유형)에 맞는 참고 조각. 보고서 작성(writer)과 fine-tune 데이터 생성이 같은 질의를 쓰도록 여기서 만든다."""
    rep = situation.get('representative')
    kb = next((x for x in knowledge if x['type'] == rep), None) or (knowledge[0] if knowledge else None)
    if not kb:
        return []
    names = ' '.join(str(kb.get(f'name_{l}', '')) for l in ('ko', 'vi', 'en'))
    return search(f'{kb["type"]} {names} {kb.get("description", "")}', domain, k=k)


def context_block(hits):
    """프롬프트에 넣을 참고 자료 블록 ([S1] 형식 — 답변에서 출처 번호로 인용)."""
    return '\n'.join(f'[S{i}] ({h["title"]} / {h["section"]}; {h["source"].split(" ; ")[0]})\n{h["text"][:450]}'
                     for i, h in enumerate(hits, 1))
