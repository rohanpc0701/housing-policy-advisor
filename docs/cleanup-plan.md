# Cleanup Plan

## Goals

Bring the repository into a state where:

- Documentation matches the implemented behavior
- Runtime modes are explicit rather than implied
- Dead or legacy paths are either restored or removed
- Configuration is meaningful and actually consumed
- Future changes have a smaller maintenance surface

## Priority 1: Fix User-Facing Drift

### 1. Align README with the current CLI

Problem:

- `README.md` documents flags that do not exist, including `--input-only`, `--use-llm`, `--building-permits-trend`, `--housing-dept-name`, and `--has-housing-dept`

Actions:

1. Regenerate the documented CLI examples from the actual parser in `housing_policy_advisor/main.py`
2. Remove claims about “mock recommendations” unless that mode is restored
3. Document the real required dependencies for recommendation generation, especially `GROQ_API_KEY`
4. Clarify that JSON is the only guaranteed output format in the current repo state

Success condition:

- A new user can copy any README command and run it without hitting unknown-argument errors

### 2. Make runtime modes explicit

Problem:

- The codebase and docs imply multiple modes, but the current implementation only supports one recommendation path

Actions:

1. Decide whether the project should support:
   - LLM-only generation
   - LLM plus retrieval generation
   - locality-profile-only export
   - mock recommendation generation
2. Either implement those modes fully or remove them from docs and interfaces
3. Encode the chosen modes in CLI flags and tests

Success condition:

- Runtime behavior can be described in one short section without caveats

## Priority 2: Remove or Restore Legacy Paths

### 3. Resolve legacy `pdf` and `docx` output handling

Problem:

- `housing_policy_advisor/pipeline.py` imports `housing_policy_advisor.past_code...`, which is absent from this repository
- Output requests for `pdf`, `docx`, or `all` silently degrade

Actions:

1. Choose one of two directions:
   - Restore the rendering implementation into this repo and test it
   - Remove those formats from the CLI and keep JSON only
2. If JSON only is the intended scope, delete `_legacy_report_adapter()` and `_try_render_legacy_outputs()`
3. Add tests that assert the supported output formats explicitly

Success condition:

- Every supported output format is implemented in-repo and test-covered

### 4. Consolidate prompt-building duplication

Problem:

- There are two prompt builders with overlapping intent:
  - `housing_policy_advisor/rag/prompt_builder.py`
  - `housing_policy_advisor/llm/prompts.py`

Actions:

1. Keep one prompt builder as the canonical implementation
2. Delete or fold the unused variant
3. Add a small test around prompt structure and evidence labeling

Success condition:

- There is one obvious place to change prompt construction

## Priority 3: Make Configuration Real

### 5. Wire validation thresholds into the validator or delete them

Problem:

- `housing_policy_advisor/config.py` defines threshold constants that are not used
- `housing_policy_advisor/llm/output_validator.py` hardcodes separate thresholds

Actions:

1. Decide whether thresholds should be configurable
2. If yes, import the config values into `output_validator.py`
3. If no, remove the unused constants from `config.py`
4. Add tests around threshold behavior so drift is visible

Success condition:

- There is one source of truth for validation thresholds

### 6. Reconcile ingestion defaults with repository contents

Problem:

- `DEFAULT_PDF_SOURCES` points at `corpus/...` directories that are not present in this checkout

Actions:

1. Either add the expected corpus layout to the repo contract and document it
2. Or remove hardcoded defaults and require explicit `--source-dir` arguments
3. Add a smoke test for the chosen ingestion entry behavior

Success condition:

- The ingest CLI either works by default or clearly requires explicit inputs

## Priority 4: Tighten Reliability

### 7. Clarify degraded-mode behavior

Problem:

- Missing HUD and BLS credentials degrade gracefully
- Missing retrieval degrades gracefully
- Missing Groq credentials fail hard

Actions:

1. Document the exact degraded behaviors in README and architecture docs
2. Decide whether missing retrieval should remain non-fatal
3. Add tests for the intended fallback contract

Success condition:

- Operators know which dependencies are optional and which are mandatory

### 8. Strengthen end-to-end contract tests

Problem:

- The module coverage is good, but there is limited coverage of the full top-level execution contract

Actions:

1. Add a CLI-level test for `housing_policy_advisor.main`
2. Add a pipeline-level test that verifies final JSON shape includes `locality_profile`
3. Add a negative-path test for missing Groq credentials
4. Add a negative-path test for unsupported output formats if those modes remain

Success condition:

- The most important user-visible contracts fail loudly in CI when broken

## Suggested Execution Order

1. Fix README and CLI drift
2. Decide supported runtime modes
3. Remove or restore legacy output formats
4. Remove prompt-builder duplication
5. Reconcile config thresholds
6. Reconcile ingest defaults
7. Add missing contract tests

## Recommended Default Direction

If the goal is a smaller and more reliable codebase, the lowest-risk direction is:

1. Keep recommendation generation as Groq-backed JSON output
2. Keep retrieval optional but explicit
3. Drop legacy `pdf` and `docx` output until it is reimplemented in-repo
4. Remove undocumented or unimplemented runtime modes
5. Keep one prompt builder and one validation-threshold source

That path reduces ambiguity without changing the core product behavior.
