+++
title = "Markdown is the interface"
date = 2026-08-15
tags = ["llms"]
description = "Why the module publishes markdown, not just HTML."
+++

## The source is the payload

Hugo already turns markdown into HTML. Publishing the markdown itself costs
one output format and gives every AI reader the structure instead of a page it
has to strip. The `MARKDOWN` output format in `hugo.toml` is the whole trick.
