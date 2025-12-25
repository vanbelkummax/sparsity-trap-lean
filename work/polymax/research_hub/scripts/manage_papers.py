#!/usr/bin/env python3
"""
Paper Management System for Research Hub

Automates downloading, organizing, and tracking papers from various sources.
Supports ArXiv, PubMed, bioRxiv, and direct URLs.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import hashlib
import yaml


class PaperManager:
    """Manages paper downloads, metadata, and organization."""

    def __init__(self, base_dir: str = "/home/user/work/polymax/research_hub/papers"):
        self.base_dir = Path(base_dir)
        self.pdfs_dir = self.base_dir / "pdfs"
        self.metadata_dir = self.base_dir / "metadata"
        self.notes_dir = self.base_dir / "notes"

        # Create directories if they don't exist
        for dir_path in [self.pdfs_dir, self.metadata_dir, self.notes_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _generate_paper_id(self, source: str, identifier: str) -> str:
        """Generate a unique paper ID from source and identifier."""
        # Create hash from source + identifier for filesystem-safe ID
        hash_input = f"{source}:{identifier}"
        hash_digest = hashlib.md5(hash_input.encode()).hexdigest()[:8]

        # Create readable ID
        if source == "arxiv":
            # ArXiv IDs are already good: 2512.21331
            clean_id = identifier.replace(".", "_").replace("v", "_v")
            return f"arxiv_{clean_id}"
        elif source == "pubmed":
            return f"pmid_{identifier}"
        elif source == "biorxiv":
            return f"biorxiv_{hash_digest}"
        else:
            return f"paper_{hash_digest}"

    def _download_pdf(self, url: str, output_path: Path) -> bool:
        """Download PDF from URL using curl."""
        try:
            cmd = [
                "curl",
                "-L",  # Follow redirects
                "-o", str(output_path),
                url,
                "--silent",
                "--show-error"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and output_path.exists():
                # Check if file is actually a PDF (first few bytes)
                with open(output_path, 'rb') as f:
                    header = f.read(4)
                    if header == b'%PDF':
                        return True
                    else:
                        print(f"Downloaded file is not a PDF: {output_path}")
                        output_path.unlink()  # Remove non-PDF file
                        return False
            else:
                print(f"Download failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error downloading PDF: {e}")
            return False

    def add_arxiv_paper(self, arxiv_id: str, title: str = None,
                       authors: List[str] = None, notes: str = None) -> Dict:
        """Add a paper from ArXiv."""
        # Clean ArXiv ID (remove 'arXiv:' prefix if present)
        clean_id = arxiv_id.replace("arXiv:", "").strip()

        # Generate paper ID
        paper_id = self._generate_paper_id("arxiv", clean_id)

        # Download PDF from ArXiv
        pdf_url = f"https://arxiv.org/pdf/{clean_id}.pdf"
        pdf_path = self.pdfs_dir / f"{paper_id}.pdf"

        print(f"Downloading ArXiv paper {clean_id}...")
        success = self._download_pdf(pdf_url, pdf_path)

        # Create metadata
        metadata = {
            "paper_id": paper_id,
            "source": "arxiv",
            "arxiv_id": clean_id,
            "title": title or f"ArXiv {clean_id}",
            "authors": authors or [],
            "url": f"https://arxiv.org/abs/{clean_id}",
            "pdf_url": pdf_url,
            "pdf_path": str(pdf_path) if success else None,
            "added_date": datetime.now().isoformat(),
            "notes": notes or ""
        }

        # Save metadata
        metadata_path = self.metadata_dir / f"{paper_id}.yaml"
        with open(metadata_path, 'w') as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

        print(f"{'✓' if success else '✗'} Paper {paper_id} {'added' if success else 'metadata saved (PDF download failed)'}")
        return metadata

    def add_pubmed_paper(self, pmid: str, title: str = None,
                        authors: List[str] = None, notes: str = None,
                        pdf_url: str = None) -> Dict:
        """Add a paper from PubMed."""
        paper_id = self._generate_paper_id("pubmed", pmid)

        # Download PDF if URL provided
        pdf_path = self.pdfs_dir / f"{paper_id}.pdf"
        success = False
        if pdf_url:
            print(f"Downloading PubMed paper {pmid}...")
            success = self._download_pdf(pdf_url, pdf_path)

        # Create metadata
        metadata = {
            "paper_id": paper_id,
            "source": "pubmed",
            "pmid": pmid,
            "title": title or f"PMID {pmid}",
            "authors": authors or [],
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "pdf_url": pdf_url,
            "pdf_path": str(pdf_path) if success else None,
            "added_date": datetime.now().isoformat(),
            "notes": notes or ""
        }

        # Save metadata
        metadata_path = self.metadata_dir / f"{paper_id}.yaml"
        with open(metadata_path, 'w') as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

        print(f"✓ Paper {paper_id} added")
        return metadata

    def add_custom_paper(self, url: str, title: str, source: str = "custom",
                        authors: List[str] = None, notes: str = None) -> Dict:
        """Add a paper from a custom URL."""
        paper_id = self._generate_paper_id(source, url)

        # Try to download PDF
        pdf_path = self.pdfs_dir / f"{paper_id}.pdf"
        print(f"Downloading paper from {url}...")
        success = self._download_pdf(url, pdf_path)

        # Create metadata
        metadata = {
            "paper_id": paper_id,
            "source": source,
            "title": title,
            "authors": authors or [],
            "url": url,
            "pdf_url": url,
            "pdf_path": str(pdf_path) if success else None,
            "added_date": datetime.now().isoformat(),
            "notes": notes or ""
        }

        # Save metadata
        metadata_path = self.metadata_dir / f"{paper_id}.yaml"
        with open(metadata_path, 'w') as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

        print(f"{'✓' if success else '✗'} Paper {paper_id} {'added' if success else 'metadata saved'}")
        return metadata

    def list_papers(self, source: Optional[str] = None) -> List[Dict]:
        """List all papers, optionally filtered by source."""
        papers = []

        for metadata_file in self.metadata_dir.glob("*.yaml"):
            with open(metadata_file) as f:
                metadata = yaml.safe_load(f)
                if source is None or metadata.get("source") == source:
                    papers.append(metadata)

        return sorted(papers, key=lambda x: x.get("added_date", ""), reverse=True)

    def search_papers(self, query: str) -> List[Dict]:
        """Search papers by title or notes."""
        query_lower = query.lower()
        results = []

        for paper in self.list_papers():
            title = paper.get("title", "").lower()
            notes = paper.get("notes", "").lower()
            if query_lower in title or query_lower in notes:
                results.append(paper)

        return results

    def get_paper(self, paper_id: str) -> Optional[Dict]:
        """Get metadata for a specific paper."""
        metadata_path = self.metadata_dir / f"{paper_id}.yaml"
        if metadata_path.exists():
            with open(metadata_path) as f:
                return yaml.safe_load(f)
        return None

    def add_note(self, paper_id: str, note: str):
        """Add a note to a paper's metadata."""
        metadata = self.get_paper(paper_id)
        if metadata:
            metadata["notes"] = note
            metadata["updated_date"] = datetime.now().isoformat()

            metadata_path = self.metadata_dir / f"{paper_id}.yaml"
            with open(metadata_path, 'w') as f:
                yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)
            print(f"✓ Note added to {paper_id}")
        else:
            print(f"✗ Paper {paper_id} not found")

    def link_to_hypothesis(self, paper_id: str, hypothesis_id: str):
        """Link a paper to a hypothesis."""
        metadata = self.get_paper(paper_id)
        if metadata:
            if "linked_hypotheses" not in metadata:
                metadata["linked_hypotheses"] = []

            if hypothesis_id not in metadata["linked_hypotheses"]:
                metadata["linked_hypotheses"].append(hypothesis_id)
                metadata["updated_date"] = datetime.now().isoformat()

                metadata_path = self.metadata_dir / f"{paper_id}.yaml"
                with open(metadata_path, 'w') as f:
                    yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)
                print(f"✓ Linked {paper_id} to hypothesis {hypothesis_id}")
        else:
            print(f"✗ Paper {paper_id} not found")


def main():
    parser = argparse.ArgumentParser(
        description="Manage research papers in the research hub"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Add ArXiv paper
    arxiv_parser = subparsers.add_parser("add-arxiv", help="Add paper from ArXiv")
    arxiv_parser.add_argument("arxiv_id", help="ArXiv ID (e.g., 2512.21331)")
    arxiv_parser.add_argument("--title", help="Paper title")
    arxiv_parser.add_argument("--authors", nargs="+", help="Authors")
    arxiv_parser.add_argument("--notes", help="Notes about the paper")

    # Add PubMed paper
    pubmed_parser = subparsers.add_parser("add-pubmed", help="Add paper from PubMed")
    pubmed_parser.add_argument("pmid", help="PubMed ID")
    pubmed_parser.add_argument("--title", help="Paper title")
    pubmed_parser.add_argument("--authors", nargs="+", help="Authors")
    pubmed_parser.add_argument("--pdf-url", help="URL to PDF")
    pubmed_parser.add_argument("--notes", help="Notes about the paper")

    # Add custom paper
    custom_parser = subparsers.add_parser("add-custom", help="Add paper from URL")
    custom_parser.add_argument("url", help="URL to PDF")
    custom_parser.add_argument("title", help="Paper title")
    custom_parser.add_argument("--source", default="custom", help="Source name")
    custom_parser.add_argument("--authors", nargs="+", help="Authors")
    custom_parser.add_argument("--notes", help="Notes about the paper")

    # List papers
    list_parser = subparsers.add_parser("list", help="List all papers")
    list_parser.add_argument("--source", help="Filter by source (arxiv, pubmed, etc.)")

    # Search papers
    search_parser = subparsers.add_parser("search", help="Search papers")
    search_parser.add_argument("query", help="Search query")

    # Add note
    note_parser = subparsers.add_parser("add-note", help="Add note to paper")
    note_parser.add_argument("paper_id", help="Paper ID")
    note_parser.add_argument("note", help="Note text")

    # Link to hypothesis
    link_parser = subparsers.add_parser("link", help="Link paper to hypothesis")
    link_parser.add_argument("paper_id", help="Paper ID")
    link_parser.add_argument("hypothesis_id", help="Hypothesis ID (e.g., H_20241224_007)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    manager = PaperManager()

    if args.command == "add-arxiv":
        manager.add_arxiv_paper(
            args.arxiv_id,
            title=args.title,
            authors=args.authors,
            notes=args.notes
        )

    elif args.command == "add-pubmed":
        manager.add_pubmed_paper(
            args.pmid,
            title=args.title,
            authors=args.authors,
            pdf_url=args.pdf_url,
            notes=args.notes
        )

    elif args.command == "add-custom":
        manager.add_custom_paper(
            args.url,
            args.title,
            source=args.source,
            authors=args.authors,
            notes=args.notes
        )

    elif args.command == "list":
        papers = manager.list_papers(source=args.source)
        if papers:
            print(f"\n{'='*80}")
            print(f"Found {len(papers)} papers")
            print(f"{'='*80}\n")
            for paper in papers:
                pdf_status = "✓ PDF" if paper.get("pdf_path") else "✗ No PDF"
                print(f"{paper['paper_id']}: {paper['title']}")
                print(f"  Source: {paper['source']} | {pdf_status}")
                print(f"  URL: {paper['url']}")
                if paper.get("notes"):
                    print(f"  Notes: {paper['notes']}")
                print()
        else:
            print("No papers found")

    elif args.command == "search":
        results = manager.search_papers(args.query)
        if results:
            print(f"\nFound {len(results)} papers matching '{args.query}':\n")
            for paper in results:
                print(f"{paper['paper_id']}: {paper['title']}")
                print(f"  {paper['url']}\n")
        else:
            print(f"No papers found matching '{args.query}'")

    elif args.command == "add-note":
        manager.add_note(args.paper_id, args.note)

    elif args.command == "link":
        manager.link_to_hypothesis(args.paper_id, args.hypothesis_id)


if __name__ == "__main__":
    main()
