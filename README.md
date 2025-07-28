# Multi-Agent Software Engineering Sandbox

[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-000000?logo=opentelemetry&logoColor=white)](https://opentelemetry.io/)
[![Mesa](https://img.shields.io/badge/Mesa-AB3B61?logo=python&logoColor=white)](https://mesa.readthedocs.io/)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?logo=openai&logoColor=white)](https://openai.com/)

A research sandbox for studying **misalignment dynamics in software engineering processes** through multi-agent interactions with **full traceability**.

---

## Project Overview

This project simulates a software development team consisting of AI agents:

- **Planner**: Decomposes features into subtasks using GPT-4  
- **Coder**: Implements subtasks with domain-specific code generation  
- **Reviewer**: Evaluates code quality and approves/rejects implementations  

The system instruments all interactions with **OpenTelemetry** for observability and exports traces to **Jaeger** for analysis.

---

## Features

### Multi-Agent Simulation

* Planner, Coder, Reviewer agents
* Sequential workflow execution

### Observability

* OpenTelemetry instrumentation
* Jaeger trace visualization

### LLM Integration

* GPT-4 for task generation
* GPT-4 for workflow decomposition

### Analysis Framework

* MAST-style misalignment metrics
* Error propagation tracking
* Role-based span timelines

---

## Repository Structure

```
code_review_mas/
├── agents/               # Agent implementations
├── analysis/             # MAST-style analysis tools
├── llm/                  # LLM task generation
├── tracing/              # OpenTelemetry configuration
├── results/              # Simulation outputs
├── model.py              # Core coordination logic
├── run_simulation.py     # Main driver
└── requirements.txt      # Dependencies
```

---

## Installation & Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
echo "OPENAI_API_KEY=your_api_key" > .env
```

### 3. Start Jaeger

```bash
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest
```

---

## Running Simulations

### Run a 50-task simulation:

```bash
python run_simulation.py
```

### Perform MAST analysis:

```bash
python -m analysis.mast_analysis results/stress_test_*/full_results.json
```

---
