"""Assert the AEO output of a built site: robots.txt and the JSON-LD graph.

Everything this checks fails silently. A robots.txt whose Sitemap line points at
a file that is not in the build still serves 200. A JSON-LD block with a typo in
it still renders — a crawler skips it and the page looks perfect to a human. An
`author` that references an @id no node defines is a graph with a hole in the
middle of it, and no browser will ever say so.

So the build is the fixture and the assertions are the review:

  robots.txt   one Sitemap line, naming a file the build actually published;
               every group carries at least one rule; the four crawlers aeo.js
               calls major are allowed; and an indexable build contains no bare
               `Disallow: /`, which is the line that would silently switch the
               whole site off.

  JSON-LD      every block parses; every page carries a publisher and a WebSite;
               posts carry a BlogPosting with the fields that make it one and a
               list page carries a CollectionPage; every @id a node references is
               defined by a node on the same page; a BreadcrumbList counts 1..n
               with no gaps and no self-link on its last crumb, and the page it
               describes is a node on that page rather than nothing at all.

  llms.txt     one per language, each starting with an H1 and naming its own
               llms-full.txt; and — the one that matters — every link in it
               resolves to a file the build actually published. A link that
               404s is the failure mode of an index nobody renders and no
               browser ever opens.

  markdown     every post publishes the index.md twin llms.txt links to, and
               that file names the post's own URL back. A twin that points at
               a different page is worse than no twin: a citation follows it.

The three [outputs]-dependent halves can be switched off for a site that never
declared them: --no-robots, --no-llms, --no-markdown. Nothing else is optional —
the JSON-LD needs no configuration and so has no flag.

Run: python3 scripts/check_aeo.py <public-dir> [--no-robots] [--not-indexable]
                                                [--no-llms] [--no-markdown]
                                                [--training-blocked]
"""

import json
import pathlib
import re
import sys
import urllib.parse

# The four aeo.js weighs in its "Major AI bots allowed" check. Being allowed is
# the module's default; a build where one of them is not is a defect unless the
# site asked for it, and a site that asked is not what CI builds.
MAJOR_BOTS = ["gptbot", "claudebot", "google-extended", "perplexitybot"]

# Three of the four above are *training* crawlers, so a site that legitimately
# sets [params.aeo] allowTraining = false fails this check three times for doing
# exactly what the switch is for. --training-blocked says so; the module's own CI
# never passes it, because a build where the module blocks them by default is the
# defect this list is watching for.
TRAINING_BOTS = ["gptbot", "claudebot", "google-extended"]

LD_RE = re.compile(
    r"""<script[^>]*type=["']?application/ld\+json["']?[^>]*>(.*?)</script>""",
    re.S | re.I)

# Hugo writes one of these per alias, and for the root index.html of a site with
# defaultContentLanguageInSubdir. They carry no content of their own, so reading
# one as a page that lost its JSON-LD is a false failure on a correct build.
REDIRECT_RE = re.compile(r"""<meta[^>]*http-equiv=["']?refresh""", re.I)


def parse_robots(text):
    """robots.txt as {agent: {"allow": [...], "disallow": [...]}}.

    Consecutive User-agent lines share the rules that follow them, which is the
    standard's own grouping and the shape the template emits. A blank line ends a
    group; a comment does not.
    """
    groups = {}
    current = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            current = []
            continue
        if line.startswith("#"):
            continue
        m = re.match(r"^user-agent:\s*(.+)$", line, re.I)
        if m:
            agent = m.group(1).strip().lower()
            current.append(agent)
            groups.setdefault(agent, {"allow": [], "disallow": []})
            continue
        m = re.match(r"^(allow|disallow):\s*(.*)$", line, re.I)
        if m and current:
            for agent in current:
                groups[agent][m.group(1).lower()].append(m.group(2).strip())
    return groups


def allowed(groups, agent):
    """Whether one agent may fetch /, by the rules in this file.

    Its own group wins outright when it has one -- a bot never reads the `*`
    group once it has matched its own name, which is the whole reason the
    template repeats the site's disallow list into every group it writes.
    """
    own = groups.get(agent.lower())
    if own is not None:
        return not ("/" in own["disallow"] and "/" not in own["allow"])
    star = groups.get("*")
    if star is None:
        return True
    return "/" not in star["disallow"] or "/" in star["allow"]


def check_robots(public, indexable, training_blocked=False):
    problems = []
    path = public / "robots.txt"
    if not path.is_file():
        return ["robots.txt: not in the build -- the site needs enableRobotsTXT = true"]
    text = path.read_text(encoding="utf-8")

    # A build that is not for indexing drops the Sitemap line, which is the
    # correct output and used to fail here: this check ran unconditionally, so
    # the script's only preview mode rejected the module's own preview build.
    sitemaps = re.findall(r"^\s*sitemap:\s*(\S+)\s*$", text, re.I | re.M)
    if indexable and len(sitemaps) != 1:
        problems.append("robots.txt: expected exactly 1 Sitemap line, found %d"
                        % len(sitemaps))
    if not indexable and sitemaps:
        problems.append("robots.txt: a build that is not for indexing still "
                        "points a Sitemap line at %s" % sitemaps[0])
    for url in sitemaps:
        name = url.rstrip("/").rsplit("/", 1)[-1]
        if not (public / name).is_file():
            problems.append("robots.txt: Sitemap names %s, which the build did not "
                            "publish" % url)

    groups = parse_robots(text)
    if not groups:
        problems.append("robots.txt: no User-agent group parsed out of it at all")
    for agent, rules in groups.items():
        if not rules["allow"] and not rules["disallow"]:
            problems.append("robots.txt: the %s group carries no rule, so nothing "
                            "in it applies" % agent)

    if indexable:
        expected = ([b for b in MAJOR_BOTS if b not in TRAINING_BOTS]
                    if training_blocked else MAJOR_BOTS)
        for bot in expected:
            if not allowed(groups, bot):
                problems.append("robots.txt: %s is blocked" % bot)
        if training_blocked:
            for bot in TRAINING_BOTS:
                if allowed(groups, bot):
                    problems.append("robots.txt: %s is still allowed, and this "
                                    "build says training is blocked" % bot)
        star = groups.get("*", {"disallow": [], "allow": []})
        if "/" in star["disallow"]:
            problems.append("robots.txt: `User-agent: *` carries `Disallow: /` -- "
                            "this build switches the whole site off")
    else:
        if allowed(groups, "gptbot"):
            problems.append("robots.txt: a build that is not for indexing still "
                            "invites crawlers")
    return problems


def json_ld(html):
    """Every ld+json block on a page, parsed. Raises on the first bad one."""
    out = []
    for i, block in enumerate(LD_RE.findall(html)):
        try:
            out.append(json.loads(block))
        except json.JSONDecodeError as exc:
            raise ValueError("block %d is not valid JSON: %s" % (i + 1, exc))
    return out


def check_page(rel, html):
    problems = []
    try:
        nodes = json_ld(html)
    except ValueError as exc:
        return ["%s: %s" % (rel, exc)]

    if not nodes:
        return ["%s: no JSON-LD at all" % rel]

    types = [n.get("@type") for n in nodes]
    defined = {n["@id"] for n in nodes if "@id" in n}

    for node in nodes:
        if node.get("@context") != "https://schema.org":
            problems.append("%s: a %s node with no @context" % (rel, node.get("@type")))

    if not ({"Person", "Organization"} & set(types)):
        problems.append("%s: no Person or Organization -- every other node "
                        "references it" % rel)
    if "WebSite" not in types:
        problems.append("%s: no WebSite node" % rel)

    # A reference to an @id nothing on the page defines is a dangling edge: the
    # consumer resolves it to nothing and the author or publisher disappears.
    for node in nodes:
        for field in ("author", "publisher", "isPartOf", "breadcrumb",
                      "mainEntityOfPage"):
            ref = node.get(field)
            if isinstance(ref, dict) and set(ref) == {"@id"} and ref["@id"] not in defined:
                problems.append("%s: %s.%s points at %s, which no node here defines"
                                % (rel, node.get("@type"), field, ref["@id"]))

    for node in nodes:
        if node.get("@type") == "BlogPosting":
            for field in ("headline", "datePublished", "author", "inLanguage",
                          "mainEntityOfPage", "wordCount"):
                if field not in node:
                    problems.append("%s: BlogPosting has no %s" % (rel, field))
            if len(node.get("headline", "")) > 110:
                problems.append("%s: headline is %d characters; Google drops it over "
                                "110" % (rel, len(node["headline"])))
            # headline and name are the same title, so one has to be a prefix of
            # the other. They stopped agreeing once: truncate escapes a plain
            # string, so headline came out with HTML entities in it -- inside a
            # JSON string, where the consumer reads them literally -- while name,
            # built from the same title, did not. Comparing them catches that
            # without this having to guess at what an entity looks like.
            name, headline = node.get("name"), node.get("headline")
            if isinstance(name, str) and isinstance(headline, str):
                if not name.startswith(headline.rstrip("…")):
                    problems.append(
                        "%s: headline %r is not the start of name %r -- they are "
                        "the same title, so one of them was transformed on the "
                        "way in" % (rel, headline, name))
        # A BreadcrumbList is a trail to the page it sits on, so something on
        # that page has to *be* that page. Without this the list pages carried a
        # trail and nothing it led to -- the dangling shape one level up, which
        # the @id check below cannot see because a BreadcrumbList names no @id.
        if node.get("@type") == "BreadcrumbList":
            described = {"BlogPosting", "WebPage", "CollectionPage"}
            if not (described & set(types)):
                problems.append("%s: a BreadcrumbList and no %s to lead to"
                                % (rel, "/".join(sorted(described))))
            crumbs = node.get("itemListElement", [])
            positions = [c.get("position") for c in crumbs]
            if positions != list(range(1, len(crumbs) + 1)):
                problems.append("%s: breadcrumb positions are %s, not 1..%d"
                                % (rel, positions, len(crumbs)))
            if crumbs and "item" in crumbs[-1]:
                problems.append("%s: the last breadcrumb links to itself" % rel)
            for crumb in crumbs[:-1]:
                if not crumb.get("item"):
                    problems.append("%s: a breadcrumb before the last has no item"
                                    % rel)
    return problems


# The link text may carry an escaped bracket, because aeo-text.html puts one
# there: a title like "TIL: array[0]" would otherwise close the link early.
# Reading the escape is what keeps this check and that partial agreeing --
# a regex that stopped at the backslash would report the correct output as
# the broken markdown it exists to catch.
LINK_RE = re.compile(r"\[(?:[^\[\]\\]|\\.)*\]\((\S+?)\)")


def local_path(public, base, url):
    """Where a published URL lives on disk, or None if it is not this site's.

    The base path comes out of llms.txt's own `- Home:` line rather than being
    passed in, so this checks the file against the site it says it describes.
    A URL ending in / is a directory, and Hugo publishes index.html into it.
    """
    if "://" in url:
        rest = url.split("://", 1)[1]
        url = "/" + rest.split("/", 1)[1] if "/" in rest else "/"
    if not url.startswith(base):
        return None
    # A permalink is percent-encoded and the directory on disk is not: Hugo
    # publishes pt/tags/migração/ and links pt/tags/migra%C3%A7%C3%A3o/. Compare
    # the decoded form or every accented tag reads as a broken link.
    rel = urllib.parse.unquote(url[len(base):]).lstrip("/")
    if rel == "" or rel.endswith("/"):
        rel += "index.html"
    return public / rel


def check_llms(public):
    problems = []
    files = sorted(public.rglob("llms.txt"))
    if not files:
        return ["llms.txt: not in the build -- the site needs LLMS in [outputs] home"]

    for path in files:
        rel = "/" + str(path.relative_to(public))
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or not lines[0].startswith("# "):
            problems.append("%s: does not start with an H1" % rel)
            continue
        home = re.search(r"^- Home:\s*(\S+)\s*$", text, re.M)
        if not home:
            problems.append("%s: no `- Home:` line, so nothing states what site "
                            "this describes" % rel)
            continue
        # The `- Home:` line is the *language* home, and /pt/llms.txt names
        # /t/pt/ while its links are rooted at /t/. Subtracting the file's own
        # directory gives the site root that every link in it is relative to —
        # get this wrong and every link in the second language reads as broken,
        # which is exactly what happened while this check was being written.
        base = home.group(1)
        if "://" in base:
            rest = base.split("://", 1)[1]
            base = "/" + rest.split("/", 1)[1] if "/" in rest else "/"
        here = path.parent.relative_to(public).as_posix()
        if here != "." and base.rstrip("/").endswith("/" + here):
            base = base.rstrip("/")[:-len(here)]
        if not base.endswith("/"):
            base += "/"
        if not any(l.startswith("## ") for l in lines):
            problems.append("%s: no H2 section -- the index lists nothing" % rel)
        full = path.parent / "llms-full.txt"
        if not full.is_file():
            problems.append("%s: no llms-full.txt beside it" % rel)
        elif "llms-full.txt" not in text:
            problems.append("%s: does not link the llms-full.txt next to it" % rel)

        # Every `- ` item under an `## ` heading is supposed to be a link, so
        # the count of items and the count of links have to agree. Matching the
        # links alone was the fail-open: a title carrying a `]` breaks the link
        # it sits in, LINK_RE stops matching it, and the item is simply not
        # checked. It is the same "quietly matched nothing" this script's own
        # docstring is written against.
        items = [l for l in lines if l.startswith("- [")]
        links = LINK_RE.findall(text)
        item_links = [l for l in items if LINK_RE.search(l)]
        if len(item_links) != len(items):
            for line in items:
                if not LINK_RE.search(line):
                    problems.append("%s: a list item is not a link -- something in "
                                    "it broke the markdown: %s" % (rel, line[:90]))

        seen = 0
        for url in links:
            target = local_path(public, base, url)
            if target is None:
                continue
            seen += 1
            if not target.is_file():
                problems.append("%s: links %s, which the build did not publish"
                                % (rel, url))
        if seen == 0:
            problems.append("%s: not one link in it points at this site" % rel)

        # A blank line inside a list is a list that ends early for a reader that
        # takes markdown literally, and it is the exact failure a line-joined
        # template produces when one value arrives with a trailing newline.
        for i, line in enumerate(lines[:-1]):
            if not line.startswith("- ") or i + 2 >= len(lines):
                continue
            nxt, after = lines[i + 1], lines[i + 2]
            if not after.startswith("- "):
                continue
            if nxt == "":
                problems.append("%s: a blank line splits the list at line %d"
                                % (rel, i + 2))
            elif not nxt.startswith("- "):
                # A newline inside a title does not leave a blank line, it
                # leaves the rest of the title on a line of its own — the same
                # broken list, one the blank-line net did not catch.
                problems.append("%s: line %d continues the item above instead of "
                                "starting one: %s" % (rel, i + 2, nxt[:90]))
    return problems


def check_markdown(public):
    problems = []
    twins = sorted(public.rglob("index.md"))
    if not twins:
        return ["index.md: not one post published a markdown twin -- the site "
                "needs MARKDOWN in [outputs] page"]
    for path in twins:
        rel = "/" + str(path.relative_to(public))
        if not (path.parent / "index.html").is_file():
            problems.append("%s: has no index.html beside it" % rel)
        text = path.read_text(encoding="utf-8")
        if not text.startswith("# "):
            problems.append("%s: does not start with an H1" % rel)
        url = re.search(r"^- URL:\s*(\S+)\s*$", text, re.M)
        if not url:
            problems.append("%s: names no canonical URL, so a citation that "
                            "lands here has nothing to cite" % rel)
        else:
            # The whole path from the site root, not the last segment: ".../
            # other/xxx-one" ends with "one" and is a different page entirely.
            # A twin that names one is worse than no twin, because a citation
            # follows it.
            here = path.parent.relative_to(public).as_posix()
            named = url.group(1).split("://", 1)[-1]
            named = named.split("/", 1)[1] if "/" in named else ""
            if not named.strip("/").endswith(here):
                problems.append("%s: names %s, which is a different page"
                                % (rel, url.group(1)))
    return problems


def check(public_dir, expect_robots=True, indexable=True, expect_llms=True,
          expect_markdown=True, training_blocked=False):
    public = pathlib.Path(public_dir)
    problems = []
    if expect_robots:
        problems += check_robots(public, indexable, training_blocked)
    if expect_llms:
        problems += check_llms(public)
    if expect_markdown:
        problems += check_markdown(public)

    pages = sorted(public.rglob("*.html"))
    if not pages:
        return ["%s: no HTML in it -- nothing was checked" % public_dir]

    # Every page that carries a graph is checked, not just the home and the
    # posts. The gate used to be `if "BlogPosting" in html`, which left the
    # lists, the taxonomies, the term pages and the whole WebPage branch
    # unverified: a /posts/index.html with all three of its blocks corrupted
    # came back clean.
    home = public / "index.html"
    posts = 0
    checked = 0
    for path in pages:
        rel = "/" + str(path.relative_to(public))
        html = path.read_text(encoding="utf-8")
        if REDIRECT_RE.search(html):
            continue
        is_home = path == home
        if not is_home and "application/ld+json" not in html:
            # A page the module deliberately leaves silent -- the 404 is one.
            continue
        checked += 1
        if "BlogPosting" in html:
            posts += 1
        problems += check_page("/" if is_home else rel, html)

    if not checked:
        problems.append("%s: not one page carried a JSON-LD block, so this "
                        "check verified nothing" % public_dir)
    if posts == 0:
        problems.append("%s: not one page carried a BlogPosting, so the post half "
                        "of this check verified nothing" % public_dir)
    return problems


# Flag -> the check() keyword it sets, and whether passing the flag means True
# or False. One mapping, because main() reads the flags and the guard below
# rejects the rest: a second hand-written list is a real flag refused as unknown,
# which is what a hardcoded set did the moment --no-llms was added.
FLAGS = {
    "--no-robots": ("expect_robots", False),
    "--not-indexable": ("indexable", False),
    "--no-llms": ("expect_llms", False),
    "--no-markdown": ("expect_markdown", False),
    "--training-blocked": ("training_blocked", True),
}


def usage():
    """The Run: line and its continuations, however many there come to be."""
    lines = __doc__.strip().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("Run:"))
    return [l for l in lines[start:] if l.strip()]


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if not args:
        print("\n".join(usage()), file=sys.stderr)
        return 2
    unknown = sorted(flags - set(FLAGS))
    if unknown:
        print("unknown flag(s): %s" % " ".join(unknown), file=sys.stderr)
        print("\n".join(usage()), file=sys.stderr)
        return 2
    opts = {name: (on if flag in flags else not on)
            for flag, (name, on) in FLAGS.items()}
    problems = check(args[0], **opts)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        print("\n%d problem(s) in the AEO output." % len(problems), file=sys.stderr)
        return 1
    # Naming what actually ran, because the line is the whole output on a green
    # run: saying "llms.txt checks out" after --no-llms turned it off is the
    # check reporting work it did not do.
    did = ["the JSON-LD graph"]
    if opts["expect_robots"]:
        did.insert(0, "robots.txt")
    if opts["expect_llms"]:
        did.append("llms.txt")
    if opts["expect_markdown"]:
        did.append("the markdown twins")
    print("%s: %s check out" % (args[0], ", ".join(did)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
