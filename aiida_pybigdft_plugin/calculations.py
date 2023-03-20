"""
Calculations provided by aiida_pybigdft_plugin.

Register calculations via the "aiida.calculations" entry point in setup.json.
"""
import os

import aiida.orm
from aiida.common import datastructures
from aiida.engine import CalcJob
from aiida.orm import to_aiida_type

from aiida_pybigdft_plugin.data.BigDFTParameters import BigDFTParameters
from aiida_pybigdft_plugin.data.BigDFTFile import BigDFTFile, BigDFTLogfile


class BigDFTCalculation(CalcJob):
    """
    AiiDA calculation plugin wrapping the diff executable.

    Simple AiiDA plugin wrapper for 'diffing' two files.
    """

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
        output_fname = 'structure.json'
        output_path = self.inputs.metadata.options.local_dir or ''

        output = os.path.join(output_path, output_fname)
        self.inputs.structure.get_ase().write(output)

        self.logger.info(f'structure written to file {output}')
        with open('/home/aiida/plugin_work/debug.txt', 'w+') as f:
            f.write(f'structure written to file {output}')

        codeinfo = datastructures.CodeInfo()

        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdout_name = self.metadata.options.output_filename

        # Prepare a `CalcInfo` to be returned to the engine
        calcinfo = datastructures.CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.local_copy_list = [
        ]
        calcinfo.retrieve_list = []

        return calcinfo
