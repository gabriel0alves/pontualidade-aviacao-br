"""
BLOCO A — Construcao do universo analitico.

Entrada : data/interim/vra.parquet        (consolidado, sem limpeza)
Saida   : data/processed/voos.parquet     (universo analitico + campos derivados)
          docs/universo_analitico.md      (funil auditavel de cada regra)

Principio: NENHUMA limpeza silenciosa. Cada regra reporta quantos registros
afeta, e o resultado e um funil reproduzivel. Colunas originais nunca sao
sobrescritas -- todo tratamento gera campo derivado com sufixo proprio.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Parametros de tratamento: importados de src/regras.py, fonte unica de
# verdade. Nao redeclare esses valores aqui -- duas declaracoes da mesma regra
# divergem silenciosamente na primeira alteracao.
from regras import (
    CHAVE_NATURAL,
    GRUPO_RESIDUAL,
    GRUPOS_COMPANHIA,
    JANELA_FIM,
    JANELA_INICIO,
    LIMIARES_SEVERIDADE,
    LIMITE_ATRASO_MIN,
    LIMITES_CATEGORIA,
    PREFIXOS_ICAO_BR,
    ROTULOS_CATEGORIA,
)

BASE = Path(__file__).resolve().parents[1]
ENTRADA = BASE / "data" / "interim" / "vra.parquet"
SAIDA_PARQUET = BASE / "data" / "processed" / "voos.parquet"
SAIDA_DOC = BASE / "docs" / "universo_analitico.md"


class Funil:
    """Registra cada etapa do funil e escreve o relatorio auditavel."""

    def __init__(self, total_inicial: int) -> None:
        self.linhas: list[dict] = []
        self.anterior = total_inicial
        self.inicial = total_inicial
        self.buffer = io.StringIO()

    def etapa(self, nome: str, restantes: int, regra: str) -> None:
        removidos = self.anterior - restantes
        self.linhas.append({
            "etapa": nome,
            "regra": regra,
            "removidos": removidos,
            "restantes": restantes,
            "pct_do_inicial": round(restantes / self.inicial * 100, 3),
        })
        self.anterior = restantes

    def imprimir(self) -> str:
        df = pd.DataFrame(self.linhas)
        texto = df.to_string(index=False)
        print(texto)
        return texto


def main() -> int:
    if not ENTRADA.exists():
        print(f"ERRO: {ENTRADA} nao existe. Rode src/02_consolidar.py", file=sys.stderr)
        return 1

    SAIDA_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(ENTRADA)
    rel = io.StringIO()

    def log(t: str = "") -> None:
        print(t)
        rel.write(t + "\n")

    log("=" * 74)
    log("BLOCO A — CONSTRUCAO DO UNIVERSO ANALITICO")
    log("=" * 74)
    log(f"registros de entrada: {len(df):,}")

    funil = Funil(len(df))

    # ------------------------------------------------------------------
    # R1 — RECORTE GEOGRAFICO: voo domestico
    # ------------------------------------------------------------------
    log("\n" + "-" * 74)
    log("R1 — RECORTE GEOGRAFICO")
    log("-" * 74)
    orig_br = df["icao_origem"].astype(str).str.startswith(PREFIXOS_ICAO_BR)
    dest_br = df["icao_destino"].astype(str).str.startswith(PREFIXOS_ICAO_BR)
    df["voo_domestico"] = orig_br & dest_br

    # validacao cruzada contra a descricao textual do aeroporto
    desc_br = (df["descricao_origem"].str.contains("BRASIL", na=False)
               & df["descricao_destino"].str.contains("BRASIL", na=False))
    divergencia = int((df["voo_domestico"] ^ desc_br).sum())
    log(f"regra: prefixo ICAO {PREFIXOS_ICAO_BR} em origem E destino")
    log(f"validacao cruzada com 'BRASIL' na descricao: {divergencia} divergencias")
    log(f"  -> as duas regras {'CONCORDAM 100%' if divergencia == 0 else 'DIVERGEM'}")
    log(f"domesticos : {df['voo_domestico'].sum():,} ({df['voo_domestico'].mean():.2%})")
    log(f"internac.  : {(~df['voo_domestico']).sum():,}")

    df = df[df["voo_domestico"]].copy()
    funil.etapa("R1 recorte domestico", len(df),
                "origem E destino com prefixo ICAO brasileiro")

    # ------------------------------------------------------------------
    # R2 — JANELA TEMPORAL
    # ------------------------------------------------------------------
    log("\n" + "-" * 74)
    log("R2 — JANELA TEMPORAL")
    log("-" * 74)
    fora = df["partida_prevista"].notna() & (
        (df["partida_prevista"] < JANELA_INICIO) | (df["partida_prevista"] >= JANELA_FIM))
    log(f"regra: partida_prevista em [{JANELA_INICIO.date()}, {JANELA_FIM.date()})")
    log(f"registros com data fora da janela: {int(fora.sum()):,}")
    if fora.any():
        log("  amostra das datas fora da janela:")
        for v in df.loc[fora, "partida_prevista"].sort_values().unique()[:5]:
            log(f"    {pd.Timestamp(v)}")
    df = df[~fora].copy()
    funil.etapa("R2 janela temporal", len(df),
                f"partida_prevista dentro de [{JANELA_INICIO.date()}, {JANELA_FIM.date()})")

    # ------------------------------------------------------------------
    # R3 — DUPLICATAS
    # ------------------------------------------------------------------
    log("\n" + "-" * 74)
    log("R3 — DUPLICATAS PELA CHAVE NATURAL")
    log("-" * 74)
    log(f"chave: {CHAVE_NATURAL}")

    chave_nula = df[CHAVE_NATURAL].isna().any(axis=1)
    log(f"registros com componente da chave nulo: {int(chave_nula.sum()):,}")
    log("  -> NAO sao duplicatas; pandas trata NaN==NaN e os marcaria falsamente.")
    log("  -> mantidos na base; serao excluidos das metricas de atraso por R5.")

    # A deduplicacao roda SOMENTE sobre registros de chave completa. Aplicar
    # drop_duplicates ao frame inteiro colapsaria os registros de chave nula
    # entre si (NaN==NaN), destruindo dezenas de milhares de voos legitimos.
    com_chave = df[~chave_nula].copy()
    sem_chave = df[chave_nula].copy()

    dup = com_chave.duplicated(subset=CHAVE_NATURAL, keep=False)
    log(f"registros em duplicata real: {int(dup.sum()):,} "
        f"({dup.sum()/len(df):.4%} do recorte)")

    # criterio de desempate: preserva o registro mais completo do grupo
    com_chave["_completude"] = com_chave.notna().sum(axis=1)
    antes = len(com_chave)
    com_chave = (com_chave
                 .sort_values("_completude", ascending=False, kind="mergesort")
                 .drop_duplicates(subset=CHAVE_NATURAL, keep="first")
                 .drop(columns="_completude"))
    removidos = antes - len(com_chave)

    df = pd.concat([com_chave, sem_chave]).sort_index()

    log("regra aplicada: manter o registro com MAIS campos preenchidos do grupo;")
    log("                empate resolvido pela ordem original (mergesort estavel)")
    log(f"removidos: {removidos:,}")
    log(f"registros de chave nula preservados integralmente: {len(sem_chave):,}")
    funil.etapa("R3 deduplicacao", len(df),
                "1 registro por chave natural, preservando o mais completo")

    # ------------------------------------------------------------------
    # R4 — CAMPOS DERIVADOS DE ATRASO
    # ------------------------------------------------------------------
    log("\n" + "-" * 74)
    log("R4 — CAMPOS DERIVADOS (originais preservados)")
    log("-" * 74)
    df["atraso_partida_min"] = ((df["partida_real"] - df["partida_prevista"])
                                .dt.total_seconds() / 60)
    df["atraso_chegada_min"] = ((df["chegada_real"] - df["chegada_prevista"])
                                .dt.total_seconds() / 60)
    df["recuperacao_min"] = df["atraso_chegada_min"] - df["atraso_partida_min"]
    log("criados: atraso_partida_min, atraso_chegada_min, recuperacao_min")
    log("  atrasos NEGATIVOS sao preservados como estao (partida antecipada e")
    log("  informacao legitima). Nao ha truncamento em zero.")

    # ------------------------------------------------------------------
    # R5 — VALIDADE PARA METRICAS DE ATRASO
    # ------------------------------------------------------------------
    log("\n" + "-" * 74)
    log("R5 — FLAG DE VALIDADE PARA METRICAS DE ATRASO")
    log("-" * 74)
    realizado = df["situacao_voo"] == "REALIZADO"
    tem_horarios = df["partida_prevista"].notna() & df["partida_real"].notna()
    dentro_limite = df["atraso_partida_min"].abs() <= LIMITE_ATRASO_MIN

    df["atraso_valido"] = realizado & tem_horarios & dentro_limite

    log(f"situacao_voo == REALIZADO           : {int(realizado.sum()):,}")
    log(f"  com partida prevista E real       : {int((realizado & tem_horarios).sum()):,}")
    log(f"  com |atraso| <= {LIMITE_ATRASO_MIN} min ({LIMITE_ATRASO_MIN//60}h) : "
        f"{int(df['atraso_valido'].sum()):,}")
    outliers = realizado & tem_horarios & ~dentro_limite
    log(f"\noutliers extremos excluidos das metricas: {int(outliers.sum()):,} "
        f"({outliers.sum()/max(int((realizado & tem_horarios).sum()),1):.4%})")
    if outliers.any():
        log("  amostra (minutos):")
        for v in df.loc[outliers, "atraso_partida_min"].sort_values().head(3):
            log(f"    {v:,.0f} min ({v/1440:,.1f} dias)")
        for v in df.loc[outliers, "atraso_partida_min"].sort_values().tail(3):
            log(f"    {v:,.0f} min ({v/1440:,.1f} dias)")
    log("  -> NAO removidos da base; apenas marcados com atraso_valido=False,")
    log("     para que continuem auditaveis e possam ser reanalisados.")

    # ------------------------------------------------------------------
    # R6 — CATEGORIAS DE ATRASO
    # ------------------------------------------------------------------
    log("\n" + "-" * 74)
    log("R6 — CLASSIFICACAO DE ATRASO (campo derivado)")
    log("-" * 74)
    limites = LIMITES_CATEGORIA
    rotulos = ROTULOS_CATEGORIA
    df["categoria_atraso"] = pd.cut(
        df["atraso_partida_min"].where(df["atraso_valido"]),
        bins=limites, labels=rotulos, right=False)

    log("Faixas (sobre atraso_partida_min, apenas onde atraso_valido):")
    for r, lo, hi in zip(rotulos, limites[:-1], limites[1:]):
        log(f"  {r:22} [{lo}, {hi})")
    log("\nNota: 'Antecipado' exige mais de 15 min de antecipacao. Um voo que parte")
    log("1 min adiantado e operacionalmente PONTUAL, nao antecipado -- por isso a")
    log("faixa Pontual e simetrica em torno de zero (-15 a +15).")
    log("")
    dist = df["categoria_atraso"].value_counts().reindex(rotulos)
    tab = pd.DataFrame({"voos": dist,
                        "pct": (dist / dist.sum() * 100).round(2)})
    log(tab.to_string())

    # flags acumuladas
    # dtype 'boolean' (anulavel) para que voos sem atraso valido fiquem NA em vez
    # de False -- False significaria "nao atrasou", o que seria afirmacao indevida
    for limiar in LIMIARES_SEVERIDADE:
        df[f"atrasado_{limiar}"] = (
            (df["atraso_partida_min"] > limiar)
            .astype("boolean")
            .where(df["atraso_valido"])
        )
    log("\ncriadas flags acumuladas: atrasado_15, atrasado_30, atrasado_60")
    log("  dtype 'boolean' anulavel: voos sem atraso valido ficam NA, nunca False")

    # ------------------------------------------------------------------
    # R7 — numero_assentos
    # ------------------------------------------------------------------
    log("\n" + "-" * 74)
    log("R7 — TRATAMENTO DE numero_assentos")
    log("-" * 74)
    neg = (df["numero_assentos"] < 0).sum()
    zero = (df["numero_assentos"] == 0).sum()
    nulo = df["numero_assentos"].isna().sum()
    log(f"negativos (impossivel) : {int(neg):,}")
    log(f"zeros                  : {int(zero):,}")
    log(f"nulos                  : {int(nulo):,}")
    df["assentos_valido"] = df["numero_assentos"].where(df["numero_assentos"] > 0)
    log(f"\ncriado 'assentos_valido': valores <= 0 viram nulo. Coluna original")
    log(f"'numero_assentos' preservada intacta.")
    log(f"validos: {int(df['assentos_valido'].notna().sum()):,} "
        f"({df['assentos_valido'].notna().mean():.2%})")
    log("-> insuficiente para metricas de oferta; ver limitacoes do case.")

    # ------------------------------------------------------------------
    # R8 — DIMENSOES AUXILIARES
    # ------------------------------------------------------------------
    log("\n" + "-" * 74)
    log("R8 — DIMENSOES DERIVADAS")
    log("-" * 74)
    df["ano"] = df["partida_prevista"].dt.year
    df["mes"] = df["partida_prevista"].dt.month
    df["ano_mes"] = df["partida_prevista"].dt.to_period("M").astype(str)
    df["dia_semana"] = df["partida_prevista"].dt.dayofweek
    df["hora_prevista"] = df["partida_prevista"].dt.hour
    df["rota"] = (df["icao_origem"].astype(str) + "-" + df["icao_destino"].astype(str))

    # Mapa por CODIGO ICAO, sem vigencia temporal -- ver regras.py para o
    # limite conhecido (caso OWT -> ACN) e a decisao pendente.
    df["grupo_companhia"] = (df["sigla_icao_empresa"].astype(str)
                             .map(GRUPOS_COMPANHIA).fillna(GRUPO_RESIDUAL))
    log("criadas: ano, mes, ano_mes, dia_semana, hora_prevista, rota, grupo_companhia")
    log("")
    log(df["grupo_companhia"].value_counts().to_frame("voos").assign(
        pct=lambda t: (t["voos"] / len(df) * 100).round(2)).to_string())

    # ------------------------------------------------------------------
    # R9 — MARCACAO DE ANO PARCIAL
    # ------------------------------------------------------------------
    log("\n" + "-" * 74)
    log("R9 — ANOS PARCIAIS")
    log("-" * 74)
    meses_por_ano = df.groupby("ano")["mes"].nunique()
    anos_parciais = meses_por_ano[meses_por_ano < 12].index.tolist()
    df["ano_parcial"] = df["ano"].isin(anos_parciais)
    log("meses distintos por ano:")
    log(meses_por_ano.to_frame("meses").to_string())
    log(f"\nanos marcados como PARCIAIS: {anos_parciais}")
    log("-> criada flag 'ano_parcial'. Comparacoes de volume anual devem usar")
    log("   YTD homologo; anualizacao e proibida (ver docs/definicao_do_case.md).")

    # ------------------------------------------------------------------
    # FUNIL FINAL
    # ------------------------------------------------------------------
    log("\n" + "=" * 74)
    log("FUNIL DO UNIVERSO ANALITICO")
    log("=" * 74)
    texto_funil = funil.imprimir()
    rel.write(texto_funil + "\n")

    log("\n" + "=" * 74)
    log("UNIVERSO FINAL")
    log("=" * 74)
    log(f"registros na base tratada     : {len(df):,}")
    log(f"  com atraso_valido = True    : {int(df['atraso_valido'].sum()):,} "
        f"({df['atraso_valido'].mean():.2%})")
    log(f"  cancelados                  : {int((df['situacao_voo']=='CANCELADO').sum()):,}")
    log(f"periodo                       : {df['partida_prevista'].min()} a "
        f"{df['partida_prevista'].max()}")
    log(f"companhias                    : {df['sigla_icao_empresa'].nunique():,}")
    log(f"aeroportos (origem)           : {df['icao_origem'].nunique():,}")
    log(f"rotas                         : {df['rota'].nunique():,}")

    df.to_parquet(SAIDA_PARQUET, engine="pyarrow", compression="snappy", index=False)
    log(f"\ngravado: {SAIDA_PARQUET}")
    log(f"tamanho: {SAIDA_PARQUET.stat().st_size / 1024**2:.1f} MB")

    SAIDA_DOC.write_text(
        "# Universo Analítico — Bloco A\n\n"
        "Documento gerado por `src/04_universo.py`. Cada regra de tratamento está\n"
        "registrada com o número de registros afetados. Nenhuma limpeza silenciosa.\n\n"
        "```\n" + rel.getvalue() + "```\n",
        encoding="utf-8")
    print(f"relatorio: {SAIDA_DOC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
