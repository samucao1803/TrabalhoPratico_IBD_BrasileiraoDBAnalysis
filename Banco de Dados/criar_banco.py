"""Cria e popula o banco de dados do Brasileirão no PostgreSQL."""
import os
import numpy as np
import psycopg2
import pandas as pd
from psycopg2.extensions import register_adapter, AsIs
from dotenv import load_dotenv

load_dotenv()

# psycopg2 não reconhece tipos numpy (int64, float64) nativamente;
# sem esses adaptadores, qualquer valor vindo do pandas gera ProgrammingError.
register_adapter(np.int64,   lambda v: AsIs(int(v)))
register_adapter(np.float64, lambda v: AsIs(float(v)))
register_adapter(np.bool_,   lambda v: AsIs(bool(v)))

# Caminho absoluto baseado no próprio arquivo para funcionar independente
# do diretório de trabalho em que o script for chamado.
_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(_DIR, "dados", "brasileirao.csv")

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME", "brasileirao"),
    "user":     os.getenv("DB_USER", "brasileirao_user"),
    "password": os.getenv("DB_PASSWORD", "brasileirao_pass"),
}

# Leitura e limpeza do CSV
df = pd.read_csv(CSV_PATH)
# Strings vazias precisam virar NA para que dropna() e isna() funcionem corretamente.
df = df.replace("", pd.NA)

colunas_numericas = [
    "ano_campeonato", "rodada", "publico", "publico_max",
    "colocacao_mandante", "colocacao_visitante",
    "valor_equipe_titular_mandante", "valor_equipe_titular_visitante",
    "idade_media_titular_mandante", "idade_media_titular_visitante",
    "gols_mandante", "gols_visitante",
    "escanteios_mandante", "escanteios_visitante",
    "faltas_mandante", "faltas_visitante",
    "chutes_bola_parada_mandante", "chutes_bola_parada_visitante",
    "defesas_mandante", "defesas_visitante",
    "impedimentos_mandante", "impedimentos_visitante",
    "chutes_mandante", "chutes_visitante",
    "chutes_fora_mandante", "chutes_fora_visitante"
]

for col in colunas_numericas:
    # errors="coerce" converte valores não parseáveis em NaN em vez de lançar exceção.
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date

# Remove linhas sem os campos mínimos obrigatórios para uma partida ser válida.
df = df.dropna(subset=[
    "ano_campeonato", "data", "rodada",
    "estadio", "arbitro",
    "time_mandante", "time_visitante",
    "gols_mandante", "gols_visitante"
])

linhas_antes = len(df)
df = df.drop_duplicates()
# Segunda passagem de deduplicação considerando apenas a chave natural da partida,
# descartando linhas com estatísticas diferentes para o mesmo jogo.
df = df.drop_duplicates(subset=[
    "ano_campeonato", "data", "rodada",
    "time_mandante", "time_visitante"
])
linhas_depois = len(df)
print(f"Duplicatas removidas: {linhas_antes - linhas_depois}")

# Validações de domínio

df = df[
    (df["ano_campeonato"] > 0) &
    (df["rodada"] > 0) &
    (df["gols_mandante"] >= 0) &
    (df["gols_visitante"] >= 0)
]

# Público e público máximo são opcionais, mas não podem ser negativos se presentes.
df = df[df["publico"].isna() | (df["publico"] >= 0)]
df = df[df["publico_max"].isna() | (df["publico_max"] > 0)]

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

for col in colunas_nao_negativas:
    df = df[df[col].isna() | (df[col] >= 0)]

# Média de idade deve ser positiva quando preenchida (zero indicaria dado corrompido).
df = df[df["idade_media_titular_mandante"].isna() | (df["idade_media_titular_mandante"] > 0)]
df = df[df["idade_media_titular_visitante"].isna() | (df["idade_media_titular_visitante"] > 0)]

# ── Conexão e DDL ────────────────────────────────────────────────────────────

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

ddl_statements = [
    # CASCADE é necessário para contornar as FK constraints sem precisar
    # respeitar a ordem inversa de dependência manualmente.
    "DROP TABLE IF EXISTS estatistica CASCADE",
    "DROP TABLE IF EXISTS partida CASCADE",
    "DROP TABLE IF EXISTS tecnico CASCADE",
    "DROP TABLE IF EXISTS arbitro CASCADE",
    "DROP TABLE IF EXISTS pessoa CASCADE",
    "DROP TABLE IF EXISTS time CASCADE",
    "DROP TABLE IF EXISTS estadio CASCADE",
    "DROP TABLE IF EXISTS campeonato CASCADE",
    """
    CREATE TABLE campeonato (
        id_campeonato INTEGER PRIMARY KEY,
        ano_campeonato INTEGER NOT NULL UNIQUE CHECK (ano_campeonato > 0)
    )
    """,
    # Árbitros e técnicos compartilham esta tabela pois a mesma pessoa
    # pode exercer os dois papéis ao longo das temporadas.
    """
    CREATE TABLE pessoa (
        id_pessoa INTEGER PRIMARY KEY,
        nome TEXT NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE tecnico (
        id_tecnico INTEGER PRIMARY KEY,
        FOREIGN KEY (id_tecnico) REFERENCES pessoa(id_pessoa)
    )
    """,
    """
    CREATE TABLE arbitro (
        id_arbitro INTEGER PRIMARY KEY,
        FOREIGN KEY (id_arbitro) REFERENCES pessoa(id_pessoa)
    )
    """,
    """
    CREATE TABLE estadio (
        id_estadio INTEGER PRIMARY KEY,
        nome_estadio TEXT NOT NULL UNIQUE,
        publico_max INTEGER CHECK (publico_max IS NULL OR publico_max > 0)
    )
    """,
    """
    CREATE TABLE time (
        id_time INTEGER PRIMARY KEY,
        nome_time TEXT NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE partida (
        id_partida INTEGER PRIMARY KEY,
        data DATE NOT NULL,
        rodada INTEGER NOT NULL CHECK (rodada > 0),
        publico INTEGER CHECK (publico IS NULL OR publico >= 0),
        gols_mandante INTEGER NOT NULL CHECK (gols_mandante >= 0),
        gols_visitante INTEGER NOT NULL CHECK (gols_visitante >= 0),
        id_campeonato INTEGER NOT NULL,
        id_estadio INTEGER NOT NULL,
        id_arbitro INTEGER NOT NULL,
        FOREIGN KEY (id_campeonato) REFERENCES campeonato(id_campeonato),
        FOREIGN KEY (id_estadio) REFERENCES estadio(id_estadio),
        FOREIGN KEY (id_arbitro) REFERENCES arbitro(id_arbitro)
    )
    """,
    """
    CREATE TABLE estatistica (
        id_estatistica INTEGER PRIMARY KEY,
        tipo_mando TEXT NOT NULL CHECK (tipo_mando IN ('mandante', 'visitante')),
        colocacao INTEGER CHECK (colocacao IS NULL OR colocacao > 0),
        valor_equipe_titular DOUBLE PRECISION
            CHECK (valor_equipe_titular IS NULL OR valor_equipe_titular >= 0),
        idade_media_titular DOUBLE PRECISION
            CHECK (idade_media_titular IS NULL OR idade_media_titular > 0),
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
    )
    """,
]

for stmt in ddl_statements:
    cursor.execute(stmt)
conn.commit()

# Inserção dos dados 

anos = sorted(df["ano_campeonato"].dropna().astype(int).unique())
map_campeonato = {ano: i + 1 for i, ano in enumerate(anos)}

for ano, id_campeonato in map_campeonato.items():
    cursor.execute(
        "INSERT INTO campeonato (id_campeonato, ano_campeonato) VALUES (%s, %s)",
        (id_campeonato, ano)
    )

# max() garante que o estádio fique com a maior capacidade já registrada
# entre todas as temporadas, evitando inconsistências por temporadas incompletas.
estadios = df.groupby("estadio")["publico_max"].max().reset_index()
map_estadio = {}

for i, row in estadios.iterrows():
    id_estadio = i + 1
    map_estadio[row["estadio"]] = id_estadio
    publico_max = None if pd.isna(row["publico_max"]) else int(row["publico_max"])
    cursor.execute(
        "INSERT INTO estadio VALUES (%s, %s, %s)",
        (id_estadio, row["estadio"], publico_max)
    )

times = sorted(pd.concat([df["time_mandante"], df["time_visitante"]]).dropna().unique())
map_time = {nome: i + 1 for i, nome in enumerate(times)}

for nome, id_time in map_time.items():
    cursor.execute("INSERT INTO time VALUES (%s, %s)", (id_time, nome))

# Árbitros e técnicos entram juntos na tabela pessoa para permitir que
# o mesmo nome apareça nos dois papéis sem duplicar registros.
pessoas = sorted(pd.concat([
    df["arbitro"],
    df["tecnico_mandante"],
    df["tecnico_visitante"]
]).dropna().unique())
map_pessoa = {nome: i + 1 for i, nome in enumerate(pessoas)}

for nome, id_pessoa in map_pessoa.items():
    cursor.execute("INSERT INTO pessoa VALUES (%s, %s)", (id_pessoa, nome))

# ON CONFLICT DO NOTHING protege contra nomes que atuaram nos dois papéis
# e por isso já foram inseridos via outro loop.
for nome in sorted(df["arbitro"].dropna().unique()):
    cursor.execute(
        "INSERT INTO arbitro VALUES (%s) ON CONFLICT DO NOTHING",
        (map_pessoa[nome],)
    )

for nome in pd.concat([df["tecnico_mandante"], df["tecnico_visitante"]]).dropna().unique():
    cursor.execute(
        "INSERT INTO tecnico VALUES (%s) ON CONFLICT DO NOTHING",
        (map_pessoa[nome],)
    )

id_estatistica = 1

for idx, row in df.reset_index(drop=True).iterrows():
    id_partida = idx + 1

    id_campeonato = map_campeonato[int(row["ano_campeonato"])]
    id_estadio    = map_estadio[row["estadio"]]
    id_arbitro    = map_pessoa[row["arbitro"]]

    cursor.execute("""
        INSERT INTO partida (
            id_partida, data, rodada, publico,
            gols_mandante, gols_visitante,
            id_campeonato, id_estadio, id_arbitro
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        id_partida,
        row["data"],
        int(row["rodada"]),
        None if pd.isna(row["publico"]) else int(row["publico"]),
        int(row["gols_mandante"]),
        int(row["gols_visitante"]),
        id_campeonato,
        id_estadio,
        id_arbitro
    ))

    for tipo_mando, col_time, col_tecnico in [
        ("mandante",  "time_mandante",  "tecnico_mandante"),
        ("visitante", "time_visitante", "tecnico_visitante"),
    ]:
        sufixo       = tipo_mando
        nome_time    = row[col_time]
        nome_tecnico = row[col_tecnico]

        id_time    = map_time[nome_time]
        id_tecnico = None if pd.isna(nome_tecnico) else map_pessoa[nome_tecnico]

        # Helpers que capturam `row` pelo closure para reduzir repetição
        # do padrão None-se-NaN em cada campo opcional de estatística.
        def _int(col):
            return None if pd.isna(row[col]) else int(row[col])

        def _float(col):
            return None if pd.isna(row[col]) else float(row[col])

        cursor.execute("""
            INSERT INTO estatistica (
                id_estatistica, tipo_mando, colocacao,
                valor_equipe_titular, idade_media_titular,
                escanteios, faltas, chutes_bola_parada,
                defesas, impedimentos, chutes, chutes_fora,
                id_partida, id_time, id_tecnico
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_estatistica,
            tipo_mando,
            _int(f"colocacao_{sufixo}"),
            _float(f"valor_equipe_titular_{sufixo}"),
            _float(f"idade_media_titular_{sufixo}"),
            _int(f"escanteios_{sufixo}"),
            _int(f"faltas_{sufixo}"),
            _int(f"chutes_bola_parada_{sufixo}"),
            _int(f"defesas_{sufixo}"),
            _int(f"impedimentos_{sufixo}"),
            _int(f"chutes_{sufixo}"),
            _int(f"chutes_fora_{sufixo}"),
            id_partida,
            id_time,
            id_tecnico
        ))

        id_estatistica += 1

conn.commit()

# Relatório de validação

print("Banco criado com sucesso!")

tabelas = [
    "campeonato", "pessoa", "tecnico", "arbitro",
    "estadio", "time", "partida", "estatistica",
]
for tabela in tabelas:
    cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
    qtd = cursor.fetchone()[0]
    print(f"{tabela}: {qtd} registros")

print("\nValidação de duplicatas:")

validacoes_duplicatas = [
    ("campeonato", "id_campeonato"),
    ("pessoa",     "id_pessoa"),
    ("tecnico",    "id_tecnico"),
    ("arbitro",    "id_arbitro"),
    ("estadio",    "id_estadio"),
    ("time",       "id_time"),
    ("partida",    "id_partida"),
    ("estatistica","id_estatistica"),
]

for tabela, coluna in validacoes_duplicatas:
    cursor.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT {coluna} FROM {tabela}
            GROUP BY {coluna}
            HAVING COUNT(*) > 1
        ) sub
    """)
    duplicados = cursor.fetchone()[0]
    print(f"{tabela}.{coluna}: {duplicados} duplicados")

print("\nValidação de participação:")

cursor.execute("""
    SELECT COUNT(*) FROM partida p
    LEFT JOIN campeonato c ON p.id_campeonato = c.id_campeonato
    WHERE c.id_campeonato IS NULL
""")
print("Partidas sem campeonato:", cursor.fetchone()[0])

cursor.execute("""
    SELECT COUNT(*) FROM partida p
    LEFT JOIN estadio e ON p.id_estadio = e.id_estadio
    WHERE e.id_estadio IS NULL
""")
print("Partidas sem estádio:", cursor.fetchone()[0])

cursor.execute("""
    SELECT COUNT(*) FROM partida p
    LEFT JOIN arbitro a ON p.id_arbitro = a.id_arbitro
    WHERE a.id_arbitro IS NULL
""")
print("Partidas sem árbitro:", cursor.fetchone()[0])

cursor.execute("""
    SELECT COUNT(*) FROM estatistica e
    LEFT JOIN partida p ON e.id_partida = p.id_partida
    WHERE p.id_partida IS NULL
""")
print("Estatísticas sem partida:", cursor.fetchone()[0])

cursor.execute("""
    SELECT COUNT(*) FROM estatistica e
    LEFT JOIN time t ON e.id_time = t.id_time
    WHERE t.id_time IS NULL
""")
print("Estatísticas sem time:", cursor.fetchone()[0])

cursor.close()
conn.close()
