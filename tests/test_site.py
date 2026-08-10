"""Build the whole site into a temp directory and assert on the output.

The generator has no server and no framework, so the only meaningful test is
the artefact: are the files there, do the links resolve, is every language
complete, and does the stack diagram say what the registry says.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from build.i18n import LANGS, PREFIX
from build.site import Registry, build, stack_svg


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("site")
    build(out=out)
    return out


@pytest.fixture(scope="module")
def reg() -> Registry:
    return Registry.load()


def test_every_language_gets_a_home_page(site: Path) -> None:
    for lang in LANGS:
        assert (site / PREFIX[lang] / "index.html").is_file()


def test_every_product_gets_a_page_in_every_language(site: Path, reg: Registry) -> None:
    for lang in LANGS:
        for product in reg.products:
            page = site / PREFIX[lang] / "products" / f"{product['slug']}.html"
            assert page.is_file(), f"missing {lang}/{product['slug']}"
            assert product["name"] in page.read_text(encoding="utf-8")


def test_deploy_files_are_written(site: Path, reg: Registry) -> None:
    assert (site / "CNAME").read_text(encoding="utf-8").strip() == reg.org["domain"]
    assert (site / ".nojekyll").is_file()
    assert (site / "404.html").is_file()
    assert "sitemap.xml" in (site / "robots.txt").read_text(encoding="utf-8")
    assert (site / "products.json").is_file()


def test_sitemap_lists_every_page(site: Path, reg: Registry) -> None:
    sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
    expected = 2 * (1 + len(reg.products))  # home + products, per language
    assert sitemap.count("<loc>") == expected
    for lang in LANGS:
        for product in reg.products:
            assert f"/{PREFIX[lang]}products/{product['slug']}.html" in sitemap


def _internal_links(html: str) -> list[str]:
    return [
        href
        for href in re.findall(r'href="([^"]+)"', html)
        if href.startswith("/") and not href.startswith("//")
    ]


def test_no_internal_link_is_broken(site: Path) -> None:
    """Walk every generated page and resolve every site-absolute href."""
    pages = list(site.rglob("*.html"))
    assert pages
    for page in pages:
        for href in _internal_links(page.read_text(encoding="utf-8")):
            target = href.split("#", 1)[0].lstrip("/")
            if not target:  # "/" or "/#anchor"
                target = "index.html"
            elif target.endswith("/"):
                target += "index.html"
            assert (site / target).exists(), f"{page.name} → {href}"


def test_language_switch_keeps_your_place(site: Path, reg: Registry) -> None:
    """A product page's switch points at the same product, not the home page."""
    for product in reg.products:
        slug = product["slug"]
        en = (site / "products" / f"{slug}.html").read_text(encoding="utf-8")
        vi = (site / "vi" / "products" / f"{slug}.html").read_text(encoding="utf-8")
        assert f'href="/vi/products/{slug}.html" hreflang="vi"' in en
        assert f'href="/products/{slug}.html" hreflang="en"' in vi


def test_pages_declare_their_language(site: Path) -> None:
    for lang in LANGS:
        html = (site / PREFIX[lang] / "index.html").read_text(encoding="utf-8")
        assert f'<html lang="{lang}">' in html


def test_private_products_do_not_advertise_a_source_link(site: Path, reg: Registry) -> None:
    for product in reg.products:
        if product["public"]:
            continue
        html = (site / "products" / f"{product['slug']}.html").read_text(encoding="utf-8")
        assert product["repo"] not in html


def test_public_products_link_their_repo(site: Path, reg: Registry) -> None:
    for product in reg.products:
        if not product["public"]:
            continue
        html = (site / "products" / f"{product['slug']}.html").read_text(encoding="utf-8")
        assert product["repo"] in html


def test_stack_diagram_draws_one_edge_per_declared_dependency(reg: Registry) -> None:
    svg = stack_svg(reg, "en")
    edges = sum(int(bool(p.get("depends_on"))) and len(p["depends_on"]) for p in reg.products)
    assert svg.count('class="stack-edge"') == edges


def test_stack_diagram_omits_non_stack_lines(reg: Registry) -> None:
    """Research datasets are catalogued but are not a layer of the runtime."""
    svg = stack_svg(reg, "en")
    for product in reg.by_line("research"):
        assert f">{product['name']}<" not in svg


def test_stack_boxes_do_not_overlap(reg: Registry) -> None:
    """Two pills sharing a row must not share any horizontal span."""
    svg = stack_svg(reg, "en")
    rects = [
        (float(x), float(y), float(w))
        for x, y, w in re.findall(
            r'<rect class="stack-box[^"]*" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)"', svg
        )
    ]
    assert rects
    by_row: dict[float, list[tuple[float, float]]] = {}
    for x, y, w in rects:
        by_row.setdefault(y, []).append((x, x + w))
    for y, spans in by_row.items():
        spans.sort()
        for (_, end), (start, _) in zip(spans, spans[1:]):
            assert start >= end, f"overlap on row y={y}"


def test_escaping_survives_a_hostile_product_name(tmp_path: Path) -> None:
    """Copy is hand-written, but it must never be able to inject markup."""
    import json

    source = Path(__file__).parent.parent / "registry" / "products.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    data["products"][0]["name"] = '<script>alert("x")</script>'
    hostile = tmp_path / "products.json"
    hostile.write_text(json.dumps(data), encoding="utf-8")

    out = tmp_path / "out"
    build(out=out, registry=hostile)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_build_is_deterministic(tmp_path: Path) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    build(out=first)
    build(out=second)
    for page in first.rglob("*"):
        if page.is_file():
            twin = second / page.relative_to(first)
            assert twin.read_bytes() == page.read_bytes(), page.name
