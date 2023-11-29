# syntax=docker/dockerfile:latest

FROM python:3.11-slim as base

RUN mkdir -p  /BUILD/randeli

ENV PIP_ROOT_USER_ACTION=ignore

RUN pip install --upgrade pip

WORKDIR "/BUILD/randeli"

#####################################################
FROM base as builder

# Keep this early to maximize the docker layer cache re-use
RUN apt-get update && apt-get upgrade

RUN pip3 install --upgrade build


ADD setup.py  pyproject.toml *.md /BUILD/randeli/
ADD randeli  /BUILD/randeli/randeli/

RUN cd /BUILD/randeli && python -m build

#####################################################
FROM base as production

# TODO: come up with an easy way of adding fonts...
RUN apt-get update && apt-get upgrade && \
    apt-get install -y \
        fonts-arkpandora \
        fonts-cmu \
        fonts-lmodern \
        fonts-noto-mono \
        fonts-urw-base35

RUN useradd --system -m -d /randeli randeli

RUN mkdir /CFG /IN /OUT && \
    chown randeli /CFG /IN /OUT && \
    chmod 775 /CFG /IN /OUT && \
    ln -s /CFG /randeli/.randeli

ENV PATH=/randeli/.local/bin:$PATH
ENV RANDELI_CONFIG_PATH=/CFG/config.ini
ENV RANDELI_LOG=/OUT/randeli.log

USER randeli

# copy the wheel from the build stage
COPY --from=builder /BUILD/randeli/dist/randeli*.whl /tmp/

RUN pip install /tmp/randeli*whl

WORKDIR "/randeli"

RUN randeli bootstrap --download

RUN pip list --format=json > /randeli/installed.json

ENTRYPOINT ["/randeli/.local/bin/randeli"]
