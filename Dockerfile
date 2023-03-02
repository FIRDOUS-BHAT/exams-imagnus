FROM python:3.10

WORKDIR /
# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade -r /requirements.txt

COPY ./ /
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
