# Use official Rasa image as base
FROM rasa/rasa:3.6.13-full

# Set working directory
WORKDIR /app

# Copy all project files
COPY . /app

# Upgrade pip and install additional dependencies safely
RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m pip install --no-cache-dir --upgrade flask requests gunicorn

# Train the Rasa model
RUN rasa train

# Expose Rasa server port
EXPOSE 5005

# Run Rasa server with API enabled
CMD ["rasa", "run", "--enable-api", "--cors", "*", "--debug"]
