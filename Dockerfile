# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose port (if your app runs on port 8080, for example)
EXPOSE 8000

# Define environment variable for Python
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["fastapi", "dev", "--host", "0.0.0.0", "--port", "8000"]

