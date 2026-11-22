// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { Captures } from "./Captures";
import { request } from "./api";

vi.mock("./api", () => ({ request: vi.fn(), accessToken: vi.fn() }));

it("shows a configured plan while explaining what blocks its first replay", async () => {
  vi.mocked(request).mockResolvedValue({
    profiles: [
      {
        id: "pilot",
        name: "Portal guide",
        cases: [212],
        plan: 43,
        environment: "Ship 5",
        digest: null,
        drift: false,
      },
    ],
    jobs: [],
    meter: "Metered replay",
    workspace: 1,
    discovery: null,
    provider_configured: false,
  });
  render(<Captures prefix="orgs/demo/projects/docs" role="admin" />);
  expect(
    await screen.findByText(/configure the ContextQA workspace API credential/),
  ).toBeTruthy();
  expect(
    screen
      .getByRole("button", { name: "Register saved definition" })
      .hasAttribute("disabled"),
  ).toBe(true);
  expect(
    screen
      .getByRole("button", { name: "Replay journey" })
      .hasAttribute("disabled"),
  ).toBe(true);
  expect(request).toHaveBeenCalledTimes(1);
});
