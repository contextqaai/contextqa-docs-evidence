# Documentation agent without a running application

Use the repository CLI to turn a committed code change into reviewable documentation files. Python 3.10+ and Git are sufficient for planning and preparation; no web server, React build or PostgreSQL service is required.

1. Map documentation paths to source paths in a manifest. Both `.md` and `.mdx` are supported. See `examples/kan-pr15/developer-manifest.json`.
2. Create a source-bound plan using full base and head commit SHAs.
3. Write a proposal from the source diff, or use your coding agent to draft it against that plan. Keep unsupported behavior as questions. The prepare command does not itself call an LLM.
4. Prepare a new output directory containing article drafts, `changes.patch`, the plan/proposal, `receipt.json`, and a local review database.
5. Collect relevant existing ContextQA evidence, review media, resolve questions and approve the changes before delivery. The draft patch is not a bypass for those requirements.

Run from this repository:

```sh
python3 -m cqa_artifacts.agent plan \
  --repo /absolute/path/to/source-repo \
  --config /absolute/path/to/manifest.json \
  --base FULL_BASE_SHA --head FULL_HEAD_SHA \
  --source-url https://github.com/OWNER/REPO/pull/NUMBER \
  --out /absolute/path/to/new-plan.json
python3 -m cqa_artifacts.agent prepare \
  --plan /absolute/path/to/new-plan.json \
  --proposal /absolute/path/to/proposal.json \
  --out /absolute/path/to/new-review-directory
```

The output directory must not already exist. Preparation neither starts ContextQA tests nor submits changes remotely. `submit` is optional for teams using the hosted review console. For a developer workflow, run planning after a PR diff changes and attach the resulting patch and review receipt to the normal code review process. Publication still requires evidence and editor approval.

For saved journey registration, maintenance, result selection, screenshot/video retrieval and evidence-backed refresh, use the [journey agent workflow](journey-agent.md).
