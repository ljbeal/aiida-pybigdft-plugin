"""
Calculations provided by aiida_bigdft.

Register calculations via the "aiida.calculations" entry point in setup.json.
"""
import getpass
import os
from datetime import datetime

import aiida.orm
import yaml
from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.orm import User

from aiida_bigdft.data.BigDFTParameters import BigDFTParameters
from aiida_bigdft.data.BigDFTFile import BigDFTFile, BigDFTLogfile

try:
    from aiida_bigdft.paths import DEBUG_PATHS
except ImportError:
    DEBUG_PATHS = None

DEBUG = True


def debug(msg, wipe=False, time=True):
    if not DEBUG or not DEBUG_PATHS:
        return
    mode = 'w+' if wipe else 'a'
    timestr = datetime.now().strftime('%H:%M:%S')

    usr = getpass.getuser()

    with open(DEBUG_PATHS[usr], mode) as o:
        if not time:
            o.write(f'{msg}\n')
            return
        o.write(f'[{timestr}] {msg}\n')


class BigDFTCalculation(CalcJob):
    """
    AiiDA calculation plugin wrapping the diff executable.

    Simple AiiDA plugin wrapper for 'diffing' two files.
    """

    _posinp = "posinp.xyz"
    _inpfile = "input.yaml"
    _logfile = "log.yaml"
    _timefile = "time.yaml"

    @classmethod
    def define(cls, spec):
        """Define inputs and outputs of the calculation."""
        super().define(spec)

        # set default values for AiiDA options
        spec.inputs["metadata"]["options"]["resources"].default = {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1,
            "tot_num_mpiprocs": 1
        }
        spec.inputs["metadata"]["options"]["parser_name"].default = "bigdft"

        # inputs
        spec.input("metadata.options.local_dir",
                   valid_type=str,
                   help="staging directory for local files")
        spec.input("structure", valid_type=aiida.orm.StructureData)
        spec.input("parameters", valid_type=BigDFTParameters, default=lambda: BigDFTParameters())
        spec.input("metadata.options.jobname", valid_type=str)

        # outputs
        spec.output("logfile", valid_type=BigDFTLogfile)
        spec.output("timefile", valid_type=BigDFTFile)

        spec.exit_code(100, 'ERROR_MISSING_OUTPUT_FILES',
                       message='Calculation did not produce all expected output files.')
        spec.exit_code(101, 'ERROR_PARSING_FAILED',
                       message='Calculation did not produce all expected output files.')
        spec.exit_code(400, 'ERROR_OUT_OF_WALLTIME',
                       message='Calculation did not finish because of a walltime issue.')
        spec.exit_code(401, 'ERROR_OUT_OF_MEMORY',
                       message='Calculation did not finish because of memory limit')

    def prepare_for_submission(self, folder):
        """
        Create input files.

        :param folder: an `aiida.common.folders.Folder` where the plugin should temporarily place all files
            needed by the calculation.
        :return: `aiida.common.datastructures.CalcInfo` instance
        """

        debug(f'operating in dir {os.getcwd()}')

        # dump structure
        structure_fname = 'structure.json'
        with folder.open(structure_fname, 'w') as o:
            self.inputs.structure.get_ase().write(o)
        debug(f'structure written to file {structure_fname}', wipe=True)

        # dump params
        debug(f'dumping params {self.inputs.parameters}')
        params_fname = 'input.yaml'
        with folder.open(params_fname, 'w') as o:
            yaml.dump(self.inputs.parameters.get_dict(), o)
        debug(f'parameters written to file {params_fname}')

        # submission parameters
        jobname = self.metadata.options.jobname
        sub_params_file = self.dump_submission_parameters(folder)

        # aiida calcinfo setup
        codeinfo = datastructures.CodeInfo()

        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.cmdline_params = ['--structure', structure_fname,
                                   '--parameters', params_fname,
                                   '--submission', sub_params_file]

        # Prepare a `CalcInfo` to be returned to the engine
        calcinfo = datastructures.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.local_copy_list = [
        ]
        calcinfo.retrieve_list = [
            f'log-{jobname}.yaml',
            f"./data-{jobname}/time-{jobname}.yaml",
            ["./debug/bigdft-err*", ".", 2],
        ]

        return calcinfo

    def dump_submission_parameters(self, folder):
        sub_params_file = 'submission_parameters.yaml'
        sub_params = {"jobname": self.metadata.options.jobname}

        sub_params["OMP"] = self.metadata.options.resources.get("num_cores_per_mpiproc", None)
        sub_params["mpi"] = self.metadata.options.resources.get("tot_num_mpiprocs", None)
        sub_params["nodes"] = self.metadata.options.resources.get("num_machines", None)

        sub_params["aiida_resources"] = self.metadata.options.resources

        computer = self.node.computer
        user = User.objects.get_default()

        sub_params["mpirun command"] = ' '.join(computer.get_mpirun_command())
        sub_params["connection"] = computer.get_authinfo(user).get_auth_params()

        # This actually updates the computer mpirun command permanently
        # self.node.computer.set_mpirun_command([])

        debug(f'dumping submission params {sub_params}')
        with folder.open(sub_params_file, 'w') as o:
            yaml.dump(sub_params, o)

        return sub_params_file
