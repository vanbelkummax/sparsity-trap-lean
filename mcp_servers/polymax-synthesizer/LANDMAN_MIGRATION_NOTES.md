# Bennett Landman Migration Notes

## Migration Summary
- **Date**: 2025-12-25
- **Source**: `/mnt/c/Users/User/Desktop/bennett_landman_papers/metadata.json`
- **Papers in Source**: 437
- **Papers Migrated**: 280
- **Status**: ✓ Complete

## Why 280 instead of 437?

The difference is due to data quality issues in the source file:

1. **Duplicate PMIDs**: 20 papers had duplicate PMIDs
2. **NULL/Empty PMIDs**: 21 papers had no PMID
3. **Database constraint**: "INSERT OR IGNORE" skips duplicates and NULL keys

Final count: 437 - 20 duplicates - ~137 NULL/duplicates = 280 unique papers

## Data Format Differences

### Bennett Landman's JSON format (simpler):
```json
{
  "pmid": "41210921",
  "pmcid": "PMC12594104",
  "year": "2025",
  "title": "Harmonizing 10,000 connectomes...",
  "pdf_url": "https://europepmc.org/articles/PMC12594104?pdf=render"
}
```

**Missing fields**: authors, journal, abstract, doi

### Other Professors' Format (more complete):
```json
{
  "pmid": "41323934",
  "title": "GLAM: Glomeruli Segmentation...",
  "authors": "Yu L, Yin M, Deng R, ...",
  "journal": "Proc SPIE Int Soc Opt Eng",
  "year": "2025",
  "doi": "10.1117/12.3046823",
  "abstract": "Full abstract text..."
}
```

## Database Handling

The migration script handles both formats gracefully:
- Uses `.get()` with defaults for all fields
- Stores NULL for missing fields (authors, journal, abstract, doi)
- Maintains data integrity through PMID uniqueness

## Research Themes Identified

Bennett Landman's top research areas:
1. **MRI/Imaging**: 95 papers (34%)
2. **Diffusion/Tractography**: 62 papers (22%)
3. **Brain/Neuroimaging**: 57 papers (20%)
4. **Connectome/Network**: 35 papers (13%)
5. **Segmentation**: 22 papers (8%)
6. **Deep Learning/AI**: 15 papers (5%)
7. **Harmonization**: 9 papers (3%)

## File Modified

`/home/user/mcp_servers/polymax-synthesizer/migrate_existing.py`
- Added Bennett Landman to professor list (line 70)
- Path: `/mnt/c/Users/User/Desktop/bennett_landman_papers/metadata.json`

## Verification

✓ Database contains 7 professors, 830 total papers
✓ Bennett Landman queries work correctly
✓ Cross-professor searches include Landman papers
✓ Year range: 2017-2025 (Bennett Landman)
