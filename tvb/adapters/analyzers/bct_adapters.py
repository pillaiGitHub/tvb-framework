# -*- coding: utf-8 -*-
#
#
# TheVirtualBrain-Framework Package. This package holds all Data Management, and
# Web-UI helpful to run brain-simulations. To use it, you also need do download
# TheVirtualBrain-Scientific Package (for simulators). See content of the
# documentation-folder for more details. See also http://www.thevirtualbrain.org
#
# (c) 2012-2013, Baycrest Centre for Geriatric Care ("Baycrest")
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 2 as published by the Free
# Software Foundation. This program is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public
# License for more details. You should have received a copy of the GNU General
# Public License along with this program; if not, you can download it here
# http://www.gnu.org/licenses/old-licenses/gpl-2.0
#
#
#   CITATION:
# When using The Virtual Brain for scientific publications, please cite it as follows:
#
#   Paula Sanz Leon, Stuart A. Knock, M. Marmaduke Woodman, Lia Domide,
#   Jochen Mersmann, Anthony R. McIntosh, Viktor Jirsa (2013)
#       The Virtual Brain: a simulator of primate brain network dynamics.
#   Frontiers in Neuroinformatics (7:10. doi: 10.3389/fninf.2013.00010)
#
#

import os
from abc import abstractmethod
from tvb.adapters.analyzers.matlab_worker import MatlabWorker
from tvb.basic.filters.chain import FilterChain
from tvb.basic.profile import TvbProfile
from tvb.core.adapters.abcadapter import ABCAsynchronous
from tvb.core.entities.model import AlgorithmTransientGroup
from tvb.core.utils import extract_matlab_doc_string
from tvb.datatypes.connectivity import Connectivity
from tvb.datatypes.graph import ConnectivityMeasure
from tvb.datatypes.mapped_values import ValueWrapper


BCT_GROUP_MODULARITY = AlgorithmTransientGroup("Modularity Algorithms", "Brain Connectivity Toolbox", "bct")
BCT_GROUP_DISTANCE = AlgorithmTransientGroup("Distance Algorithms", "Brain Connectivity Toolbox", "bctdistance")

BCT_PATH = os.path.join(TvbProfile.current.EXTERNALS_FOLDER_PARENT, "externals/BCT")

LABEL_CONNECTIVITY_BINARY = "Binary (directed/undirected) connection matrix"
LABEL_CONN_WEIGHTED_DIRECTED = "Weighted directed connection matrix"
LABEL_CONN_WEIGHTED_UNDIRECTED = "Weighted undirected connection matrix"


def bct_description(mat_file_name):
    return extract_matlab_doc_string(os.path.join(BCT_PATH, mat_file_name))


class BaseBCT(ABCAsynchronous):
    """
    Interface between Brain Connectivity Toolbox of Olaf Sporns and TVB Framework.
    This adapter requires BCT deployed locally, and Matlab or Octave installed separately of TVB.
    """
    _ui_connectivity_label = "Connection matrix:"


    def __init__(self):
        ABCAsynchronous.__init__(self)
        self.matlab_worker = MatlabWorker()


    @staticmethod
    def can_be_active():
        return not not TvbProfile.current.MATLAB_EXECUTABLE


    def get_input_tree(self):
        return [dict(name="connectivity", label=self._ui_connectivity_label, type=Connectivity, required=True)]


    def get_output(self):
        return [ConnectivityMeasure, ValueWrapper]


    def get_required_memory_size(self, **kwargs):
        # We do not know how much memory is needed.
        return -1


    def get_required_disk_size(self, **kwargs):
        return 0


    def execute_matlab(self, matlab_code, **kwargs):
        self.matlab_worker.add_to_path(BCT_PATH)
        self.log.info("Starting execution of MATLAB code:" + matlab_code)
        runcode, matlablog, result = self.matlab_worker.matlab(matlab_code, kwargs)
        self.log.debug("Code run in MATLAB: " + str(runcode))
        self.log.debug("MATLAB log: " + str(matlablog))
        self.log.debug("Finished MATLAB execution:" + str(result))
        return result


    def build_connectivity_measure(self, result, key, connectivity, title="", label_x="", label_y=""):
        measure = ConnectivityMeasure(storage_path=self.storage_path)
        measure.array_data = result[key]
        measure.connectivity = connectivity
        measure.title = title
        measure.label_x = label_x
        measure.label_y = label_y
        return measure


    def build_float_value_wrapper(self, result, key, title=""):
        value = ValueWrapper(storage_path=self.storage_path)
        value.data_value = float(result[key])
        value.data_type = 'float'
        value.data_name = title
        return value


    def build_int_value_wrapper(self, result, key, title=""):
        value = ValueWrapper(storage_path=self.storage_path)
        value.data_value = int(result[key])
        value.data_type = 'int'
        value.data_name = title
        return value


    @abstractmethod
    def launch(self, connectivity, **kwargs):
        pass


class BaseUndirected(BaseBCT):
    """
    """
    _ui_connectivity_label = "Undirected connection matrix:"

    def get_input_tree(self):
        return [dict(name="connectivity", label=self._ui_connectivity_label, type=Connectivity, required=True,
                     conditions=FilterChain(fields=[FilterChain.datatype + '._undirected'],
                                            operations=["=="], values=['1']))]


    @abstractmethod
    def launch(self, connectivity, **kwargs):
        pass


class ModularityOCSM(BaseBCT):
    """
    """
    _ui_group = BCT_GROUP_MODULARITY
    _ui_connectivity_label = "Directed (weighted or binary) connection matrix:"

    _ui_name = "Optimal Community Structure and Modularity"
    _ui_description = bct_description("modularity_dir.m")
    _matlab_code = "[Ci,Q] = modularity_dir(CW);"


    def launch(self, connectivity, **kwargs):
        # Prepare parameters
        kwargs['CW'] = connectivity.weights
        # Execute the matlab code
        result = self.execute_matlab(self._matlab_code, **kwargs)
        # Gather results
        measure = self.build_connectivity_measure(result, 'Ci', connectivity, "Optimal Community Structure")
        value = self.build_float_value_wrapper(result, 'Q', title="Maximized Modularity")
        return [measure, value]


class ModularityOpCSMU(ModularityOCSM):
    """
    """
    _ui_name = "Optimal Community Structure and Modularity (Undirected)"
    _ui_description = bct_description("modularity_und.m")
    _matlab_code = "[Ci,Q] = modularity_und(CW);"


class DistanceDBIN(BaseBCT):
    """
    """
    _ui_group = BCT_GROUP_DISTANCE

    _ui_name = "Distance binary matrix"
    _ui_description = bct_description("distance_bin.m")
    _matlab_code = "D = distance_bin(A);"


    def launch(self, connectivity, **kwargs):
        kwargs['A'] = connectivity.weights
        result = self.execute_matlab(self._matlab_code, **kwargs)
        measure = self.build_connectivity_measure(result, 'D', connectivity, "Distance matrix")
        return [measure]


class DistanceDWEI(DistanceDBIN):
    """
    """
    _ui_connectivity_label = "Weighted (directed/undirected) connection matrix:"
    _ui_name = "Distance weighted matrix"
    _ui_description = bct_description("distance_wei.m")
    _matlab_code = "D = distance_wei(A);"


class DistanceRDM(DistanceDBIN):
    """
    """
    _ui_name = "Reachability and distance matrices (Breadth-first search)"
    _ui_description = bct_description("breadthdist.m")
    _matlab_code = "[R,D] = breadthdist(A);"


    def launch(self, connectivity, **kwargs):
        kwargs['A'] = connectivity.weights
        result = self.execute_matlab(self._matlab_code, **kwargs)

        measure1 = self.build_connectivity_measure(result, 'R', connectivity, "Reachability matrix")
        measure2 = self.build_connectivity_measure(result, 'D', connectivity, "Distance matrix")
        return [measure1, measure2]


class DistanceRDA(DistanceRDM):
    """
    """
    _ui_name = "Reachability and distance matrices (Algebraic path count)"
    _ui_description = bct_description("reachdist.m")
    _matlab_code = "[R,D] = reachdist(A);"


class DistanceNETW(DistanceDBIN):
    """
    """
    _ui_name = "Network walks"
    _ui_description = bct_description("findwalks.m")
    _matlab_code = "[Wq,twalk,wlq]  = findwalks(A);"


    def launch(self, connectivity, **kwargs):
        kwargs['A'] = connectivity.weights
        result = self.execute_matlab(self._matlab_code, **kwargs)

        measure1 = self.build_connectivity_measure(result, 'Wq', connectivity, "3D matrix")
        measure2 = self.build_connectivity_measure(result, 'wlq', connectivity, "Walk length distribution")
        value = self.build_float_value_wrapper(result, 'twalk', title="Total number of walks found")
        return [measure1, value, measure2]