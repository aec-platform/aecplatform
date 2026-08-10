# AEC Platform

**An open toolchain for the built environment — and the construction software
Vietnam actually runs on.**

This is the umbrella repository: the brand, the product catalogue, and the
generator behind [aecplatform.vn](https://aecplatform.vn). The products
themselves live in their own repositories under the
[`aec-platform`](https://github.com/aec-platform) organization.

```bash
make build     # generate site/ from registry/products.json
make serve     # …and serve it on http://localhost:8492
make test      # 29 tests
make check     # validate the registry without writing anything
```

---

## The one rule

**`registry/products.json` is the only place a fact about a product is written.**

The website, the org profile README, and anything else generated here read from
it. Nothing in `build/` knows a product name. That means the catalogue cannot
drift from the site, and a contributor can add a product without reading the
generator.

It also means the registry gets guarded hard. `make check` refuses a build with
a missing translation, an unknown status, a dependency pointing at nothing, or a
dependency cycle. `make check-packages` asks PyPI whether the `published` flags
are still true. `install` is not a field you write — it is derived, so the site
can never advertise a `pip install` for a name that is not on the index.

## What is in the catalogue

Seventeen products in four lines. The full copy, in English and Vietnamese, is in
the registry; this is the shape.

### Products — commercial, Vietnam-first

| | |
|---|---|
| **AEC Suite** | Sixteen modules covering a Vietnamese construction project end to end. NĐ 06/2021, QCVN 06:2022, NĐ 123/2020, Luật Đấu thầu 2023 encoded as schema. |
| **Atlas** | The Atlassian workspace shape, rebuilt around RFIs, submittals and NCRs. |
| **Studio** | Floor plan analysis and generation through a Vietnamese phong thủy ontology. |

### Open tools — MIT and Apache-2.0, self-hosted, no account

`qto` quantity takeoff · `ifcdiff` model changelog · `plancheck` code as rules (43 rules, 26 Vietnamese) ·
`ecfactors` embodied carbon with provenance · `bimq` read-only BIM query for
agents · `roomgraph` plan PDF to room graph · `setlint` drawing-set lint ·
`sitecard` one-page site context · `bimview` IFC to a self-contained HTML viewer ·
`tcvn-compliance-copilot` drawing review against Vietnamese standards

### Foundations

`ifc-spf` — an ISO 10303-21 reader in pure Python, and the layer `qto` and
`plancheck` actually import. `ifctrap` — a language-neutral conformance suite
that keeps any IFC reader honest.

### Research

`phong-thuy-corpus` — 35 rules across 4 schools over floor-plan graphs, with the
inter-school conflict benchmark that measures a 39.6% Bát Trạch ↔ Huyền Không
disagreement rate. `qcvn-conflict-map` — the same method turned on the statutory
codes: where QCVN and TCVN contradict each other, one TOML file per conflict.

## The stack is real

The diagram on the home page is generated from `depends_on` in the registry, and
those edges are real imports, not an architecture aspiration:

```
ecfactors ──▶ qto ──┐
                    │
      plancheck ────┼──▶ ifc-spf
                    │
        bimview ────┘
```

`test_stack_diagram_draws_one_edge_per_declared_dependency` and
`test_dependency_graph_is_acyclic` keep it that way.

## Layout

```
registry/
  products.json     the catalogue — the only source of truth
  schema.json       what a product entry may contain, and why
build/
  site.py           registry → site/, standard library only
  i18n.py           interface strings; check() finds untranslated keys
  org_readme.py     registry → the GitHub org profile README
  check_packages.py registry ↔ PyPI, for the `published` flags
site/               generated; committed so CI can prove it is current
docs/
  DOMAIN.md         DNS, TLS and GitHub Pages for the apex domain
```

Positioning, voice and the org-move record live in the private
`aec-platform/aec-internal` repo — they are not things a public catalogue needs
in order to be useful.

## Adding a product

1. Add an entry to `registry/products.json` — `slug`, `line`, `status`,
   `license`, `public`, `repo`, plus `tagline`, `description` and `highlights`
   in **both** `en` and `vi`.
2. `make check` — it will tell you exactly what is missing.
3. `make build && make test`.
4. Commit `registry/` and `site/` together. CI fails if `site/` is stale.

If the product imports another product in this catalogue, add `depends_on`. The
stack diagram redraws itself.

## Status

Pre-launch. All seventeen products live in the
[`aec-platform`](https://github.com/aec-platform) org as of 2026-08-10.
Fifteen are public; `aec-suite` and `atlas` are commercial and closed.

The site builds and deploys from this repo to
[aecplatform.vn](https://aecplatform.vn); what is left of the launch — the DNS
records and PyPI — is tracked in the private `aec-platform/aec-internal` repo.

None of the open tools are on PyPI yet, which is why every install line
currently points at `git+https://…`. Publishing flips one boolean per package.
