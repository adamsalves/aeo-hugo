# aeo-hugo

Answer Engine Optimization as a drop-in [Hugo module](https://gohugo.io/hugo-modules/). All of it in Hugo templates — **no npm, no post-build step, no third-party JS**.

- **`llms.txt`** — an index an answer engine reads in one request: title, description, every page as a linked list. Per language on multilingual sites.
- **`llms-full.txt`** — the content behind those links, in markdown, in one file.
- **A markdown twin per page** (`/posts/foo/index.md` next to `/posts/foo/`), linked from `llms.txt`.
- **`robots.txt`** — `User-agent` groups that name the answer engines and the training crawlers separately, each with its own switch.
- **Flat sitemap option** for multilingual sites (one `<urlset>` instead of a `<sitemapindex>`).
- **JSON-LD** — a linked `Person`/`Organization`, `WebSite`, `BlogPosting`/`WebPage`/`CollectionPage`, `BreadcrumbList` graph.
- **A preview gate** — non-production builds publish nothing to crawlers unless you opt in.
- **Guarded params** — a config written in the wrong shape warns and falls back instead of aborting the build.
- **A build-time self-check** — the module says so when the site imported it but never wired it up, which is otherwise a silent no-op.

Requires **Hugo ≥ 0.158**.

## Installation

### Via Hugo Modules (recommended)

```toml
# hugo.toml
[module]
  [[module.imports]]
    path = "github.com/adamsalves/aeo-hugo"
```

### Via Git submodule

```bash
git submodule add https://github.com/adamsalves/aeo-hugo themes/aeo-hugo
```

```toml
# hugo.toml
theme = ["aeo-hugo", "your-theme"]
```

The `theme` array lists components in precedence order, left to right. Put
`aeo-hugo` **first** (left-most): most themes ship a `robots.txt` of their
own, the left-most one wins outright, and a site whose theme wins publishes a
`robots.txt` where `allowAI`, `allowTraining` and `disallow` decided nothing —
with a green build and no symptom anywhere. The module warns when this
happens; see [Verifying the wiring](#verifying-the-wiring). Your own
`layouts/` always wins over every component.

## The one block the module cannot provide

Hugo does not merge a component's `[outputs]` into a site's, so the site
declares which page kinds publish which AEO formats:

```toml
# hugo.toml
[outputs]
  home = ["HTML", "RSS", "LLMS", "LLMSFULL"]
  page = ["HTML", "MARKDOWN"]
```

`HTML` stays first — it is the primary output and decides the permalinks.
And for `robots.txt`, set the root key the module cannot turn on:

```toml
enableRobotsTXT = true
```

## Wiring the head

The module cannot inject itself into your theme's `<head>`. Two options:

- **Your theme renders its own `<head>`** — call the schema partial for the
  JSON-LD, and align your noindex meta with the gate:

  ```html
  <head>
    ...
    {{ if not (partial "aeo-indexable.html" .) }}
    <meta name="robots" content="noindex, nofollow">
    {{ end }}
    {{ partial "aeo-schema.html" . }}
  </head>
  ```

- **Your theme has no SEO head** — call `aeo-head.html` once, which renders
  `<title>`, description, canonical, hreflang, Open Graph, Twitter cards, the
  RSS links, the noindex gate and the JSON-LD in one block. See
  `exampleSite/layouts/_default/baseof.html`.

## Configuration

Every key is optional. Defaults shown:

```toml
# hugo.toml
[params.aeo]
  # Answer engines (search: fetch a page to answer a question and cite it).
  allowAI = true
  # Training crawlers (collect pages into a dataset, no citation).
  allowTraining = true

  # Path prefixes excluded from robots.txt AND from llms.txt, llms-full.txt
  # and the markdown twins, so the files can never disagree.
  disallow = ["/drafts/"]

  # Content sections whose pages are posts (BlogPosting + the llms listing).
  postSections = ["blogs", "posts"]

  # Open a non-production build to crawlers. See The preview gate below.
  allowIndexing = false

  # Turn off the build-time self-check. See Verifying the wiring below.
  quiet = false

  # Who publishes the site. Person is the default. Set type = "Organization"
  # only if the site genuinely is one — Google requires a logo before it will
  # use an Organization at all.
  [params.aeo.publisher]
    type = "Person"
    jobTitle = "Software Engineer"     # Person only
    # logo = "img/logo.png"            # Organization only
    sameAs = ["https://github.com/you", "https://linkedin.com/in/you"]
```

Other params the templates read, all optional:

| Param | Where it comes from | Purpose |
|---|---|---|
| `title` | `[params]` or `title` | Site name in every file |
| `description` | `[params]` | Description in llms.txt / JSON-LD |
| `ogImage` | `[params]` | og:image / twitter:image |
| `twitter` | `[params]` | `twitter:site` |

`disallow` is a path from the **site** root, and one prefix covers every
language: `disallow = ["/drafts/"]` excludes `/drafts/` and `/pt/drafts/`
both, from robots.txt, from the sitemap, from llms.txt, from llms-full.txt
and from the markdown twins.

The two crawler groups, spelled out — these are the names `robots.txt`
actually writes, so you can see what a switch flips before you flip it:

| Switch | Crawlers named in robots.txt |
|---|---|
| `allowAI` | `OAI-SearchBot`, `ChatGPT-User`, `Claude-SearchBot`, `Claude-User`, `PerplexityBot`, `Perplexity-User`, `DuckAssistBot`, `MistralAI-User`, `Amazonbot`, `Applebot` |
| `allowTraining` | `GPTBot`, `ClaudeBot`, `Google-Extended`, `Applebot-Extended`, `meta-externalagent`, `CCBot`, `Bytespider`, `cohere-ai` |

### The flat sitemap

On a **multilingual** site, Hugo publishes `/sitemap.xml` as a
`<sitemapindex>` pointing at per-language sitemaps. A number of crawlers —
aeo.js among them — read every `<loc>` as a page and never follow the index.
`[params.aeo] flatSitemap = true` publishes one `<urlset>` at the root with
every page of every language and its hreflang alternates instead. It is inert
on single-language sites (they use Hugo's built-in sitemap) and off by
default, because a module upgrade should not quietly change what a site
already publishes.

### The preview gate

Any build whose environment is not `production` (`hugo server`, deploy
previews) publishes nothing to crawlers: noindex meta, `Disallow: /` in
robots.txt, and AEO files that state the build is not for indexing. The plain
`hugo` command builds in the production environment. To open a non-production
build, set:

```toml
# hugo.toml
[params.aeo]
  allowIndexing = true
```

(The pre-1.0 spelling was `[params] allowIndexing` at the root. It still
works and warns once.)

## Try it

```bash
cd exampleSite
hugo server --themesDir ../..
```

Build output: `/llms.txt`, `/llms-full.txt`, `/robots.txt`, `/sitemap.xml`,
and `index.md` beside every post.

## Verifying the wiring

Everything this module publishes is read by machines and opened by nobody, so
a site can import it, write every `[params.aeo]` key correctly and publish
none of it — green build, correct-looking pages, and an answer engine that
never had anything to read. Two things guard against that.

**The module warns at build time** when it finds itself unwired:

| Warning id | What it means |
|---|---|
| `aeo-no-robots` | No `robots.txt` came from this module — either `enableRobotsTXT = true` is missing, or another component's `robots.txt` won the `theme` array |
| `aeo-no-llms` | `LLMS` is not in `[outputs] home`, so there is no `llms.txt` |
| `aeo-no-markdown` | `MARKDOWN` is not in `[outputs] page`, so no page publishes a twin |

`[outputs]` is the block Hugo will not merge from a component, so its absence
is a legitimate choice: these only ever warn. Silence one with Hugo's own
`ignoreLogs = ['aeo-no-llms']`, or all of them with `[params.aeo] quiet = true`.

**And `scripts/check_aeo.py` asserts the built output**, which is the half a
template cannot check: that every link in `llms.txt` resolves to a file the
build published, that the `Sitemap:` line names one too, that every `@id` a
JSON-LD node references is defined on the same page, that no breadcrumb has a
gap in it, and that each markdown twin names its own page back. Point it at
your `public/`:

```bash
python3 themes/aeo-hugo/scripts/check_aeo.py public
```

It needs nothing but Python 3. Pass `--no-llms` / `--no-markdown` / `--no-robots`
for the outputs your site does not declare, `--not-indexable` for a preview
build, and `--training-blocked` if you set `allowTraining = false` — without it
the script reports your own opt-out as a defect, which is exactly what it is
for anyone who did not ask for it.

## Design notes

- **The exclusion is the point.** A page under a `disallow` prefix is removed
  from robots.txt, from the sitemap *and* from every AEO file. A path excluded
  from crawling whose full body sits in `llms-full.txt` is not excluded — and a
  sitemap is an invitation to fetch a URL, so listing one robots.txt blocks is
  the same disagreement pointed the other way.
- **The link goes to the markdown twin.** `llms.txt` links to `index.md` when
  a page publishes one, because that is what the [llmstxt.org](https://llmstxt.org)
  proposal asks for — and the citation costs nothing: the twin's first
  metadata line is the canonical URL.
- **Keys stay English.** The labels in `llms.txt` / `llms-full.txt` (`- URL:`,
  `- Language:`) are the same on every language's copy. They are keys, not
  prose; the values carry the language.
- **Plain text has no forgiving renderer.** The AEO files are built as lines
  and joined, so a stray newline can't end a list in the middle.
- **One `<script>` per JSON-LD node**, not one `@graph`: consumers that parse
  each block and look at `["@type"]` without descending into `@graph` read a
  correct graph as one object of no type.

## Acknowledgements

Extracted from the [terminal-mono](https://github.com/adamsalves/terminal-mono)
theme, where the AEO integration was originally built and battle-tested (its
CI asserts the output on a bilingual example site).

## License

[MIT](LICENSE) — Copyright (c) 2026 Adams Alves.
