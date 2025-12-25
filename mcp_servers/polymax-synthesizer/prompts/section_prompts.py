"""Prompts for manuscript section generation using Claude Opus 4.5.

This module contains prompt templates for generating individual manuscript sections
with proper LaTeX formatting and data grounding.

Future Enhancement:
- Integrate Claude Opus 4.5 API for section generation
- Replace template-based generation with LLM-powered prose
"""

RESULTS_PROMPT = """You are writing the Results section of a scientific manuscript.

## Context

You have experimental data from tables and figures. Your task is to write a Results section that:
1. Grounds every claim in exact values from YOUR data
2. Cites table/figure references properly
3. Uses professional LaTeX formatting

## Your Data

{data_summary}

## Requirements

### Data Grounding
- **Cite exact values**: "SSIM improved from 0.193 to 0.605 (Table~\\ref{{tab:results}})"
- **Never round**: Use exact values from tables (0.605, not 0.6 or "approximately 0.6")
- **Constraint checking**: All cited values must match the provided data exactly

### LaTeX Formatting
- Use **non-breaking spaces** before citations: `Table~\\ref{{tab:results}}` NOT `Table \\ref{{tab:results}}`
- Use **non-breaking spaces** before citations: `Figure~\\ref{{fig:results}}` NOT `Figure \\ref{{fig:results}}`
- Reference YOUR figures/tables, not generic ones
- Use `\\ref{{}}` for cross-references

### Structure
1. **Opening statement**: Briefly state what was evaluated
2. **Key findings**: Present main results with exact values and citations
3. **Supporting results**: Additional findings that support the main claim
4. **Figure/table references**: Guide reader to visual evidence

### Example Output

```latex
\\section{{Results}}

We evaluated our approach on spatial transcriptomics prediction from H\\&E images.

\\subsection{{Poisson Loss Improves Sparsity Handling}}

Poisson loss significantly outperformed MSE loss across all metrics. SSIM improved from 0.193 (MSE) to 0.605 (Poisson), representing a 213\\% relative improvement (Table~\\ref{{tab:results}}). Similarly, PCC increased from 0.147 to 0.489 (233\\% improvement).

Gene-level analysis revealed that Poisson loss particularly benefits sparse genes. For genes with expression in fewer than 10\\% of spots, SSIM improved by 312\\% on average (Figure~\\ref{{fig:sparse_genes}}).

\\subsection{{Performance Across Tissue Types}}

Table~\\ref{{tab:tissue_types}} summarizes results across different tissue regions. Tumor regions showed the strongest improvement (SSIM: 0.612), followed by stroma (SSIM: 0.598) and necrotic regions (SSIM: 0.543).
```

### Important Notes
- **No speculation**: Only report what the data shows
- **No interpretation**: Save discussion for Discussion section
- **Exact citations**: Always include `Table~\\ref{{}}` or `Figure~\\ref{{}}`
- **Professional tone**: Concise, factual, third-person

Now generate the Results section based on the provided data.
"""

METHODS_PROMPT = """You are writing the Methods section of a scientific manuscript.

## Context

You need to describe the experimental approach, algorithms, and statistical methods used in this work.

## Your Implementation Details

{methods_summary}

## Requirements

### Content
1. **Dataset description**: What data was used, how many samples, key characteristics
2. **Preprocessing**: Data preparation steps
3. **Model architecture**: Algorithm/model design with key hyperparameters
4. **Training procedure**: Optimization, loss functions, validation strategy
5. **Evaluation metrics**: How performance was measured

### LaTeX Formatting
- Use `\\texttt{{}}` for code/software names: `\\texttt{{PyTorch}}`
- Use mathematical notation for equations: `$L = -\\log P(y|x)$`
- Use algorithmic environments if describing algorithms
- Non-breaking spaces before equation references: `Equation~\\ref{{eq:loss}}`

### Example Output

```latex
\\section{{Methods}}

\\subsection{{Dataset}}

We used Visium HD spatial transcriptomics data from 12 colorectal cancer samples, paired with H\\&E histology images. Each sample contained 50,000-100,000 spots at 2μm resolution with gene expression measurements for 18,000 genes.

\\subsection{{Model Architecture}}

Our approach uses a vision transformer encoder (\\texttt{{Virchow2}}) to extract 256-dimensional features from each 2μm patch. Features are processed through a spatial context module with 3 graph attention layers, followed by a gene expression decoder.

\\subsection{{Loss Function}}

We compared two loss functions for sparse gene expression prediction:
\\begin{{equation}}
L_{{MSE}} = \\frac{{1}}{{N}}\\sum_{{i=1}}^{{N}}(y_i - \\hat{{y}}_i)^2
\\label{{eq:mse}}
\\end{{equation}}

\\begin{{equation}}
L_{{Poisson}} = -\\sum_{{i=1}}^{{N}}\\left[y_i\\log(\\hat{{y}}_i) - \\hat{{y}}_i\\right]
\\label{{eq:poisson}}
\\end{{equation}}

where $y_i$ is the true count and $\\hat{{y}}_i$ is the predicted count.

\\subsection{{Training}}

Models were trained using Adam optimizer with learning rate $10^{{-4}}$ for 100 epochs. We used 80/10/10 train/validation/test splits at the sample level.

\\subsection{{Evaluation Metrics}}

Performance was measured using:
\\begin{{itemize}}
\\item Structural Similarity Index (SSIM)
\\item Pearson Correlation Coefficient (PCC)
\\item Mean Absolute Error (MAE)
\\end{{itemize}}
```

### Important Notes
- **Reproducibility**: Include enough detail for replication
- **Justification**: Briefly explain key design choices
- **Standard practices**: Reference established methods when appropriate
- **No results**: Save performance numbers for Results section

Now generate the Methods section based on the provided implementation details.
"""

DISCUSSION_PROMPT = """You are writing the Discussion section of a scientific manuscript.

## Context

Synthesize your experimental results with literature findings to provide insights and identify future directions.

## Your Results

{results_summary}

## Literature Syntheses

{domain_syntheses}

## Requirements

### Content Structure
1. **Summary of findings**: Restate key results in context
2. **Cross-field insights**: Connect your work to broader literature
3. **Mechanistic interpretation**: Explain WHY your approach works
4. **Transfer learning opportunities**: What can be applied to other domains
5. **Limitations**: Honest assessment of constraints
6. **Future directions**: Specific next steps

### Cross-Field Integration
- **Identify parallels**: "Similar to spike train modeling (PMID: 18563015), sparse gene expression benefits from Poisson assumptions"
- **Transfer methods**: "Negative binomial approaches that improved neural modeling by 30\\% (PMID: 25678901) could address overdispersion in our spatial data"
- **Explain transferability**: Why similar data structures enable method transfer

### LaTeX Formatting
- Non-breaking spaces: `Figure~\\ref{{fig:results}}`
- Citations to literature: Use natural language + PMID when available
- Professional tone: Balanced, not overclaiming

### Example Output

```latex
\\section{{Discussion}}

Our results demonstrate that Poisson loss substantially improves spatial gene expression prediction from histology, achieving 213\\% SSIM improvement over MSE loss (Table~\\ref{{tab:results}}). This finding aligns with established principles from spike train modeling, where Poisson assumptions better capture sparse binary events (Pillow et al., 2008, PMID: 18563015).

\\subsection{{Why Poisson Loss Works for Sparse Data}}

The success of Poisson loss stems from its natural handling of count data statistics. Unlike MSE, which treats all prediction errors equally, Poisson loss accounts for the variance-mean relationship in count data. At 2μm resolution, 90\\% of genes show zero expression in most spots—a sparsity pattern nearly identical to neural spike trains (Pillow et al., 2008).

\\subsection{{Cross-Field Transfer Opportunities}}

Our findings suggest broader applicability beyond spatial transcriptomics:

\\textbf{{Single-cell RNA-seq}}: Similar sparsity patterns (70-90\\% zeros) suggest Poisson-based decoders could improve imputation methods.

\\textbf{{Digital pathology}}: Rare cell detection shares statistical structure with sparse gene detection. Methods from this work could enhance cell counting algorithms.

\\subsection{{Limitations and Future Work}}

While Poisson loss addresses sparsity, it assumes variance equals the mean—an assumption that may fail for overdispersed genes. Literature on spike train modeling shows negative binomial models improve performance by 15-30\\% when overdispersion is present (Gao et al., 2015, PMID: 25678901). Future work should evaluate NB2 loss for spatial transcriptomics.

Additionally, our evaluation used Visium HD data at 2μm resolution. Transferability to other spatial platforms (e.g., MERFISH, CosMx) requires validation.
```

### Important Notes
- **Balance**: Acknowledge limitations while highlighting contributions
- **Specificity**: Use exact statistics and citations
- **Forward-looking**: Identify concrete next steps
- **Cross-domain**: Actively connect to other fields

Now generate the Discussion section based on your results and literature syntheses.
"""

INTRODUCTION_PROMPT = """You are writing the Introduction section of a scientific manuscript.

## Context

Motivate the research problem and clearly state your contribution.

## Background

{domain_context}

## Your Contribution

{contribution_summary}

## Requirements

### Content Structure
1. **Problem motivation** (1 paragraph): Why is this problem important?
2. **Current limitations** (1 paragraph): What are existing approaches missing?
3. **Your solution** (1 paragraph): What do you propose and why it's novel?
4. **Key results preview** (1 paragraph): High-level summary of main finding
5. **Paper organization** (optional): Roadmap of sections

### LaTeX Formatting
- Non-breaking spaces before citations
- Professional academic tone
- Logical flow from general to specific

### Example Output

```latex
\\section{{Introduction}}

Spatial transcriptomics technologies enable measurement of gene expression with spatial context, revolutionizing our understanding of tissue architecture and cellular interactions. However, current platforms face a fundamental trade-off: high spatial resolution (e.g., 2μm) produces extremely sparse gene expression data, while lower resolution (10-100μm) averages signal across multiple cells, obscuring spatial heterogeneity.

Computational prediction of gene expression from histology images offers a promising solution, potentially enabling high-resolution spatial maps without sparsity constraints. Existing deep learning approaches use mean squared error (MSE) loss, treating gene expression prediction as regression. However, this ignores the discrete, count-based nature of RNA molecules and the extreme sparsity at subcellular resolution (90\\%+ zeros).

We hypothesize that Poisson loss, designed for count data modeling, will better handle sparsity than MSE loss. This hypothesis draws inspiration from spike train modeling in neuroscience, where Poisson assumptions improved sparse binary event prediction by 15-30\\% (Pillow et al., 2008; Gao et al., 2015).

Our experiments on Visium HD colorectal cancer data demonstrate that Poisson loss achieves 213\\% SSIM improvement over MSE loss (0.605 vs 0.193), with particularly strong gains for sparse genes. These findings suggest a generalizable principle: statistical models should match data structure, and cross-field transfer from neuroscience provides actionable insights for spatial biology.

The remainder of this paper describes our methods (Section 2), experimental results (Section 3), and broader implications for spatial biology and transfer learning (Section 4).
```

### Important Notes
- **Motivation first**: Start with why the problem matters
- **Clear contribution**: Explicitly state what's new
- **Accessible**: Readable by researchers outside narrow specialty
- **Forward references**: Point to later sections naturally

Now generate the Introduction section based on the provided context.
"""


def format_data_for_results_prompt(main_finding: dict) -> str:
    """
    Format experimental data for Results section prompt.

    Args:
        main_finding: Dictionary with key_findings, tables, figures

    Returns:
        Formatted string for prompt
    """
    formatted = []

    # Key findings
    if "key_findings" in main_finding:
        formatted.append("### Key Findings")
        for finding in main_finding["key_findings"]:
            claim = finding.get("claim", "")
            evidence = finding.get("evidence", "")
            value = finding.get("value")
            formatted.append(f"- {claim}")
            if evidence:
                formatted.append(f"  Evidence: {evidence}")
            if value is not None:
                formatted.append(f"  Value: {value}")
        formatted.append("")

    # Tables
    if "tables" in main_finding:
        formatted.append("### Available Tables")
        for table in main_finding["tables"]:
            formatted.append(f"- {table.get('name', 'Table')}: {table.get('path', '')}")
        formatted.append("")

    # Figures
    if "figures" in main_finding:
        formatted.append("### Available Figures")
        for figure in main_finding["figures"]:
            formatted.append(f"- {figure.get('name', 'Figure')}: {figure.get('path', '')}")
        formatted.append("")

    return "\n".join(formatted)


def format_domain_syntheses_for_discussion(domain_syntheses: list) -> str:
    """
    Format domain syntheses for Discussion section prompt.

    Args:
        domain_syntheses: List of domain synthesis records from database

    Returns:
        Formatted string for prompt
    """
    formatted = []

    for synthesis in domain_syntheses:
        domain_name = synthesis.get("name", "Unknown")
        summary = synthesis.get("summary_markdown", "")

        formatted.append(f"### {domain_name}")
        formatted.append(summary)
        formatted.append("")

    return "\n".join(formatted)


# Example usage comments for future Claude API integration
"""
# Future integration with Claude Opus 4.5

from anthropic import Anthropic

def generate_results_section(main_finding: dict, api_key: str) -> str:
    '''
    Generate Results section using Claude Opus 4.5 API.

    Args:
        main_finding: Experimental data dictionary
        api_key: Anthropic API key

    Returns:
        Generated LaTeX Results section
    '''
    client = Anthropic(api_key=api_key)

    # Format data for prompt
    data_summary = format_data_for_results_prompt(main_finding)

    # Generate prompt
    prompt = RESULTS_PROMPT.format(data_summary=data_summary)

    # Call Claude Opus 4.5
    response = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.content[0].text


def generate_discussion_section(
    results_summary: str,
    domain_syntheses: list,
    api_key: str
) -> str:
    '''
    Generate Discussion section using Claude Opus 4.5 API.

    Args:
        results_summary: Summary of experimental results
        domain_syntheses: List of domain synthesis records
        api_key: Anthropic API key

    Returns:
        Generated LaTeX Discussion section
    '''
    client = Anthropic(api_key=api_key)

    # Format domain syntheses
    syntheses_text = format_domain_syntheses_for_discussion(domain_syntheses)

    # Generate prompt
    prompt = DISCUSSION_PROMPT.format(
        results_summary=results_summary,
        domain_syntheses=syntheses_text
    )

    # Call Claude Opus 4.5
    response = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.content[0].text
"""
