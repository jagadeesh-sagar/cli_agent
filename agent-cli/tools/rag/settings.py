import os 
from pathlib import Path

INDEX_DIRNAME=".agent_index"

EMBED_MODEL="all-MiniLM-L6-v2"
RERANK_MODEL="cross-encoder/ms-marco-MiniLM-L-6-v2"
USE_RERANKER=os.getenv("RAG_RERANK","1")!="0"

MAX_FILE_BYTES = 400_000
WINDOW_LINES = 50
WINDOW_OVERLAP = 10
MAX_CHUNK_LINES = 80
EMBED_CHAR_LIMIT = 2000

CANDIDATES_PER_RETRIEVER = 20
RRF_K = 60
RERANK_TOP_N = 30
FINAL_TOP_K = 6
MAX_CHUNKS_PER_FILE = 3
MIN_RERANK_SCORE = -6.0
CONTEXT_CHAR_BUDGET = 9000

SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "env", "__pycache__", INDEX_DIRNAME,
    "memory", "dist", "build", ".mypy_cache", ".pytest_cache", ".idea", ".vscode",
    "site-packages", "target", ".next", "coverage",
}
SKIP_FILES = {".env", "package-lock.json", "yarn.lock", "poetry.lock", "pnpm-lock.yaml", "PLAN.json", "eval.py", "try.py"}
CODE_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".c", ".h",
    ".cpp", ".hpp", ".cs", ".rb", ".php", ".sh", ".sql", ".html", ".css", ".scss",
    ".vue", ".svelte", ".md", ".toml", ".yaml", ".yml", ".json",
}
REGEX_SYMBOL_EXTS = {
    ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".sh", ".java", ".kt",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".rb", ".php", ".vue", ".svelte",
}
EXT_NAMES = {e.lstrip(".") for e in CODE_EXTS}


def index_dir(root: Path) -> Path:
    d = Path(root).resolve() / INDEX_DIRNAME
    d.mkdir(parents=True, exist_ok=True)
    return d