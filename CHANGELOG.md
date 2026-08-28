# Changelog

Notable changes to aeo-hugo. Versions are Hugo Module semver tags, so
`hugo mod get github.com/adamsalves/aeo-hugo@v0.1.0` resolves exactly one of
the entries below.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
this project follows [semantic versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1]

### Fixed

- The JSON-LD `image` falls back to `[params] ogImage` when a page sets none of
  its own, which is the chain `aeo-head.html` already builds `og:image` and
  `twitter:image` from. Reading only the front matter left a page advertising a
  picture in its `<head>` and none in its graph — one page saying two things —
  and on a site that sets the site-wide image and writes no per-post one, it
  dropped `image` from every `BlogPosting` it had. Lost when these templates
  were extracted from terminal-mono, where the head computed the fallback and
  handed the result to the schema partial; found by diffing a real site's
  output across the upgrade, and now asserted in CI, which had no fixture
  setting `ogImage` at all.

## [0.1.0]

First tagged release. Before it, `hugo mod get` had no tag to resolve and
picked a pseudo-version off the default branch.

### Added

- `llms.txt` and `llms-full.txt` as Hugo output formats, one pair per
  language.
- A markdown twin per page (`/posts/foo/index.md`), linked from `llms.txt`.
- `robots.txt` naming answer engines and training crawlers as two groups with
  a switch each — `[params.aeo] allowAI` and `allowTraining`.
- A `Person`/`Organization`, `WebSite`, `BlogPosting`/`WebPage`/
  `CollectionPage` and `BreadcrumbList` JSON-LD graph, linked by `@id`.
- `aeo-head.html`, a complete SEO + AEO head block for themes that have none.
- `[params.aeo] flatSitemap`, publishing one `<urlset>` at the root of a
  multilingual site instead of the `<sitemapindex>` a number of crawlers do
  not follow.
- A preview gate: a build whose environment is not `production` publishes
  nothing to crawlers unless `[params.aeo] allowIndexing = true`.
- Guarded param reads, so a config written in the wrong shape warns and falls
  back instead of aborting the build.
- A build-time self-check (`aeo-no-robots`, `aeo-no-llms`, `aeo-no-markdown`)
  for the failure this module is most exposed to: a site that imported it and
  never wired it up, which is otherwise silent. Silence one with Hugo's
  `ignoreLogs`, or all with `[params.aeo] quiet = true`.
- `scripts/check_aeo.py`, which asserts a built site's AEO output — documented
  for consuming sites, not only used by this repository's CI. It now reads the
  sitemap too: every `<loc>` has to resolve to something the build published,
  in an index and in a `<urlset>` alike.
- A bilingual example site, and CI assertions for the halves that had none: the
  multilingual output, the flat sitemap, `allowTraining = false`, a malformed
  config, and a site that imported the module without wiring it up.

### Changed

- `allowIndexing` moved from the root `[params]` into `[params.aeo]`. The root
  spelling still works and warns once (`aeo-allowindexing-moved`); it was the
  only key this module kept outside its own namespace, and generic enough that
  a theme might want the name.
- `hreflang` in the head is now `.Language.Locale` (`pt-BR`) rather than
  `.Language.Lang` (`pt`), matching what the flat sitemap already wrote, and
  an `x-default` alternate is emitted.
- The sitemap honours `[params.aeo] disallow`. A sitemap is an invitation to
  fetch a URL, so listing one `robots.txt` blocks is the two files disagreeing
  in the direction Search Console reports as an error.
- `robots.txt` writes its `Disallow` lines rooted at the host. `disallow` is a
  path from the *site* root and one prefix covers every language, so
  `/drafts/` now emits `/drafts/` and `/pt/drafts/` — and, under a sub-path
  `baseURL`, `/blog/drafts/` rather than a path that matched nothing.
- `og:type` follows `[params.aeo] postSections` rather than calling every
  non-home page an article, and `article:published_time` is omitted where the
  JSON-LD beside it already omitted a zero date.
- No `[module.mounts]` block. Declaring any mount replaces *all* of Hugo's
  defaults for the module, so naming `layouts` and `static` was two of seven
  written out by hand for identical output — and a trap for the day the module
  grows an `i18n/`.

### Fixed

- `tags` written as a string, `image` written as a list, and `author` written
  as a list are read through the same guards as every other param. The first
  two aborted the build.
- `llms.txt` no longer ships HTML entities in a summary. `truncate` escapes a
  plain string, so `A "quoted" thing & more` reached the file as
  `A &#34;quoted&#34; thing &amp; more` — on a line whose title half was clean
  because nothing truncated it.

[Unreleased]: https://github.com/adamsalves/aeo-hugo/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/adamsalves/aeo-hugo/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/adamsalves/aeo-hugo/releases/tag/v0.1.0
