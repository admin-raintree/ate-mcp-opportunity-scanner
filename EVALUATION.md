# Evaluation

The current scanner is useful for discovery, but it does not establish compatibility or safety.

## Development sample

On September 4, 2026, the scanner evaluated 17 local repositories covering documentation, developer tooling, web applications, finance, media, security, and personal utilities. The sample was used during ranker development, so it is not a held-out benchmark.

A manual review used this narrow label:

> A candidate is relevant when its described capability could plausibly assist the repository based on approved metadata. Relevance does not mean that the server is compatible, maintained, safe, or worth installing.

Results after opportunity-class ranking:

- 13 of 17 repositories had a relevant first candidate: 76% top-1 development-sample relevance.
- 17 of 17 repositories had at least one relevant candidate in the first five: 100% top-5 development-sample relevance.
- 0 of 85 candidate installations were executed or compatibility-tested.
- 0 of 85 candidate repositories received a source-code security audit.

## Observed false positives

- General code-review tools can outrank a more specific integration.
- Documentation-heavy repositories can receive irrelevant document-conversion tools.
- Large mixed-purpose repositories activate too many opportunity classes.
- Similar tools can appear under several server listings despite name-based deduplication.
- ATE's original occupational labels can be implausible even when the underlying function is useful.

## Release criterion

Version `0.1.0` is an experimental discovery release. A future compatibility claim requires a held-out repository set, reproducible labels from more than one reviewer, and successful server-level integration tests. A future safety claim requires source review and behavior testing for each recommended server.
