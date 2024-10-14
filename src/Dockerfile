# syntax=docker/dockerfile:1
# Use the official Python image as a base
FROM python:3.13-slim-bullseye

# Install Node.js
RUN apt-get update && apt-get install -y curl && \
  curl -fsSL https://deb.nodesource.com/setup_16.x | bash - && \
  apt-get install -y nodejs && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*


# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /src

# Copy the requirements file into the container
COPY requirements.txt /src/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Node.js dependencies
COPY src/theme/static_src/package.json src/theme/static_src/package-lock.json /src/theme/static_src/

# Install Tailwind dependencies using npm ci for a clean install
RUN npm ci --prefix /src/theme/static_src/

# Copy the project into the container
COPY . /src/

# Expose the port that the Django app runs on
EXPOSE 8000

# Run the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]