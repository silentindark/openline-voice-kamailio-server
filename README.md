# openline-voice-kamailio-server

currently this docker image only supports WebRTC to WebRTC

to build the docker image:

```
./build.sh
```

to run the kamailio server:

```
docker run -d -p 8080:8080 --name openline-kamailio-server openline.ai/openline-kamailio-server
```
