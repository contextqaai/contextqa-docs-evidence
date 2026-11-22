import { useState, useEffect } from "react";
import { request } from "./api";
import { Heading, SourceLink } from "./components";
type Stats = {
  repo: string;
  branch: string;
  root: string;
  connected: boolean;
  role: string;
  media_files: number;
  media_bytes: number;
  groups: Record<string, Record<string, number>>;
  refresh: {
    path: string;
    revision: string;
    item: string;
    journeys: string[];
    base_current: boolean;
    status?: string;
    reason?: string;
    proposal?: string;
  }[];
  phases?: {
    item: string;
    phase: string;
    revision: string;
    successful?: string;
  }[];
  deliveries: { item: string; status: string; url: string | null }[];
};
export function Operations({
  prefix,
  open,
}: {
  prefix: string;
  open: (i: string) => void;
}) {
  const [stats, load] = useState<Stats | null>(null),
    [error, fail] = useState(""),
    [message, tell] = useState(""),
    [busy, lock] = useState(false);
  const [item, setItem] = useState(""),
    [base, setBase] = useState(""),
    [consent, confirm] = useState(false);
  const [path, setPath] = useState("api/reference.md"),
    [reference, setRef] = useState(""),
    [input, setInput] = useState("");
  async function refresh() {
    load(await request(prefix + "/operations"));
  }
  useEffect(() => {
    refresh().catch((e) => fail(e.message));
  }, [prefix]);
  async function act(f: () => Promise<void>) {
    lock(true);
    fail("");
    try {
      await f();
      await refresh();
    } catch (e) {
      fail((e as Error).message);
    } finally {
      lock(false);
    }
  }
  return (
    <>
      <Heading
        title="Documentation operations"
        description="Inspect refresh requests, destination receipts and stored guide evidence."
      >
        <button disabled={busy} onClick={() => void act(refresh)}>
          Refresh status
        </button>
      </Heading>
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      {stats && (
        <>
          <section className="panel">
            <h2>GitBook repository destination</h2>
            <p>
              {stats.connected
                ? stats.repo +
                  " · " +
                  stats.branch +
                  " · " +
                  (stats.root || "repository root")
                : "Connect the documentation repository in Workspace settings."}
            </p>
            <p>
              Git Sync uses the reviewed documentation branch. GitBook manages
              synchronization and site publication.
            </p>
            {stats.role === "admin" && stats.connected && (
              <>
                <button
                  disabled={busy}
                  onClick={() =>
                    void act(async () => {
                      const r = await request(prefix + "/gitbook/check", {});
                      tell(
                        "Verified GitBook root " +
                          (r.root || "/") +
                          " at " +
                          r.revision,
                      );
                    })
                  }
                >
                  Check GitBook root
                </button>
                <details>
                  <summary>Create a reviewed draft pull request</summary>
                  <label>
                    Approved request ID
                    <input
                      value={item}
                      onChange={(e) => setItem(e.target.value)}
                    />
                  </label>
                  <label>
                    Reviewed documentation base SHA
                    <input
                      value={base}
                      onChange={(e) => setBase(e.target.value)}
                    />
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={consent}
                      onChange={(e) => confirm(e.target.checked)}
                    />
                    Create a draft pull request for this approved revision
                  </label>
                  <button
                    disabled={
                      busy || !consent || !item || !/^[0-9a-f]{40}$/.test(base)
                    }
                    onClick={() =>
                      void act(async () => {
                        const r = await request(
                          prefix + "/operations/draft-pr",
                          { item, base_sha: base, confirm: consent },
                        );
                        tell(r.url || r.status);
                        confirm(false);
                      })
                    }
                  >
                    Create draft pull request
                  </button>
                </details>
              </>
            )}
            {stats.phases?.map((p) => (
              <p key={p.item + p.phase}>
                {p.item} · {p.phase} · {p.revision.slice(0, 10)}{" "}
                {p.successful === "false" ? "failed" : ""}
              </p>
            ))}
            {stats.deliveries.map((d) => (
              <div key={d.item} className="gate-row">
                <button onClick={() => open(d.item)}>Open request</button>
                <span>{d.status}</span>
                {d.status === "merged" && stats.role === "admin" && (
                  <button
                    disabled={busy}
                    onClick={() =>
                      void act(async () => {
                        const r = await request(
                          prefix + "/publication/" + d.item + "/verify",
                          {},
                        );
                        tell("Verified " + r.files + " live files");
                      })
                    }
                  >
                    Verify live site
                  </button>
                )}
                {d.url && <SourceLink url={d.url}>Pull request</SourceLink>}
                {stats.role === "admin" && (
                  <button
                    disabled={busy}
                    onClick={() =>
                      void act(async () => {
                        const r = await request(
                          prefix + "/operations/reconcile/" + d.item,
                          {},
                        );
                        tell("GitHub receipt: " + r.status);
                      })
                    }
                  >
                    Reconcile with GitHub
                  </button>
                )}
              </div>
            ))}
          </section>
          <section className="panel">
            <h2>Refresh queue</h2>
            {stats.refresh.length ? (
              stats.refresh.map((x) => (
                <div className="gate-row" key={x.path + x.revision}>
                  <div>
                    <strong>{x.path}</strong>
                    <p>
                      {x.revision.slice(0, 10)} · {x.journeys.join(", ")} ·{" "}
                      {x.status ||
                        (x.base_current
                          ? "Review required"
                          : "Baseline advanced")}{" "}
                      {x.reason}
                    </p>
                  </div>
                  <button onClick={() => open(x.proposal || x.item)}>
                    Review change
                  </button>
                </div>
              ))
            ) : (
              <p>No signed product changes have matched a saved guide.</p>
            )}
          </section>
          <section className="panel">
            <h2>Worker activity</h2>
            {Object.entries(stats.groups).map(([g, v]) => (
              <p key={g}>
                {g.replace("_", " ")} ·{" "}
                {Object.entries(v)
                  .map(([s, n]) => n + " " + s)
                  .join(", ") || "No jobs"}
              </p>
            ))}
            <p>
              {stats.media_files} verified files ·{" "}
              {stats.media_bytes.toLocaleString()} bytes
            </p>
          </section>
          <section className="panel">
            <h2>Import API reference</h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void act(async () => {
                  const r = await request(prefix + "/operations/import-api", {
                    path,
                    reference,
                    spec: JSON.parse(input),
                  });
                  tell(
                    r.status + " · " + r.skipped.length + " entries skipped",
                  );
                  if (r.item_id) open(r.item_id);
                });
              }}
            >
              <label>
                Article path
                <input
                  value={path}
                  onChange={(e) => setPath(e.target.value)}
                  required
                />
              </label>
              <label>
                Specification source URL
                <input
                  type="url"
                  value={reference}
                  onChange={(e) => setRef(e.target.value)}
                  required
                />
              </label>
              <label>
                OpenAPI 3 JSON
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  required
                  rows={5}
                />
              </label>
              <button disabled={busy}>Create review request</button>
            </form>
          </section>
        </>
      )}
    </>
  );
}
