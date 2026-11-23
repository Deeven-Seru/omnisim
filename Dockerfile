# Multi-stage lightweight production container for OmniSim
FROM python:3.12-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY omnisim/ omnisim/
RUN pip install --no-cache-dir .

FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="OmniSim"
LABEL org.opencontainers.image.description="Universal Counterfactual Simulation Engine & Pre-Flight Action Gate"
LABEL org.opencontainers.image.url="https://github.com/Deeven-Seru/omnisim"
LABEL org.opencontainers.image.source="https://github.com/Deeven-Seru/omnisim"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /workspace

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/omnisim /usr/local/bin/omnisim

ENTRYPOINT ["omnisim"]
CMD ["simulate", "--domain", "systems", "--horizon", "6"]
