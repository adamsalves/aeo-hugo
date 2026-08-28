+++
title = "Olá, motores de resposta"
date = 2026-08-01
tags = ["aeo", "hugo"]
description = "Um primeiro post para a demonstração."
+++

## Por que este arquivo importa

Um motor de resposta lendo este site quer os títulos, as listas e o código —
não o cromo do HTML. Este post vira três artefatos no build:

1. A página HTML que uma pessoa lê.
2. Um gêmeo `index.md` ao lado dela, linkado a partir do `llms.txt`.
3. O markdown completo dentro do `llms-full.txt`, endereçado pela sua URL.

```go
package main

import "fmt"

func main() {
    fmt.Println("oi")
}
```
