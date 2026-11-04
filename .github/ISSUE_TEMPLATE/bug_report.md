---
name: Bug report
about: Report reproducible misbehaviour in forge-django or in its generated output
title: ""
labels: bug
---

<!-- Search existing issues first. Security vulnerabilities: see SECURITY.md —
     report them privately via GitHub Security Advisories, not here. -->

## forge-django version

```
forge-django --version
```

<!-- Paste the output. Also note how it was installed (`uv tool install
     forge-django`, `pipx install forge-django`, from source, …). -->

## Wizard answers

<!-- Paste the exact non-interactive command, including --api, --db, --layers:

     forge-django start myproject --no-input --api ninja --db postgres --layers docker,celery

     For an interactive run, list the answers you chose (API framework,
     database, optional layers) and any other prompts you saw. -->

```
```

## Environment

- OS: <!-- e.g. Windows 11, Ubuntu 24.04, macOS 15 -->
- Python version: <!-- `python --version` -->
- Installer / environment: <!-- uv tool, pipx, venv, system pip -->

## What happened

<!-- The command you ran, the actual output or traceback, and which generated
     file is wrong if the bug is in the scaffolded project. -->

## Expected behaviour

## Repro steps

1.
2.
3.

## Additional context

<!-- Generated `.forge-manifest.json`, relevant rendered files, logs, or a
     link to a repository that reproduces the problem. -->
