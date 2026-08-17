"""
Ingestao dos microdados VRA (Voo Regular Ativo) da ANAC.

Fonte : https://siros.anac.gov.br/siros/registros/diversos/vra/
Grao  : 1 linha = 1 voo de transporte aereo regular
Saida : data/raw/VRA_<ano>_<mes>.csv  (camada bruta, imutavel)

O download e idempotente: arquivos ja baixados e com tamanho coerente
sao ignorados, permitindo retomar a ingestao apos uma interrupcao.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests

BASE_URL = "https://siros.anac.gov.br/siros/registros/diversos/vra"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

PERIODO_INICIO = (2019, 1)
PERIODO_FIM = (2026, 6)

TIMEOUT = 120
MAX_TENTATIVAS = 3
CHUNK = 1024 * 256


def meses_do_periodo(inicio: tuple[int, int], fim: tuple[int, int]):
    """Gera os pares (ano, mes) do intervalo fechado [inicio, fim]."""
    ano, mes = inicio
    while (ano, mes) <= fim:
        yield ano, mes
        mes += 1
        if mes > 12:
            ano, mes = ano + 1, 1


def tamanho_remoto(url: str) -> int | None:
    """Retorna o Content-Length do arquivo remoto, ou None se indisponivel."""
    try:
        resp = requests.head(url, timeout=TIMEOUT)
        resp.raise_for_status()
        return int(resp.headers.get("Content-Length", 0)) or None
    except requests.RequestException:
        return None


def baixar(url: str, destino: Path) -> tuple[str, int]:
    """
    Baixa `url` para `destino`, pulando o download se o arquivo local ja
    estiver completo. Retorna (status, bytes) onde status e um de:
    'baixado', 'existente', 'indisponivel'.
    """
    esperado = tamanho_remoto(url)
    if esperado is None:
        return "indisponivel", 0

    if destino.exists() and destino.stat().st_size == esperado:
        return "existente", esperado

    temporario = destino.with_suffix(".parcial")
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            with requests.get(url, stream=True, timeout=TIMEOUT) as resp:
                resp.raise_for_status()
                with open(temporario, "wb") as f:
                    for bloco in resp.iter_content(chunk_size=CHUNK):
                        f.write(bloco)
            # so promove o arquivo se o download veio completo
            if temporario.stat().st_size == esperado:
                temporario.replace(destino)
                return "baixado", esperado
            raise OSError(
                f"tamanho divergente: {temporario.stat().st_size} != {esperado}"
            )
        except (requests.RequestException, OSError) as erro:
            if tentativa == MAX_TENTATIVAS:
                temporario.unlink(missing_ok=True)
                raise
            time.sleep(2 * tentativa)

    return "indisponivel", 0


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    meses = list(meses_do_periodo(PERIODO_INICIO, PERIODO_FIM))
    print(f"Ingestao VRA/ANAC | {len(meses)} meses | destino: {RAW_DIR}")
    print("-" * 62)

    contagem = {"baixado": 0, "existente": 0, "indisponivel": 0}
    total_bytes = 0
    indisponiveis: list[str] = []

    for ano, mes in meses:
        nome = f"VRA_{ano}_{mes:02d}.csv"
        url = f"{BASE_URL}/{ano}/{nome}"
        destino = RAW_DIR / nome

        status, tamanho = baixar(url, destino)
        contagem[status] += 1
        total_bytes += tamanho
        if status == "indisponivel":
            indisponiveis.append(nome)

        marcador = {"baixado": "+", "existente": ".", "indisponivel": "x"}[status]
        print(f"{marcador} {nome:20} {tamanho / 1024**2:8.2f} MB  ({status})")

    print("-" * 62)
    print(
        f"baixados: {contagem['baixado']} | "
        f"ja existentes: {contagem['existente']} | "
        f"indisponiveis: {contagem['indisponivel']}"
    )
    print(f"volume total em data/raw: {total_bytes / 1024**3:.2f} GB")

    if indisponiveis:
        print("\nMeses nao publicados pela ANAC:")
        for nome in indisponiveis:
            print(f"  - {nome}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
