import { useState } from "react";
import type { Item, State } from "./types";
import { Modal } from "./components";
type Mutation = (
  action: string,
  data: unknown,
  message: string,
) => Promise<any>;
export function QueueActions({
  item,
  state,
  disabled,
  mutate,
}: {
  item: Item;
  state: State;
  disabled: boolean;
  mutate: Mutation;
}) {
  const [dialog, setDialog] = useState(""),
    [recipient, pick] = useState(""),
    [note, setNote] = useState(""),
    [error, setError] = useState("");
  const editor = state.role !== "contributor",
    closed = ["archived", "resolved", "delivered"].includes(item.status);
  async function apply(action: string, data: object = {}) {
    setError("");
    try {
      await mutate(
        "review",
        { item_id: item.id, version: item.version, action, data },
        action === "handoff"
          ? "Handoff recorded in the recipient’s inbox"
          : "Review updated",
      );
      setDialog("");
      setNote("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <section className="context-section">
      <h3>Review actions</h3>
      {editor && !closed && (
        <label>
          Priority
          <select
            disabled={disabled}
            value={item.priority || "normal"}
            onChange={(e) =>
              void apply("priority", { priority: e.target.value })
            }
          >
            {["normal", "high", "urgent"].map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </label>
      )}
      <div className="writing-actions">
        {!closed && (
          <>
            <button
              disabled={
                disabled || !item.changes.some((c) => c.decision === "pending")
              }
              onClick={() => setDialog("accept_item")}
            >
              Accept all in request
            </button>
            <button disabled={disabled} onClick={() => setDialog("handoff")}>
              Hand off review
            </button>
          </>
        )}
        {editor && !closed && (
          <>
            <button disabled={disabled} onClick={() => setDialog("resolve")}>
              Resolve
            </button>
            <button disabled={disabled} onClick={() => setDialog("archive")}>
              Archive
            </button>
          </>
        )}
        {editor && item.status === "archived" && (
          <button disabled={disabled} onClick={() => void apply("restore")}>
            Restore to inbox
          </button>
        )}
      </div>
      {item.handoffs?.map((h, n) => (
        <p key={n}>
          Handed off to {h.recipient} · {h.note}
          {item.status === "ready" && <strong> · Ready for approval</strong>}
        </p>
      ))}
      {error && !dialog && <p role="alert">{error}</p>}
      {dialog && (
        <Modal
          title={
            {
              accept_item: "Accept pending articles in this request?",
              handoff: "Hand off review",
              resolve: "Resolve this request?",
              archive: "Archive this request?",
            }[dialog] || ""
          }
          onClose={() => {
            setDialog("");
            setError("");
          }}
          busy={disabled}
        >
          <p>
            {dialog === "accept_item"
              ? item.changes.filter((c) => c.decision === "pending").length +
                " pending articles in " +
                item.title
              : item.title}
          </p>
          {dialog === "handoff" && (
            <>
              <label>
                Recipient
                <select
                  value={recipient}
                  onChange={(e) => pick(e.target.value)}
                >
                  <option value="">Choose an editor</option>
                  {Object.entries(state.members)
                    .filter(
                      ([id, r]) =>
                        id !== state.actor && ["editor", "admin"].includes(r),
                    )
                    .map(([id]) => (
                      <option key={id}>{id}</option>
                    ))}
                </select>
              </label>
              <label>
                Handoff note
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </label>
            </>
          )}
          {error && <p role="alert">{error}</p>}
          <div className="modal-footer">
            <button onClick={() => setDialog("")}>Cancel</button>
            <button
              className="primary"
              disabled={
                disabled ||
                (dialog === "handoff" && (!recipient || !note.trim()))
              }
              onClick={() =>
                void apply(
                  dialog,
                  dialog === "handoff" ? { assignee: recipient, note } : {},
                )
              }
            >
              {dialog === "handoff" ? "Send to inbox" : "Confirm"}
            </button>
          </div>
        </Modal>
      )}
    </section>
  );
}
