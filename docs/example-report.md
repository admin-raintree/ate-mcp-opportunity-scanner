# Illustrative report

This example uses fictional server names and descriptions. It demonstrates the output format without redistributing ATE rows or implying that a server was verified.

## MCP opportunities for sample-dashboard

Detected agent surfaces: Codex, Cursor

Opportunity classes: Web quality, Database operations, Code maintenance

1. **scan_accessibility** from **example-browser-tools**

   - Possible use: Test pages against common accessibility rules in several viewport sizes.
   - Matching signals: Web quality: accessibility, browser, testing
   - Action risk: low
   - Repository: `https://github.com/example/example-browser-tools`
   - Repository screen: screened

2. **inspect_schema** from **example-database-tools**

   - Possible use: Read a database schema and report relationships and migration risks.
   - Matching signals: Database operations: database, schema, migration
   - Action risk: low
   - Repository: `https://github.com/example/example-database-tools`
   - Repository screen: warning
   - Repository warnings: No repository license was detected.

These are discovery leads, not compatibility or security approvals.
