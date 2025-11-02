FROM rasa/rasa:3.6.2

WORKDIR /app

# Copy requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files
COPY . /app

# Expose port
EXPOSE 5005

# Run Rasa
CMD ["rasa", "run", "--enable-api", "--cors", "*", "--port", "5005", "--debug"]