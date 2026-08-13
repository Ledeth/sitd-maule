FROM python:3.11-slim

# GDAL/GEOS/PROJ: dependencias nativas de geopandas/shapely/pyproj
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev libgeos-dev libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render (y la mayoría de PaaS) inyectan el puerto por la variable $PORT.
# En local, si PORT no está definido, cae a 8000.
ENV PORT=8000
EXPOSE 8000

# Sin --reload en producción. Usa sh -c para expandir $PORT en runtime.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
