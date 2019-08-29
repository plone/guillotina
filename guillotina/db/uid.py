import uuid


MAX_UID_LENGTH = 64
UID_SPLIT_LENGTH = 3
UUID_LENGTH = 32
# | is sorted *after* alphanumeric characters so parents
# will show before their children in the key range
# -- not sure there is a lot more value in parents being before children
#    in key range sorting but...
OID_DELIMITER = "|"

# max object depth this provides best benefit to is:
#   (MAX_UID_LENGTH - UUID_LENGTH) / UID_SPLIT_LENGTH


def get_short_uid(oid):
    return oid.split(OID_DELIMITER)[-1]


def bw_oid_generator(ob):
    return uuid.uuid4().hex


def generate_uid(ob):
    """
    We want OIDs that allow keys to organize data where it is logically
    in the hierarchy of data in the object tree.


    - 00000000000000000000000000000000 (root)
        - a79143c988f143c28a2a2cb3821424e8
        - ba2ed51e874a423e93b156ab7950a5ad
            - ba2|12c3bbd82f22403eb889d0d25b53b0b0
            - ba2|286d9ff90f65416cba5b85fdfdd6d7b2
                - ba2|286|aee97de832f54eeea7484676ceb4e854
                - ba2|286|aed97de832f54eeea7484676ceb4e854
                - ba2|286|aee|cc6ecc8510684ceaa24bf509f5f936c7
                - ba2|286|aee|ec6e76d668934136bee1442bc5b0c61d
    """

    parts = []
    current = ob
    while current.__parent__:
        parent = current.__parent__
        if parent.__parent__:
            # no value in including root as part of this...
            parts.append(get_short_uid(parent.__uuid__)[:UID_SPLIT_LENGTH])
        current = current.__parent__
    parts = parts[::-1]  # reverse it
    if ob.__of__:
        parts.append(ob.__of__[:UID_SPLIT_LENGTH])
    short_oid = uuid.uuid4().hex
    if len(parts) > 0:
        oid = "{}{}{}".format("|".join(parts), OID_DELIMITER, short_oid)
    else:
        oid = short_oid
    return oid[-MAX_UID_LENGTH:]  # trim any possible extra...
