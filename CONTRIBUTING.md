# Contributing Guidelines

Thank you for contributing.

## Branching Strategy

The organization follows the Git Flow model.

### Permanent branches

- `develop` — Integration branch and default branch.
- `main` — Production branch.

### Working branches

Create work from `develop` using one of the approved prefixes:

```
feature/
bugfix/
hotfix/
release/
chore/
docs/
refactor/
test/
```

Examples:

```
feature/add-login
bugfix/fix-timeout
release/v1.2.0
```

## Pull Requests

All changes must be submitted through a Pull Request.

Direct pushes to protected branches are not permitted.

Before requesting review:

- Ensure CI passes.
- Update documentation where appropriate.
- Resolve merge conflicts.
- Complete the Pull Request template.

## Code Reviews

- Address review comments before merging.
- Resolve all review conversations.
- At least the required number of approvals must be obtained.

## Commit Guidelines

Write clear, descriptive commit messages.

Example:

```
Add login validation

Fix timeout when calling Graph API

Update onboarding documentation
```

## CI Requirements

Pull requests must pass all required status checks before merging.

## Questions

If you're unsure about a workflow or standard, contact the Engineering team before merging.