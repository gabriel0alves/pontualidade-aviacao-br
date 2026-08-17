"""
Auditoria de qualidade da camada consolidada (data/interim/vra.parquet).

Objetivo: descrever o dado como ele e -- sem corrigir nada -- para embasar
as decisoes de limpeza da etapa seguinte. Toda regra de limpeza aplicada
depois deve poder ser justificada por um numero deste relatorio.

Saida: relatorio em stdout + docs/auditoria_qualidade.md
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
ENTRADA = BASE / "data" / "interim" / "vra.parquet"
SAIDA_MD = BASE / "docs" / "auditoria_qualidade.md"

COLUNAS_DATA = ["partida_prevista", "partida_real", "chegada_prevista", "chegada_real"]


class Relatorio:
    """Escreve simultaneamente no stdout e num buffer para virar markdown."""

    def __init__(self) -> None:
        self.buffer = io.StringIO()

    def secao(self, titulo: str) -> None:
        self("\n" + "=" * 70)
        self(titulo)
        self("=" * 70)

    def __call__(self, texto: str = "") -> None:
        print(texto)
        self.buffer.write(texto + "\n")


def main() -> int:
    if not ENTRADA.exists():
        print(f"ERRO: {ENTRADA} nao existe.", file=sys.stderr)
        print("Execute antes: python src/02_consolidar.py", file=sys.stderr)
        return 1

    r = Relatorio()
    df = pd.read_parquet(ENTRADA)

    # ------------------------------------------------------------------
    r.secao("1. VISAO GERAL")
    r(f"registros : {len(df):,}")
    r(f"colunas   : {df.shape[1]}")
    r(f"memoria   : {df.memory_usage(deep=True).sum() / 1024**3:.2f} GB")
    r(f"periodo   : {df['ano_arquivo'].min()} a {df['ano_arquivo'].max()}")

    # ------------------------------------------------------------------
    r.secao("2. COMPLETUDE E CARDINALIDADE POR COLUNA")
    resumo = pd.DataFrame(
        {
            "tipo": df.dtypes.astype(str),
            "nulos": df.isna().sum(),
            "pct_nulo": (df.isna().mean() * 100).round(2),
            "distintos": df.nunique(dropna=True),
        }
    )
    r(resumo.to_string())

    # ------------------------------------------------------------------
    r.secao("3. DUPLICATAS")
    r(f"linhas identicas em todas as colunas: {df.duplicated().sum():,}")
    chave = ["sigla_icao_empresa", "numero_voo", "icao_origem",
             "icao_destino", "partida_prevista"]
    dup_chave = df.duplicated(subset=chave).sum()
    r(f"duplicatas pela chave natural {chave}:")
    r(f"  {dup_chave:,} ({dup_chave / len(df):.3%})")

    # ------------------------------------------------------------------
    r.secao("4. VOLUME POR ANO (detecta quebra estrutural)")
    por_ano = df.groupby("ano_arquivo").size().rename("voos").to_frame()
    base_2019 = por_ano.loc[2019, "voos"] if 2019 in por_ano.index else None
    if base_2019:
        por_ano["indice_2019=100"] = (por_ano["voos"] / base_2019 * 100).round(1)
    r(por_ano.to_string())

    # ------------------------------------------------------------------
    r.secao("5. SITUACAO DO VOO (base para definir cancelamento)")
    r(df["situacao_voo"].value_counts(dropna=False).to_string())
    r("")
    r("situacao_partida:")
    r(df["situacao_partida"].value_counts(dropna=False).head(15).to_string())

    # ------------------------------------------------------------------
    r.secao("6. COERENCIA DAS DATAS")
    for col in COLUNAS_DATA:
        s = df[col].dropna()
        if len(s):
            r(f"{col:20} min={s.min()}  max={s.max()}  nulos={df[col].isna().sum():,}")

    realizados = df[df["partida_real"].notna() & df["chegada_real"].notna()]
    invertidos = (realizados["chegada_real"] < realizados["partida_real"]).sum()
    r("")
    r(f"voos com chegada_real ANTES de partida_real: {invertidos:,} "
      f"({invertidos / max(len(realizados), 1):.4%})  <-- impossivel fisicamente")

    prev = df[df["partida_prevista"].notna() & df["chegada_prevista"].notna()]
    invertidos_prev = (prev["chegada_prevista"] < prev["partida_prevista"]).sum()
    r(f"voos com chegada_prevista ANTES de partida_prevista: {invertidos_prev:,}")

    # ------------------------------------------------------------------
    r.secao("7. ATRASO (metrica derivada -- ainda NAO limpa)")
    d = df.dropna(subset=["partida_prevista", "partida_real"]).copy()
    d["atraso_partida_min"] = (
        (d["partida_real"] - d["partida_prevista"]).dt.total_seconds() / 60
    )
    r(f"voos com partida prevista e real: {len(d):,}")
    r("")
    r("distribuicao do atraso de partida (minutos):")
    r(d["atraso_partida_min"]
      .describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.95, 0.99])
      .round(1).to_string())
    r("")
    absurdos = d["atraso_partida_min"].abs() > 24 * 60
    r(f"|atraso| > 24h: {absurdos.sum():,} ({absurdos.mean():.4%})  <-- outliers a tratar")
    r(f"atraso > 15 min (padrao de pontualidade): {(d['atraso_partida_min'] > 15).mean():.2%}")

    # ------------------------------------------------------------------
    r.secao("8. DIMENSOES CANDIDATAS")
    for col, rotulo in [
        ("sigla_icao_empresa", "companhias aereas"),
        ("icao_origem", "aeroportos de origem"),
        ("icao_destino", "aeroportos de destino"),
        ("modelo_equipamento", "modelos de aeronave"),
        ("codigo_tipo_linha", "tipos de linha"),
        ("codigo_di", "codigos DI"),
    ]:
        r(f"{rotulo:26} distintos: {df[col].nunique():,}")

    r("")
    r("top 12 companhias por volume:")
    top = (df.groupby("sigla_icao_empresa", observed=True)
             .agg(voos=("numero_voo", "size"),
                  empresa=("empresa_aerea", "first"))
             .sort_values("voos", ascending=False).head(12))
    top["pct"] = (top["voos"] / len(df) * 100).round(2)
    r(top.to_string())

    # ------------------------------------------------------------------
    r.secao("9. JUSTIFICATIVA (texto livre)")
    preenchida = df["justificativa"].notna().sum()
    r(f"preenchida em {preenchida:,} registros ({preenchida / len(df):.2%})")
    r(f"valores distintos: {df['justificativa'].nunique():,}")
    r("")
    r("top 15 justificativas:")
    r(df["justificativa"].value_counts().head(15).to_string())

    # ------------------------------------------------------------------
    SAIDA_MD.parent.mkdir(parents=True, exist_ok=True)
    SAIDA_MD.write_text(
        "# Auditoria de qualidade - VRA/ANAC\n\n```\n"
        + r.buffer.getvalue()
        + "\n```\n",
        encoding="utf-8",
    )
    print(f"\n\nrelatorio gravado em: {SAIDA_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
