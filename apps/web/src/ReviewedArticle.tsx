import { Fragment, useEffect, useState } from "react";
import { accessToken } from "./api";
import { Markdown } from "./components";

function Figure({
  path,
  caption,
  video,
}: {
  path: string;
  caption: string;
  video: boolean;
}) {
  const [url, setUrl] = useState(""),
    [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl = "";
    setUrl("");
    setError("");
    async function read() {
      const response = await fetch(path, {
        headers: { Authorization: "Bearer " + (await accessToken()) },
        signal: controller.signal,
      });
      if (!response.ok) throw Error("The reviewed attachment is unavailable.");
      const blob = await response.blob();
      if (controller.signal.aborted) return;
      objectUrl = URL.createObjectURL(blob);
      setUrl(objectUrl);
    }
    read().catch((e) => {
      if (!controller.signal.aborted) setError(e.message);
    });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);
  return (
    <figure className="reviewed-figure">
      {url ? (
        video ? (
          <video aria-label={caption} src={url} controls preload="metadata" />
        ) : (
          <a href={url} target="_blank" rel="noreferrer" aria-label={'Open original screenshot: ' + caption}>
            <img src={url} alt={caption} style={{maxWidth: "100%", width: "auto", height: "auto"}} />
          </a>
        )
      ) : (
        <p role="status">{error || "Loading reviewed evidence…"}</p>
      )}
      <figcaption>{caption}</figcaption>
    </figure>
  );
}

export function ReviewedArticle({
  text,
  prefix,
  item,
  change,
  side = "after",
  versionPath,
  version,
}: {
  text: string;
  prefix?: string;
  item: string;
  change?: string;
  side?: "before" | "after";
  versionPath?: string;
  version?: string;
}) {
  // Resolve evidence and repository-relative figures through authenticated routes.
  const nodes: React.ReactElement[] = [];
  let lines: string[] = [],
    inCode = false;
  const flush = () => {
    if (lines.length) {
      nodes.push(
        <Markdown key={"text-" + nodes.length} text={lines.join("\n")} />,
      );
      lines = [];
    }
  };
  for (const line of text.split("\n")) {
    if (line.startsWith("```")) inCode = !inCode;
    if (
      !inCode &&
      /^<!-- (?:\/?contextqa:editorial:|docs:section:)[\w-]+ -->$/.test(line)
    )
      continue;
    const match =
      !inCode &&
      prefix &&
      line.match(
        /^!?\[(.+)\]\((?:\.\.\/)*evidence\/([a-f0-9]{64})\/assets\/([a-f0-9]{64})\.(png|jpg|webp|mp4|webm)\)$/,
      );
    const local = !inCode && !match && prefix && change && line.trim().match(
      /^(!?)\[([^\]]*)\]\(([^):\s]+\.(?:png|jpe?g|webp|mp4|webm))\)$/i,
    );
    if (local && !local[3].startsWith("/") && (local[1] || /\.(mp4|webm)$/i.test(local[3]))) {
      flush();
      const params = new URLSearchParams({ change, side, ref: local[3] });
      nodes.push(<Figure key={"repo-" + nodes.length} caption={local[2] || local[3]}
        video={/\.(mp4|webm)$/i.test(local[3])}
        path={"/api/" + prefix + "/writing/" + item + "/repository-media?" + params} />);
      continue;
    }
    if (!match) {
      lines.push(line);
      continue;
    }
    flush();
    nodes.push(
      <Figure
        key={"media-" + nodes.length}
        caption={match[1]}
        video={["webm", "mp4"].includes(match[4])}
        path={
          versionPath && version
            ? "/api/" +
              prefix +
              "/library/media/" +
              match[3] +
              "?" +
              new URLSearchParams({ path: versionPath, version })
            : "/api/" +
              prefix +
              "/writing/" +
              item +
              "/figures/" +
              match[2] +
              "/" +
              match[3]
        }
      />,
    );
  }
  flush();
  return <Fragment>{nodes}</Fragment>;
}
