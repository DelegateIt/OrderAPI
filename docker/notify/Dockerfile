FROM delegateit/gatbase
MAINTAINER Austin Middleton

WORKDIR /var/gator/api/notify
USER gator
EXPOSE 8060
ENV GATOR_CONFIG_PATH=/var/gator/api/local-config.json
ENV PYTHONPATH=/var/gator/api/
ENTRYPOINT ["nodejs", "socketio.js"]
