"""
Configuracao comum dos testes.

Dois niveis de teste, deliberadamente separados:

  - UNITARIOS: rodam sobre amostras deterministicas construidas no proprio
    teste. Sao rapidos e nao dependem de artefato nenhum. Sempre executam.

  - CONTRATO DE DADOS (marca 'dados'): validam o artefato real
    data/processed/voos.parquet. Sao pulados automaticamente se o arquivo nao
    existir, para que o repositorio possa ser clonado e testado sem 3,6 GB de
    dados. Leem apenas as colunas necessarias e, quando possivel, apenas os
    metadados do Parquet -- reconstruir 5,4 milhoes de linhas a cada teste
    seria desperdicio.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
PARQUET_UNIVERSO = RAIZ / "data" / "processed" / "voos.parquet"
PARQUET_INTERIM = RAIZ / "data" / "interim" / "vra.parquet"

# src/ nao e um pacote instalavel; entra no path para que 'import regras'
# funcione igual ao que acontece quando os scripts rodam com 'python src/xx.py'.
sys.path.insert(0, str(RAIZ / "src"))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "dados: exige o artefato data/processed/voos.parquet (pulado se ausente)",
    )


@pytest.fixture(scope="session")
def caminho_universo() -> Path:
    if not PARQUET_UNIVERSO.exists():
        pytest.skip(f"artefato ausente: {PARQUET_UNIVERSO} — rode src/04_universo.py")
    return PARQUET_UNIVERSO


@pytest.fixture(scope="session")
def esquema_universo(caminho_universo: Path):
    """Esquema Arrow lido dos METADADOS, sem carregar dado algum."""
    import pyarrow.parquet as pq

    return pq.ParquetFile(caminho_universo).schema_arrow


@pytest.fixture(scope="session")
def meta_universo(caminho_universo: Path):
    """Metadados do Parquet (contagens, row groups, estatisticas)."""
    import pyarrow.parquet as pq

    return pq.ParquetFile(caminho_universo).metadata
