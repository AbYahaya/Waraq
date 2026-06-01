# Font Installation for Export Preflight

Observation 2.4 requires the backend host to expose the critical export fonts through fontconfig.

## Required Font Families

- `KFGQPC Uthmanic Script HAFS`
- `Traditional Naskh`
- `Noto Sans Arabic`
- `Calibri`

Current local status checked on 2026-06-01:

- Available: `Noto Sans Arabic`
- Missing: `KFGQPC Uthmanic Script HAFS`, `Traditional Naskh`, `Calibri`
- Available through Ubuntu package only as a substitute: `Carlito`, via `fonts-crosextra-carlito`

## Install User-Provided Exact Fonts

Place the licensed `.ttf`, `.otf`, or `.ttc` files in one folder, then run:

```bash
cd /home/abyahaya/Waraq/Waraq
backend/scripts/install_local_fonts.sh /path/to/font-files
```

The script installs fonts into:

```text
~/.local/share/fonts/waraq
```

Then it refreshes fontconfig and prints the current matches for all four critical font names.

## Optional Calibri-Compatible Substitute

If exact Calibri is unavailable and a substitute is acceptable for local testing only:

```bash
sudo apt-get update
sudo apt-get install -y fonts-crosextra-carlito
```

This installs `Carlito`, which is metrically compatible with Calibri, but it does not satisfy exact `Calibri` font-name checks unless the app is explicitly changed to accept substitutes.

## Notes

- `Calibri` needs a licensed Microsoft font source for exact compliance.
- `KFGQPC Uthmanic Script HAFS` should come from the official King Fahd Quran Complex font package or another trusted licensed source.
- `Traditional Naskh` should come from a licensed source.
- The current guard-near check is intentionally strict: substitutes are not silently accepted for canonical export preflight.
