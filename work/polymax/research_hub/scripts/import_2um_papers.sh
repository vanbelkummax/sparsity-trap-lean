#!/bin/bash
# Import key papers for 2um sparsity trap hypotheses

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANAGE_PAPERS="$SCRIPT_DIR/manage_papers.py"

echo "Importing key papers for 2um sparsity trap research..."
echo ""

# TICON - Highest priority (H_007)
echo "Adding TICON paper (arXiv:2512.21331)..."
python3 "$MANAGE_PAPERS" add-arxiv "2512.21331" \
  --title "TICON: Transformer-based Tile Contextualizer" \
  --notes "Highest priority for H_20241224_007. Tile-level contextualization for WSI. SoTA on HEST-Bench spatial transcriptomics."

# NegBio-VAE (H_005)
echo "Adding NegBio-VAE paper (arXiv:2508.05423)..."
python3 "$MANAGE_PAPERS" add-arxiv "2508.05423" \
  --title "Negative Binomial Variational Autoencoders" \
  --notes "For H_20241224_005. NB2 loss for overdispersed spike trains. Cross-field transfer: neuroscience -> spatial transcriptomics."

# Img2ST-Net baseline
echo "Adding Img2ST-Net baseline (PMID:41210922)..."
python3 "$MANAGE_PAPERS" add-pubmed "41210922" \
  --title "Img2ST-Net: predicting spatial transcriptomics from histology with deep learning" \
  --notes "Baseline for 2um work. Huo et al. Shows 2um challenge."

# Physics-Informed Neural Networks (H_008, H_009)
echo "Adding PINN paper..."
python3 "$MANAGE_PAPERS" add-custom \
  "https://www.mdpi.com/2076-3417/14/8/3204/pdf" \
  "Physics-Informed Neural Networks for High-Frequency Problems" \
  --source "mdpi" \
  --notes "For H_20241224_008 and H_20241224_009. Conservation and spatial constraints. 2 orders of magnitude improvement."

# Adaptive PINNs (H_009)
echo "Adding Adaptive PINNs paper..."
python3 "$MANAGE_PAPERS" add-custom \
  "https://arxiv.org/pdf/2503.18181.pdf" \
  "Adaptive Physics-informed Neural Networks" \
  --source "arxiv" \
  --notes "For H_20241224_009. Adaptive spatial sampling for under-sampled regions."

# PINN regularization (H_008)
echo "Adding PINN regularization paper..."
python3 "$MANAGE_PAPERS" add-custom \
  "https://amostech.com/TechnicalPapers/2024/Machine-Learning-for-SDA/Badura.pdf" \
  "Regularizing Training of PINNs" \
  --source "amostech" \
  --notes "For H_20241224_008. Spatial regularization improves PINN training."

echo ""
echo "✓ Paper import complete!"
echo ""
echo "To view imported papers:"
echo "  python3 $MANAGE_PAPERS list"
echo ""
echo "To link papers to hypotheses:"
echo "  python3 $MANAGE_PAPERS link <paper_id> H_20241224_007"
