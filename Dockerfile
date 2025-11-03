FROM python:3.9-slim

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy main application file
COPY app.py .

# Expose Flask port
EXPOSE 5000

# Run app
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]

