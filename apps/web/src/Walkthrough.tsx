import { useEffect, useState } from "react";
import { request } from "./api";
import { Figure } from "./ReviewedArticle";

type Scene = {
  caption: string;
  kind: "screenshot" | "video";
  digest: string;
  journey: string;
  revision: string;
  run: number;
  step: number;
};

export function Walkthrough({ prefix, path, version, current }: {
  prefix: string; path: string; version: string; current: boolean;
}) {
  const [scenes, setScenes] = useState<Scene[] | null>(null);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState("");
  const [attempt, retry] = useState(0);
  useEffect(() => {
    let active = true;
    setError("");
    setScenes(null);
    setIndex(0);
    request(prefix + "/library/walkthrough?" + new URLSearchParams({ path, digest: version }))
      .then((data) => { if (active) setScenes(data.scenes); })
      .catch((e) => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [prefix, path, version, attempt]);
  const scene = scenes?.[index];
  return <section aria-label="Walkthrough preview">
    <h2>Walkthrough preview</h2>
    <p>{current ? "Current edition" : "Historical edition"} · {version.slice(0, 8)}</p>
    {error ? <><p role="alert">{error}</p><button onClick={() => retry(a => a + 1)}>Retry preview</button></> :
      scenes === null ? <p role="status">Loading scenes…</p> :
      scene ? <>
        <p aria-live="polite">Scene {index + 1} of {scenes.length} · {scene.caption}</p>
        <Figure key={index} caption={scene.caption} video={scene.kind === "video"}
          path={"/api/" + prefix + "/library/media/" + scene.digest + "?" + new URLSearchParams({path, version})} />
        <p>Journey {scene.journey} · Run {scene.run} · Step {scene.step} · Build {scene.revision.slice(0, 8)}</p>
        <div className="writing-actions">
          <button disabled={index === 0} onClick={() => setIndex(i => Math.max(0, i - 1))}>Previous scene</button>
          <button disabled={index === scenes.length - 1} onClick={() => setIndex(i => Math.min(scenes.length - 1, i + 1))}>Next scene</button>
        </div>
      </> : <p>This edition has no reviewed scenes. Save a guide with linked ContextQA evidence to preview a walkthrough.</p>}
  </section>;
}
