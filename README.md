# llms-pipeline

A Claude Code skill that generates spec-compliant `llms.txt` files for any website from scratch.

It crawls the site, discovers navigation, business info, and policies, then produces a comprehensive `llms.txt` following the [llmstxt.org](https://llmstxt.org) spec — plus `llms-full.txt`, `llms-ctx.txt`, and `llms-ctx-full.txt` variants.

Supports 10 site types: ecommerce, SaaS, news, corporate, restaurant, education, healthcare, nonprofit, portfolio, government.

## Installation

Clone into your Claude Code skills directory:

```bash
git clone https://github.com/<your-username>/llms-pipeline.git ~/.claude/skills/llms-pipeline
```

Install Python dependencies:

```bash
pip install -r ~/.claude/skills/llms-pipeline/requirements.txt
```

That's it — Claude Code will pick up the skill automatically.

## Usage

Once installed, just ask Claude Code in natural language. Trigger phrases:

- `"generate llms.txt for this site"`
- `"llms uret"`
- `"bu site icin llms dosyalari olustur"`
- `"llms-ctx uret"`
- `"AEO dosyalari hazirla"`

The skill will crawl the target site, detect its type, and produce all four llms.txt variants in English regardless of source language.

## Requirements

- Python 3.8+
- Claude Code

## License

MIT
