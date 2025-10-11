#!/usr/bin/env python3
import os
import sys
import json
import argparse
import requests
import numpy as np
from typing import List, Dict, Any
import util

# Constants
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDINGS_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3"  # Default model, can be changed via command line
EMBEDDINGS_FILE = os.path.join(util.BASE_PATH, "embeddings.json")
MAX_CONTEXT_CHUNKS = 5  # Number of chunks to include in context

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    
    if a_norm == 0 or b_norm == 0:
        return 0
    
    return np.dot(a, b) / (a_norm * b_norm)

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
        sys.exit(1)

def query_ollama(model: str, prompt: str, system_prompt: str = None) -> str:
    """Query Ollama with a prompt and return the response."""
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
        return response.json()["response"]
    except requests.exceptions.RequestException as e:
        print(f"Error querying Ollama: {e}")
        sys.exit(1)

def load_embeddings() -> List[Dict[str, Any]]:
    """Load embeddings from the JSON file."""
    try:
        with open(EMBEDDINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Embeddings file not found at {EMBEDDINGS_FILE}")
        print("Please run ollama_index.py first to generate embeddings.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in embeddings file {EMBEDDINGS_FILE}")
        sys.exit(1)

def find_relevant_chunks(query_embedding: List[float], embeddings: List[Dict[str, Any]], top_k: int = MAX_CONTEXT_CHUNKS) -> List[Dict[str, Any]]:
    """Find the most relevant chunks for a query embedding."""
    # Calculate similarities
    for chunk in embeddings:
        chunk["similarity"] = cosine_similarity(query_embedding, chunk["embedding"])
    
    # Sort by similarity (descending)
    sorted_chunks = sorted(embeddings, key=lambda x: x["similarity"], reverse=True)
    
    # Return top k chunks
    return sorted_chunks[:top_k]

def format_context(chunks: List[Dict[str, Any]]) -> str:
    """Format chunks into a context string."""
    context = "Here is relevant information from my knowledge base:\n\n"
    
    for i, chunk in enumerate(chunks):
        context += f"--- Document {i+1}: {chunk['file_path']} ---\n"
        context += chunk["content"]
        context += "\n\n"
    
    return context

def main():
    parser = argparse.ArgumentParser(description="Query Obsidian vault using Ollama RAG")
    parser.add_argument("--model", default=LLM_MODEL, help=f"Ollama model to use (default: {LLM_MODEL})")
    parser.add_argument("--query", help="Query to run (if not provided, interactive mode is used)")
    parser.add_argument("--system", help="System prompt to use")
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
    
    # Load embeddings
    print("Loading embeddings...")
    embeddings = load_embeddings()
    print(f"Loaded {len(embeddings)} chunks with embeddings")
    
    # Default system prompt
    system_prompt = args.system or "You are a helpful assistant that answers questions based on the provided context from my personal knowledge base. If the answer cannot be found in the context, say so clearly."
    
    # Interactive mode or single query
    if args.query:
        queries = [args.query]
    else:
        print("\nEntering interactive mode. Type 'exit' or 'quit' to end the session.")
        queries = []
        while True:
            query = input("\nEnter your query: ")
            if query.lower() in ["exit", "quit"]:
                break
            queries.append(query)
    
    # Process queries
    for query in queries:
        print(f"\nQuery: {query}")
        
        # Get embedding for the query
        print("Generating query embedding...")
        query_embedding = get_embedding(query)
        
        # Find relevant chunks
        print("Finding relevant context...")
        relevant_chunks = find_relevant_chunks(query_embedding, embeddings)
        
        # Format context
        context = format_context(relevant_chunks)
        
        # Construct prompt
        prompt = f"{context}\n\nQuestion: {query}\n\nAnswer:"
        
        # Query Ollama
        print(f"Querying Ollama with model {args.model}...")
        response = query_ollama(args.model, prompt, system_prompt)
        
        # Print response
        print("\n--- Response ---")
        print(response)
        print("----------------")

if __name__ == "__main__":
    main()