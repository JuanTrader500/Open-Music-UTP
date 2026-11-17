import { describe, expect, it, vi } from "vitest";

import {
  YouTubePlayer,
  mapPlayerError,
  playerStateLabel,
} from "./playerController";
import { formatDuration } from "../utils/format";

class FakePlayer {
  static instance = null;

  constructor(elementId, config) {
    this.elementId = elementId;
    this.config = config;
    this.loaded = [];
    this.destroyed = false;
    FakePlayer.instance = this;
    config.events.onReady();
  }

  loadVideoById(trackId) {
    this.loaded.push(trackId);
  }

  playVideo() {
    this.played = true;
  }

  pauseVideo() {
    this.paused = true;
  }

  seekTo(seconds, allowSeekAhead) {
    this.seeked = { seconds, allowSeekAhead };
  }

  getCurrentTime() {
    return 12;
  }

  getDuration() {
    return 200;
  }

  destroy() {
    this.destroyed = true;
  }
}

describe("YouTubePlayer", () => {
  it("crea el reproductor una sola vez y carga el video seleccionado", async () => {
    const controller = new YouTubePlayer({
      elementId: "player-test",
      loadApi: async () => ({ Player: FakePlayer }),
    });

    const player = await controller.mount();
    await controller.play("video123");

    expect(player).toBe(FakePlayer.instance);
    expect(FakePlayer.instance.elementId).toBe("player-test");
    expect(FakePlayer.instance.loaded).toEqual(["video123"]);
    expect(controller.ready).toBe(true);
  });

  it("rechaza una canción sin identificador", async () => {
    const controller = new YouTubePlayer({
      loadApi: async () => ({ Player: FakePlayer }),
    });

    await expect(controller.play("")).rejects.toThrow("identificador");
  });

  it("pausa, reanuda, busca dentro del video y expone el progreso", async () => {
    const controller = new YouTubePlayer({
      loadApi: async () => ({ Player: FakePlayer }),
    });

    await controller.mount();
    controller.pause();
    expect(FakePlayer.instance.paused).toBe(true);

    await controller.resume();
    expect(FakePlayer.instance.played).toBe(true);

    controller.seekTo(30);
    expect(FakePlayer.instance.seeked).toEqual({ seconds: 30, allowSeekAhead: true });
    expect(controller.getCurrentTime()).toBe(12);
    expect(controller.getDuration()).toBe(200);
  });

  it("traduce los errores de la IFrame API", () => {
    expect(mapPlayerError(2)).toMatch(/identificador/);
    expect(mapPlayerError(100)).toMatch(/no existe/);
    expect(mapPlayerError(101)).toMatch(/no permite/);
    expect(mapPlayerError(150)).toMatch(/no permite/);
    expect(mapPlayerError(999)).toMatch(/No fue posible/);
  });

  it("traduce los estados del reproductor", () => {
    expect(playerStateLabel(1)).toBe("Reproduciendo");
    expect(playerStateLabel(2)).toBe("En pausa");
    expect(playerStateLabel(0)).toBe("Finalizado");
  });

  it("formatea duraciones cortas y largas", () => {
    expect(formatDuration(0)).toBe("0:00");
    expect(formatDuration(215)).toBe("3:35");
    expect(formatDuration(3661)).toBe("1:01:01");
    expect(formatDuration(-5)).toBe("0:00");
  });
});
