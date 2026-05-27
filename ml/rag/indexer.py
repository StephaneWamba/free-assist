"""
FreeAssist — Knowledge Base Indexer CLI

Usage:
    python indexer.py \
        --kb_dir ../../data/knowledge_base \
        --index_dir ../../data/faiss_index
"""

import argparse
from pathlib import Path

from pipeline import build_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build FAISS index from knowledge base")
    parser.add_argument("--kb_dir", default="../../data/knowledge_base")
    parser.add_argument("--index_dir", default="../../data/faiss_index")
    args = parser.parse_args()

    build_index(
        knowledge_base_dir=Path(args.kb_dir),
        index_dir=Path(args.index_dir),
    )
    print("Index built successfully.")


if __name__ == "__main__":
    main()
