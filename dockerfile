# Use the official Python image as a base
FROM python:3

# Set the working directory in the container
WORKDIR /app

# Copy the application files into the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables from .env file
ENV $(cat .env | xargs)

# Expose port if needed
EXPOSE 5252

# Command to run the application
CMD ["python", "main.py"]
