FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
ENV PROJECT_ID=cloud-project-74451
ENV LOCATION=us-central1

CMD exec gunicorn --bind :$PORT --workers 2 --threads 8 --timeout 0 app:app