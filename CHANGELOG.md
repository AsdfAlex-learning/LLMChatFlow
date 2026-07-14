# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- API Server thread safety: session is now passed as parameter instead of mutating shared singleton
- Added rate limiting middleware to /chat and /retrieve endpoints
- Added input length validation (max 10000 chars) to API endpoints
- Embedding failure now returns None instead of silent zero vector
- SQLite connection cleanup via close() method and context manager protocol
- FAISS worker thread stops after repeated failures instead of infinite retry
- LLM client now retries with exponential backoff on transient failures
- API key is no longer logged in error messages

### Changed

- Unified config defaults between config.py and config.yaml
- Aligned dependency versions between pyproject.toml and requirements.txt
- Moved inline imports to file top in default.py and pipeline.py
- Split long methods in SQLiteFaissMemoryStore and StructuredContextBuilder
- Injected AppConfig into StructuredContextBuilder instead of global singleton

### Added

- API server integration tests
- CHANGELOG.md
- CONTRIBUTING.md

## [0.1.0]

- Initial release
