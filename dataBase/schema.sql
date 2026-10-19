-- =====================================================================
-- Open Music UTP · schema.sql v6 · PostgreSQL 16
-- Basadode en SRS-RMW-001 v0.4: sección 3.5 y reglas RN-003/004/005/010/014/015.
-- v5: la tabla artists ya no depende de genres (se elimina artists.genre_id).
-- v6: tracks.video_id pasa a llamarse track_id (también en las tablas que la referencian).
-- Ejecución: psql -v ON_ERROR_STOP=1 -d openmusic -f schema.sql
--
-- Convenciones
--   * Un solo esquema (public). Ninguna columna admite NULL.
--   * No hay triggers: los límites y umbrales configurables (RN-005, RN-010)
--     se validan en el backend y se leen del archivo de configuración (SRS 1.5).
-- =====================================================================
BEGIN;

-- ---------------------------------------------------------------------
-- 1. CATÁLOGO (datos globales, compartidos por todos los usuarios)
-- ---------------------------------------------------------------------

-- Lista cerrada de géneros (RF-011, RN-009)
CREATE TABLE genres (
    id    SMALLINT    GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code  VARCHAR(30) NOT NULL UNIQUE,
    name  VARCHAR(60) NOT NULL
);

-- Artistas: tabla independiente, no depende de ninguna otra. El género de un artista
-- no se guarda: se deduce de sus canciones (tracks.genre_id). El nombre normalizado
-- evita duplicados (SRS 3.5).
-- Artistas de un género (por ejemplo, para el onboarding, RF-021):
--   SELECT DISTINCT a.* FROM artists a JOIN tracks t ON t.artist_id = a.id WHERE t.genre_id = :genre_id;
CREATE TABLE artists (
    id               BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name             VARCHAR(200) NOT NULL,
    name_normalized  VARCHAR(200) NOT NULL UNIQUE             -- lower(btrim(name))
);

-- Canciones: un video de música de YouTube (RF-010, RF-011, RF-012)
CREATE TABLE tracks (
    track_id       VARCHAR(32)   PRIMARY KEY,                 -- se llena con el id del video que entrega YouTube; único (RNF-015)
    title          VARCHAR(300)  NOT NULL,
    artist_id      BIGINT        NOT NULL REFERENCES artists (id) ON DELETE RESTRICT,
    genre_id       SMALLINT      NOT NULL REFERENCES genres  (id) ON DELETE RESTRICT,
    genre_source   VARCHAR(20)   NOT NULL
                   CHECK (genre_source IN ('seed', 'artist', 'youtube_category', 'unclassified')),  -- RF-011; 'artist' = inferido de otras canciones del mismo artista
    duration_s     INTEGER       NOT NULL CHECK (duration_s >= 0),
    view_count     BIGINT        NOT NULL DEFAULT 0 CHECK (view_count >= 0),
    like_count     BIGINT        NOT NULL DEFAULT 0 CHECK (like_count >= 0),
    thumbnail_url  VARCHAR(2048) NOT NULL,
    is_embeddable  BOOLEAN       NOT NULL DEFAULT TRUE,       -- FALSE = no reproducible (RN-012)
    updated_at     TIMESTAMPTZ   NOT NULL DEFAULT now()       -- última vez que se refrescó desde YouTube
);

-- Playlists públicas de YouTube que llenan el catálogo, con su género (RF-011)
CREATE TABLE genre_seeds (
    playlist_id  VARCHAR(64) PRIMARY KEY,
    genre_id     SMALLINT    NOT NULL REFERENCES genres (id) ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------
-- 2. USUARIOS Y SUS DATOS (RN-003: se guardan por cuenta)
--    Todo lo de esta sección se borra con la cuenta (RN-015).
-- ---------------------------------------------------------------------

CREATE TABLE users (
    id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email          VARCHAR(254) NOT NULL UNIQUE CHECK (email = lower(email)),   -- RN-004
    password_hash  VARCHAR(255) NOT NULL,                     -- Argon2id o bcrypt (RNF-026)
    is_simulated   BOOLEAN      NOT NULL DEFAULT FALSE,       -- RN-014
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Géneros elegidos en el onboarding (RF-021). Un usuario puede elegir los que quiera.
CREATE TABLE user_genre_preferences (
    user_id         UUID         NOT NULL REFERENCES users  (id) ON DELETE CASCADE,
    genre_id        SMALLINT     NOT NULL REFERENCES genres (id) ON DELETE CASCADE,
    initial_weight  NUMERIC(6,2) NOT NULL DEFAULT 10 CHECK (initial_weight > 0),  -- 10 min virtuales (RN-007)
    PRIMARY KEY (user_id, genre_id)
);

-- Artistas elegidos en el onboarding (RF-021). Un usuario puede elegir los que quiera.
CREATE TABLE user_artist_preferences (
    user_id         UUID         NOT NULL REFERENCES users   (id) ON DELETE CASCADE,
    artist_id       BIGINT       NOT NULL REFERENCES artists (id) ON DELETE CASCADE,
    initial_weight  NUMERIC(6,2) NOT NULL DEFAULT 5 CHECK (initial_weight > 0),   -- 5 min virtuales (RN-007)
    PRIMARY KEY (user_id, artist_id)
);

-- Playlists del usuario registrado (RF-013). Máx. 50 por usuario (RN-010): lo valida el backend.
CREATE TABLE playlists (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name        VARCHAR(80) NOT NULL CHECK (length(btrim(name)) >= 1),          -- 1 a 80 caracteres
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Canciones de una playlist (RF-014, RF-015). Máx. 500 por playlist (RN-010): lo valida el backend.
-- Tiene clave propia porque una canción puede repetirse en la misma playlist tras confirmar (RF-014).
CREATE TABLE playlist_tracks (
    id           BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    playlist_id  UUID        NOT NULL REFERENCES playlists (id) ON DELETE CASCADE,
    track_id     VARCHAR(32) NOT NULL REFERENCES tracks (track_id) ON DELETE RESTRICT,
    position     INTEGER     NOT NULL CHECK (position >= 1),
    -- Diferible para poder reordenar (intercambiar posiciones) dentro de una transacción (RF-015)
    UNIQUE (playlist_id, position) DEFERRABLE INITIALLY DEFERRED
);

-- Favoritos del usuario registrado (RF-016): un par (usuario, canción) una sola vez
CREATE TABLE favorites (
    user_id   UUID        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    track_id  VARCHAR(32) NOT NULL REFERENCES tracks (track_id) ON DELETE RESTRICT,
    PRIMARY KEY (user_id, track_id)
);

-- Tiempo realmente escuchado de cada pista (RF-023)
CREATE TABLE listening_events (
    id                 BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id            UUID         NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    track_id           VARCHAR(32)  NOT NULL REFERENCES tracks (track_id) ON DELETE RESTRICT,
    started_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    seconds_listened   INTEGER      NOT NULL CHECK (seconds_listened >= 0),
    duration_s         INTEGER      NOT NULL CHECK (duration_s >= 0),
    fraction_listened  NUMERIC(5,4) NOT NULL CHECK (fraction_listened BETWEEN 0 AND 1),  -- seconds_listened / duration_s
    skipped            BOOLEAN      NOT NULL,                  -- TRUE si se escuchó menos del umbral (RN-005, 30 s)
    session_id         UUID         NOT NULL,
    is_simulated       BOOLEAN      NOT NULL DEFAULT FALSE     -- RN-014
);

-- ---------------------------------------------------------------------
-- 3. ÍNDICES
-- ---------------------------------------------------------------------
-- Recomendaciones: canciones más vistas de un género (RF-026) y del catálogo (RF-027)
CREATE INDEX ix_tracks_genre_views ON tracks (genre_id, view_count DESC) WHERE is_embeddable;
CREATE INDEX ix_tracks_views       ON tracks (view_count DESC)           WHERE is_embeddable;
CREATE INDEX ix_tracks_artist      ON tracks (artist_id);
-- Artistas de un género (onboarding, RF-021): el género del artista se deduce de sus canciones
CREATE INDEX ix_tracks_genre_artist ON tracks (genre_id, artist_id);
-- Biblioteca del usuario
CREATE INDEX ix_playlists_user     ON playlists (user_id);
-- Historial y resumen de escucha (RF-024) y «lo que aún no ha escuchado» (RF-026)
CREATE INDEX ix_events_user_started ON listening_events (user_id, started_at DESC);
CREATE INDEX ix_events_user_track   ON listening_events (user_id, track_id);

-- ---------------------------------------------------------------------
-- 4. DATOS SEMILLA
-- ---------------------------------------------------------------------

-- 4.1 Lista cerrada de géneros (TBD-07): 44 géneros + «sin clasificar»
INSERT INTO genres (code, name) VALUES
    ('rock', 'Rock'),
    ('hard_rock', 'Hard rock'),
    ('metal', 'Metal'),
    ('punk', 'Punk'),
    ('alternative_rock', 'Rock alternativo'),
    ('indie', 'Indie'),
    ('pop', 'Pop'),
    ('hip_hop', 'Hip hop'),
    ('trap', 'Trap'),
    ('r_and_b', 'R&B'),
    ('soul_funk', 'Soul y funk'),
    ('disco', 'Disco'),
    ('country', 'Country'),
    ('folk', 'Folk'),
    ('blues', 'Blues'),
    ('jazz', 'Jazz'),
    ('bossa_nova', 'Bossa nova'),
    ('clasica', 'Música clásica'),
    ('reggae', 'Reggae'),
    ('reggaeton', 'Reguetón'),
    ('latin_pop', 'Pop latino'),
    ('balada', 'Balada'),
    ('salsa', 'Salsa'),
    ('vallenato', 'Vallenato'),
    ('cumbia', 'Cumbia'),
    ('bachata', 'Bachata'),
    ('merengue', 'Merengue'),
    ('k_pop', 'K-pop'),
    ('edm', 'EDM'),
    ('house', 'House'),
    ('deep_house', 'Deep house'),
    ('tech_house', 'Tech house'),
    ('progressive_house', 'Progressive house'),
    ('trance', 'Trance'),
    ('drum_and_bass', 'Drum and bass'),
    ('dubstep', 'Dubstep'),
    ('techno', 'Techno'),
    ('minimal_techno', 'Minimal techno'),
    ('detroit_techno', 'Detroit techno'),
    ('acid_techno', 'Acid techno'),
    ('hard_techno', 'Hard techno'),
    ('melodic_techno', 'Melodic techno'),
    ('industrial_techno', 'Industrial techno'),
    ('dub_techno', 'Dub techno'),
    ('sin_clasificar', 'Sin clasificar');   -- «sin clasificar» (RN-009) no entra en recomendaciones por género

-- 4.2 Artistas semilla: 10 por bloque, en orden aproximado de fama (lista editorial, ajústala).
--     Los artistas ya no llevan género; los comentarios de bloque solo ordenan la lista.
--     name_normalized = lower(btrim(name)); los apóstrofes se escapan duplicándolos.
INSERT INTO artists (name, name_normalized)
SELECT s.n, lower(btrim(s.n))
FROM (VALUES
    -- Rock
    ('The Beatles'), ('The Rolling Stones'), ('Queen'), ('Pink Floyd'), ('The Who'),
    ('Bruce Springsteen'), ('U2'), ('Fleetwood Mac'), ('The Doors'), ('David Bowie'),
    -- Hard rock
    ('Led Zeppelin'), ('AC/DC'), ('Guns N'' Roses'), ('Deep Purple'), ('Aerosmith'),
    ('Van Halen'), ('Kiss'), ('Bon Jovi'), ('Def Leppard'), ('Whitesnake'),
    -- Metal
    ('Metallica'), ('Iron Maiden'), ('Black Sabbath'), ('Slayer'), ('Megadeth'), ('Judas Priest'),
    ('Pantera'), ('Motörhead'), ('Slipknot'), ('Rammstein'),
    -- Punk
    ('Ramones'), ('Sex Pistols'), ('The Clash'), ('Green Day'), ('Blink-182'), ('The Offspring'),
    ('Misfits'), ('Bad Religion'), ('Sum 41'), ('Dead Kennedys'),
    -- Rock alternativo
    ('Nirvana'), ('Radiohead'), ('Pearl Jam'), ('Red Hot Chili Peppers'),
    ('Foo Fighters'), ('Oasis'), ('Linkin Park'), ('R.E.M.'), ('Soundgarden'), ('Muse'),
    -- Indie
    ('Arctic Monkeys'), ('The Strokes'), ('Tame Impala'), ('Vampire Weekend'), ('Arcade Fire'),
    ('Mac DeMarco'), ('Florence + The Machine'), ('Bon Iver'), ('The National'), ('Beach House'),
    -- Pop
    ('Michael Jackson'), ('Madonna'), ('Taylor Swift'), ('Ariana Grande'), ('Ed Sheeran'),
    ('Justin Bieber'), ('Dua Lipa'), ('Katy Perry'), ('Lady Gaga'), ('Billie Eilish'),
    -- Hip hop
    ('Eminem'), ('Jay-Z'), ('Kendrick Lamar'), ('Drake'), ('Kanye West'), ('Snoop Dogg'), ('Nas'),
    ('2Pac'), ('The Notorious B.I.G.'), ('Dr. Dre'),
    -- Trap
    ('Travis Scott'), ('Future'), ('Migos'), ('Lil Baby'), ('21 Savage'), ('Gucci Mane'),
    ('Young Thug'), ('Lil Uzi Vert'), ('Playboi Carti'), ('Roddy Ricch'),
    -- R&B
    ('Beyoncé'), ('Rihanna'), ('The Weeknd'), ('Usher'), ('Alicia Keys'), ('Mary J. Blige'),
    ('Frank Ocean'), ('SZA'), ('Whitney Houston'), ('Aaliyah'),
    -- Soul y funk
    ('James Brown'), ('Stevie Wonder'), ('Marvin Gaye'), ('Aretha Franklin'), ('Prince'),
    ('Earth, Wind & Fire'), ('Otis Redding'), ('Sam Cooke'), ('Curtis Mayfield'), ('Al Green'),
    -- Disco
    ('Bee Gees'), ('Donna Summer'), ('ABBA'), ('Chic'), ('Gloria Gaynor'), ('Village People'),
    ('Boney M.'), ('KC and the Sunshine Band'), ('Sister Sledge'), ('Kool & the Gang'),
    -- Country
    ('Johnny Cash'), ('Dolly Parton'), ('Willie Nelson'), ('Garth Brooks'), ('Shania Twain'),
    ('Luke Combs'), ('Kenny Rogers'), ('Hank Williams'), ('George Strait'), ('Morgan Wallen'),
    -- Folk
    ('Bob Dylan'), ('Joni Mitchell'), ('Simon and Garfunkel'), ('Neil Young'), ('Leonard Cohen'),
    ('Joan Baez'), ('Woody Guthrie'), ('Fleet Foxes'), ('Mumford and Sons'), ('Cat Stevens'),
    -- Blues
    ('B.B. King'), ('Muddy Waters'), ('Robert Johnson'), ('Howlin'' Wolf'), ('John Lee Hooker'),
    ('Stevie Ray Vaughan'), ('Eric Clapton'), ('Buddy Guy'), ('Albert King'), ('Etta James'),
    -- Jazz
    ('Miles Davis'), ('John Coltrane'), ('Louis Armstrong'), ('Duke Ellington'),
    ('Ella Fitzgerald'), ('Billie Holiday'), ('Thelonious Monk'), ('Charlie Parker'), ('Dave Brubeck'),
    ('Herbie Hancock'),
    -- Bossa nova
    ('João Gilberto'), ('Antônio Carlos Jobim'), ('Astrud Gilberto'), ('Stan Getz'),
    ('Vinicius de Moraes'), ('Sérgio Mendes'), ('Baden Powell'), ('Elis Regina'), ('Nara Leão'),
    ('Marcos Valle'),
    -- Música clásica
    ('Ludwig van Beethoven'), ('Wolfgang Amadeus Mozart'), ('Johann Sebastian Bach'),
    ('Frédéric Chopin'), ('Antonio Vivaldi'), ('Pyotr Ilyich Tchaikovsky'), ('Claude Debussy'),
    ('Franz Schubert'), ('Johannes Brahms'), ('Giuseppe Verdi'),
    -- Reggae
    ('Bob Marley'), ('Peter Tosh'), ('Jimmy Cliff'), ('Toots and the Maytals'),
    ('Burning Spear'), ('UB40'), ('Damian Marley'), ('Steel Pulse'), ('Black Uhuru'), ('Gregory Isaacs'),
    -- Reguetón
    ('Daddy Yankee'), ('Bad Bunny'), ('J Balvin'), ('Don Omar'), ('Wisin & Yandel'),
    ('Karol G'), ('Maluma'), ('Ozuna'), ('Nicky Jam'), ('Anuel AA'),
    -- Pop latino
    ('Shakira'), ('Ricky Martin'), ('Enrique Iglesias'), ('Juanes'), ('Luis Fonsi'),
    ('Alejandro Sanz'), ('Paulina Rubio'), ('Thalía'), ('Sebastián Yatra'), ('Camilo'),
    -- Balada
    ('Juan Gabriel'), ('Camilo Sesto'), ('José José'), ('Luis Miguel'), ('Julio Iglesias'),
    ('Marco Antonio Solís'), ('Ricardo Arjona'), ('Franco De Vita'), ('Rocío Dúrcal'), ('Roberto Carlos'),
    -- Salsa
    ('Celia Cruz'), ('Héctor Lavoe'), ('Willie Colón'), ('Rubén Blades'), ('Marc Anthony'),
    ('Tito Puente'), ('Óscar D''León'), ('Joe Arroyo'), ('Gilberto Santa Rosa'), ('Grupo Niche'),
    -- Vallenato
    ('Diomedes Díaz'), ('Carlos Vives'), ('Binomio de Oro'), ('Silvestre Dangond'),
    ('Jorge Celedón'), ('Los Hermanos Zuleta'), ('Kaleth Morales'), ('Peter Manjarrés'), ('Iván Villazón'),
    ('Jorge Oñate'),
    -- Cumbia
    ('Los Ángeles Azules'), ('Celso Piña'), ('Los Palmeras'), ('Grupo Cañaveral'),
    ('Aniceto Molina'), ('Lisandro Meza'), ('Totó la Momposina'), ('Los Mirlos'), ('Sonora Dinamita'),
    ('Los Corraleros de Majagual'),
    -- Bachata
    ('Romeo Santos'), ('Aventura'), ('Prince Royce'), ('Juan Luis Guerra'),
    ('Monchy & Alexandra'), ('Anthony Santos'), ('Xtreme'), ('Zacarías Ferreira'), ('Luis Vargas'),
    ('Frank Reyes'),
    -- Merengue
    ('Wilfrido Vargas'), ('Elvis Crespo'), ('Olga Tañón'), ('Johnny Ventura'),
    ('Milly Quezada'), ('Los Hermanos Rosario'), ('Fernando Villalona'), ('Oro Sólido'), ('Toño Rosario'),
    ('Eddy Herrera'),
    -- K-pop
    ('BTS'), ('BLACKPINK'), ('EXO'), ('TWICE'), ('Stray Kids'), ('BIGBANG'), ('Girls'' Generation'),
    ('PSY'), ('SEVENTEEN'), ('NewJeans'),
    -- EDM
    ('Calvin Harris'), ('David Guetta'), ('Avicii'), ('Martin Garrix'), ('Marshmello'), ('Zedd'),
    ('The Chainsmokers'), ('Swedish House Mafia'), ('Kygo'), ('Alesso'),
    -- House
    ('Daft Punk'), ('Frankie Knuckles'), ('Marshall Jefferson'), ('Masters at Work'),
    ('Todd Terry'), ('Roger Sanchez'), ('Armand Van Helden'), ('Basement Jaxx'), ('Disclosure'), ('Mark Farina'),
    -- Deep house
    ('Larry Heard'), ('Kerri Chandler'), ('Duke Dumont'), ('Maya Jane Coles'),
    ('Gorgon City'), ('Jimpster'), ('Lost Frequencies'), ('Robin Schulz'), ('Kungs'), ('Felix Jaehn'),
    -- Tech house
    ('FISHER'), ('Chris Lake'), ('Green Velvet'), ('Claude VonStroke'), ('Solardo'),
    ('CamelPhat'), ('Patrick Topping'), ('Jamie Jones'), ('Seth Troxler'), ('Michael Bibi'),
    -- Progressive house
    ('Deadmau5'), ('Eric Prydz'), ('Sasha'), ('John Digweed'), ('Hernan Cattaneo'),
    ('Nick Warren'), ('Guy J'), ('Lane 8'), ('Axwell'), ('Gabriel & Dresden'),
    -- Trance
    ('Armin van Buuren'), ('Paul van Dyk'), ('Tiësto'), ('Above & Beyond'), ('Ferry Corsten'),
    ('Paul Oakenfold'), ('Cosmic Gate'), ('Gareth Emery'), ('Aly & Fila'), ('Markus Schulz'),
    -- Drum and bass
    ('Pendulum'), ('Chase & Status'), ('Sub Focus'), ('Andy C'), ('Netsky'), ('Noisia'),
    ('LTJ Bukem'), ('Goldie'), ('Roni Size'), ('High Contrast'),
    -- Dubstep
    ('Skrillex'), ('Excision'), ('Flux Pavilion'), ('Rusko'), ('Bassnectar'), ('Nero'), ('Zomboy'),
    ('Datsik'), ('Virtual Riot'), ('Skream'),
    -- Techno
    ('Carl Cox'), ('Adam Beyer'), ('Nina Kraviz'), ('Charlotte de Witte'), ('Amelie Lens'),
    ('Sven Väth'), ('Ben Klock'), ('Marcel Dettmann'), ('Paul Kalkbrenner'), ('Joseph Capriati'),
    -- Minimal techno
    ('Richie Hawtin'), ('Ricardo Villalobos'), ('Luciano'), ('Raresh'), ('Rhadoo'),
    ('Petre Inspirescu'), ('Zip'), ('Sonja Moonear'), ('Margaret Dygas'), ('Mathew Jonson'),
    -- Detroit techno
    ('Juan Atkins'), ('Derrick May'), ('Kevin Saunderson'), ('Jeff Mills'),
    ('Underground Resistance'), ('Carl Craig'), ('Robert Hood'), ('Octave One'), ('Kenny Larkin'),
    ('Stacey Pullen'),
    -- Acid techno
    ('Josh Wink'), ('Hardfloor'), ('Phuture'), ('Emmanuel Top'), ('Dave Clarke'),
    ('Speedy J'), ('Luke Slater'), ('Chris Liberator'), ('Dave the Drummer'), ('DJ Rush'),
    -- Hard techno
    ('Reinier Zonneveld'), ('I Hate Models'), ('Kobosil'), ('Dax J'), ('Sara Landry'),
    ('Indira Paganotto'), ('Eli Brown'), ('Nico Moreno'), ('Space 92'), ('999999999'),
    -- Melodic techno
    ('Tale Of Us'), ('Stephan Bodzin'), ('Mind Against'), ('Anyma'), ('Adriatique'),
    ('ARTBAT'), ('Innellea'), ('Kevin de Vries'), ('Massano'), ('Boris Brejcha'),
    -- Industrial techno
    ('Perc'), ('Surgeon'), ('Regis'), ('Ancient Methods'), ('Blawan'),
    ('Oscar Mulero'), ('Rebekah'), ('Truncate'), ('Gesloten Cirkel'), ('Paula Temple'),
    -- Dub techno
    ('Basic Channel'), ('Rhythm & Sound'), ('Deepchord'), ('Echospace'), ('Monolake'),
    ('Maurizio'), ('Intrusion'), ('Sleeparchive'), ('Pole'), ('Gas')
) AS s(n);

COMMIT;
