## Kamailio - equivalent of routing blocks in Python
##
## KSR - the new dynamic object exporting Kamailio functions
## Router - the old object exporting Kamailio functions
##

## Relevant remarks:
##  * return code -255 is used to propagate the 'exit' behaviour to the
##  parent route block function. The alternative is to use the native
##  Python function sys.exit() (or exit()) -- it throws an exception that
##  is caught by Kamailio and previents the stop of the interpreter.


import KSR as KSR
import re


# global variables corresponding to defined values (e.g., flags) in kamailio.cfg
FLT_ACC=1
FLT_ACCMISSED=2
FLT_ACCFAILED=3
FLT_NATS=5

FLB_NATB=6
FLB_NATSIPPING=7

# global function to instantiate a kamailio class object
# -- executed when kamailio app_python module is initialized
def mod_init():
    KSR.info("===== from Python mod init\n")
    # dumpObj(KSR)
    return kamailio()


# -- {start defining kamailio class}
class kamailio:
    def __init__(self):
        KSR.info('===== kamailio.__init__\n')


    # executed when kamailio child processes are initialized
    def child_init(self, rank):
        KSR.info('===== kamailio.child_init(%d)\n' % rank)
        return 0


    # SIP request routing
    # -- equivalent of request_route{}
    def ksr_request_route(self, msg):
        # KSR.info("===== request - from kamailio python script\n")
        # KSR.info("===== method [%s] r-uri [%s]\n" % (KSR.pv.get("$rm"),KSR.pv.get("$ru")))
        if (KSR.pv.get("$Rp") == 8080 or KSR.pv.get("$Rp") == 4443) and not (KSR.is_WS() or KSR.is_WSS()):
            KSR.log("warn", "SIP request received on " + KSR.pv.getw("$Rp") + "\n")
            KSR.sl.send_reply(403, "Forbidden")
            return 0

        # per request initial checks
        if self.ksr_route_reqinit(msg)==-255 :
            return 1

        # NAT detection
        if self.ksr_route_natdetect(msg)==-255 :
            return 1

        # CANCEL processing
        if KSR.is_CANCEL():
            if KSR.tm.t_check_trans() > 0:
                self.ksr_route_relay(msg)
            return 1

        # handle requests within SIP dialogs
        if self.ksr_route_withindlg(msg) == -255 :
            return 1

        # -- only initial requests (no To tag)

        # handle retransmissions
        if KSR.tmx.t_precheck_trans()>0 :
            KSR.tm.t_check_trans()
            return 1

        if KSR.tm.t_check_trans()==0 :
            return 1

        # authentication
 #       if self.ksr_route_auth(msg)==-255 :
 #           return 1

        # record routing for dialog forming requests (in case they are routed)
        # - remove preloaded route headers
        KSR.hdr.remove("Route")
        if KSR.is_method_in("IS") :
            KSR.rr.record_route()


        # account only INVITEs
        if KSR.pv.get("$rm")=="INVITE" :
            KSR.setflag(FLT_ACC) # do accounting


        # dispatch requests to foreign domains
#        if self.ksr_route_sipout(msg)==-255 :
#            return 1

        # # requests for my local domains

        # handle registrations
        if self.ksr_route_registrar(msg)==-255 :
            return 1

        if KSR.corex.has_ruri_user() < 0 :
            # request with no Username in RURI
            KSR.sl.sl_send_reply(484,"Address Incomplete")
            return 1


        # user location service
        self.ksr_route_location(msg)

        return 1


    # wrapper around tm relay function
    def ksr_route_relay(self, msg):
        # enable additional event routes for forwarded requests
        # - serial forking, RTP relaying handling, a.s.o.
        if KSR.is_method_in("IBSU"):
            if KSR.tm.t_is_set("branch_route") < 0:
                KSR.tm.t_on_branch("ksr_branch_manage")

        if KSR.is_method_in("ISU"):
            if KSR.tm.t_is_set("onreply_route") < 0:
                KSR.tm.t_on_reply("ksr_onreply_manage")

        if KSR.is_INVITE() :
            if KSR.tm.t_is_set("failure_route") < 0:
                KSR.tm.t_on_failure("ksr_failure_manage")

        if KSR.tm.t_relay() < 0:
            KSR.sl.sl_reply_error()

        return -255


    # Per SIP request initial checks
    def ksr_route_reqinit(self, msg):

        if KSR.corex.has_user_agent() > 0 :
            ua = KSR.pv.gete("$ua")
            if (ua.find("friendly")!=-1 or ua.find("scanner")!=-1
                    or ua.find("sipcli")!=-1 or ua.find("sipvicious")!=-1) :
                KSR.sl.sl_send_reply(200, "Processed")
                return -255

        if KSR.maxfwd.process_maxfwd(10) < 0 :
            KSR.sl.sl_send_reply(483,"Too Many Hops")
            return -255

        if (KSR.is_OPTIONS()
                and KSR.corex.has_ruri_user() < 0) :
            KSR.sl.sl_send_reply(200,"Keepalive")
            return -255

        if KSR.sanity.sanity_check(17895, 7)<0 :
            KSR.err("Malformed SIP message from "
                    + KSR.pv.get("$si") + ":" + str(KSR.pv.get("$sp")) +"\n")
            return -255


    # Handle requests within SIP dialogs
    def ksr_route_withindlg(self, msg):
        if KSR.siputils.has_totag()<0 :
            return 1

        # sequential request withing a dialog should
        # take the path determined by record-routing
        if KSR.rr.loose_route()>0 :
            if self.ksr_route_dlguri(msg)==-255 :
                return -255
            if KSR.is_BYE() :
                # do accounting ...
                KSR.setflag(FLT_ACC)
                # ... even if the transaction fails
                KSR.setflag(FLT_ACCFAILED)
            elif KSR.is_ACK() :
                # ACK is forwarded statelessly
                if self.ksr_route_natmanage(msg)==-255 :
                    return -255
            elif KSR.is_NOTIFY() :
                # Add Record-Route for in-dialog NOTIFY as per RFC 6665.
                KSR.rr.record_route()

            self.ksr_route_relay(msg)
            return -255

        if KSR.is_ACK():
            if KSR.tm.t_check_trans() > 0:
                # no loose-route, but stateful ACK
                # must be an ACK after a 487
                # or e.g. 404 from upstream server
                self.ksr_route_relay(msg)
                return -255
            else:
                # ACK without matching transaction ... ignore and discard
                return -255

        KSR.sl.sl_send_reply(404, "Not here")
        return -255


    # Handle SIP registrations
    def ksr_route_registrar(self, msg):
        if not KSR.is_REGISTER():
            return 1
        KSR.registrar.unregister("location", KSR.pv.get("$fu"))
        if KSR.isflagset(FLT_NATS) :
            KSR.setbflag(FLB_NATB)
            # do SIP NAT pinging
            KSR.setbflag(FLB_NATSIPPING)

        if KSR.registrar.save("location", 0) < 0:
            KSR.sl.sl_reply_error()

        return -255


    # User location service
    def ksr_route_location(self, msg):
        rc = KSR.registrar.lookup("location")
        if rc < 0:
            KSR.tm.t_newtran()
            if rc == -1 or rc == -3:
                KSR.sl.send_reply(404, "Not Found")
                return -255
            elif rc == -2:
                KSR.sl.send_reply(405, "Method Not Allowed")
                return -255

        # when routing via usrloc, log the missed calls also
        if KSR.is_INVITE():
            KSR.setflag(FLT_ACCMISSED)

        self.ksr_route_relay(msg)
        return -255




    # Caller NAT detection
    def ksr_route_natdetect(self, msg):
        KSR.force_rport()

        if KSR.nathelper.nat_uac_test(65)>0 :
            if KSR.is_REGISTER() :
                KSR.nathelper.fix_nated_register()
            elif KSR.siputils.is_first_hop()>0 :
                KSR.nathelper.set_contact_alias()

            KSR.setflag(FLT_NATS)

        return 1


    # RTPProxy control
    def ksr_route_natmanage(self, msg):
        if KSR.siputils.is_request()>0 :
            if KSR.siputils.has_totag()>0 :
                if KSR.rr.check_route_param("nat=yes")>0 :
                    KSR.setbflag(FLB_NATB)

        if (not (KSR.isflagset(FLT_NATS) or KSR.isbflagset(FLB_NATB))) :
            return 1

        #KSR.rtpproxy.rtpproxy_manage("co")

        if KSR.siputils.is_request()>0 :
            if not KSR.siputils.has_totag() :
                if KSR.tmx.t_is_branch_route()>0 :
                    KSR.rr.add_rr_param(";nat=yes")

        if KSR.siputils.is_reply()>0 :
            if KSR.isbflagset(FLB_NATB) :
                KSR.nathelper.set_contact_alias()

        return 1


    # URI update for dialog requests
    def ksr_route_dlguri(self, msg):
        if not KSR.isdsturiset() :
            KSR.nathelper.handle_ruri_alias()

        return 1


    # Routing to foreign domains
    def ksr_route_sipout(self, msg):
        if KSR.is_myself_ruri() :
            return 1

        KSR.hdr.append("P-Hint: outbound\r\n")
        self.ksr_route_relay(msg)
        return -255


    # Manage outgoing branches
    # -- equivalent of branch_route[...]{}
    def ksr_branch_manage(self, msg):
        KSR.dbg("new branch ["+ str(KSR.pv.get("$T_branch_idx"))
                    + "] to "+ KSR.pv.get("$ru") + "\n")
        self.ksr_route_natmanage(msg)
        return 1


    # Manage incoming replies
    # -- equivalent of onreply_route[...]{}
    def ksr_onreply_manage(self, msg):
        KSR.dbg("incoming reply\n")
        scode = KSR.pv.get("$rs")
        if scode>100 and scode<299 :
            self.ksr_route_natmanage(msg)

        return 1

    def ksr_onsend_route(self, msg):
        return 1

    # Manage failure routing cases
    # -- equivalent of failure_route[...]{}
    def ksr_failure_manage(self, msg):
        if self.ksr_route_natmanage(msg)==-255 : return 1

        if KSR.tm.t_is_canceled()>0 :
            return 1

        return 1


    # SIP response handling
    # -- equivalent of reply_route{}
    def ksr_reply_route(self, msg):
        KSR.dbg("response handling - python script\n")

        if KSR.sanity.sanity_check(17604, 6)<0 :
            KSR.err("Malformed SIP response from "
                    + KSR.pv.get("$si") + ":" + str(KSR.pv.get("$sp")) +"\n")
            KSR.set_drop()
            return -255

        return 1

    def ksr_xhttp_event(self, msg, evname):
        KSR.info("===== xhttp module triggered event: " + evname + "\n")
        KSR.set_reply_close()
        KSR.set_reply_no_connect()
        if KSR.pv.get("$Rp") != 8080 and KSR.pv.get("$Rp") != 4443:
            KSR.xhttp.xhttp_reply(403, "Forbidden", "", "")
            return -255

        if re.search("websocket", KSR.pv.getw("$hdr(Upgrade)")) is not None and re.search("Upgrade", KSR.pv.getw("$hdr(Connection)")) is not None and re.search("GET", KSR.pv.getw("$rm")) is not None :
            if KSR.websocket.handle_handshake()>0 :
                return 1

    def ksr_websocket_event(self, msg, evname):
        #KSR.dbg("===== websocket module triggered event: " + evname + "\n")

        KSR.info("WebSocket connection from " +
                 KSR.pv.getw("$si") + ":" + str(KSR.pv.getw("$sp")) + " has closed")



# -- {end defining kamailio class}


# global helper function for debugging purposes
def dumpObj(obj):
    for attr in dir(obj):
        KSR.info("obj.%s = %s\n" % (attr, getattr(obj, attr)))

