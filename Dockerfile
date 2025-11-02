# Use official Rasa image as base
FROM rasa/rasa:3.6.13-full

# Set working directory
WORKDIR /app

# Copy ALL project files including data directory
COPY . /app

# Install additional dependencies (not Rasa, it's already in base image)
RUN pip install --no-cache-dir flask==3.0.2 requests==2.31.0 gunicorn==21.2.0

# Train the Rasa model (make sure data folder exists)
RUN rasa train

# Expose Rasa server port
EXPOSE 5005

# Run Rasa server with API enabled
CMD ["rasa", "run", "--enable-api", "--cors", "*", "--debug"]
