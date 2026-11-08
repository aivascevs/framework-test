## Summary

<!-- What changed and why. Two or three sentences. The governed-change skill writes this for you. -->

## Change metadata

<!--
CI reads the risk class, AI use, AI tool, capability profile and data class from the specification.
You only link it. /new-change writes the specification for you.

Light path (Routine change, AI only suggested code or no AI): replace the Specification line with
  Specification: none
  Risk class: Routine
  AI use: suggest        (or: none)
  AI tool: github-copilot (or: claude-code, none)
  Capability profile: P0 (or: n/a when AI use is none)
-->

Specification: specs/NNN-short-name/spec.md
Exception: none

## Verification

<!-- Which checks ran, and anything a reviewer must look at by hand. -->

- [ ] I checked the change against every acceptance criterion in the specification.
- [ ] I read the reviewer agent findings and the "Change guardrails" result.

## AI disclosure

<!-- Self-declared. It does not prove which lines a model wrote. -->

- [ ] A human read every changed line. The summary alone is not enough.
- [ ] I did not give the AI tool data above the permitted data class (governance/data-handling.md).
