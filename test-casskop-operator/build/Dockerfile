# Copy the controller-manager into a thin image
FROM alpine:latest

LABEL org.opencontainers.image.documentation="https://github.com/Orange-OpenSource/casskop/blob/master/README.md"
LABEL org.opencontainers.image.authors="Sébastien Allamand <sebastien.allamand@orange.com>"
LABEL org.opencontainers.image.source="https://github.com/Orange-OpenSource/casskop"
LABEL org.opencontainers.image.vendor="Orange France - Digital Factory"
LABEL org.opencontainers.image.version="0.1"
LABEL org.opencontainers.image.description="Operateur des Gestion de Clusters Cassandra"
LABEL org.opencontainers.image.url="https://github.com/Orange-OpenSource/casskop"
LABEL org.opencontainers.image.title="Operateur Cassandra"

LABEL org.label-schema.usage="https://github.com/Orange-OpenSource/casskop/blob/master/README.md"
LABEL org.label-schema.docker.cmd="/usr/local/bin/casskop"
LABEL org.label-schema.docker.cmd.devel="N/A"
LABEL org.label-schema.docker.cmd.test="N/A"
LABEL org.label-schema.docker.cmd.help="N/A"
LABEL org.label-schema.docker.cmd.debug="N/A"
LABEL org.label-schema.docker.params="LOG_LEVEL=define loglevel,RESYNC_PERIOD=period in second to execute resynchronisation,WATCH_NAMESPACE=namespace to watch for cassandraclusters,OPERATOR_NAME=name of the operator instance pod"


RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories
RUN apk update
RUN apk upgrade
RUN apk add bash

# install operator binary
COPY build/_output/bin/casskop /usr/local/bin/

CMD ["sleep", "infinity"]
