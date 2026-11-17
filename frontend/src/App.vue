<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";

import TrackCard from "./components/TrackCard.vue";
import { createApiClient } from "./api/client";
import { YouTubePlayer } from "./player/playerController";
import { formatDuration } from "./utils/format";

const api = createApiClient();

const GITHUB_URL = "https://github.com/JuanTrader500/Open-Music-UTP";
const DEFAULT_QUERY = "rock";

const query = ref("");
const activeQuery = ref("");
const tracks = ref([]);
const loading = ref(false);
const searched = ref(false);
const hasUserSearched = ref(false);
const error = ref("");
const currentTrack = ref(null);
const playerStatus = ref("Selecciona una canción para empezar.");
const playerError = ref("");
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(0);

let progressTimer = null;

const quickSearches = [
  { label: "Mix diario", hint: "Tus géneros favoritos", query: "rock", mark: "01", tone: "lime" },
  { label: "Mix de estudio", hint: "Música para concentrarte", query: "study music", mark: "02", tone: "violet" },
  { label: "Enfoque", hint: "Para estudiar o programar", query: "instrumental", mark: "03", tone: "amber" },
  { label: "Relajación", hint: "Baja el ritmo después de clase", query: "chill", mark: "04", tone: "blue" },
  { label: "Noche", hint: "Sonidos para cerrar el día", query: "night", mark: "05", tone: "rose" },
  { label: "Descubrimiento", hint: "Algo nuevo cada día", query: "music", mark: "06", tone: "graphite" },
];

const mixes = [
  { title: "Mix diario 1", hint: "Según tus géneros y artistas favoritos", query: "rock", code: "mix_01", tone: "graphite" },
  { title: "Mix diario 2", hint: "Música nueva para tu día", query: "pop", code: "mix_02", tone: "lime" },
  { title: "Enfoque", hint: "Para estudiar o programar", query: "instrumental", code: "focus", tone: "stripe" },
  { title: "Relajación", hint: "Baja el ritmo después de clase", query: "chill", code: "chill", tone: "silver" },
  { title: "Noche", hint: "Sonidos tranquilos para cerrar el día", query: "night", code: "night", tone: "blue" },
];

const shortcuts = [
  { label: "Rock", query: "rock", tone: "lime" },
  { label: "Salsa", query: "salsa", tone: "amber" },
  { label: "Pop", query: "pop", tone: "rose" },
  { label: "The Beatles", query: "The Beatles", tone: "blue" },
];

const greeting = computed(() => {
  const hour = new Date().getHours();
  if (hour < 12) return "Buenos días";
  if (hour < 19) return "Buenas tardes";
  return "Buenas noches";
});

const selectedId = computed(() => currentTrack.value?.track_id ?? "");
const elapsedLabel = computed(() => formatDuration(Math.floor(currentTime.value)));
const durationLabel = computed(() =>
  formatDuration(Math.floor(duration.value || currentTrack.value?.duration_s || 0)),
);
const progressPercent = computed(() => {
  if (!duration.value) return 0;
  return Math.min(100, Math.max(0, (currentTime.value / duration.value) * 100));
});
const resultsTitle = computed(() =>
  hasUserSearched.value && activeQuery.value
    ? `Resultados para “${activeQuery.value}”`
    : "Tendencias desde YouTube",
);
const resultsHint = computed(() => {
  if (loading.value) return "Buscando…";
  if (tracks.value.length) return `${tracks.value.length} canciones`;
  return "Busca para descubrir música";
});

const player = new YouTubePlayer({
  onStateChange: (code, label) => {
    playerStatus.value = label;
    isPlaying.value = code === 1;

    if (code === 1 || code === 3) {
      startProgress();
    } else if (code === 2 || code === 0) {
      stopProgress();
    }
    if (code === 0) {
      currentTime.value = 0;
    }
  },
  onError: (message) => {
    playerError.value = message;
    playerStatus.value = "Sin reproducción";
    stopProgress();
  },
});

async function runSearch(rawQuery = query.value, { userInitiated = true } = {}) {
  const cleaned = rawQuery.trim();
  if (cleaned.length < 2) {
    error.value = "Escribe al menos 2 caracteres para buscar.";
    tracks.value = [];
    searched.value = false;
    return;
  }

  if (userInitiated) {
    query.value = cleaned;
    hasUserSearched.value = true;
  }
  activeQuery.value = cleaned;
  loading.value = true;
  error.value = "";
  playerError.value = "";

  try {
    const result = await api.searchTracks(cleaned, { limit: 12 });
    tracks.value = result.items ?? [];
    searched.value = true;
  } catch (requestError) {
    tracks.value = [];
    searched.value = false;
    error.value = requestError?.message || "No fue posible buscar canciones.";
  } finally {
    loading.value = false;
  }
}

function search() {
  return runSearch(query.value, { userInitiated: true });
}

function quickSearch(term) {
  query.value = term;
  return runSearch(term, { userInitiated: true });
}

function clearSearch() {
  query.value = "";
  activeQuery.value = "";
  tracks.value = [];
  searched.value = false;
  hasUserSearched.value = false;
  error.value = "";
}

async function playTrack(track) {
  currentTrack.value = track;
  duration.value = Number(track.duration_s) || 0;
  currentTime.value = 0;
  playerError.value = "";
  playerStatus.value = "Cargando canción...";

  try {
    // El contenedor del iframe se monta cuando aparece `currentTrack`.
    await nextTick();
    await player.play(track.track_id);
  } catch (playbackError) {
    playerError.value = playbackError?.message || "No fue posible iniciar la reproducción.";
    playerStatus.value = "Sin reproducción";
  }
}

async function togglePlayback() {
  if (!currentTrack.value) return;
  if (isPlaying.value) {
    player.pause();
    return;
  }

  playerError.value = "";
  try {
    if (player.ready) {
      await player.resume();
    } else {
      await player.play(currentTrack.value.track_id);
    }
  } catch (playbackError) {
    playerError.value = playbackError?.message || "No fue posible reanudar la reproducción.";
    playerStatus.value = "Sin reproducción";
  }
}

function seekTo(event) {
  const seconds = Number(event.target.value);
  if (!Number.isFinite(seconds)) return;
  currentTime.value = seconds;
  player.seekTo(seconds);
}

function syncProgress() {
  const nextTime = Number(player.getCurrentTime?.() ?? 0);
  const nextDuration = Number(player.getDuration?.() ?? 0);
  if (Number.isFinite(nextTime)) {
    currentTime.value = Math.max(0, nextTime);
  }
  if (Number.isFinite(nextDuration) && nextDuration > 0) {
    duration.value = nextDuration;
  }
}

function startProgress() {
  if (progressTimer || typeof window === "undefined") return;
  progressTimer = window.setInterval(syncProgress, 500);
}

function stopProgress() {
  if (!progressTimer) return;
  window.clearInterval(progressTimer);
  progressTimer = null;
}

function youtubeUrl(trackId) {
  return `https://www.youtube.com/watch?v=${encodeURIComponent(trackId)}`;
}

function focusSearch() {
  document.getElementById("track-query")?.focus();
}

function scrollToTop() {
  window.scrollTo?.({ top: 0, behavior: "smooth" });
}

onMounted(() => {
  // Carga las tendencias una vez para que la pantalla no arranque vacía.
  runSearch(DEFAULT_QUERY, { userInitiated: false });
});

onBeforeUnmount(() => {
  stopProgress();
  player.destroy();
});
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar" aria-label="Navegación principal">
      <div class="sidebar__panel sidebar__brand-panel">
        <button class="brand" type="button" @click="scrollToTop">
          <span class="brand__mark" aria-hidden="true">&lt;/&gt;</span>
          <span class="brand__text">Open Music <strong>UTP</strong></span>
        </button>
      </div>

      <div class="sidebar__panel sidebar__nav-panel">
        <nav class="nav" aria-label="Secciones">
          <button class="nav__item" type="button" @click="scrollToTop">
            <span class="nav__icon" aria-hidden="true">⌂</span>
            Inicio
          </button>
          <button class="nav__item nav__item--active" type="button" @click="focusSearch">
            <span class="nav__icon" aria-hidden="true">⌕</span>
            Buscar
            <span class="nav__dot" aria-hidden="true"></span>
          </button>
          <button
            class="nav__item"
            type="button"
            disabled
            title="Disponible cuando se integre el inicio de sesión"
          >
            <span class="nav__icon" aria-hidden="true">▤</span>
            Tu biblioteca
            <span class="nav__soon">Pronto</span>
          </button>
        </nav>
      </div>

      <div class="sidebar__panel sidebar__shortcuts">
        <p class="sidebar__label">Búsquedas rápidas</p>
        <button
          v-for="item in shortcuts"
          :key="item.query"
          class="shortcut"
          type="button"
          @click="quickSearch(item.query)"
        >
          <span class="shortcut__cover" :class="`shortcut__cover--${item.tone}`" aria-hidden="true"></span>
          <span class="shortcut__copy">
            <span class="shortcut__title">{{ item.label }}</span>
            <span class="shortcut__hint">Búsqueda</span>
          </span>
        </button>
        <p class="sidebar__note">Las playlists y el inicio de sesión llegarán en la siguiente fase.</p>
      </div>

      <div class="sidebar__footer">
        <span class="chip">MIT</span>
        <span class="chip">v0.4</span>
        <span class="chip">self-hosted</span>
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <form class="search-form" role="search" @submit.prevent="search">
          <button
            class="search-form__icon"
            type="button"
            :disabled="loading"
            aria-label="Buscar canciones"
            title="Buscar"
            @click="search"
          >
            <span aria-hidden="true">⌕</span>
          </button>
          <label class="sr-only" for="track-query">Buscar canciones</label>
          <input
            id="track-query"
            v-model="query"
            type="search"
            name="q"
            placeholder="¿Qué quieres escuchar?"
            autocomplete="off"
            :disabled="loading"
          />
          <kbd class="search-form__kbd" aria-hidden="true">↵</kbd>
        </form>

        <div class="topbar__actions">
          <a class="topbar__button topbar__button--ghost" :href="GITHUB_URL" target="_blank" rel="noreferrer">
            <span class="topbar__button-icon" aria-hidden="true">◉</span>
            Fork en GitHub
          </a>
          <a class="topbar__button topbar__button--accent" :href="GITHUB_URL" target="_blank" rel="noreferrer">
            Contribuir
          </a>
          <span class="avatar" title="Open Music UTP">UTP</span>
        </div>
      </header>

      <div class="main__content">
        <section class="hero" aria-labelledby="greeting-title">
          <p class="hero__eyebrow">Tu música, tu ritmo</p>
          <h1 id="greeting-title">{{ greeting }}</h1>
          <p class="hero__subtitle">
            Busca canciones reales de YouTube y escúchalas sin salir de la página.
          </p>

          <div class="quick-grid">
            <button
              v-for="item in quickSearches"
              :key="item.label"
              class="quick-card"
              :class="`quick-card--${item.tone}`"
              type="button"
              @click="quickSearch(item.query)"
            >
              <span class="quick-card__mark" aria-hidden="true">{{ item.mark }}</span>
              <span class="quick-card__copy">
                <span class="quick-card__label">{{ item.label }}</span>
                <span class="quick-card__hint">{{ item.hint }}</span>
              </span>
              <span class="quick-card__arrow" aria-hidden="true">↗</span>
            </button>
          </div>
        </section>

        <p v-if="error" class="alert" role="alert">{{ error }}</p>

        <section v-if="currentTrack" class="now-playing" aria-label="Canción actual">
          <div class="now-playing__video">
            <div id="youtube-player"></div>
            <div class="now-playing__video-badge">Video de YouTube</div>
          </div>
          <div class="player__details now-playing__details">
            <p class="eyebrow">Ahora suena</p>
            <h2>{{ currentTrack.title }}</h2>
            <p class="now-playing__meta">
              {{ currentTrack.artist.name }} <span aria-hidden="true">·</span> {{ currentTrack.genre.name }}
            </p>
            <p class="now-playing__status" role="status">{{ playerStatus }}</p>
            <p v-if="playerError" class="player__error" role="alert">{{ playerError }}</p>
            <a
              class="now-playing__link"
              :href="youtubeUrl(currentTrack.track_id)"
              target="_blank"
              rel="noreferrer"
            >
              Abrir en YouTube ↗
            </a>
          </div>
        </section>

        <section class="section" aria-labelledby="for-you-title">
          <div class="section__header">
            <h2 id="for-you-title" class="section__title">Hecho para ti</h2>
            <span class="section__hint">Mezclas para descubrir</span>
          </div>
          <div class="mix-grid">
            <button
              v-for="mix in mixes"
              :key="mix.code"
              class="mix-card"
              type="button"
              @click="quickSearch(mix.query)"
            >
              <span class="mix-card__art" :class="`mix-card__art--${mix.tone}`" aria-hidden="true">
                {{ mix.code }}
              </span>
              <span class="mix-card__title">{{ mix.title }}</span>
              <span class="mix-card__hint">{{ mix.hint }}</span>
            </button>
          </div>
        </section>

        <section class="section results" aria-labelledby="results-title">
          <div class="section__header">
            <h2 id="results-title" class="section__title">{{ resultsTitle }}</h2>
            <div class="section__actions">
              <span class="section__hint">{{ resultsHint }}</span>
              <button v-if="hasUserSearched" class="section__clear" type="button" @click="clearSearch">
                Limpiar
              </button>
            </div>
          </div>

          <div v-if="loading" class="state state--loading" role="status">
            <span class="state__spinner" aria-hidden="true"></span>
            Buscando canciones…
          </div>

          <div v-else-if="searched && !tracks.length && !error" class="state">
            No encontramos canciones embebibles para esa búsqueda.
          </div>

          <div v-else-if="tracks.length" class="track-grid">
            <TrackCard
              v-for="track in tracks"
              :key="track.track_id"
              :track="track"
              :active="track.track_id === selectedId"
              @play="playTrack"
            />
          </div>

          <div v-else class="state state--empty">
            <span class="state__icon" aria-hidden="true">♪</span>
            <p class="state__title">Descubre tu próxima canción</p>
            <p>Prueba con rock, salsa o The Beatles.</p>
            <div class="state__chips">
              <button type="button" @click="quickSearch('rock')">rock</button>
              <button type="button" @click="quickSearch('salsa')">salsa</button>
              <button type="button" @click="quickSearch('The Beatles')">The Beatles</button>
            </div>
          </div>
        </section>

        <section class="promo">
          <p class="promo__code">
            <span>$ git clone open-music-utp</span>
            <span>$ docker compose up</span>
          </p>
          <div class="promo__copy">
            <h2>Código abierto. Música de todos.</h2>
            <p>
              Open Music UTP es software libre bajo licencia MIT. Revisa el código,
              repórtalo, mejóralo o hospédalo tú mismo.
            </p>
          </div>
          <a class="promo__button" :href="GITHUB_URL" target="_blank" rel="noreferrer">
            Ver repositorio
          </a>
        </section>
      </div>
    </div>

    <footer class="player-bar" aria-label="Reproductor de música">
      <div class="player-bar__track">
        <div class="player-bar__cover" :class="{ 'player-bar__cover--active': currentTrack }">
          <img
            v-if="currentTrack?.thumbnail_url"
            :src="currentTrack.thumbnail_url"
            alt=""
            aria-hidden="true"
          />
          <span v-else aria-hidden="true">♪</span>
        </div>
        <div class="player-bar__copy">
          <p class="player-bar__title">{{ currentTrack?.title || "Nada reproduciéndose" }}</p>
          <p class="player-bar__artist">
            {{ currentTrack?.artist.name || "Selecciona una canción de la lista" }}
          </p>
        </div>
      </div>

      <div class="player-bar__center">
        <div class="player-bar__controls">
          <button
            class="player-bar__play"
            type="button"
            :disabled="!currentTrack"
            :aria-label="isPlaying ? 'Pausar canción' : 'Reproducir canción'"
            @click="togglePlayback"
          >
            <span v-if="isPlaying" aria-hidden="true">❚❚</span>
            <span v-else aria-hidden="true">▶</span>
          </button>
        </div>
        <div class="player-bar__timeline">
          <span>{{ elapsedLabel }}</span>
          <input
            class="player-bar__range"
            type="range"
            min="0"
            :max="duration || 0"
            step="1"
            :value="currentTime"
            :disabled="!currentTrack || !duration"
            aria-label="Progreso de la canción"
            :style="{ '--progress': `${progressPercent}%` }"
            @input="seekTo"
          />
          <span>{{ durationLabel }}</span>
        </div>
      </div>

      <div class="player-bar__right">
        <span class="player-bar__source">fuente: YouTube</span>
        <a
          v-if="currentTrack"
          class="player-bar__link"
          :href="youtubeUrl(currentTrack.track_id)"
          target="_blank"
          rel="noreferrer"
          aria-label="Abrir la canción en YouTube"
        >
          ↗
        </a>
        <span class="player-bar__status" role="status">{{ playerStatus }}</span>
      </div>
    </footer>
  </div>
</template>
