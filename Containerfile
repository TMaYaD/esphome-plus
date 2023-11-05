# Global ARG, available to all stages (if renewed)
ARG WORKDIR="/app"

FROM python:3.12 AS builder

# Renew (https://stackoverflow.com/a/53682110):
ARG WORKDIR

# Don't buffer `stdout`:
ENV PYTHONUNBUFFERED=1
# Don't create `.pyc` files:
ENV PYTHONDONTWRITEBYTECODE=1

RUN pip install poetry && poetry config virtualenvs.in-project true

WORKDIR ${WORKDIR}
COPY pyproject.toml poetry.lock .
RUN poetry install --no-root --no-directory --only main --no-ansi

COPY . .

RUN poetry install --only main --no-ansi

FROM python:3.12-slim

ARG WORKDIR

WORKDIR ${WORKDIR}

COPY --from=builder ${WORKDIR} .

# App-specific settings:
ENV pio_cache_base=/cache/platformio
RUN mkdir -p "${pio_cache_base}"

# we can't set core_dir, because the settings file is stored in `core_dir/appstate.json`
# setting `core_dir` would therefore prevent pio from accessing
ENV PLATFORMIO_PLATFORMS_DIR="${pio_cache_base}/platforms"
ENV PLATFORMIO_PACKAGES_DIR="${pio_cache_base}/packages"
ENV PLATFORMIO_CACHE_DIR="${pio_cache_base}/cache"
ENV PATH="${WORKDIR}/.venv/bin:${PATH}"

# Settings for dashboard
ENV USERNAME="" PASSWORD=""

# Expose the dashboard to Docker
EXPOSE 6052

# # For options, see https://boxmatrix.info/wiki/Property:adduser
# RUN adduser app -DHh ${WORKDIR} -u 1000
# USER 1000

ENTRYPOINT ["esphome-plus"]
CMD ["reconcile", "-a", "/config"]
