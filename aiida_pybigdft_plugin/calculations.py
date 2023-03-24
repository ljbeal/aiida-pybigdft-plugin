"""
Calculations provided by aiida_pybigdft_plugin.

Register calculations via the "aiida.calculations" entry point in setup.json.
"""
import os
from datetime import datetime

import aiida.orm
import yaml
from aiida.common import datastructures
from aiida.engine import CalcJob

from aiida_pybigdft_plugin.data.BigDFTParameters import BigDFTParameters
from aiida_pybigdft_plugin.data.BigDFTFile import BigDFTFile, BigDFTLogfile


def debug(msg, wipe=False):
    mode = 'w+' if wipe else 'a'
    timestr = datetime.now().strftime('%H:%M:%S')
    with open('/home/aiida/plugin_work/aiida.log', mode) as o:
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
        }
        spec.inputs["metadata"]["options"]["parser_name"].default = "pybigdft_plugin"

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

        spec.exit_code(
            300,
            "ERROR_MISSING_OUTPUT_FILES",
            message="Calculation did not produce all expected output files.",
        )

    def prepare_for_submission(self, folder):
        """
        Create input files.

        :param folder: an `aiida.common.folders.Folder` where the plugin should temporarily place all files
            needed by the calculation.
        :return: `aiida.common.datastructures.CalcInfo` instance
        """

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

        jobname = self.metadata.options.jobname

        codeinfo = datastructures.CodeInfo()

        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.cmdline_params = ['--structure', structure_fname,
                                   '--parameters', params_fname,
                                   '--jobname', jobname]

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
