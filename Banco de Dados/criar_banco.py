import sqlite3
import pandas as pd

# Caminhos dos arquivos de dados e do banco de dados
CSV_PATH = "dados/brasileirao.csv"
DB_PATH = "brasileirao.sqlite"

# Carrega o arquivo CSV para um DataFrame do Pandas
df = pd.read_csv(CSV_PATH)

# Substitui textos vazios por valores nulos (NA) do Pandas
df = df.replace("", pd.NA)

# Lista de colunas que devem ser tratadas como números
colunas_numericas = [
    "ano_campeonato", "rodada", "publico", "publico_max",
    "colocacao_mandante", "colocacao_visitante",
    "valor_equipe_titular_mandante", "valor_equipe_titular_visitante",
    "idade_media_titular_mandante", "idade_media_titular_visitante",
    "gols_mandante", "gols_visitante",
    "gols_1_tempo_mandante", "gols_1_tempo_visitante",
    "escanteios_mandante", "escanteios_visitante",
    "faltas_mandante", "faltas_visitante",
    "chutes_bola_parada_mandante", "chutes_bola_parada_visitante",
    "defesas_mandante", "defesas_visitante",
    "impedimentos_mandante", "impedimentos_visitante",
    "chutes_mandante", "chutes_visitante",
    "chutes_fora_mandante", "chutes_fora_visitante"
]

# Converte as colunas da lista para formato numérico (valores inválidos viram NaN)
for col in colunas_numericas:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Converte a coluna de data para o formato de data do Python (AAAA-MM-DD)
df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date

# Remove linhas que não possuem informações essenciais sobre o jogo
df = df.dropna(subset=[
    "ano_campeonato", "data", "rodada",
    "estadio", "arbitro",
    "time_mandante", "time_visitante",
    "gols_mandante", "gols_visitante"
])

# Guardar a quantidade de linhas original para o cálculo de duplicatas
linhas_antes = len(df)

# Remove linhas que possuem todas as colunas 100% idênticas
df = df.drop_duplicates()

# Remove partidas repetidas considerando apenas chaves principais (mesmo dia, rodada e times)
df = df.drop_duplicates(subset=[
    "ano_campeonato",
    "data",
    "rodada",
    "time_mandante",
    "time_visitante"
])

# Exibe no terminal quantas linhas duplicadas foram descartadas
linhas_depois = len(df)
print(f"Duplicatas removidas: {linhas_antes - linhas_depois}")

# Filtra o DataFrame mantendo apenas dados válidos para o banco (valores não negativos)
df = df[
    (df["ano_campeonato"] > 0) &
    (df["rodada"] > 0) &
    (df["gols_mandante"] >= 0) &
    (df["gols_visitante"] >= 0)
]

# Permite público nulo, mas se existir, deve ser maior ou igual a zero
df = df[df["publico"].isna() | (df["publico"] >= 0)]

# Permite público máximo nulo, mas se existir, deve ser maior que zero
df = df[df["publico_max"].isna() | (df["publico_max"] > 0)]

# Garante que gols do 1º tempo não sejam negativos se o campo estiver preenchido
df = df[df["gols_1_tempo_mandante"].isna() | (df["gols_1_tempo_mandante"] >= 0)]
df = df[df["gols_1_tempo_visitante"].isna() | (df["gols_1_tempo_visitante"] >= 0)]

# Lista de colunas de estatísticas que não podem ter valores negativos
colunas_nao_negativas = [
    "escanteios_mandante", "escanteios_visitante",
    "faltas_mandante", "faltas_visitante",
    "chutes_bola_parada_mandante", "chutes_bola_parada_visitante",
    "defesas_mandante", "defesas_visitante",
    "impedimentos_mandante", "impedimentos_visitante",
    "chutes_mandante", "chutes_visitante",
    "chutes_fora_mandante", "chutes_fora_visitante",
    "valor_equipe_titular_mandante", "valor_equipe_titular_visitante"
]

# Remove linhas onde qualquer estatística da lista acima seja menor que zero
for col in colunas_nao_negativas:
    df = df[df[col].isna() | (df[col] >= 0)]

# Garante que a média de idade dos titulares (se preenchida) seja maior que zero
df = df[df["idade_media_titular_mandante"].isna() | (df["idade_media_titular_mandante"] > 0)]
df = df[df["idade_media_titular_visitante"].isna() | (df["idade_media_titular_visitante"] > 0)]

# Abre ou cria a conexão com o arquivo do banco de dados SQLite
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Habilita o suporte a chaves estrangeiras no SQLite
cursor.execute("PRAGMA foreign_keys = ON;")

# Executa o script SQL para resetar e recriar as tabelas com suas restrições (CHECKs)
cursor.executescript("""
DROP TABLE IF EXISTS estatistica;
DROP TABLE IF EXISTS partida;
DROP TABLE IF EXISTS tecnico;
DROP TABLE IF EXISTS arbitro;
DROP TABLE IF EXISTS pessoa;
DROP TABLE IF EXISTS time;
DROP TABLE IF EXISTS estadio;
DROP TABLE IF EXISTS campeonato;

CREATE TABLE campeonato (
    id_campeonato INTEGER PRIMARY KEY,
    ano_campeonato INTEGER NOT NULL UNIQUE CHECK (ano_campeonato > 0)
);

CREATE TABLE pessoa (
    id_pessoa INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE tecnico (
    id_tecnico INTEGER PRIMARY KEY,
    FOREIGN KEY (id_tecnico) REFERENCES pessoa(id_pessoa)
);

CREATE TABLE arbitro (
    id_arbitro INTEGER PRIMARY KEY,
    FOREIGN KEY (id_arbitro) REFERENCES pessoa(id_pessoa)
);

CREATE TABLE estadio (
    id_estadio INTEGER PRIMARY KEY,
    nome_estadio TEXT NOT NULL UNIQUE,
    publico_max INTEGER CHECK (publico_max IS NULL OR publico_max > 0)
);

CREATE TABLE time (
    id_time INTEGER PRIMARY KEY,
    nome_time TEXT NOT NULL UNIQUE
);

CREATE TABLE partida (
    id_partida INTEGER PRIMARY KEY,
    data DATE NOT NULL,
    rodada INTEGER NOT NULL CHECK (rodada > 0),
    publico INTEGER CHECK (publico IS NULL OR publico >= 0),
    gols_mandante INTEGER NOT NULL CHECK (gols_mandante >= 0),
    gols_visitante INTEGER NOT NULL CHECK (gols_visitante >= 0),
    gols_1_tempo_mandante INTEGER CHECK (gols_1_tempo_mandante IS NULL OR gols_1_tempo_mandante >= 0),
    gols_1_tempo_visitante INTEGER CHECK (gols_1_tempo_visitante IS NULL OR gols_1_tempo_visitante >= 0),
    id_campeonato INTEGER NOT NULL,
    id_estadio INTEGER NOT NULL,
    id_arbitro INTEGER NOT NULL,
    FOREIGN KEY (id_campeonato) REFERENCES campeonato(id_campeonato),
    FOREIGN KEY (id_estadio) REFERENCES estadio(id_estadio),
    FOREIGN KEY (id_arbitro) REFERENCES arbitro(id_arbitro)
);

CREATE TABLE estatistica (
    id_estatistica INTEGER PRIMARY KEY,
    tipo_mando TEXT NOT NULL CHECK (tipo_mando IN ('mandante', 'visitante')),
    colocacao INTEGER CHECK (colocacao IS NULL OR colocacao > 0),
    valor_equipe_titular REAL CHECK (valor_equipe_titular IS NULL OR valor_equipe_titular >= 0),
    idade_media_titular REAL CHECK (idade_media_titular IS NULL OR idade_media_titular > 0),
    escanteios INTEGER CHECK (escanteios IS NULL OR escanteios >= 0),
    faltas INTEGER CHECK (faltas IS NULL OR faltas >= 0),
    chutes_bola_parada INTEGER CHECK (chutes_bola_parada IS NULL OR chutes_bola_parada >= 0),
    defesas INTEGER CHECK (defesas IS NULL OR defesas >= 0),
    impedimentos INTEGER CHECK (impedimentos IS NULL OR impedimentos >= 0),
    chutes INTEGER CHECK (chutes IS NULL OR chutes >= 0),
    chutes_fora INTEGER CHECK (chutes_fora IS NULL OR chutes_fora >= 0),
    id_partida INTEGER NOT NULL,
    id_time INTEGER NOT NULL,
    id_tecnico INTEGER,
    FOREIGN KEY (id_partida) REFERENCES partida(id_partida),
    FOREIGN KEY (id_time) REFERENCES time(id_time),
    FOREIGN KEY (id_tecnico) REFERENCES tecnico(id_tecnico),
    UNIQUE (id_partida, id_time, tipo_mando)
);
""")

# Mapeia e insere os anos únicos dos campeonatos, ordenando do mais antigo ao mais novo
anos = sorted(df["ano_campeonato"].dropna().astype(int).unique())
map_campeonato = {ano: i + 1 for i, ano in enumerate(anos)}

for ano, id_campeonato in map_campeonato.items():
    cursor.execute("""
    INSERT INTO campeonato (id_campeonato, ano_campeonato)
    VALUES (?, ?)
""", (id_campeonato, ano))

# Agrupa estádios para pegar a maior capacidade registrada de cada um e insere na tabela
estadios = df.groupby("estadio")["publico_max"].max().reset_index()
map_estadio = {}

for i, row in estadios.iterrows():
    id_estadio = i + 1
    map_estadio[row["estadio"]] = id_estadio
    cursor.execute(
        "INSERT INTO estadio VALUES (?, ?, ?)",
        (id_estadio, row["estadio"], None if pd.isna(row["publico_max"]) else int(row["publico_max"]))
    )

# Junta times mandantes e visitantes, cria IDs sequenciais únicos e faz a inserção
times = pd.concat([df["time_mandante"], df["time_visitante"]]).dropna().unique()
times = sorted(times)
map_time = {nome: i + 1 for i, nome in enumerate(times)}

for nome, id_time in map_time.items():
    cursor.execute(
        "INSERT INTO time VALUES (?, ?)",
        (id_time, nome)
    )

# Junta árbitros e técnicos na mesma lista para alimentar a tabela genérica 'pessoa'
pessoas = pd.concat([
    df["arbitro"],
    df["tecnico_mandante"],
    df["tecnico_visitante"]
]).dropna().unique()

pessoas = sorted(pessoas)
map_pessoa = {nome: i + 1 for i, nome in enumerate(pessoas)}

for nome, id_pessoa in map_pessoa.items():
    cursor.execute(
        "INSERT INTO pessoa VALUES (?, ?)",
        (id_pessoa, nome)
    )

# Filtra os nomes que atuaram como árbitros e vincula seus IDs à tabela 'arbitro'
arbitros = sorted(df["arbitro"].dropna().unique())

for nome in arbitros:
    cursor.execute(
        "INSERT OR IGNORE INTO arbitro VALUES (?)",
        (map_pessoa[nome],)
    )

# Filtra os nomes que atuaram como técnicos e vincula seus IDs à tabela 'tecnico'
tecnicos = pd.concat([
    df["tecnico_mandante"],
    df["tecnico_visitante"]
]).dropna().unique()

for nome in tecnicos:
    cursor.execute(
        "INSERT OR IGNORE INTO tecnico VALUES (?)",
        (map_pessoa[nome],)
    )

# Inicializa o contador de chaves primárias para a tabela de estatísticas
id_estatistica = 1

# Percorre linha por linha do DataFrame limpo para salvar os registros finais
for idx, row in df.reset_index(drop=True).iterrows():
    id_partida = idx + 1

    # Recupera os IDs gerados anteriormente através dos dicionários de mapeamento
    id_campeonato = map_campeonato[int(row["ano_campeonato"])]
    id_estadio = map_estadio[row["estadio"]]
    id_arbitro = map_pessoa[row["arbitro"]]

    # Insere os dados gerais da rodada/confronto na tabela 'partida'
    cursor.execute("""
        INSERT INTO partida (
            id_partida, data, rodada, publico,
            gols_mandante, gols_visitante,
            gols_1_tempo_mandante, gols_1_tempo_visitante,
            id_campeonato, id_estadio, id_arbitro
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        id_partida,
        str(row["data"]),
        int(row["rodada"]),
        None if pd.isna(row["publico"]) else int(row["publico"]),
        int(row["gols_mandante"]),
        int(row["gols_visitante"]),
        None if pd.isna(row["gols_1_tempo_mandante"]) else int(row["gols_1_tempo_mandante"]),
        None if pd.isna(row["gols_1_tempo_visitante"]) else int(row["gols_1_tempo_visitante"]),
        id_campeonato,
        id_estadio,
        id_arbitro
    ))

    # Estrutura auxiliar para rodar duas vezes por linha 
    registros_estatistica = [
        ("mandante", "time_mandante", "tecnico_mandante"),
        ("visitante", "time_visitante", "tecnico_visitante")
    ]

    for tipo_mando, col_time, col_tecnico in registros_estatistica:
        sufixo = tipo_mando

        nome_time = row[col_time]
        nome_tecnico = row[col_tecnico]

        id_time = map_time[nome_time]
        id_tecnico = None if pd.isna(nome_tecnico) else map_pessoa[nome_tecnico]

        # Insere dados detalhados (chutes, faltas, etc.) de cada equipe envolvida no jogo
        cursor.execute("""
            INSERT INTO estatistica (
                id_estatistica, tipo_mando, colocacao,
                valor_equipe_titular, idade_media_titular,
                escanteios, faltas, chutes_bola_parada,
                defesas, impedimentos, chutes, chutes_fora,
                id_partida, id_time, id_tecnico
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            id_estatistica,
            tipo_mando,
            None if pd.isna(row[f"colocacao_{sufixo}"]) else int(row[f"colocacao_{sufixo}"]),
            None if pd.isna(row[f"valor_equipe_titular_{sufixo}"]) else float(row[f"valor_equipe_titular_{sufixo}"]),
            None if pd.isna(row[f"idade_media_titular_{sufixo}"]) else float(row[f"idade_media_titular_{sufixo}"]),
            None if pd.isna(row[f"escanteios_{sufixo}"]) else int(row[f"escanteios_{sufixo}"]),
            None if pd.isna(row[f"faltas_{sufixo}"]) else int(row[f"faltas_{sufixo}"]),
            None if pd.isna(row[f"chutes_bola_parada_{sufixo}"]) else int(row[f"chutes_bola_parada_{sufixo}"]),
            None if pd.isna(row[f"defesas_{sufixo}"]) else int(row[f"defesas_{sufixo}"]),
            None if pd.isna(row[f"impedimentos_{sufixo}"]) else int(row[f"impedimentos_{sufixo}"]),
            None if pd.isna(row[f"chutes_{sufixo}"]) else int(row[f"chutes_{sufixo}"]),
            None if pd.isna(row[f"chutes_fora_{sufixo}"]) else int(row[f"chutes_fora_{sufixo}"]),
            id_partida,
            id_time,
            id_tecnico
        ))

        id_estatistica += 1

# Confirma todas as operações de escrita no arquivo de banco de dados 
conn.commit()

# Exibe o relatório básico contando o número total de registros salvos por tabela
print("Banco criado com sucesso!")

for tabela in [
    "campeonato", "pessoa", "tecnico", "arbitro",
    "estadio", "time", "partida", "estatistica"
]:
    qtd = cursor.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
    print(f"{tabela}: {qtd} registros")

# Roda consultas agregadas no SQL buscando registros duplicados (
print("\nValidação de duplicatas:")

validacoes_duplicatas = [
    ("campeonato", "id_campeonato"),
    ("pessoa", "id_pessoa"),
    ("tecnico", "id_tecnico"),
    ("arbitro", "id_arbitro"),
    ("estadio", "id_estadio"),
    ("time", "id_time"),
    ("partida", "id_partida"),
    ("estatistica", "id_estatistica")
]

for tabela, coluna in validacoes_duplicatas:
    duplicados = cursor.execute(f"""
        SELECT COUNT(*)
        FROM (
            SELECT {coluna}
            FROM {tabela}
            GROUP BY {coluna}
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    print(f"{tabela}.{coluna}: {duplicados} duplicados")

# Realiza LEFT JOINs para checar se existem chaves órfãs perdidas 
print("\nValidação de participação:")

partidas_sem_campeonato = cursor.execute("""
    SELECT COUNT(*)
    FROM partida p
    LEFT JOIN campeonato c ON p.id_campeonato = c.id_campeonato
    WHERE c.id_campeonato IS NULL
""").fetchone()[0]

partidas_sem_estadio = cursor.execute("""
    SELECT COUNT(*)
    FROM partida p
    LEFT JOIN estadio e ON p.id_estadio = e.id_estadio
    WHERE e.id_estadio IS NULL
""").fetchone()[0]

partidas_sem_arbitro = cursor.execute("""
    SELECT COUNT(*)
    FROM partida p
    LEFT JOIN arbitro a ON p.id_arbitro = a.id_arbitro
    WHERE a.id_arbitro IS NULL
""").fetchone()[0]

estatisticas_sem_partida = cursor.execute("""
    SELECT COUNT(*)
    FROM estatistica e
    LEFT JOIN partida p ON e.id_partida = p.id_partida
    WHERE p.id_partida IS NULL
""").fetchone()[0]

estatisticas_sem_time = cursor.execute("""
    SELECT COUNT(*)
    FROM estatistica e
    LEFT JOIN time t ON e.id_time = t.id_time
    WHERE t.id_time IS NULL
""").fetchone()[0]

print("Partidas sem campeonato:", partidas_sem_campeonato)
print("Partidas sem estádio:", partidas_sem_estadio)
print("Partidas sem árbitro:", partidas_sem_arbitro)
print("Estatísticas sem partida:", estatisticas_sem_partida)
print("Estatísticas sem time:", estatisticas_sem_time)

# Fecha a comunicação de forma segura com o banco de dados SQLite
conn.close()