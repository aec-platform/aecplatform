"""Generate the aecplatform.vn static site from ``registry/products.json``.

Standard library only, matching the tools the site is about. One command:

    python -m build.site

writes ``site/`` — an English tree at the root, a Vietnamese tree under
``/vi/``, a product page per product in each, plus ``CNAME``, ``robots.txt``,
``sitemap.xml`` and a public copy of the registry at ``/products.json``.

Nothing here knows a product name. If a fact appears on the site it came from
the registry, which means the site cannot drift from the catalogue.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from html import escape
from pathlib import Path

from . import i18n
from .i18n import LANGS, PREFIX, STATUS, t

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry" / "products.json"
OUT = ROOT / "site"

# Tiers of the stack diagram, bottom to top. Lines not listed (research) are
# catalogued but not drawn — a dataset is not a layer of the runtime stack.
STACK_TIERS = ("foundation", "open", "products")


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Registry:
    org: dict
    lines: list[dict]
    products: list[dict]

    @classmethod
    def load(cls, path: Path = REGISTRY) -> "Registry":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(org=data["org"], lines=data["lines"], products=data["products"])

    def by_line(self, line_id: str) -> list[dict]:
        return [p for p in self.products if p["line"] == line_id]

    def by_slug(self, slug: str) -> dict | None:
        return next((p for p in self.products if p["slug"] == slug), None)

    def dependents_of(self, slug: str) -> list[dict]:
        """Products that declare ``slug`` in ``depends_on`` — the reverse edge."""
        return [p for p in self.products if slug in p.get("depends_on", [])]

    def validate(self) -> list[str]:
        """Every consistency rule the site relies on, checked in one place."""
        problems: list[str] = []
        line_ids = {line["id"] for line in self.lines}
        seen: set[str] = set()

        for product in self.products:
            slug = product.get("slug", "<missing slug>")
            if slug in seen:
                problems.append(f"{slug}: duplicate slug")
            seen.add(slug)

            if product.get("line") not in line_ids:
                problems.append(f"{slug}: unknown line {product.get('line')!r}")
            if product.get("status") not in STATUS:
                problems.append(f"{slug}: unknown status {product.get('status')!r}")

            for field in ("tagline", "description"):
                for lang in LANGS:
                    if not product.get(field, {}).get(lang):
                        problems.append(f"{slug}: {field} missing {lang}")
            for lang in LANGS:
                if not product.get("highlights", {}).get(lang):
                    problems.append(f"{slug}: highlights missing {lang}")

            for dep in product.get("depends_on", []):
                if self.by_slug(dep) is None:
                    problems.append(f"{slug}: depends_on unknown product {dep!r}")

        for lang in LANGS:
            if not self.org["tagline"].get(lang):
                problems.append(f"org.tagline missing {lang}")
            if not self.org["thesis"].get(lang):
                problems.append(f"org.thesis missing {lang}")

        problems.extend(f"i18n gap: {gap}" for gap in i18n.check())
        return problems


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------


def rel(lang: str, path: str = "") -> str:
    """A site-absolute URL for ``path`` inside ``lang``'s tree."""
    return "/" + PREFIX[lang] + path.lstrip("/")


def other_lang(lang: str) -> str:
    return "vi" if lang == "en" else "en"


def product_url(lang: str, slug: str) -> str:
    return rel(lang, f"products/{slug}.html")


def _e(value: str) -> str:
    return escape(str(value), quote=True)


def install_command(product: dict) -> tuple[str, bool] | None:
    """How a reader can actually install this today, and whether it is on an index.

    Derived rather than stored: a hand-written ``pip install foo`` line survives
    long after ``foo`` turns out not to be on PyPI, and the site would keep
    advertising it. Returns ``None`` when there is nothing honest to offer.
    """
    package = product.get("package")
    if not package or not product["public"]:
        return None
    if package["published"]:
        return f"pip install {package['name']}", True
    return f"pip install git+{product['repo']}.git", False


# --------------------------------------------------------------------------
# stack diagram
# --------------------------------------------------------------------------


def stack_svg(reg: Registry, lang: str) -> str:
    """Draw the dependency stack, laid out from the registry's own edges.

    Boxes are sized to their label and wrapped into rows; arrows are drawn from
    each product that declares a dependency to the product it depends on. A
    same-tier edge arcs; a cross-tier edge is a straight drop.
    """
    box_h, row_gap, tier_gap, pad, width = 34, 12, 58, 20, 960
    char_w, label_pad = 7.4, 26

    # Lay out each tier as one or more centred rows of pills.
    tiers: list[list[list[dict]]] = []  # tier -> rows -> boxes
    for line_id in STACK_TIERS:
        members = reg.by_line(line_id)
        rows: list[list[dict]] = [[]]
        used = 0.0
        for product in members:
            w = len(product["name"]) * char_w + label_pad
            if used + w + row_gap > width - 2 * pad and rows[-1]:
                rows.append([])
                used = 0.0
            rows[-1].append({"p": product, "w": w})
            used += w + row_gap
        tiers.append(rows)

    # Assign coordinates bottom-up so the foundation sits at the bottom.
    placed: dict[str, tuple[float, float, float]] = {}  # slug -> (x, y, w)
    tier_labels: list[tuple[float, str]] = []
    y = 0.0
    heights = []
    for rows in tiers:
        heights.append(len(rows) * box_h + (len(rows) - 1) * row_gap)
    total = sum(heights) + tier_gap * (len(tiers) - 1) + 2 * pad

    y = total - pad
    for tier_index, rows in enumerate(tiers):
        y -= heights[tier_index]
        tier_labels.append((y - 10, STACK_TIERS[tier_index]))
        row_y = y
        for row in rows:
            row_w = sum(b["w"] for b in row) + row_gap * (len(row) - 1)
            x = (width - row_w) / 2
            for box in row:
                placed[box["p"]["slug"]] = (x, row_y, box["w"])
                x += box["w"] + row_gap
            row_y += box_h + row_gap
        y -= tier_gap

    parts: list[str] = [
        f'<svg class="stack" viewBox="0 0 {width} {total:.0f}" role="img" '
        f'aria-label="{_e(t("stack_heading", lang))}" xmlns="http://www.w3.org/2000/svg">',
        '<defs><marker id="ar" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" '
        'markerHeight="7" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="currentColor"/>'
        "</marker></defs>",
    ]

    # Tier captions, drawn behind the boxes.
    for label_y, line_id in tier_labels:
        line = next(item for item in reg.lines if item["id"] == line_id)
        parts.append(
            f'<text class="stack-tier" x="{pad}" y="{label_y:.0f}">'
            f'{_e(line["name"][lang]).upper()}</text>'
        )

    # Edges first, so pills paint over the arrow tails.
    for product in reg.products:
        if product["slug"] not in placed:
            continue
        for dep in product.get("depends_on", []):
            if dep not in placed:
                continue
            fx, fy, fw = placed[product["slug"]]
            tx, ty, tw = placed[dep]
            x1, x2 = fx + fw / 2, tx + tw / 2
            if abs(fy - ty) < 1:  # same tier — arc beneath the row
                mid = (x1 + x2) / 2
                parts.append(
                    f'<path class="stack-edge" d="M{x1:.0f} {fy + box_h:.0f} '
                    f"Q{mid:.0f} {fy + box_h + 26:.0f} {x2:.0f} {ty + box_h:.0f}\" "
                    'marker-end="url(#ar)"/>'
                )
            else:
                parts.append(
                    f'<path class="stack-edge" d="M{x1:.0f} {fy + box_h:.0f} '
                    f'L{x2:.0f} {ty - 4:.0f}" marker-end="url(#ar)"/>'
                )

    for slug, (x, y_, w) in placed.items():
        product = reg.by_slug(slug)
        assert product is not None
        cls = "stack-box" + ("" if product["public"] else " is-private")
        parts.append(
            f'<a href="{product_url(lang, slug)}">'
            f'<rect class="{cls}" x="{x:.0f}" y="{y_:.0f}" width="{w:.0f}" '
            f'height="{box_h}" rx="6"/>'
            f'<text class="stack-label" x="{x + w / 2:.0f}" y="{y_ + box_h / 2 + 4.5:.0f}" '
            f'text-anchor="middle">{_e(product["name"])}</text></a>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


# --------------------------------------------------------------------------
# page chrome
# --------------------------------------------------------------------------


def page(
    reg: Registry,
    lang: str,
    *,
    title: str,
    description: str,
    body: str,
    alt_url: str | None = None,
) -> str:
    """Wrap ``body`` in the shared chrome.

    ``alt_url`` is where the language switch goes. It defaults to the other
    language's home page, but a product page passes the same product in the
    other language — switching language should not lose your place.
    """
    org = reg.org
    alt = other_lang(lang)
    alt_url = alt_url or rel(alt)
    canonical = f"https://{org['domain']}"
    nav = "".join(
        f'<a href="{rel(lang, href)}">{_e(t(key, lang))}</a>'
        for key, href in (
            ("nav_products", "#products"),
            ("nav_open", "#open"),
            ("nav_thesis", "#why"),
            ("nav_contact", "#contact"),
        )
    )
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(title)}</title>
<meta name="description" content="{_e(description)}">
<meta property="og:title" content="{_e(title)}">
<meta property="og:description" content="{_e(description)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" hreflang="{alt}" href="{canonical}{alt_url}">
<link rel="alternate" hreflang="{lang}" href="{canonical}{rel(lang)}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%231D4E89'/%3E%3Cpath d='M8 23L16 9l8 14' stroke='%23fff' stroke-width='2.5' fill='none' stroke-linejoin='round'/%3E%3C/svg%3E">
<style>{CSS}</style>
</head>
<body>
<header class="top">
  <div class="wrap top-inner">
    <a class="brand" href="{rel(lang)}">
      <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="6" fill="currentColor" opacity=".12"/><path d="M8 23L16 9l8 14" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linejoin="round"/></svg>
      <span>{_e(org['name'])}</span>
    </a>
    <nav class="nav">{nav}</nav>
    <a class="nav-app" href="https://app.{org['domain']}">{_e(t("nav_app", lang))}</a>
    <a class="lang" href="{alt_url}" hreflang="{alt}">{_e(i18n.LABEL[alt])}</a>
  </div>
</header>
{body}
<footer class="foot">
  <div class="wrap foot-inner">
    <div>
      <strong>{_e(org['name'])}</strong>
      <p class="muted small">{_e(org['base'])} · {_e(t('footer_rights', lang))}</p>
    </div>
    <div class="foot-links">
      <a href="mailto:{_e(org['contact'])}">{_e(org['contact'])}</a>
      <a href="https://github.com/{_e(org['github'])}">github.com/{_e(org['github'])}</a>
      <a href="{alt_url}">{_e(i18n.LABEL[alt])}</a>
    </div>
  </div>
</footer>
</body>
</html>
"""


# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------


def product_card(product: dict, lang: str) -> str:
    meta = [_e(product["language"]), _e(STATUS[product["status"]][lang])]
    if product.get("tests"):
        meta.append(f"{product['tests']} {_e(t('product_tests', lang)).lower()}")
    badge = "" if product["public"] else '<span class="pill pill-private">·</span>'
    return f"""<a class="card" href="{product_url(lang, product['slug'])}">
  <h3>{_e(product['name'])}{badge}</h3>
  <p>{_e(product['tagline'][lang])}</p>
  <p class="meta">{' · '.join(meta)}</p>
</a>"""


def line_section(reg: Registry, line: dict, lang: str) -> str:
    products = reg.by_line(line["id"])
    if not products:
        return ""
    cards = "\n".join(product_card(p, lang) for p in products)
    return f"""<section class="section" id="{line['id']}">
  <div class="wrap">
    <h2>{_e(line['name'][lang])}</h2>
    <p class="lead">{_e(line['blurb'][lang])}</p>
    <div class="grid">{cards}</div>
  </div>
</section>"""


def home(reg: Registry, lang: str) -> str:
    org = reg.org
    open_products = [p for p in reg.products if p["line"] in ("open", "foundation")]
    numbers = [
        (len(reg.products), t("numbers_products", lang)),
        (len(open_products), t("numbers_open", lang)),
        (sum(p.get("tests", 0) for p in open_products), t("numbers_tests", lang)),
        (0, t("numbers_deps", lang)),
    ]
    number_html = "".join(
        f'<div><span class="num">{value:,}</span><span class="num-label">{_e(label)}</span></div>'
        for value, label in numbers
    )
    thesis = "".join(f"<p>{_e(par)}</p>" for par in org["thesis"][lang])
    sections = "\n".join(line_section(reg, line, lang) for line in reg.lines)

    return page(
        reg,
        lang,
        title=f"{org['name']} — {org['tagline'][lang]}",
        description=org["tagline"][lang],
        body=f"""
<section class="hero">
  <div class="wrap">
    <h1>{_e(org['tagline'][lang])}</h1>
    <p class="lead">{_e(org['thesis'][lang][0])}</p>
    <div class="cta">
      <a class="btn btn-primary" href="{rel(lang, '#open')}">{_e(t('hero_cta_primary', lang))}</a>
      <a class="btn" href="{rel(lang, '#contact')}">{_e(t('hero_cta_secondary', lang))}</a>
    </div>
  </div>
</section>

<section class="numbers"><div class="wrap numbers-inner">{number_html}</div></section>

<section class="section" id="stack">
  <div class="wrap">
    <h2>{_e(t('stack_heading', lang))}</h2>
    <p class="lead">{_e(t('stack_note', lang))}</p>
    <div class="stack-wrap">{stack_svg(reg, lang)}</div>
  </div>
</section>

{sections}

<section class="section band" id="why">
  <div class="wrap">
    <h2>{_e(t('thesis_heading', lang))}</h2>
    <div class="prose">{thesis}</div>
  </div>
</section>

<section class="section" id="contact">
  <div class="wrap">
    <h2>{_e(t('contact_heading', lang))}</h2>
    <p class="lead">{_e(t('contact_body', lang))}</p>
    <p><a class="btn btn-primary" href="mailto:{_e(org['contact'])}">{_e(org['contact'])}</a></p>
  </div>
</section>
""",
    )


def product_page(reg: Registry, product: dict, lang: str) -> str:
    org = reg.org
    facts = [
        (t("product_status", lang), STATUS[product["status"]][lang]),
        (t("product_license", lang), product["license"]),
        (t("product_language", lang), product["language"]),
    ]
    if product.get("tests"):
        facts.append((t("product_tests", lang), f"{product['tests']:,}"))
    fact_html = "".join(
        f'<div><dt>{_e(label)}</dt><dd>{_e(value)}</dd></div>' for label, value in facts
    )

    code = ""
    install = install_command(product)
    if install:
        line, on_index = install
        note = (
            ""
            if on_index
            else f'<p class="muted small">{_e(t("product_not_on_index", lang))}</p>'
        )
        code += (
            f'<h3>{_e(t("product_install", lang))}</h3>'
            f"<pre><code>{_e(line)}</code></pre>{note}"
        )
    if product.get("command"):
        code += (
            f'<h3>{_e(t("product_run", lang))}</h3>'
            f"<pre><code>{_e(product['command'])}</code></pre>"
        )

    highlights = "".join(f"<li>{_e(item)}</li>" for item in product["highlights"][lang])

    def links(slugs, label):
        items = [reg.by_slug(s) for s in slugs]
        items = [i for i in items if i]
        if not items:
            return ""
        anchors = " · ".join(
            f'<a href="{product_url(lang, i["slug"])}">{_e(i["name"])}</a>' for i in items
        )
        return f"<p class=\"related\"><span>{_e(label)}</span> {anchors}</p>"

    related = links(product.get("depends_on", []), t("product_builds_on", lang))
    related += links(
        [p["slug"] for p in reg.dependents_of(product["slug"])], t("product_used_by", lang)
    )

    if product["public"]:
        source = (
            f'<a class="btn btn-primary" href="{_e(product["repo"])}">'
            f'{_e(t("product_source", lang))} →</a>'
        )
    elif product["line"] in ("open", "foundation"):
        source = f'<p class="muted small">{_e(t("product_source_unpublished", lang))}</p>'
    else:
        source = (
            f'<p class="muted small">{_e(t("product_source_private", lang))}</p>'
            f'<a class="btn btn-primary" href="mailto:{_e(org["contact"])}">'
            f'{_e(t("hero_cta_secondary", lang))}</a>'
        )

    return page(
        reg,
        lang,
        title=f"{product['name']} — {org['name']}",
        description=product["tagline"][lang],
        alt_url=product_url(other_lang(lang), product["slug"]),
        body=f"""
<article class="section product">
  <div class="wrap">
    <p class="crumb"><a href="{rel(lang)}">← {_e(t('back_home', lang))}</a></p>
    <h1>{_e(product['name'])}</h1>
    <p class="lead">{_e(product['tagline'][lang])}</p>
    <dl class="facts">{fact_html}</dl>
    {code}
    <div class="prose"><p>{_e(product['description'][lang])}</p></div>
    <h3>{_e(t('product_highlights', lang))}</h3>
    <ul class="ticks">{highlights}</ul>
    {related}
    <p class="source">{source}</p>
  </div>
</article>
""",
    )


def not_found(reg: Registry, lang: str) -> str:
    return page(
        reg,
        lang,
        title=f"404 — {reg.org['name']}",
        description=t("not_found_body", lang),
        body=f"""
<section class="section">
  <div class="wrap">
    <h1>{_e(t('not_found_title', lang))}</h1>
    <p class="lead">{_e(t('not_found_body', lang))}</p>
    <p><a class="btn btn-primary" href="{rel(lang)}">{_e(t('back_home', lang))}</a></p>
  </div>
</section>
""",
    )


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------


def build(out: Path = OUT, registry: Path = REGISTRY) -> list[Path]:
    reg = Registry.load(registry)
    problems = reg.validate()
    if problems:
        raise SystemExit("registry is not publishable:\n  " + "\n  ".join(problems))

    if out.exists():
        shutil.rmtree(out)
    written: list[Path] = []

    def write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)

    urls: list[str] = []
    for lang in LANGS:
        base = out / PREFIX[lang]
        write(base / "index.html", home(reg, lang))
        urls.append(rel(lang))
        for product in reg.products:
            write(base / "products" / f"{product['slug']}.html", product_page(reg, product, lang))
            urls.append(product_url(lang, product["slug"]))

    # GitHub Pages serves this for any unmatched path.
    write(out / "404.html", not_found(reg, "en"))

    domain = reg.org["domain"]
    write(out / "CNAME", domain + "\n")
    write(
        out / "robots.txt",
        f"User-agent: *\nAllow: /\nSitemap: https://{domain}/sitemap.xml\n",
    )
    write(
        out / "sitemap.xml",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>https://{domain}{u}</loc></url>\n" for u in urls)
        + "</urlset>\n",
    )
    # The registry is the product catalogue; publish it so others can consume it.
    write(out / "products.json", registry.read_text(encoding="utf-8"))
    # Pages would otherwise run the output through Jekyll.
    write(out / ".nojekyll", "")

    return written


CSS = """
:root{
  --bg:#FBFAF7; --surface:#FFFFFF; --ink:#14161A; --muted:#5A6069;
  --line:#E5E3DC; --accent:#1D4E89; --mark:#B4682A; --band:#F4F2EC;
  --radius:10px;
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:#0E1116; --surface:#161A21; --ink:#E8EAED; --muted:#98A1AD;
    --line:#262C35; --accent:#7FAEE0; --mark:#DCA164; --band:#12161C;
  }
}
:root[data-theme="dark"]{
  --bg:#0E1116; --surface:#161A21; --ink:#E8EAED; --muted:#98A1AD;
  --line:#262C35; --accent:#7FAEE0; --mark:#DCA164; --band:#12161C;
}
:root[data-theme="light"]{
  --bg:#FBFAF7; --surface:#FFFFFF; --ink:#14161A; --muted:#5A6069;
  --line:#E5E3DC; --accent:#1D4E89; --mark:#B4682A; --band:#F4F2EC;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,"Helvetica Neue",Arial,sans-serif;
  font-feature-settings:"kern" 1;
}
a{color:var(--accent); text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1080px; margin:0 auto; padding:0 24px}
h1,h2,h3{letter-spacing:-.02em; line-height:1.2; margin:0 0 .5em}
h1{font-size:clamp(30px,5vw,46px); font-weight:660}
h2{font-size:clamp(22px,3vw,30px); font-weight:640; margin-bottom:.35em}
h3{font-size:17px; font-weight:640; margin-top:2rem}
p{margin:0 0 1rem}
.lead{color:var(--muted); font-size:clamp(16px,2vw,19px); max-width:62ch}
.small{font-size:14px}
.muted{color:var(--muted)}

/* The only route from the marketing site into the product. It was missing
   entirely: every nav item pointed at an anchor on this page, so a visitor had
   to guess the app.* subdomain. Styled as a button rather than a fifth nav
   link, because it is the one thing here that is not reading. */
.nav-app{display:inline-flex;align-items:center;padding:.4rem .85rem;border:1px solid var(--line);
  border-radius:8px;font-size:.9rem;text-decoration:none;color:var(--ink);white-space:nowrap}
.nav-app:hover{border-color:var(--accent);color:var(--accent)}
@media (max-width:640px){.nav-app{padding:.3rem .6rem;font-size:.85rem}}
/* header */
.top{position:sticky; top:0; z-index:10; background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:saturate(1.4) blur(10px); border-bottom:1px solid var(--line)}
.top-inner{display:flex; align-items:center; gap:20px; height:60px}
.brand{display:flex; align-items:center; gap:9px; color:var(--ink); font-weight:640;
  letter-spacing:-.01em; text-decoration:none}
.brand svg{color:var(--accent)}
.nav{display:flex; gap:20px; margin-left:auto; font-size:14.5px}
.nav a{color:var(--muted)}
.nav a:hover{color:var(--ink); text-decoration:none}
.lang{font-size:13px; color:var(--muted); border:1px solid var(--line);
  padding:4px 10px; border-radius:99px; white-space:nowrap}
.lang:hover{color:var(--ink); border-color:var(--accent); text-decoration:none}
@media (max-width:720px){ .nav{display:none} }

/* hero */
.hero{position:relative; padding:88px 0 64px; border-bottom:1px solid var(--line);
  overflow:hidden}
/* The drafting grid is decoration only, so it lives on its own layer — masking
   the section itself would fade the headline with it. */
.hero::before{content:""; position:absolute; inset:0; pointer-events:none;
  background-image:linear-gradient(var(--line) 1px,transparent 1px),
                   linear-gradient(90deg,var(--line) 1px,transparent 1px);
  background-size:52px 52px; background-position:center;
  -webkit-mask-image:radial-gradient(ellipse 80% 75% at 50% 0%,#000 10%,transparent 72%);
          mask-image:radial-gradient(ellipse 80% 75% at 50% 0%,#000 10%,transparent 72%);
}
.hero .wrap{position:relative}
.hero h1{max-width:19ch}
.hero .lead{margin-top:18px}
.cta{display:flex; gap:12px; flex-wrap:wrap; margin-top:28px}
.btn{display:inline-block; padding:10px 18px; border-radius:8px; border:1px solid var(--line);
  background:var(--surface); color:var(--ink); font-size:14.5px; font-weight:560}
.btn:hover{border-color:var(--accent); text-decoration:none}
/* --bg tracks the theme, so the label stays legible on the light-blue dark-mode
   accent as well as the deep-blue light-mode one. */
.btn-primary{background:var(--accent); border-color:var(--accent); color:var(--bg)}
.btn-primary:hover{filter:brightness(1.08)}

/* numbers */
.numbers{border-bottom:1px solid var(--line); background:var(--band)}
.numbers-inner{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:24px; padding-top:28px; padding-bottom:28px}
.num{display:block; font-size:30px; font-weight:660; letter-spacing:-.03em; color:var(--mark)}
.num-label{display:block; font-size:13.5px; color:var(--muted); margin-top:2px}

/* sections */
.section{padding:64px 0; border-bottom:1px solid var(--line)}
.band{background:var(--band)}
.prose{max-width:66ch; margin-top:18px}
.prose p{margin-bottom:1.15rem}

/* cards */
.grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(272px,1fr));
  gap:14px; margin-top:26px}
.card{display:block; padding:20px; border:1px solid var(--line); border-radius:var(--radius);
  background:var(--surface); color:var(--ink); transition:border-color .15s,transform .15s}
.card:hover{border-color:var(--accent); text-decoration:none; transform:translateY(-2px)}
.card h3{margin:0 0 8px; font-size:17px}
.card p{margin:0; font-size:14.5px; color:var(--muted); line-height:1.55}
.card .meta{margin-top:12px; font-size:12.5px; color:var(--muted); opacity:.85}
.pill-private{display:inline-block; width:6px; height:6px; border-radius:99px;
  background:var(--mark); margin-left:7px; vertical-align:middle; overflow:hidden;
  text-indent:-99px}

/* stack diagram */
.stack-wrap{margin-top:28px; overflow-x:auto; border:1px solid var(--line);
  border-radius:var(--radius); background:var(--surface); padding:14px}
.stack{display:block; min-width:640px; width:100%; height:auto; color:var(--muted)}
.stack-box{fill:var(--band); stroke:var(--line)}
.stack-box.is-private{stroke-dasharray:4 3}
.stack a:hover .stack-box{stroke:var(--accent)}
.stack-label{fill:var(--ink); font-size:13px; font-weight:560;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.stack-tier{fill:var(--muted); font-size:10.5px; letter-spacing:.14em; opacity:.75}
.stack-edge{stroke:var(--mark); stroke-width:1.4; fill:none; opacity:.75}

/* product page */
.crumb{font-size:14px}
.facts{display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr));
  gap:14px; margin:26px 0 0; padding:18px 20px; border:1px solid var(--line);
  border-radius:var(--radius); background:var(--surface)}
.facts dt{font-size:12px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted)}
.facts dd{margin:3px 0 0; font-weight:560; font-size:15px}
pre{margin:10px 0 0; padding:14px 16px; overflow-x:auto; border:1px solid var(--line);
  border-radius:var(--radius); background:var(--surface)}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:13.5px}
.ticks{margin:14px 0 0; padding:0; list-style:none; max-width:70ch}
.ticks li{position:relative; padding-left:24px; margin-bottom:11px; color:var(--muted)}
.ticks li::before{content:""; position:absolute; left:4px; top:.62em; width:7px; height:7px;
  border-radius:2px; background:var(--mark)}
.related{margin-top:26px; font-size:14.5px}
.related span{color:var(--muted); margin-right:6px}
.source{margin-top:32px}

/* footer */
.foot{padding:36px 0; background:var(--band)}
.foot-inner{display:flex; flex-wrap:wrap; gap:20px; justify-content:space-between}
.foot p{margin:4px 0 0}
.foot-links{display:flex; flex-direction:column; gap:5px; font-size:14px}
"""


if __name__ == "__main__":  # pragma: no cover
    files = build()
    print(f"wrote {len(files)} files to {OUT}")
