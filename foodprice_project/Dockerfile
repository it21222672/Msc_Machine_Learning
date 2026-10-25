FROM python:3.11-slim

# lightgbm needs the OpenMP runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 appuser
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=appuser:appuser . .
USER appuser

ENV PORT=7860 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
EXPOSE 7860
CMD ["sh", "start.sh"]
