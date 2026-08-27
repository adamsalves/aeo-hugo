{{- /* The markdown twin of a post, published next to it as index.md.

       Two things want this. A reader that is an answer engine gets the source
       without having to strip a page's chrome back off it, and a citation that
       lands here lands on the same words the HTML shows rather than on a
       reconstruction of them.

       The metadata is a plain list rather than a YAML front-matter block. This
       file is read as prose by a model, not parsed by a static-site generator,
       and fenced front matter is a delimiter the reader has to know about
       before the first line means anything.

       .RawContent, not .Plain, for the reason llms-full.txt gives: headings,
       lists and code fences are the structure, and .Plain is what is left over
       after throwing them away. */ -}}
{{- $gate := partial "aeo-gate.html" . -}}
{{- $allowed := partial "aeo-allowed.html" (dict "pages" (slice .) "disallow" $gate.disallow) -}}
{{- if or (not $gate.indexable) (not $allowed) -}}
{{- /* The twin is written per page, so it is published either way — what it
       carries is the choice. A build that is not for indexing, or a page under
       a [params.aeo] disallow prefix, gets the fact rather than the body: the
       exclusion means nothing if the excluded text ships beside it in markdown.
       */ -}}
# {{ .Title }}

- URL: {{ .Permalink }}
- Not published here: {{ cond $gate.indexable "this page is excluded by [params.aeo] disallow" "this build is not for indexing" }}.
{{- else -}}
{{- $out := slice (printf "# %s" (partial "aeo-text.html" .Title)) "" -}}
{{- $out = $out | append (printf "- URL: %s" .Permalink) -}}
{{- with .Description }}{{ $out = $out | append (printf "- Summary: %s" (partial "aeo-text.html" .)) }}{{ end -}}
{{- if not .Date.IsZero }}{{ $out = $out | append (printf "- Published: %s" (.Date.Format "2006-01-02")) }}{{ end -}}
{{- if not .Lastmod.IsZero }}{{ $out = $out | append (printf "- Updated: %s" (.Lastmod.Format "2006-01-02")) }}{{ end -}}
{{- $tags := partial "aeo-params-list.html" (dict "value" .Params.tags "path" (printf "tags in %s" .RelPermalink) "maps" false) -}}
{{- with $tags }}{{ $out = $out | append (printf "- Tags: %s" (delimit (apply . "partial" "aeo-text.html" ".") ", ")) }}{{ end -}}
{{- $out = $out | append (printf "- Words: %d" .WordCount) -}}
{{- $out = $out | append (printf "- Language: %s" (or .Language.Locale .Language.Lang)) -}}
{{- with .Translations -}}
  {{- range . -}}
    {{- $out = $out | append (printf "- Also published in %s: %s" (or .Language.Locale .Language.Lang) .Permalink) -}}
  {{- end -}}
{{- end -}}
{{- $out = $out | append "" (.RenderShortcodes | strings.TrimSpace) -}}
{{ delimit $out "\n" }}
{{- end -}}
