# Use official Rasa image as base
FROM rasa/rasa:3.6.13-full

# Switch to root to install packages
USER root

# Set working directory
WORKDIR /app

# Copy all project files
COPY . /app

# Safely install dependencies (without touching system pip)
RUN pip install --no-cache-dir --user flask requests gunicorn

# Train the Rasa model
RUN rasa train

# Expose Rasa server port
EXPOSE 5005

# Switch back to non-root user for security
USER 1001

# Run Rasa server with API enabled
CMD ["rasa", "run", "--enable-api", "--cors", "*", "--debug"]
