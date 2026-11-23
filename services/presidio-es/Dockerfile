FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Modified Presidio packages (Spanish enterprise recognizers + MappingAnonymizerEngine)
COPY presidio/presidio-analyzer ./presidio/presidio-analyzer
COPY presidio/presidio-anonymizer ./presidio/presidio-anonymizer

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" pdfminer.six && \
    pip install --no-cache-dir -e ./presidio/presidio-analyzer && \
    pip install --no-cache-dir -e ./presidio/presidio-anonymizer && \
    python -m spacy download es_core_news_md

COPY server.py .

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 3000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000"]
