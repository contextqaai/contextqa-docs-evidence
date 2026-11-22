// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ReviewedArticle } from "./ReviewedArticle";

vi.mock("./api", () => ({ accessToken: async () => "reader" }));

it("renders the selected revision's relative screenshot and recording inline", async () => {
  const fetchFigure = vi.fn(async () => new Response(new Blob(["example"])));
  vi.stubGlobal("fetch", fetchFigure);
  const create = vi.fn(() => "blob:example");
  const revoke = vi.fn();
  vi.stubGlobal("URL", class extends URL {
    static createObjectURL = create;
    static revokeObjectURL = revoke;
  });
  try {
    const ref = "../.gitbook/assets/step.jpg";
    const { unmount } = render(<ReviewedArticle prefix="orgs/demo/projects/docs" item="entry"
      change="change-id" side="before"
      text={`![Edit invitation](${ref})\n\n[Watch](../.gitbook/assets/step.mp4)`} />);
    expect((await screen.findByRole("img", { name: "Edit invitation" })).getAttribute("src")).toBe("blob:example");
    await waitFor(() => expect(screen.getByLabelText("Watch").tagName).toBe("VIDEO"));
    expect(fetchFigure).toHaveBeenCalledWith(
      "/api/orgs/demo/projects/docs/writing/entry/repository-media?" +
        new URLSearchParams({ change: "change-id", side: "before", ref }),
      expect.objectContaining({ headers: { Authorization: "Bearer reader" } }),
    );
    unmount();
    expect(revoke).toHaveBeenCalledTimes(2);
  } finally {
    vi.unstubAllGlobals();
  }
});
