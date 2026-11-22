# M03 acceptance and import scope

M03 adds a repository preview to **Knowledge base**. Editors and administrators can import the existing documentation from the repository, branch and directory selected in M02. Every file read belongs to one commit. Confirming the preview adds usable baselines to the same store the review and guide-writing workflows use. A missing page in a listing never authorizes deletion.

## Existing repository check

A separate local workspace imported eight existing articles from `contextqaai/contextqa-docs-evidence`, branch `main`, directory `docs/salesforce/guides`, at commit `1d62a9a1fe5fcdcdc6ca573e782bdaad07f523df`. The API returned eight created and zero skipped. Its persisted receipt and article count were checked through the running app. This sample used public GitHub API reads without a credential. The customer workflow uses the M02 GitHub installation binding. The sample has no active installation connection. [Pinned source directory](https://github.com/contextqaai/contextqa-docs-evidence/tree/1d62a9a1fe5fcdcdc6ca573e782bdaad07f523df/docs/salesforce/guides)

## Acceptance criteria

| Criterion | Verification |
|---|---|
| AC-1 · Nested paths, shared titles and local images | Database-backed HTTP tests imported two articles titled Getting started at different paths. They have distinct IDs. The local figure endpoint returned the verified PNG. A second import retained both IDs. |
| AC-2 · Incomplete or interrupted reads | A truncated Git tree stopped the preview. A temporary blob failure left previously read files available to resume. Attempting to apply the partial job failed. An omitted page survived a subsequent completed import. |
| AC-3 · File-level diagnostics and static content | Invalid navigation JSON, invalid navigation text and interactive MDX were skipped. Valid pages in the same preview remained importable. The parser reads Markdown and a static subset of MDX as text. |
| AC-4 · Unchanged and changed content | Reapplying identical content yielded two unchanged articles. Changing one page created version 2 for its existing ID. The database retained all three original and revised versions across both articles. A stale preview and a conflicting manual edit were protected. |
| AC-5 · Independent addresses | The team article retained source `docs/teams/setup.mdx`, reader path `/team-onboarding` and navigation group **Team guides**. An additional test verified that a shared reader path raises a preview warning. |
| Authorization | Downgrading an editor to contributor denied preview, apply and figure access. A different organization could not read the import. |

All 244 local checks passed across the Python domain suite (193), hosted API, identity and PostgreSQL suite (23), React suite (14), legacy UI suite (4), and offline AI transport suite (10). The TypeScript and Vite production build passed.

## Supported input and recovery

- The importer reads regular Markdown and static MDX files from a pinned Git tree. It checks each downloaded Git blob against its object ID. It interprets root-level Mintlify `docs.json` and `mint.json` navigation. Other recognized site configurations get a format notice. Custom components, expressions and JavaScript configuration require separate review. [GitHub tree API](https://docs.github.com/en/rest/git/trees) · [GitHub blob API](https://docs.github.com/en/rest/git/blobs)
- Flat front matter supplies title, slug or permalink. Without an explicit reader path, the inventory derives one from the relative filename. The article detail shows this path, its navigation group, repository path, version and commit. The preview is an inventory of source documentation. Verifying public website routing is a separate publication check.
- Local Markdown figure references resolve inside the configured directory. PNG, JPEG and WebP are supported. The importer does not fetch external image URLs. A missing local figure is shown as unavailable.
- One preview supports up to 500 supported files and 12 MB total readable content. Individual text files are limited to 100 KB and raster images to 512 KB. For larger repositories, select a smaller directory. Existing baselines from an older import or a different directory are retained.
- Reopening **Knowledge base** restores the latest import receipt or in-progress read. **Resume reading files** continues the pinned preview after an interrupted file read. If the tree listing itself was incomplete, choose **Preview repository** again. If someone edits an article after preview or changes the GitHub scope, obtain a fresh preview before applying.
- This module inventories what already exists. Scheduled or push-triggered inventory refresh belongs to the workflow automation modules. A live private installation with a client-owned repository remains a customer acceptance check.


## Ship 5 verification

The isolated preview served the compiled application and used the production import endpoints against PostgreSQL. A deterministic GitHub transport supplied the synthetic source tree, its blobs and one truncated listing. The browser used a synthetic editor session. All three exploratory cases passed on the initial bundle. The saved cases were replayed with the final M03 bundle `index-CaWNtHsg.js` from implementation commit `d6ddf62`.

| Saved case | Results | Observations |
|---|---|---|
| 204 · Import and inspect | 469 initial, 473 final | The desktop replay passed 17 steps. The editor previewed two shared-title pages, imported them, searched by path, checked source/reader/navigation/version metadata and inspected a local PNG. |
| 205 · Incomplete listing and retry | 470 initial, 472 final | The desktop replay passed 17 steps. The expected error left the old inventory visible. A new preview identified both unsupported files, reimport reported two unchanged and two skipped, and a missing search showed the empty result. |
| 206 · Mobile article selection | 468 initial, 471 final | The 390 × 844 replay passed 13 steps. It imported the two pages, selected the admin path, inspected its source and version, then returned to the matching inventory entry. |

The trace confirms a 1280 × 720 CSS viewport for results 472 and 473. The capture proxy omitted the sidebar logo asset. Its empty image is visible in the captures. Rendered contrast, keyboard-only navigation, large customer repositories and real private-installation authorization have separate acceptance needs.

Guide disposition is **create**. The earlier guide documented the empty knowledge-base screen. The [repository import guide](m03-walkthrough.md) adds preview, import, article lookup, figure inspection and recovery using the successful runs. The linked receipts preserve original screenshot and recording checksums. Publication to a customer repository remains a separate reviewed operation.

Case 207, result 474, step result 857, also passed on the final M03 build. The browser verified the original admin article at version 1, an import with one updated and one unchanged, the new admin paragraph at version 2, and the team article still at version 1. [Version-change evidence](m03-evidence/changed-baseline-provenance.json)

Ship 5's available balance moved from 14,764 to 14,746 credits over these seven M03 executions, a difference of 18 against the 1,000-credit module allowance. This is a tenant balance comparison measured before starting M04.
