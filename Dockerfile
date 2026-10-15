# Use an official lightweight Python image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirement file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application source code
COPY . .

# Expose port 5000 for the Flask app
EXPOSE 5000

# Command to run the Flask application
CMD ["python", "app.py"]