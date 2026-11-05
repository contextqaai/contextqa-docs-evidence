# ContextQA Docs Evidence

For **solutions engineers and technical writers**: turn selected ContextQA workflow evidence into reviewed guides, then compare versions when the application changes.

[Usage guide](docs/how-to-use.md) · [Technical guide](docs/POWERFUL.md) · [Capture and refresh](docs/capture-and-refresh.md) · [Proof status](docs/documentation-proof.md)

![ContextQA Docs Evidence: contextqa → assemble → review → export. Refresh requires a new review.](assets/readme/overview.svg)

## Try it locally

Requires **Python 3.10+**; no runtime dependencies. From the repository root, choose a fresh output path:

```sh
python3 examples/contextqa_demo.py /tmp/NEW-contextqa-guide-preview
```

This is an **account-free API simulation**, not a live run or screenshot capture. For real evidence, follow the [usage guide](docs/how-to-use.md) and [API setup](docs/contextqa-api.md).

**Know the boundary:** review selected content and media before export. Standalone capture needs a separate producer; automatic recapture, semantic visual diff and native partner publishing are not implemented. [Kan evidence and remaining gates](docs/documentation-proof.md) are scoped separately.

**Private candidate:** no open-source license or public release yet. Optional AI and hosted execution use separate credentials and may incur charges.

[Developer instructions](AGENTS.md) · [Security and publication](docs/security.md) · [Capability evidence](docs/capability-register.md)
