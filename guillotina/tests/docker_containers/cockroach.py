from guillotina.tests.docker_containers.base import BaseImage

import psycopg2


class CockroachDB(BaseImage):
    label = 'cockroach'
    image = 'cockroachdb/cockroach:v1.0'
    to_port = from_port = 26257
    image_options = BaseImage.image_options.copy()
    image_options.update(dict(
        command=' '.join([
            'start --insecure',
        ])
    ))

    def check(self, host):
        conn = cur = None
        try:
            conn = psycopg2.connect("dbname=guillotina user=root host=%s port=26257" % host)  # noqa
            conn.set_session(autocommit=True)
            cur = conn.cursor()
            cur.execute('SHOW DATABASES;')
            for result in cur.fetchall():
                if result[0] == 'guillotina':
                    conn.close()
                    cur.close()
                    return True
            cur.execute("CREATE DATABASE IF NOT EXISTS guillotina;")
            cur.close()
            conn.close()
        except: # noqa
            if conn is not None:
                conn.close()
            if cur is not None:
                cur.close()
        return False


image = CockroachDB()
