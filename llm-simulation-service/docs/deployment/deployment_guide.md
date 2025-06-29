# Deployment Guide

This service ships with a Dockerfile and `docker-compose.yml` for easy deployment.

## Build Image
```bash
docker build -t llm-sim-service .
```

## Run with Docker
```bash
docker run -p 5000:5000 -e OPENAI_API_KEY=sk-... llm-sim-service
```
Logs and results are stored in `/app/logs` and `/app/results` inside the container.

## docker-compose
```bash
docker compose up -d
```
This uses environment variables from your shell and mounts `results/` and `logs/` directories for persistence.
