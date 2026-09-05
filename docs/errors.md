# Resolve scanner errors

Each scanner failure begins with a stable code. Use the recovery action for that code, then run the scanner again.

| Code | What happened | Recovery action |
| --- | --- | --- |
| `ATE100` | A command argument is invalid. | Correct the argument shown in the message. Run `ate-scan --help` to review accepted values. |
| `ATE101` | Offline mode could not find a catalog. | Run without `--offline` to download the official catalog, or pass `--catalog` with an existing ATE JSONL file. |
| `ATE102` | The official ATE catalog could not be downloaded, extracted, or refreshed. A failed initial build does not create a complete cache. A failed refresh preserves the previous complete cache. | Check the network connection and retry. If the failure continues, pass `--catalog` with an existing file. |
| `ATE103` | A selected project path was not scanned. | Correct the path so it names an existing project directory. |
| `ATE104` | The selected catalog could not be read. | Pass `--catalog` with a valid ATE JSONL file. |
| `ATE105` | No selected project was scanned. | Correct every path reported with `ATE103`, then run the command again. |
| `ATE106` | The report could not be written. The selected output file may be incomplete. | Select a new writable output path and run the command again. |
| `ATE107` | The inert configuration review bundle could not be written. No client configuration was changed. | Select a new writable review-bundle path and run the command again. |

The scanner does not install MCP servers or modify scanned projects when one of these failures occurs. A failed cache refresh can leave the previous complete cache available; temporary download files are deleted.
