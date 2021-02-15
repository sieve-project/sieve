FROM kindest/node:latest
# COPY sonar-server/* /sonar-server/
RUN echo "Build my own kind image..." \
    && apt update && apt install -y bash vim
