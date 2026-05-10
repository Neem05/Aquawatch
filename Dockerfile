FROM python:3.11-slim

WORKDIR /app

# Copy requirements from root (where it is)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app.py from backend folder
COPY backend/app.py .

# Copy any other backend files if needed
# COPY backend/other_files.py . (if any)

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Run the application
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
