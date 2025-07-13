import sqlite3
from sqlite3 import IntegrityError

database: str = "studentdb.db"

def connect():
    return sqlite3.connect(database)

def getprocess(sql: str) -> list:
    conn = connect()
    conn.row_factory = sqlite3.Row  # to return a dictionary formatted data
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    return rows

def getall(table: str) -> list:
    sql: str = f"SELECT * FROM {table}"
    return getprocess(sql)

def getall_idno(table: str) -> list:
    conn = connect()  # Assuming 'connect()' is a function that returns an SQLite connection
    conn.row_factory = sqlite3.Row  # to return a dictionary formatted data
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT idno FROM {table}")
    
    # Extract 'idno' values directly
    idnos = [row['idno'] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return idnos

def doprocess(sql)->bool:
    db = connect()
    cursor = db.cursor()
    try:
        cursor.execute(sql)
        db.commit()
        print(sql)
    except IntegrityError as e:
        if "Duplicate entry" in str(e) and "for key 'idno'" in str(e):
            print("ERROR: IDNO already exists!")
        else:
            print(f"ERROR: {e}")
        print("ERORRRRR")
        return False
    return True if cursor.rowcount>0 else False
	
def addrecord(table: str, **kwargs) -> bool:
    flds = list(kwargs.keys())
    vals = [str(val) for val in kwargs.values()]
    fld = ",".join(flds)
    val = "','".join(vals)
    sql = f"INSERT INTO {table}({fld}) values('{val}')"
    success = doprocess(sql)
    return success

def userlogin(table: str, **kwargs) -> bool:
    sql = ""
    keyVals = []
    for key, value in kwargs.items():
        print(f"KEY: {key}")
        print(f"VALUE: {value}")
        keyVals.append(f"{key} = '{value}'")
    condition:str = " and ".join(keyVals)
    print(condition)
    sql = f"SELECT * FROM {table} WHERE {condition}"
    print(f"SQL: {sql}")
    return getprocess(sql)
    
def getrecord(table:str,**kwargs)->list:
    params = list(kwargs.items())
    fields = []
    for index, flds in enumerate(params):
        flds = list(params[index])
        fields.append(f"{flds[0]} LIKE '{flds[1]}'")

    condition = " and ".join(fields)
    sql = f"SELECT * FROM {table} WHERE {condition}"
    print(f"sql={sql}")
    return getprocess(sql)
