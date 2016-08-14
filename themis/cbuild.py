import os
import shutil
import subprocess
import tempfile
import pkg_resources


def build_program(main_file_data, library_header, shared_library, gcc_prefix, cflags, package=__name__):
    with tempfile.TemporaryDirectory() as tempdir:
        shead_name = os.path.basename(library_header)
        shlib_name = os.path.basename(shared_library)
        assert shlib_name.startswith("lib") and shlib_name.endswith(".so") and shead_name.endswith(".h")
        shlib_short = shlib_name[3:-3]  # strip "lib" and ".so"

        shared_lib_path = os.path.join(tempdir, shlib_name)
        lib_header_path = os.path.join(tempdir, shead_name)
        main_file_path = os.path.join(tempdir, "themis_main.c")
        main_output_path = os.path.join(tempdir, "themis_main")

        with open(shared_lib_path, "wb") as fout:
            with pkg_resources.resource_stream(package, shared_library) as fin:
                shutil.copyfileobj(fin, fout)
        with open(lib_header_path, "wb") as fout:
            with pkg_resources.resource_stream(package, library_header) as fin:
                shutil.copyfileobj(fin, fout)
        with open(main_file_path, "w") as fout:
            fout.write(main_file_data)

        subprocess.check_call([gcc_prefix + "gcc", *cflags.split(), "-I", tempdir, "-L", tempdir, "-l", shlib_short,
                               main_file_path, "-o", main_output_path])
        subprocess.check_call([gcc_prefix + "strip", main_output_path])
        with open(main_output_path, "rb") as fin:
            main_output_data = fin.read()
    return main_output_data
