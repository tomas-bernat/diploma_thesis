#---------PRVNÍ ČÁST-------------#
import arcpy, zipfile
from os import listdir
from os.path import isfile, join
from dateutil.parser import parse

kb = arcpy.GetParameterAsText(0)
sde_name = arcpy.GetParameterAsText(1)
username = arcpy.GetParameterAsText(2)
date = parse(arcpy.GetParameterAsText(3))
folder = arcpy.GetParameterAsText(4)

filename = username + '_' + date.strftime('%Y%m%d')

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

#---------DRUHÁ ČÁST-------------#
def add_layer(filepath):
    """Funkce pro přidání vrstvy do aktuálního MXD projektu"""
    df = arcpy.mapping.MapDocument("CURRENT").activeDataFrame
    layer = arcpy.mapping.Layer(filepath)
    arcpy.mapping.AddLayer(df, layer, "TOP")

def export_data(table,filename,folder):
    """Funkce pro export dat z PostGIS do SHP v souřadnicovém systému WGS84"""
    crs = arcpy.SpatialReference(4326)
    filepath = join(folder,filename + '.shp')
    temp_file = arcpy.Project_management(table,filepath,crs)
    arcpy.AddMessage('Vytvoren shapefile ' + filename + '.shp')
    add_layer(filepath)
    return(temp_file)

def get_table_fields(conn,table):
    """Funkce pro získání pole s názvy sloupců a jejich datovými typy"""
    sql = """SELECT column_name, udt_name
             FROM information_schema.columns WHERE table_name = '"""+table+"'"
    raw_output = conn.execute(sql)
    dict = {'varchar': 'TEXT', 'numeric': 'DOUBLE', 'timestamp': 'DATE'}
    # převod mezi datovými typy SQL a SHP
    output = []
    for item in raw_output:
        name = item[0]
        if name != 'id_kb': #already exist
            data_type = dict[item[1]]
            output.append([name,data_type])
    return(output)

#---------TŘETÍ ČÁST-------------#
def delete_useless_fields(filename):
    """Funkce pro smazání nepotřebných atributů"""
    useless_fields = [f.name for f in arcpy.ListFields(filename)
                      if f.required == False and f.name != 'id_kb']
    arcpy.DeleteField_management(filename, useless_fields)
    arcpy.AddMessage('Smazany nepotrebne atributy ' + str(useless_fields))

def add_fields(filename,pasport_fields):
    """Funkce pro vytvoření nových atributů"""
    for f in pasport_fields:
        arcpy.AddField_management(filename, f[0],f[1])
    arcpy.AddMessage('Pridany atributy ' + str(pasport_fields))

def fill_fields(filename,date,username):
    """Funkce pro vyplnění atributů id_kb, pasport_id, zpracoval, datum_cas"""
    cur = arcpy.UpdateCursor(filename)
    for row in cur:
        pasport_id = row.getValue('id_kb') + date.strftime('%Y%m%d')
        row.setValue('pasport_id',pasport_id)
        row.setValue('zpracoval',username)
        row.setValue('datum_cas', date.strftime('%d.%m.%Y %H:%M'))
        cur.updateRow(row)
    arcpy.AddMessage('Vyplneny atributy id_kb, pasport_id, zpracoval, datum_cas')

def manage_fields(filename,pasport_fields,date,username):
    """Funkce pro aplikaci smazání nepotřebných atributů,
       přidání nových atributů a naplnění některých z nich"""
    delete_useless_fields(filename)
    add_fields(filename,pasport_fields)
    fill_fields(filename, date, username)

#---------ČTVRTÁ ČÁST-------------#
def zip_and_delete(filename,folder,temp_file):
    """Funkce pro vytvoření ZIP z SHP a následné smazání SHP"""
    files = [f for f in listdir(folder) if isfile(join(folder, f))]
    with zipfile.ZipFile(join(folder,filename+'.zip'), "w", zipfile.ZIP_DEFLATED) as zip:
        for f in files:
            name, extension = f.split('.')[0], f.split('.')[-1] 
            if name == filename and extension != 'lock':
                file = join(folder,f)
                zip.write(file,f)
    arcpy.AddMessage('Vytvoreny ZIP ' + filename + '.zip')
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = mxd.activeDataFrame
    layer = arcpy.mapping.ListLayers(mxd,'', df)[0]
    arcpy.mapping.RemoveLayer(df,layer) # smazání vrstvy z aktuálního MXD projektu
    arcpy.Delete_management(temp_file)
    arcpy.AddMessage('Smazan jiz nepotrebny shapefile ' + filename + '.shp\n')

conn = db_connection(sde_name)
temp_file = export_data(kb,filename,folder)
pasport_fields = get_table_fields(conn,'pasport')
manage_fields(filename,pasport_fields,date,username)
zip_and_delete(filename,folder,temp_file)