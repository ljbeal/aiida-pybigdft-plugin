def dump_to_file(structure, fname):
    structure.get_ase().write(fname)

    return fname