import os
import sys
import json
import click
import requests
import numpy as np
from tqdm import tqdm
from pkms.core.config import get_config
from pkms.core.utils import find_all_files

OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDINGS_MODEL = "nomic-embed-text"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

@click.group('rag')
def rag():
    """Commands for the RAG system."""
    pass

def get_embedding(text: str) -> list[float]:
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

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks more efficiently."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            check_from = max(start + (chunk_size // 2), start)
            chunk_to_check = text[check_from:end]
            newline_pos = chunk_to_check.rfind('\n')
            if newline_pos != -1:
                end = check_from + newline_pos + 1
            else:
                period_pos = chunk_to_check.rfind('. ')
                if period_pos != -1:
                    end = check_from + period_pos + 2
        chunks.append(text[start:end])
        start = end - chunk_overlap

    return chunks

@rag.command('index')
def index():
    """Index the vault for RAG."""
    config = get_config()
    embeddings_file = config.embeddings_file
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if response.status_code != 200:
            click.echo(f"Error connecting to Ollama: {response.status_code}", err=True)
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        click.echo("Error: Could not connect to Ollama. Make sure it's running on localhost:11434", err=True)
        sys.exit(1)

    md_files = find_all_files(str(config.vault_path))
    click.echo(f"Found {len(md_files)} markdown files")

    with open(embeddings_file, 'w', encoding='utf-8') as f:
        f.write("[")

    total_chunks = 0
    is_first_chunk = True

    for file_path in tqdm(md_files, desc="Processing files"):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if not content.strip():
            continue
        rel_path = os.path.relpath(file_path, str(config.vault_path))
        chunks = chunk_text(content)
        for i, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            if embedding:
                if not is_first_chunk:
                    with open(embeddings_file, 'a', encoding='utf-8') as f:
                        f.write(",")
                with open(embeddings_file, 'a', encoding='utf-8') as f:
                    json.dump({
                        "file_path": rel_path,
                        "chunk_index": i,
                        "content": chunk,
                        "embedding": embedding
                    }, f, ensure_ascii=False, indent=2)
                if is_first_chunk:
                    is_first_chunk = False
                total_chunks += 1

    with open(embeddings_file, 'a', encoding='utf-8') as f:
        f.write("]")

    click.echo(f"Generated and saved embeddings for {total_chunks} chunks to {embeddings_file}")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0
    return np.dot(a, b) / (a_norm * b_norm)

@rag.command('query')
@click.option('--query', required=True, help='Query to run')
@click.option('--model', default='llama3', help='Ollama model to use')
@click.option('--system', help='System prompt to use')
def query(query, model, system):
    """Query the vault using Ollama RAG."""
    config = get_config()
    embeddings_file = config.embeddings_file
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if response.status_code != 200:
            click.echo(f"Error connecting to Ollama: {response.status_code}", err=True)
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        click.echo("Error: Could not connect to Ollama. Make sure it's running on localhost:11434", err=True)
        sys.exit(1)

    try:
        with open(embeddings_file, 'r', encoding='utf-8') as f:
            embeddings = json.load(f)
    except FileNotFoundError:
        click.echo(f"Error: Embeddings file not found at {embeddings_file}", err=True)
        click.echo("Please run 'pkms rag index' first to generate embeddings.", err=True)
        sys.exit(1)
    except json.JSONDecodeError:
        click.echo(f"Error: Invalid JSON in embeddings file {embeddings_file}", err=True)
        sys.exit(1)

    system_prompt = system or "You are a helpful assistant that answers questions based on the provided context from my personal knowledge base. If the answer cannot be found in the context, say so clearly."

    query_embedding = get_embedding(query)
    for chunk in embeddings:
        chunk["similarity"] = cosine_similarity(query_embedding, chunk["embedding"])
    sorted_chunks = sorted(embeddings, key=lambda x: x["similarity"], reverse=True)
    relevant_chunks = sorted_chunks[:5]

    context = "Here is relevant information from my knowledge base:\n\n"
    for i, chunk in enumerate(relevant_chunks):
        context += f"--- Document {i+1}: {chunk['file_path']} ---
"
        context += chunk["content"]
        context += "\n\n"

    prompt = f"{context}\n\nQuestion: {query}\n\nAnswer:"

    url = f"{OLLAMA_BASE_URL}/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    if system_prompt:
        data["system"] = system_prompt

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        click.echo(response.json()["response"])
    except requests.exceptions.RequestException as e:
        click.echo(f"Error querying Ollama: {e}", err=True)
        sys.exit(1)
