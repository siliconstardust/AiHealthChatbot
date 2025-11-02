# Use official Rasa image as base
FROM rasa/rasa:3.6.13

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Train the Rasa model
RUN rasa train

# Expose Rasa server port
EXPOSE 5005

# Run Rasa server with API enabled
CMD ["rasa", "run", "--enable-api", "--cors", "*", "--debug"]
