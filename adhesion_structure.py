import pandas as pd
import random
import math
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry.polygon import LinearRing, Polygon, Point
from maxrect import get_intersection, get_maximal_rectangle, rect2poly


def heating_top_layer(file_name, layer_no):
    """
    after changing the filament,
    moves nozzle without extrusion to heat the previous layer.
    :param layer_no: target layer number
    :return: null
    """
    gcode = open(file_name, "r")
    pause = open("pause_code.txt","r")
    pauselines = pause.readlines()
    pausecode =""
    lines = gcode.readlines()
    layer_count = 0
    flag = "no"

    i = 0
    head = ""
    after_half_layer = ""
    half_layer = ""
    replaced = ""
    layer_flag = "no"
    goback = ""
    goback2 = ""

    # Get pausecode
    for p in pauselines:
        pausecode += p

    # Get total layer count
    for i in range(len(lines)):

        if ";LAYER_COUNT:" in lines[i]:
            countline = lines[i].split(":")
            layer_count = int(countline[1])
    # Get header part of code
    for l in lines:

        if ";LAYER:" + str(int(layer_no)) + "\n" in l:
            break
        else:
            head += l

    # Get layer to be repeated and remove the E commands
    for i in range(len(lines)):
        if ";LAYER:"+str(int(layer_no)) + "\n" in lines[i]:
            flag = "yes"

        elif ";LAYER:" in lines[i]:
            flag = "no"


        if flag == "yes":
            half_layer += lines[i]
            # Get co-ordinates of where the extruder paused and Z height
            if "Z" in lines[i]:
                split_goback = lines[i].split(" ")

                for j in range(len(split_goback)):
                    if "F" in split_goback[j]:
                        split_goback[j] = "F6000"
                    goback2 += split_goback[j] + " "
                    if "Z" in split_goback[j]:
                        current_z = float(split_goback[j].split("Z")[1])
                        new_z = current_z - 0.2
                        split_goback[j] = "Z"+str(new_z)
                    goback += split_goback[j] + " "

            split_layer = lines[i].split(" ")

            for k in range(len(split_layer)):
                if "E" in split_layer[k]:
                    split_layer[k]="\n"

            for j in range(len(split_layer)):
                replaced += split_layer[j] + " "



    #Get rest of the code
    for i in range(len(lines)):
        if ";LAYER:"+str(int(layer_no)+1) in lines[i]:
            layer_flag = "yes"
        if layer_flag == "yes":
            after_half_layer += lines[i]


    #print(layer_no)
    newcode = open(file_name.split(".gcode")[0] +"_heating.gcode", "wt")
    #withoutheat = open("dogbonewithoutheat.gcode", "wt")
    n = newcode.write(head + half_layer + pausecode + "\n" + goback + "\n" + "\n;REPEAT LAYER\n"+ replaced + after_half_layer)
    #m = withoutheat.write(head + half_layer + pausecode + "\n" + goback2 + "\n" + after_half_layer)
    #withoutheat.close()
    #newcode.close()


def get_min_max(input_list):
    '''
    get minimum and maximum value in the list
    :param input_list: list of numbers
    :return: min, max
    '''

    min_value = input_list[0]
    max_value = input_list[0]

    for i in input_list:
        if i > max_value:
            max_value = i
        elif i < min_value:
            min_value = i

    return min_value, max_value


def get_largest_polygon(x_values, y_values):
    '''
    Get the largest polygon among multiple polygons (if exist)
    :param x_values: a list of all x coordinates in infill
    :param y_values: a list of all y coordinates in infill
    :return: the list of x-y coordinates of the largest polygon
    '''

    areas = []
    polygon_coords = []

    all_polygons = []

    for i in range(len(x_values)):
        if x_values[i] == "G0":  # next polygon
            if len(polygon_coords) != 0:
                areas.append(Polygon(polygon_coords).area)
                all_polygons.append(polygon_coords)
                polygon_coords = []
        else:
            polygon_coords.append([x_values[i], y_values[i]])

    max_area = areas[0]
    max_index = 0

    #print(areas)

    for i in range(len(areas)):
        if areas[i] > max_area:
            max_area = areas[i]
            max_index = i

    return all_polygons[max_index]


def is_far_from_inner_wall(x, y, x_values, y_values, threshold):
    """
    determine if the point is fairly distant from points on polygon
    :param x: point_x
    :param y: point_y
    :param x_values: x coordinates of polygon
    :param y_values: y coordinates of polygon
    :param threshold: maximum distance
    :return: true or false
    """

    for k in range(len(x_values)):
        if math.hypot(x - x_values[k], y - y_values[k]) < threshold:
            return False

    return True


def get_grid_points_for_target_layer(file, target_layer, gap):
    '''
    get grid points inside infill on the target layer
    :param file: gcode file location
    :param target_layer: target layer number
    :param gap: gap between grid points (mm)
    :return: lists of x coordinates and y coordinates of a-structure and b-structure
    '''

    gcode = open(file)

    lines = gcode.readlines()

    is_target = 0
    is_inner_wall = 0

    target_lines = ""

    for l in lines:
        if is_target == 1 and is_inner_wall == 1 and ";TYPE:WALL-OUTER" in l:
            break
        if ";LAYER:" + str(target_layer)+"\n" in l:  # target layer
            is_target = 1
            target_lines += l
        if is_target == 1 and ";TYPE:WALL-INNER" in l:
            is_inner_wall = 1
        if is_target == 1 and is_inner_wall == 1:
            target_lines += l

    x_values = []
    y_values = []

    for l in target_lines.split("\n"):
        if "G1" in l:
            elems = l.split(" ")

            for e in elems:
                if ";" not in e:
                    if "X" in e:
                        x_values.append(float(e.split("X")[1]))
                    if "Y" in e:
                        y_values.append(float(e.split("Y")[1]))

        elif "G0" in l:  # flag that indicates the next polygon
            x_values.append("G0")
            y_values.append("G0")

    polygon_coords = get_largest_polygon(x_values, y_values)

    polygon_coords.append(polygon_coords[0])

    #print(polygon_coords)

    x_values = []
    y_values = []

    for i in range(len(polygon_coords)):
        x_values.append(polygon_coords[i][0])
        y_values.append(polygon_coords[i][1])

    #print(polygon.area)

    x_min, x_max = get_min_max(x_values)
    y_min, y_max = get_min_max(y_values)

    grid_x = []
    grid_y = []

    current_x = x_min + gap / 2.2
    current_y = y_min + gap / 2.2
    #print(x_min)
    #print(y_min)

    grid_x.append(current_x)
    grid_y.append(current_y)

    while current_x <= x_max:
        current_x += gap
        grid_x.append(current_x)
    while current_y <= y_max:
        current_y += gap
        grid_y.append(current_y)

    #print(grid_x)
    #print(grid_y)

    # a structure
    a_x = []
    a_y = []

    polygon = Polygon(polygon_coords)

    for i in range(len(grid_x)):
        for j in range(len(grid_y)):
            current_point = Point(grid_x[i], grid_y[j])

            if polygon.contains(current_point):

                if is_far_from_inner_wall(current_point.x, current_point.y, x_values, y_values, threshold=1):
                    a_x.append(current_point.x)
                    a_y.append(current_point.y)

    a_coords = []  # coordinates of a structure

    for i in range(len(a_x)):
        a_coords.append([a_x[i], a_y[i]])

    #print(a_coords)

    #print(sorted(a_coords, key=lambda x: x[1]))

    # x and y values for b structure
    b_x = []
    b_y = []

    # check if the unit square is included in the polygon
    for i in range(len(a_coords)):
        if unit_square_is_included(a_coords[i], gap, a_coords):
            b_x.append(a_coords[i][0] + gap/2)
            b_y.append(a_coords[i][1] + gap/2)


    #plt.plot(x_values, y_values, 'ro')
    #plt.plot(a_x, a_y, 'bo')
    #plt.plot(b_x, b_y, 'go')
    #plt.show()

    return a_x, a_y, b_x, b_y


def generate_grid_infill(a_x, a_y, b_x, b_y, gap):

    arbitrary = 0.08  # arbitrary number to optimize extrusion amount

    # a-structure

    g0 = "G0 F9500 "
    g1 = "G1 F2000 "

    a_structure = ""

    layer_height = 0.2
    nozzle_dia = 0.4
    length = gap
    fa = ((1.75/2) ** 2) / math.pi

    extrusion = (layer_height * nozzle_dia * length * arbitrary) / fa

    a_structure += g0 + "X" + str(a_x[0]) + " Y" + str(a_y[0]) + "\n"

    a_final = get_zig_zag_for_lines(a_x, a_y)

    for i in range(len(a_x)):
        if i + 1 < len(a_x):
            if a_final[i + 1][0] == a_final[i][0]:  # at the same line (y-axis)
                a_structure += g1 + "X" + str(a_final[i + 1][0]) + " Y" + str(a_final[i + 1][1]) + " E" + str(
                    extrusion) + "\n"
            elif a_final[i + 1][0] > a_final[i][0]:  # next line
                a_structure += g0 + "X" + str(a_final[i + 1][0]) + " Y" + str(a_final[i + 1][1]) + "\n"

    a_structure += g0 + "X" + str(a_final[0][0]) + " Y" + str(a_final[0][1]) + "\n"

    a_coords = []  # coordinates of a structure

    for i in range(len(a_x)):
        a_coords.append([a_x[i], a_y[i]])

    y_sorted = sorted(a_coords, key=lambda k: k[1])

    a_structure += g0 + "X" + str(a_x[0]) + " Y" + str(a_y[0]) + "\n"

    #print(y_sorted)

    v_x = []
    v_y = []

    for i in range(len(y_sorted)):
        v_x.append(y_sorted[i][0])
        v_y.append(y_sorted[i][1])

    v_final = get_zig_zag_for_lines_for_y(v_x, v_y)

    for i in range(len(v_final)):
        if i + 1 < len(v_final):
            if v_final[i + 1][1] == v_final[i][1]:  # at the same line (x-axis)
                a_structure += g1 + "X" + str(v_final[i + 1][0]) + " Y" + str(v_final[i + 1][1]) + " E" + str(extrusion) + "\n"
            elif a_x[i + 1] > a_x[i]:  # next line
                a_structure += g0 + "X" + str(v_final[i + 1][0]) + " Y" + str(v_final[i + 1][1]) + "\n"

    # b-structure
    b_structure = ""

    filling = 0.9  # optimized amount (by experiments) of extrusion for filling empty spaces of grid

    g0 = "G0 F9500 "
    g1 = "G1 F50 "

    count = 0

    for i in range(len(b_x)):
        count += 1
        b_structure += g0 + "X" + str(b_x[i]) + " Y" + str(b_y[i]) + "\n"
        b_structure += g1 + "X" + str(b_x[i]) + " Y" + str(b_y[i]) + " E" + str(filling) + "\n"

    return a_structure, b_structure


def get_zig_zag_for_lines(x, y):

    final = []
    line = []

    line.append([x[0], y[0]])

    for i in range(len(x) - 1):
        if x[i + 1] == x[i]:  # at the same line
            line.append([x[i + 1], y[i + 1]])
        elif x[i + 1] > x[i]:  # next line
            if len(final) % 2 == 0:
                final.append(line)
                line = []
            else:
                line.reverse()
                final.append(line)
                line = []
            line.append([x[i+1], y[i+1]])

    line.append([x[-1], y[-1]])
    if len(final) % 2 == 0:
        final.append(line)
    else:
        line.reverse()
        final.append(line)

    result = []

    for f in final:
        for i in f:
            result.append(i)

    return result


def get_zig_zag_for_lines_for_y(x, y):

    final = []
    line = []

    line.append([x[0], y[0]])

    for i in range(len(y) - 1):
        if y[i + 1] == y[i]:  # at the same line
            line.append([x[i + 1], y[i + 1]])
        elif y[i + 1] > y[i]:  # next line
            if len(final) % 2 == 0:
                final.append(line)
                line = []
            else:
                line.reverse()
                final.append(line)
                line = []
            line.append([x[i+1], y[i+1]])

    line.append([x[-1], y[-1]])
    if len(final) % 2 == 0:
        final.append(line)
    else:
        line.reverse()
        final.append(line)

    result = []

    for f in final:
        for i in f:
            result.append(i)

    return result


def generate_blob_infill(a_x, a_y, b_x, b_y, gap, file_name, target_layer):

    gcode = open(file_name)

    lines = gcode.readlines()

    current_z = 0
    new_z = 0

    target_z = "no"

    # get Z value
    for i in range(len(lines)):
        if ";LAYER:" + str(target_layer) + "\n" in lines[i]:  # target layer
            target_z = "yes"
        elif ";LAYER" in lines[i]:
            target_z = "no"

        if target_z == "yes":
            # print(lines[i])
            if "Z" in lines[i]:
                #print(lines[i])
                splitline = lines[i].split(" ")
                for j in range(len(splitline)):
                    if "Z" in splitline[j]:
                        if splitline[j].split("Z")[1] == '':
                            break
                        else:
                            current_z = float(splitline[j].split("Z")[1])
                            current_z -= 0.2
                            new_z = current_z + 0.4

    a_final = get_zig_zag_for_lines(a_x, a_y)

    b_final = get_zig_zag_for_lines(b_x, b_y)

    #print(a_final)
    #print(b_final)

    # a-structure
    g0 = "G0 F9500 "
    g1 = "G1 F9500 "

    a_structure = ""
    b_structure = ""

    extrusion = 0.7  # extrusion amount optimized by experiment

    for i in range(len(a_final)):
        if i + 1 < len(a_final):
            a_structure += g1 + "X" + str(a_final[i][0]) + " Y" + str(a_final[i][1]) + " E" + str(extrusion) + "\n"
            a_structure += g0 + "X" + str(a_final[i][0]) + " Y" + str(a_final[i][1]) + " Z" + str(new_z) + "\n"
            a_structure += g0 + "X" + str(a_final[i][0]) + " Y" + str(a_final[i + 1][1]) + " Z" + str(current_z) + "\n"

    a_structure += g1 + "X" + str(a_final[-1][0]) + " Y" + str(a_final[-1][1]) + " E" + str(extrusion) + "\n"
    a_structure += g0 + "X" + str(a_final[-1][0]) + " Y" + str(a_final[-1][1]) + " Z" + str(new_z) + "\n"

    for i in range(len(b_final)):
        if i + 1 < len(b_final):
            b_structure += g1 + "X" + str(b_final[i][0]) + " Y" + str(b_final[i][1]) + " E" + str(extrusion) + "\n"
            b_structure += g0 + "X" + str(b_final[i][0]) + " Y" + str(b_final[i][1]) + " Z" + str(new_z) + "\n"
            b_structure += g0 + "X" + str(b_final[i + 1][0]) + " Y" + str(b_final[i][1]) + " Z" + str(current_z) + "\n"

    b_structure += g1 + "X" + str(b_final[-1][0]) + " Y" + str(b_final[-1][1]) + " E" + str(extrusion) + "\n"
    b_structure += g0 + "X" + str(b_final[-1][0]) + " Y" + str(b_final[-1][1]) + " Z" + str(new_z) + "\n"

    return a_structure, b_structure


def generate_full_infill(a_x, a_y, gap=0.2):

    arbitrary = 0.4  # arbitrary number to optimize extrusion amount

    # a-structure

    g0 = "G0 F9500 "
    g1 = "G1 F2000 "

    a_structure = ""

    layer_height = 0.2
    nozzle_dia = 0.4
    length = gap
    fa = ((1.75 / 2) ** 2) / math.pi

    extrusion = (layer_height * nozzle_dia * length * arbitrary) / fa

    a_structure += g0 + "X" + str(a_x[0]) + " Y" + str(a_y[0]) + "\n"

    for i in range(len(a_x)):
        if i + 1 < len(a_x):
            if a_x[i + 1] == a_x[i]:  # at the same line (y-axis)
                a_structure += g1 + "X" + str(a_x[i + 1]) + " Y" + str(a_y[i + 1]) + " E" + str(extrusion) + "\n"
            elif a_x[i + 1] > a_x[i]:  # next line
                a_structure += g0 + "X" + str(a_x[i + 1]) + " Y" + str(a_y[i + 1]) + "\n"

    a_structure += g0 + "X" + str(a_x[0]) + " Y" + str(a_y[0]) + "\n"

    return a_structure


def replace_infill_to_adhesion_structure(file_name, target_layer, type, flag):
    '''
    replace infill of the target layer to adhesion structure
    :param file_name: location of source gcode file
    :param target_layer: target layer
    :param type: type of adhesion structure
    :return: null
    '''

    gcode = open(file_name)

    pause_code = open("./pause_code.txt").readlines()

    lines = gcode.readlines()

    if type == "grid":
        gap = 2
        a_x, a_y, b_x, b_y = get_grid_points_for_target_layer(file_name, target_layer, gap)
        f_x, f_y, unused1, unused1 = get_grid_points_for_target_layer(file_name, target_layer, gap=0.6)
        a_structure, b_structure = generate_grid_infill(a_x, a_y, b_x, b_y, gap)
        full_structure = generate_full_infill(f_x, f_y)
    elif type == "blob":
        gap = 2
        a_x, a_y, b_x, b_y = get_grid_points_for_target_layer(file_name, target_layer, gap)
        f_x, f_y, unused1, unused1 = get_grid_points_for_target_layer(file_name, target_layer, gap=0.6)
        a_structure, b_structure = generate_blob_infill(a_x, a_y, b_x, b_y, gap, file_name, target_layer)
        full_structure = generate_full_infill(f_x, f_y)

    is_target = 0
    is_mesh = 0

    mesh = ""

    pop_list = []
    index = 0
    # get mesh code of the target layer
    for l in lines:
        if ";LAYER:" + str(target_layer) + "\n" in l:
            is_target = 1
        if ";MESH:NONMESH" in l and is_target == 1:
            is_mesh = 1

        if is_target == 1 and is_mesh == 1:
            if ";TIME_ELAPSED:" in l:
                break
            mesh += l
            pop_list.append(index)

        index += 1

    lines_a = lines
    lines = []
    for i in range(len(lines_a)):
        if i not in pop_list:
            lines.append(lines_a[i])

    mesh_f_replaced = ""

    for m in mesh.split("\n"):
        if "F300" in m:
            m = m.replace("F300", "F9500")
        if "Z" in m and type == "blob":
            z = m.split("Z")[1]
            new_z = float(z) - 0.2
            m = m.replace("Z"+str(z), "Z"+str(round(new_z, 2)))
        mesh_f_replaced += m + "\n"

    is_target = 0
    is_infill = 0

    modified = ""

    is_b = 0

    mesh_each = ""
    is_mesh = 0

    target_layers = [target_layer - 2, target_layer -  1, target_layer, target_layer + 1]

    # grid structure
    if type == "grid":
        layer = 0
        for l in lines:
            # generate grid structure for 4 layers including target layer
            if ";LAYER:" + str(target_layer - 2) + "\n" in l \
                    or ";LAYER:" + str(target_layer - 1) + "\n" in l \
                    or ";LAYER:" + str(target_layer) + "\n" in l \
                    or ";LAYER:" + str(target_layer + 1) + "\n" in l:  # target layer
                #is_target = 1
                layer = int(l.split(":")[1].strip())
                if ";LAYER:" + str(target_layer + 1) + "\n" in l:
                    is_b = 1
                    #layer = 0
                #if ";LAYER:" + str(target_layer) + "\n" in l:
                #    layer = target_layer
            if is_target == 1 and ";TYPE:FILL" in l:
                modified += l
                is_infill = 1
            if is_target == 1 and ";TYPE:SKIN" in l:
                modified += l
                is_infill = 1
            if is_target == 1 and ";MESH:" in l:
                is_mesh = 1
                #mesh_each += l

            if is_mesh == 1 and is_target == 1:
                mesh_each += l

            if ";MESH:" in l and is_infill == 1 and layer in target_layers:
                is_mesh = 0
                #is_target = 0
                is_infill = 0
                if is_b == 0:  # a structure

                    modified += ";TYPE:A-STRUCTURE\n" + a_structure
                    modified += mesh_each
                    #print(mesh_each)
                    mesh_each = ""
                    if layer == target_layer:
                        modified += "\n"
                        modified += mesh + "\n"
                        modified += "\n"
                        for p in pause_code:
                            modified += p
                        modified += "\n"
                        modified += mesh_f_replaced + "\n"
                else:
                    modified += ";TYPE:B-STRUCTURE\n" + b_structure
                    modified += ";TYPE:FULL-IN-B-STRUCTURE\n" + full_structure
                    modified += mesh_each
                    mesh_each = ""
                    is_mesh = 0
                    is_b = 0
                #modified += ";MESH:NONMESH\n"
            #elif is_target == 1 and is_infill == 1:
            #    pass
            else:
                modified += l

        structured = modified.split("\n")

        final = ""

        for l in structured:
            l += "\n"
            if ";LAYER:" + str(target_layer - 3) + "\n" in l \
                    or ";LAYER:" + str(target_layer + 2) + "\n" in l:  # target layer
                is_target = 1

            if is_target == 1 and ";TYPE:FILL" in l:
                final += l
                is_infill = 1
            if is_target == 1 and ";TYPE:SKIN" in l:
                modified += l
                is_infill = 1

            if ";MESH:NONMESH" in l and is_target == 1 and is_infill == 1:
                is_target = 0
                is_infill = 0
                final += ";TYPE:FULL-INFILL\n" + full_structure
            elif is_target == 1 and is_infill == 1:
                pass
            else:
                final += l

        if flag == 0:
            with open(file_name.split(".gcode")[0] + "_grid.gcode", "w") as f:
                f.write(final)
        elif flag == 1:
            with open(file_name, "w") as f:
                f.write(final)

    # blob structure
    elif type == "blob":
        # add a and b structure
        for l in lines:
            if ";LAYER:" + str(target_layer) + "\n" in l\
                    or ";LAYER:" + str(target_layer + 1) + "\n" in l:  # target layer
                is_target = 1
                if ";LAYER:" + str(target_layer + 1) + "\n" in l:
                    is_b = 1
                    #modified += mesh_f_replaced + "\n"

            if is_target == 1 and ";TYPE:FILL" in l:
                modified += l
                is_infill = 1

            if is_target == 1 and ";TYPE:SKIN" in l:
                modified += l
                is_infill = 1

            if ";TIME_ELAPSED:" in l and is_target == 1 and is_infill == 1:
                is_target = 0
                is_infill = 0
                if is_b == 0:

                    modified += a_structure
                    modified += mesh + "\n"
                    modified += "\n"
                    for p in pause_code:
                        modified += p
                    modified += "\n"
                    modified += mesh_f_replaced + "\n"
                else:
                    modified += b_structure
                    is_b = 0
            elif is_target == 1 and is_infill == 1:
                pass
            else:
                modified += l

        structured = modified.split("\n")

        final = ""

        for l in structured:
            l += "\n"
            if ";LAYER:" + str(target_layer - 1) + "\n" in l\
                    or ";LAYER:" + str(target_layer + 2) + "\n" in l:  # target layer
                is_target = 1

            if is_target == 1 and ";TYPE:FILL" in l:
                final += l
                is_infill = 1
            if is_target == 1 and ";TYPE:SKIN" in l:
                modified += l
                is_infill = 1

            if ";MESH:NONMESH" in l and is_target == 1 and is_infill == 1:
                is_target = 0
                is_infill = 0
                final += full_structure
            elif is_target == 1 and is_infill == 1:
                pass
            else:
                final += l

        if flag == 0:
            with open(file_name.split(".gcode")[0] + "_blob.gcode", "w") as f:
                f.write(final)
        elif flag == 1:
            with open(file_name, "w") as f:
                f.write(final)


def unit_square_is_included(p, gap, coords):

    if [p[0] + gap, p[1]] not in coords:
        return False
    if [p[0], p[1] + gap] not in coords:
        return False
    if [p[0] + gap, p[1] + gap] not in coords:
        return False

    return True


def adhesion_structure(file_name, target_layers, type):

    target_layers.sort()

    # todo: handle layer number issue (what if the layer number is invalid??

    replace_infill_to_adhesion_structure(file_name, target_layers[0], type, flag=0)

    if len(target_layers) > 1:
        for i in range(1, len(target_layers)):
            replace_infill_to_adhesion_structure(file_name.split(".gcode")[0] + "_" + type + ".gcode", target_layers[i], type, flag=1)


def adhesion_structure_horizontal(file_name):

    gcode = open(file_name)

    lines = gcode.readlines()

    # get inner wall
    extruder = 0
    layer = 0
    is_inner_wall = 0
    inner_walls = []
    layer_count = 0
    all_layers = []

    set = ""

    for l in lines:
        if "T0" in l:
            extruder = 0
        elif "T1" in l:
            extruder = 1
        elif ";LAYER:" in l:
            layer = int(l.split(":")[1].strip())

        if ";TYPE:WALL-INNER" in l:
            is_inner_wall = 1
        elif is_inner_wall == 1 and ";TYPE:" in l:
            is_inner_wall = 0

        if is_inner_wall == 1:
            if len(inner_walls) == 0:
                set += l
                inner_walls.append([layer, extruder, set])
            else:
                if inner_walls[-1][0] == layer and inner_walls[-1][1] == extruder:
                    set += l
                    inner_walls[-1][2] = set
                else:
                    set = l
                    inner_walls.append([layer, extruder, set])

            #inner_walls.append([layer, extruder, l])
            all_layers.append([layer, extruder])

        if ";LAYER_COUNT:" in l:
            layer_count = int(l.split(":")[-1].strip())

    # get multimaterial layers
    layers_drop_dups = []

    for i in all_layers:
        if i not in layers_drop_dups:
            layers_drop_dups.append(i)

    layer_df = pd.DataFrame(layers_drop_dups, columns=['layer', 'extruder'])

    layer_df = layer_df.groupby(['layer']).size().reset_index(name='count')

    multi_layers_number = []

    for i in range(len(layer_df)):
        if layer_df.iloc[i]['count'] > 1:
            multi_layers_number.append(layer_df.iloc[i]['layer'])

    first_or_last = []
    excluded_layers = [0, 1, 2, 3, 4,
                       layer_count - 1, layer_count - 2, layer_count - 3, layer_count - 4, layer_count - 5]

    '''
    for i in range(len(multi_layers_number)):
        if multi_layers_number[i] in excluded_layers:
            pass
        else:
            first_or_last.append(i)
    '''
    for i in excluded_layers:
        multi_layers_number.remove(i)

    # get inner walls of multimaterial layers
    multi_inner_walls = []

    for i in range(len(inner_walls)):
        if inner_walls[i][0] in multi_layers_number:  # if the layer contains two materials
            multi_inner_walls.append(inner_walls[i])

    flag = 0
    points_0 = []
    points_1 = []

    #for i in range(len(infills)):
     #   points_0 = []
      #  points_1 = []
#       print(infills)


    # get outer wall
    is_outer_wall = 0
    extruder = 0
    layer = 0
    set = ""

    outer_walls = []

    for l in lines:
        if "T0" in l:
            extruder = 0
        elif "T1" in l:
            extruder = 1
        elif ";LAYER:" in l:
            layer = int(l.split(":")[1].strip())

        if layer in multi_layers_number:
            if ";TYPE:WALL-OUTER" in l:
                is_outer_wall = 1
            elif is_outer_wall == 1 and ";" in l:
                is_outer_wall = 0

            if is_outer_wall == 1:
                #outer_walls.append([layer, extruder, l])
                if len(outer_walls) == 0:
                    set += l
                    outer_walls.append([layer, extruder, set])
                else:
                    if outer_walls[-1][0] == layer and outer_walls[-1][1] == extruder:
                        set += l
                        outer_walls[-1][2] = set
                    else:
                        set = l
                        outer_walls.append([layer, extruder, set])
                        set = ""


    # plt.plot(x_values, y_values, 'ro')
    # plt.plot(a_x, a_y, 'bo')
    # plt.plot(b_x, b_y, 'go')
    # plt.show()
    inner_walls_df = pd.DataFrame(multi_inner_walls, columns=['layer', 'extruder', 'commands'])
    outer_walls_df = pd.DataFrame(outer_walls, columns=['layer', 'extruder', 'commands'])

    #for i in range(len(outer_walls_df)):
    #    print(outer_walls_df.iloc[i]['commands'])

    #polygons_x_list = []
    #polygons_y_list = []
    polygons_list = []

    for i in range(len(outer_walls)):
        commands = outer_walls[i][2].split("\n")
        extruder = outer_walls[i][1]

        polygons_list.append(get_polygons_of_wall(commands))

    outer_walls_df['polygons'] = polygons_list

    polygons_list = []

    for i in range(len(multi_inner_walls)):
        commands = multi_inner_walls[i][2].split("\n")
        extruder = multi_inner_walls[i][1]

        polygons_list.append(get_polygons_of_wall(commands))

    inner_walls_df['polygons'] = polygons_list


    #print(inner_walls_df)

    #print(outer_walls_df['polygons'])

    #print(outer_walls_df)

    #for i in range(len(outer_walls_df)):
    #    print(len(outer_walls_df.iloc[i]['polygons']))

    stitches_per_layer = []

    dist = 0.4

    for i in multi_layers_number:

        current_outer_walls_df = outer_walls_df.loc[outer_walls_df['layer'] == i]
        current_inner_walls_df = inner_walls_df.loc[inner_walls_df['layer'] == i]

        adjacency_set = []

        # first material
        polygons_0 = current_outer_walls_df.iloc[0]['polygons']
        # second material
        polygons_1 = current_outer_walls_df.iloc[1]['polygons']

        # inner polygons
        inner_polygon_0 = current_inner_walls_df.iloc[0]['polygons']
        inner_polygon_1 = current_inner_walls_df.iloc[1]['polygons']

        pairs = []

        # find material 0 - material 1 pairs
        for j in range(len(polygons_0)):
            for k in range(len(polygons_1)):
                pairs.append([j, k])

        # print(pairs)

        adjacency = []

        for j in range(len(pairs)):
            p_0 = polygons_0[pairs[j][0]]
            p_1 = polygons_1[pairs[j][1]]

            for k in range(len(p_0)):
                for l in range(len(p_1)):
                    if math.hypot(p_0[k][0] - p_1[l][0], p_0[k][1] - p_1[l][1]) <= dist:
                        # print(math.hypot(p_0[k][0] - p_1[l][0], p_0[k][1] - p_1[l][1]))
                        if p_0[k] not in adjacency:
                            adjacency.append(p_0[k])
                        if p_1[l] not in adjacency:
                            adjacency.append(p_1[l])

            if len(adjacency) != 0:
                adjacency_set.append(adjacency)
            adjacency = []


        #print(adjacency_set)

        stitches = ";TYPE:STITCH\n"

        for j in range(len(adjacency_set)):
            adj_points = adjacency_set[j]

            x_min = 0
            y_min = 0
            x_max = 0
            y_max = 0

            x_values = []
            y_values = []
            #print(adj_points)
            for k in range(len(adj_points)):
                x_values.append(adj_points[k][0])
                y_values.append(adj_points[k][1])

            x_min, x_max = get_min_max(x_values)
            y_min, y_max = get_min_max(y_values)

            fair_dist = 3
            fair_dist_to_outer = 1.2

            # direction = 0  # 0: horizontal, 1: vertical

            if x_max - x_min < y_max - y_min:
                direction = 0
            else:
                direction = 1

            if direction == 0:  # horizontal alignment
                x_min -= fair_dist
                x_max += fair_dist
                y_min += fair_dist_to_outer
                y_max -= fair_dist_to_outer

            elif direction == 1:  # vertical alignment
                x_min += fair_dist_to_outer
                x_max -= fair_dist_to_outer
                y_min -= fair_dist
                y_max += fair_dist

            stitch_x, stitch_y = generate_adjacent_stitch(x_min, x_max, y_min, y_max, direction)

            stitch = generate_full_infill_for_horizontal_stitch(stitch_x, stitch_y, direction)
            stitches += stitch

        stitches_per_layer.append([i, stitches])

    stitch_df = pd.DataFrame(stitches_per_layer, columns=['layer', 'stitch'])

    #print(len(stitch_df))

    # get final gcode
    final = ""
    stitch = ""

    for l in lines:

        if ";LAYER:" in l:
            layer = int(l.split(":")[1].strip())

        if ";MESH:NONMESH" in l and layer in multi_layers_number:
            stitch = stitch_df.loc[stitch_df['layer'] == int(layer)].iloc[0][1]
            final += stitch

        final += l

    with open(file_name.split(".gcode")[0] + "_stitched.gcode", "w") as f:
        f.write(final)

    #print(multi_layers_number)
    '''

    for i in multi_layers_number:
        current_outer_walls_df = outer_walls_df.loc[outer_walls_df['layer'] == i]
        current_inner_walls_df = inner_walls_df.loc[inner_walls_df['layer'] == i]

        adjacency_set = []

        # first material
        polygons_0 = current_outer_walls_df.iloc[0]['polygons']
        # second material
        polygons_1 = current_outer_walls_df.iloc[1]['polygons']

        # inner polygons
        inner_polygon_0 = current_inner_walls_df.iloc[0]['polygons']
        inner_polygon_1 = current_inner_walls_df.iloc[1]['polygons']

        pairs = []

        # find material 0 - material 1 pairs
        for j in range(len(polygons_0)):
            for k in range(len(polygons_1)):
                pairs.append([j, k])

        #print(pairs)

        adjacency = []

        for j in range(len(pairs)):
            p_0 = polygons_0[pairs[j][0]]
            p_1 = polygons_1[pairs[j][1]]

            for k in range(len(p_0)):
                for l in range(len(p_1)):
                    if math.hypot(p_0[k][0] - p_1[l][0], p_0[k][1] - p_1[l][1]) <= dist:
                        #print(math.hypot(p_0[k][0] - p_1[l][0], p_0[k][1] - p_1[l][1]))
                        if p_0[k] not in adjacency:
                            adjacency.append(p_0[k])
                        if p_1[l] not in adjacency:
                            adjacency.append(p_1[l])

            adjacency_set.append(adjacency)

        stitches = []

        print(adjacency_set)

        for j in range(len(adjacency_set)):
            adj_points = adjacency_set[j]

            x_min = 0
            y_min = 0
            x_max = 0
            y_max = 0

            for k in range(len(adj_points)):
                if adj_points[k][0] < x_min:
                    x_min = adj_points[k][0]
                elif adj_points[k][0] > x_max:
                    x_max = adj_points[k][0]

                if adj_points[k][1] < y_min:
                    y_min = adj_points[k][1]
                elif adj_points[k][1] > y_max:
                    y_max = adj_points[k][1]

            fair_dist = 5
            
            x_min -= fair_dist
            y_min -= fair_dist
            x_max += fair_dist
            y_max += fair_dist
            
            
            
    
            

        #for j in range(len(pairs)):
            #inner_p_0 = inner_polygon_0[pairs[j][0]]
            #inner_p_1 = inner_polygon_1[pairs[j][1]]
            #adj_points =

        stitches_per_layer.append([i, stitches])
        
        

    p_x = []
    p_y = []
    for p in adjacency_set[0]:
        p_x.append(p[0])
        p_y.append(p[1])

    #print(len(polygons_0[0]))
   #print(len(polygons_1[0]))

    p_0_x = []
    p_0_y = []
    p_1_x = []
    p_1_y = []
    p_2_x = []
    p_2_y = []

    for p in polygons_0[0]:
        p_0_x.append(p[0])
        p_0_y.append(p[1])
    for p in polygons_0[1]:
        p_1_x.append(p[0])
        p_1_y.append(p[1])
    for p in polygons_1[0]:
        p_2_x.append(p[0])
        p_2_y.append(p[1])

    plt.plot(p_0_x, p_0_y, 'bo')
    plt.plot(p_1_x, p_1_y, 'bo')
    plt.plot(p_2_x, p_2_y, 'yo')
    plt.plot(stitches[0][0], stitches[0][1], 'mo')
    plt.plot(stitches[1][0], stitches[1][1], 'ko')
    plt.plot(p_x, p_y, 'ro')
    plt.show()
    
    '''


#def get_adjacent_points_set(polygons):

 #   for i in range(len(polygons)):
  #      polygons


def generate_full_infill_for_horizontal_stitch(a_x, a_y, direction, gap=0.2):

    arbitrary = 0.4  # arbitrary number to optimize extrusion amount

    # a-structure

    g0 = "G0 F9500 "
    g1 = "G1 F2000 "

    a_structure = ""

    layer_height = 0.2
    nozzle_dia = 0.4
    length = gap
    fa = ((1.75 / 2) ** 2) / math.pi

    extrusion = (layer_height * nozzle_dia * length * arbitrary) / fa

    if direction == 1:
        a_structure += g0 + "X" + str(a_x[0]) + " Y" + str(a_y[0]) + "\n"

        for i in range(len(a_x)):
            if i + 1 < len(a_x):
                if a_x[i + 1] == a_x[i]:  # at the same line (y-axis)
                    a_structure += g1 + "X" + str(a_x[i + 1]) + " Y" + str(a_y[i + 1]) + " E" + str(extrusion) + "\n"
                elif a_x[i + 1] > a_x[i]:  # next line
                    a_structure += g0 + "X" + str(a_x[i + 1]) + " Y" + str(a_y[i + 1]) + "\n"

        #a_structure += g0 + "X" + str(a_x[0]) + " Y" + str(a_y[0]) + "\n"

    elif direction == 0:
        a_structure += g0 + "X" + str(a_x[0]) + " Y" + str(a_y[0]) + "\n"

        for i in range(len(a_y)):
            if i + 1 < len(a_y):
                if a_y[i + 1] == a_y[i]:  # at the same line (x-axis)
                    a_structure += g1 + "X" + str(a_x[i + 1]) + " Y" + str(a_y[i + 1]) + " E" + str(extrusion) + "\n"
                elif a_y[i + 1] > a_y[i]:  # next line
                    a_structure += g0 + "X" + str(a_x[i + 1]) + " Y" + str(a_y[i + 1]) + "\n"

        #a_structure += g0 + "X" + str(a_x[0]) + " Y" + str(a_y[0]) + "\n"

    return a_structure


def generate_adjacent_stitch(x_min, x_max, y_min, y_max, direction):

    grid_points = []

    gap = 0.6

    grid_x = []
    grid_y = []

    current_x = x_min
    current_y = y_min

    grid_x.append(current_x)
    grid_y.append(current_y)

    while current_x <= x_max:
        current_x += gap
        grid_x.append(current_x)
    while current_y <= y_max:
        current_y += gap
        grid_y.append(current_y)

    a_x = []
    a_y = []

    #print(x_min, x_max, y_min, y_max)

    if direction == 1:
        for i in range(len(grid_x)):
            for j in range(len(grid_y)):
                a_x.append(grid_x[i])
                a_y.append(grid_y[j])
    elif direction == 0:
        for i in range(len(grid_y)):
            for j in range(len(grid_x)):
                a_x.append(grid_x[j])
                a_y.append(grid_y[i])
    #print(a_x)
    #print(a_y)

    return a_x, a_y


def get_polygons_of_wall(commands):

    g1_x = []
    g1_y = []

    # g0_x = []
    # g0_y = []

    polygons_x = []
    polygons_y = []
    flag = 0

    for c in commands:
        if "G1" in c:
            flag = 0
            words = c.split(" ")
            for w in words:
                if "X" in w:
                    flag = 0
                    g1_x.append(float(w.split("X")[1]))
                elif "Y" in w:
                    g1_y.append(float(w.split("Y")[1]))
        elif "G0" in c and flag == 0:  # next polygon
            flag = 1
            polygons_x.append(g1_x)
            polygons_y.append(g1_y)

            g1_x = []
            g1_y = []
        elif "G0" in c and flag == 1:
            pass

    #print(polygons_x)
    #print(polygons_y)

    polygons = []
    poly = []

    for i in range(len(polygons_x)):

        for j in range(len(polygons_x[i])):
            poly.append([polygons_x[i][j], polygons_y[i][j]])

        polygons.append(poly)
        poly = []
    #print(polygons)
    #return polygons_x, polygons_y
    return polygons


def calculate_extrusion_amount(filename):

    gcode = open(filename, "r")

    lines = gcode.readlines()

    total_extrusion = 0

    for l in lines:
        if "G1" in l:
            parts = l.split(" ")

            for p in parts:
                if "E" in p:
                    total_extrusion += float(p.split("E")[1])

    print(total_extrusion)


if __name__ == "__main__":

    #adhesion_structure("./gcode/sandal.gcode", [15, 24], "blob")
    #adhesion_structure("./gcode/sandal.gcode", [15, 24], "grid")
    #adhesion_structure("./gcode/CE3_d2095_samesidehole.gcode", [190], "blob")
    #adhesion_structure("./gcode/CE3_d2095_samesidehole.gcode", [190], "grid")
    #adhesion_structure("./gcode/CE3_d2095_small_11.7.gcode", [125], "blob")
    adhesion_structure("./gcode/CE3_final_5.gcode", [127], "grid")
    #adhesion_structure("./gcode/CE3_final_abs_cpla.gcode", [127], "blob")
    #adhesion_structure("./example/CE3_gripper.gcode", [10], "blob")
    #adhesion_structure_horizontal("./gcode_dual/FCPRO_final_5.gcode")

    #calculate_extrusion_amount("./gcode/CE3_final_grid.gcode")
