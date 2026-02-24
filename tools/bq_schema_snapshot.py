"""Gera snapshot das tabelas do BigQuery para revisão de estrutura atual.

Uso comum:
  python tools/bq_schema_snapshot.py \
    --project ingestaokraken \
    --dataset cotacao_intraday \
    --tables acao_bovespa,cotacao_b3,sinais_eod

Também aceita lista em arquivo (um nome por linha):
  python tools/bq_schema_snapshot.py --tables-file minhas_tabelas.txt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List, Sequence

from google.cloud import bigquery


def _parse_tables(raw_tables: str | None, tables_file: str | None) -> List[str]:
    tables: list[str] = []

    if raw_tables:
        tables.extend([item.strip() for item in raw_tables.split(",") if item.strip()])

    if tables_file:
        for line in Path(tables_file).read_text(encoding="utf-8").splitlines():
            cleaned = line.strip()
            if cleaned and not cleaned.startswith("#"):
                tables.append(cleaned)

    # remove duplicados preservando ordem
    seen: set[str] = set()
    unique_tables: list[str] = []
    for table in tables:
        if table not in seen:
            seen.add(table)
            unique_tables.append(table)
    return unique_tables


def _list_dataset_tables(client: bigquery.Client, dataset_ref: str) -> list[str]:
    return sorted([table.table_id for table in client.list_tables(dataset_ref)])


def _build_table_snapshot(table: bigquery.table.Table) -> dict:
    schema = [
        {
            "name": field.name,
            "type": field.field_type,
            "mode": field.mode,
            "description": field.description,
            "policy_tags": (
                list(field.policy_tags.names) if field.policy_tags else None
            ),
        }
        for field in table.schema
    ]

    return {
        "full_table_id": f"{table.project}.{table.dataset_id}.{table.table_id}",
        "table_type": table.table_type,
        "num_rows": int(table.num_rows or 0),
        "num_bytes": int(table.num_bytes or 0),
        "created": table.created.isoformat() if table.created else None,
        "modified": table.modified.isoformat() if table.modified else None,
        "partitioning": {
            "type": (
                table.time_partitioning.type_
                if table.time_partitioning
                else ("RANGE" if table.range_partitioning else None)
            ),
            "field": (
                table.time_partitioning.field
                if table.time_partitioning
                else (
                    table.range_partitioning.field if table.range_partitioning else None
                )
            ),
            "expiration_ms": (
                table.time_partitioning.expiration_ms if table.time_partitioning else None
            ),
        },
        "clustering_fields": table.clustering_fields,
        "labels": table.labels,
        "schema": schema,
    }


def _render_markdown(summary: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Snapshot BigQuery: `{summary['dataset']}`")
    lines.append("")
    lines.append(f"- Projeto: `{summary['project']}`")
    lines.append(f"- Dataset: `{summary['dataset']}`")
    lines.append(f"- Tabelas encontradas: `{len(summary['tables'])}`")
    if summary["missing_tables"]:
        lines.append(
            f"- Tabelas ausentes (solicitadas, mas não encontradas): `{', '.join(summary['missing_tables'])}`"
        )
    lines.append("")

    for table in summary["tables"]:
        lines.append(f"## `{table['full_table_id']}`")
        lines.append("")
        lines.append(f"- Tipo: `{table['table_type']}`")
        lines.append(f"- Linhas: `{table['num_rows']}`")
        lines.append(f"- Tamanho (bytes): `{table['num_bytes']}`")
        partition_type = table["partitioning"]["type"] or "NONE"
        partition_field = table["partitioning"]["field"] or "-"
        clustering = ", ".join(table["clustering_fields"] or []) or "-"
        lines.append(f"- Particionamento: `{partition_type}` em `{partition_field}`")
        lines.append(f"- Clusterização: `{clustering}`")
        lines.append("")
        lines.append("### Colunas")
        lines.append("")
        lines.append("| Nome | Tipo | Modo |")
        lines.append("|------|------|------|")
        for field in table["schema"]:
            lines.append(f"| {field['name']} | {field['type']} | {field['mode']} |")
        lines.append("")

    return "\n".join(lines)


def _resolve_target_tables(
    requested_tables: Sequence[str],
    dataset_tables: Sequence[str],
) -> tuple[list[str], list[str]]:
    if not requested_tables:
        return list(dataset_tables), []

    available = set(dataset_tables)
    found = [table for table in requested_tables if table in available]
    missing = [table for table in requested_tables if table not in available]
    return found, missing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="ingestaokraken", help="ID do projeto GCP")
    parser.add_argument(
        "--dataset",
        default="cotacao_intraday",
        help="Dataset no BigQuery (ex.: cotacao_intraday)",
    )
    parser.add_argument(
        "--tables",
        default=None,
        help="Lista separada por vírgula de tabelas para inspecionar",
    )
    parser.add_argument(
        "--tables-file",
        default=None,
        help="Arquivo com uma tabela por linha",
    )
    parser.add_argument(
        "--output-json",
        default="bq_schema_snapshot.json",
        help="Caminho do arquivo JSON de saída",
    )
    parser.add_argument(
        "--output-md",
        default="bq_schema_snapshot.md",
        help="Caminho do arquivo Markdown de saída",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = bigquery.Client(project=args.project)
    dataset_ref = f"{args.project}.{args.dataset}"

    requested_tables = _parse_tables(args.tables, args.tables_file)
    dataset_tables = _list_dataset_tables(client, dataset_ref)
    target_tables, missing_tables = _resolve_target_tables(requested_tables, dataset_tables)

    snapshots: list[dict] = []
    for table_id in target_tables:
        table = client.get_table(f"{dataset_ref}.{table_id}")
        snapshots.append(_build_table_snapshot(table))

    payload = {
        "project": args.project,
        "dataset": args.dataset,
        "requested_tables": requested_tables,
        "missing_tables": missing_tables,
        "tables": snapshots,
    }

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(_render_markdown(payload), encoding="utf-8")

    print(f"Snapshot gerado: {output_json}")
    print(f"Resumo Markdown: {output_md}")
    if missing_tables:
        print(f"Tabelas não encontradas: {', '.join(missing_tables)}")


if __name__ == "__main__":
    main()
