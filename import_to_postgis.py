#---------PRVNÍ ČÁST-------------#
import arcpy, os, zipfile

file = arcpy.GetParameterAsText(0)
sde_name = arcpy.GetParameterAsText(1)

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

def unzip(file):
    """Funkce pro rozbalení vstupního souboru"""
    path, ext = os.path.splitext(file)
    if ext == '.zip':
        zip = zipfile.ZipFile(file)
        zip.extractall()
        zip.close()
        arcpy.AddMessage('Soubor ' + file + ' byl rozzipovan')
        shp_file = path.replace('shpshp', 'shp.shp') #vytvoření koncovky .shp
        return(shp_file)
    return(file)

#---------DRUHÁ ČÁST-------------#
def get_fields_to_import(file):
    """Funkce pro získání názvů atributů pro import do PostGIS"""
    status = False
    fields = []
    for f in arcpy.ListFields(file):
        if f.name == 'id_kb':
            status = True
        if status:
            fields.append(f.name)
    return(fields)

def row_to_string(row):
    """Funkce pro vytvoření řetězce z hodnot řádku atributové tabulky"""
    string = ''
    for i in row:
        if type(i) is float:
            string += str(i) + ','
        else:
            string += "'" + i + "',"
    return(string[0:-1])

def import_data(conn,shp_file,table):
    """Funkce pro import dat z shapefile do PostGIS"""
    fields = get_fields_to_import(shp_file)
    sql = 'INSERT INTO ' + table + ' VALUES'
    for row in arcpy.da.SearchCursor(shp_file, fields):
        sql += '\n(' + row_to_string(row) + '),'
    sql = sql[0:-1]
    conn.execute(sql)
    arcpy.AddMessage('Soubor '+shp_file+' byl naimportovan jako tabulka '+table+'\n')

#---------TŘETÍ ČÁST-------------#
def del_unzip_shp(file):
    """Funkce pro smazání rozbaleného shapefile souboru"""
    path, ext = os.path.splitext(file)
    if ext == '.zip':
        shp_file = path.replace('shpshp', 'shp.shp') #vytvoření koncovky .shp
        arcpy.Delete_management(shp_file)
        arcpy.AddMessage('Rozbaleny soubor ' + shp_file + ' byl smazan\n')

conn = db_connection(sde_name)
shp_file = unzip(file)
import_data(conn,shp_file,'pasport')
del_unzip_shp(file)


def get_postgis_coords(conn,table):
    sql = 'SELECT id_kb, ST_X(shape), ST_Y(shape) FROM ' + table
    raw_output = conn.execute(sql)
    coords = {}
    for item in raw_output:
        coords[item[0]] = [item[1],item[2]]
    return(coords)