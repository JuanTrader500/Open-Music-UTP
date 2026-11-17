import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App.vue";

const mocks = vi.hoisted(() => ({
  searchTracks: vi.fn(),
  play: vi.fn(),
  resume: vi.fn(),
  pause: vi.fn(),
  seekTo: vi.fn(),
  getCurrentTime: vi.fn(() => 0),
  getDuration: vi.fn(() => 0),
  destroy: vi.fn(),
}));

vi.mock("./api/client", () => ({
  createApiClient: () => ({
    searchTracks: mocks.searchTracks,
  }),
}));

vi.mock("./player/playerController", () => ({
  YouTubePlayer: class {
    ready = false;
    play = mocks.play;
    resume = mocks.resume;
    pause = mocks.pause;
    seekTo = mocks.seekTo;
    getCurrentTime = mocks.getCurrentTime;
    getDuration = mocks.getDuration;
    destroy = mocks.destroy;
  },
}));

const track = {
  track_id: "abc123",
  title: "Fuego en la Avenida",
  artist: { id: 1, name: "Los Cafeteros Eléctricos" },
  genre: { id: 1, code: "rock", name: "Rock" },
  duration_s: 215,
  view_count: 1200000,
  like_count: 40000,
  thumbnail_url: "https://i.ytimg.com/vi/abc123/mqdefault.jpg",
  is_embeddable: true,
};

async function searchFor(wrapper, query = "rock") {
  await wrapper.find("#track-query").setValue(query);
  await wrapper.find("form").trigger("submit");
  await flushPromises();
}

describe("App", () => {
  beforeEach(() => {
    mocks.searchTracks.mockReset();
    mocks.play.mockReset();
    mocks.resume.mockReset();
    mocks.pause.mockReset();
    mocks.seekTo.mockReset();
    mocks.getCurrentTime.mockReset();
    mocks.getDuration.mockReset();
    mocks.destroy.mockReset();
    mocks.getCurrentTime.mockReturnValue(0);
    mocks.getDuration.mockReturnValue(0);
    mocks.searchTracks.mockResolvedValue({ items: [], total: 0, query: "" });
  });

  it("carga las tendencias al abrir la página", async () => {
    const wrapper = mount(App);
    await flushPromises();

    expect(mocks.searchTracks).toHaveBeenCalledWith("rock", { limit: 12 });
    expect(wrapper.text()).toContain("Tendencias desde YouTube");

    wrapper.unmount();
  });

  it("envía la búsqueda al pulsar el botón de la lupa", async () => {
    const wrapper = mount(App);
    await flushPromises();
    mocks.searchTracks.mockClear();

    await wrapper.find("#track-query").setValue("salsa");
    await wrapper.find(".search-form__icon").trigger("click");
    await flushPromises();

    expect(mocks.searchTracks).toHaveBeenCalledWith("salsa", { limit: 12 });
    wrapper.unmount();
  });

  it("muestra la miniatura y reproduce la tarjeta seleccionada", async () => {
    mocks.searchTracks.mockResolvedValue({
      items: [track],
      total: 1,
      query: "rock",
    });
    const wrapper = mount(App);
    await flushPromises();

    await searchFor(wrapper);

    expect(mocks.searchTracks).toHaveBeenCalledWith("rock", { limit: 12 });
    expect(wrapper.find(".track-card__thumb img").attributes("src")).toBe(
      track.thumbnail_url,
    );
    expect(wrapper.text()).toContain("Los Cafeteros Eléctricos");
    expect(wrapper.text()).toContain("3:35");

    await wrapper.find(".track-card__button").trigger("click");
    await flushPromises();

    expect(mocks.play).toHaveBeenCalledWith("abc123");
    expect(wrapper.find(".player__details").text()).toContain(track.title);

    wrapper.unmount();
    expect(mocks.destroy).toHaveBeenCalled();
  });

  it("muestra el error del backend", async () => {
    mocks.searchTracks.mockRejectedValue(new Error("La base de datos no responde."));
    const wrapper = mount(App);
    await flushPromises();

    await searchFor(wrapper);

    expect(wrapper.find(".alert").text()).toBe("La base de datos no responde.");
  });

  it("valida que la búsqueda tenga al menos dos caracteres", async () => {
    const wrapper = mount(App);
    await flushPromises();
    mocks.searchTracks.mockClear();

    await searchFor(wrapper, "a");

    expect(mocks.searchTracks).not.toHaveBeenCalled();
    expect(wrapper.find(".alert").text()).toContain("al menos 2 caracteres");
  });
});
