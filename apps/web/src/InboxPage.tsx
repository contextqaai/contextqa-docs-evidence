import { useState } from "react";
import { Search, GitPullRequest } from "lucide-react";
import { Badge, Empty, Modal, Heading, date } from "./components";
import type { State } from "./types";
import { itemMatches } from "../../../cqa_artifacts/loop_ui/ui-core.js";
export function InboxPage({
  state,
  open,
  mutate,
  busy = false,
}: {
  state: State;
  open: (id: string) => void;
  mutate?: (action: string, data: unknown, message: string) => Promise<any>;
  busy?: boolean;
}) {
  const [filter, setFilter] = useState("all"),
    [query, setQuery] = useState("");
  const [page, setPage] = useState(0),
    [selection, setSelection] = useState<{ id: string; version: number }[]>([]),
    [receipt, setReceipt] = useState("");
  const items = Object.values(state.items),
    matches = items
      .filter(
        (i) =>
          itemMatches(i, filter, query, state.actor) &&
          (filter === "archived" || i.status !== "archived"),
      )
      .sort((a, b) => b.created_at - a.created_at);
  const last = Math.max(0, Math.ceil(matches.length / 10) - 1),
    index = Math.min(page, last),
    visible = matches.slice(index * 10, (index + 1) * 10);
  async function acceptPage() {
    try {
      const result = await mutate?.(
        "review-page",
        { items: selection },
        "Page decisions recorded",
      );
      if (!result) return;
      const failures = result.results.filter(
        (r: { accepted: boolean }) => !r.accepted,
      );
      setReceipt(
        String(result.results.length - failures.length) +
          " requests accepted." +
          (failures.length
            ? " Refresh and review " +
              failures
                .map(
                  (r: { id: string }) =>
                    items.find((i) => i.id === r.id)?.title || r.id,
                )
                .join(", ") +
              "."
            : ""),
      );
      setSelection([]);
    } catch (e) {
      setReceipt((e as Error).message);
    }
  }
  return (
    <>
      <Heading
        title="Review inbox"
        description="Product changes, ready for your expertise."
      >
        <span className="source-chip">
          <GitPullRequest />
          {state.manifest.repository}
        </span>
      </Heading>
      <div className="metrics">
        {[
          [
            "In review",
            items.filter((i) => ["open", "ready"].includes(i.status)).length,
          ],
          [
            "Needs evidence",
            items.filter((i) => i.status === "needs_input").length,
          ],
          ["Article baselines", Object.keys(state.articles).length],
          [
            "Delivered",
            items.filter((i) => ["delivered", "resolved"].includes(i.status))
              .length,
          ],
        ].map(([label, n]) => (
          <div className="metric" key={label}>
            <div className="metric-label">{label}</div>
            <div className="metric-value">
              <b>{n}</b>
            </div>
          </div>
        ))}
      </div>
      <div className="toolbar">
        <div className="filters" aria-label="Filter requests">
          {[
            ["all", "All requests"],
            ["review", "In review"],
            ["blocked", "Needs evidence"],
            ["assigned", "Assigned to me"],
            ["done", "Completed"],
            ["archived", "Archived"],
          ].map(([value, label]) => (
            <button
              key={value}
              aria-pressed={filter === value}
              className={filter === value ? "selected" : ""}
              onClick={() => {
                setFilter(value);
                setPage(0);
              }}
            >
              {label}
              <b>
                {
                  items.filter(
                    (i) =>
                      itemMatches(i, value, "", state.actor) &&
                      (value === "archived" || i.status !== "archived"),
                  ).length
                }
              </b>
            </button>
          ))}
        </div>
        <label className="search-box">
          <Search />
          <input
            aria-label="Search requests"
            placeholder="Search requests…"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(0);
            }}
          />
        </label>
      </div>
      {visible.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>REQUEST</th>
                <th>STATUS</th>
                <th>PRIORITY</th>
                <th>CHANGES</th>
                <th>ASSIGNED TO</th>
                <th>CREATED</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((i) => (
                <tr key={i.id}>
                  <td>
                    <button className="text-link" onClick={() => open(i.id)}>
                      {i.title}
                    </button>
                    <div className="row-subtitle">
                      {i.source} · {state.manifest.repository}
                    </div>
                  </td>
                  <td>
                    <Badge status={i.status} />
                  </td>
                  <td>{i.priority || "normal"}</td>
                  <td>{i.changes.length} articles</td>
                  <td>{i.assignee || "Unassigned"}</td>
                  <td>{date(i.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="table-footer">
            {matches.length} requests · Page {index + 1} of {last + 1}
            <div className="writing-actions">
              <button disabled={!index} onClick={() => setPage(index - 1)}>
                Previous
              </button>
              <button
                disabled={index >= last}
                onClick={() => setPage(index + 1)}
              >
                Next
              </button>
              {mutate && (
                <button
                  disabled={
                    busy ||
                    !visible.some(
                      (i) =>
                        i.changes.some((c) => c.decision === "pending") &&
                        !["archived", "resolved", "delivered"].includes(
                          i.status,
                        ),
                    )
                  }
                  onClick={() =>
                    setSelection(
                      visible
                        .filter(
                          (i) =>
                            !["archived", "resolved", "delivered"].includes(
                              i.status,
                            ) &&
                            i.changes.some((c) => c.decision === "pending"),
                        )
                        .map((i) => ({ id: i.id, version: i.version })),
                    )
                  }
                >
                  Accept pending on this page
                </button>
              )}
            </div>
          </div>
        </div>
      ) : (
        <Empty title="No requests match this view">
          Try another filter or search term.
        </Empty>
      )}
      {receipt && <p role="status">{receipt}</p>}
      {selection.length > 0 && (
        <Modal
          title="Accept this page’s pending articles?"
          description="Only the listed requests are included."
          busy={busy}
          onClose={() => setSelection([])}
        >
          <ul>
            {selection.map((s) => (
              <li key={s.id}>{items.find((i) => i.id === s.id)?.title}</li>
            ))}
          </ul>
          <button onClick={() => setSelection([])}>Cancel</button>
          <button disabled={busy} onClick={() => void acceptPage()}>
            Confirm page decisions
          </button>
        </Modal>
      )}
    </>
  );
}
