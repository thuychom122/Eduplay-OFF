# Security Policy (EduPlay Studio 1.0.0)

This document explains how to report security vulnerabilities related to EduPlay Studio.

## Scope

- Source code in this repository
- Installers and binaries built from this repository

## Secret management

- Do not commit API keys or tokens into the repository.
- EduPlay Studio talks to its own AI gateway (OpenAI-compatible) and registers the
  device automatically — **no API key is required to run the app**.
- Optional user-entered keys (OpenAI / Gemini, in *Cài đặt → AI*) are stored locally in
  `Documents\EduPlay\Settings`. Device tokens live in `ai_proxy_token.txt` there.
- Logs live in `%LOCALAPPDATA%\EduPlayStudio\logs` — `crash.log`, `run.log`,
  `faulthandler.log`. When sharing logs/screenshots, remove/obfuscate any secrets.

## Reporting a vulnerability

Please do not publicly disclose vulnerabilities before contacting the maintainers.

- Email: support@eduplay-studio.io.vn

Include:
- OS + Python version
- EduPlay Studio version (1.0.0)
- Reproduction steps
- Any relevant logs (without secrets)
