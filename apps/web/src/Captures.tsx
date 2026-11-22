import { useEffect, useState, useRef } from "react";
import { request, accessToken } from "./api";
import { Empty, Heading } from "./components";

type Profile = {
  drift: boolean;
  id: string;
  name: string;
  cases: number[];
  plan: number;
  environment: string;
  digest: string | null;
};
type Artifact = {
  id: string;
  kind: string;
  sha256: string;
  step_results: number[];
};
type Receipt = {
  deployment_verified: boolean;
  steps: number;
  coverage_gaps: string[];
  instructions?: {
    step_result_id: number;
    title: string;
    instruction: string;
  }[];
  media: Artifact[];
};
type Job = {
  id: string;
  journey: string;
  revision: string;
  status: string;
  reason: string | null;
  provider_run: number | null;
  receipt: Receipt | null;
  receipt_digest: string | null;
};
type Data = {
  profiles: Profile[];
  jobs: Job[];
  meter: string | null;
  workspace: number | null;
  discovery: string | null;
};
export function Captures({ prefix, role }: { prefix: string; role: string }) {
  const base = prefix + "/captures",
    allowed = role === "admin" || role === "editor";
  const [data, setData] = useState<Data | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const [profileId, pick] = useState(""),
    [revision, setRevision] = useState(""),
    [confirmed, confirm] = useState(false),
    [selected, select] = useState("");
  const [approved, approve] = useState(false);
  const retry = useRef<{ key: string; id: string } | null>(null);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    let active = true,
      timer = 0;
    async function read() {
      try {
        const d: Data = await request(base);
        if (!active) return;
        setData(d);
        if (
          d.jobs.some((j) =>
            ["queued", "starting", "running", "collecting"].includes(j.status),
          )
        )
          timer = window.setTimeout(read, 4000);
      } catch (e) {
        if (active) setError((e as Error).message);
      }
    }
    if (allowed) void read();
    return () => {
      active = false;
      mounted.current = false;
      clearTimeout(timer);
    };
  }, [base, allowed, busy]);
  const profile =
      data?.profiles.find((p) => p.id === profileId) ?? data?.profiles[0],
    job = data?.jobs.find((j) => j.id === selected);
  async function action(path: string, body: object) {
    setBusy(true);
    setError("");
    try {
      const result = await request(base + "/" + path, body);
      if (!mounted.current) return;
      if (result.id) select(result.id);
      retry.current = null;
      confirm(false);
      approve(false);
    } catch (e) {
      if (mounted.current) setError((e as Error).message);
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  async function download(j: Job, a: Artifact) {
    setError("");
    try {
      const response = await fetch(
        "/api/" + base + "/jobs/" + j.id + "/media/" + a.id,
        { headers: { Authorization: "Bearer " + (await accessToken()) } },
      );
      if (!response.ok)
        throw Error(
          "The verified file is unavailable. Refresh the capture and check its status.",
        );
      const blob = await response.blob(),
        url = URL.createObjectURL(blob),
        anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = a.id + "." + blob.type.split("/")[1];
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (e) {
      if (mounted.current) setError((e as Error).message);
    }
  }
  if (!allowed)
    return (
      <Empty title="Capture access requires an editor">
        Ask your workspace administrator for access.
      </Empty>
    );
  return (
    <>
      <Heading
        title="Capture journeys"
        description="Replay saved ContextQA journeys and review their evidence."
      />
      {error && (
        <p role="alert" className="error-banner">
          {error}
        </p>
      )}
      {!data ? (
        <p role="status">Loading capture journeys…</p>
      ) : (
        <>
          <section className="panel">
            <h2>Discovery</h2>
            <p>
              {data.discovery
                ? "Latest discovery status · " +
                  data.discovery.replaceAll("_", " ")
                : "No discovery has been recorded for this project."}{" "}
              Manage the target and crawl in Workspace settings.
            </p>
          </section>
          <section className="panel">
            <h2>Saved journeys</h2>
            {profile ? (
              <>
                <label>
                  Journey
                  <select
                    value={profile.id}
                    onChange={(e) => {
                      pick(e.target.value);
                      confirm(false);
                    }}
                  >
                    {data.profiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </label>
                <p>
                  Workspace {data.workspace} · {profile.environment} · Plan{" "}
                  {profile.plan} · Cases {profile.cases.join(", ")}
                </p>
                {profile.drift && (
                  <p role="status">
                    The saved journey changed. Register the current definition
                    before replay.
                  </p>
                )}
                {role === "admin" && (
                  <>
                    <button
                      disabled={busy}
                      onClick={() => void action(profile.id + "/register", {})}
                    >
                      {profile.digest
                        ? "Refresh saved definition"
                        : "Register saved definition"}
                    </button>
                    <label>
                      Deployed commit
                      <input
                        value={revision}
                        onChange={(e) => {
                          setRevision(e.target.value);
                          confirm(false);
                        }}
                        placeholder="40-character Git commit SHA"
                      />
                    </label>
                    <p>
                      {data.meter ||
                        "Configure the workspace metering terms before replay."}
                    </p>
                    <label>
                      <input
                        type="checkbox"
                        checked={confirmed}
                        onChange={(e) => confirm(e.target.checked)}
                      />
                      I approve this metered ContextQA replay.
                    </label>
                    <button
                      disabled={
                        busy ||
                        !profile.digest ||
                        !data.meter ||
                        !confirmed ||
                        !/^[a-f0-9]{40}$/.test(revision)
                      }
                      onClick={() => {
                        const key = [profile.id, profile.digest, revision].join(
                          "/",
                        );
                        if (retry.current?.key !== key)
                          retry.current = { key, id: crypto.randomUUID() };
                        void action(profile.id + "/replay", {
                          digest: profile.digest,
                          revision,
                          confirm: true,
                          request_id: retry.current.id,
                        });
                      }}
                    >
                      Replay journey
                    </button>
                  </>
                )}
              </>
            ) : (
              <p>
                Ask the workspace administrator to connect a saved ContextQA
                plan and its cases.
              </p>
            )}
          </section>
          <section className="panel">
            <h2>Replay history</h2>
            {data.jobs.length ? (
              data.jobs.map((j) => (
                <p key={j.id}>
                  <button
                    aria-pressed={selected === j.id}
                    onClick={() => {
                      select(j.id);
                      approve(false);
                    }}
                  >
                    {j.journey} · {j.status.replaceAll("_", " ")} ·{" "}
                    {j.revision.slice(0, 8)}
                  </button>
                </p>
              ))
            ) : (
              <p>No saved journeys have been replayed.</p>
            )}
          </section>
          {job && (
            <section className="panel">
              <h2>Replay details</h2>
              <p>
                {job.status.replaceAll("_", " ")} ·{" "}
                {job.provider_run
                  ? "ContextQA run " + job.provider_run
                  : "Awaiting an attributable provider run"}
              </p>
              <p>
                Requested commit <code>{job.revision}</code>
              </p>
              {job.reason && <p role="status">{job.reason}</p>}
              {role === "admin" &&
                ["reconcile", "needs_evidence"].includes(job.status) && (
                  <button
                    disabled={busy}
                    onClick={() => void action("jobs/" + job.id + "/check", {})}
                  >
                    Check original run
                  </button>
                )}
              {job.receipt && (
                <>
                  <p>
                    {job.receipt.deployment_verified
                      ? "Deployment verified"
                      : "Deployment unverified"}{" "}
                    · {job.receipt.steps} recorded steps
                  </p>
                  {job.receipt.coverage_gaps.map((g) => (
                    <p key={g}>Coverage gap · {g}</p>
                  ))}
                  <ol>
                    {job.receipt.instructions?.map((s) => (
                      <li key={s.step_result_id}>
                        <strong>{s.title}</strong>
                        <p>{s.instruction}</p>Step result {s.step_result_id}
                      </li>
                    ))}
                  </ol>
                  {job.receipt.media.map((a) => (
                    <p key={a.id}>
                      <button onClick={() => void download(job, a)}>
                        Download {a.kind} · step {a.step_results.join(", ")}
                      </button>
                    </p>
                  ))}
                  {job.status === "awaiting_review" && (
                    <>
                      <label>
                        <input
                          type="checkbox"
                          checked={approved}
                          onChange={(e) => approve(e.target.checked)}
                        />
                        I reviewed the steps, media and permission to use them.
                      </label>
                      <button
                        disabled={busy || !approved}
                        onClick={() =>
                          void action("jobs/" + job.id + "/review", {
                            confirm: true,
                            digest: job.receipt_digest,
                          })
                        }
                      >
                        Approve capture
                      </button>
                    </>
                  )}
                </>
              )}
            </section>
          )}
        </>
      )}
    </>
  );
}
