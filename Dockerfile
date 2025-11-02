# Use official Rasa image as base
FROM rasa/rasa:3.6.13-full

# Switch to root for safe package installation
USER root

# Set working directory
WORKDIR /app

# Copy all files into container
COPY . /app

# Upgrade pip safely and install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir flask requests gunicorn

# Train the Rasa model
RUN rasa train

# Switch back to non-root user (Render requires this)
USER 1001

# Expose Rasa default port
EXPOSE 5005

# Run Rasa server with API enabled
CMD ["rasa", "run", "--enable-api", "--cors", "*", "--debug"]
