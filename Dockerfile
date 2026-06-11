FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the ONNX model from local disk — no internet download needed
RUN mkdir -p /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2
COPY onnx_model/onnx.tar.gz /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]