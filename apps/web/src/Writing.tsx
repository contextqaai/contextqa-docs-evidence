import { useEffect, useState } from "react";
import { request } from "./api";
import type { Item, State } from "./types";
import type { Profile } from "./WritingProfile";
export type Brief = {
  profile_revision?: number;
  path: string;
  template: string;
  audience: string;
  goal: string;
  prerequisite: string;
  fact: string;
  source: string;
  recovery: string;
  capture: string | null;
};
export type WritingRound = {
  brief: Brief;
  status: string;
  missing: string[];
  report?: { blockers: string[] };
};
type Props = {
  item: Item;
  state: State;
  prefix?: string;
  busy: boolean;
  mutate: (a: string, d: unknown, m: string) => Promise<any>;
  setDirty: (v: boolean) => void;
};
export function Writing({
  item,
  state,
  prefix,
  busy,
  mutate,
  setDirty,
}: Props) {
  const event = state.events[item.event_id].event,
    existing = item.writing;
  const [form, setForm] = useState<Brief>(
    () =>
      existing?.brief ?? {
        path: item.changes[0]?.path || item.affected[0]?.path || "",
        template: "Reference",
        audience: "",
        goal: "",
        prerequisite: "",
        fact: "",
        recovery: "",
        source: event.source_url || "",
        capture: null,
      },
  );
  const [captures, setCaptures] = useState<
      { id: string; journey: string; revision: string }[]
    >([]),
    [problem, setProblem] = useState("");
  useEffect(() => {
    let active = true;
    if (prefix)
      request(prefix + "/captures")
        .then((r) => {
          if (active)
            setCaptures(
              r.jobs.filter(
                (j: { status: string; revision: string }) =>
                  j.status === "reviewed" &&
                  (!event.revision || j.revision === event.revision),
              ),
            );
        })
        .catch((e) => {
          if (active) setProblem(e.message);
        });
    return () => {
      active = false;
    };
  }, [prefix, event.revision]);
  function field(k: keyof Brief, v: string) {
    setForm((f) => ({ ...f, [k]: v || (k === "capture" ? null : "") }));
    setDirty(true);
    setProblem("");
  }
  async function submit(mode: string) {
    setProblem("");
    try {
      await mutate(
        "writing",
        { item_id: item.id, version: item.version, mode, brief: form },
        mode === "save"
          ? "Partial answers saved"
          : mode === "generate"
            ? "Guide drafted for review"
            : "No-change decision recorded",
      );
    } catch (e) {
      setProblem((e as Error).message);
    }
  }
  const sourceText = (event.title + " " + event.text).toLowerCase();
  const matches = Object.values(state.articles).filter(
    (a) =>
      a.title.trim().length > 3 &&
      sourceText.includes(a.title.toLowerCase()) &&
      !item.affected.some((m) => m.path === a.path),
  );
  const candidates = [
    ...new Set([
      ...item.affected.map((a) => a.path),
      ...item.changes.map((c) => c.path),
      ...matches.map((a) => a.path),
      ...Object.keys(state.articles),
    ]),
  ];
  return (
    <section className="document-content writing-panel">
      <h2>Writing brief</h2>
      <p>{event.text}</p>
      {item.affected.map((a) => (
        <p key={a.path}>
          <code>{a.path}</code> · {a.reasons.join(", ")}
        </p>
      ))}
      {matches.map((a) => (
        <p key={a.path}>
          <code>{a.path}</code> · Imported article title appears in the source
        </p>
      ))}
      {!matches.length && !item.affected.length && (
        <p>
          No matching section was found. Choose the article to update or enter a
          new path.
        </p>
      )}
      {existing?.report?.blockers?.length ? (
        <details>
          <summary>Draft review checks</summary>
          <ul>
            {existing.report.blockers.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </details>
      ) : null}
      {existing && (
        <p role="status">
          {existing.status === "drafted"
            ? "Draft available in Article and Changes"
            : existing.status === "no_change"
              ? "No documentation change required"
              : "Partial answers saved"}
          {existing.missing.length
            ? " · Missing " + existing.missing.join(", ")
            : ""}
        </p>
      )}
      <fieldset
        disabled={
          busy || ["resolved", "archived", "delivered"].includes(item.status)
        }
      >
        <label>
          Article path
          <input
            list="writing-paths"
            value={form.path}
            onChange={(e) => field("path", e.target.value)}
          />
        </label>
        <datalist id="writing-paths">
          {candidates.map((p) => (
            <option key={p} value={p} />
          ))}
        </datalist>
        <label>
          Guide format
          <select
            value={form.template}
            onChange={(e) => field("template", e.target.value)}
          >
            {["Reference", "Concept", "Tutorial"].map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </label>
        {prefix && <div>
          <button type="button" onClick={async () => {
            try {
              const p: Profile = await request(prefix + "/writing-profile");
              if (!p.revision || !p.audience) { setProblem("Ask a workspace administrator to save a writing profile."); return; }
              setForm(f => ({ ...f, profile_revision: p.revision, audience: p.audience! }));
              setProblem(""); setDirty(true);
            } catch (e) { setProblem((e as Error).message); }
          }}>Apply workspace writing profile</button>
          {form.profile_revision && <p>Writing profile revision {form.profile_revision}</p>}
        </div>}
        <label>
          Intended reader
          <input
            value={form.audience}
            onChange={(e) => field("audience", e.target.value)}
          />
        </label>
        <label>
          Reader goal
          <input
            value={form.goal}
            onChange={(e) => field("goal", e.target.value)}
          />
        </label>
        <label>
          Prerequisite
          <input
            value={form.prerequisite}
            onChange={(e) => field("prerequisite", e.target.value)}
          />
        </label>
        <label>
          Supported fact or expected result
          <textarea
            value={form.fact}
            onChange={(e) => field("fact", e.target.value)}
          />
        </label>
        <label>
          Source URL
          <input
            type="url"
            value={form.source}
            onChange={(e) => field("source", e.target.value)}
          />
        </label>
        <label>
          Recovery guidance (optional)
          <textarea
            value={form.recovery}
            onChange={(e) => field("recovery", e.target.value)}
          />
        </label>
        <label>
          Reviewed ContextQA capture
          <select
            value={form.capture || ""}
            onChange={(e) => field("capture", e.target.value)}
          >
            <option value="">Select a reviewed replay</option>
            {captures.map((c) => (
              <option key={c.id} value={c.id}>
                {c.journey} · {c.revision.slice(0, 8)}
              </option>
            ))}
          </select>
          {!captures.length && (
            <small>
              Review a matching replay in Capture journeys. Every guide needs a
              linked screenshot or video before delivery.
            </small>
          )}
        </label>
        <details>
          <summary>Guide outline</summary>
          <ol>
            <li>Reader goal</li>
            <li>Before you begin</li>
            <li>
              {form.template === "Tutorial"
                ? "Observed steps and expected result"
                : form.template === "Reference"
                  ? "Reference details"
                  : "What to know"}
            </li>
            {form.recovery && <li>Recovery guidance</li>}
            <li>Source reference</li>
          </ol>
        </details>
        {problem && <p role="alert">{problem}</p>}
        <div className="writing-actions">
          <button onClick={() => void submit("save")}>
            Save partial answers
          </button>
          <button className="primary" onClick={() => void submit("generate")}>
            Generate draft
          </button>
          <button onClick={() => void submit("no_change")}>
            Record no change
          </button>
        </div>
      </fieldset>
    </section>
  );
}
