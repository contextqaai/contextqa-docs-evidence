import { useState } from "react";
import { request } from "./api";

type Preview = { repository: string; branch: string; base: string; preview: string; guide: string; unchanged: boolean; media_count: number };
export function PagesHandoff({ prefix, path, version }: { prefix: string; path: string; version: string }) {
  const [preview, setPreview] = useState<Preview>();
  const [approved, setApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState<{ url: string; state: string }>();

  async function run(publish: boolean) {
    setBusy(true);
    setError("");
    try {
      if (publish && preview && approved) {
        setReceipt(await request(prefix + "/pages/draft-pr", { path, version, preview: preview.preview, approved_for_public: true }));
      } else {
        setReceipt(undefined);
        setApproved(false);
        setPreview(undefined);
        setPreview(await request(prefix + "/pages/preview", { path, version }));
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return <details><summary>Publish to GitHub Pages</summary>
    <fieldset disabled={busy}>
      <legend>Public disclosure review</legend>
      <button onClick={() => void run(false)}>Check publishing destination</button>
      {preview && <><p>{preview.repository} · {preview.branch} at {preview.base.slice(0, 8)} · {preview.media_count} evidence files</p>
        <p>Public guide path <code>{preview.guide}</code></p>
        {preview.unchanged && <p role="status">This guide revision is already on the publishing branch.</p>}
        <label><input type="checkbox" checked={approved} onChange={e => setApproved(e.target.checked)} /> I reviewed this guide and each original attachment for public sharing on this repository.</label>
        <button disabled={preview.unchanged || !approved || !!receipt} onClick={() => void run(true)}>Open publishing draft PR</button></>}
      {error && <p role="alert">{error}</p>}
      {receipt && <a href={receipt.url} target="_blank" rel="noreferrer">View publishing PR ({receipt.state})</a>}
    </fieldset>
  </details>;
}
