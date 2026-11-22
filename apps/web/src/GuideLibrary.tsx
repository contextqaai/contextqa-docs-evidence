import { useEffect, useState } from "react";
import { accessToken, request } from "./api";
import { Heading, Empty, SourceLink } from "./components";
import { PagesHandoff } from "./PagesHandoff";
import { ReviewedArticle } from "./ReviewedArticle";
import type { State } from "./types";

type Media = {
  digest: string;
  kind: string;
  path: string;
  run: number;
  step: number;
  revision: string;
  journey: string;
};
type Version = {
  digest: string;
  path: string;
  current: boolean;
  item: string;
  media: Media[];
};
type Detail = {
  body: string;
  media: Media[];
  previous_media: Media[];
  source: { source_url?: string; title: string; fixture?: boolean };
  diff: string;
  item: string;
};
type Asset = {
  id: string;
  path: string;
  digest: string;
  audience: string;
  format: string;
  body: string;
  version: number;
  status: string;
  exported_at: string | null;
  owner: string;
  stale: boolean;
};
function download(blob: Blob, file: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = file;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function GuideLibrary({
  prefix,
  state,
  open,
}: {
  prefix: string;
  state: State;
  open: (i: string) => void;
}) {
  const [data, setData] = useState<{
      versions: Version[];
      assets: Asset[];
    } | null>(null),
    [key, setKey] = useState(""),
    [detail, show] = useState<Detail | null>(null);
  const [tab, pick] = useState("Guides"),
    [error, fail] = useState(""),
    [epoch, reload] = useState(0),
    [busy, lock] = useState(false),
    [message, tell] = useState("");
  const [audience, setAudience] = useState(""),
    [format, setFormat] = useState("Training lesson"),
    [filter, search] = useState(""),
    [assetId, setAsset] = useState(""),
    [copy, edit] = useState("");
  const [image, setImage] = useState(""),
    [operation, choose] = useState("redact"),
    [rect, box] = useState([0, 0, 50, 30]),
    [derivative, setDerivative] = useState("");
  const [alias, setAlias] = useState(""),
    [removal, setRemoval] = useState(""),
    [reason, setReason] = useState(""),
    [verified, setVerified] = useState(false),
    [proposal, setProposal] = useState("");
  const [redirectFeedback, setRedirectFeedback] = useState<{
    key: string;
    role: "alert" | "status";
    text: string;
  } | null>(null);
  const versions = data?.versions || [],
    selected = versions.find((v) => v.path + "@" + v.digest === key);
  const asset = data?.assets.find((a) => a.id === assetId);
  useEffect(() => {
    let active = true;
    request(prefix + "/library")
      .then((r) => {
        if (active) {
          setData(r);
          if (!key && r.versions.length)
            setKey(r.versions[0].path + "@" + r.versions[0].digest);
        }
      })
      .catch((e) => {
        if (active) fail(e.message);
      });
    return () => {
      active = false;
    };
  }, [prefix, epoch]);
  const params = selected
    ? new URLSearchParams({
        path: selected.path,
        digest: selected.digest,
      }).toString()
    : "";
  useEffect(() => {
    show(null);
    setImage("");
    setDerivative("");
    if (!params) return;
    let active = true;
    request(prefix + "/library/version?" + params)
      .then((v) => {
        if (active) {
          show(v);
          setImage(
            v.media.find((m: Media) => m.kind === "screenshot")?.digest || "",
          );
        }
      })
      .catch((e) => {
        if (active) fail(e.message);
      });
    return () => {
      active = false;
    };
  }, [params, prefix]);
  async function act(fn: () => Promise<void>) {
    lock(true);
    fail("");
    tell("");
    try {
      await fn();
      reload((x) => x + 1);
    } catch (e) {
      fail((e as Error).message);
    } finally {
      lock(false);
    }
  }
  async function saveRedirect() {
    if (!selected) return;
    lock(true);
    setRedirectFeedback(null);
    try {
      await request(prefix + "/reader/redirects", { source: alias, target: selected.path });
      setRedirectFeedback({ key, role: "status", text: "Reader redirect saved." });
    } catch (e) {
      setRedirectFeedback({ key, role: "alert", text: (e as Error).message });
    } finally {
      lock(false);
    }
  }
  async function save(itemId: string) {
    const item = state.items[itemId];
    const heads = Object.fromEntries(
      item.changes
        .filter((c) => c.decision === "accepted")
        .map((c) => [
          c.path,
          versions.find((v) => v.current && v.path === c.path)?.digest || null,
        ]),
    );
    await request(prefix + "/library/save", {
      item: item.id,
      version: item.version,
      expected_heads: heads,
    });
    tell("Reviewed guide version saved.");
  }
  const eligible = Object.values(state.items).filter(
    (i) => i.approval && ["ready", "delivered"].includes(i.status),
  );
  return (
    <>
      <Heading
        title="Guide library"
        description="Read approved versions, inspect their evidence, and prepare release materials."
      />
      <div className="filters">
        {["Guides", "Evidence media", "Enablement"].map((t) => (
          <button key={t} aria-pressed={tab === t} onClick={() => pick(t)}>
            {t}
          </button>
        ))}
      </div>
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      {tab === "Guides" && (
        <section className="panel">
          <h2>Save an approved request</h2>
          {eligible.length ? (
            eligible.map((i) => (
              <div className="gate-row" key={i.id}>
                <button className="text-link" onClick={() => open(i.id)}>
                  {i.title}
                </button>
                <button
                  disabled={busy || !data}
                  onClick={() => void act(() => save(i.id))}
                >
                  Save guide version
                </button>
              </div>
            ))
          ) : (
            <p>
              Approve a request with linked ContextQA evidence to save its first
              guide version.
            </p>
          )}
        </section>
      )}
      {data && versions.length > 0 ? (
        <section className="panel">
          <label>
            Find a guide
            <input value={filter} onChange={(e) => search(e.target.value)} />
          </label>
          <label>
            Guide version
            <select value={key} onChange={(e) => setKey(e.target.value)}>
              <option value="">Choose a guide</option>
              {versions
                .filter((v) =>
                  v.path.toLowerCase().includes(filter.toLowerCase()),
                )
                .map((v) => (
                  <option
                    key={v.path + v.digest}
                    value={v.path + "@" + v.digest}
                  >
                    {v.path} · {v.digest.slice(0, 8)} ·{" "}
                    {v.current ? "Current" : "History"}
                  </option>
                ))}
            </select>
          </label>
          {detail && selected && tab === "Guides" && (
            <>
              {detail.source.fixture && <p>Workshop example using a recorded Ship 5 screenshot.</p>}
              <SourceLink url={detail.source.source_url}>
                Change source
              </SourceLink>
              <ReviewedArticle
                text={detail.body}
                prefix={prefix}
                item={detail.item}
                versionPath={selected.path}
                version={selected.digest}
              />
              <details>
                <summary>Compare with previous version</summary>
                <pre className="code-block">{detail.diff}</pre>
                <p>
                  {detail.previous_media.length} previous media references ·{" "}
                  {detail.media.length} current
                </p>
              </details>
              {selected.current && state.role === "admin" && (
                <PagesHandoff key={prefix + key} prefix={prefix} path={selected.path} version={selected.digest} />
              )}
              {selected.current && (
                <details>
                  <summary>Reader address and retirement</summary>
                  <label>
                    Old reader path
                    <input
                      value={alias}
                      disabled={busy}
                      onChange={(e) => {
                        setAlias(e.target.value);
                        setRedirectFeedback(null);
                      }}
                    />
                  </label>
                  <button
                    disabled={busy || !alias}
                    onClick={() => void saveRedirect()}
                  >
                    Add redirect to this guide
                  </button>
                  {redirectFeedback?.key === key && (
                    <p role={redirectFeedback.role}>{redirectFeedback.text}</p>
                  )}
                  <label>
                    Removal review request ID
                    <input
                      value={removal}
                      onChange={(e) => {
                        setRemoval(e.target.value);
                        setProposal("");
                      }}
                    />
                  </label>
                  <label>
                    Reason
                    <textarea
                      value={reason}
                      onChange={(e) => {
                        setReason(e.target.value);
                        setProposal("");
                      }}
                    />
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={verified}
                      onChange={(e) => {
                        setVerified(e.target.checked);
                        setProposal("");
                      }}
                    />
                    A signed product change and reviewed replay confirm the task
                    was removed
                  </label>
                  <button
                    disabled={busy || !removal || reason.length < 4}
                    onClick={() =>
                      void act(async () => {
                        const k = selected.digest + removal + reason;
                        const r = await request(prefix + "/reader/retire", {
                          path: selected.path,
                          version: selected.digest,
                          item: removal,
                          reason,
                          confirmed_task_removal: verified,
                          confirm_retirement: proposal === k,
                        });
                        setProposal(r.status === "proposed" ? k : "");
                        tell(
                          r.status +
                            " · " +
                            (r.incoming_links || []).length +
                            " incoming links · " +
                            (r.derived_assets || []).length +
                            " dependent materials",
                        );
                      })
                    }
                  >
                    {proposal === selected.digest + removal + reason
                      ? "Confirm retirement"
                      : verified
                        ? "Review retirement impact"
                        : "Record investigation"}
                  </button>
                </details>
              )}
            </>
          )}
          {detail && selected && tab === "Evidence media" && (
            <>
              <h2>Capture references</h2>
              {detail.media.map((m, n) => (
                <p key={m.digest + n}>
                  {m.kind} · {m.journey} · run {m.run} · step {m.step} ·{" "}
                  {m.revision.slice(0, 8)}
                </p>
              ))}
              {image && (
                <fieldset disabled={busy}>
                  <legend>Edit a screenshot</legend>
                  <label>
                    Original screenshot
                    <select
                      value={image}
                      onChange={(e) => {
                        setImage(e.target.value);
                        setDerivative("");
                      }}
                    >
                      {detail.media
                        .filter((m) => m.kind === "screenshot")
                        .map((m, n) => (
                          <option key={n} value={m.digest}>
                            Run {m.run} · Step {m.step}
                          </option>
                        ))}
                    </select>
                  </label>
                  <label>
                    Operation
                    <select
                      value={operation}
                      onChange={(e) => choose(e.target.value)}
                    >
                      {["redact", "crop", "outline"].map((o) => (
                        <option key={o}>{o}</option>
                      ))}
                    </select>
                  </label>
                  <div className="writing-actions">
                    {["Left", "Top", "Width", "Height"].map((l, i) => (
                      <label key={l}>
                        {l}
                        <input
                          type="number"
                          min={i < 2 ? 0 : 1}
                          value={rect[i]}
                          onChange={(e) =>
                            box(
                              rect.map((v, j) =>
                                j === i ? Number(e.target.value) : v,
                              ),
                            )
                          }
                        />
                      </label>
                    ))}
                  </div>
                  <button
                    onClick={() =>
                      void act(async () => {
                        const r = await request(prefix + "/media/edits", {
                          path: selected.path,
                          version: selected.digest,
                          image,
                          operation,
                          box: {
                            x: rect[0],
                            y: rect[1],
                            width: rect[2],
                            height: rect[3],
                          },
                        });
                        setDerivative(r.id);
                        tell(
                          "Edited image saved with its original and rectangle.",
                        );
                      })
                    }
                  >
                    Create edited image
                  </button>
                  {derivative && (
                    <button
                      onClick={() =>
                        void act(async () => {
                          const r = await fetch(
                            "/api/" + prefix + "/media/edits/" + derivative,
                            {
                              headers: {
                                Authorization:
                                  "Bearer " + (await accessToken()),
                              },
                            },
                          );
                          if (!r.ok) throw Error("Edited image unavailable.");
                          download(await r.blob(), "reviewed-image.png");
                        })
                      }
                    >
                      Download edited PNG
                    </button>
                  )}
                </fieldset>
              )}
            </>
          )}
          {detail && selected && tab === "Enablement" && (
            <fieldset disabled={busy || !selected.current}>
              <legend>Create material from this guide</legend>
              <label>
                Audience
                <input
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                />
              </label>
              <label>
                Format
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                >
                  <option>Training lesson</option>
                  <option>Release note</option>
                </select>
              </label>
              <button
                disabled={!audience.trim()}
                onClick={() =>
                  void act(async () => {
                    const r = await request(prefix + "/library/assets", {
                      path: selected.path,
                      digest: selected.digest,
                      audience,
                      format,
                    });
                    setAsset("");
                    tell("Material ready for owner review.");
                    setAsset(r.id);
                  })
                }
              >
                Generate material
              </button>
            </fieldset>
          )}
        </section>
      ) : data ? (
        <Empty title="No saved guide versions">
          A guide appears here after an editor saves its approved text and
          reviewed media.
        </Empty>
      ) : (
        !error && <p role="status">Loading guide versions…</p>
      )}
      {tab === "Enablement" && data && (
        <section className="panel">
          <h2>Owner review</h2>
          {data.assets.map((a) => (
            <button
              key={a.id}
              onClick={() => {
                setAsset(a.id);
                edit(a.body);
              }}
            >
              {a.format} · {a.audience} ·{" "}
              {a.stale ? "Source updated" : a.status}
            </button>
          ))}
          {asset?.stale && asset.owner === state.actor && (
            <button
              disabled={busy}
              onClick={() =>
                void act(async () => {
                  const r = await request(
                    prefix + "/library/assets/" + asset.id,
                    { version: asset.version, action: "refresh" },
                  );
                  setAsset(r.id);
                  edit("");
                  tell("Refresh draft created.");
                })
              }
            >
              Refresh from current guide
            </button>
          )}
          {asset && (
            <section aria-label="Material preview">
              <h3>Material preview</h3>
              <ReviewedArticle text={copy || asset.body} prefix={prefix} item={asset.id}
                versionPath={asset.path} version={asset.digest} />
            </section>
          )}
          {asset && (
            <fieldset
              disabled={busy || asset.stale || asset.owner !== state.actor}
            >
              <legend>
                {asset.format} for {asset.audience}
              </legend>
              <textarea
                aria-label="Material text"
                rows={12}
                value={copy || asset.body}
                onChange={(e) => edit(e.target.value)}
              />
              {["save", "approve", "export"].map((a) => (
                <button
                  key={a}
                  disabled={
                    (a === "export" && asset.status !== "approved") ||
                    (a !== "save" && !!copy && copy !== asset.body)
                  }
                  onClick={() =>
                    void act(async () => {
                      const r = await request(
                        prefix + "/library/assets/" + asset.id,
                        {
                          version: asset.version,
                          action: a,
                          ...(a === "save" ? { body: copy || asset.body } : {}),
                        },
                      );
                      if (a === "export") download(r, "reviewed-material.zip");
                      tell(
                        a === "export"
                          ? "Exported with reviewed evidence."
                          : "Owner decision saved.",
                      );
                    })
                  }
                >
                  {a === "save"
                    ? "Save changes"
                    : a === "approve"
                      ? "Approve material"
                      : "Export material"}
                </button>
              ))}
            </fieldset>
          )}
        </section>
      )}
    </>
  );
}
