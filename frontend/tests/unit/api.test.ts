import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, setApiUser } from "@/lib/api";

describe("typed API client", () => {
  afterEach(() => vi.restoreAllMocks());

  it("sends the X-VRA-User identity header to same-origin /api", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, text: async () => JSON.stringify({ missions: [] }) });
    vi.stubGlobal("fetch", fetchMock);
    setApiUser("a.lang");
    await api.missions();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/missions",
      expect.objectContaining({ headers: expect.objectContaining({ "X-VRA-User": "a.lang" }) }),
    );
  });

  it("treats an empty 200 body as undefined instead of throwing", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, text: async () => "" });
    vi.stubGlobal("fetch", fetchMock);
    await expect(api.missions()).resolves.toBeUndefined();
  });

  it("surfaces backend gateway denials as ApiError with stage + code", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      statusText: "Forbidden",
      json: async () => ({ detail: "role technician not permitted", code: "denied", stage: "role" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await expect(api.decide("APR-1", { decision: "approve" })).rejects.toBeInstanceOf(ApiError);
    vi.stubGlobal("fetch", fetchMock);
    await expect(api.decide("APR-1", { decision: "approve" })).rejects.toMatchObject({
      status: 403,
      stage: "role",
      code: "denied",
    });
  });
});
