# This file is licensed using the "MIT License" below:
#
# ##################################################################################################
#
# MIT License
#
# Copyright 2019-2020 Home Brew Robotics Club
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be included in all copies
# or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#
# ##################################################################################################
# <======================================= 100 characters =======================================> #

"""kidocgen generates a KiCAD .dcm file from a directory .csv files.

Usage: kidocgen CSVS_DIR FILE.dcm  # Input Output

`kidocgen` scans CSVS_DIR for a bunch of `.csv` files with the suffix of `.kipart.csv`.

The first line of each `.kipart.csv` file must match the expected first line for `kipart` input.
This is:

Part_Name,Reference_Prefix,Footprint_Name,Data_Sheet_URL,Short_Description;Long_Description
Note that this is 4 commas and 1 semicolon.
"""

from pathlib import Path
from typing import List
import sys


def strip_quotes(text: str) -> str:
    """Remove the double quotes surrounding a string."""
    text = text.strip(' "')
    return text


def main():
    """Generate a KiCAD `.dcm` file from a directory of `.csv` files.

    Usage: kidocgen CSVS_DIR OUTPUT.dcm
    """
    error_code: int = 0
    arguments: List[str] = sys.argv
    if len(arguments) <= 2:
        print("Usage: kidocgen CSVS_DIR OUTPUT.dcm")
        error_code = 1
    else:
        # Grab the two file names:
        csvs_directory: Path = Path(arguments[1])
        dcm_path: Path = Path(arguments[2])

        # Collect the result a bunch of *lines*:
        lines: List[str] = ["EESchema-DOCLIB  Version 2.0"]

        # Sweep through all of the `*.kipart.csv` files in *csv_directory*:
        kipart_csv: Path
        for kipart_csv in csvs_directory.glob("*.kipart.csv"):
            # print(f"file:{kipart_csv}")
            with open(kipart_csv) as kipart_csv_file:
                # Parse the header line:
                kipart_csv_text: str = kipart_csv_file.read()
                kipart_csv_lines: List[str] = kipart_csv_text.split('\n')
                header: str = strip_quotes(kipart_csv_lines[0]) if len(kipart_csv_lines) > 0 else ""
                fields: List[str] = header.split(',')
                name: str = strip_quotes(fields[0]) if len(fields) > 0 else "~"
                data_sheet: str = strip_quotes(fields[3]) if len(fields) > 3 else ""
                descriptions_text: str = strip_quotes(fields[5]) if len(fields) > 5 else ""
                descriptions: List[str] = descriptions_text.split(';')
                long_description: str = descriptions[0].strip() if len(descriptions) > 0 else "~"
                short_description: str = descriptions[1].strip() if len(descriptions) > 1 else "~"

                # Output the data:
                if name != "~":
                    lines.append("#")
                    lines.append(f"$CMP {name}")
                    lines.append(f"D {long_description}")
                    lines.append(f"K {short_description}")
                    lines.append(f"F {data_sheet}")
                    lines.append("$ENDCMP")

    # Put the trailing lines in place:
    lines.append("#")
    lines.append("#End Doc Library")
    lines.append("")

    # Write *lines* out to *dcm_path*:
    master_board_dcm_text: str = '\n'.join(lines)
    with open(dcm_path, "w") as master_board_dcm_file:
        master_board_dcm_file.write(master_board_dcm_text)

    # Return with an error code (0 => OK, 1 => Not OK):
    return error_code


if __name__ == "__main__":
    main()
