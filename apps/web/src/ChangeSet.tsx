import { useState } from "react";
import type { Item, State } from "./types";
import { ReviewedArticle } from "./ReviewedArticle";

export function ChangeSet({
  item,
  state,
  prefix,
  busy,
  mutate,
}: {
  item: Item;
  state: State;
  prefix?: string;
  busy: boolean;
  mutate: (a: string, d: unknown, m: string) => Promise<unknown>;
}) {
  const accepted = item.changes.filter((c) => c.decision === "accepted");
  const [fix, setFix] = useState(""),
    [body, setBody] = useState(""),
    [target, setTarget] = useState(""),
    [problem, setProblem] = useState("");
  const targetArticle = state.articles[target];
  const locked = ["archived", "resolved", "delivered"].includes(item.status);
  return (
    <section className="document-content">
      <h2>Accepted output</h2>
      {accepted.length ? (
        accepted.map((c) => (
          <details key={c.id}>
            <summary>{c.path}</summary>
            <ReviewedArticle prefix={prefix} item={item.id} change={c.id} text={c.after} />
          </details>
        ))
      ) : (
        <p>Accept an article to include it in this preview.</p>
      )}
      <h3>Baseline conflicts</h3>
      {!item.changes.some(
        (c) => (state.articles[c.path]?.body || "") !== c.before,
      ) && <p>All proposals match the current article baselines.</p>}
      {item.changes
        .filter((c) => (state.articles[c.path]?.body || "") !== c.before)
        .map((c) => (
          <div key={c.id}>
            <p>
              <code>{c.path}</code> ·{" "}
              {state.articles[c.path]
                ? c.before
                  ? "The imported article changed."
                  : "An article was added at this path."
                : "The original path is missing."}
            </p>
            {state.role !== "contributor" && !locked && (
              <button
                onClick={() => {
                  setFix(c.id);
                  setBody(c.after);
                  setTarget(c.path);
                  setProblem("");
                }}
              >
                Resolve conflict
              </button>
            )}
            {fix === c.id && (
              <fieldset disabled={busy}>
                <label>
                  Destination path
                  <input
                    value={target}
                    onChange={(e) => setTarget(e.target.value)}
                  />
                </label>
                <details open>
                  <summary>Current baseline</summary>
                  <pre>{targetArticle?.body || "New path"}</pre>
                </details>
                <label>
                  Resolved article
                  <textarea
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    rows={12}
                  />
                </label>
                {problem && <p role="alert">{problem}</p>}
                <button onClick={() => setFix("")}>Cancel</button>
                <button
                  onClick={async () => {
                    try {
                      await mutate(
                        "review",
                        {
                          item_id: item.id,
                          version: item.version,
                          action: "reconcile",
                          data: {
                            change_id: c.id,
                            path: target,
                            after: body,
                            base_digest: targetArticle?.digest || null,
                          },
                        },
                        "Conflict resolved. Review the updated article.",
                      );
                      setFix("");
                    } catch (e) {
                      setProblem((e as Error).message);
                    }
                  }}
                >
                  Save resolution
                </button>
              </fieldset>
            )}
          </div>
        ))}
    </section>
  );
}
