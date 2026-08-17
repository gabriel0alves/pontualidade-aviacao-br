"""
Consolidacao da camada bruta VRA em um unico dataset colunar (Parquet).

Entrada : data/raw/VRA_<ano>_<mes>.csv   (CSV, latin-1, separador ';')
Saida   : data/interim/vra.parquet       (tipado, nomes normalizados)

Responsabilidades desta etapa (e SOMENTE estas):
  - ler cada arquivo com o encoding e separador corretos;
  - normalizar nomes de coluna para snake_case ASCII;
  - alinhar arquivos de layouts diferentes POR NOME, nunca por posicao;
  - converter tipos (datas, inteiros) registrando falhas de conversao;
  - persistir em Parquet.

Regras de negocio e limpeza de conteudo NAO acontecem aqui, para que esta
camada permaneca uma representacao fiel do dado publicado pela ANAC. Elas
ficam em:
  - 03_auditoria.py  -> descreve os problemas, sem corrigir nada;
  - 04_universo.py   -> aplica as regras R1-R9 e produz o universo analitico;
  - regras.py        -> declara os parametros dessas regras (fonte unica).
"""

from __future__ import annotations

import codecs
import sys
import unicodedata
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW_DIR = BASE / "data" / "raw"
INTERIM_DIR = BASE / "data" / "interim"
SAIDA = INTERIM_DIR / "vra.parquet"

SEPARADOR = ";"
FORMATO_DATA = "%d/%m/%Y %H:%M"

# A ANAC nao mantem encoding constante entre publicacoes: a maior parte da
# serie e UTF-8, mas ha meses isolados em Latin-1 (ex.: VRA_2025_10.csv).
# Fixar o encoding corromperia o texto silenciosamente, entao ele e detectado
# por arquivo. A ordem importa: Latin-1 aceita qualquer byte e nunca falha,
# por isso UTF-8 precisa ser testado primeiro.
ENCODINGS_CANDIDATOS = ("utf-8", "latin-1")
BLOCO_LEITURA = 1024 * 1024

# Esquema canonico. Arquivos que nao tragam alguma destas colunas recebem
# nulo, e colunas inesperadas sao reportadas em vez de descartadas em silencio.
COLUNAS_CANONICAS = [
    "sigla_icao_empresa",
    "empresa_aerea",
    "numero_voo",
    "codigo_di",
    "codigo_tipo_linha",
    "modelo_equipamento",
    "numero_assentos",
    "icao_origem",
    "descricao_origem",
    "partida_prevista",
    "partida_real",
    "icao_destino",
    "descricao_destino",
    "chegada_prevista",
    "chegada_real",
    "situacao_voo",
    "justificativa",
    "referencia",
    "situacao_partida",
    "situacao_chegada",
    "codeshare",
]

COLUNAS_DATA = [
    "partida_prevista",
    "partida_real",
    "chegada_prevista",
    "chegada_real",
]

# Mapeamento do cabecalho original (ja normalizado) para o nome canonico.
RENOMEAR = {
    "sigla_icao_empresa_aerea": "sigla_icao_empresa",
    "numero_de_assentos": "numero_assentos",
    "sigla_icao_aeroporto_origem": "icao_origem",
    "descricao_aeroporto_origem": "descricao_origem",
    "sigla_icao_aeroporto_destino": "icao_destino",
    "descricao_aeroporto_destino": "descricao_destino",
}


def normalizar_nome(nome: str) -> str:
    """'Sigla ICAO Empresa Aerea' -> 'sigla_icao_empresa_aerea'."""
    sem_acento = (
        unicodedata.normalize("NFKD", nome).encode("ASCII", "ignore").decode("ASCII")
    )
    return "_".join(sem_acento.lower().split())


def _decodifica_sem_erro(caminho: Path, encoding: str) -> bool:
    """
    Verifica se o arquivo inteiro decodifica em `encoding`.

    Usa decodificador incremental de proposito: fatiar bytes em blocos fixos
    corta caracteres multibyte ao meio, e um `bytes.decode()` sobre esse
    pedaco falharia por truncamento -- nao por encoding errado. O decodificador
    incremental retem os bytes parciais entre blocos e elimina esse falso
    positivo.
    """
    decodificador = codecs.getincrementaldecoder(encoding)()
    with open(caminho, "rb") as fh:
        while bloco := fh.read(BLOCO_LEITURA):
            try:
                decodificador.decode(bloco)
            except UnicodeDecodeError:
                return False
    try:
        decodificador.decode(b"", final=True)
    except UnicodeDecodeError:
        return False
    return True


def detectar_encoding(caminho: Path) -> str:
    """Retorna o primeiro encoding candidato que decodifica o arquivo inteiro."""
    for enc in ENCODINGS_CANDIDATOS:
        if _decodifica_sem_erro(caminho, enc):
            return enc
    return ENCODINGS_CANDIDATOS[-1]


def ler_arquivo(caminho: Path) -> tuple[pd.DataFrame, str, list[str]]:
    """Le um CSV do VRA e devolve (dataframe alinhado, encoding, colunas inesperadas)."""
    encoding = detectar_encoding(caminho)
    df = pd.read_csv(
        caminho,
        sep=SEPARADOR,
        encoding=encoding,
        dtype=str,          # tudo como texto; a tipagem e explicita mais adiante
        keep_default_na=False,
        na_values=[""],
        low_memory=False,
    )
    df.columns = [RENOMEAR.get(c, c) for c in map(normalizar_nome, df.columns)]

    inesperadas = [c for c in df.columns if c not in COLUNAS_CANONICAS]

    # reindex alinha POR NOME: ausentes viram NaN, ordem fica estavel
    df = df.reindex(columns=COLUNAS_CANONICAS)

    ano, mes = caminho.stem.split("_")[1:3]
    df["ano_arquivo"] = int(ano)
    df["mes_arquivo"] = int(mes)
    return df, encoding, inesperadas


def main() -> int:
    arquivos = sorted(RAW_DIR.glob("VRA_*.csv"))
    if not arquivos:
        print(f"ERRO: nenhum arquivo encontrado em {RAW_DIR}", file=sys.stderr)
        print("Execute antes: python src/01_ingest.py", file=sys.stderr)
        return 1

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Consolidando {len(arquivos)} arquivos de {RAW_DIR}")
    print("-" * 62)

    partes: list[pd.DataFrame] = []
    alertas: list[str] = []
    encodings: dict[str, list[str]] = {}

    for caminho in arquivos:
        df, encoding, inesperadas = ler_arquivo(caminho)
        partes.append(df)
        encodings.setdefault(encoding, []).append(caminho.name)
        if inesperadas:
            alertas.append(f"{caminho.name}: colunas fora do esquema {inesperadas}")
        print(f"  {caminho.name:20} {len(df):>8,} linhas  [{encoding}]")

    df = pd.concat(partes, ignore_index=True)
    del partes

    print("-" * 62)
    print(f"total bruto concatenado: {len(df):,} linhas")

    # --- tipagem explicita, medindo perdas ------------------------------
    print("\nConversao de tipos (registrando falhas):")

    for col in COLUNAS_DATA:
        preenchidos = df[col].notna().sum()
        df[col] = pd.to_datetime(df[col], format=FORMATO_DATA, errors="coerce")
        convertidos = df[col].notna().sum()
        falhas = preenchidos - convertidos
        aviso = "  <-- INVESTIGAR" if falhas else ""
        print(
            f"  {col:20} preenchidos={preenchidos:>9,} "
            f"convertidos={convertidos:>9,} falhas={falhas:>7,}{aviso}"
        )

    for col in ["numero_assentos"]:
        preenchidos = df[col].notna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int32")
        falhas = preenchidos - df[col].notna().sum()
        print(f"  {col:20} falhas de conversao numerica={falhas:,}")

    for col in ["sigla_icao_empresa", "icao_origem", "icao_destino",
                "situacao_voo", "situacao_partida", "situacao_chegada",
                "codigo_di", "codigo_tipo_linha", "modelo_equipamento"]:
        df[col] = df[col].astype("category")

    # --- persistencia ---------------------------------------------------
    df.to_parquet(SAIDA, engine="pyarrow", compression="snappy", index=False)

    tamanho_raw = sum(f.stat().st_size for f in arquivos) / 1024**3
    tamanho_pq = SAIDA.stat().st_size / 1024**3

    print("-" * 62)
    print(f"gravado: {SAIDA}")
    print(f"linhas : {len(df):,} | colunas: {df.shape[1]}")
    print(
        f"tamanho: CSV {tamanho_raw:.2f} GB -> Parquet {tamanho_pq:.2f} GB "
        f"({tamanho_raw / tamanho_pq:.1f}x menor)"
    )

    print("\nEncodings detectados na fonte:")
    for enc, nomes in encodings.items():
        exemplo = "" if len(nomes) > 3 else f"  ({', '.join(nomes)})"
        print(f"  {enc:10} {len(nomes):>3} arquivos{exemplo}")

    if alertas:
        print("\nALERTAS DE ESQUEMA:")
        for a in alertas:
            print(f"  - {a}")
    else:
        print("\nNenhum alerta de esquema: todos os arquivos alinharam ao esquema canonico.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
