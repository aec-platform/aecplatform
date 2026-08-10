# aecplatform.vn

The site is static, so hosting is a solved problem and the only real decision
is who terminates TLS.

## Where things stand

| | |
|---|---|
| Domain | **aecplatform.vn**, DNS at **Mắt Bão** (`ns1`/`ns2.matbao.vn`) |
| Repo | `aec-platform/aecplatform`, public — Pages needs that on a free org |
| Pages | enabled, source **GitHub Actions**, custom domain **set to `aecplatform.vn`** |
| DNS today | apex `A` → `142.132.170.171`, which does not answer on port 80 |

So the build and the GitHub side are done. **The one remaining step is the DNS
records, which live in your Mắt Bão account.**

## The records to set at Mắt Bão

Replace the existing apex `A` record — it points at a host that is not
answering. Then:

| Type | Name | Value | Proxy |
|---|---|---|---|
| A | `@` | `185.199.108.153` | **DNS only** |
| A | `@` | `185.199.109.153` | **DNS only** |
| A | `@` | `185.199.110.153` | **DNS only** |
| A | `@` | `185.199.111.153` | **DNS only** |
| AAAA | `@` | `2606:50c0:8000::153` | **DNS only** |
| AAAA | `@` | `2606:50c0:8001::153` | **DNS only** |
| AAAA | `@` | `2606:50c0:8002::153` | **DNS only** |
| AAAA | `@` | `2606:50c0:8003::153` | **DNS only** |
| CNAME | `www` | `aec-platform.github.io` | **DNS only** |

**Set the proxy to DNS only (grey cloud), not proxied (orange).** Cloudflare's
proxy in front of GitHub Pages works, but only with SSL mode **Full** — the
default **Flexible** produces an infinite redirect loop, because Cloudflare
talks HTTP to an origin that redirects to HTTPS. Grey cloud avoids the whole
question and lets GitHub issue and renew the certificate.

Then, once `dig +short aecplatform.vn` returns the GitHub addresses, tick
**Enforce HTTPS** in the repo's Pages settings. It cannot be set before that —
the API returns *"The certificate does not exist yet"*, because there is no
certificate until GitHub can see the domain pointing at it.

The addresses themselves are GitHub's and apply at any DNS host; only the
proxy column is Cloudflare-specific.

### Claim the domain at the org level

Without this, anyone who takes over a dangling DNS record can serve a Pages site
on a subdomain of your domain. It is two minutes and it closes that hole:

**Org settings → Pages → Verified domains → Add** — GitHub gives you a `TXT`
record on `_github-pages-challenge-aec-platform.aecplatform.vn` to add at Mắt Bão
alongside the records above.

## Alternative: Cloudflare Pages

Point Cloudflare Pages at the repo with build command `make build` and output
directory `site`, and move the nameservers to Cloudflare. Worth it if you later
want redirects, geo-routing, analytics without a third-party script, or an API
on the same domain — and it is the option that would let this repo go back to
being private, since GitHub Pages on a private repo needs a paid org plan.

If you switch, **delete `.github/workflows/pages.yml`** so two systems are not
racing to serve the same domain.

## Subdomains worth reserving

| Host | For |
|---|---|
| `docs.` | aggregated tool documentation, when there is enough to aggregate |
| `api.` | if the registry ever becomes a queryable service rather than a file |
| `status.` | once anything is hosted that can be down |

Nothing needs them today. `aecplatform.vn/products.json` already serves the
catalogue as data.

## Email

`sophie.nguyenthuthuy@gmail.com` is what the registry publishes and what the
site shows. Moving to `hello@aecplatform.vn` later means adding MX records and
changing `org.contact` in `registry/products.json` — one field, then `make build`.
