export class ApiError extends Error {
  constructor(message, { status = 0, code = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function readError(response) {
  try {
    const payload = await response.json();
    return {
      message: payload?.message || payload?.detail || `Error HTTP ${response.status}`,
      code: payload?.code ?? null,
    };
  } catch {
    return {
      message: `Error HTTP ${response.status}`,
      code: null,
    };
  }
}

/**
 * Cliente REST del catálogo. En producción el frontend vive detrás de nginx y
 * llama rutas relativas `/api`; en desarrollo Vite redirige al backend 7845.
 */
export function createApiClient({
  baseUrl = import.meta.env?.VITE_API_BASE_URL || "/api",
  fetchImpl = globalThis.fetch,
} = {}) {
  if (typeof fetchImpl !== "function") {
    throw new Error("fetch no está disponible en este entorno.");
  }

  const normalizedBase = baseUrl.replace(/\/$/, "");

  async function request(path, options = {}) {
    const { headers, ...rest } = options;
    let response;

    try {
      response = await fetchImpl(`${normalizedBase}${path}`, {
        ...rest,
        headers: {
          Accept: "application/json",
          ...(rest.body ? { "Content-Type": "application/json" } : {}),
          ...headers,
        },
      });
    } catch (error) {
      if (error?.name === "AbortError") {
        throw error;
      }
      throw new ApiError("No fue posible conectar con el servidor.", {
        code: "NETWORK_ERROR",
      });
    }

    if (!response.ok) {
      const { message, code } = await readError(response);
      throw new ApiError(message, { status: response.status, code });
    }

    if (response.status === 204) {
      return null;
    }
    return response.json();
  }

  return {
    searchTracks(query, { limit = 12, signal } = {}) {
      const params = new URLSearchParams({
        q: query,
        limit: String(limit),
      });
      return request(`/catalog/search?${params.toString()}`, { signal });
    },

    getTrack(trackId, { signal } = {}) {
      return request(`/catalog/tracks/${encodeURIComponent(trackId)}`, { signal });
    },

    markUnplayable(trackId) {
      return request(`/catalog/tracks/${encodeURIComponent(trackId)}/unplayable`, {
        method: "POST",
      });
    },
  };
}
