// @vitest-environment jsdom
import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { request } from "./api";
import { GuideLibrary } from "./GuideLibrary";
import type { State } from "./types";

vi.mock("./api", () => ({ request: vi.fn(), accessToken: vi.fn() }));

it("shows the redirect error and recovery beside the reader address control", async () => {
  const path = "guides/invites.md";
  const digest = "a".repeat(64);
  const versions = [{ path, digest, current: true, item: "item", media: [] }];
  vi.mocked(request).mockImplementation(async (url, body) => {
    if (url.endsWith("/library")) return { versions, assets: [] };
    if (url.includes("/library/version?")) {
      return { body: "# Invitations", media: [], previous_media: [], source: {}, diff: "", item: "item" };
    }
    if (url.endsWith("/reader/redirects")) {
      if ((body as { source: string }).source === path) throw Error("Choose an unused source path.");
      return {};
    }
    throw Error("Unexpected request");
  });
  render(<GuideLibrary prefix="orgs/demo/projects/docs" state={{ items: {} } as State} open={vi.fn()} />);
  const section = (await screen.findByText("Reader address and retirement")).closest("details")!;
  fireEvent.click(within(section).getByText("Reader address and retirement"));
  const form = within(section);
  const input = form.getByLabelText("Old reader path");
  fireEvent.change(input, { target: { value: path } });
  fireEvent.click(form.getByText("Add redirect to this guide"));
  expect((await form.findByRole("alert")).textContent).toContain("unused source");
  fireEvent.change(input, { target: { value: "guides/previous.md" } });
  expect(form.queryByRole("alert")).toBeNull();
  fireEvent.click(form.getByText("Add redirect to this guide"));
  expect((await form.findByRole("status")).textContent).toBe("Reader redirect saved.");
});
