FROM alpine
MAINTAINER Sebastian Hutter <mail@sebastian-hutter.ch>

RUN apk --no-cache add python py-pip tini

ADD docker-entrypoint.sh /

ADD requirements.txt /

RUN pip install -r /requirements.txt && \
    chmod +x /docker-entrypoint.sh

ADD app /app/

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["python", "/app/podcaster/podcaster.py"]