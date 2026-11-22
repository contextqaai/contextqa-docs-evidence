import { useEffect, useState } from "react";
import { request } from "./api";
import { Heading } from "./components";
type Hit = {
  title: string;
  excerpt: string;
  kind: string;
  citation: {
    item?: string;
    path?: string;
    version?: string;
    article?: string;
  };
};
export function Ask({
  prefix,
  open,
}: {
  prefix: string;
  open: (id: string) => void;
}) {
  const [q, change] = useState(""),
    [hits, show] = useState<Hit[] | null>(null),
    [keys, setKeys] = useState<
      { id: string; label: string; expires_at: string }[]
    >([]),
    [label, name] = useState(""),
    [key, issue] = useState(""),
    [error, fail] = useState(""),
    [busy, lock] = useState(false);
  const [goal, setGoal] = useState(""),
    [source, setSource] = useState(""),
    [requestId, setRequestId] = useState("");
  async function list() {
    setKeys(await request(prefix + "/ask/keys"));
  }
  useEffect(() => {
    list().catch((e) => fail(e.message));
  }, [prefix]);
  async function act(f: () => Promise<void>) {
    lock(true);
    fail("");
    try {
      await f();
    } catch (e) {
      fail((e as Error).message);
    } finally {
      lock(false);
    }
  }
  return (
    <>
      <Heading
        title="Ask documentation"
        description="Search accessible requests and reviewed guides for answers with sources."
      />
      <form
        className="panel"
        onSubmit={(e) => {
          e.preventDefault();
          void act(async () =>
            show((await request(prefix + "/ask", { question: q })).results),
          );
        }}
      >
        <label>
          Question
          <input
            value={q}
            onChange={(e) => change(e.target.value)}
            required
            minLength={2}
          />
        </label>
        <button disabled={busy}>Find sources</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {hits && (
        <section className="panel">
          <h2>Matching sources</h2>
          {!hits.length && <p>No accessible source matched this question.</p>}
          {hits.map((h, n) => (
            <article key={n}>
              <h3>{h.title}</h3>
              <p>{h.excerpt}</p>
              <small>
                {h.kind} · {h.citation.path || h.citation.article} ·{" "}
                {h.citation.version}
              </small>
              {h.citation.item && (
                <button onClick={() => open(h.citation.item!)}>
                  Open request
                </button>
              )}
            </article>
          ))}
        </section>
      )}
      {hits?.some((h) => h.citation.item) && (
        <details className="panel">
          <summary>Propose documentation work</summary>
          <label>
            Source request
            <select
              value={source}
              onChange={(e) => {
                setSource(e.target.value);
                setRequestId(crypto.randomUUID());
              }}
            >
              <option value="">Select a source</option>
              {hits
                .filter((h) => h.citation.item)
                .map((h, n) => (
                  <option key={n} value={h.citation.item}>
                    {h.title}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Requested outcome
            <input
              value={goal}
              onChange={(e) => {
                setGoal(e.target.value);
                setRequestId(crypto.randomUUID());
              }}
            />
          </label>
          <button
            disabled={busy || !source || goal.trim().length < 3}
            onClick={() =>
              void act(async () => {
                const r = await request(prefix + "/ask/propose", {
                  request_id: requestId,
                  source_item: source,
                  goal,
                });
                open(r.item_id);
              })
            }
          >
            Create review request
          </button>
        </details>
      )}
      <details className="panel">
        <summary>CLI and assistant access</summary>
        <p>
          A reader key can search the sources visible to your account. It
          expires after 30 days.
        </p>
        <label>
          Connection name
          <input value={label} onChange={(e) => name(e.target.value)} />
        </label>
        <button
          disabled={busy || !label.trim()}
          onClick={() =>
            void act(async () => {
              const r = await request(prefix + "/ask/keys", { label });
              issue(r.key);
              await list();
            })
          }
        >
          Create reader key
        </button>
        {key && (
          <div>
            <label>
              Copy this key into your secret manager
              <input
                readOnly
                type="password"
                value={key}
                onFocus={(e) => e.target.select()}
              />
            </label>
            <button onClick={() => issue("")}>Hide key</button>
          </div>
        )}
        {keys.map((k) => (
          <div className="gate-row" key={k.id}>
            <span>
              {k.label} · expires {k.expires_at.slice(0, 10)}
            </span>
            <button
              disabled={busy}
              onClick={() =>
                void act(async () => {
                  await request(prefix + "/ask/keys/" + k.id + "/revoke", {});
                  issue("");
                  await list();
                })
              }
            >
              Revoke
            </button>
          </div>
        ))}
      </details>
    </>
  );
}
