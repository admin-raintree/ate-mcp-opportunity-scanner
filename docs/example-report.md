# Illustrative report

This example uses fictional server names and descriptions. It demonstrates the output format without redistributing ATE rows or implying that a server was verified.

An MCP tool is a callable function. An MCP server provides one or more MCP tools.

## MCP opportunities for sample-dashboard

Agent configuration check: Codex and Cursor folders found

Opportunity classes: Web quality, Database operations, Code maintenance

1. **scan_accessibility** from **example-browser-tools**

   - Published description: Test pages against common accessibility rules in several viewport sizes.
   - Matching signals: Web quality: accessibility, browser, testing
   - Action risk: low
   - Repository: `https://github.com/example/example-browser-tools`
   - Repository screen: screened

2. **inspect_schema** from **example-database-tools**

   - Published description: Read a database schema and report relationships and migration risks.
   - Matching signals: Database operations: database, schema, migration
   - Action risk: low
   - Repository: `https://github.com/example/example-database-tools`
   - Repository screen: warning
   - Repository warnings: No repository license was detected.

These are discovery leads, not compatibility or security approvals. Action-risk labels come from a keyword classifier. Match scores are internal ranking values with no fixed maximum; they are not probabilities.
