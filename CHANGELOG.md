# Changelog

All notable changes to EduPlay Studio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-05

### Added
- Desktop application (PySide6) for creating educational games.
- Edubot (AI assistant) connected to the EduPlay AI gateway (OpenAI-compatible).
  Device is registered automatically — **no API key required**.
- Game templates: Quiz, Millionaire, Fishing, Adventure, Platformer.
- Export:
  - HTML5 web game export (bundles assets for offline use, single file)
  - Web publishing to Firebase with a public play link (auto-renew, ~15 day TTL)
- PowerPoint integration (Windows): installs local Office add-ins (taskpane + content) from within the app.
- Packaging scripts: Cython + Nuitka build script + Inno Setup installer script.
- Question import from `.docx` / `.doc` / `.pdf` / `.xlsx` / `.txt` plus downloadable templates.
- Editor undo/redo (`Ctrl+Z` / `Ctrl+Y`), command palette (`Ctrl+K`), quick calculator (`Ctrl+T`).
- In-app help (button **?**), organised by task, translated in 5 languages.
- Crash diagnostics: `%LOCALAPPDATA%\EduPlayStudio\logs\crash.log` + `run.log`.

### Notes
- PowerPoint add-ins may require Office activation and a PowerPoint restart after installation.
- **Not exposed in the UI:** Native/PyGame (EXE) export. Code exists but no button
  reaches it, so it is deliberately not documented as an export option.
- Web links expire after ~15 days; republishing from the same machine overwrites
  the existing link instead of creating a new one.
