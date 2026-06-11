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