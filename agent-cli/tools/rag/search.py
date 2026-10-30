import threading
from pathlib import Path

from . import settings as S
from .builder import build_context
from .indexer import update_index
from .retrieve import hybrid_retrieve
from .store import Store
from .vector import VectorIndex

_engines: dict[str, dict] = {}
_engines_lock = threading.Lock()


def _root(path) -> Path:
    return Path(path or ".").expanduser().resolve()


def _engine(root: Path) -> dict:
    key = str(root)
    with _engines_lock:
        if key not in _engines:
            d = S.index_dir(root)
            _engines[key] = {"store": Store(d / "index.db"), "vec": VectorIndex(d),
                             "lock": threading.Lock()}
        return _engines[key]


def index_project(project_path: str = ".", force: bool = False) -> str:
    root = _root(project_path)
    if not root.is_dir():
        return f"TOOL_ERROR: {root} is not a directory"
    eng = _engine(root)
    with eng["lock"]:
        st = update_index(root, eng["store"], eng["vec"], force=force)
    return (f"Index ready for {root}: {st['files_indexed']} files (re)indexed, "
            f"{st['chunks']} chunks, {st['files_removed']} removed, "
            f"{st['total_files']} files tracked.")


def code_search(query: str, k: int = S.FINAL_TOP_K, path: str = ".") -> str:
    if not query or not query.strip():
        return "TOOL_ERROR: empty query"
    root = _root(path)
    if not root.is_dir():
        return f"TOOL_ERROR: {root} is not a directory"
    eng = _engine(root)
    with eng["lock"]:
        update_index(root, eng["store"], eng["vec"])
    hits = hybrid_retrieve(query, eng["store"], eng["vec"], max(1, min(int(k), 15)))
    return build_context(query, hits, root)


def warm_up(project_path: str = "."):
    def run():
        try:
            index_project(project_path)
            from .models import get_embedder, get_reranker
            get_embedder()
            get_reranker()
        except Exception as e:
            print(f"[RAG] warm-up failed: {e}")

    threading.Thread(target=run, daemon=True, name="rag-warmup").start()