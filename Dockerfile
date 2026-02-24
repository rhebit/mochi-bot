FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app


# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create volume mount point for data
VOLUME /app/data

# Set environment variable for database path (can be overridden)
ENV DB_PATH=/app/data/mochi.db

# Run the bot
CMD ["python", "main.py"]
