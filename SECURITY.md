# Security Policy

## Reporting a vulnerability

Please use GitHub's **Report a vulnerability** button on the repository's Security tab. Do not open a public issue for authentication bypasses, exposed credentials, request-signature problems, or anything that could create unauthorized fal.ai charges.

Never include fal.ai keys, Frame Art bearer tokens, Cloudflare tunnel tokens, TV pairing tokens, or private notification topics in reports or logs.

## Deployment boundary

Frame Art is designed to run on a trusted home network. Only `/api/alexa`, `/api/generate`, `/api/jobs/*`, and `/healthz` should be reachable through an optional public tunnel. Initial setup is restricted to local clients and disables itself after configuration. Alexa requests are checked for both Amazon's signature and the configured `ALEXA_SKILL_ID`.

Generated prompts and images are sent to fal.ai. Optional notifications are sent to the configured ntfy server.
