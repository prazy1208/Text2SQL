"""Tests for FK relationship loading from metadata JSON."""

from pathlib import Path

import pytest

from backend.config import METADATA_STORE_DIR, RELATIONSHIP_METADATA_NAMES
from backend.services.relationship_retrieval import (
    filter_relationships_for_selected_tables,
    list_relationships_from_metadata,
)


def test_list_relationships_from_metadata_strips_embeddings():
    path = METADATA_STORE_DIR / RELATIONSHIP_METADATA_NAMES["retail_schema"]
    if not path.is_file():
        pytest.skip(f"Fixture not in repo: {path}")

    rows = list_relationships_from_metadata("retail_schema")
    assert isinstance(rows, list)
    assert len(rows) >= 1
    for r in rows:
        assert "embedding" not in r
        assert r.get("relationship_text")
        assert r.get("schema_name") == "retail_schema"


def test_filter_relationships_for_selected_tables():
    schema = "retail_schema"
    rel = [
        {
            "schema_name": schema,
            "source_table": "orders",
            "source_column": "customer_id",
            "target_schema": schema,
            "target_table": "customers",
            "target_column": "customer_id",
            "relationship_text": "x",
        }
    ]
    selected = [f"{schema}.orders", f"{schema}.customers"]
    out = filter_relationships_for_selected_tables(schema, rel, selected)
    assert len(out) == 1

    out2 = filter_relationships_for_selected_tables(schema, rel, [f"{schema}.orders"])
    assert out2 == []
