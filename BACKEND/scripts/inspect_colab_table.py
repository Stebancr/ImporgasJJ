from django.db import connection

with connection.cursor() as c:
    c.execute('SHOW CREATE TABLE colaboradores')
    row = c.fetchone()
    if row:
        print(row[1])
    else:
        print('No table info')
