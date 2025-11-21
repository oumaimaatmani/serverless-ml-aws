# Contributing Guidelines

## Branch Strategy
- main (stable)
- feature/* (new features)
- fix/* (bug fixes)
- docs/* (documentation improvements)

## Workflow
```bash
git checkout -b feature/your-feature
# make changes
git commit -m "feat: concise description"
git push origin feature/your-feature
```

Open a Pull Request and ensure:
- Code is formatted
- No secrets committed
- Documentation updated if behavior changes

## Code Style
- Python: keep functions small, prefer explicit returns
- JavaScript: modern ES modules, no unused console logs
- Terraform: group resources logically, use descriptive tags

## Commit Message Prefixes
- feat:
- fix:
- docs:
- refactor:
- chore:
- test:
- ci:

## Tests
If adding logic inside Lambda handlers, prefer factoring logic into helper functions and unit test with pytest + moto (future expansion).

## Security
Never commit AWS credentials. Use environment variables or Terraform-managed state.

## Review Checklist
- Error handling (no silent failures)
- Clear logging (no sensitive data)
- Performance acceptable (no unnecessary loops)