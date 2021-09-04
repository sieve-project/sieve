FROM kindest/node:latest
# COPY sieve-server/* /sieve-server/
RUN echo "Build my own kind image..." \
    && apt update && apt install -y bash vim
