# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-04-29

### Added
- **Internationalization**: English documentation (`docs/README.md`, `docs/ARCHITECTURE.md`)
- **English Use Case**: ERP Knowledge Assistant use case study (`docs/use_cases/erp_knowledge_assistant.md`)
- **OpenTelemetry Exporter**: Full tracing and metrics support (`macs_pkg/monitoring/openTelemetry_exporter.py`)
- **CONTRIBUTING.md**: Contribution guidelines and coding standards
- **CODE_OF_CONDUCT.md**: Community code of conduct
- **SECURITY.md**: Security vulnerability reporting policy
- **CI/CD**: GitHub Actions workflow with multi-version Python testing
- **Optional OpenTelemetry Dependencies**: New `otel` extra in `pyproject.toml`
- **Badges**: CI/PyPI/license badges in README

### Fixed
- **ChineseCharNgramEmbedder export**: Added to `macs_pkg.rag.__all__`
- **OpenTelemetryExporter export**: Added to `macs_pkg.monitoring.__all__`

### Changed
- Updated `pyproject.toml` with `otel` optional dependency group

## [0.1.0] - 2026-04-27

### Added
- **Multi-Agent Framework**: BaseAgent with think()/act() lifecycle
- **Collaboration Modes**: Hierarchical, Decentralized, Pipeline, Dynamic Selector
- **LLM Providers**: ClaudeProvider, MiniMaxProvider, OpenAICompatibleProvider
- **LLM-Powered Agents**: LLMPlannerAgent, LLMExecutorAgent, LLMReviewerAgent (Claude), MiniMaxPlannerAgent, MiniMaxExecutorAgent, MiniMaxReviewerAgent (MiniMax)
- **RAG Pipeline**: RAGEngine, InMemoryVectorStore, offline Chinese embedder (ChineseCharNgramEmbedder)
- **Tool System**: ToolRegistry, RAGSearchTool, built-in tools
- **Memory System**: MemPalace long-term memory integration
- **Execution Tracing**: Mermaid sequence diagram generation
- **Prometheus Metrics**: MetricsStore and PrometheusExporter
- **Docker Support**: Dockerfile and docker-compose.yml
- **Unit Tests**: 20 tests covering core components

### Architecture
- **Agent Roles**: Planner (decomposition), Executor (execution), Reviewer (validation), Tool (external calls)
- **Proactive RAG**: Keyword-based automatic knowledge base retrieval for ERP domain
- **Error Handling**: TimeoutError, RateLimitError, LLMError with graceful degradation

---

## Versioning

We use [CalVer](https://calver.org/) with format `YYYY.MM.MICRO`:
- `0.1.0` — Initial release (April 2026)
- `0.1.1` — Documentation and enterprise features (April 2026)

---

## Release Process

1. All tests pass on all supported Python versions
2. Changelog updated with date and changes
3. Git tag created: `git tag -a v0.1.1 -m "Release version 0.1.1"`
4. Published to PyPI (automatic via GitHub Actions)
5. GitHub Release created with changelog excerpt
