"""critic_providers.py — the one place the cloud provider table lives.

Imported by both external_critic.py (--discover / --configure) and critic_setup.py
(guided setup), so the provider -> (lineage, OpenAI-compatible base URL) map can't
drift between them. Base URLs are perishable — verify on each vendor's own docs.
Each lineage is DIFFERENT from Claude (that is what buys the independence).
"""

PROVIDERS = {
    "openai":       ("GPT",      "https://api.openai.com/v1"),
    "google":       ("Gemini",   "https://generativelanguage.googleapis.com/v1beta/openai"),
    "deepseek":     ("DeepSeek", "https://api.deepseek.com/v1"),
    "glm":          ("GLM",      "https://api.z.ai/api/paas/v4"),
    "mistral":      ("Mistral",  "https://api.mistral.ai/v1"),
    "ollama-cloud": ("(varies)", "https://ollama.com/v1"),
}
