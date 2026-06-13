# Evaluator Agent

An AI-powered evaluation agent built with CrewAI for automated assessment tasks.

## Overview

This project implements an evaluator agent system using CrewAI framework with LangChain integration. The agent is designed to perform automated evaluations based on configurable criteria.

## Features

- CrewAI-based multi-agent evaluation system
- Configurable agents and tasks via YAML
- Pydantic models for structured data validation
- YAML-based configuration for prompts and settings

## Installation

```bash
pip install -e .
```

## Dependencies

- Python >= 3.10
- crewai >= 1.14.6
- langchain-openai >= 0.3.0
- pydantic >= 2.0
- pyyaml >= 6.0

## Project Structure

```
src/
├── config/           # Agent and task configurations
│   ├── agents.yaml   # Agent definitions
│   └── tasks.yaml    # Task definitions
├── skills/           # Custom skills
│   ├── preeval/      # Pre-evaluation skills
│   └── tipsc/        # TIPS-C skills
├── main.py           # Entry point
├── models.py         # Pydantic models
└── __init__.py
```

## Usage

```bash
python -m src.main
```

## Configuration

Edit `src/config/agents.yaml` and `src/config/tasks.yaml` to customize agent behavior and evaluation criteria.

## LLM Model Configuration

This project supports multiple LLM providers. The default configuration uses LM Studio for local deployment. To use different LLM models, modify the `load_llm()` function in `src/main.py`:

### LM Studio (Default)
```python
def load_llm() -> LLM:
    base_url = os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1")
    return LLM(
        model="openai/mistralai/mistral-7b-instruct-v0.3",
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",
        temperature=0.3,
    )
```

**Changes required:**
- Set `OPENAI_API_KEY=lm-studio` and `OPENAI_MODEL_NAME=openai/mistralai/mistral-7b-instruct-v0.3` in environment
- Ensure LM Studio server is running at http://localhost:1234/v1

### OpenAI
```python
def load_llm() -> LLM:
    return LLM(
        model="gpt-4o",
        api_key=os.environ.get("OPENAI_API_KEY"),
        temperature=0.3,
    )
```

**Changes required:**
- Set `OPENAI_API_KEY` to your OpenAI API key
- Remove LM Studio environment variables

### Anthropic
```python
def load_llm() -> LLM:
    return LLM(
        model="claude-3-5-sonnet-20241022",
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        temperature=0.3,
    )
```

**Changes required:**
- Set `ANTHROPIC_API_KEY` to your Anthropic API key
- Remove OpenAI environment variables

### Google Gemini
```python
def load_llm() -> LLM:
    return LLM(
        model="gemini-1.5-pro",
        api_key=os.environ.get("GOOGLE_API_KEY"),
        temperature=0.3,
    )
```

**Changes required:**
- Set `GOOGLE_API_KEY` to your Google Gemini API key
- Remove OpenAI environment variables

### Azure OpenAI
```python
def load_llm() -> LLM:
    return LLM(
        model="gpt-4o",
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        base_url=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        temperature=0.3,
    )
```

**Changes required:**
- Set `AZURE_OPENAI_API_KEY` to your Azure OpenAI key
- Set `AZURE_OPENAI_ENDPOINT` to your Azure OpenAI endpoint URL
- Remove LM Studio environment variables

## Environment Variables

Set the following environment variables before running the application:

- `LM_STUDIO_URL`: LM Studio server URL (default: http://localhost:1234/v1)
- `OPENAI_API_KEY`: OpenAI API key (if using OpenAI)
- `OPENAI_MODEL_NAME`: OpenAI model name (default: openai/mistralai/mistral-7b-instruct-v0.3)
- `ANTHROPIC_API_KEY`: Anthropic API key (if using Anthropic)
- `GOOGLE_API_KEY`: Google Gemini API key (if using Gemini)
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key (if using Azure)
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint URL (if using Azure)
- `TAVILY_API_KEY` : Your tavily search api key (line 20 , main.py)