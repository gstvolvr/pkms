import click
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from pkms.core.utils import find_all_files
from pkms.core.config import get_config

@click.group('llm')
def llm():
    """Commands for interacting with local LLMs."""
    pass

@llm.command('summarize')
@click.option('--model', default='gpt2', help='Name of the model to use')
def summarize(model):
    """Summarize notes using a local LLM."""
    config = get_config()
    click.echo(f"Loading model: {model}")
    tokenizer = AutoTokenizer.from_pretrained(model)
    model = AutoModelForCausalLM.from_pretrained(model)
    llm_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer)

    files = find_all_files(str(config.pensieve_path))
    for file_path in files:
        click.echo(f"\nFile: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content:
            continue
        prompt = f"Summarize this text:\n{content[:1000]}"
        summary = llm_pipeline(prompt, max_length=300, num_return_sequences=1)[0]["generated_text"]
        click.echo(f"Summary:\n{summary}\n")

