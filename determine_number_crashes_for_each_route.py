import arcpy
import os
import csv


def aggregate_by_route_by_injury_type(route_fc, crash_fc, gdb, distance):
    arcpy.env.workspace = gdb
    route_dictionary = {}
    for row in arcpy.da.SearchCursor(route_fc, ["ROUTE_TOM", "AGENCY"]):
        route = row[0]
        agency = row[1]
        if (route, agency) not in route_dictionary:
            route_dictionary[(route, agency)] = {}
        current_layer = os.path.join(gdb, "current")
        sql_query = "\"ROUTE_TOM\" = '" + str(route) + "' AND \"AGENCY\" = '" + agency + "'"
        arcpy.MakeFeatureLayer_management(route_fc, current_layer, sql_query)
        arcpy.MakeFeatureLayer_management(crash_fc, "crashes")
        arcpy.SelectLayerByLocation_management("crashes", "WITHIN_A_DISTANCE", current_layer, distance, "NEW_SELECTION")
        selected_crashes = os.path.join(gdb, "selected")
        arcpy.CopyFeatures_management("crashes", selected_crashes)

        for row2 in arcpy.da.SearchCursor(selected_crashes, ["INJY_STAT_DESCR"]):
            if row2[0] not in route_dictionary[(route, agency)]:
                route_dictionary[(route, agency)][row2[0]] = 1
            else:
                route_dictionary[(route, agency)][row2[0]] += 1

        arcpy.Delete_management(current_layer)
        arcpy.Delete_management("crashes")
        arcpy.Delete_management(selected_crashes)
    return route_dictionary


def write_results_to_text_file(route_dictionary, output_path):
    with open(output_path, "wb") as text_file:
        writer = csv.writer(text_file, delimiter="\t")
        legend = ["Bus Route", "Agency", "Injury Type", "Count"]
        writer.writerow(legend)
        for (route, agency) in route_dictionary:
            for injury in route_dictionary[(route, agency)]:
                row = [route, agency, injury, route_dictionary[(route, agency)][injury]]
                writer.writerow(row)
    del text_file


def write_results_to_gis_feature_class(route_dictionary, gis_fc):
    injury_type_list = ["Fatal injury", "Non-fatal injury - Incapacitating", "Non-fatal injury - Non-incapacitating",
                        "Non - fatal injury - Possible"]
    for i in injury_type_list:
        arcpy.AddField_management(gis_fc, i, "SHORT")
    arcpy.AddField_management(gis_fc, "EPDO", "LONG")
    fields = ["ROUTE_TOM", "AGENCY", "EPDO"] + [i.replace(" ", "_").replace("-", "_") for i in injury_type_list]
    with arcpy.da.UpdateCursor(gis_fc, fields) as cursor:
        for row in cursor:
            key = (row[0], row[1])
            if key in route_dictionary:
                total = 0
                for inj in injury_type_list:
                    if inj in route_dictionary[key]:
                        total += (route_dictionary[key][inj] * 10 if inj == "Fatal injury" else route_dictionary[key][inj] * 5)
                        injury = inj.replace(" ", "_").replace("-", "_")
                        row[fields.index(injury)] = route_dictionary[key][inj]
                row[2] = total
                cursor.updateRow(row)
    del cursor
    return

buses_fc = r"U:\Projects\Tasks_For_Bonnie\Bicyclist_Bus_Routes_092116\bicyclist_bus_routes_092116.gdb\MBTA_Bus_Routes"
crashes_fc = r"U:\Projects\Tasks_For_Bonnie\Bicyclist_Bus_Routes_092116\bicyclist_bus_routes_092116.gdb\bicyclist_crashes_with_mbta_120516"
geodatabase = r"U:\Projects\Tasks_For_Bonnie\Bicyclist_Bus_Routes_092116\output.gdb"
out_file = os.path.join(r"U:\Projects\Tasks_For_Bonnie\Bicyclist_Bus_Routes_092116", "Bicyclist Route Crashes MBTA - 120716.txt")

route_dict = aggregate_by_route_by_injury_type(buses_fc, crashes_fc, geodatabase, "50 Feet")
write_results_to_text_file(route_dict, out_file)
write_results_to_gis_feature_class(route_dict, buses_fc)
