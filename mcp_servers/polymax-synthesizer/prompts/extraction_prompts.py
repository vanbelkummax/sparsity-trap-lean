"""
Extraction prompt templates for Claude API integration.

These prompts guide Claude in performing hierarchical extraction of paper content.
The extraction follows a four-level hierarchy:

1. HIGH_LEVEL: Main claims, novelty, contribution (conceptual understanding)
2. MID_LEVEL: Statistics, methods, parameters (quantitative details)
3. LOW_LEVEL: Direct quotes with context (verbatim evidence)
4. CODE_METHODS: Algorithms, equations, hyperparameters (implementation details)

Usage:
    These are templates for future Claude API integration. The MVP implementation
    uses rule-based extraction (see paper_extractor.py). Future versions will
    use these prompts with Claude API for semantic understanding.

Example Input:
    {
        "title": "ZINB Loss for Zero-Inflated Spatial Transcriptomics",
        "abstract": "We propose a ZINB loss that achieves SSIM of 0.70...",
        "full_text": "# Introduction\\n...",
        "year": 2024,
        "journal": "Nature Methods"
    }

Example Output:
    {
        "high_level": {...},
        "mid_level": {...},
        "low_level": {...},
        "code_methods": {...}
    }
"""

HIGH_LEVEL_PROMPT = """You are a scientific literature analyst. Extract the high-level conceptual content from this paper.

Paper Information:
Title: {title}
Authors: {authors}
Year: {year}
Journal: {journal}

Abstract:
{abstract}

Extract the following:

1. **Main Claim**: The central thesis or finding of the paper (1-2 sentences)
   - What is the primary contribution?
   - What problem does it solve?

2. **Novelty**: What makes this work unique or different? (1-2 sentences)
   - First application of X to Y?
   - Novel method or approach?
   - Unexpected finding?

3. **Contribution**: How does this advance the field? (1-2 sentences)
   - What gap does it fill?
   - What new capability does it enable?
   - What future work does it enable?

Return a JSON object with these three fields:
{{
    "main_claim": "...",
    "novelty": "...",
    "contribution": "..."
}}

Be concise and precise. Focus on what the paper CLAIMS, not whether those claims are valid.
"""

MID_LEVEL_PROMPT = """You are a scientific literature analyst. Extract quantitative statistics and methodological details from this paper.

Paper Information:
Title: {title}

Abstract:
{abstract}

Full Text:
{full_text}

Extract the following:

1. **Statistics**: Performance metrics, experimental results, comparisons
   For each statistic, provide:
   - type: "performance_metric" | "comparison" | "p_value" | "effect_size"
   - metric: Name of the metric (e.g., "SSIM", "accuracy", "AUC")
   - value: Numeric value (extract as number if possible)
   - context: Brief context (e.g., "on Visium HD dataset")
   - page: Page number or section (e.g., "Results", page 5)
   - comparison: Optional comparison (e.g., "vs 0.54 for baseline")

2. **Methods**: Technical approaches, algorithms, models used
   For each method, provide:
   - name: Method/algorithm name (e.g., "U-Net", "ZINB loss")
   - parameters: Key parameters or hyperparameters (dict)
   - page: Where it's introduced/described
   - description: Brief 1-sentence description

Return a JSON object:
{{
    "stats": [
        {{
            "type": "performance_metric",
            "metric": "SSIM",
            "value": 0.70,
            "context": "ZINB on Visium HD validation set",
            "page": 5,
            "comparison": "vs 0.54 for Poisson"
        }},
        ...
    ],
    "methods": [
        {{
            "name": "ZINB loss",
            "parameters": {{"pi": "zero-inflation rate", "theta": "dispersion"}},
            "page": 3,
            "description": "Negative log-likelihood for zero-inflated negative binomial"
        }},
        ...
    ]
}}

Extract ALL reported statistics and methods. Be thorough and precise.
"""

LOW_LEVEL_PROMPT = """You are a scientific literature analyst. Extract verbatim quotes that capture key findings and claims.

Paper Information:
Title: {title}

Abstract:
{abstract}

Full Text:
{full_text}

Extract direct quotes that:
1. State key findings or results
2. Make strong claims about performance/novelty
3. Provide context for important decisions
4. Compare to prior work
5. Discuss limitations or future work

For each quote, provide:
- text: Exact verbatim quote (include surrounding context if needed)
- page: Page number or section name
- section: Section where it appears (e.g., "Results", "Discussion")
- context: Why this quote is important (1 sentence)

Return a JSON object:
{{
    "quotes": [
        {{
            "text": "ZINB achieves SSIM of 0.70 compared to 0.54 for Poisson (p<0.001), demonstrating superior handling of zero-inflation.",
            "page": 5,
            "section": "Results",
            "context": "Primary quantitative finding comparing loss functions"
        }},
        ...
    ]
}}

Select 5-15 quotes that best capture the paper's key claims and evidence.
Use exact wording from the paper - do not paraphrase.
"""

CODE_METHODS_PROMPT = """You are a scientific literature analyst specializing in computational methods. Extract algorithms, equations, and implementation details.

Paper Information:
Title: {title}

Full Text:
{full_text}

Extract the following:

1. **Algorithms**: Pseudocode, procedural descriptions, training procedures
   For each algorithm, provide:
   - name: Algorithm name
   - pseudocode: Simplified pseudocode representation
   - page: Where it's described
   - description: What it does (1 sentence)

2. **Equations**: Mathematical formulas (LaTeX format)
   For each equation, provide:
   - latex: LaTeX representation of the equation
   - description: What the equation represents
   - page: Where it appears
   - variables: Dict mapping variable names to descriptions

3. **Hyperparameters**: Training details, model configurations
   For each hyperparameter set, provide:
   - context: What experiment/model (e.g., "U-Net training")
   - parameters: Dict of parameter names and values
   - page: Where reported

Return a JSON object:
{{
    "algorithms": [
        {{
            "name": "ZINB NLL computation",
            "pseudocode": "def zinb_nll(y, mu, theta, pi):\\n    zero_prob = pi + (1-pi) * nb_pmf(0, mu, theta)\\n    nonzero_prob = (1-pi) * nb_pmf(y, mu, theta)\\n    return -log(zero_prob if y==0 else nonzero_prob)",
            "page": 12,
            "description": "Computes negative log-likelihood for ZINB distribution"
        }},
        ...
    ],
    "equations": [
        {{
            "latex": "\\\\mathcal{{L}} = -\\\\log(\\\\pi \\\\cdot \\\\delta_{{y,0}} + (1-\\\\pi) \\\\cdot NB(y; \\\\mu, \\\\theta))",
            "description": "ZINB likelihood function",
            "page": 3,
            "variables": {{
                "pi": "zero-inflation probability",
                "mu": "mean of negative binomial",
                "theta": "dispersion parameter"
            }}
        }},
        ...
    ],
    "hyperparameters": [
        {{
            "context": "U-Net encoder training",
            "parameters": {{
                "learning_rate": 1e-4,
                "batch_size": 16,
                "epochs": 100,
                "optimizer": "Adam"
            }},
            "page": 8
        }},
        ...
    ]
}}

Focus on extractable, reusable technical details. Convert math to LaTeX format.
"""


def format_extraction_prompt(level: str, paper_data: dict) -> str:
    """
    Format an extraction prompt for a given level.

    Args:
        level: One of ["high_level", "mid_level", "low_level", "code_methods"]
        paper_data: Dictionary containing:
            - title: str
            - abstract: str
            - full_text: str (optional)
            - authors: str (optional)
            - year: int (optional)
            - journal: str (optional)

    Returns:
        Formatted prompt string ready for Claude API

    Example:
        >>> paper = {
        ...     "title": "ZINB Loss for Spatial Transcriptomics",
        ...     "abstract": "We propose...",
        ...     "authors": "Smith et al.",
        ...     "year": 2024,
        ...     "journal": "Nature Methods"
        ... }
        >>> prompt = format_extraction_prompt("high_level", paper)
        >>> # Send prompt to Claude API
    """
    prompts = {
        "high_level": HIGH_LEVEL_PROMPT,
        "mid_level": MID_LEVEL_PROMPT,
        "low_level": LOW_LEVEL_PROMPT,
        "code_methods": CODE_METHODS_PROMPT
    }

    if level not in prompts:
        raise ValueError(f"Invalid level: {level}. Must be one of {list(prompts.keys())}")

    # Provide defaults for missing fields
    formatted_data = {
        "title": paper_data.get("title", "Unknown"),
        "abstract": paper_data.get("abstract", "No abstract available"),
        "full_text": paper_data.get("full_text", ""),
        "authors": paper_data.get("authors", "Unknown"),
        "year": paper_data.get("year", "Unknown"),
        "journal": paper_data.get("journal", "Unknown")
    }

    return prompts[level].format(**formatted_data)


# Example usage documentation
EXTRACTION_WORKFLOW = """
Future Claude API Integration Workflow
=======================================

1. For each paper in batch:
   a. Load paper data from database (title, abstract, full_text)
   b. Format prompts for each extraction level
   c. Send to Claude API in sequence or parallel
   d. Parse JSON responses
   e. Store in paper_extractions table

2. Parallel Processing Strategy:
   - Process 5-10 papers concurrently using async/await
   - Within each paper, can parallelize high/mid/low levels
   - CODE_METHODS depends on full_text availability

3. Error Handling:
   - Retry failed extractions (network errors)
   - Log malformed JSON responses
   - Fall back to rule-based extraction if API fails

4. Cost Optimization:
   - Cache extractions (don't re-extract same paper)
   - Use extraction_depth to skip levels ("high_only", "mid", "full")
   - Batch API calls when possible

Example Code:
    from prompts.extraction_prompts import format_extraction_prompt
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Format prompt
    prompt = format_extraction_prompt("high_level", paper_data)

    # Call Claude API
    response = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse response
    extraction = json.loads(response.content[0].text)
"""
