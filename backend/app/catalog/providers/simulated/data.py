"""Catálogo ficticio en memoria para pruebas sin red (RNF-033)."""
from app.catalog.providers.models import TrackMetadata

SIMULATED_TRACKS: list[TrackMetadata] = [
    TrackMetadata(track_id="sim_rock_01", title="Fuego en la Avenida", channel_title="Los Cafeteros Eléctricos", duration_s=215, view_count=1_200_000, like_count=40_000, thumbnail_url="https://example.com/sim_rock_01.jpg"),
    TrackMetadata(track_id="sim_rock_02", title="Carretera sin Fin", channel_title="Los Cafeteros Eléctricos", duration_s=243, view_count=800_000, like_count=22_000, thumbnail_url="https://example.com/sim_rock_02.jpg"),
    TrackMetadata(track_id="sim_rock_03", title="Rock del Eje", channel_title="Tormenta Cafetera", duration_s=198, view_count=450_000, like_count=9_000, thumbnail_url="https://example.com/sim_rock_03.jpg"),
    TrackMetadata(track_id="sim_pop_01", title="Luces de Pereira", channel_title="Valentina Mora", duration_s=187, view_count=3_400_000, like_count=120_000, thumbnail_url="https://example.com/sim_pop_01.jpg"),
    TrackMetadata(track_id="sim_pop_02", title="Verano Digital", channel_title="Valentina Mora", duration_s=205, view_count=2_100_000, like_count=75_000, thumbnail_url="https://example.com/sim_pop_02.jpg"),
    TrackMetadata(track_id="sim_salsa_01", title="Baila Conmigo", channel_title="Orquesta Río Otún", duration_s=260, view_count=2_800_000, like_count=90_000, thumbnail_url="https://example.com/sim_salsa_01.jpg"),
    TrackMetadata(track_id="sim_salsa_02", title="Noche de Salsa", channel_title="Orquesta Río Otún", duration_s=277, view_count=1_500_000, like_count=51_000, thumbnail_url="https://example.com/sim_salsa_02.jpg"),
    TrackMetadata(track_id="sim_broken_01", title="Video No Embebible", channel_title="Canal Restringido", duration_s=190, view_count=10, like_count=0, is_embeddable=False),
]

# Playlists semilla simuladas -> ids de video
SIMULATED_PLAYLISTS: dict[str, list[str]] = {
    "PL_SIM_ROCK": ["sim_rock_01", "sim_rock_02", "sim_rock_03"],
    "PL_SIM_POP": ["sim_pop_01", "sim_pop_02"],
    "PL_SIM_SALSA": ["sim_salsa_01", "sim_salsa_02", "sim_broken_01"],
}
