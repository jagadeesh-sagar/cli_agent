"""
providers/__init__.py — Provider factory.

Reads `provider` from .agent.yaml (via cfg) and returns the correct
LLM provider instance.  Everything else in the codebase just does:

    from providers import get_provider
    provider = get_provider()

To add a new provider (e.g. Groq):
  1. Create providers/groq.py  with a GroqProvider(BaseProvider) class
  2. Register it in REGISTRY below
  3. Set  provider: groq  in .agent.yaml  — done, no other changes needed
"""

from config import cfg
from .base import BaseProvider

# ── Registry: name → class (imported lazily to avoid unnecessary deps) ─────────
def _load_provider(name: str) -> BaseProvider:
    """Import and instantiate the provider class matching `name`."""
    name = name.lower().strip()

    if name == "anthropic":
        from .anthropic import AnthropicProvider
        return AnthropicProvider()

    # ── OpenAI-compatible providers (one class handles all of them) ────────────
    if name in ("groq", "deepseek", "openrouter", "together", "openai", "sarvam","google"):
        from .openai_compat import OpenAICompatProvider
        return OpenAICompatProvider(provider_name=name)

    # ── Add more providers here as you build them ──────────────────────────────
    # if name == "cohere":
    #     from .cohere import CohereProvider
    #     return CohereProvider()

    raise ValueError(
        f"Unknown provider '{name}'. "
        f"Check providers/ folder and the REGISTRY in providers/__init__.py"
    )


# ── Executor singleton ─────────────────────────────────────────────────────────
_instance: BaseProvider | None = None

def get_provider() -> BaseProvider:
    """Return the shared executor provider instance (created from cfg.provider)."""
    global _instance
    if _instance is None:
        _instance = _load_provider(cfg.provider)
    return _instance


# ── Planner singleton (separate — can be a different model/provider) ───────────
_planner_instance: BaseProvider | None = None

def get_planner_provider() -> BaseProvider:
    """
    Return the shared planner provider instance.

    Reads cfg.planner_provider and cfg.planner_model from .agent.yaml.
    Falls back to the executor provider if planner_provider is not set,
    so existing setups with only `provider:` still work.
    """
    global _planner_instance
    if _planner_instance is None:
        planner_name = getattr(cfg, "planner_provider", None) or cfg.provider
        _planner_instance = _load_provider(planner_name)
    return _planner_instance