#---------PRVNÍ ČÁST-------------#
import arcpy

intra15 = arcpy.GetParameterAsText(0)
intra09 = arcpy.GetParameterAsText(1)

def create_dict(layer):
    """Funkce pro vytvoření slovníku FID : (AREA, defaultní hodnota MID = -1, IID)"""
    dict = {}
    for row in arcpy.da.SearchCursor(layer, ["FID", "AREA"]):
        dict[row[0]] = [row[1], -1, row[0]]
    return(dict)

def import_dict_as_fields(layer,dict):
    """Funkce pro vložení získaných hodnot jako atributy MID, IID"""
    midList = [v for v in dict.values()]  # vytvoření pole ze slovníku
    arcpy.AddField_management(layer, "MID", "LONG")
    arcpy.AddField_management(layer, "IID", "LONG")
    cur = arcpy.UpdateCursor(layer)
    i = 0
    for row in cur:
        row.setValue("MID", midList[i][1])
        row.setValue("IID", midList[i][2])
        cur.updateRow(row)
        i += 1

intersect = arcpy.Intersect_analysis([intra09,intra15],"temp_file","ONLY_FID")
arcpy.AddField_management(intersect,"AREA","DOUBLE")
arcpy.AddField_management(intra15,"AREA","DOUBLE")
arcpy.AddField_management(intra09,"AREA","DOUBLE")
# tvorba průnikové vrstvy a atributu pro výpočet plochy polygonu

arcpy.CalculateField_management(intersect,"AREA","!SHAPE.AREA@SQUAREMETERS!","PYTHON_9.3")
arcpy.CalculateField_management(intra15,"AREA","!SHAPE.AREA@SQUAREMETERS!","PYTHON_9.3")
arcpy.CalculateField_management(intra09,"AREA","!SHAPE.AREA@SQUAREMETERS!","PYTHON_9.3")
# výpočet plochy polygonu

#---------DRUHÁ ČÁST-------------#
dict15 = create_dict(intra15)
dict09 = create_dict(intra09)

for row in arcpy.da.SearchCursor(intersect,["FID_"+intra15,"FID_"+intra09,"AREA"]):
    fid15 = row[0]
    fid09 = row[1]
    areaI = row[2]
    
    area15 = dict15[fid15][0]
    area09 = dict09[fid09][0]

    if (areaI / area15) > 0.5:
        dict15[fid15][1] = fid09

    if (areaI / area09) > 0.5:
        dict09[fid09][1] = fid15
# procházení všech průnikových polygonů

import_dict_as_fields(intra15,dict15)
import_dict_as_fields(intra09,dict09)

arcpy.Delete_management(intersect)
# úklid temp_file