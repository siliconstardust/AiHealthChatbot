FROM rasa/rasa:3.6.2

WORKDIR /app

# Copy all files first
COPY . /app

# Install only Twilio with compatible version
RUN pip install --no-cache-dir twilio==8.2.2

# Expose port
EXPOSE 5005

# Run Rasa
CMD ["rasa", "run", "--enable-api", "--cors", "*", "--port", "5005", "--debug"]
