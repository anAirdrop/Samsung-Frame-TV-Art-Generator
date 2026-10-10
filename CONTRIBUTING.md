# Contributing

Thanks for helping make Frame Art work across more Samsung Frame generations.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

On Windows, activate with `.venv\Scripts\Activate.ps1`.

Keep integrations small and explicit. New fal.ai models should be added as tested presets with validated arguments rather than arbitrary user-provided payloads. TV compatibility changes should include the model code, model year, Art API version when available, and tests using sanitized fixtures.

Never commit `.env`, files under `data/`, TV tokens, tunnel tokens, API keys, private IP inventories, or generated images containing personal material.

## Pull requests

- Keep changes focused.
- Add or update tests for behavior changes.
- Run the complete test and lint suite.
- Update the setup instructions when changing user-visible configuration.
- Describe any real Frame TV model and firmware used for validation.
