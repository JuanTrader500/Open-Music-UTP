<script setup>
import { computed, ref, watch } from "vue";

import { formatDuration } from "../utils/format";

const props = defineProps({
  track: {
    type: Object,
    required: true,
  },
  active: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["play"]);

const imageFailed = ref(false);
const durationLabel = computed(() => formatDuration(props.track.duration_s));
const fallbackLetter = computed(() => (props.track.title || "♪").trim().charAt(0).toUpperCase());

watch(
  () => props.track.thumbnail_url,
  () => {
    imageFailed.value = false;
  },
);
</script>

<template>
  <article class="track-card" :class="{ 'track-card--active': active }">
    <button
      class="track-card__button"
      type="button"
      :aria-label="`Reproducir ${track.title} de ${track.artist.name}`"
      :aria-pressed="active"
      @click="emit('play', track)"
    >
      <span class="track-card__thumb">
        <img
          v-if="track.thumbnail_url && !imageFailed"
          :src="track.thumbnail_url"
          :alt="`Miniatura de ${track.title}`"
          loading="lazy"
          decoding="async"
          @error="imageFailed = true"
        />
        <span v-else class="track-card__placeholder" aria-hidden="true">
          {{ fallbackLetter }}
        </span>

        <span class="track-card__duration" aria-hidden="true">{{ durationLabel }}</span>
        <span class="track-card__play" aria-hidden="true">▶</span>
      </span>

      <span class="track-card__body">
        <span class="track-card__title" :title="track.title">{{ track.title }}</span>
        <span class="track-card__artist" :title="track.artist.name">{{ track.artist.name }}</span>
        <span class="track-card__meta">
          <span>{{ track.genre.name }}</span>
          <span>{{ durationLabel }}</span>
        </span>
      </span>
    </button>
  </article>
</template>
