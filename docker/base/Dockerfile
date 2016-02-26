FROM ubuntu:14.04
MAINTAINER Austin Middleton

RUN apt-get update
RUN apt-get upgrade -y

#######################
# Production packages #
#######################


RUN apt-get install -y\
    python3-pip\
    nodejs\
    npm

RUN ln -s /usr/bin/nodejs /usr/bin/node
ENV NODE_PATH=/usr/local/lib/node_modules
RUN npm install -g\
    aws-sdk\
    socket.io\
    express\
    body-parser\
    socket.io-client\
    mocha

#pip is installed but needs to upgraded because the apt repo is behind
RUN pip3 install --upgrade pip

#the upgrade version of pip runs as `pip` NOT `pip3`
RUN pip install\
    boto\
    jsonpickle\
    requests\
    nose\
    Flask\
    eventlet\
    gunicorn\
    stripe\
    twilio\
    pylint

##################
# Configurations #
##################

RUN addgroup --gid 4000 gator
RUN useradd --gid 4000 --no-create-home gator

ENTRYPOINT ["/bin/bash"]
