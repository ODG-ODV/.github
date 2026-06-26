# Organization Defaults

This repository contains organization-wide GitHub configuration and templates that are automatically used by repositories across the organization unless they define their own equivalents.

## Purpose

The goal of this repository is to standardize the development experience and enforce consistent engineering practices across all projects.

## Contents

### Pull Request Template

Location:

```
.github/PULL_REQUEST_TEMPLATE.md
```

Provides a standardized pull request template for all repositories that do not define their own.

## Repository Standards

This repository supports the organization's GitHub governance, including:

- Standardized branch naming conventions
- Pull request workflow
- Repository rulesets
- Code review practices
- Continuous Integration (CI) standards

Additional templates and organization defaults may be added over time, including:

- Issue templates
- Security policy
- Contributing guidelines
- Code of Conduct
- GitHub Actions workflow templates

## Repository-Specific Overrides

Repositories can override any of these defaults by providing their own files in the appropriate locations.

For example:

```
.github/PULL_REQUEST_TEMPLATE.md
```

inside a repository will take precedence over the organization-wide template.

## Maintainers

This repository is maintained by the Engineering team. Changes should be reviewed carefully as they affect repositories across the organization.