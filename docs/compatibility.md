# Samsung Frame Compatibility

Samsung does not publish the local Art Mode WebSocket API used by this project, and behavior can change with model year and firmware. Compatibility claims in this project are based on user reports and sanitized diagnostics rather than the retail product name alone.

## Current matrix

| Model code | Model year | Firmware | Art API | Pair | Upload | Select | Report |
|---|---:|---|---|---|---|---|---|
| _Awaiting verified reports_ | | | | | | | |

## Submit a report

Run this inside the container:

```bash
docker compose exec frame-art frame-art-diagnostics
```

Review the output before attaching it to a GitHub issue. The command excludes fal.ai credentials, API bearer tokens, pairing tokens, and TV IP addresses. You should still remove room names or error messages you consider private.

Report whether pairing, upload, and immediate display each succeeded. A failure on one firmware does not necessarily mean every television from that model year is incompatible.
