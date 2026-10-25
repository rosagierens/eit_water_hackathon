FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Settings normally read from app/api/.env (not copied into the image).
# ENV APP_NAME="EIT-Water-Hackathon" \
#     APP_ENV="production" \
#     FACILITIES_CSV="data/app_input/facilities.csv" \
#     RAW_DISCHARGE_DATA="data/app_input/environment/discharge.parquet" \
#     WATER_TEMPERATURE_DATA="data/app_input/environment/water_temperature.parquet" \
#     CURTAILMENT_DATA="data/app_input/environment/curtailment.parquet"

WORKDIR /src

COPY app/requirements.txt app/requirements.txt
RUN pip install -r app/requirements.txt

COPY app/ app/
COPY data/app_input/ data/app_input/

RUN useradd --system --no-create-home appuser \
 && chmod -R a+rX /src
USER appuser

EXPOSE 8050
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8050/api/plants', timeout=4)"

CMD ["python", "-m", "app", "--host", "0.0.0.0", "--port", "8050"]
