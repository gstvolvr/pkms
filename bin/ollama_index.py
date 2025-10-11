#!/usr/bin/env python3
import os
import sys
import json
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
from tqdm import tqdm
import util

# Constants
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDINGS_MODEL = "nomic-embed-text"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDINGS_FILE = os.path.join(util.BASE_PATH, "embeddings.json")

def get_embedding(text: str) -> List[float]:
    """Get embedding for a text using Ollama's embedding endpoint."""
    url = f"{OLLAMA_BASE_URL}/api/embeddings"
    data = {
        "model": EMBEDDINGS_MODEL,
        "prompt": text
    }

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()["embedding"]
    except requests.exceptions.RequestException as e:
        print(f"Error getting embedding: {e}")
        return []

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks more efficiently."""
    # Handle small texts
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        # Determine the end of this chunk
        end = min(start + chunk_size, text_len)

        # Only look for break points if we're not at the end of the text
        if end < text_len:
            # Find the last newline or period in the chunk
            # We'll only check a small window at the end of the chunk to improve performance
            check_from = max(start + (chunk_size // 2), start)  # Only check in the second half
            chunk_to_check = text[check_from:end]

            # Look for newline first (higher priority)
            newline_pos = chunk_to_check.rfind('\n')
            if newline_pos != -1:
                end = check_from + newline_pos + 1  # +1 to include the newline
            else:
                # Look for period followed by space
                period_pos = chunk_to_check.rfind('. ')
                if period_pos != -1:
                    end = check_from + period_pos + 2  # +2 to include the period and space

        # Add the chunk
        chunks.append(text[start:end])

        # Move to the next chunk with overlap
        start = end - chunk_overlap

    return chunks

def process_file(file_path: str):
    """Process a single file and yield chunks with embeddings one at a time."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip empty files
        if not content.strip():
            return

        # Get relative path from the vault base
        rel_path = os.path.relpath(file_path, util.BASE_PATH)

        # Chunk the content
        chunks = chunk_text(content)

        for i, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            if embedding:
                yield {
                    "file_path": rel_path,
                    "chunk_index": i,
                    "content": chunk,
                    "embedding": embedding
                }
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return

def initialize_embeddings_file():
    """Initialize the embeddings file with an opening bracket."""
    with open(EMBEDDINGS_FILE, 'w', encoding='utf-8') as f:
        f.write("[\n")

def append_chunk_to_file(chunk: Dict[str, Any], is_first: bool = False):
    """Append a chunk to the embeddings file."""
    with open(EMBEDDINGS_FILE, 'a', encoding='utf-8') as f:
        if not is_first:
            f.write(",\n")
        json.dump(chunk, f, ensure_ascii=False, indent=2)

def finalize_embeddings_file():
    """Finalize the embeddings file with a closing bracket."""
    with open(EMBEDDINGS_FILE, 'a', encoding='utf-8') as f:
        f.write("\n]")

def main():
    parser = argparse.ArgumentParser(description="Index Obsidian vault for RAG with Ollama")
    parser.add_argument("--path", default=util.BASE_PATH, help="Path to the Obsidian vault")
    args = parser.parse_args()

    # Check if Ollama is running
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if response.status_code != 200:
            print(f"Error connecting to Ollama: {response.status_code}")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Ollama. Make sure it's running on localhost:11434")
        sys.exit(1)

    # Get all markdown files
    print(f"Finding all markdown files in {args.path}...")
    md_files = util.find_all_files(args.path)
    print(f"Found {len(md_files)} markdown files")

    # Initialize the embeddings file
    initialize_embeddings_file()

    # Process files and generate embeddings
    total_chunks = 0
    is_first_chunk = True

    for file_path in tqdm(md_files, desc="Processing files"):
        for chunk in process_file(file_path):
            append_chunk_to_file(chunk, is_first_chunk)
            if is_first_chunk:
                is_first_chunk = False
            total_chunks += 1

    # Finalize the embeddings file
    finalize_embeddings_file()

    print(f"Generated and saved embeddings for {total_chunks} chunks to {EMBEDDINGS_FILE}")

if __name__ == "__main__":
    main()
