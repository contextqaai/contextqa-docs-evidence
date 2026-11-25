// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Walkthrough } from "./Walkthrough";
import { request } from "./api";

vi.mock("./api", () => ({ request: vi.fn(), accessToken: async () => "fixture" }));
const base = { prefix: "orgs/test/projects/docs", path: "guides/setup.md", version: "a".repeat(64), current: true };
const photo = { caption: "Open review", digest: "b".repeat(64), kind: "screenshot", revision: "candidate", journey: "review", run: 40, step: 401 };
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.resetAllMocks(); });

it("navigates only within this edition and requests the versioned media", async () => {
  vi.mocked(request).mockResolvedValue({ scenes: [photo, { ...photo, caption: "Watch review", digest: "c".repeat(64), kind: "video" }] });
  const fetchMedia = vi.fn(async () => new Response(new Blob(["fixture"])));
  vi.stubGlobal("fetch", fetchMedia);
  vi.stubGlobal("URL", class extends URL {
    static createObjectURL = () => "blob:fixture";
    static revokeObjectURL = vi.fn();
  });
  render(<Walkthrough {...base} />);
  await screen.findByRole("img", { name: "Open review" });
  expect(fetchMedia.mock.calls[0]).toEqual(["/api/" + base.prefix + "/library/media/" + photo.digest + "?" +
    new URLSearchParams({path: base.path, version: base.version}), expect.objectContaining({ headers: { Authorization: "Bearer fixture" } })]);
  const prev = screen.getByRole("button", {name:"Previous scene"}) as HTMLButtonElement;
  const next = screen.getByRole("button", {name:"Next scene"}) as HTMLButtonElement;
  expect(prev.disabled).toBe(true);
  fireEvent.click(next);
  await waitFor(() => expect(screen.getByLabelText("Watch review").tagName).toBe("VIDEO"));
  expect(next.disabled).toBe(true);
  fireEvent.click(prev);
  await screen.findByRole("img", { name: "Open review" });
});

it("recovers from a failed preview and explains an empty historical edition", async () => {
  vi.mocked(request).mockRejectedValueOnce(Error("Preview unavailable")).mockResolvedValueOnce({ scenes: [] });
  render(<Walkthrough {...base} current={false} />);
  expect((await screen.findByRole("alert")).textContent).toContain("Preview unavailable");
  fireEvent.click(screen.getByText("Retry preview"));
  await screen.findByText(/no reviewed scenes/);
  expect(screen.getByText(/Historical edition/)).toBeTruthy();
  expect(screen.queryByRole("button", {name: "Next scene"})).toBeNull();
});

it("shows media failure and bounds a single scene", async () => {
  vi.mocked(request).mockResolvedValue({ scenes: [photo] });
  vi.stubGlobal("fetch", vi.fn(async () => new Response(null, {status: 404})));
  render(<Walkthrough {...base} />);
  await screen.findByText("The reviewed attachment is unavailable.");
  expect((screen.getByText("Next scene") as HTMLButtonElement).disabled).toBe(true);
  expect(screen.queryByRole("img")).toBeNull();
});
