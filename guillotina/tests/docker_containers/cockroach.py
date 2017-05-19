from guillotina.tests.docker_containers.base import BaseImage

import psycopg2


class CockroachDB(BaseImage):
    label = 'cockroach'
    image = 'cockroachdb/cockroach:v1.0'
    to_port = 5432
    from_port = 26257
    image_options = BaseImage.image_options.copy()
    image_options.update(dict(
        command=' '.join([
            'cockroachdb/cockroach:v1.0 start --insecure',
        ])
    ))

    def check(self, host):
        try:
            conn = psycopg2.connect("dbname=guillotina user=root host=%s port=26257" % host)  # noqa
            cur = conn.cursor()
            cur.execute("CREATE DATABASE guillotina;")
            cur.fetchone()
            cur.close()
            conn.close()
            return True
        except: # noqa
            pass
        return False


image = CockroachDB()
