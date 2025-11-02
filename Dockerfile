WORKDIR /app

# Copy all files
COPY . /app

# Install Twilio
RUN pip install --no-cache-dir twilio==8.2.2

# Expose port
EXPOSE 5005

# Fixed CMD - remove duplicate 'rasa'
CMD ["run", "--enable-api", "--cors", "*", "--port", "5005", "--debug"]
