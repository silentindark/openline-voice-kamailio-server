import unittest
import KSR as KSR
import sys
sys.path.insert(0, "../")
import kamailio as kamailio
import ksr_utils as ksr_utils


class MyTestCase(unittest.TestCase):

    def setUp(self) -> None:
        ksr_utils.ksr_utils_init(KSR._mock_data)


    def test_register(self):
        ksr_utils.pvar_set("$rm", "REGISTER")
        ksr_utils.pvar_set("$fu", "sip:test@openline.ai")
        ksr_utils.pvar_set("$ct", "<sip:10.0.0.1:9999>;expires=6000")
        ksr_utils.pvar_set("$Rp", 8080)


        k = kamailio.kamailio()
        k.ksr_request_route(None)
        print(ksr_utils.registrations["location"][ksr_utils.pvar_get("$fu")])
        print(ksr_utils.pvar_get("$ct"))
        self.assertEqual(ksr_utils.registrations["location"][ksr_utils.pvar_get("$fu")], ksr_utils.pvar_get("$ct"))  # add assertion here


    def test_INVITE(self):
        ksr_utils.pvar_set("$rm", "INVITE")
        ksr_utils.pvar_set("$ru", "sip:test@openline.ai")
        ksr_utils.pvar_set("$ct", "<sip:10.0.0.2:8080>")
        ksr_utils.pvar_set("$Rp", 8080)

        #simulate a registration in the location db
        ksr_utils.registrations["location"][ksr_utils.pvar_get("$ru")] = "<sip:10.0.0.1:9999>;expires=6000"


        k = kamailio.kamailio()
        k.ksr_request_route(None)

        self.assertEqual(ksr_utils.pvar_get("$ru"), "<sip:10.0.0.1:9999>;expires=6000")  # add assertion here


if __name__ == '__main__':
    unittest.main()
