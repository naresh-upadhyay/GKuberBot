# Use official Python image
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port if needed (optional)
EXPOSE 5000

# Entry point
#CMD ["python", "StartGKuber.py"]
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
