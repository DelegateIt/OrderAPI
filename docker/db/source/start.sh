#!/bin/sh

cd /var/gator/db
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -delayTransientStatuses -port 8041 &

sleep 1

cd /var/gator/api/notify
nodejs lambdaserver.js &

sleep 1

cd /var/gator/api
exec gunicorn --error-logfile - -b 0.0.0.0:8040 --reload gator.dynamoproxy:app
sleep 1
