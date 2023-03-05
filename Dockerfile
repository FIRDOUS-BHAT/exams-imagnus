# Pull base image
FROM python:3.10
# Set environment varibles
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /code/
# Install dependencies
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . /code/
EXPOSE 8000
CMD ["python", "main.py"]







