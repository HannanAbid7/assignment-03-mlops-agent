FROM python:3.11-slim
WORKDIR /app
COPY api/ api/
RUN pip install fastapi uvicorn
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
