FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN addgroup --system bot && adduser --system --ingroup bot bot

COPY --chown=bot:bot src/ ./src/

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER bot

STOPSIGNAL SIGTERM

CMD ["python", "src/main.py"]
