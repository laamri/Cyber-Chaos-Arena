# Cyber Chaos Arena
## Containerized honeynet and SOC observability lab

A team cybersecurity project exploring deception, runtime detection, centralized telemetry, and investigation. This repository publishes a **Docker Compose implementation** of part of the broader academic project.

### What to review
- [Service definitions](docker/docker-compose.yml): Cowrie, web honeypot, real web application, Nginx, Falco, Elasticsearch, Kibana, Filebeat, Loki, Grafana, and MinIO.
- [Falco rules](docker/falco/falco_rules.local.yaml): custom runtime detection rules.
- [Web honeypot](docker/web-honeypot/app.py) and [web application](docker/real-web-app/app.py): application components.
- [PowerShell orchestration](scripts/): setup, secret generation, LAN configuration, stack launch, and health checks.

### Architecture
Nginx fronts the application and web honeypot. Cowrie provides an SSH honeypot. Falco provides runtime detection; Filebeat collects container logs into Elasticsearch for Kibana investigation. Loki and Grafana provide additional observability, while MinIO provides object storage.

### Local setup
Review the scripts before running them. Use an isolated lab with Docker Desktop and PowerShell; Falco also needs a compatible Linux kernel/container environment.

```powershell
git clone https://github.com/laamri/Cyber-Chaos-Arena.git
cd Cyber-Chaos-Arena
.\scripts\generate-secrets.ps1
.\scripts\launch-soc.ps1
```

The launcher requires a local `.env` containing Grafana and MinIO credentials and `SOC_BIND_ADDRESS`. The Compose file defaults published services to loopback. Inspect [bootstrap](scripts/bootstrap.ps1) and [LAN configuration](scripts/configure-lan.ps1) for environment-specific setup.

### Public implementation scope
The committed stack uses Docker Compose, Falco, ELK, Cowrie, Loki, Grafana, and MinIO. Kubernetes, Wazuh, and Ollama are part of the broader project description in the CV, but are not represented as services in this public Compose implementation. This page describes repository contents; it does not claim a verified end-to-end deployment.

### Team
Sayf Eddine Laamri, Bagy Oussama, Halima Badr, Asma Bensassi Nour, and Ikram Laabouki. Supervised by Pr. Ali Azougaghe.

[Sayf's portfolio and project report](https://laamri-sayf-eddine.vercel.app) · [GitHub profile](https://github.com/laamri)
