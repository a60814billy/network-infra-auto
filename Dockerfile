FROM python:3.12.4-slim AS builder
WORKDIR /build
RUN pip install uv
COPY deps/ deps/
COPY pyproject.toml uv.lock ./
COPY src/ src/
RUN uv build && \
    cp ./deps/*.whl ./dist/

FROM python:3.12.4-slim
WORKDIR /app

# install git
RUN apt-get update && \
    apt-get install -y \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/dist/*.whl ./
RUN pip install *.whl && \
    rm *.whl
