#!/usr/bin/env python3
"""critic_setup.py — cross-platform, GUIDED setup for the external critic.

Detects your OS, shell, RAM, and Ollama, then prints a tailored, copy-pasteable
setup — so you don't hand-edit dotfiles or hard-code a model:

  * a LOCAL free critic: the best Ollama model for your RAM (pull only on your say-so);
  * a CLOUD critic: safe API-key storage in your OS secret store + the `critic-env`
    snippet for YOUR shell, then `external_critic.py --discover` to pick models by score.

Detection + guidance ONLY. It never stores a key, installs software, or pulls a model
on its own — it prints the exact commands and leaves the doing to you. Stdlib only,
cross-platform (macOS / Linux / Windows; zsh / bash / fish / PowerShell).

Usage:
    python3 critic_setup.py                      # local Ollama (free) — the default
    python3 critic_setup.py --provider google    # a cloud, different-lineage seat
    python3 critic_setup.py --provider list      # show the provider table
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys


def os_name():
    return platform.system()  # "Darwin" | "Linux" | "Windows"


def detect_shell():
    """Best-effort current shell (the rc file we point you at depends on it)."""
    if os.name == "nt":
        # PSModulePath is set inside PowerShell; otherwise assume classic cmd.
        return "powershell" if os.environ.get("PSModulePath") else "cmd"
    sh = os.environ.get("SHELL", "")
    for s in ("zsh", "fish", "bash"):
        if s in sh:
            return s
    return "bash"


def rc_file(shell):
    home = os.path.expanduser("~")
    return {
        "zsh": os.path.join(home, ".zshrc"),
        # macOS login shells read ~/.bash_profile; most Linux read ~/.bashrc
        "bash": os.path.join(home, ".bash_profile" if os_name() == "Darwin" else ".bashrc"),
        "fish": os.path.join(home, ".config", "fish", "config.fish"),
        "powershell": "$PROFILE  (run `notepad $PROFILE`)",
        "cmd": "a User environment variable (setx), not an rc file",
    }.get(shell, os.path.join(home, ".profile"))


def ram_gb():
    """Total physical RAM in GiB (0 = couldn't tell). Cross-platform, stdlib only."""
    try:
        s = os_name()
        if s == "Darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], timeout=5)
            return int(out.strip()) // (1024 ** 3)
        if s == "Linux":
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        return int(line.split()[1]) // (1024 ** 2)  # kB -> GiB
        if s == "Windows":
            import ctypes

            class _MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = _MS()
            m.dwLength = ctypes.sizeof(_MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))  # type: ignore[attr-defined]
            return int(m.ullTotalPhys) // (1024 ** 3)
    except Exception:  # noqa: BLE001 — detection is best-effort; 0 means "unknown"
        return 0
    return 0


# Local Ollama candidates, best-first, with approx LOADED GiB. Perishable — verify the
# current strong tags on ollama.com/library; refresh this list by hand. Pick a lineage
# DIFFERENT from your primary model for real independence.
LOCAL_MODELS = [
    ("qwen3:4b", 3, "light floor"),
    ("qwen3:8b", 5, "good general floor"),
    ("deepseek-r1:14b", 9, "reasoning, different lineage"),
    ("gpt-oss:20b", 14, "strong; wants ~24GB+"),
    ("qwen3:32b", 20, "stronger; wants ~32GB+"),
]


def recommend_local(ram):
    """Biggest candidate that fits ~60% of RAM (the comfortable, stays-on-GPU budget)."""
    if ram <= 0:
        return None, "RAM unknown — see ollama.com/library and pick by size"
    comfort = ram * 60 // 100
    fit = [m for m in LOCAL_MODELS if m[1] <= comfort]
    if fit:
        name, gb, note = fit[-1]
        return (name, gb, note), f"~{gb}GB loaded, comfortable on {ram}GB RAM"
    name, gb, note = LOCAL_MODELS[0]
    return (name, gb, note), f"~{gb}GB (tight on {ram}GB — or use a cloud key for something bigger)"


# Cloud providers (OpenAI-compatible base URLs). Each a DIFFERENT lineage from Claude.
# Base URLs are perishable — verify on the vendor's own docs before trusting.
PROVIDERS = {
    "openai":       ("GPT",      "https://api.openai.com/v1"),
    "google":       ("Gemini",   "https://generativelanguage.googleapis.com/v1beta/openai"),
    "deepseek":     ("DeepSeek", "https://api.deepseek.com/v1"),
    "glm":          ("GLM",      "https://api.z.ai/api/paas/v4"),
    "mistral":      ("Mistral",  "https://api.mistral.ai/v1"),
    "ollama-cloud": ("(varies)", "https://ollama.com/v1"),
}


def key_storage_cmd(osn, item="critic-api-key"):
    return {
        # the trailing -w with NO value PROMPTS — the key never lands on the command line/history
        "Darwin": f'security add-generic-password -s {item} -a "$USER" -w   # prompts; nothing on disk/history',
        "Linux":  f'secret-tool store --label="{item}" service {item}        # prompts; or use `pass`',
        # native Windows: a User env var. setx writes to console history, so prefer the GUI for secrecy.
        "Windows": 'System Properties > Environment Variables > New User variable CRITIC_API_KEY  '
                   '(GUI = no history)\n       #   quick alt (writes to console history): '
                   'setx CRITIC_API_KEY "<paste-key>"',
    }.get(osn, "store the key in your OS secret manager (never a dotfile or your shell history)")


def key_load_expr(osn, item="critic-api-key"):
    return {
        "Darwin": f'$(security find-generic-password -s {item} -w 2>/dev/null)',
        "Linux":  f'$(secret-tool lookup service {item})',
        "Windows": "$env:CRITIC_API_KEY",  # already present once stored as a User env var
    }.get(osn, "<your key, loaded from the secret store>")


def env_snippet(shell, base_url, osn):
    """A `critic-env`-style function for the detected shell. Loads endpoint + key
    just-in-time; leaves CRITIC_MODEL empty so `--discover` can choose."""
    load = key_load_expr(osn)
    if shell in ("zsh", "bash"):
        return ("critic-env() {                       # usage: critic-env [model]\n"
                f'  export CRITIC_BASE_URL="{base_url}"\n'
                '  export CRITIC_MODEL="${1:-}"        # empty -> run `--discover` to pick\n'
                f'  export CRITIC_API_KEY="{load}"\n'
                '  [ -n "$CRITIC_API_KEY" ] && echo "critic-env ready" || echo "WARN: key not found" >&2\n'
                "}")
    if shell == "fish":
        return ("function critic-env            # usage: critic-env [model]\n"
                f'  set -gx CRITIC_BASE_URL "{base_url}"\n'
                "  set -gx CRITIC_MODEL $argv[1]\n"
                f'  set -gx CRITIC_API_KEY ({load})\n'
                "end")
    if shell == "powershell":
        # CRITIC_API_KEY is a User env var (set once); a new shell already has it in $env.
        return ("function critic-env {            # usage: critic-env [model]\n"
                f'  $env:CRITIC_BASE_URL = "{base_url}"\n'
                "  $env:CRITIC_MODEL = $args[0]\n"
                "  if (-not $env:CRITIC_API_KEY) { Write-Warning 'CRITIC_API_KEY not set (User env var)' }\n"
                "}")
    return (f'set CRITIC_BASE_URL={base_url}\nset CRITIC_API_KEY=<your key>   '
            "(prefer a User env var over an inline set so it persists, not your history)")


def show_local(osn, shell, ram):
    have = shutil.which("ollama")
    rec, why = recommend_local(ram)
    print("LOCAL OLLAMA — free, private (nothing leaves your machine; a different lineage from Claude):")
    print("  · ollama installed:", "yes" if have else "NO — get it at https://ollama.com/download")
    if rec:
        name, gb, note = rec
        print(f"  · recommended for your RAM: {name}  ({why}; {note})")
        print(f"  · pull it WHEN YOU CHOOSE (≈{gb}GB):  ollama pull {name}")
        print(f"  · point the critic at it:  export CRITIC_MODEL={name}   (leave CRITIC_BASE_URL empty = local)")
    else:
        print(f"  · {why}")
    print("  · certify it really critiques:  python3 external_critic.py --probe")
    print("  · then build the panel:         python3 external_critic.py --select")


def show_cloud(provider, osn, shell, rc):
    lineage, base = PROVIDERS[provider]
    print(f"CLOUD PROVIDER: {provider}  (lineage: {lineage}; a paid/keyed, different-lineage seat)")
    print(f"  verify the base URL on the vendor's docs (these move): {base}\n")
    print("  1) store your API key in your OS secret store — NOT a dotfile, NOT your shell history:")
    print("       " + key_storage_cmd(osn))
    print(f"\n  2) add this to your shell profile ({rc}):\n")
    for line in env_snippet(shell, base, osn).splitlines():
        print("       " + line)
    print("\n  3) load it, then DISCOVER which models that key can use (pick by score & free/paid):")
    print("       critic-env")
    print("       python3 external_critic.py --discover")
    print("       python3 external_critic.py --select        # panel: distinct lineages, paid flagged")


def main():
    ap = argparse.ArgumentParser(description="Guided, cross-platform setup for the external critic.")
    ap.add_argument("--provider", default="local",
                    choices=["local", "list", *PROVIDERS],
                    help="local Ollama (default, free) | a cloud vendor | 'list' to show the table")
    args = ap.parse_args()

    osn, shell = os_name(), detect_shell()
    rc, ram = rc_file(shell), ram_gb()

    if args.provider == "list":
        print("Cloud providers (each a different lineage from Claude; verify base URLs on vendor docs):")
        for name, (lineage, base) in PROVIDERS.items():
            print(f"  {name:13} {lineage:10} {base}")
        print("\nLocal Ollama (free, no key) is the default: `python3 critic_setup.py`")
        return

    print(f"# external-critic setup — detected: {osn} · {shell} · {ram or '?'}GB RAM\n")
    if args.provider == "local":
        show_local(osn, shell, ram)
    else:
        show_cloud(args.provider, osn, shell, rc)
    print("\nNever commit the key. This script only DETECTS and PRINTS — it stores nothing, "
          "installs nothing, and pulls nothing on its own.")


if __name__ == "__main__":
    main()
