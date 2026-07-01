---
title: GitHub REST API
base_url: https://api.github.com
version: "2022-11-28"
description: GitHub REST API — repositories, issues, PRs, and actions.
auth: "Bearer <GITHUB_TOKEN>  (headers: Authorization + Accept: application/vnd.github+json)"
tags: [github, git, devops]
created: 2026-06-30
updated: 2026-06-30
---

All requests need two headers:
- `Authorization: Bearer <your_token>`
- `Accept: application/vnd.github+json`

::: endpoint
method: GET
path: /repos/{owner}/{repo}
title: Get Repository
description: Returns metadata for a single repository.

param: owner | path | string | required | GitHub username or organisation name
param: repo  | path | string | required | Repository name

response: 200 | Success
{
  "id": 1296269,
  "name": "Hello-World",
  "full_name": "octocat/Hello-World",
  "private": false,
  "html_url": "https://github.com/octocat/Hello-World",
  "description": "My first repository",
  "default_branch": "main",
  "open_issues_count": 3,
  "stargazers_count": 80
}

response: 404 | Not Found
{"message": "Not Found", "documentation_url": "https://docs.github.com/..."}
:::

::: endpoint
method: GET
path: /repos/{owner}/{repo}/issues
title: List Issues
description: Lists issues for a repository. Pull requests are also returned as issues.

param: owner  | path  | string  | required | Repository owner
param: repo   | path  | string  | required | Repository name
param: state  | query | string  | optional | open, closed, or all (default: open)
param: labels | query | string  | optional | Comma-separated label names
param: sort   | query | string  | optional | created, updated, comments (default: created)
param: per_page| query | integer | optional | Results per page (max 100, default 30)
param: page   | query | integer | optional | Page number (default: 1)

response: 200 | Success
[
  {
    "id": 1,
    "number": 42,
    "title": "Found a bug",
    "state": "open",
    "user": {"login": "octocat"},
    "labels": [{"name": "bug"}],
    "created_at": "2024-01-01T00:00:00Z"
  }
]
:::

::: endpoint
method: POST
path: /repos/{owner}/{repo}/issues
title: Create Issue
description: Creates a new issue. Requires push access to the repository.

param: owner    | path | string | required | Repository owner
param: repo     | path | string | required | Repository name
param: title    | body | string | required | Issue title
param: body     | body | string | optional | Issue body (markdown supported)
param: labels   | body | array  | optional | Array of label names
param: assignees| body | array  | optional | Array of GitHub usernames to assign

response: 201 | Created
{
  "id": 1,
  "number": 43,
  "title": "New issue title",
  "html_url": "https://github.com/owner/repo/issues/43",
  "state": "open"
}

response: 422 | Validation Failed
{"message": "Validation Failed", "errors": [{"field": "title", "code": "missing"}]}
:::

::: endpoint
method: GET
path: /repos/{owner}/{repo}/actions/runs
title: List Workflow Runs
description: Lists workflow runs for a repository.

param: owner    | path  | string  | required | Repository owner
param: repo     | path  | string  | required | Repository name
param: status   | query | string  | optional | completed, action_required, cancelled, failure, neutral, skipped, stale, success, timed_out, in_progress, queued, requested, waiting
param: branch   | query | string  | optional | Filter by branch name
param: per_page | query | integer | optional | Results per page (max 100)
param: page     | query | integer | optional | Page number

response: 200 | Success
{
  "total_count": 2,
  "workflow_runs": [
    {
      "id": 30433642,
      "name": "CI",
      "status": "completed",
      "conclusion": "success",
      "head_branch": "main",
      "created_at": "2024-01-01T00:00:00Z",
      "html_url": "https://github.com/owner/repo/actions/runs/30433642"
    }
  ]
}
:::

::: endpoint
method: POST
path: /repos/{owner}/{repo}/pulls
title: Create Pull Request
description: Creates a pull request. Requires write access to the repository.

param: owner  | path | string | required | Repository owner
param: repo   | path | string | required | Repository name
param: title  | body | string | required | PR title
param: body   | body | string | optional | PR description (markdown)
param: head   | body | string | required | Branch name of the PR source
param: base   | body | string | required | Branch to merge into (e.g. main)
param: draft  | body | boolean| optional | Create as draft PR (default: false)

response: 201 | Created
{
  "number": 5,
  "title": "My PR",
  "state": "open",
  "draft": false,
  "html_url": "https://github.com/owner/repo/pull/5",
  "head": {"ref": "feature-branch"},
  "base": {"ref": "main"}
}

response: 422 | Validation Failed — e.g. head branch same as base
{"message": "Validation Failed"}
:::
