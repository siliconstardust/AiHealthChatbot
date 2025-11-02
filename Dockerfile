FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Upgrade pip
RUN pip install --upgrade pip

# Install dependencies one by one to catch errors
RUN pip install --no-cache-dir rasa==3.6.13
RUN pip install --no-cache-dir rasa-sdk==3.6.2
RUN pip install --no-cache-dir flask==3.0.2
RUN pip install --no-cache-dir requests==2.31.0
RUN pip install --no-cache-dir gunicorn==21.2.0

# Copy rest of application
COPY . .

# Train the Rasa model
RUN rasa train

# Expose port
EXPOSE 5005

# Run command
CMD ["rasa", "run", "--enable-api", "--cors", "*", "--debug"]
