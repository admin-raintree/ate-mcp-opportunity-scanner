# Evaluation

The current evidence supports an experimental discovery release. It does not establish general recommendation quality, compatibility, or safety.

## Available evidence

The automated test suite covers metadata minimization, agent-configuration opt-in, untrusted links and Markdown, catalog limits, risk labels, and one positive ranking example. GitHub Actions runs the tests and package-installation check on Python 3.11 through 3.14.

During development, one reviewer inspected recommendations for 17 local repositories. Those repositories influenced the ranker, and the review did not preserve enough privacy-safe item-level evidence for independent reproduction. This document therefore makes no numerical quality claim from that review.

Future evaluation must use this relevance definition:

> A candidate is relevant when its described capability could plausibly assist the repository based on approved metadata. Relevance does not mean that the server is compatible, maintained, safe, or worth installing.

No recommended MCP server has been compatibility-tested or approved through this project. No numerical relevance, compatibility, or safety claim should be made until the release criterion below is satisfied.

## Observed false positives

- General code-review tools can outrank a more specific integration.
- Documentation-heavy repositories can receive irrelevant document-conversion tools.
- Large mixed-purpose repositories activate too many opportunity classes.
- Similar tools can appear under several server listings despite name-based deduplication.
- ATE's original occupational labels can be implausible even when the underlying MCP tool is useful.

## Release criterion

Version `0.1.1` remains an experimental discovery release. A future relevance claim requires a versioned scanner commit, a documented repository-selection method, a held-out repository set, privacy-safe item-level labels, more than one independent reviewer, disagreement measurement, and a reproducible scoring procedure. A future compatibility claim also requires successful server-level integration tests. A future safety claim requires source review and behavior testing for each recommended MCP server.
