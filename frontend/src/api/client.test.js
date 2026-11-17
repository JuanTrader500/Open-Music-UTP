import { describe, expect, it, vi } from "vitest";

import { ApiError, createApiClient } from "./client";

function fakeResponse(payload, { ok = true, status = 200 } = {}) {
  return {
    ok,
    status,
    json: vi.fn().mockResolvedValue(payload),
  };
}

describe("createApiClient", () => {
  it("construye la búsqueda, codifica los parámetros y devuelve el JSON", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      fakeResponse({
        items: [{ track_id: "abc123", title: "Rock" }],
        total: 1,
        query: "rock & roll",
      }),
    );
    const client = createApiClient({ baseUrl: "/api/", fetchImpl });

    const result = await client.searchTracks("rock & roll", { limit: 8 });

    expect(fetchImpl).toHaveBeenCalledWith(
      "/api/catalog/search?q=rock+%26+roll&limit=8",
      expect.objectContaining({
        headers: expect.objectContaining({ Accept: "application/json" }),
      }),
    );
    expect(result.items[0].track_id).toBe("abc123");
  });

  it("convierte una respuesta de error del backend en ApiError", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      fakeResponse(
        { code: "SERVICE_UNAVAILABLE", message: "La base de datos no responde." },
        { ok: false, status: 503 },
      ),
    );
    const client = createApiClient({ baseUrl: "/api", fetchImpl });

    await expect(client.searchTracks("rock")).rejects.toMatchObject({
      name: "ApiError",
      message: "La base de datos no responde.",
      status: 503,
      code: "SERVICE_UNAVAILABLE",
    });
  });

  it("informa un error de red con un mensaje entendible", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const client = createApiClient({ baseUrl: "/api", fetchImpl });

    await expect(client.searchTracks("rock")).rejects.toBeInstanceOf(ApiError);
    await expect(client.searchTracks("rock")).rejects.toThrow(
      "No fue posible conectar con el servidor.",
    );
  });

  it("codifica el identificador al pedir el detalle", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(fakeResponse({ track_id: "a/b" }));
    const client = createApiClient({ baseUrl: "/api", fetchImpl });

    await client.getTrack("a/b");

    expect(fetchImpl).toHaveBeenCalledWith(
      "/api/catalog/tracks/a%2Fb",
      expect.any(Object),
    );
  });
});
