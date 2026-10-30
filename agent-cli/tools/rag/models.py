import contextlib
import logging
import os
import threading
import warnings

from . import settings as S

os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TQDM_DISABLE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore")

for _name in ("sentence_transformers", "transformers", "huggingface_hub", "chromadb"):
    logging.getLogger(_name).setLevel(logging.ERROR)

_lock = threading.Lock()
_embedder = None
_reranker = None
_reranker_tried = False


@contextlib.contextmanager
def _quiet():
    with open(os.devnull, "w") as devnull:
        with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            try:
                from transformers.utils import logging as hf_logging
                hf_logging.set_verbosity_error()
                hf_logging.disable_progress_bar()
            except Exception:
                pass
            yield


def _load_st(cls, model_name: str, **kwargs):
    with _quiet():
        try:
            return cls(model_name, local_files_only=True, **kwargs)
        except Exception:
            os.environ.pop("HF_HUB_OFFLINE", None)
            res = cls(model_name, **kwargs)
            os.environ["HF_HUB_OFFLINE"] = "1"
            return res


def get_embedder():
    global _embedder
    with _lock:
        if _embedder is None:
            from sentence_transformers import SentenceTransformer
            _embedder = _load_st(SentenceTransformer, S.EMBED_MODEL)
        return _embedder


def embed(texts: list[str]) -> list[list[float]]:
    vecs = get_embedder().encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return vecs.tolist()


def get_reranker():
    global _reranker, _reranker_tried
    if not S.USE_RERANKER:
        return None
    with _lock:
        if not _reranker_tried:
            _reranker_tried = True
            try:
                from sentence_transformers import CrossEncoder
                _reranker = _load_st(CrossEncoder, S.RERANK_MODEL, max_length=512)
            except Exception:
                pass
        return _reranker
