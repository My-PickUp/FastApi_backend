# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5101 available to the world outside this container
EXPOSE 5101

# Define environment variable
ENV NAME World

# Command to run the application on port 5101
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5101", "--reload"]
