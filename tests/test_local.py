from pathlib import Path
from ghrapt.util.tree.local_node import LocalAux


def test_1():
    aux = LocalAux()
    no = aux.node_from(
        Path("/mnt/SHARE/dev/blender_manual_v430_en/advanced/command_line")
    )
    assert no.is_dir()
    assert not no.is_file()
    assert not no.is_symlink()
    for x in no:
        print(x.name, x.size, x.hash)
    # print(no, hex(no.mode), hex(no.type), no.is_dir())
    # assert add(2, 3) == 5
    # assert add(-1, 1) == 0

    # assert add(0, 0) == 0
    # no.intern("PWES")
