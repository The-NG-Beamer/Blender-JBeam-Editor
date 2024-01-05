# Copyright (c) 2023 BeamNG GmbH, Angelo Matteo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pickle
import traceback

import bpy

# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

import bmesh

from . import constants
from . import utils
from . import export_utils
from . import text_editor

import timeit

last_exported_jbeams = {}


def save_post_callback(filepath):
    # On saving, set the JBeam part meshes import file paths to what is saved in the Python environment filepath
    for obj in bpy.context.scene.objects:
        obj_data = obj.data
        jbeam_part = obj_data.get(constants.MESH_JBEAM_PART)
        if jbeam_part == None:
            continue

        bm = None
        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(obj_data)
        else:
            bm = bmesh.new()
            bm.from_mesh(obj_data)

        if jbeam_part in last_exported_jbeams:
            obj_data[constants.MESH_JBEAM_FILE_PATH] = last_exported_jbeams[jbeam_part]['in_filepath']

        bm.free()


# https://blender.stackexchange.com/a/110112
def show_message_box(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


def export_new_jbeam(context, obj, obj_data, bm, init_node_id_layer, node_id_layer, filepath):
    node_names = []
    longest_node_name = 0
    longest_x = 0
    longest_y = 0
    pos_strs = []
    abs_pos_strs = []

    bm.verts.ensure_lookup_table()
    for i in range(len(bm.verts)):
        v = bm.verts[i]
        node_id = v[node_id_layer].decode('utf-8')
        pos_str = (to_float_str(v.co.x), to_float_str(v.co.y), to_float_str(v.co.z))
        abs_pos_str = (pos_str[0].replace('-','',1), pos_str[1].replace('-','',1), pos_str[2].replace('-','',1))
        pos_strs.append(pos_str)
        abs_pos_strs.append(abs_pos_str)

        longest_node_name = max(longest_node_name, len(node_id))
        longest_x = max(longest_x, len(abs_pos_str[0]))
        longest_y = max(longest_y, len(abs_pos_str[1]))
        node_names.append(node_id)

    nodes = ['["id", "posX", "posY", "posZ"]']

    for i in range(len(bm.verts)):
        v = bm.verts[i]
        node_id = v[node_id_layer].decode('utf-8')
        pos_str = pos_strs[i]
        abs_pos_str = abs_pos_strs[i]

        x_space = ((pos_str[0][0] != '-' and 1 or 0) + longest_node_name - len(node_id)) * ' '
        y_space = ((pos_str[1][0] != '-' and 1 or 0) + longest_x - len(abs_pos_str[0])) * ' '
        z_space = ((pos_str[2][0] != '-' and 1 or 0) + longest_y - len(abs_pos_str[1])) * ' '

        nodes.append('["{}",{} {},{} {},{} {}]'.format(node_id, x_space, pos_str[0], y_space, pos_str[1], z_space, pos_str[2]))

    str_jbeam_data = '{\n"' + obj.name + '": {\n    "nodes": [\n        '
    str_jbeam_data += ',\n        '.join(nodes)
    str_jbeam_data += '\n    ],\n},\n}'

    #str_jbeam_data = sjson.dumps(jbeam_data, '  ')
    #str_jbeam_data = sjson.dumps(sjson.loads(context.scene['jbeam_file_str_data']), '  ')

    f = open(filepath, 'w', encoding='utf-8')
    f.write(str_jbeam_data)
    f.close()

    obj_data[constants.MESH_JBEAM_FILE_PATH] = filepath


# Exports by using jbeam file imported to make changes on it:
# 1. Import original file, parse using an SJSON parser into Python data
# 2. Get node moves, renames, additions, deletions,
# 2. Make a clone of the data and modify it with moves and renames
# 3. Traverse AST and keep track of position in the SJSON data structure and modify AST node values where the data has changed between the two SJSON parsed data
#    and also add and delete nodes
# 4. Stringify AST and export to chosen output file
def export_existing_jbeam(obj: bpy.types.Object):
    try:
        t0 = timeit.default_timer()
        context = bpy.context
        obj_data = obj.data

        jbeam_filepath = obj_data[constants.MESH_JBEAM_FILE_PATH]
        part_name = obj_data[constants.MESH_JBEAM_PART]
        part_data = pickle.loads(obj_data[constants.MESH_SINGLE_JBEAM_PART_DATA])

        export_utils.export_file(jbeam_filepath, [obj], part_data)

        text_editor.check_files_for_changes(context, [jbeam_filepath])

        tf = timeit.default_timer()
        print('Exporting Time', round(tf - t0, 2), 's')
    except:
        traceback.print_exc()


def auto_export(obj_name: str):
    jbeam_objs: bpy.types.Collection | None = bpy.data.collections.get('JBeam Objects')
    if jbeam_objs is None:
        return
    obj: bpy.types.Object | None = jbeam_objs.all_objects.get(obj_name)
    if obj is None:
        return
    export_existing_jbeam(obj)


class JBEAM_EDITOR_OT_export_jbeam(Operator, ExportHelper):
    bl_idname = 'jbeam_editor.export_jbeam'
    bl_label = "Export JBeam"
    bl_description = 'Export to a new or existing BeamNG JBeam file'
    # ExportHelper mixin class uses this
    filename_ext = ".jbeam"

    filter_glob: StringProperty(
        default="*.jbeam",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )


    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj:
            return False

        obj_data = obj.data
        jbeam_part = obj_data.get(constants.MESH_JBEAM_PART)
        if jbeam_part == None:
            return False

        return True


    def execute(self, context):
        '''out_filepath = Path(self.filepath).as_posix()

        obj = context.active_object
        obj_data = obj.data

        bm = None
        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(obj_data)
        else:
            bm = bmesh.new()
            bm.from_mesh(obj_data)

        init_node_id_layer = bm.verts.layers.string[constants.VLS_INIT_NODE_ID]
        node_id_layer = bm.verts.layers.string[constants.VLS_NODE_ID]
        imported_jbeam_part = obj_data.get(constants.MESH_JBEAM_PART)
        imported_jbeam_file_path = obj_data.get(constants.MESH_JBEAM_FILE_PATH)

        if imported_jbeam_file_path != None:
            # If last exported jbeam filepath exists, prioritize using that for the filepath over the one stored in the object to avoid undo/redo complications
            if imported_jbeam_part in last_exported_jbeams:
                imported_jbeam_file_path = last_exported_jbeams[imported_jbeam_part]['in_filepath']

            export_existing_jbeam(obj)
        else:
            export_new_jbeam(context, obj, obj_data, bm, init_node_id_layer, node_id_layer, out_filepath)

        if obj.mode != 'EDIT':
            bm.to_mesh(obj_data)

        bm.free()'''

        return {'FINISHED'}
