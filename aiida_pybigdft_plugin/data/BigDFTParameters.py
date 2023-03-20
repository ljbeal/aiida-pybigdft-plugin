"""
Data types provided by plugin

Register data types via the "aiida.data" entry point in setup.json.
"""
# You can directly use or subclass aiida.orm.data.Data
# or any other data type listed under 'verdi data'
from voluptuous import Optional, Schema

from aiida.orm import Dict


class BigDFTParameters(Dict):  # pylint: disable=too-many-ancestors
    """
    Command line options for diff.
    This class represents a python dictionary used to
    pass command line options to the executable.
    """

    # pylint: disable=redefined-builtin
    def __init__(self, dict=None, **kwargs):
        """
        Constructor for the data class
        Usage: ``DiffParameters(dict{'ignore-case': True})``
        :param parameters_dict: dictionary with commandline parameters
        :param type parameters_dict: dict
        """
        dict = self.validate(dict)
        super().__init__(dict=dict, **kwargs)

    def validate(
        self, parameters_dict
    ):  # Can we remove this and put all args within an inpfile?
        """Validate command line options.
        Uses the voluptuous package for validation. Find out about allowed keys using::
            print(DiffParameters).schema.schema
        :param parameters_dict: dictionary with commandline parameters
        :param type parameters_dict: dict
        :returns: validated dictionary
        """
        return parameters_dict

    def __str__(self):
        """String representation of node.
        Append values of dictionary to usual representation. E.g.::
            uuid: b416cbee-24e8-47a8-8c11-6d668770158b (pk: 590)
            {'ignore-case': True}
        """
        string = super().__str__()
        string += "\n" + str(self.get_dict())
        return
