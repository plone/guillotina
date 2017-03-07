import pickle


def reader(result):
    obj = pickle.loads(result['state'])
    obj._p_oid = result['zoid']
    obj._p_serial = result['tid']
    obj.__name__ = result['id']
    return obj
