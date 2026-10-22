---
description: Find outdated and vulnerable dependencies and turn them into upgrade batches for the dev agent
agent: deps
subagent: true
---
Check the project's dependencies.

Scope, if given (an ecosystem, a folder, or a package):

$ARGUMENTS

Manifests and lockfiles in this repository:

!`git ls-files 2>/dev/null | grep -E '(^|/)(package\.json|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lockb?|requirements[^/]*\.txt|pyproject\.toml|poetry\.lock|uv\.lock|go\.mod|Cargo\.toml|Cargo\.lock|[^/]*\.csproj|Gemfile|Gemfile\.lock|composer\.json|Dockerfile[^/]*|\.nvmrc|\.python-version|\.tool-versions)$|^\.github/workflows/' | head -60`
