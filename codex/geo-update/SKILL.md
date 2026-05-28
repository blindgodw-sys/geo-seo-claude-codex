---
name: geo-update
description: Safe Codex update workflow for the GEO-SEO skill bundle. Use for geo update requests, update checks, and refreshing an installed Codex GEO skill without deleting local files.
---

# GEO-SEO Update For Codex

Use the installed CLI for update checks:

```bash
~/.codex/skills/geo/scripts/geo_cli.py update
```

If `CODEX_HOME` is set, use:

```bash
"${CODEX_HOME}/skills/geo/scripts/geo_cli.py" update
```

## Rules

1. Default to dry-run update checks. The CLI reports the current checkout and
   does not modify installed files.
2. To refresh the installation, update the source checkout and run
   `codex-install.sh` from that checkout.
3. The Codex installer moves replaced skill directories to a timestamped
   `/tmp/geo-codex-install-*` backup directory. Do not delete installed files
   or temporary directories during the update workflow.
4. After reinstalling, verify visibility with:

```bash
codex debug prompt-input 'geo audit https://example.com'
```

