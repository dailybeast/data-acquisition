FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fetch_post_stats.py .
COPY main.py .

CMD ["python", "main.py"]
