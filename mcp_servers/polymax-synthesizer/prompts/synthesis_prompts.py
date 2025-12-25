"""Prompts for domain synthesis using Claude Opus 4.5.

This module contains prompt templates for generating cross-domain syntheses
from hierarchical paper extractions.

Future Enhancement:
- Integrate Claude Opus 4.5 API for synthesis generation
- Replace rule-based domain_synthesizer with LLM-powered synthesis
"""

DOMAIN_SYNTHESIS_PROMPT = """You are a research synthesis expert tasked with creating a concise 1-page synthesis of papers from the {domain} domain.

You have been provided with hierarchical extractions from {num_papers} papers. Your goal is to synthesize key findings, statistical approaches, and identify cross-field transfer opportunities.

## Input Data

{paper_extractions}

## Task

Create a 1-page markdown synthesis with the following structure:

### Required Sections

1. **# {domain}: [Brief Descriptive Title]**
   - Create a clear, descriptive title for this domain's synthesis

2. **## Key Findings**
   - Synthesize 2-4 most important findings across papers
   - Include specific statistics with citations (PMID and page numbers)
   - Format: "Finding statement (Author et al., Year, PMID: XXXXX, p.Y)"
   - Example: "Neural spike trains exhibit 90-95% sparsity, similar to 2μm spatial transcriptomics (Pillow et al., 2008, PMID: 18563015, p.7)"

3. **## Statistical Approaches**
   - Identify 2-3 key statistical methods used across papers
   - For each method, provide:
     - Method name and brief description
     - Key parameters or assumptions
     - Quantitative performance metrics (with exact values, PMID, page numbers)
   - Example format:
     ```
     1. **Poisson GLM**: Standard for spike modeling
        - Assumption: Variance = mean
        - **Key stat**: 15% RMSE improvement over baseline (PMID: 12345678, p.7)
     ```

4. **## Cross-Field Transfer**
   - Identify similarities to other domains
   - Explain what is transferable (methods, insights, statistical approaches)
   - Predict expected impact/improvement if transferred
   - Example: "If NB2 improves spike modeling by 15-30%, similar gains expected for sparse gene expression"

5. **## Top Papers**
   - List 3-5 most influential papers with:
     - Full citation (Author et al., Year - Title)
     - PMID
     - One-sentence summary of contribution

## Important Guidelines

1. **Be specific**: Always include exact statistics, not vague statements
2. **Cite everything**: Every claim must have (PMID: XXXXX, p.Y)
3. **Focus on transfer**: Highlight what can be applied to other domains
4. **Keep it concise**: Target ~500-800 words total
5. **Use markdown formatting**: Headers, bold, lists, code blocks

## Example Output Structure

```markdown
# Neuroscience: Sparse Spike Train Modeling

## Key Findings

Neural spike trains exhibit 90-95% sparsity, similar to 2μm spatial transcriptomics (Pillow et al., 2008, PMID: 18563015, p.7). This sparsity creates unique statistical challenges for modeling zero-inflated count data.

Overdispersion (variance >> mean) is prevalent in neural recordings, requiring models beyond simple Poisson assumptions (Gao et al., 2015, PMID: 25678901, p.12).

## Statistical Approaches

1. **Poisson GLM**: Standard baseline for spike modeling
   - Assumption: Variance = mean
   - Suitable for simple spike patterns
   - Limitation: Fails for overdispersed data
   - **Key stat**: 15% RMSE improvement over linear models (PMID: 18563015, p.7)

2. **Negative Binomial (NB2)**: Addresses overdispersion
   - Parameters: μ (mean), θ (dispersion)
   - Variance = μ + μ²/θ
   - **Key stat**: 15-30% RMSE improvement over Poisson (PMID: 25678901, p.12)

## Cross-Field Transfer

**Similarity**: Sparse binary events (spike/no-spike ≈ gene expressed/not expressed at 2μm resolution)

**Transferable**:
- Loss function design (Poisson vs NB2)
- Dispersion parameter estimation methods
- Zero-inflation handling strategies

**Expected Impact**: If NB2 improves spike modeling by 15-30%, similar gains expected for 2μm spatial transcriptomics where sparsity is 90%+.

## Top Papers

1. Pillow et al. (2008) - Spatio-temporal correlations and visual signalling in a complete neuronal population (PMID: 18563015)
   - First application of Poisson GLM to complete neural populations

2. Gao et al. (2015) - Linear dynamical neural population models through nonlinear embeddings (PMID: 25678901)
   - Introduced NB2 for overdispersed spike data, demonstrated 15-30% RMSE improvement
```

---

Now generate the synthesis for {domain} domain.
"""

CROSS_FIELD_INSIGHT_PROMPT = """Given these findings from {domain}:

{findings}

And these findings from {target_domain}:

{target_findings}

Identify potential cross-field transfer opportunities:

1. What similarities exist in the data structure or statistical properties?
2. What methods from {domain} could be applied to {target_domain}?
3. What quantitative improvements might we expect?
4. What are the key differences that might limit transferability?

Provide specific, actionable insights with references to exact statistics and methods.
"""

TRANSFER_LEARNING_PROMPT = """Analyze potential transfer learning opportunities between domains:

Source Domain: {source_domain}
Target Domain: {target_domain}

Source Domain Methods:
{source_methods}

Target Domain Challenges:
{target_challenges}

Generate:
1. Method matching: Which source methods address target challenges?
2. Adaptation requirements: What modifications are needed?
3. Expected performance: Quantitative predictions based on source domain results
4. Risk assessment: What could fail during transfer?

Format as structured JSON with clear reasoning.
"""

def format_paper_extractions_for_prompt(extractions: list) -> str:
    """
    Format paper extractions into a readable structure for the LLM prompt.

    Args:
        extractions: List of paper extraction dictionaries

    Returns:
        Formatted string representation of extractions
    """
    formatted = []

    for i, paper in enumerate(extractions, 1):
        formatted.append(f"### Paper {i}: {paper.get('title', 'Unknown')}")
        formatted.append(f"Year: {paper.get('year', 'N/A')} | PMID: {paper.get('pmid', 'N/A')}")
        formatted.append("")

        # High-level
        high = paper.get('high_level', {})
        if high:
            formatted.append("**High-Level Summary:**")
            formatted.append(f"- Main Claim: {high.get('main_claim', 'N/A')}")
            formatted.append(f"- Novelty: {high.get('novelty', 'N/A')}")
            formatted.append(f"- Contribution: {high.get('contribution', 'N/A')}")
            formatted.append("")

        # Mid-level stats
        mid = paper.get('mid_level', {})
        if mid and mid.get('stats'):
            formatted.append("**Key Statistics:**")
            for stat in mid['stats']:
                formatted.append(f"- {stat.get('metric', 'Unknown')}: {stat.get('value', 'N/A')} "
                               f"(page {stat.get('page', 'N/A')})")
            formatted.append("")

        # Mid-level methods
        if mid and mid.get('methods'):
            formatted.append("**Methods:**")
            for method in mid['methods']:
                params = method.get('parameters', {})
                param_str = ", ".join(f"{k}={v}" for k, v in params.items()) if params else "N/A"
                formatted.append(f"- {method.get('name', 'Unknown')}: {param_str}")
            formatted.append("")

        # Low-level quotes
        low = paper.get('low_level', {})
        if low and low.get('quotes'):
            formatted.append("**Key Quotes:**")
            for quote in low['quotes'][:3]:  # Limit to 3 quotes per paper
                formatted.append(f'- "{quote.get("text", "N/A")}" '
                               f'(page {quote.get("page", "N/A")})')
            formatted.append("")

        formatted.append("---")
        formatted.append("")

    return "\n".join(formatted)

# Example usage in comments for future implementation
"""
# Future integration with Claude Opus 4.5

from anthropic import Anthropic

def synthesize_with_claude(domain: str, extractions: list) -> str:
    '''
    Generate domain synthesis using Claude Opus 4.5 API.

    Args:
        domain: Domain name (e.g., "neuroscience")
        extractions: List of hierarchical paper extractions

    Returns:
        Generated 1-page markdown synthesis
    '''
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Format extractions for prompt
    formatted_extractions = format_paper_extractions_for_prompt(extractions)

    # Generate prompt
    prompt = DOMAIN_SYNTHESIS_PROMPT.format(
        domain=domain,
        num_papers=len(extractions),
        paper_extractions=formatted_extractions
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
