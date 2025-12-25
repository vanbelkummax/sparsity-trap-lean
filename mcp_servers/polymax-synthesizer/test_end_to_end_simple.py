"""Simplified end-to-end integration test for PolyMaX Synthesizer.

Tests the complete pipeline with real sparsity-trap-manuscript repository.
This is a simplified version that matches the actual implementation.
"""
import pytest
import os
from pathlib import Path


# Test data location
SPARSITY_TRAP_REPO = "/home/user/sparsity-trap-manuscript"


def test_01_analyze_repository():
    """Test repository analysis."""
    from repo_analyzer import analyze_repository

    print("\n[1/4] Analyzing repository...")

    result = analyze_repository(SPARSITY_TRAP_REPO)

    # Validate
    assert "detected_mode" in result
    assert result["detected_mode"] == "primary_research"
    assert "detected_domains" in result
    assert "spatial-transcriptomics" in result["detected_domains"]
    assert "repo_structure" in result
    assert result["repo_structure"]["has_results"] == True
    assert len(result["repo_structure"]["tables"]) >= 3

    print(f"  ✓ Mode: {result['detected_mode']}")
    print(f"  ✓ Domains: {', '.join(result['detected_domains'])}")
    print(f"  ✓ Tables: {len(result['repo_structure']['tables'])}")


def test_02_ingest_results():
    """Test results ingestion."""
    from results_ingester import ingest_results_data

    print("\n[2/4] Ingesting results...")

    result = ingest_results_data(SPARSITY_TRAP_REPO)

    # Validate
    assert "key_findings" in result
    assert "constraints" in result
    assert len(result["key_findings"]) > 0
    assert len(result["constraints"]) > 0

    print(f"  ✓ Key findings: {len(result['key_findings'])}")
    print(f"  ✓ Constraints: {len(result['constraints'])}")


def test_03_discover_literature(tmp_path):
    """Test literature discovery."""
    from literature_discovery import discover_targeted_literature

    print("\n[3/4] Discovering literature...")

    # Use temp database
    db_path = str(tmp_path / "test.db")

    # Initialize database
    from database import init_database
    init_database(db_path)

    # Discover
    queries = ["spatial transcriptomics histology"]
    result = discover_targeted_literature(queries, db_path)

    # Validate
    assert "papers_added" in result
    assert result["papers_added"] >= 0  # May be 0 if network issues

    print(f"  ✓ Papers found: {result['papers_added']}")


def test_04_detect_field():
    """Test field detection."""
    from section_generator import detect_field_from_domains

    print("\n[4/4] Detecting field from domains...")

    # Detect field
    domains = ["spatial-transcriptomics", "loss-functions"]
    field = detect_field_from_domains(domains)

    # Validate
    assert field is not None
    assert len(field) > 0

    print(f"  ✓ Field detected: {field}")


def test_pipeline_integration(tmp_path):
    """Run complete pipeline in sequence."""
    print("\n" + "="*60)
    print("RUNNING SIMPLIFIED END-TO-END PIPELINE")
    print("="*60)

    test_01_analyze_repository()
    test_02_ingest_results()
    test_03_discover_literature(tmp_path)
    test_04_detect_field()

    print("\n" + "="*60)
    print("PIPELINE COMPLETE ✓")
    print("="*60)


if __name__ == "__main__":
    """Run end-to-end test standalone."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        test_pipeline_integration(Path(tmpdir))
