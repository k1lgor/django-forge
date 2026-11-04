# Security Policy

## Supported versions

Only the latest release of `forge-django` on PyPI receives security fixes.

| Version | Supported |
| ------- | --------- |
| 0.4.x   | yes       |
| < 0.4   | no        |

## Reporting a vulnerability

Report vulnerabilities privately through
[GitHub Security Advisories](https://github.com/k1lgor/django-forge/security/advisories)
on this repository ("Report a vulnerability"). The report is visible only to
the maintainers until a fix is released.

Do not open a public issue, pull request, or discussion for a vulnerability,
and do not send reports by email — there is no public security contact
address. Public issues that disclose a vulnerability will be converted to a
private advisory where possible.

Include in your report:

- `forge-django --version` output
- the exact command or interactive answers used (OS and Python version)
- the rendered files that demonstrate the problem
- the impact and, if known, a suggested fix

You will be contacted when the report is triaged and again when it is fixed.
Fixes are released through a normal version bump; disclosure timing is agreed
with the reporter.

## Scope

In scope:

- `forge-django` itself: the CLI, the rendering pipeline, the layer registry,
  and the defaults it writes.
- The security posture of **generated projects**: secrets handling in `.env`
  and `.env.example`, production settings (`config/settings/prod.py`),
  `DEBUG`/secret-key handling, deploy-check behaviour, CORS/HTTPS/proxy
  defaults, and the dependency pins shipped in the generated
  `pyproject.toml`.

Out of scope:

- vulnerabilities only in dependencies of a generated project — report those
  upstream, then open an issue here if our pin blocks the fixed release
- the scaffolded project's own code after you modify it
- reports that require a modified or unsupported version of `forge-django`
