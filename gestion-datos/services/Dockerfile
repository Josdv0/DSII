# Un solo Dockerfile para todos los microservicios. Contexto de build = raíz del proyecto.
FROM python:3.12-slim
ARG SERVICE
WORKDIR /app
COPY services/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common ./common
COPY services/${SERVICE}/main.py ./main.py
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
