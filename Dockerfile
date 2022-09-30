FROM kamailio/kamailio:5.5.5-bullseye

#Copy the config file onto the Filesystem of the Docker instance
COPY kamailio.cfg /etc/kamailio/

#Expose port 5060 (SIP) for TCP and UDP
EXPOSE 5060
EXPOSE 5060/udp

EXPOSE 8080
EXPOSE 4443
