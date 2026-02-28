import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

function mockApi(url: string) {
  if (url === "/subjects") {
    return { subjects: ["Science", "Mathematics"] };
  }
  if (url === "/papers") {
    return {
      papers: [{ paper_id: "paper_001", title: "Science Mock", subject: "Science", created_at: "2026-01-01T00:00:00Z" }],
    };
  }
  if (url === "/evaluation") {
    return {
      evaluations: [
        {
          evaluation_id: "ev_001",
          total_marks: 7,
          max_marks: 10,
          corrected_pdf_url: "/evaluation/ev_001/corrected-pdf",
          created_at: "2026-01-01T00:00:00Z",
        },
      ],
    };
  }
  if (url.startsWith("/chapters/")) {
    return { chapters: ["Chapter 1", "Chapter 2"] };
  }
  return {};
}

describe("App smoke tests", () => {
  beforeEach(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation(() => ({
        matches: false,
        media: "",
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = typeof input === "string" ? input : input.toString();
        return new Response(JSON.stringify(mockApi(url)), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("renders main screens and loads startup data", async () => {
    render(<App />);

    expect(screen.getByText("Examora")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Question Preparation" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Answer Correction" })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Science Mock (Science)")).toBeInTheDocument();
    });
  });
});
