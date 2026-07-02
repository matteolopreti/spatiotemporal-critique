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
# (deepseek-r1 / gpt-oss retired 2026-07: reachable but null on real artifacts —
#  they summarized instead of critiquing; gemma4:12b probed 2/2 on the planted flaws.)
LOCAL_MODELS = [
    ("qwen3:4b", 3, "light floor"),
    ("qwen3:8b", 5, "good general floor"),
    ("gemma4:12b", 8, "probed 2/2 — strong reviewer, Gemini lineage"),
    ("qwen3:14b", 9, "strong general"),
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


# Cloud providers live in the shared critic_providers module (one source of truth,
# imported by external_critic.py too, so the map can't drift between the two scripts).
from critic_providers import PROVIDERS  # noqa: E402


def _shell_base(url, shell):
    """A provider base for the critic-env snippet: Cloudflare's {account} becomes a
    shell-expanded CLOUDFLARE_ACCOUNT_ID reference (set it in your rc; not a secret)."""
    ref = {"powershell": "$env:CLOUDFLARE_ACCOUNT_ID",
           "fish": "$CLOUDFLARE_ACCOUNT_ID"}.get(shell, "${CLOUDFLARE_ACCOUNT_ID}")
    return url.replace("{account}", ref)


def key_storage_cmd(osn, provider):
    """Store THIS provider's key under a PER-PROVIDER item, so several keys (OpenAI +
    Google + …) coexist without overwriting each other."""
    item = f"critic-api-key-{provider}"
    envvar = "CRITIC_API_KEY_" + provider.upper().replace("-", "_")
    return {
        # the trailing -w with NO value PROMPTS — the key never lands on the command line/history
        "Darwin": f'security add-generic-password -s {item} -a "$USER" -w   # prompts; nothing on disk/history',
        "Linux":  f'secret-tool store --label="{item}" service {item}        # prompts; or use `pass`',
        # native Windows: a per-provider User env var, set via Read-Host so the key is NEVER on the
        # command line / PSReadLine history (setx would leak it; the GUI works too).
        "Windows": f'[Environment]::SetEnvironmentVariable("{envvar}", (Read-Host "Paste {provider} key"), "User")'
                   '   # PowerShell; prompts, nothing in history',
    }.get(osn, f"store the key as {item} in your OS secret manager (never a dotfile or your history)")


def env_snippet(shell, osn):
    """ONE `critic-env <provider> [model]` for the detected shell — it switches the base
    URL per provider and loads THAT provider's per-provider key, so all your keys coexist
    behind a single function. CRITIC_MODEL is left empty so `--discover` can choose."""
    names = " | ".join(PROVIDERS)
    if shell in ("zsh", "bash"):
        cases = "\n".join(f'    {p}) export CRITIC_BASE_URL="{_shell_base(u, shell)}" ;;'
                          for p, (lg, u) in PROVIDERS.items())
        load = {"Darwin": 'export CRITIC_API_KEY="$(security find-generic-password -s critic-api-key-$1 -w 2>/dev/null)"',
                "Linux":  'export CRITIC_API_KEY="$(secret-tool lookup service critic-api-key-$1)"',
                }.get(osn, 'export CRITIC_API_KEY="$CRITIC_API_KEY"   # load critic-api-key-$1 from your secret store')
        return ("critic-env() {                          # usage: critic-env <provider> [model]\n"
                '  case "$1" in\n'
                f"{cases}\n"
                f'    *) echo "usage: critic-env <{names}> [model]" >&2; return 1 ;;\n'
                "  esac\n"
                '  export CRITIC_MODEL="${2:-}"           # empty -> --discover picks\n'
                f"  {load}\n"
                '  [ -n "$CRITIC_API_KEY" ] && echo "critic-env: $1 ready" || echo "WARN: no key stored for $1" >&2\n'
                "}")
    if shell == "fish":
        cases = "\n".join(f'    case {p}; set -gx CRITIC_BASE_URL "{_shell_base(u, shell)}"'
                          for p, (lg, u) in PROVIDERS.items())
        load = {"Darwin": "set -gx CRITIC_API_KEY (security find-generic-password -s critic-api-key-$argv[1] -w 2>/dev/null)",
                "Linux":  "set -gx CRITIC_API_KEY (secret-tool lookup service critic-api-key-$argv[1])",
                }.get(osn, "set -gx CRITIC_API_KEY $CRITIC_API_KEY")
        return ("function critic-env               # usage: critic-env <provider> [model]\n"
                "  switch $argv[1]\n"
                f"{cases}\n"
                f'    case "*"; echo "usage: critic-env <{names}> [model]" >&2; return 1\n'
                "  end\n"
                '  set -gx CRITIC_MODEL "$argv[2]"   # quoted: omitted arg -> empty string, not unset\n'
                f"  {load}\n"
                "end")
    if shell == "powershell":
        cases = "\n".join(f'    "{p}" {{ $env:CRITIC_BASE_URL = "{_shell_base(u, shell)}" }}'
                          for p, (lg, u) in PROVIDERS.items())
        return ("function critic-env {              # usage: critic-env <provider> [model]\n"
                "  switch ($args[0]) {\n"
                f"{cases}\n"
                f'    default {{ Write-Error "usage: critic-env <{names}> [model]"; return }}\n'
                "  }\n"
                "  $env:CRITIC_MODEL = $args[1]\n"
                '  $key = "CRITIC_API_KEY_" + $args[0].ToUpper().Replace("-","_")\n'
                '  $env:CRITIC_API_KEY = [Environment]::GetEnvironmentVariable($key, "User")\n'
                '  if (-not $env:CRITIC_API_KEY) { Write-Warning "no key stored for $($args[0]) ($key)" }\n'
                "}")
    return "# set CRITIC_BASE_URL per provider and load CRITIC_API_KEY from your OS secret store"


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
    print("  · then build the panel:         python3 external_critic.py --configure")


def show_cloud(provider, osn, shell, rc):
    lineage, base = PROVIDERS[provider]
    print(f"CLOUD PROVIDER: {provider}  (lineage: {lineage}; a paid/keyed, different-lineage seat)")
    print(f"  verify the base URL on the vendor's docs (these move): {base}")
    if "{account}" in base:
        print("  needs your account id too (dash.cloudflare.com — it's in the dashboard URL; not a secret):")
        print("      export CLOUDFLARE_ACCOUNT_ID=<id>       # put it in your shell rc, or the skill's .env")
    print()
    print(f"  1) store {provider}'s key under its OWN item (so several keys coexist) — never a dotfile/history:")
    print("       " + key_storage_cmd(osn, provider))
    print(f"\n  2) add this ONE function to your shell profile ({rc}) — it handles ALL your providers:\n")
    for line in env_snippet(shell, osn).splitlines():
        print("       " + line)
    print(f"\n  3) load THIS provider, discover its models, certify, build the panel:")
    print(f"       critic-env {provider}")
    print("       python3 external_critic.py --discover     # models this key serves, newest-first + score")
    print("       python3 external_critic.py --probe        # certify the one you pick")
    print("       python3 external_critic.py --configure    # pick + REMEMBER 1-3 across lineages; paid flagged")
    print(f"\n  MULTIPLE KEYS (e.g. OpenAI + Google)? Repeat step 1 for each (its own item), then before probing")
    print(f"  each, switch with `critic-env <provider>`. The registry keeps every capable seat, and `--configure`")
    print(f"  builds ONE panel spanning all your distinct lineages — both keys are recognized.")


_MARKER = "# external critic (spatiotemporal-critique) — critic-env <provider> [model]"


def do_install(osn, shell, rc, assume_yes):
    """Consent-gated, idempotent: append the critic-env function to the rc file. ONE
    upfront prompt (not per-action). Prints the key-store commands (each interactive +
    safe) — it never types your key. Returns a non-zero code in a non-TTY session that
    gave no --yes, so CI knows nothing was installed."""
    if shell not in ("zsh", "bash", "fish"):
        print(f"--install writes rc files for zsh/bash/fish; on {shell} use the printed guidance:")
        show_cloud(next(iter(PROVIDERS)), osn, shell, rc)
        return 2
    snippet = env_snippet(shell, osn)
    try:
        existing = open(rc, encoding="utf-8").read() if os.path.exists(rc) else ""
    except OSError:
        existing = ""
    if "critic-env()" in existing or "function critic-env" in existing:
        print(f"critic-env is already in {rc} — nothing to append (idempotent).")
    else:
        if not assume_yes and not sys.stdin.isatty():
            print(f"would append critic-env to {rc}, but this is non-interactive and no --yes was given.\n"
                  f"re-run with --yes, or paste it yourself (python3 critic_setup.py --provider <x>).")
            return 1
        ok = assume_yes or input(f"Append the critic-env function to {rc}? [y/N] ").strip().lower() in ("y", "yes")
        if not ok:
            print("declined — nothing written.")
            return 0
        try:
            with open(rc, "a", encoding="utf-8") as f:
                f.write(f"\n{_MARKER}\n{snippet}\n")
            print(f"✓ appended critic-env to {rc} — open a new shell or `source {rc}`.")
        except OSError as e:
            sys.exit(f"could not write {rc}: {e}")
    print("\nNow store each provider's key (interactive prompt — never on the command line/history):")
    for p in ("openai", "google"):
        print("   " + key_storage_cmd(osn, p))
    print("   …(same for deepseek | glm | mistral | cloudflare | perplexity | ollama-cloud)")
    print("\nThen configure the panel:  critic-env <provider> ; python3 external_critic.py --configure")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Guided, cross-platform setup for the external critic.")
    ap.add_argument("--provider", default="local",
                    choices=["local", "list", *PROVIDERS],
                    help="local Ollama (default, free) | a cloud vendor | 'list' to show the table")
    ap.add_argument("--install", action="store_true",
                    help="consent-gated: append the critic-env function to your shell rc (idempotent)")
    ap.add_argument("--yes", action="store_true",
                    help="assume yes (for --install in a non-interactive session)")
    args = ap.parse_args()

    osn, shell = os_name(), detect_shell()
    rc, ram = rc_file(shell), ram_gb()

    if args.install:
        print(f"# external-critic install — {osn} · {shell} · rc={rc}\n")
        print("This will APPEND a critic-env function to your rc (with your ok) and PRINT key-store commands.")
        print("It never stores a key itself, installs software, or pulls a model.\n")
        sys.exit(do_install(osn, shell, rc, args.yes))

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
    print("\nThis prints guidance only (stores/installs/pulls nothing). To append the function for you: --install.")


if __name__ == "__main__":
    main()
