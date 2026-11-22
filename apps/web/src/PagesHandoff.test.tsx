// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { request } from "./api";
import { PagesHandoff } from "./PagesHandoff";

vi.mock("./api", () => ({request: vi.fn()}));

it("binds public approval to the reviewed preview and links to the resulting draft", async () => {
  const path = "guides/example.md";
  const version = "a".repeat(64);
  const preview = "b".repeat(64);
  vi.mocked(request).mockResolvedValueOnce({
    repository: "example/docs", branch: "staging-publish", base: "1".repeat(40),
    preview, guide: "sofa/example/index.html", media_count: 1, unchanged: false,
  }).mockResolvedValueOnce({ url: "https://github.com/example/docs/pull/4", state: "open" });
  render(<PagesHandoff prefix="project" path={path} version={version} />);
  fireEvent.click(screen.getByText("Publish to GitHub Pages"));
  fireEvent.click(screen.getByText("Check publishing destination"));
  const open = await screen.findByRole("button", { name: "Open publishing draft PR" });
  expect((open as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(open);
  expect((await screen.findByText("View publishing PR (open)")).getAttribute("href")).toBe("https://github.com/example/docs/pull/4");
  expect(request).toHaveBeenLastCalledWith("project/pages/draft-pr", {path, version, preview, approved_for_public:true});
});
