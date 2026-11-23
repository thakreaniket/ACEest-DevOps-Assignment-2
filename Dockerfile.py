FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ACEest_Fitness.py .
COPY test_app.py .

RUN python -c "from ACEest_Fitness import init_db; init_db()"

ENV APP_VERSION=v1.0.0
ENV DB_NAME=/app/aceest_fitness.db

EXPOSE 5000

CMD ["python", "ACEest_Fitness.py"]