# Task 5: analyze_repo Tool - Implementation Complete

## Summary
Successfully implemented the `analyze_repo` tool for the PolyMaX Synthesizer MCP server. This tool detects repository mode (primary research vs review), analyzes structure, detects domains, and creates synthesis run records in the database.

## Files Created/Modified

### Created:
- **repo_analyzer.py** (1,946 bytes)
  - Main analysis function `analyze_repository()`
  - Repository structure parsing
  - Domain detection from README keywords
  - Mode detection (primary_research vs review)

### Modified:
- **server.py**
  - Added imports for `Database` and `analyze_repository`
  - Added `DB_PATH` constant
  - Implemented `analyze_repo` tool handler in `call_tool()`
  - Creates synthesis_run records in database
  - Returns structured JSON response

- **test_server.py**
  - Added `test_analyze_repo_primary_research()` test
  - Tests mode detection, structure parsing, and domain detection

## Test Results

### Unit Test (test_server.py)
```bash
$ pytest test_server.py::test_analyze_repo_primary_research -v
PASSED ✓
```

All tests verify:
- Correct mode detection (primary_research when tables + figures present)
- Domain extraction from README keywords
- Repository structure parsing (tables, figures, readme)

### End-to-End Testing

#### Test Case: Sparsity Trap Repository
Repository structure:
```
sparsity-trap-manuscript/
├── tables/
│   ├── gene_ssim_comparison.csv (5 genes, SSIM metrics)
│   └── encoder_performance.csv (3 encoders)
├── figures/
│   ├── poisson_vs_mse_comparison.png
│   ├── encoder_benchmark.png
│   └── spatial_predictions.png
└── README.md (spatial transcriptomics, loss functions, deep learning)
```

Output:
```json
{
  "synthesis_run_id": 2,
  "detected_mode": "primary_research",
  "repo_structure": {
    "has_results": true,
    "tables": ["encoder_performance.csv", "gene_ssim_comparison.csv"],
    "figures": ["poisson_vs_mse_comparison.png", "encoder_benchmark.png", "spatial_predictions.png"],
    "readme_exists": true
  },
  "detected_domains": [
    "spatial-transcriptomics",
    "loss-functions",
    "computational-pathology"
  ],
  "next_step": "Call ingest_results to load experimental data"
}
```

Database record created:
```
ID: 2
Repo Path: /tmp/.../sparsity-trap-manuscript
Mode: primary_research
Detected Domains: ["spatial-transcriptomics", "loss-functions", "computational-pathology"]
Status: analyzing
Created: 2025-12-25 17:31:56
```

## Domain Detection Keywords

The analyzer detects these domains from README content:

| Domain | Keywords |
|--------|----------|
| spatial-transcriptomics | "spatial transcriptomics", "visium" |
| loss-functions | "loss function", "mse", "poisson" |
| deep-learning | "deep learning", "neural network" |
| computational-pathology | "pathology", "histology" |

## Integration with Database

The tool creates records in `synthesis_runs` table:
- `repo_path`: Full path to repository
- `mode`: "primary_research" or "review"
- `detected_domains`: JSON array of domains
- `status`: "analyzing" (initial state)
- Returns `synthesis_run_id` for downstream tools

## Next Steps (from plan)

The tool correctly guides users to the next step:
- **Primary research mode**: "Call ingest_results to load experimental data"
- **Review mode**: "Call discover_literature"

## Sample Usage (via MCP)

```python
# Call via Claude Code MCP client
result = mcp_client.call_tool("analyze_repo", {
    "repo_path": "/home/user/sparsity-trap-manuscript",
    "mode": "auto"  # Optional: auto-detect
})

# Returns synthesis_run_id for next steps
synthesis_run_id = result["synthesis_run_id"]
```

## Validation

✅ Test fails before implementation (ModuleNotFoundError)
✅ Test passes after implementation
✅ End-to-end integration works
✅ Database records created correctly
✅ Domain detection accurate
✅ Mode detection accurate
✅ JSON response structure matches spec

## Commit

Commit SHA: `1448b2d673`

```
feat: implement analyze_repo tool

- Detects primary_research vs review mode
- Parses repository structure (tables, figures, README)
- Simple keyword-based domain detection
- Creates synthesis_run record in database
- Returns synthesis_run_id for next steps
```

---

**Task 5 Complete** ✓
Ready for Task 6: Implement ingest_results Tool
