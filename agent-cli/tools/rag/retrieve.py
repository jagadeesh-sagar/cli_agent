import re
from collections import defaultdict

from . import settings as S
from .models import embed, get_reranker
from .store import IDENT, STOPWORDS

_CODEY = re.compile(r"_|[a-z][A-Z]|^[A-Z]{2,}")
_DOTTED = re.compile(r"\b[A-Za-z_]\w*\.[A-Za-z_]\w*\b")


def analyze_query(query: str) -> tuple[set, set]:
    strong = {t.strip("`() ") for t in re.findall(r"`([^`]+)`", query)}
    strong |= set(_DOTTED.findall(query))
    first = query.split()[0] if query.split() else ""
    weak = set()
    for tok in IDENT.findall(query):
        if tok.lower() in STOPWORDS or len(tok) < 3:
            continue
        is_capitalised_mid = tok[0].isupper() and not tok.isupper() and tok != first
        (strong if _CODEY.search(tok) or is_capitalised_mid else weak).add(tok)
    return strong, weak - strong


def symbol_hits(store, strong: set, weak: set, limit: int):
    scores: dict[str, float] = {}
    for name, (sname, qual, kind, path, start, end, _sig) in store.find_symbols(list(strong | weak)):
        score = 2.0 if name in strong else 1.0
        if sname == name or qual == name:
            score += 1.0
        if kind in ("class", "function", "method"):
            score += 0.5
        for cid in store.chunks_covering(path, start, end):
            scores[cid] = max(scores.get(cid, 0.0), score)
    for t in strong:
        if "." in t and t.rsplit(".", 1)[-1].lower() in S.EXT_NAMES:
            for cid in store.chunks_for_path(t):
                scores[cid] = max(scores.get(cid, 0.0), 1.5)
    ranked = sorted(scores, key=scores.get, reverse=True)[:limit]
    return ranked, scores


def _rerank_text(ch: dict) -> str:
    return f"{ch['path']} {ch['symbol']}\n{ch['text'][:1500]}"


def hybrid_retrieve(query: str, store, vec, k: int) -> list[dict]:
    strong, weak = analyze_query(query)
    n = S.CANDIDATES_PER_RETRIEVER

    vector_ids = vec.query(embed([query])[0], n)
    bm25_ids = store.bm25(query, n)
    sym_ids, sym_scores = symbol_hits(store, strong, weak, n)

    weights = ({"vector": 0.7, "bm25": 1.0, "symbol": 1.6} if strong
               else {"vector": 1.2, "bm25": 0.8, "symbol": 0.6})

    fused: dict[str, float] = defaultdict(float)
    sources: dict[str, set] = defaultdict(set)
    for name, ids in (("vector", vector_ids), ("bm25", bm25_ids), ("symbol", sym_ids)):
        for rank, cid in enumerate(ids):
            fused[cid] += weights[name] / (S.RRF_K + rank + 1)
            sources[cid].add(name)
    if not fused:
        return []

    candidates = sorted(fused, key=fused.get, reverse=True)[:S.RERANK_TOP_N]
    chunks = store.get_chunks(candidates)
    candidates = [c for c in candidates if c in chunks]

    reranker = get_reranker()
    reranked = bool(reranker) and len(candidates) > 1
    if reranked:
        scores = reranker.predict([(query, _rerank_text(chunks[c])) for c in candidates],
                                  batch_size=16, show_progress_bar=False)
        final = {c: float(s) for c, s in zip(candidates, scores)}
    else:
        final = {c: fused[c] for c in candidates}

    pinned = [c for c in candidates if sym_scores.get(c, 0.0) >= 3.0]
    order = pinned + [c for c in sorted(candidates, key=final.get, reverse=True) if c not in pinned]

    picked, per_file = [], defaultdict(int)
    for c in order:
        if reranked and c not in pinned and len(picked) >= 2 and final[c] < S.MIN_RERANK_SCORE:
            continue
        path = chunks[c]["path"]
        if per_file[path] >= S.MAX_CHUNKS_PER_FILE:
            continue
        per_file[path] += 1
        picked.append({**chunks[c], "score": final[c], "sources": sorted(sources[c])})
        if len(picked) >= k:
            break
    return picked