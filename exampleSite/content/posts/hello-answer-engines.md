+++
title = "Hello, answer engines"
date = 2026-08-01
tags = ["aeo", "hugo"]
description = "A first post for the demo."
+++

## Why this file matters

An answer engine reading this site wants the headings, the lists and the code,
not the HTML chrome. This post becomes three artifacts at build time:

1. The HTML page a human reads.
2. An `index.md` twin next to it, linked from `llms.txt`.
3. Its full markdown inside `llms-full.txt`, addressed by its URL.

```go
package main

import "fmt"

func main() {
    fmt.Println("hi")
}
```
