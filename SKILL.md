---
name: llms-pipeline
description: >
  Generates spec-compliant llms.txt files for any website from scratch.
  Crawls the site, discovers navigation, business info, and policies,
  then produces a comprehensive llms.txt following llmstxt.org spec.
  Also generates llms-full.txt, llms-ctx.txt, and llms-ctx-full.txt variants.
  Supports 10 site types: ecommerce, saas, news, corporate, restaurant,
  education, healthcare, nonprofit, portfolio, government.
  Trigger: "llms uret", "llms.txt pipeline", "generate llms.txt for this site",
  "bu site icin llms dosyalari olustur", "llms-ctx uret", "AEO dosyalari hazirla",
  or any request involving llms.txt creation or site content mapping for LLMs.
---

# llms.txt Pipeline Skill

This skill generates comprehensive, spec-compliant llms.txt files for any website.
It goes beyond simple reformatting — it crawls the site to discover structure,
business context, and policies, then produces a rich output that LLMs can actually use.

The pipeline automatically detects the site type and adapts its discovery and
section structure accordingly.

All output MUST be in English regardless of the site's language.

## llmstxt.org Spec (the rules)

A valid llms.txt follows this structure:

```markdown
# Site Name                          ← H1 (required, only one)

> One-line summary of what this site/company is   ← blockquote (optional)

Additional context paragraphs...     ← body text (optional)

## Section Name                      ← H2 sections (optional, unlimited)
- [Link Title](https://url): Description of what this page contains
```

Key rules:
- Only ONE `# H1` — the site/brand name
- `> blockquote` for the summary — keep it 1-2 sentences
- Body text for essential context (contact info, key facts)
- `## H2` sections with `- [title](url): description` links
- `## Optional` section for secondary/nice-to-have links
- Keep it concise and expert-level, not a full documentation dump

## Output Formats

| Format | Description |
|--------|-------------|
| `llms.txt` | Spec-compliant structured overview of the site |
| `llms-full.txt` | Each link's content fetched and embedded inline |
| `llms-ctx.txt` | XML context format (Optional section excluded) |
| `llms-ctx-full.txt` | XML context format (Optional section included) |

## Workflow

When a user provides a URL, follow these steps:

### Step 1: Discovery

Use the helper script for initial data gathering:

```bash
python3 ~/.claude/skills/llms-pipeline/scripts/llms_pipeline.py discover https://example.com
```

This probes the site, **auto-detects the site type**, and saves raw discovery data
including type scores. The script probes common paths first, then type-specific paths.

Also use WebFetch to explore pages the script found, especially:
- Homepage (navigation structure, mega menu)
- Key pages identified by the type-specific probe

### Step 2: Review detected type

The discovery output includes `site_type` and `type_scores`. Check if the detection
makes sense. If it doesn't, override it mentally and use the correct type's section
checklist below.

### Step 3: Build the llms.txt

Using discovery data, construct the llms.txt using the **type-specific section checklist**
below. The goal is to give an LLM everything it needs to answer questions about this site.

### Step 4: Save Output

Save to `output_<domain>/llms.txt` in the current working directory.

Ask the user if they also want llms-full.txt, llms-ctx.txt, or llms-ctx-full.txt.
For those formats, use the script:

```bash
echo "2,3,4" | python3 ~/.claude/skills/llms-pipeline/scripts/llms_pipeline.py https://example.com
```

## Site Types & Section Checklists

Every llms.txt starts with:
- `# Brand/Site Name` + `> summary` + body with contact info / key facts

Then add sections based on the detected type:

---

### E-commerce

| Section | What to include |
|---------|----------------|
| `## Shopping Channels` | Website, mobile apps, marketplace presence |
| `## Stores` | Store locator, formats, count, hours (if physical retail) |
| `## Shipping & Delivery` | Methods, times, costs, coverage area, free shipping threshold |
| `## Returns & Payments` | Return policy, payment methods, installments |
| `## Key Features` | USPs, guarantees, loyalty programs |
| `## [Category]` | Product categories with subcategories (e.g. Women, Men, Kids, Home) |
| `## Campaigns` | Active promotions, deals page |
| `## Corporate` | About page, parent company, legal info |
| `## Optional` | Brand directory, account pages, legal, editorial |

---

### SaaS / Software

| Section | What to include |
|---------|----------------|
| `## Product` | Core features, key capabilities |
| `## Pricing` | Plans, tiers, free tier, enterprise |
| `## Documentation` | Docs, guides, tutorials, quickstart |
| `## API` | API reference, SDKs, libraries, authentication |
| `## Integrations` | Available integrations, marketplace, plugins |
| `## Solutions` | Use cases, industries served |
| `## Customers` | Case studies, testimonials, logos |
| `## Resources` | Blog, changelog, status page, community |
| `## Company` | About, careers, press, security/compliance |
| `## Optional` | Legal, open source, events |

---

### News / Media

| Section | What to include |
|---------|----------------|
| `## Sections` | Main content categories (Politics, Economy, World, Sports, etc.) |
| `## Opinion` | Columnists, editorials, op-eds |
| `## Multimedia` | Video, podcast, photo galleries, live |
| `## Subscribe` | Subscription plans, newsletter, app |
| `## About` | Masthead, editorial team, contact, history |
| `## Optional` | Archive, special reports, events, supplements |

---

### Corporate / Business Services

| Section | What to include |
|---------|----------------|
| `## Services` | Core service offerings |
| `## Solutions` | Industry solutions, verticals |
| `## Case Studies` | Client work, success stories |
| `## About` | Story, mission, values, leadership team |
| `## Careers` | Jobs, culture, benefits |
| `## Investors` | IR page, annual reports, financials (if public) |
| `## News & Press` | Press releases, media kit |
| `## Locations` | Offices, global presence |
| `## Optional` | Sustainability, CSR, partners, legal |

---

### Restaurant / Food & Beverage

| Section | What to include |
|---------|----------------|
| `## Menu` | Full menu with categories, dietary info, seasonal menus |
| `## Reservations` | How to book, party sizes, private dining |
| `## Order` | Online ordering, delivery, takeout options |
| `## Locations` | Addresses, hours, maps, parking |
| `## About` | Story, chef, philosophy, cuisine style |
| `## Events` | Special events, catering, private dining |
| `## Optional` | Gift cards, wine list, gallery, careers |

---

### Education

| Section | What to include |
|---------|----------------|
| `## Programs` | Degrees, certificates, majors, departments |
| `## Admissions` | How to apply, requirements, deadlines, tuition |
| `## Campus` | Campus life, facilities, housing, dining |
| `## Faculty & Research` | Notable faculty, research centers, publications |
| `## Student Life` | Clubs, athletics, student services |
| `## Alumni` | Alumni network, notable alumni, giving |
| `## About` | History, mission, rankings, accreditation |
| `## Optional` | Library, events, news, athletics, calendar |

---

### Healthcare

| Section | What to include |
|---------|----------------|
| `## Services` | Medical services, specialties, departments |
| `## Find a Doctor` | Physician directory, specialties, availability |
| `## Patients` | Appointments, patient portal, insurance, billing |
| `## Locations` | Hospitals, clinics, ERs, addresses, hours |
| `## Health Library` | Conditions, treatments, wellness info |
| `## About` | History, mission, awards, accreditation |
| `## Optional` | Research, careers, education, giving, visitors |

---

### Nonprofit / NGO

| Section | What to include |
|---------|----------------|
| `## Mission` | What they do, who they serve, approach |
| `## Programs` | Active programs, initiatives, campaigns |
| `## Impact` | Results, reports, success stories |
| `## Get Involved` | Donate, volunteer, advocate, events |
| `## About` | History, leadership, financials, partners |
| `## Resources` | Reports, publications, data, toolkits |
| `## Optional` | Press, careers, corporate partnerships |

---

### Portfolio / Personal

| Section | What to include |
|---------|----------------|
| `## Work` | Projects, case studies, selected work |
| `## About` | Bio, skills, experience, philosophy |
| `## Services` | What they offer, availability, process |
| `## Writing` | Blog posts, articles, talks |
| `## Contact` | How to reach, social links, availability |
| `## Optional` | Uses, now page, colophon, testimonials |

---

### Government

| Section | What to include |
|---------|----------------|
| `## Services` | Citizen services, online services, forms |
| `## Departments` | Government departments, agencies |
| `## Transparency` | Budget, procurement, tenders, public records |
| `## Council / Officials` | Elected officials, meetings, agendas |
| `## News` | Announcements, press releases, events |
| `## About` | History, mission, demographics, maps |
| `## Optional` | Careers, emergency, directory, calendars |

---

### Generic (fallback)

If the site doesn't fit any specific type, use a flexible structure:

| Section | What to include |
|---------|----------------|
| `## About` | What the site/org does |
| `## Key Pages` | Most important pages from discovery |
| `## Resources` | Blog, docs, guides, FAQs |
| `## Contact` | How to reach |
| `## Optional` | Everything else |

## Quality Standards

A good llms.txt:
- Has context an LLM couldn't get from just crawling (specific data, policies, numbers)
- Includes real data: phone numbers, hours, thresholds, prices, deadlines
- Has proper depth in its domain (not just top-level categories)
- Uses `## Optional` correctly for secondary content
- Is written in English, even for non-English sites — translate but keep proper nouns as-is
- Stays under ~200 lines for core sections (excluding Optional)
- Uses sections appropriate to the site type

A bad llms.txt:
- Just lists URLs without context
- Has no domain-specific info (just generic about/contact)
- Dumps hundreds of links into one section
- Uses wrong format (URL:/TITLE:/DESCRIPTION: instead of markdown links)
- Has multiple H1 headers
- Uses e-commerce sections for a SaaS site (or vice versa)

## Helper Script

The `scripts/llms_pipeline.py` script (v4.0) handles:
- Site type auto-detection (10 types + generic fallback)
- Type-specific page probing
- Fetching and parsing existing llms.txt files (both spec and flat formats)
- Generating llms-full.txt, llms-ctx.txt, llms-ctx-full.txt from a finalized llms.txt

Dependencies:
```bash
pip install requests beautifulsoup4 markdownify
```

## Notes

- `llms-full.txt` and `llms-ctx*` formats fetch link content — can be slow for large sites
- Content is truncated to 3000-4000 chars per link to stay within token limits
- Output goes to `output_<domain>/` directory
- Always verify URLs are accessible before including them
- The site type detection uses keyword scoring from nav links, page text, meta tags, and domain name
- You can override the detected type if it seems wrong — use your judgment
