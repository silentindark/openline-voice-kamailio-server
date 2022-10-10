pvar_vals = {}
registrations = {}
registrations["location"] = {}

def ksr_utils_init(_mock_data):
    pvar_vals = {}
    registrations["location"] = {}

    _mock_data['pv']['get'] = pvar_get
    _mock_data['pv']['getw'] = pvar_getw
    _mock_data['pv']['gete'] = pvar_gete
    _mock_data['pv']['set'] = pvar_set
    _mock_data['']['is_INVITE'] = is_invite
    _mock_data['']['is_ACK'] = is_ack
    _mock_data['']['is_BYE'] = is_bye
    _mock_data['']['is_CANCEL'] = is_cancel
    _mock_data['']['is_REGISTER'] = is_register
    _mock_data['']['is_OPTIONS'] = is_options
    _mock_data['']['is_method_in'] = is_method_in
    _mock_data['registrar']['save'] = location_save
    _mock_data['registrar']['lookup'] = location_lookup
    _mock_data['registrar']['unregister'] = location_unregister
    _mock_data['siputils']['has_totag'] = siputils_has_to_tag
    _mock_data['tmx']['t_precheck_trans'] = -1
    _mock_data['tm']['t_check_trans'] = -1



def location_unregister(table: str, uri: str):
    registrations[table][uri] = None
    return 1


def location_save(table: str, flags: int):
    registrations[table][pvar_get("$fu")] = pvar_get("$ct")
    return 1


def location_lookup(table: str):
    if registrations[table] is None or registrations[table][pvar_get("$ru")] is None:
        return -1

    pvar_set("$ru", registrations[table][pvar_get("$ru")])
    return 1


def pvar_gete(key):
    if key not in pvar_vals or pvar_vals[key] is None:
        return ""
    return pvar_vals[key]

def pvar_getw(key):
    if key not in pvar_vals or pvar_vals[key] is None:
        return "<<null>>"
    return pvar_vals[key]

def pvar_get(key):
    return pvar_vals[key]


def pvar_set(key, value):
    pvar_vals[key] = value
    return 1


def siputils_has_to_tag():
    if pvar_gete("$tt") == "":
        return -1
    return 1


def is_invite():
    if pvar_get("$rm") == "INVITE":
        return True
    return False


def is_ack():
    if pvar_get("$rm") == "ACK":
        return True
    return False


def is_bye():
    if pvar_get("$rm") == "BYE":
        return True
    return False


def is_cancel():
    if pvar_get("$rm") == "CANCEL":
        return True
    return False


def is_register():
    if pvar_get("$rm") == "REGISTER":
        return True
    return False


def is_options():
    if pvar_get("$rm") == "OPTIONS":
        return True
    return False

def is_method_in(vmethod: str):
    method = pvar_get("$rm")

    if method == "INVITE" and vmethod.__contains__("I"):
        return True
    elif method == "ACK" and vmethod.__contains__("A"):
        return True
    elif method == "CANCEL" and vmethod.__contains__("C"):
        return True
    elif method == "BYE" and vmethod.__contains__("B"):
        return True
    elif method == "OPTIONS" and vmethod.__contains__("O"):
        return True
    elif method == "REGISTER" and vmethod.__contains__("R"):
        return True
    else:
        return True


