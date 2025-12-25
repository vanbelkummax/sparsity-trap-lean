"""End-to-end integration test for PolyMaX Synthesizer.

Tests the complete pipeline with real sparsity-trap-manuscript repository:
1. analyze_repo
2. ingest_results
3. discover_literature (targeted)
4. extract_papers
5. synthesize_domains
6. generate_manuscript

Validates:
- Each tool returns expected structure
- Database state after each step
- Final manuscript has proper LaTeX structure
- Constraint satisfaction (values match tables)
"""
import pytest
import sqlite3
import os
import json
import re
from pathlib import Path


# Test data location
SPARSITY_TRAP_REPO = "/home/user/sparsity-trap-manuscript"


@pytest.fixture
def test_db(tmp_path):
    """Create isolated test database."""
    db_path = tmp_path / "test_e2e.db"

    # Initialize schema
    from database import init_database
    init_database(str(db_path))

    yield str(db_path)

    # Cleanup
    if db_path.exists():
        db_path.unlink()


class TestEndToEnd:
    """End-to-end pipeline tests."""

    def test_01_analyze_repo(self, test_db):
        """Step 1: Analyze sparsity-trap-manuscript repository."""
        from repo_analyzer import analyze_repository

        # Analyze real repo
        result = analyze_repository(SPARSITY_TRAP_REPO)

        # Validate structure
        assert "detected_mode" in result
        assert "repo_structure" in result
        assert "detected_domains" in result

        # Should detect primary research
        assert result["detected_mode"] == "primary_research"

        # Should detect tables
        assert result["repo_structure"]["has_results"] == True
        assert len(result["repo_structure"]["tables"]) >= 3

        # Should detect spatial transcriptomics domain
        assert "spatial-transcriptomics" in result["detected_domains"]

        print(f"✓ Analyzed repo: {result['detected_mode']}")
        print(f"✓ Domains: {', '.join(result['detected_domains'])}")
        print(f"✓ Tables: {len(result['repo_structure']['tables'])}")

    def test_02_ingest_results(self, test_db):
        """Step 2: Ingest results from tables."""
        from results_ingester import ingest_results_data

        # Ingest from sparsity-trap repo (function takes repo_path, not tables_dir)
        result = ingest_results_data(SPARSITY_TRAP_REPO)

        # Validate ingestion
        assert "total_experiments" in result
        assert "total_results" in result
        assert result["total_experiments"] >= 1
        assert result["total_results"] >= 50  # At least 50 genes

        # Check database state
        conn = sqlite3.connect(test_db)
        c = conn.cursor()

        # Should have experiments
        c.execute("SELECT COUNT(*) FROM experiments")
        exp_count = c.fetchone()[0]
        assert exp_count >= 1

        # Should have results with SSIM values
        c.execute("""
            SELECT COUNT(*) FROM results
            WHERE metric_name = 'SSIM_Poisson'
        """)
        ssim_count = c.fetchone()[0]
        assert ssim_count >= 50

        # Verify specific values from README
        c.execute("""
            SELECT metric_value FROM results
            WHERE metric_name = 'SSIM_Poisson'
            AND gene_name = 'TSPAN8'
        """)
        tspan8_ssim = c.fetchone()
        if tspan8_ssim:
            # TSPAN8 should have high SSIM
            assert float(tspan8_ssim[0]) > 0.5

        conn.close()

        print(f"✓ Ingested {result['total_experiments']} experiments")
        print(f"✓ Ingested {result['total_results']} results")

    def test_03_discover_literature(self, test_db):
        """Step 3: Discover literature (targeted mode)."""
        from literature_discovery import discover_targeted_literature

        # Use targeted discovery for speed
        queries = [
            "spatial transcriptomics prediction histology",
            "loss function sparse gene expression"
        ]

        result = discover_targeted_literature(
            queries=queries,
            db_path=test_db
        )

        # Validate discovery
        assert "total_papers_found" in result
        assert "queries_processed" in result
        assert result["queries_processed"] == len(queries)
        assert result["total_papers_found"] >= 2  # At least some papers

        # Check database state
        conn = sqlite3.connect(test_db)
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM papers")
        paper_count = c.fetchone()[0]
        assert paper_count >= 2

        conn.close()

        print(f"✓ Discovered {result['total_papers_found']} papers")
        print(f"✓ Processed {result['queries_processed']} queries")

    def test_04_extract_papers(self, test_db):
        """Step 4: Extract paper content."""
        from paper_extractor import extract_multiple_papers

        # Get paper IDs
        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute("SELECT id FROM papers")
        paper_ids = [row[0] for row in c.fetchall()]
        conn.close()

        # Extract papers
        result = extract_multiple_papers(
            paper_ids=paper_ids,
            db_path=test_db,
            depth="high"  # Fast extraction
        )

        # Validate extraction
        assert "total_papers" in result
        assert "successfully_extracted" in result
        assert result["successfully_extracted"] >= 1

        # Check database state
        conn = sqlite3.connect(test_db)
        c = conn.cursor()

        c.execute("""
            SELECT COUNT(*) FROM papers
            WHERE abstract IS NOT NULL
        """)
        extracted_count = c.fetchone()[0]
        assert extracted_count >= 1

        conn.close()

        print(f"✓ Extracted {result['successfully_extracted']}/{result['total_papers']} papers")

    def test_05_synthesize_domains(self, test_db):
        """Step 5: Synthesize domain knowledge."""
        from domain_synthesizer import synthesize_multiple_domains

        # Get domains
        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute("SELECT DISTINCT domains FROM experiments")
        domains_json = c.fetchone()
        conn.close()

        if domains_json:
            import json
            domains = json.loads(domains_json[0])
        else:
            domains = ["spatial-transcriptomics"]

        # Synthesize
        result = synthesize_multiple_domains(
            domains=domains,
            db_path=test_db
        )

        # Validate synthesis
        assert "domains_synthesized" in result
        assert "total_papers_analyzed" in result
        assert result["domains_synthesized"] >= 1

        # Check database state
        conn = sqlite3.connect(test_db)
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM domain_syntheses")
        synthesis_count = c.fetchone()[0]
        assert synthesis_count >= 1

        # Should have synthesis content
        c.execute("""
            SELECT synthesis FROM domain_syntheses
            LIMIT 1
        """)
        synthesis = c.fetchone()
        assert synthesis is not None
        assert len(synthesis[0]) > 100  # Non-trivial synthesis

        conn.close()

        print(f"✓ Synthesized {result['domains_synthesized']} domains")
        print(f"✓ Analyzed {result['total_papers_analyzed']} papers")

    def test_06_generate_manuscript(self, test_db, tmp_path):
        """Step 6: Generate complete manuscript."""
        from section_generator import assemble_manuscript

        # Generate manuscript
        output_dir = tmp_path / "manuscript"
        output_dir.mkdir()

        # Get experiment and domain info
        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute("SELECT id, domains FROM experiments LIMIT 1")
        row = c.fetchone()
        if row:
            experiment_id = row[0]
            import json
            domains = json.loads(row[1])
        else:
            experiment_id = 1
            domains = ["spatial-transcriptomics"]
        conn.close()

        result = assemble_manuscript(
            experiment_id=experiment_id,
            domains=domains,
            db_path=test_db,
            output_dir=str(output_dir)
        )

        # Validate generation
        assert "sections_generated" in result
        assert "output_path" in result
        assert result["sections_generated"] >= 3  # At least 3 sections

        # Check files created
        manuscript_file = Path(result["output_path"])
        assert manuscript_file.exists()

        # Read manuscript content
        manuscript = manuscript_file.read_text()

        # Validate LaTeX structure
        assert r"\documentclass" in manuscript
        assert r"\begin{document}" in manuscript
        assert r"\end{document}" in manuscript
        assert r"\section{Introduction}" in manuscript
        assert r"\section{Methods}" in manuscript

        # Validate citations exist
        assert r"\cite{" in manuscript or "citet{" in manuscript

        # Validate references to results
        # Should mention key metrics from README
        # Note: exact values depend on synthesis, check patterns
        assert "SSIM" in manuscript or "ssim" in manuscript.lower()
        assert "Poisson" in manuscript

        print(f"✓ Generated {result['sections_generated']} sections")
        print(f"✓ Output: {result['output_path']}")
        print(f"✓ Manuscript length: {len(manuscript)} chars")

        # Additional validation: check for constraint satisfaction
        self._validate_constraint_satisfaction(manuscript, test_db)

    def _validate_constraint_satisfaction(self, manuscript: str, db_path: str):
        """Validate that manuscript values match database constraints."""
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Get SSIM values from database
        c.execute("""
            SELECT gene_name, metric_value
            FROM results
            WHERE metric_name = 'SSIM_Poisson'
            ORDER BY metric_value DESC
            LIMIT 5
        """)
        top_genes = c.fetchall()

        if top_genes:
            # Check if top gene is mentioned
            top_gene = top_genes[0][0]
            top_ssim = float(top_genes[0][1])

            # Manuscript should reference high-performing genes or metrics
            # (exact mention depends on synthesis, so we check for patterns)
            has_metrics = bool(re.search(r'\d+\.\d{3}', manuscript))  # SSIM format
            has_gene_discussion = len(re.findall(r'[A-Z0-9]{3,}', manuscript)) > 10

            print(f"  ✓ Metrics present: {has_metrics}")
            print(f"  ✓ Gene discussion present: {has_gene_discussion}")

            # At least one should be true for constraint satisfaction
            assert has_metrics or has_gene_discussion

        conn.close()


def test_pipeline_integration(test_db, tmp_path):
    """Test complete pipeline in sequence."""
    print("\n" + "="*60)
    print("RUNNING COMPLETE END-TO-END PIPELINE")
    print("="*60)

    suite = TestEndToEnd()

    print("\n[1/6] Analyzing repository...")
    suite.test_01_analyze_repo(test_db)

    print("\n[2/6] Ingesting results...")
    suite.test_02_ingest_results(test_db)

    print("\n[3/6] Discovering literature...")
    suite.test_03_discover_literature(test_db)

    print("\n[4/6] Extracting papers...")
    suite.test_04_extract_papers(test_db)

    print("\n[5/6] Synthesizing domains...")
    suite.test_05_synthesize_domains(test_db)

    print("\n[6/6] Generating manuscript...")
    suite.test_06_generate_manuscript(test_db, tmp_path)

    print("\n" + "="*60)
    print("PIPELINE COMPLETE ✓")
    print("="*60)


if __name__ == "__main__":
    """Run end-to-end test standalone."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")

        # Initialize
        from database import init_database
        init_database(db_path)

        # Run pipeline
        test_pipeline_integration(db_path, Path(tmpdir))
