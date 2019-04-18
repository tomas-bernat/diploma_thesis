#---------PRVNÍ ČÁST-------------#
import arcpy

kb = arcpy.GetParameterAsText(0)
sberne_plochy = arcpy.GetParameterAsText(1)
sde_name = arcpy.GetParameterAsText(2)

def db_connection(sde_name):
    """Funkce pro připojení se k databázi dle SDE"""
    sde = 'Database Connections\Connection to ' + sde_name + '.sde'
    try:
        conn = arcpy.ArcSDESQLExecute(sde)
        arcpy.AddMessage('\nDatabazove pripojeni ' + sde_name + ' probehlo uspesne')
    except:
        raise Exception('\nDatabazove pripojeni ' + sde_name + ' neexistuje.'
                        '\nPripojeni je treba vytvorit pomoci "Add Database Connection".')
    return(conn)

def import_data(shp_file,sde_name,table):
    """Funkce pro import SHP dat do databáze"""
    sde = 'Database Connections\Connection to ' + sde_name + '.sde'
    arcpy.FeatureClassToFeatureClass_conversion(shp_file,sde,table)
    arcpy.AddMessage('Vrstva ' + shp_file + ' byla naimportovana jako tabulka ' + table)

#---------DRUHÁ ČÁST-------------#
def change_data_type(conn,table,field):
    """Funkce pro změnu datového typu sloupce na text"""
    sql = 'ALTER TABLE '+table+' ALTER COLUMN '+field+' TYPE VARCHAR(20)'
    conn.execute(sql)
    arcpy.AddMessage('Pro tabulku '+table+' zmenen datovy typ sloupce '+field+' na text')

def drop_primary_key(conn,table):
    """Funkce pro odstranění defaultního primárního klíče tabulky"""
    sql = 'ALTER TABLE '+table+' DROP CONSTRAINT '+table+'_pkey'
    conn.execute(sql)
    arcpy.AddMessage('Pro tabulku '+table+' byl odstranen defaultni primarni klic')

def add_primary_key(conn,table,field):
    """Funkce pro přidání primárního klíče tabulky"""
    sql = 'ALTER TABLE '+table+' ADD PRIMARY KEY('+field+')'
    conn.execute(sql)
    arcpy.AddMessage('Pro tabulku '+table+' byl pridan primarni klic '+field)

def add_foreign_key(conn,table,field,ref_table,ref_field):
    """Funkce pro přidání cizího klíče tabulky"""
    sql = 'ALTER TABLE '+table+' ADD CONSTRAINT '+table+'_fkey FOREIGN KEY ('+field+') '
    sql += 'REFERENCES '+ref_table+'('+ref_field+')'
    conn.execute(sql)
    arcpy.AddMessage('Pro tabulku '+table+' byl pridan cizi klic '+field)

#---------TŘETÍ ČÁST-------------#
def get_select_output(conn,select_querry):
    """Funkce pro vytvoření slovníku z výstupu SQL příkazu"""
    raw_output = conn.execute(select_querry)
    output = {}
    for item in raw_output:
        key = str(item[0])
        values = [str(i) for i in item[1:]]
        output[key]=values
    return(output)

def rem_und(fields):
    """Funkce pro odstranění podtržítek z názvu sloupce"""
    if type(fields) is list:
        for f in fields:
            fields[fields.index(f)] = f.replace('_','')
    else:
        fields = fields.replace('_','')
    return(fields)

def classify_fields(conn,keep_fields):
    """Funkce pro klasifikaci sloupců na duplikované a sloupce k přesunu"""
    sql = """SELECT column_name, udt_name, character_maximum_length,
             numeric_precision, numeric_scale
             FROM information_schema.columns WHERE table_name = 'kb'"""
    kb_fields = get_select_output(conn,sql)
    sql = """SELECT column_name FROM information_schema.columns
             WHERE table_name = 'sberne_plochy'"""
    sberne_plochy_fields = get_select_output(conn,sql)
    duplicated_fields = []
    transfer_fields = {}
    for key, values in kb_fields.items():
        if key not in keep_fields:
            if rem_und(key) in rem_und(sberne_plochy_fields.keys()):
                duplicated_fields.append(key)
            else:
                transfer_fields[key] = values
    return(duplicated_fields,transfer_fields)

#---------ČTVRTÁ ČÁST-------------#
def add_columns(conn,table,fields):
    """Funkce pro přidání sloupců do tabulky"""
    sql = 'ALTER TABLE ' + table
    for key, value in fields.items():
        sql += '\nADD COLUMN ' + key +' '
        if value[0] == 'varchar':
            sql += value[0]+'('+value[1]+'),'
        elif value[0] == 'numeric':
            sql += value[0]+'('+value[2]+','+value[3]+'),'
        else:
            sql += value[0]+','
    sql = sql[0:-1] #oddělání poslední čárky
    conn.execute(sql)
    arcpy.AddMessage('Pro tabulku ' + table + ' byly vytvoreny presunute sloupce')

def update_columns(conn,to_table,from_table,fields,to_id,from_id):
    """Funkce pro kopírování dat do nových sloupců"""
    sql = 'UPDATE ' + to_table + '\nSET '
    for f in fields:
        sql += f + '=' + from_table + '.' + f + ','
    sql = sql[0:-1]  # oddělání poslední čárky
    sql += '\nFROM ' + from_table
    sql += '\nWHERE ' + to_table + '.' + to_id + '=' +from_table + '.' + from_id
    conn.execute(sql)
    arcpy.AddMessage('Pro tabulku ' + to_table + ' byly naplneny presunute sloupce')

def drop_columns(conn,table,fields):
    """Funkce pro odstranění nadbytečných sloupců"""
    sql = "ALTER TABLE " + table
    for f in fields:
        sql += "\nDROP COLUMN " + f + ","
    sql = sql[0:-1]  # oddělání poslední čárky
    conn.execute(sql)
    arcpy.AddMessage('Pro tabulku ' + table + ' byly smazany presunute sloupce')

#---------PÁTÁ ČÁST-------------#
def create_pasport_table(conn):
    """Funkce pro vytvoření tabulky pasport"""
    sql = """CREATE TABLE pasport(
             id_kb VARCHAR(20) REFERENCES kb(id_kb),
             pasport_id VARCHAR(20) PRIMARY KEY,
             zpracoval VARCHAR(50),
             datum_cas TIMESTAMP,
             problemy VARCHAR(50),
             zatrubneni VARCHAR(50),
             p_l_m VARCHAR(50),
             tekouci VARCHAR(50),
             prikopy VARCHAR(50),
             zatravneni VARCHAR(50),
             eroze VARCHAR(50),
             vel_posun NUMERIC(10,5),
             smer_posun VARCHAR(10),
             b NUMERIC(10,5),
             h_lb NUMERIC(10,5),
             h_pb NUMERIC(10,5),
             m_lb VARCHAR(10),
             m_pb VARCHAR(10),
             foto_kb VARCHAR(10),
             foto_dso VARCHAR(10),
             poznamky VARCHAR(355)
            )"""
    conn.execute(sql)
    arcpy.AddMessage('Byla vytvorena tabulka pasport\n')

#---------ŠESTÁ ČÁST-------------#
conn = db_connection(sde_name)

import_data(kb,sde_name,'kb')
import_data(sberne_plochy,sde_name,'sberne_plochy')

change_data_type(conn,'kb','id_kb')
drop_primary_key(conn,'kb')
add_primary_key(conn,'kb','id_kb')

change_data_type(conn,'sberne_plochy','id_krit_bo')
drop_primary_key(conn,'sberne_plochy')
add_foreign_key(conn,'sberne_plochy','id_krit_bo','kb','id_kb')

keep_fields = ['id_kb','newid','type','dist','shape']
duplicated_fields, transfer_fields = classify_fields(conn,keep_fields)

add_columns(conn,'sberne_plochy',transfer_fields)
update_columns(conn,'sberne_plochy','kb',transfer_fields.keys(),'id_krit_bo','id_kb')
drop_columns(conn,'kb',duplicated_fields+transfer_fields.keys())

create_pasport_table(conn)