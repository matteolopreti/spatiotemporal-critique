"""critic_providers.py — the one place the cloud provider table lives.

Imported by both external_critic.py (--discover / --configure) and critic_setup.py
(guided setup), so the provider -> (lineage, OpenAI-compatible base URL) map can't
drift between them. Base URLs are perishable — verify on each vendor's own docs.
Each lineage is DIFFERENT from Claude (that is what buys the independence).
"""

import os

PROVIDERS = {
    "openai":       ("GPT",      "https://api.openai.com/v1"),
    "google":       ("Gemini",   "https://generativelanguage.googleapis.com/v1beta/openai"),
    "deepseek":     ("DeepSeek", "https://api.deepseek.com/v1"),
    "glm":          ("GLM",      "https://api.z.ai/api/paas/v4"),
    "mistral":      ("Mistral",  "https://api.mistral.ai/v1"),
    # Cloudflare Workers AI: one key serves MANY lineages (GLM, Kimi, DeepSeek, Qwen,
    # Gemma…) with a free daily allocation. Needs CLOUDFLARE_ACCOUNT_ID for the base URL.
    "cloudflare":   ("(varies)", "https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1"),
    "perplexity":   ("Sonar",    "https://api.perplexity.ai"),
    "ollama-cloud": ("(varies)", "https://ollama.com/v1"),
}

# Providers that serve NO OpenAI-compat GET /models (Cloudflare 405s, Perplexity 404s):
# discovery falls back to these hand-refreshed candidates — verified live 2026-07;
# re-verify on the vendor's docs when they stop answering.
STATIC_MODELS = {
    "cloudflare": ["@cf/zai-org/glm-5.2", "@cf/moonshotai/kimi-k2.7-code",
                   "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b", "@cf/qwen/qwen3-30b-a3b-fp8"],
    "perplexity": ["sonar-pro", "sonar", "sonar-reasoning-pro"],
}


def resolve_base(base):
    """Fill Cloudflare's {account} placeholder from CLOUDFLARE_ACCOUNT_ID (env; the
    account id is not a secret). None = unfillable -> the caller skips that provider."""
    if "{account}" not in base:
        return base
    acct = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    return base.replace("{account}", acct) if acct else None
