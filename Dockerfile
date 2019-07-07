FROM nixos/nix:2.2.1

COPY . /mediatum/mediatum
WORKDIR /mediatum/mediatum
RUN \
    # install mediatum dependencies
    ./mediatum.py --help \
    && mkdir /mediatum/data

CMD ./mediatum.py