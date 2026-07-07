# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY server.py weather.py overlay.py weather_page.py ./
COPY fonts/ ./fonts/

# Make port 5001 available to the world outside this container
EXPOSE 5001

ENV PYTHONUNBUFFERED=1

# Run the application with Gunicorn
# 4 workers is a good start for general purpose
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "--capture-output", "--log-level", "debug", "--error-logfile", "-", "server:app"]
