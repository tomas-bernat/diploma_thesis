#---------PRVNÍ ČÁST-------------#
import arcpy
from math import sqrt

kb15 = arcpy.GetParameterAsText(0)
kb09 = arcpy.GetParameterAsText(1)
DSO = arcpy.GetParameterAsText(2)

def distance(A,B):
    """Funkce pro výpočet vzdálenosti [m] mezi dvěma body"""
    dx = (A[0]-B[0])
    dy = (A[1]-B[1])
    d = sqrt(dx**2+dy**2)
    return(d)

#---------DRUHÁ ČÁST-------------#
def code(hid, dict):
    """Funkce pro vytvoření kódu daného hid (HydroID) a doplnění jej do slovníku dict"""
    input_hid = hid  # vstupní hid
    next = dict[hid][0]  # id následující linie
    code = "." + str(hid) + "." # iniciální tvorba kódu
    while next != -1:  # dokud se algoritmus nedostane až na konec sítě
        code += str(next) + "."  # postupné rozšiřování kódu
        hid = next
        next = dict[hid][0]
    dict[input_hid][1] = code  # doplnění kódu do slovníku

def intra_test(iidA,midA,iidB,midB):
    """Funkce pro určení, zda jeden polygon intravilánu leží z většiny v druhém"""
    if midA == iidB or midB == iidA:
        return True
    else:
        return False

def dso_test(A,B):
    """Funkce pro určení, zda jsou dvě linie DSO navzájem následné"""
    if (A in B) or (B in A):
        return True
    else:
        return False

def import_array_as_fields(layer,array):
    """Funkce pro vložení získaných hodnot jako atributy NEWID, TYPE, DIST"""
    arcpy.AddField_management(layer, "NEWID", "TEXT")
    arcpy.AddField_management(layer, "TYPE", "TEXT")
    arcpy.AddField_management(layer, "DIST", "DOUBLE")
    cur = arcpy.UpdateCursor(layer)
    i = 0
    for row in cur:
        row.setValue("NEWID", array[i][0])
        row.setValue("TYPE", array[i][4])
        row.setValue("DIST", array[i][6])
        cur.updateRow(row)
        i += 1

#---------TŘETÍ ČÁST-------------#
dict_DSO = {}
for row in arcpy.da.SearchCursor(DSO, ["HydroID", "NextDownID"]):
    dict_DSO[row[0]] = [row[1], ""]
# vytvoření slovníku HydroID : (NextDownID, "prázdný prostor pro kód" )

for hid in dict_DSO:
    code(hid, dict_DSO)
# aplikace funkce code pro celý slovník

for row in arcpy.da.SearchCursor(DSO,["HydroID","FID"]):
    dict_DSO[row[1]] = dict_DSO.pop(row[0])
# přepis HydroID na FID

arcpy.Near_analysis (kb15,DSO)
arcpy.Near_analysis (kb09,DSO)
# přiřazení FID DSO k danému kritickému bodu

#---------ČTVRTÁ ČÁST-------------#
array09 = []
for row in arcpy.da.SearchCursor(kb09,["TARGET_FID","IID","MID","NEAR_FID","SHAPE@XY"]):
    newid = str(row[0])
    iid = row[1]
    mid = row[2]
    code = dict_DSO[row[3]][1]
    type = ''
    coords = row[4]
    dist = -1
    array09.append([newid,iid,mid,code,type,coords,dist])
# iniciální tvorba array09

#---------PÁTÁ ČÁST-------------#
array15, D_array09, S_array09 = [], [], []
for row in arcpy.da.SearchCursor(kb15,["IID","MID","NEAR_FID","SHAPE@XY"]):
    ident = ''
    iid = row[0]
    mid = row[1]
    code = dict_DSO[row[2]][1]
    type = ''
    coords = row[3]
    dist = -1
    for i in range(len(array09)):
        if intra_test(iid,mid,array09[i][1],array09[i][2])and dso_test(code,array09[i][3]):
            # přiřazování kb09 ku kb15
            dist = distance(coords, array09[i][5])
            array09[i][6] = dist
            if ident == '':
                ident = array09[i][0]
            else:
                ident = ident + '_' + array09[i][0]
    if ident == '':
        # nenalezen ekvivalentní kb09, vytvořeno nové číslo identifikátoru
        newid = str(int(newid) + 1)
        ident = newid
        type = 'N'
    else:
        if '_' in ident:
            # nalezeno více ekvivalentních kb09
            type = 'D'
            dist = -1
            for number in ident.split('_'):
                D_array09.append(number)
        else:
            # nalezen právě jeden ekvivalentní kb09
            type = 'S'
            S_array09.append(ident)
    array15.append([ident,iid,mid,code,type,coords,dist])
# iniciální tvorba array15

#---------ŠESTÁ ČÁST-------------#
for i in range(len(array09)):
    if array09[i][0] in D_array09:
        # zpětné přiřazování typu D
        array09[i][4] = 'D'
    elif array09[i][0] in S_array09:
        # zpětné přiřazování typu S
        array09[i][4] = 'S'
        I_indexes = []
        for j in range(len(array15)):
            if array09[i][0] == array15[j][0]:
                I_indexes.append(j)
        if len(I_indexes)>1:
            # přepis na typ I
            array09[i][4] = 'I'
            array09[i][6] = -1
            for j in range(len(I_indexes)):
                I_index = I_indexes[j]
                array15[I_index][0] += chr(97+j)
                array15[I_index][4] = 'I'
    else:
        # nenalezen ekvivalentní kb15
        array09[i][4] = 'R'
# doplnění a úprava pole array09 i array15

import_array_as_fields(kb15,array15)
import_array_as_fields(kb09,array09)