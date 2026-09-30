# Documentation

This page lists the project documents. Start with the [project README](../README.md) for the workflow and a first run.

## Run and operate

- [Run the review service in Docker](setup-docker.md)
- [Set up a Cloudflare tunnel](setup-cloudflare.md)
- [Run an end-to-end check without model cost](setup-mock-llm.md)
- [HTTP API](api.md) — jobs, authentication, reader input, responses
- [Operations](operations.md) — escalation, cost controls, data handling, prompt injection

## How it works

- [Architecture](architecture.md) — layers, State, rubrics and scope, rules every node follows
- [Agent node specs](agent-node-specs/README.md) — one page per graph node

## Evidence

- [Evaluation](evaluation.md) — suites, results, and limits
- [Architecture decisions](architecture-decisions/README.md) — why the design is the way it is
- Lessons from earlier work: [the previous implementation](lessons-from-previous-projects/disclosure-plain-language.md) and [the guardrail research study](lessons-from-previous-projects/guardrail-research-study.md)
