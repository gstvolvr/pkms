import os
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from pathlib import Path
import util

# Set up paths
MODEL_NAME = "gpt2"  # Replace with your desired model

def load_model(model_name):
    """Load the specified model and tokenizer."""
    print(f"Loading model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    return pipeline("text-generation", model=model, tokenizer=tokenizer)

def get_vault_files(vault_path):
    """Retrieve all Markdown files in the Obsidian vault."""
    vault = Path(vault_path)
    return list(vault.rglob("*.md"))

def read_file(file_path):
    """Read the content of a Markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def query_llm(pipeline, prompt, max_length=300):
    """Query the local LLM with a prompt."""
    response = pipeline(prompt, max_length=max_length, num_return_sequences=1)
    return response[0]["generated_text"]

def main():
    # Load the model
    llm_pipeline = load_model(MODEL_NAME)

    # Get all Markdown files from the Obsidian vault
    md_files = get_vault_files(util.PENSIEVE_PATH)
    print(f"Found {len(md_files)} Markdown files.")

    # Select a file and read its content
    for md_file in md_files:
        content = read_file(md_file)
        print(f"\nFile: {md_file}")
        print(f"Content:\n{content[:500]}...\n")

        # Interact with the LLM
        prompt = f"Summarize this text:\n{content[:1000]}"
        summary = query_llm(llm_pipeline, prompt)
        print(f"Summary:\n{summary}\n")

        # Optionally save or process the summary further

if __name__ == "__main__":
    main()
