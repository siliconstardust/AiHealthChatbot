# Use official Rasa image as base
FROM rasa/rasa:3.6.13-full

WORKDIR /app
COPY . /app

# Install additional dependencies
RUN pip install --no-cache-dir flask==3.0.2 requests==2.31.0 gunicorn==21.2.0

# Expose Rasa default port
EXPOSE 5005

# Start Rasa server using your pre-trained model
CMD ["rasa", "run", "--enable-api", "--cors", "*", "--debug"]
