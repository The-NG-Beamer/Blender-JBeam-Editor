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

import copy
import os
from pathlib import Path
import sys

import bpy
from bpy import ops
import bmesh

from . import utils

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

from . import constants
from . import sjson
from . import export_jbeam

from .jbeam import io as jbeam_io


def load_jbeam(vehicle_directories: list[Path], vehicle_config: dict):
    """load all the jbeam and construct the thing in memory"""
    print('Reading files...')
    io_ctx = jbeam_io.start_loading(vehicle_directories)
    print('Done reading files')


def load_vehicle_stage_1(vehicles_dir: Path, vehicle_dir: Path, vehicle_config: dict):
    vehicle_directories = [vehicle_dir, Path(vehicles_dir).joinpath('common')]
    load_jbeam(vehicle_directories, vehicle_config)


def build_config(config_path):
    res = {}
    file_data = utils.sjson_read_file(config_path)
    res['partConfigFilename'] = config_path
    if file_data and file_data['format'] == 2:
        file_data['format'] = None
        res.update(file_data)
    else:
        res['parts'] = file_data or {}

    return res


def import_vehicle(config_path: Path):
    vehicle_dir = config_path.parent.absolute()
    vehicles_dir = Path(vehicle_dir).parent.absolute()

    vehicle_config = build_config(config_path)
    load_vehicle_stage_1(vehicles_dir, vehicle_dir, vehicle_config)


class JBEAM_EDITOR_OT_import_vehicle(Operator, ImportHelper):
    bl_idname = 'jbeam_editor.import_vehicle'
    bl_label = 'Import JBeam'
    bl_description = 'Import a BeamNG Part Config file (.pc)'
    filename_ext = ".pc"

    filter_glob: StringProperty(
        default="*.pc",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        import_vehicle(Path(self.filepath))
        return {'FINISHED'}
