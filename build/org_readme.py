"""Generate the GitHub org profile README from the same registry the site uses.

Prints to stdout, so it can be redirected wherever the ``.github`` repo lives:

    python -m build.org_readme > ../.github/profile/README.md

Keeping this generated is the whole point — a hand-written org README drifts
from the catalogue within a month, and then two places disagree about what the
company ships.
"""

from __future__ import annotations

import sys

from .i18n import STATUS
from .site import Registry, install_command

LANG = "en"


def render(reg: Registry) -> str:
    org = reg.org
    out: list[str] = [
        f"# {org['name']}",
        "",
        f"**{org['tagline'][LANG]}**",
        "",
        org["thesis"][LANG][1],
        "",
    ]

    for line in reg.lines:
        products = reg.by_line(line["id"])
        if not products:
            continue
        out += [f"## {line['name'][LANG]}", "", line["blurb"][LANG], ""]
        out.append("| | What it does | Status | Install |")
        out.append("|---|---|---|---|")
        for product in products:
            name = product["name"]
            link = f"[{name}]({product['repo']})" if product["public"] else f"`{name}`"
            install = install_command(product)
            install = f"`{install[0]}`" if install else "—"
            out.append(
                f"| {link} | {product['tagline'][LANG]} "
                f"| {STATUS[product['status']][LANG]} | {install} |"
            )
        out.append("")

    open_products = [p for p in reg.products if p["line"] in ("open", "foundation")]
    out += [
        "---",
        "",
        f"{sum(p.get('tests', 0) for p in open_products):,} tests across "
        f"{len(open_products)} open-source tools, zero third-party runtime "
        "dependencies between them.",
        "",
        f"[{org['domain']}](https://{org['domain']}) · <{org['contact']}> · {org['base']}",
        "",
    ]
    return "\n".join(out)


if __name__ == "__main__":  # pragma: no cover
    sys.stdout.write(render(Registry.load()))
