"""Search commands using Ollama RAG."""
import click
import json
import requests
import numpy as np
from pathlib import Path
from tqdm import tqdm
from typing import List, Dict, Any

from pkms.core import get_config, find_all_files

OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDINGS_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_CONTEXT_CHUNKS = 5


def get_embedding(text: str) -> List[float]:
    """Get embedding for a text using Ollama's embedding endpoint."""
    url = f"{OLLAMA_BASE_URL}/api/embeddings"
    data = {"model": EMBEDDINGS_MODEL, "prompt": text}

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()["embedding"]
    except requests.exceptions.RequestException as e:
        click.echo(f"Error getting embedding: {e}", err=True)
        return []


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
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


@click.group()
def search():
    """Search and query your vault using RAG."""
    pass


@search.command()
@click.option('--path', type=click.Path(exists=True), help='Path to vault (overrides config)')
def index(path):
    """Index vault for RAG search."""
    config = get_config()
    vault_path = Path(path) if path else config.vault_path
    embeddings_file = vault_path / 'embeddings.json'

    # Check Ollama
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if response.status_code != 200:
            click.echo(f"Error connecting to Ollama: {response.status_code}", err=True)
            return
    except requests.exceptions.ConnectionError:
        click.echo("Error: Could not connect to Ollama. Make sure it's running on localhost:11434", err=True)
        return

    # Get markdown files
    click.echo(f"Finding markdown files in {vault_path}...")
    md_files = find_all_files(str(vault_path))
    click.echo(f"Found {len(md_files)} files")

    # Initialize embeddings file
    with open(embeddings_file, 'w', encoding='utf-8') as f:
        f.write("[\n")

    total_chunks = 0
    is_first = True

    for file_path in tqdm(md_files, desc="Processing files"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                continue

            rel_path = str(Path(file_path).relative_to(vault_path))
            chunks = chunk_text(content)

            for i, chunk in enumerate(chunks):
                embedding = get_embedding(chunk)
                if embedding:
                    chunk_data = {
                        "file_path": rel_path,
                        "chunk_index": i,
                        "content": chunk,
                        "embedding": embedding
                    }
                    with open(embeddings_file, 'a', encoding='utf-8') as f:
                        if not is_first:
                            f.write(",\n")
                        json.dump(chunk_data, f, ensure_ascii=False, indent=2)
                    if is_first:
                        is_first = False
                    total_chunks += 1
        except Exception as e:
            click.echo(f"Error processing {file_path}: {e}", err=True)

    # Finalize
    with open(embeddings_file, 'a', encoding='utf-8') as f:
        f.write("\n]")

    click.echo(f"✓ Indexed {total_chunks} chunks to {embeddings_file}")


@search.command()
@click.argument('query', required=False)
@click.option('--model', default=LLM_MODEL, help='Ollama model to use')
@click.option('--system', help='Custom system prompt')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode')
def query(query, model, system, interactive):
    """Query your vault using RAG."""
    config = get_config()
    embeddings_file = config.embeddings_file

    if not embeddings_file.exists():
        click.echo(f"Error: Embeddings file not found. Run 'pkms search index' first.", err=True)
        return

    # Check Ollama
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if response.status_code != 200:
            click.echo(f"Error connecting to Ollama: {response.status_code}", err=True)
            return
    except requests.exceptions.ConnectionError:
        click.echo("Error: Could not connect to Ollama.", err=True)
        return

    # Load embeddings
    click.echo("Loading embeddings...")
    with open(embeddings_file, 'r', encoding='utf-8') as f:
        embeddings = json.load(f)
    click.echo(f"Loaded {len(embeddings)} chunks")

    system_prompt = system or "You are a helpful assistant that answers questions based on the provided context from my personal knowledge base."

    # Query mode
    queries = []
    if interactive or not query:
        click.echo("Interactive mode. Type 'exit' or 'quit' to end.")
        while True:
            q = click.prompt('\nQuery', default='', show_default=False)
            if q.lower() in ['exit', 'quit', '']:
                break
            queries.append(q)
    else:
        queries = [query]

    # Process queries
    for q in queries:
        click.echo(f"\n🔍 Query: {q}")

        # Get embedding
        query_embedding = get_embedding(q)

        # Find relevant chunks
        for chunk in embeddings:
            chunk["similarity"] = cosine_similarity(query_embedding, chunk["embedding"])
        sorted_chunks = sorted(embeddings, key=lambda x: x["similarity"], reverse=True)
        relevant = sorted_chunks[:MAX_CONTEXT_CHUNKS]

        # Format context
        context = "Here is relevant information from my knowledge base:\n\n"
        for i, chunk in enumerate(relevant):
            context += f"--- Document {i+1}: {chunk['file_path']} ---\n"
            context += chunk["content"] + "\n\n"

        # Query Ollama
        prompt = f"{context}\n\nQuestion: {q}\n\nAnswer:"
        url = f"{OLLAMA_BASE_URL}/api/generate"
        data = {"model": model, "prompt": prompt, "stream": False, "system": system_prompt}

        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            answer = response.json()["response"]
            click.echo(f"\n💡 Answer:\n{answer}\n")
        except requests.exceptions.RequestException as e:
            click.echo(f"Error querying Ollama: {e}", err=True)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0
    return np.dot(a, b) / (a_norm * b_norm)
