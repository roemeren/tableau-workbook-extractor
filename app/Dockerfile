# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install graphviz
RUN apt-get update && apt-get install -y graphviz

# Expose the port the app runs on
EXPOSE 5000

# Run flask_app.py when the container launches
CMD ["gunicorn", "web.dash_app:app", "--bind", "0.0.0.0:5000"]