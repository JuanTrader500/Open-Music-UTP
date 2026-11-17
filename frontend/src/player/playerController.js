const IFRAME_API_URL = "https://www.youtube.com/iframe_api";

let iframeApiPromise = null;

const STATE_LABELS = {
  "-1": "Listo para reproducir",
  0: "Finalizado",
  1: "Reproduciendo",
  2: "En pausa",
  3: "Cargando",
  5: "En cola",
};

export function resetIframeApiForTests() {
  iframeApiPromise = null;
}

/**
 * Carga la IFrame Player API una sola vez y reutiliza la promesa.
 * La reproducción no necesita YOUTUBE_API_KEY: la clave solo la usa el backend.
 */
export function loadIframeApi({ documentRef = document, windowRef = window } = {}) {
  if (windowRef.YT?.Player) {
    return Promise.resolve(windowRef.YT);
  }
  if (iframeApiPromise) {
    return iframeApiPromise;
  }

  iframeApiPromise = new Promise((resolve, reject) => {
    const previousReady = windowRef.onYouTubeIframeAPIReady;
    windowRef.onYouTubeIframeAPIReady = () => {
      if (typeof previousReady === "function") {
        previousReady();
      }
      if (windowRef.YT?.Player) {
        resolve(windowRef.YT);
      } else {
        reject(new Error("YouTube no expuso la IFrame Player API."));
      }
    };

    const existing = documentRef.querySelector(`script[src="${IFRAME_API_URL}"]`);
    if (existing) {
      return;
    }

    const script = documentRef.createElement("script");
    script.src = IFRAME_API_URL;
    script.async = true;
    script.onerror = () => {
      iframeApiPromise = null;
      reject(new Error("No fue posible cargar el reproductor de YouTube."));
    };
    documentRef.head.appendChild(script);
  });

  return iframeApiPromise;
}

export class YouTubePlayer {
  constructor({
    elementId = "youtube-player",
    loadApi = loadIframeApi,
    onReady,
    onStateChange,
    onError,
  } = {}) {
    this.elementId = elementId;
    this.loadApi = loadApi;
    this.onReady = onReady;
    this.onStateChange = onStateChange;
    this.onError = onError;
    this.player = null;
    this.ready = false;
    this.readyPromise = null;
    this.resolveReady = null;
    this.rejectReady = null;
  }

  async mount() {
    if (this.player && this.ready) {
      return this.player;
    }

    if (this.player && this.readyPromise) {
      await this.readyPromise;
      return this.player;
    }

    const YT = await this.loadApi();
    if (!YT?.Player) {
      throw new Error("La IFrame Player API de YouTube no está disponible.");
    }

    this.readyPromise = new Promise((resolve, reject) => {
      this.resolveReady = resolve;
      this.rejectReady = reject;
    });

    try {
      this.player = new YT.Player(this.elementId, {
        width: "100%",
        height: "100%",
        playerVars: {
          autoplay: 0,
          controls: 1,
          rel: 0,
          playsinline: 1,
          origin: window.location.origin,
        },
        events: {
          onReady: () => {
            this.ready = true;
            this.resolveReady?.(this.player);
            this.resolveReady = null;
            this.rejectReady = null;
            this.onReady?.();
          },
          onStateChange: (event) => {
            this.onStateChange?.(event.data, playerStateLabel(event.data));
          },
          onError: (event) => {
            if (!this.ready && this.rejectReady) {
              this.rejectReady(new Error(mapPlayerError(event.data)));
              this.rejectReady = null;
            }
            this.onError?.(mapPlayerError(event.data), event.data);
          },
        },
      });
    } catch (error) {
      this.player = null;
      this.readyPromise = null;
      this.resolveReady = null;
      this.rejectReady = null;
      throw error;
    }

    if (!this.player) {
      this.readyPromise = null;
      throw new Error("No fue posible crear el reproductor de YouTube.");
    }

    await this.readyPromise;
    return this.player;
  }

  async play(trackId) {
    if (!trackId) {
      throw new Error("La canción no tiene identificador de YouTube.");
    }
    const player = await this.mount();
    player.loadVideoById(trackId);
  }

  async resume() {
    const player = await this.mount();
    player.playVideo?.();
  }

  pause() {
    this.player?.pauseVideo?.();
  }

  seekTo(seconds) {
    this.player?.seekTo?.(seconds, true);
  }

  getCurrentTime() {
    return this.player?.getCurrentTime?.() ?? 0;
  }

  getDuration() {
    return this.player?.getDuration?.() ?? 0;
  }

  destroy() {
    this.player?.destroy?.();
    this.player = null;
    this.ready = false;
    this.readyPromise = null;
    this.resolveReady = null;
    this.rejectReady = null;
  }
}

export function mapPlayerError(code) {
  switch (Number(code)) {
    case 2:
      return "El identificador de la canción no es válido.";
    case 5:
      return "El navegador no puede reproducir este video.";
    case 100:
      return "La canción no existe o es privada.";
    case 101:
    case 150:
      return "El propietario no permite reproducir esta canción fuera de YouTube.";
    default:
      return "No fue posible reproducir esta canción.";
  }
}

export function playerStateLabel(code) {
  return STATE_LABELS[String(code)] ?? "Listo para reproducir";
}
