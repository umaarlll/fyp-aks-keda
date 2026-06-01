FROM python:3.11-slim
WORKDIR /app
COPY processor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY processor/main.py .
COPY response_engine ./response_engine
CMD ["python", "main.py"]