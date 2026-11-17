"""Paridad entre los modelos ORM y el esquema PostgreSQL (F0-10).

Compara la metadata declarativa y la base de pruebas real: tablas, columnas,
tipos, nulabilidad, claves, checks e índices del esquema v6.
"""

from __future__ import annotations

from sqlalchemy import inspect

from app.core.base import Base

EXPECTED_COLUMNS: dict[str, set[str]] = {
    "genres": {"id", "code", "name"},
    "artists": {"id", "name", "name_normalized"},
    "tracks": {
        "track_id",
        "title",
        "artist_id",
        "genre_id",
        "genre_source",
        "duration_s",
        "view_count",
        "like_count",
        "thumbnail_url",
        "is_embeddable",
        "updated_at",
    },
    "genre_seeds": {"playlist_id", "genre_id"},
    "users": {"id", "email", "password_hash", "is_simulated", "created_at"},
    "user_genre_preferences": {"user_id", "genre_id", "initial_weight"},
    "user_artist_preferences": {"user_id", "artist_id", "initial_weight"},
    "playlists": {"id", "user_id", "name", "created_at"},
    "playlist_tracks": {"id", "playlist_id", "track_id", "position"},
    "favorites": {"user_id", "track_id"},
    "listening_events": {
        "id",
        "user_id",
        "track_id",
        "started_at",
        "seconds_listened",
        "duration_s",
        "fraction_listened",
        "skipped",
        "session_id",
        "is_simulated",
    },
}

EXPECTED_PRIMARY_KEYS: dict[str, set[str]] = {
    "genres": {"id"},
    "artists": {"id"},
    "tracks": {"track_id"},
    "genre_seeds": {"playlist_id"},
    "users": {"id"},
    "user_genre_preferences": {"user_id", "genre_id"},
    "user_artist_preferences": {"user_id", "artist_id"},
    "playlists": {"id"},
    "playlist_tracks": {"id"},
    "favorites": {"user_id", "track_id"},
    "listening_events": {"id"},
}

EXPECTED_FOREIGN_KEYS: dict[str, set[tuple[str, str, str | None]]] = {
    "tracks": {
        ("artist_id", "artists", "RESTRICT"),
        ("genre_id", "genres", "RESTRICT"),
    },
    "genre_seeds": {("genre_id", "genres", "RESTRICT")},
    "user_genre_preferences": {
        ("user_id", "users", "CASCADE"),
        ("genre_id", "genres", "CASCADE"),
    },
    "user_artist_preferences": {
        ("user_id", "users", "CASCADE"),
        ("artist_id", "artists", "CASCADE"),
    },
    "playlists": {("user_id", "users", "CASCADE")},
    "playlist_tracks": {
        ("playlist_id", "playlists", "CASCADE"),
        ("track_id", "tracks", "RESTRICT"),
    },
    "favorites": {
        ("user_id", "users", "CASCADE"),
        ("track_id", "tracks", "RESTRICT"),
    },
    "listening_events": {
        ("user_id", "users", "CASCADE"),
        ("track_id", "tracks", "RESTRICT"),
    },
}

EXPECTED_CHECKS: dict[str, set[str]] = {
    "users": {"users_email_check"},
    "tracks": {
        "tracks_genre_source_check",
        "tracks_duration_s_check",
        "tracks_view_count_check",
        "tracks_like_count_check",
    },
    "playlists": {"playlists_name_check"},
    "playlist_tracks": {"playlist_tracks_position_check"},
    "listening_events": {
        "listening_events_seconds_listened_check",
        "listening_events_duration_s_check",
        "listening_events_fraction_listened_check",
    },
    "user_genre_preferences": {"user_genre_preferences_initial_weight_check"},
    "user_artist_preferences": {"user_artist_preferences_initial_weight_check"},
}

EXPECTED_INDEXES: dict[str, set[str]] = {
    "tracks": {
        "ix_tracks_genre_views",
        "ix_tracks_views",
        "ix_tracks_artist",
        "ix_tracks_genre_artist",
    },
    "playlists": {"ix_playlists_user"},
    "listening_events": {"ix_events_user_started", "ix_events_user_track"},
}

TYPE_NAMES = {
    "Uuid": "UUID",
    "String": "VARCHAR",
    "SmallInteger": "SMALLINT",
    "BigInteger": "BIGINT",
    "Integer": "INTEGER",
    "DateTime": "TIMESTAMP",
    "Boolean": "BOOLEAN",
    "Numeric": "NUMERIC",
}


def _db_type_name(type_repr: object) -> str:
    """Extrae el nombre base del tipo que reporta el inspector."""
    return str(type_repr).split("(")[0].split()[0].upper()


def test_metadata_declara_las_11_tablas_y_sus_columnas():
    assert set(Base.metadata.tables) == set(EXPECTED_COLUMNS)
    for table_name, columns in EXPECTED_COLUMNS.items():
        assert set(Base.metadata.tables[table_name].columns.keys()) == columns


def test_base_de_datos_coincide_con_la_metadata(test_engine):
    inspector = inspect(test_engine)

    assert set(inspector.get_table_names()) == set(EXPECTED_COLUMNS)

    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        db_columns = {column["name"]: column for column in inspector.get_columns(table_name)}
        assert set(db_columns) == expected_columns, table_name
        for column in Base.metadata.tables[table_name].columns:
            db_column = db_columns[column.name]
            expected_type = TYPE_NAMES[type(column.type).__name__]
            assert _db_type_name(db_column["type"]) == expected_type, (
                f"{table_name}.{column.name}: {db_column['type']!r}"
            )
            assert db_column["nullable"] == column.nullable, f"{table_name}.{column.name}"


def test_claves_primarias(test_engine):
    inspector = inspect(test_engine)
    for table_name, expected in EXPECTED_PRIMARY_KEYS.items():
        actual = set(inspector.get_pk_constraint(table_name)["constrained_columns"])
        assert actual == expected, table_name


def test_claves_foraneas(test_engine):
    inspector = inspect(test_engine)
    for table_name, expected in EXPECTED_FOREIGN_KEYS.items():
        actual = {
            (
                foreign_key["constrained_columns"][0],
                foreign_key["referred_table"],
                foreign_key["options"].get("ondelete"),
            )
            for foreign_key in inspector.get_foreign_keys(table_name)
        }
        assert actual == expected, table_name


def test_restricciones_check(test_engine):
    inspector = inspect(test_engine)
    for table_name, expected in EXPECTED_CHECKS.items():
        actual = {check["name"] for check in inspector.get_check_constraints(table_name)}
        assert expected <= actual, table_name


def test_indices(test_engine):
    inspector = inspect(test_engine)
    for table_name, expected in EXPECTED_INDEXES.items():
        actual = {index["name"] for index in inspector.get_indexes(table_name)}
        assert expected <= actual, table_name
