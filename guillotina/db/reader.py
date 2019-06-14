import pickle


def reader(result):
    obj = pickle.loads(result['state'])
    obj.__uuid__ = result['zoid']
    obj.__serial__ = result['tid']
    obj.__name__ = result['id']
    return obj
