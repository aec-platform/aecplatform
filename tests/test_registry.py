"""The registry is the source of truth, so it is what gets guarded hardest.

A wrong fact here becomes a wrong fact on aecplatform.vn and in every deck
generated from it. These tests are the reason a contributor can edit
``products.json`` without reading the generator.
"""

from __future__ import annotations

import json

import pytest

from build.i18n import LANGS, STATUS
from build.site import REGISTRY, Registry


@pytest.fixture(scope="module")
def reg() -> Registry:
    return Registry.load()


def test_registry_is_publishable(reg: Registry) -> None:
    assert reg.validate() == []


def test_registry_matches_its_own_schema_keys(reg: Registry) -> None:
    """Every product field is one the schema declares — no silent typos."""
    schema = json.loads((REGISTRY.parent / "schema.json").read_text(encoding="utf-8"))
    allowed = set(schema["properties"]["products"]["items"]["properties"])
    for product in reg.products:
        unknown = set(product) - allowed
        assert not unknown, f"{product['slug']}: undeclared field(s) {sorted(unknown)}"


def test_required_product_fields(reg: Registry) -> None:
    schema = json.loads((REGISTRY.parent / "schema.json").read_text(encoding="utf-8"))
    required = schema["properties"]["products"]["items"]["required"]
    for product in reg.products:
        missing = [field for field in required if field not in product]
        assert not missing, f"{product['slug']}: missing {missing}"


def test_slugs_are_unique_and_url_safe(reg: Registry) -> None:
    slugs = [p["slug"] for p in reg.products]
    assert len(slugs) == len(set(slugs))
    for slug in slugs:
        assert slug == slug.lower()
        assert " " not in slug and "/" not in slug


def test_every_line_has_at_least_one_product(reg: Registry) -> None:
    for line in reg.lines:
        assert reg.by_line(line["id"]), f"line {line['id']!r} is empty"


def test_statuses_are_known(reg: Registry) -> None:
    for product in reg.products:
        assert product["status"] in STATUS


def test_dependency_graph_is_acyclic(reg: Registry) -> None:
    """A cycle would make the stack diagram meaningless and loop the layout."""
    state: dict[str, int] = {}

    def visit(slug: str, trail: list[str]) -> None:
        if state.get(slug) == 1:
            raise AssertionError("dependency cycle: " + " → ".join(trail + [slug]))
        if state.get(slug) == 2:
            return
        state[slug] = 1
        product = reg.by_slug(slug)
        for dep in (product or {}).get("depends_on", []):
            visit(dep, trail + [slug])
        state[slug] = 2

    for product in reg.products:
        visit(product["slug"], [])


def test_dependencies_point_at_real_products(reg: Registry) -> None:
    for product in reg.products:
        for dep in product.get("depends_on", []):
            assert reg.by_slug(dep) is not None, f"{product['slug']} → unknown {dep}"


def test_reverse_edges_agree_with_forward_edges(reg: Registry) -> None:
    for product in reg.products:
        for dep in product.get("depends_on", []):
            assert product in reg.dependents_of(dep)


def test_public_products_have_a_repo_url(reg: Registry) -> None:
    for product in reg.products:
        if product["public"]:
            assert product["repo"].startswith("https://github.com/")


def test_install_command_never_promises_an_unpublished_package(reg: Registry) -> None:
    """A `pip install <name>` line may only appear once the name is on the index."""
    from build.site import install_command

    for product in reg.products:
        result = install_command(product)
        if result is None:
            continue
        line, on_index = result
        package = product["package"]
        assert on_index is package["published"]
        if on_index:
            assert line == f"pip install {package['name']}"
        else:
            assert line.startswith("pip install git+")


def test_private_products_offer_no_install_line(reg: Registry) -> None:
    from build.site import install_command

    for product in reg.products:
        if not product["public"]:
            assert install_command(product) is None


def test_translations_are_complete(reg: Registry) -> None:
    for product in reg.products:
        for lang in LANGS:
            assert product["tagline"][lang].strip()
            assert product["description"][lang].strip()
            assert product["highlights"][lang]
            assert all(item.strip() for item in product["highlights"][lang])


def test_taglines_stay_short_enough_for_a_card(reg: Registry) -> None:
    for product in reg.products:
        for lang in LANGS:
            length = len(product["tagline"][lang])
            assert length <= 130, f"{product['slug']} {lang} tagline is {length} chars"


def test_test_counts_are_plausible(reg: Registry) -> None:
    """Guards against a stray zero or a pasted line count."""
    for product in reg.products:
        if "tests" in product:
            assert 0 < product["tests"] < 10_000, product["slug"]
