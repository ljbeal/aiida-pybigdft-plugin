"""
Parsers provided by aiida_bigdft_new.

Register parsers via the "aiida.parsers" entry point in setup.json.
"""
import os
import re

from aiida.common import exceptions
from aiida.engine import ExitCode
from aiida.parsers.parser import Parser

from aiida_pybigdft_plugin.calculations import BigDFTCalculation
from aiida_pybigdft_plugin.data.BigDFTFile import BigDFTFile, BigDFTLogfile


class BigDFTParser(Parser):
    """
    Parser class for parsing output of calculation.
    """

    def __init__(self, node):
        """
        Initialize Parser instance

        Checks that the ProcessNode being passed was produced by a DiffCalculation.

        :param node: ProcessNode of calculation
        :param type node: :class:`aiida.orm.nodes.process.process.ProcessNode`
        """
        super().__init__(node)
        if not issubclass(node.process_class, BigDFTCalculation):
            raise exceptions.ParsingError("Can only parse DiffCalculation")

    def parse_stderr(self, inputfile):
        """Parse the stderr file to get commong errors, such as OOM or timeout.

        :param i inputfile: stderr file
        :returns: exit code in case of an error, None otherwise
        """
        timeout_messages = {
            "DUE TO TIME LIMIT",  # slurm
            "exceeded hard wallclock time",  # UGE
            "TERM_RUNLIMIT: job killed",  # LFS
            "walltime .* exceeded limit",  # PBS/Torque
        }

        oom_messages = {
            "[oO]ut [oO]f [mM]emory",
            "oom-kill",  # generic OOM messages
            "Exceeded .* memory limit",  # slurm
            "exceeds job hard limit .*mem.* of queue",  # UGE
            "TERM_MEMLIMIT: job killed after reaching LSF memory usage limit",  # LFS
            "mem .* exceeded limit",  # PBS/Torque
        }
        for message in timeout_messages:
            if re.search(message, inputfile):
                return self.exit_codes.ERROR_OUT_OF_WALLTIME
        for message in oom_messages:
            if re.search(message, inputfile):
                return self.exit_codes.ERROR_OUT_OF_MEMORY
        return

    def parse(self, **kwargs):
        """
        Parse outputs, store results in database.

        :returns: an exit code, if parsing fails (or nothing if parsing succeeds)
        """

        exitcode = ExitCode(0)

        stderr = self.node.get_scheduler_stderr()
        if stderr:
            exitcode = self.parse_stderr(stderr)
            if exitcode:
                self.logger.error("Error in stderr: " + exitcode.message)

        output_filename = self.node.get_option("output_filename")
        # jobname = self.node.get_option('jobname')
        # if jobname is not None:
        #     output_filename = "log-" + jobname + ".yaml"
        # Check that folder content is as expected
        files_retrieved = self.retrieved.list_object_names()
        files_expected = [output_filename]
        # Note: set(A) <= set(B) checks whether A is a subset of B
        if not set(files_expected) <= set(files_retrieved):
            self.logger.error(
                f"Found files '{files_retrieved}', expected to find '{files_expected}'"
            )
            return self.exit_codes.ERROR_MISSING_OUTPUT_FILES

        logfile = self.parse_file(output_filename, "logfile", exitcode)
        timefile = self.parse_file("time.yaml", "timefile", exitcode)

        self.out("logfile", logfile)
        self.out("timefile", timefile)

        return exitcode

    def parse_file(self, output_filename, name, exitcode):
        """
        Parse a retrieved file into a BigDFTFile object
        """

        # add output file
        self.logger.info(f"Parsing '{output_filename}'")
        try:
            with open(output_filename, "w+") as tmp:
                tmp.write(self.retrieved.get_object_content(output_filename))
                if name == "logfile":
                    output = BigDFTLogfile(os.path.join(os.getcwd(), output_filename))
                else:
                    output = BigDFTFile(os.path.join(os.getcwd(), output_filename))

        except ValueError:
            self.logger.error(f"Impossible to parse {name} {output_filename}")
            if (
                not exitcode
            ):  # if we already have OOW or OOM, failure here will be handled later
                return self.exit_codes.ERROR_PARSING_FAILED
        try:
            output.store()
            self.logger.info(f"Successfully parsed {name} '{output_filename}'")
        except exceptions.ValidationError:
            self.logger.info(
                f"Impossible to store {name} - ignoring '{output_filename}'"
            )
            if (
                not exitcode
            ):  # if we already have OOW or OOM, failure here will be handled later
                return self.exit_codes.ERROR_PARSING_FAILED

        return output