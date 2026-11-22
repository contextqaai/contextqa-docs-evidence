// Session-only recovery. The original request revision is retained across reloads.
export const draftPrefix = "contextqa:article-draft:";
type Recovery = { body: string; version: number };
export function readDraft(key: string): Recovery | null {
  try {
    const data = JSON.parse(sessionStorage.getItem(key) || "null");
    return data &&
      typeof data.body === "string" &&
      Number.isInteger(data.version)
      ? data
      : null;
  } catch {
    return null;
  }
}
export function rememberDraft(key: string, data: Recovery) {
  try {
    sessionStorage.setItem(key, JSON.stringify(data));
  } catch {
    /* The editor still retains the unsaved text in memory. */
  }
}
export function clearDrafts() {
  for (const key of Object.keys(sessionStorage)) {
    if (key.startsWith(draftPrefix)) sessionStorage.removeItem(key);
  }
}
