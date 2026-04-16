#!/usr/bin/env python3
"""
llms.txt Pipeline v4.0
Generates spec-compliant llms.txt files for any website.

Modes:
  discover <url>   — Probe the site, detect site type, extract nav structure
  <url>            — Parse existing llms.txt and generate output formats

Site types: ecommerce, saas, news, corporate, restaurant, education,
            healthcare, nonprofit, portfolio, government, generic

Supported input formats:
  1. Spec-compliant (llmstxt.org): # Title, > summary, ## Section, - [title](url): desc
  2. Flat format: URL: / TITLE: / DESCRIPTION: triplets
  3. Mixed: Both formats in the same file
"""

import sys
import re
import os
import json
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import markdownify

# —— Helpers ————————————————————————————————————————————————————————

HEADERS = {"User-Agent": "llms-pipeline/4.0 (compatible; +https://llmstxt.org)"}

def normalize_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    return url.rstrip("/")

def fetch(url: str, timeout: int = 15) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            if "Just a moment" in r.text[:500] and "_cf_chl" in r.text:
                return None
            return r.text
    except Exception:
        pass
    return None

def html_to_markdown(html: str, base_url: str = "") -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
        tag.decompose()
    md = markdownify.markdownify(str(soup), heading_style="ATX", strip=["img"])
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()

def fetch_as_markdown(url: str) -> str | None:
    md_url = url.rstrip("/") + ".md"
    content = fetch(md_url)
    if content and not content.strip().startswith("<"):
        return content.strip()
    html = fetch(url)
    if html:
        return html_to_markdown(html, base_url=url)
    return None

def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text().strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text().strip()
    return ""

def extract_meta_description(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    return ""

def extract_meta_keywords(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "keywords"})
    if meta and meta.get("content"):
        return meta["content"].strip().lower()
    return ""

def extract_nav_links(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen = set()
    nav_elements = soup.find_all(["nav", "ul", "div"], class_=re.compile(
        r"nav|menu|mega|header|category|main-nav", re.I
    ))
    for nav in nav_elements:
        for a in nav.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/"):
                href = urljoin(base_url, href)
            if not href.startswith("http"):
                continue
            if href in seen:
                continue
            seen.add(href)
            text = a.get_text().strip()
            if text and len(text) > 1 and len(text) < 100:
                links.append({"title": text, "url": href})
    return links

def extract_all_link_texts(html: str) -> list[str]:
    """Extract all visible link texts for site type detection."""
    soup = BeautifulSoup(html, "html.parser")
    texts = []
    for a in soup.find_all("a"):
        t = a.get_text().strip().lower()
        if t and len(t) > 1 and len(t) < 80:
            texts.append(t)
    return texts

# —— Site Type Detection ——————————————————————————————————————————

SITE_TYPE_SIGNALS = {
    "ecommerce": {
        "keywords": [
            "shop", "cart", "add to cart", "buy", "checkout", "price",
            "shipping", "delivery", "kargo", "sepet", "satin al",
            "product", "catalog", "catalogue", "store", "order",
            "payment", "iade", "return", "refund", "free shipping",
            "sale", "discount", "coupon", "wishlist", "size guide",
        ],
        "paths": ["/cart", "/checkout", "/shop", "/products", "/collections", "/sepet"],
        "meta_patterns": [r"shop", r"store", r"buy", r"e-?commerce", r"retail"],
    },
    "saas": {
        "keywords": [
            "pricing", "plans", "sign up", "free trial", "demo",
            "documentation", "docs", "api", "developer", "sdk",
            "integrations", "changelog", "release notes", "status",
            "features", "solutions", "enterprise", "startup",
            "dashboard", "login", "get started", "book a demo",
        ],
        "paths": ["/pricing", "/docs", "/api", "/developer", "/changelog", "/status", "/integrations"],
        "meta_patterns": [r"saas", r"platform", r"software", r"cloud", r"api"],
    },
    "news": {
        "keywords": [
            "breaking", "headline", "opinion", "editorial", "columnist",
            "reporter", "subscribe", "newsletter", "latest news",
            "politics", "economy", "sports", "culture", "world",
            "exclusive", "live", "video", "podcast", "haberler",
            "gundem", "son dakika", "yazarlar",
        ],
        "paths": ["/politics", "/economy", "/sports", "/opinion", "/world", "/gundem", "/yazarlar"],
        "meta_patterns": [r"news", r"haber", r"gazete", r"journal", r"media"],
    },
    "corporate": {
        "keywords": [
            "about us", "our team", "leadership", "careers", "jobs",
            "investors", "annual report", "sustainability", "csr",
            "press", "media kit", "partners", "case studies",
            "our story", "mission", "values", "hakkimizda",
            "services", "solutions", "industries", "consulting",
        ],
        "paths": ["/careers", "/investors", "/press", "/team", "/case-studies", "/services"],
        "meta_patterns": [r"corporate", r"company", r"consulting", r"enterprise", r"firm"],
    },
    "restaurant": {
        "keywords": [
            "menu", "reservation", "book a table", "order online",
            "delivery", "takeout", "dine in", "chef", "cuisine",
            "breakfast", "lunch", "dinner", "appetizer", "dessert",
            "wine list", "happy hour", "catering", "restoran",
            "rezervasyon", "siparis", "yemek", "mutfak",
        ],
        "paths": ["/menu", "/reservations", "/order", "/catering", "/locations"],
        "meta_patterns": [r"restaurant", r"restoran", r"cafe", r"bistro", r"dining", r"food"],
    },
    "education": {
        "keywords": [
            "courses", "programs", "admissions", "apply", "enrollment",
            "faculty", "campus", "student", "academic", "degree",
            "certificate", "curriculum", "syllabus", "tuition",
            "scholarship", "alumni", "research", "library",
            "egitim", "ders", "basvuru", "ogrenci",
        ],
        "paths": ["/admissions", "/programs", "/courses", "/faculty", "/campus", "/library", "/research"],
        "meta_patterns": [r"university", r"college", r"school", r"academy", r"educa", r"learn"],
    },
    "healthcare": {
        "keywords": [
            "doctor", "physician", "appointment", "patient", "health",
            "clinic", "hospital", "medical", "treatment", "specialist",
            "insurance", "emergency", "pharmacy", "lab results",
            "doktor", "randevu", "hasta", "klinik", "hastane",
            "tedavi", "saglik",
        ],
        "paths": ["/doctors", "/appointments", "/patients", "/services", "/departments", "/find-a-doctor"],
        "meta_patterns": [r"health", r"hospital", r"clinic", r"medical", r"saglik", r"hastane"],
    },
    "nonprofit": {
        "keywords": [
            "donate", "volunteer", "mission", "impact", "cause",
            "charity", "foundation", "grant", "fundraise", "campaign",
            "community", "support", "give", "help", "awareness",
            "bagis", "gonullu", "vakif", "dernek",
        ],
        "paths": ["/donate", "/volunteer", "/impact", "/programs", "/about-us", "/get-involved"],
        "meta_patterns": [r"nonprofit", r"charity", r"foundation", r"vakif", r"dernek", r"ngo"],
    },
    "portfolio": {
        "keywords": [
            "portfolio", "projects", "work", "case study", "clients",
            "hire me", "freelance", "resume", "cv", "skills",
            "experience", "testimonials", "photography", "design",
        ],
        "paths": ["/portfolio", "/projects", "/work", "/resume", "/contact"],
        "meta_patterns": [r"portfolio", r"freelanc", r"designer", r"developer", r"photograph"],
    },
    "government": {
        "keywords": [
            "citizen", "services", "department", "regulation", "form",
            "permit", "license", "public", "municipal", "council",
            "transparency", "procurement", "tender", "belediye",
            "vatandas", "hizmet", "ihale", "meclis",
        ],
        "paths": ["/services", "/departments", "/forms", "/council", "/transparency", "/tenders"],
        "meta_patterns": [r"gov", r"government", r"municipal", r"belediye", r"public\s+service"],
    },
}

def detect_site_type(homepage_html: str | None, nav_links: list[dict],
                     pages_found: list[dict], domain: str) -> tuple[str, dict]:
    """Detect site type based on homepage content, nav links, and found pages.
    Returns (type_name, confidence_scores)."""
    scores: dict[str, float] = {t: 0.0 for t in SITE_TYPE_SIGNALS}

    all_text = ""
    link_texts = []

    if homepage_html:
        all_text = homepage_html.lower()
        link_texts = extract_all_link_texts(homepage_html)

    # Score from link texts
    nav_texts = [l["title"].lower() for l in nav_links]
    all_link_texts = link_texts + nav_texts

    for site_type, signals in SITE_TYPE_SIGNALS.items():
        # Keyword matches in link texts
        for kw in signals["keywords"]:
            for lt in all_link_texts:
                if kw in lt:
                    scores[site_type] += 1.0
                    break  # count each keyword once

        # Keyword matches in full page text
        for kw in signals["keywords"]:
            if kw in all_text:
                scores[site_type] += 0.3

        # Meta pattern matches
        for pattern in signals["meta_patterns"]:
            if re.search(pattern, all_text, re.I):
                scores[site_type] += 2.0

        # Domain-based hints
        for pattern in signals["meta_patterns"]:
            if re.search(pattern, domain, re.I):
                scores[site_type] += 3.0

        # Found pages matching type-specific paths
        found_paths = {p["path"] for p in pages_found}
        for path in signals["paths"]:
            if path in found_paths:
                scores[site_type] += 2.0

    # Normalize and pick winner
    max_score = max(scores.values()) if scores else 0
    if max_score < 3.0:
        return "generic", scores

    winner = max(scores, key=scores.get)
    return winner, scores


# —— Site Type Specific Probe Paths ————————————————————————————————

COMMON_PROBE_PATHS = [
    # Universal pages
    ("/help", "Help Center"),
    ("/yardim", "Yardim"),
    ("/contact", "Contact"),
    ("/iletisim", "Iletisim"),
    ("/about", "About"),
    ("/hakkimizda", "Hakkimizda"),
    ("/about-us", "About Us"),
    ("/privacy", "Privacy Policy"),
    ("/terms", "Terms"),
    ("/kvkk", "KVKK"),
    ("/gizlilik", "Gizlilik"),
    ("/blog", "Blog"),
    ("/faq", "FAQ"),
    ("/llms.txt", "llms.txt"),
]

TYPE_PROBE_PATHS = {
    "ecommerce": [
        ("/shipping", "Shipping"),
        ("/kargo", "Kargo"),
        ("/delivery", "Delivery"),
        ("/teslimat", "Teslimat"),
        ("/returns", "Returns"),
        ("/iade", "Iade"),
        ("/refund", "Refund"),
        ("/return-policy", "Return Policy"),
        ("/stores", "Stores"),
        ("/magazalar", "Magazalar"),
        ("/store-locator", "Store Locator"),
        ("/locations", "Locations"),
        ("/brands", "Brands"),
        ("/campaigns", "Campaigns"),
        ("/deals", "Deals"),
        ("/content/kampanyalar", "Campaigns"),
        ("/content/kesfet", "Discover"),
        ("/mag", "Magazine"),
        ("/magazine", "Magazine"),
        ("/gift-cards", "Gift Cards"),
        ("/loyalty", "Loyalty Program"),
        ("/size-guide", "Size Guide"),
    ],
    "saas": [
        ("/pricing", "Pricing"),
        ("/docs", "Documentation"),
        ("/documentation", "Documentation"),
        ("/api", "API Reference"),
        ("/api-reference", "API Reference"),
        ("/developer", "Developers"),
        ("/developers", "Developers"),
        ("/sdk", "SDK"),
        ("/integrations", "Integrations"),
        ("/changelog", "Changelog"),
        ("/release-notes", "Release Notes"),
        ("/status", "Status Page"),
        ("/security", "Security"),
        ("/compliance", "Compliance"),
        ("/guides", "Guides"),
        ("/tutorials", "Tutorials"),
        ("/examples", "Examples"),
        ("/community", "Community"),
        ("/support", "Support"),
        ("/enterprise", "Enterprise"),
        ("/solutions", "Solutions"),
        ("/features", "Features"),
        ("/customers", "Customers"),
        ("/case-studies", "Case Studies"),
        ("/partners", "Partners"),
        ("/marketplace", "Marketplace"),
        ("/open-source", "Open Source"),
    ],
    "news": [
        ("/politics", "Politics"),
        ("/economy", "Economy"),
        ("/world", "World"),
        ("/sports", "Sports"),
        ("/culture", "Culture"),
        ("/technology", "Technology"),
        ("/science", "Science"),
        ("/health", "Health"),
        ("/opinion", "Opinion"),
        ("/editorial", "Editorial"),
        ("/columnists", "Columnists"),
        ("/yazarlar", "Yazarlar"),
        ("/gundem", "Gundem"),
        ("/podcast", "Podcast"),
        ("/video", "Video"),
        ("/newsletter", "Newsletter"),
        ("/subscribe", "Subscribe"),
        ("/archive", "Archive"),
        ("/photo-gallery", "Photo Gallery"),
        ("/live", "Live"),
    ],
    "corporate": [
        ("/services", "Services"),
        ("/solutions", "Solutions"),
        ("/industries", "Industries"),
        ("/careers", "Careers"),
        ("/jobs", "Jobs"),
        ("/team", "Team"),
        ("/leadership", "Leadership"),
        ("/investors", "Investors"),
        ("/investor-relations", "Investor Relations"),
        ("/press", "Press"),
        ("/media", "Media"),
        ("/news", "News"),
        ("/case-studies", "Case Studies"),
        ("/partners", "Partners"),
        ("/sustainability", "Sustainability"),
        ("/annual-report", "Annual Report"),
        ("/csr", "CSR"),
        ("/locations", "Locations"),
        ("/offices", "Offices"),
    ],
    "restaurant": [
        ("/menu", "Menu"),
        ("/our-menu", "Our Menu"),
        ("/reservations", "Reservations"),
        ("/book", "Book a Table"),
        ("/order", "Order Online"),
        ("/order-online", "Order Online"),
        ("/delivery", "Delivery"),
        ("/catering", "Catering"),
        ("/events", "Events"),
        ("/private-dining", "Private Dining"),
        ("/locations", "Locations"),
        ("/gallery", "Gallery"),
        ("/chef", "Our Chef"),
        ("/story", "Our Story"),
        ("/wine", "Wine List"),
        ("/happy-hour", "Happy Hour"),
        ("/gift-cards", "Gift Cards"),
    ],
    "education": [
        ("/admissions", "Admissions"),
        ("/apply", "Apply"),
        ("/programs", "Programs"),
        ("/courses", "Courses"),
        ("/departments", "Departments"),
        ("/faculty", "Faculty"),
        ("/research", "Research"),
        ("/campus", "Campus"),
        ("/campus-life", "Campus Life"),
        ("/library", "Library"),
        ("/tuition", "Tuition & Fees"),
        ("/financial-aid", "Financial Aid"),
        ("/scholarships", "Scholarships"),
        ("/alumni", "Alumni"),
        ("/student-life", "Student Life"),
        ("/events", "Events"),
        ("/news", "News"),
        ("/athletics", "Athletics"),
        ("/calendar", "Academic Calendar"),
    ],
    "healthcare": [
        ("/doctors", "Doctors"),
        ("/find-a-doctor", "Find a Doctor"),
        ("/physicians", "Physicians"),
        ("/appointments", "Appointments"),
        ("/patients", "For Patients"),
        ("/visitors", "For Visitors"),
        ("/services", "Services"),
        ("/departments", "Departments"),
        ("/specialties", "Specialties"),
        ("/conditions", "Conditions"),
        ("/treatments", "Treatments"),
        ("/emergency", "Emergency"),
        ("/pharmacy", "Pharmacy"),
        ("/insurance", "Insurance"),
        ("/patient-portal", "Patient Portal"),
        ("/locations", "Locations"),
        ("/careers", "Careers"),
        ("/research", "Research"),
        ("/health-library", "Health Library"),
    ],
    "nonprofit": [
        ("/donate", "Donate"),
        ("/give", "Give"),
        ("/volunteer", "Volunteer"),
        ("/get-involved", "Get Involved"),
        ("/programs", "Programs"),
        ("/impact", "Our Impact"),
        ("/stories", "Stories"),
        ("/mission", "Our Mission"),
        ("/events", "Events"),
        ("/news", "News"),
        ("/press", "Press"),
        ("/annual-report", "Annual Report"),
        ("/financials", "Financials"),
        ("/partners", "Partners"),
        ("/corporate-partnerships", "Corporate Partnerships"),
        ("/advocacy", "Advocacy"),
        ("/resources", "Resources"),
        ("/careers", "Careers"),
    ],
    "portfolio": [
        ("/portfolio", "Portfolio"),
        ("/projects", "Projects"),
        ("/work", "Work"),
        ("/case-studies", "Case Studies"),
        ("/clients", "Clients"),
        ("/services", "Services"),
        ("/resume", "Resume"),
        ("/cv", "CV"),
        ("/testimonials", "Testimonials"),
        ("/photography", "Photography"),
        ("/gallery", "Gallery"),
        ("/design", "Design"),
        ("/writing", "Writing"),
        ("/talks", "Talks"),
        ("/colophon", "Colophon"),
        ("/uses", "Uses"),
        ("/now", "Now"),
    ],
    "government": [
        ("/services", "Services"),
        ("/departments", "Departments"),
        ("/forms", "Forms"),
        ("/permits", "Permits"),
        ("/licenses", "Licenses"),
        ("/council", "Council"),
        ("/meetings", "Meetings"),
        ("/transparency", "Transparency"),
        ("/budget", "Budget"),
        ("/tenders", "Tenders"),
        ("/procurement", "Procurement"),
        ("/news", "News"),
        ("/announcements", "Announcements"),
        ("/events", "Events"),
        ("/emergency", "Emergency"),
        ("/directory", "Directory"),
        ("/maps", "Maps"),
        ("/public-records", "Public Records"),
        ("/careers", "Careers"),
    ],
    "generic": [],
}

# —— Site Discovery ————————————————————————————————————————————————

def discover_site(base_url: str, out_dir: str) -> dict:
    """Probe the site, detect type, and collect structured discovery data."""
    print(f"\n🔍 Discovering: {base_url}\n")
    discovery = {
        "base_url": base_url,
        "domain": urlparse(base_url).netloc,
        "site_type": "generic",
        "type_scores": {},
        "homepage": {},
        "pages_found": [],
        "pages_not_found": [],
        "nav_links": [],
        "llms_txt": None,
    }

    # 1. Fetch homepage
    print("📄 Fetching homepage...")
    homepage_html = fetch(base_url)
    if homepage_html:
        discovery["homepage"] = {
            "title": extract_title(homepage_html),
            "description": extract_meta_description(homepage_html),
            "keywords": extract_meta_keywords(homepage_html),
        }
        discovery["nav_links"] = extract_nav_links(homepage_html, base_url)
        print(f"   ✅ Title: {discovery['homepage']['title']}")
        print(f"   ✅ Nav links found: {len(discovery['nav_links'])}")
    else:
        print("   ❌ Homepage not accessible (Cloudflare or blocked)")

    # 2. Probe common paths first (needed for type detection)
    print("\n🔎 Probing common pages...\n")
    for path, label in COMMON_PROBE_PATHS:
        url = base_url + path
        content = fetch(url)
        if content:
            title = extract_title(content)
            desc = extract_meta_description(content)
            page_info = {
                "path": path, "url": url, "label": label,
                "title": title, "description": desc,
            }
            if path == "/llms.txt":
                if not content.strip().startswith("<"):
                    discovery["llms_txt"] = {
                        "url": url,
                        "size_chars": len(content),
                        "size_kb": round(len(content) / 1024, 1),
                    }
                    raw_path = os.path.join(out_dir, "raw_llms.txt")
                    with open(raw_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"   ✅ {label:<20} → {title or path} ({discovery['llms_txt']['size_kb']} KB)")
                    print(f"      Saved raw to: {raw_path}")
                else:
                    print(f"   ⚠️  {label:<20} → exists but returned HTML (Cloudflare?)")
                continue
            discovery["pages_found"].append(page_info)
            print(f"   ✅ {label:<20} → {title or path}")
        else:
            discovery["pages_not_found"].append({"path": path, "label": label})

    # 3. Detect site type
    site_type, scores = detect_site_type(
        homepage_html, discovery["nav_links"],
        discovery["pages_found"], discovery["domain"]
    )
    discovery["site_type"] = site_type
    discovery["type_scores"] = {k: round(v, 1) for k, v in sorted(scores.items(), key=lambda x: -x[1]) if v > 0}

    print(f"\n🏷️  Detected site type: {site_type.upper()}")
    if discovery["type_scores"]:
        top3 = list(discovery["type_scores"].items())[:3]
        print(f"   Scores: {', '.join(f'{t}={s}' for t, s in top3)}")

    # 4. Probe type-specific paths
    type_paths = TYPE_PROBE_PATHS.get(site_type, [])
    if type_paths:
        print(f"\n🔎 Probing {site_type}-specific pages...\n")
        already_probed = {p for p, _ in COMMON_PROBE_PATHS}
        for path, label in type_paths:
            if path in already_probed:
                continue
            url = base_url + path
            content = fetch(url)
            if content:
                title = extract_title(content)
                desc = extract_meta_description(content)
                discovery["pages_found"].append({
                    "path": path, "url": url, "label": label,
                    "title": title, "description": desc,
                })
                print(f"   ✅ {label:<20} → {title or path}")
            else:
                discovery["pages_not_found"].append({"path": path, "label": label})

    # 5. Save discovery data
    os.makedirs(out_dir, exist_ok=True)
    discovery_path = os.path.join(out_dir, "discovery.json")
    with open(discovery_path, "w", encoding="utf-8") as f:
        json.dump(discovery, f, indent=2, ensure_ascii=False)

    # 6. Print summary
    print(f"\n{'='*60}")
    print(f"📊 Discovery Summary for {discovery['domain']}")
    print(f"{'='*60}")
    print(f"   Site type      : {site_type}")
    print(f"   Pages found    : {len(discovery['pages_found'])}")
    print(f"   Pages missing  : {len(discovery['pages_not_found'])}")
    print(f"   Nav links      : {len(discovery['nav_links'])}")
    print(f"   Existing llms  : {'Yes' if discovery['llms_txt'] else 'No'}")
    print(f"\n   Discovery saved to: {discovery_path}")

    if discovery["pages_found"]:
        print(f"\n   Found pages:")
        for p in discovery["pages_found"]:
            print(f"     • {p['label']}: {p['url']}")

    print(f"\n{'='*60}")
    return discovery

# —— Format Detection ——————————————————————————————————————————————

def detect_format(text: str) -> str:
    has_spec_links = bool(re.search(r"^- \[.+\]\(.+\)", text, re.MULTILINE))
    has_flat_entries = bool(re.search(r"^URL:\s*https?://", text, re.MULTILINE))
    if has_spec_links and not has_flat_entries:
        return "spec"
    elif has_flat_entries and not has_spec_links:
        return "flat"
    elif has_flat_entries and has_spec_links:
        return "mixed"
    else:
        return "spec"

# —— Parsers ———————————————————————————————————————————————————————

def parse_spec_format(text: str) -> dict:
    result = {"title": "", "summary": "", "info": "", "sections": {}}
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("# ") and not line.startswith("## "):
            result["title"] = line[2:].strip()
            i += 1
            break
        i += 1

    summary_lines = []
    info_lines = []
    current_section = None
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = stripped[3:].strip()
            if current_section not in result["sections"]:
                result["sections"][current_section] = []
            i += 1
            continue
        if current_section is not None:
            if stripped.startswith("- ["):
                m = re.match(r"-\s*\[([^\]]+)\]\(([^\)]+)\)(?::\s*(.*))?", stripped)
                if m:
                    result["sections"][current_section].append({
                        "title": m.group(1),
                        "url": m.group(2),
                        "desc": (m.group(3) or "").strip()
                    })
            elif stripped.startswith("- "):
                result["sections"][current_section].append({
                    "title": stripped[2:], "url": "", "desc": ""
                })
            elif stripped:
                if result["sections"][current_section]:
                    last = result["sections"][current_section][-1]
                    last["desc"] = (last["desc"] + " " + stripped).strip()
        else:
            if stripped.startswith(">"):
                summary_lines.append(stripped.lstrip("> ").strip())
            elif stripped and not stripped.startswith("#"):
                info_lines.append(stripped)
        i += 1
    result["summary"] = " ".join(summary_lines).strip()
    result["info"] = "\n".join(info_lines).strip()
    return result


def parse_flat_format(text: str) -> dict:
    result = {"title": "", "summary": "", "info": "", "sections": {"Links": []}}
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("# ") and not line.startswith("## "):
            result["title"] = line[2:].strip()
            i += 1
            break
        i += 1

    summary_lines = []
    info_lines = []
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("URL:"):
            break
        if stripped.startswith(">"):
            summary_lines.append(stripped.lstrip("> ").strip())
        elif stripped:
            info_lines.append(stripped)
        i += 1

    result["summary"] = " ".join(summary_lines).strip()
    if not result["summary"] and info_lines:
        first = info_lines[0]
        dot_pos = first.find(". ")
        if 0 < dot_pos < 200:
            result["summary"] = first[:dot_pos + 1]
        else:
            result["summary"] = first[:200] + ("..." if len(first) > 200 else "")
        result["info"] = "\n".join(info_lines[1:]).strip()
    else:
        result["info"] = "\n".join(info_lines).strip()

    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("URL:"):
            url = stripped[4:].strip()
            title = ""
            desc = ""
            j = i + 1
            while j < len(lines) and j <= i + 4:
                next_line = lines[j].strip()
                if next_line.startswith("TITLE:"):
                    title = next_line[6:].strip()
                elif next_line.startswith("DESCRIPTION:"):
                    desc = next_line[12:].strip()
                elif next_line.startswith("URL:"):
                    break
                j += 1
            if url:
                result["sections"]["Links"].append({
                    "title": title or url, "url": url, "desc": desc
                })
            i = j
            continue
        i += 1
    return result


def parse_llms_txt(text: str) -> dict:
    fmt = detect_format(text)
    print(f"   Format : {fmt}")
    if fmt == "flat":
        return parse_flat_format(text)
    elif fmt == "mixed":
        result = parse_spec_format(text)
        flat_result = parse_flat_format(text)
        for section, items in flat_result["sections"].items():
            if section not in result["sections"]:
                result["sections"][section] = items
            else:
                existing_urls = {item["url"] for item in result["sections"][section]}
                for item in items:
                    if item["url"] not in existing_urls:
                        result["sections"][section].append(item)
        return result
    else:
        return parse_spec_format(text)

# —— Output Generators ———————————————————————————————————————————————

def generate_llms_txt(parsed: dict, base_url: str) -> str:
    lines = []
    lines.append(f"# {parsed['title']}")
    lines.append("")
    if parsed["summary"]:
        lines.append(f"> {parsed['summary']}")
        lines.append("")
    if parsed["info"]:
        lines.append(parsed["info"])
        lines.append("")
    for section, items in parsed["sections"].items():
        lines.append(f"## {section}")
        for item in items:
            if item["url"]:
                if item["desc"]:
                    lines.append(f"- [{item['title']}]({item['url']}): {item['desc']}")
                else:
                    lines.append(f"- [{item['title']}]({item['url']})")
            elif item["title"]:
                lines.append(f"- {item['title']}")
        lines.append("")
    return "\n".join(lines).strip()

def generate_llms_full_txt(parsed: dict, base_url: str) -> str:
    lines = []
    lines.append(f"# {parsed['title']}")
    lines.append("")
    if parsed["summary"]:
        lines.append(f"> {parsed['summary']}")
        lines.append("")
    if parsed["info"]:
        lines.append(parsed["info"])
        lines.append("")
    for section, items in parsed["sections"].items():
        lines.append(f"## {section}")
        lines.append("")
        for item in items:
            if item["url"]:
                url = item["url"]
                if not url.startswith("http"):
                    url = urljoin(base_url, url)
                if item["desc"]:
                    lines.append(f"- [{item['title']}]({url}): {item['desc']}")
                else:
                    lines.append(f"- [{item['title']}]({url})")
                print(f"  ⏳ Fetching: {url}")
                content = fetch_as_markdown(url)
                if content:
                    lines.append("")
                    lines.append(f"### {item['title']}")
                    lines.append("")
                    lines.append(content[:3000])
                    if len(content) > 3000:
                        lines.append("\n[... content truncated ...]")
                    lines.append("")
            elif item["title"]:
                lines.append(f"- {item['title']}")
        lines.append("")
    return "\n".join(lines).strip()

def generate_llms_ctx_txt(parsed: dict, base_url: str, include_optional: bool = False) -> str:
    lines = ["<documents>"]
    lines.append("<document>")
    lines.append("<title>Site Overview</title>")
    lines.append("<content>")
    lines.append(f"# {parsed['title']}")
    if parsed["summary"]:
        lines.append(f"\n{parsed['summary']}")
    if parsed["info"]:
        lines.append(f"\n{parsed['info']}")
    lines.append("</content>")
    lines.append("</document>")
    for section, items in parsed["sections"].items():
        if section.lower() == "optional" and not include_optional:
            continue
        for item in items:
            if not item["url"]:
                continue
            url = item["url"]
            if not url.startswith("http"):
                url = urljoin(base_url, url)
            print(f"  ⏳ Fetching: {url}")
            content = fetch_as_markdown(url)
            lines.append("<document>")
            lines.append(f"<title>{item['title']}</title>")
            lines.append(f"<url>{url}</url>")
            lines.append(f"<section>{section}</section>")
            if item["desc"]:
                lines.append(f"<description>{item['desc']}</description>")
            lines.append("<content>")
            if content:
                lines.append(content[:4000])
                if len(content) > 4000:
                    lines.append("\n[... content truncated ...]")
            else:
                lines.append("[Content not available]")
            lines.append("</content>")
            lines.append("</document>")
    lines.append("</documents>")
    return "\n".join(lines)

# —— Multi-select Menu ———————————————————————————————————————————————

OPTIONS = [
    ("llms.txt",          "Reformat llms.txt to spec-compliant format"),
    ("llms-full.txt",     "Embed fetched content for each link"),
    ("llms-ctx.txt",      "XML context file (excluding Optional)"),
    ("llms-ctx-full.txt", "XML context file (including Optional)"),
]

def multi_select_menu() -> list[str]:
    print("\n┌─ Which formats to generate? ───────────────────────────────┐")
    for i, (name, desc) in enumerate(OPTIONS, 1):
        print(f"│  [{i}] {name:<20} {desc}")
    print("└────────────────────────────────────────────────────────────┘")
    print("  Separate multiple with commas (e.g. 1,3)")
    print("  For all: all")
    raw = input("\n> ").strip().lower()
    if raw == "all":
        return [name for name, _ in OPTIONS]
    selected = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(OPTIONS):
                selected.append(OPTIONS[idx][0])
    return selected

# —— Main ————————————————————————————————————————————————————————————

def main():
    print("┌────────────────────────────────────────┐")
    print("│      llms.txt Pipeline v4.0            │")
    print("│   Multi-type site support              │")
    print("└────────────────────────────────────────┘\n")

    if len(sys.argv) > 1 and sys.argv[1] == "discover":
        if len(sys.argv) < 3:
            url = input("Site URL (e.g. example.com): ").strip()
        else:
            url = sys.argv[2]
        url = normalize_url(url)
        domain = urlparse(url).netloc
        out_dir = f"output_{domain}"
        os.makedirs(out_dir, exist_ok=True)
        discover_site(url, out_dir)
        return

    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Site URL (e.g. example.com): ").strip()

    url = normalize_url(url)
    domain = urlparse(url).netloc
    llms_url = url + "/llms.txt"

    print(f"\n🔍 Looking for {llms_url}...")
    raw = fetch(llms_url)

    if not raw:
        print("❌ llms.txt not found. Try 'discover' mode instead:")
        print(f"   python3 {sys.argv[0]} discover {url}")
        sys.exit(1)

    print(f"✅ llms.txt found ({len(raw)} chars)\n")
    parsed = parse_llms_txt(raw)
    print(f"   Title   : {parsed['title']}")
    summary_display = parsed['summary'][:80] + "..." if len(parsed['summary']) > 80 else parsed['summary']
    print(f"   Summary : {summary_display}")
    sections = list(parsed['sections'].keys())
    print(f"   Sections: {len(sections)}")
    for s in sections:
        print(f"     - {s} ({len(parsed['sections'][s])} links)")

    selected = multi_select_menu()

    if not selected:
        print("\n⚠️  No format selected.")
        sys.exit(0)

    out_dir = f"output_{domain}"
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n⚙️  Generating: {', '.join(selected)}\n")

    for fmt in selected:
        out_path = os.path.join(out_dir, fmt)
        print(f"📄 Generating {fmt}...")
        if fmt == "llms.txt":
            content = generate_llms_txt(parsed, url)
        elif fmt == "llms-full.txt":
            content = generate_llms_full_txt(parsed, url)
        elif fmt == "llms-ctx.txt":
            content = generate_llms_ctx_txt(parsed, url, include_optional=False)
        elif fmt == "llms-ctx-full.txt":
            content = generate_llms_ctx_txt(parsed, url, include_optional=True)
        else:
            continue
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        size_kb = len(content.encode()) / 1024
        print(f"   ✅ Saved → {out_path} ({size_kb:.1f} KB)")

    print(f"\n🎉 Done! Files: ./{out_dir}/")

if __name__ == "__main__":
    main()
