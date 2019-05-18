from pg import DB

db = DB(dbname='follow-api', host='localhost',
        port=5432, user='juan', passwd='1234')

def get_table_names():
    tables = db.get_tables()
    return list(map(lambda x: x.split('.')[1], tables))

def get_table_structure(table_name):
    return db.get_attnames(table_name)

def get_table_contents(table_name):
    # return db.query('SELECT * FROM $1')
    return db.get_as_list('"Alarms"')

# print(get_table_contents('Products'))


