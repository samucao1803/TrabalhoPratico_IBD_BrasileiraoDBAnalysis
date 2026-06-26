# Brasileirao DB Analysis

Projeto da disciplina **Introdução a Banco de Dados** da **UFMG (Universidade Federal de Minas Gerais)**.  
O **Brasileirao DB Analysis** tem como objetivo modelar, implementar e analisar uma base de dados aberta do Campeonato Brasileiro Série A (2003–2024), transformando dados brutos em informações estruturadas e úteis para análise.

## 📌 Objetivo

Construir um pipeline completo de banco de dados, incluindo:

- modelagem conceitual (ER/EER),
- modelo relacional normalizado (até 3FN),
- implementação de ETL com Python,
- carga e validação no PostgreSQL,
- análises exploratórias com SQL e visualizações.

## 🗂️ Dataset

- Base dos Dados:  
  https://basedosdados.org/dataset/c861330e-bca2-474d-9073-bc70744a1b23?table=18835b0d-233e-4857-b454-1fa34a81b4fa

## 🧱 Estrutura do Banco

Entidades principais:

- Campeonato
- Pessoa (superclasse)
  - Técnico
  - Árbitro
- Estádio
- Time
- Partida
- Estatística

O esquema foi normalizado até a **3FN**, com chaves primárias, estrangeiras e regras de integridade.

## ⚙️ Tecnologias Utilizadas

- PostgreSQL
- Docker / Docker Compose
- Python 3
- Pandas
- psycopg2
- python-dotenv
- Jupyter Notebook
- Matplotlib / Seaborn

## 📁 Estrutura do Projeto

```text
Banco de Dados/
├── dados/
│   └── brasileirao.csv
├── docker-compose.yml
├── .env
├── .env.example
├── requirements.txt
└── criar_banco.py
```

## 🚀 Como Executar

1. Criar e ativar ambiente virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/Mac
   # .venv\Scripts\activate    # Windows
   ```

2. Instalar dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Subir PostgreSQL com Docker:
   ```bash
   docker compose up -d
   ```

4. Executar o ETL:
   ```bash
   python criar_banco.py
   ```

## ✅ Resultados da Carga

- Registros originais: **8453**
- Registros finais carregados (partidas): **6731**
- Registros em estatística: **13462** (2 por partida)

Validações finais:
- 0 violações de domínio
- 0 duplicidades de chave primária
- 0 falhas de integridade referencial

## 📊 Análises Exploratórias

1. Fator casa por estádio  
2. Eficiência ofensiva vs valor do elenco  
3. Perfil dos árbitros  
4. Juventude × experiência na tabela

## 👥 Integrantes

- **Samuel Lima Horta** — 2023060561  
- **Thiago Tobias Valente de Oliveira Santos** — 2023060790  
- **Bernardo Soares Diniz Lara** — 2023060898  
- **Luigi Pinesi Tavares Jacob** — 20230799