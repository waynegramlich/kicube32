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

"""kicube32: A program for generating KiCad schematic symbols for STM32 processors.

Usage: kicube32 BASE.ioc BASE.csv KIPART.csv # input input output
"""

from typing import Any, Dict, IO, List, Tuple

import os
import sys


# main:
def main() -> int:
    """Parse arguments a execute program."""
    # Parse the command line *arguments*:
    result: int = 1  # Default to an error return.  Set to 0 only on success.
    arguments: List[str] = sys.argv[1:]
    arguments_size: int = len(arguments)
    if arguments_size != 3:
        print("Usage: kicube32 CUBE_IOC_FILE CUBE_CSV_FILE KIPART_CSV_FILE # input input output")
    else:
        ioc_file_name: str = arguments[0]
        stm32cube_csv_file_name: str = arguments[1]
        kipart_csv_file_name: str = arguments[2]
        if not ioc_file_name.endswith(".ioc"):
            print(f"First file name '{ioc_file_name}' does not end in '.ioc'.")
        elif not stm32cube_csv_file_name.endswith(".csv"):
            print(f"Second file name '{kipart_csv_file_name}' does not end in '.ioc'.")
        elif not kipart_csv_file_name.endswith(".csv"):
            print(f"Third file name '{kipart_csv_file_name}' does not end in '.csv'.")
        else:
            # Read in the *ioc_file_name* extract the values:
            ioc: IOC = IOC(ioc_file_name)

            board_name: str = ioc.board_name
            mcu_name: str = ioc.mcu_name
            package: str = ioc.package
            # print("mcu_name='{0}'".format(mcu_name))
            # print("board_name='{0}".format(board_name))
            # print("package='{0}".format(package))
            kicube: KiCube = KiCube(ioc_file_name, stm32cube_csv_file_name,
                                    mcu_name, board_name, package)

            # Verify timestamps:
            if ioc.timestamp >= kicube.timestamp:
                print(f"File '{ioc_file_name}' has changed! "
                      f"Please update file '{stm32cube_csv_file_name}'!!!")
            else:
                kicube.kipart_generate(kipart_csv_file_name)
                result = 0

    return result


# ChipPin:
class ChipPin:
    """Represents information about one physical microcontroller pin."""

    # ChipPin.__init__():
    def __init__(self, line: str) -> None:
        """Initialize ChipPin object.

        The arguments are:
        * *line* (str): One line from a `.csv` file of the form '"P","N","K","S","L"', where:
          * "P" is name of the physical the chip pin (e.g 'B12', '3', '29', etc.)
          * "N" is the vendor logical name for the chip pin (e.g. 'PB3', 'VSS', 'NRST', etc.)
          * "K" is the electrical kind of the chip pin (e.g. "Power", "I/O", "Input", etc.)
          * "S" is the internal signal name for chip pin (e.g. 'UART7_RX', etc.)
          * "L" is some additional information about the pin, usually for GPI pins.
        These values are stuffed into directly into attributes named *position*, *name*,
        *kind*, *signal*, and *label*.

        In addition, two sort keys are generated to order a list of *ChipPin* objects.
        The *position_key* is used to sort exclusively by *position*.  The *group_key* is used
        to group pins into ordered groups.

        ??The arguments are directly stuffed into the *ChipPin* object (i.e. *self*).
        In addition, to make sorting lists easier, sort keys named *position_key* and *name_key*
        are generated.  Lastly, the overall type of pin is specified by *is_port*, *is_power*,
        and *is_other* attributes, of exactly one is *True* and the other two are *False*.
        """
        # Verify argument types:
        assert isinstance(line, str)
        # print("line={0}".format(line))

        # Split *line* into *fields* and break them out into *position*, *name*, *kind*, etc.:
        fields: List[str] = line.replace('"', "").split(',')
        assert len(fields) == 5, "line='{0} fields={1}'".format(line, fields)
        position: str = fields[0]
        name: str = fields[1]
        kind: str = fields[2]
        signal: str = fields[3]
        label: str = fields[4]

        # Convert STMCube32 userlabels that start with "_" to a KiCAD negation character:
        if len(label) >= 1 and label[0] == '_':
            label = '~' + label[1:]

        # Compute *trimmed_name* which is *name* with everything after the '/' or '-' removed:
        slash_index: int = name.find('/')
        hypen_index: int = name.find('-')
        trim_index: int = max(slash_index, hypen_index)
        trimmed_name: str = name if trim_index < 0 else name[:trim_index]

        # Create *position_key* from *position* and stuff into *chip_pin*:
        position_key: Tuple[Any, ...]
        if position[0].isalpha():
            # We have1 a ball grid pin:
            assert position[1:].isdigit()
            position_key = (position[0], int(position[1:]))
        else:
            # We have a more standard numerical pin:
            assert position.isdigit()
            position_key = tuple(position)

        # if trimmed_name in ("PA7", "PA15", "PA14"):
        #     print("name='{0}' trimmed_name='{1}' position='{2}'".
        #       format(name, trimmed_name, position))

        # Figure out which ...
        asterisk_appended: bool = False
        kicad_type: str = "no_connect"
        style: str = "non_logic"
        side: str = "right"
        tag: str
        unit: str
        unit_sort: Tuple[Any, ...]
        if kind in ("I/O", "Input", "Output"):  # or (name[0] == 'P' and name[2].isdigit() ):
            # Parse out the Port name"
            if (len(trimmed_name) >= 3 and (trimmed_name[0] == 'P' and
                                            trimmed_name[1].isalpha() and
                                            trimmed_name[2:].isdigit())):
                # We have a port name:
                unit = trimmed_name[:2]
                unit_sort = tuple(trimmed_name[2:])  # int(trimmed_name[2:])
            else:
                unit = "?"
                unit_sort = tuple("")
                print("Unknown I/O name '{0}' (trimmed_name = '{1}')".format(name, trimmed_name))

            # Set *style* to be either a regular line or an inverted line:
            style = "line"
            if len(label) >= 1 and label[0] == '~':
                style = "inverted"
            if signal == "":
                # Unused:
                kicad_type = "no_connect"
            elif signal.startswith("ETH_"):
                kicad_type = "bidirectional"
                name += "({0})".format(signal)
            elif signal.startswith("GPIO_EXT"):
                # External interrupt:
                # print("External interrupt signal='{0}'".format(signal))
                kicad_type = "input"
                if label == "":
                    tag = signal[5:]
                else:
                    tag = label
                # print("tag='{0}".format(tag))
                name += "({0})".format(tag)
            elif signal.startswith("GPIO_Input"):
                kicad_type = "input"
                if label == "":
                    tag = "GPIN"
                elif label.startswith("USB_OverCurrent"):
                    tag = "USB_OVER_CURRENT"
                elif '[' in label:
                    print("Unhandled Input label '{0}'".format(label))
                    tag = label
                else:
                    tag = label
                name += "({0})".format(tag)
            elif signal.startswith("GPIO_Output"):
                kicad_type = "output"
                if label == "":
                    tag = "GPOUT"
                elif label.startswith("USB_PowerSwitchOn"):
                    tag = "USB_POWER_ON"
                elif '[' in label:
                    if label.startswith("LD"):
                        bracket_index = label.find('[')
                        tag = "NUCELO_{0}_LED".format(label[bracket_index+1:-1].upper())
                    else:
                        print("Unhandled Output label '{0}'".format(label))
                        tag = label
                else:
                    # print("signal[-7:-2]='{0}'".format(signal[-7:-2]))
                    # print("Unrecognized GPIO signal: '{0}'".format(signal))
                    tag = label
                # print("trimmed_name:'{0}' label:'{1}' tag:'{2}'".format(trimmed_name, label, tag))
                name += "({0})".format(tag)
            elif signal.startswith("I2C"):
                # I2C signal:
                if signal.endswith("_SDA") or signal.endswith("_SCL"):
                    kicad_type = "bidirectional"
                else:
                    print("Unrecognized I2C signal: '{0}'".format(signal))
                name += "({0})".format(signal)
            elif signal.startswith("RCC_"):
                if signal.endswith("_IN"):
                    kicad_type = "passive"
                elif signal.endswith("_OUT"):
                    kicad_type = "output"
                else:
                    print("Unrecognized RCC signal: '{0}'".format(signal))
                name += "({0})*".format(signal[4:])
                asterisk_appended = True
            elif signal.startswith("SYS_"):
                kicad_type = "bidirectional"
                name += "({0})*".format(signal[4:])
                asterisk_appended = True
                # print("name='{0}'".format(name))
            elif signal.startswith("TIM"):
                kicad_type = "output"
                name += "({0})".format(signal)
            elif signal.startswith("UART") or signal.startswith("USART"):
                # print("UART signal='{0}'".format(signal))
                if signal.endswith("_RX"):
                    kicad_type = "input"
                elif signal.endswith("_TX"):
                    kicad_type = "output"
                else:
                    print("Unrecognized UART/USART signal: '{0}'".format(signal))
                    kicad_type = "bidirectional"
                name += "({0})".format(signal)
            elif signal.startswith("USB_"):
                kicad_type = "bidirectional"
                if signal.startswith("USB_OTG_FS_"):
                    name += "(USB_OTG_{0})*".format(signal[12:])
                    asterisk_appended = True
                else:
                    print("Unhandled USB signal '{0}'".format(signal))
                    name += "({0})*".format(signal[4:])
                    asterisk_appended = True
            else:
                print("Unhandled I/O signal'{0}' for '{1}'".format(signal, name))
        elif kind == "Power":
            unit = "ZPWR"
            style = "line"
            if name in ("VSS", "VSSA", "GND", "AGND"):
                unit_sort = tuple('G') + position_key
                kicad_type = "power_in"
                name += "(PI)"
            elif name in ("VDD", "AVDD", "VBAT", "VIN", "VREF+", "VDDA", "VCAP_1", "VCAP_2",
                          "VDDUSB", "VDDSDMMC", "E5V"):
                unit_sort = tuple('V') + position_key
                kicad_type = "power_in"
                name += "(PI)"
                side = "left"
            elif name in ("+5V", "+3.3V", "U5V", "IOREF"):
                unit_sort = tuple('V') + position_key
                side = "left"
                kicad_type = "power_out"
                name += "(PO)"
            else:
                unit_sort = tuple('?') + position_key
                print("Unrecognized Power '{0}'".format(name))
        elif kind in ("Reset", "Boot"):
            unit = "YMISC"
            kicad_type = "input"
            style = "line"
            unit_sort = tuple('?') + position_key
        elif kind in ("NC",):
            unit = "YMISC"
            kicad_type = "no_connect"
            unit_sort = tuple('?') + position_key
        else:
            unit = "~"
            unit_sort = tuple("?")
            print("Unrecognized kind='{0}'".format(kind))
        if '[' in label and not asterisk_appended:
            name += "*"

        # if trimmed_name in ("PA7", "PA15", "PA14"):
        #    print("name='{0}' trimmed_name='{1}' position='{2}'".
        #      format(name, trimmed_name, position))

        # Stuff everything into *chip_pin* (i.e. *self*):
        # chip_pin: ChipPin = self
        self.position: str = position
        self.name: str = name
        self.kind: str = kind
        self.trimmed_name: str = trimmed_name
        self.signal: str = signal
        self.label: str = label
        self.unit: str = unit
        self.unit_sort: Tuple[Any, ...] = unit_sort
        self.kicad_type: str = kicad_type
        self.style: str = style
        self.side: str = side
        self.position_key: Tuple[Any, ...] = position_key

    def __format__(self, format: str) -> str:
        """Convert the ChipPin object to a string."""
        chip_pin: ChipPin = self
        position: str = chip_pin.position
        name: str = chip_pin.name
        kind: str = chip_pin.kind
        signal: str = chip_pin.signal
        label: str = chip_pin.label
        return "{0:4} {1:6} {2:15} {3:20} {4}".format(position, name, kind, signal, label)

    def position_set(self, position: str) -> None:
        """Set the ChipPin position."""
        chip_pin: ChipPin = self
        chip_pin.position = position


# IOC:
class IOC:
    """Represents an STM32CubeMX .ioc file."""

    # IOC.__init__():
    def __init__(self, ioc_file_name: str) -> None:
        """Read in and process an ioc file."""
        assert ioc_file_name.endswith(".ioc")
        base_name: str = ioc_file_name[:-4]
        timestamp: float = os.path.getmtime(ioc_file_name)
        mcu_name: str = ""
        board_name: str = ""
        package: str = ""
        ioc_file: Any[IO]
        with open(ioc_file_name, "r") as ioc_file:
            lines: List[str] = ioc_file.read().split('\n')
            line: str
            for line in lines:
                if line.startswith("Mcu.Name="):
                    mcu_name = line[9:]
                    if mcu_name.endswith('x'):
                        mcu_name = mcu_name[:-1]
                elif line.startswith("board="):
                    board_name = line[6:]
                elif line.startswith("Mcu.Package="):
                    package = line[12:]

        # Load values into *ioc*:
        # ioc: IOC = self
        self.base_name: str = base_name
        self.board_name: str = board_name
        self.file_name: str = ioc_file_name
        self.mcu_name: str = mcu_name
        self.package: str = package
        self.timestamp: float = timestamp


# KiCube:
class KiCube:
    """KiCube represents data gleaned from an STM32Cube project."""

    # Kicube.__init__():
    def __init__(self, ioc_file_name: str, stm32cube_csv_file_name: str,
                 mcu_name: str, board_name: str, package: str) -> None:
        """Initialize a KiCube object."""
        kicube: KiCube = self
        cpu_name: str = ""
        footprint: str = ""
        nucleo_bindings: List[Tuple[int, str]] = []
        if len(board_name) > 0:
            # Nucleo board:
            assert board_name.startswith("NUCLEO-")
            cpu_name = board_name[7:]
            nucleo144_bindings: List[Tuple[int, str]] = kicube.nucleo144_bindings_generate(cpu_name)
            nucleo64_bindings: List[Tuple[int, str]]
            nucleo64_bindings = kicube.nucleo64_bindings_generate(cpu_name, ["PC0", "PC1"])
            if isinstance(nucleo144_bindings, list):
                footprint = "NUCLEO144"
                nucleo_bindings = nucleo144_bindings
            elif isinstance(nucleo64_bindings, list):
                footprint = "NUCLEO64"
                nucleo_bindings = nucleo64_bindings
            else:
                assert False
        else:
            # Bare chip:
            assert mcu_name.startswith("STM32")
            cpu_name = mcu_name[5:]
            footprint = package
        # print("cpu_name='{0}'".format(cpu_name))
        # print("footprint='{0}'".format(footprint))

        # Read in *stm32cube_csv_file_name*, break it into *lines* and extract the interesting
        # lines into *all__pins*:
        chip_pins: List[ChipPin] = []
        if not os.path.isfile(stm32cube_csv_file_name):
            print(f"File '{stm32cube_csv_file_name}' does not exist!!!")
            sys.exit(1)
        csv_file: Any[IO]
        with open(stm32cube_csv_file_name, "r") as csv_file:
            lines: List[str] = csv_file.read().splitlines()
            line: str
            for line in lines[1:]:
                chip_pin: ChipPin = ChipPin(line)
                chip_pins.append(chip_pin)
                # print("{0}".format(chip_pin))

        # Stuff *chip_pins* into *cube* (i.e. *self*):
        # kicube: KiCub = self
        self.ioc_file_name: str = ioc_file_name
        self.stm32cube_csv_file_name: str = stm32cube_csv_file_name
        self.chip_pins: List[ChipPin] = chip_pins
        self.cpu_name: str = cpu_name
        self.footprint: str = footprint
        self.nucleo_bindings: List[Tuple[int, str]] = nucleo_bindings
        self.timestamp: float = os.path.getmtime(stm32cube_csv_file_name)
        # print("len(kicube.nucleo_bindings)={0}".format(len(kicube.nucleo_bindings)))

    # KiCube.kipart_genarate():
    def kipart_generate(self, kipart_csv_file_name: str) -> None:
        """Generate a schematic."""
        kicube: KiCube = self
        chip_pins: List[ChipPin] = kicube.chip_pins
        nucleo_bindings: List[Tuple[int, str]] = kicube.nucleo_bindings

        # Sweep through *chip_pins* and build up a table based on
        chip_pins_table: Dict[str, ChipPin] = {}
        chip_pin: ChipPin
        for chip_pin in chip_pins:
            chip_pins_table[chip_pin.trimmed_name] = chip_pin

        nucleo_chip_pins: List[ChipPin] = list()
        nucleo_position: int
        name: str
        for nucleo_position, name in nucleo_bindings:
            if name in ("GND", "AGND", "E5V", "U5V", "+3.3V", "+5V", "AVDD", "VIN", "IOREF"):
                # Power/Ground pin
                chip_pin = ChipPin('"{0}","{1}","Power","",""'.format(nucleo_position, name))
            elif name in ("RESET"):
                chip_pin = ChipPin('"{0}","{1}","Reset","",""'.format(nucleo_position, name))
            elif name.startswith("NC"):
                chip_pin = ChipPin('"{0}","{1}","NC","",""'.format(nucleo_position, name))
            elif name in chip_pins_table:
                chip_pin = chip_pins_table[name]
                chip_pin.position_set(str(nucleo_position))
            else:
                print("Need to deal with nucleo_pin: '{0}'".format(name))
            nucleo_chip_pins.append(chip_pin)
        # print("len(nucleo_chip_pins)={0}".format(len(nucleo_chip_pins)))

        # Sort *nucleo_chip_pins* using the group key:
        nucleo_chip_pins.sort(key=lambda chip_pin: (chip_pin.unit, chip_pin.unit_sort))
        ioc_file_name: str = kicube.ioc_file_name
        base_name: str = ioc_file_name[:-4].upper()
        foot_print: str = kicube.footprint.upper()
        # print("kicad_part_name='{0}'".format(kicad_part_name))

        # Construct the file as a list of *lines*.
        lines: List[str] = []
        line_format: str = '"{0}", "{1}", "{2}", "{3}", "{4}", "{5}"\n'

        # Output the first line which is a comma separated list of values:
        #     SYMBOL_NAME,REF_PREFIX,FOOTPRINT,DATA_SHEET_URL,SHORT_DESCRIPTION;LONG_DESCRIPTION
        symbol_name: str = f"{base_name};{foot_print}"
        data_sheet_url: str = ("https://www.st.com/resource/en/user_manual/" +
                               "dm00244518-stm32-nucleo144-boards-stmicroelectronics.pdf")
        manufacturer_number: str = f"{foot_print}-{base_name}"
        description: str = f"NUCLEO144-{base_name};Nucleo144 STM32{base_name}"
        lines.append(line_format.format(symbol_name, "CN", foot_print, data_sheet_url,
                                        manufacturer_number, description))
        lines.append(line_format.format("Pin", "Unit", "Type", "Name", "Style", "Side"))

        for nucleo_chip_pin in nucleo_chip_pins:
            position = nucleo_chip_pin.position
            unit: str = nucleo_chip_pin.unit
            kicad_type: str = nucleo_chip_pin.kicad_type
            name = nucleo_chip_pin.name
            style: str = nucleo_chip_pin.style
            side: str = nucleo_chip_pin.side
            line: str = line_format.format(position, unit, kicad_type, name, style, side)
            lines.append(line)

        # Terminate the file with ",,,,,," and a blank line:
        lines.append(",,,,,,\n")
        lines.append("\n")

        kipart_csv_file: IO[Any]
        with open(kipart_csv_file_name, "w") as kipart_csv_file:
            kipart_csv_file.writelines(lines)

        # print("calling kipart...")
        # lib_file_name: str = "{0}_{1}.lib".format(kicube.base_name.upper(),
        #                                           kicube.footprint.upper())
        # subprocess.call(
        #   ("kipart", kipart_csv_file_name, "--overwrite", "-o", lib_file_name))
        # print("kipart called...")

        # Read *lib_file_name* in:
        # schematic_library: SchematicLibrary = SchematicLibrary(lib_file_name)
        # cpu_symbol = schematic_library.lookup(kicad_part_name)
        # cpu_symbol.fixup()
        # output_library.insert(cpu_symbol)

    # KiCube.nucleo144_bindings_generate():
    def nucleo144_bindings_generate(self, processor: str) -> List[Tuple[int, str]]:
        """Return list of Nucleo-144 pin bindings."""
        nucleo144_mcus: List[str] = [
          "F207ZG",
          "F303ZE",        # FIXME: This one may be slightly different!!!
          "F412ZG",
          "F413ZG",
          "F429ZI",
          "F746ZG",
          "F767ZI",
          "H743ZI",
        ]

        nucleo144_bindings: List[Tuple[int, str]] = []
        if processor in nucleo144_mcus:
            nucleo144_bindings = [
              (1101, "PC10"),  (1102, "PC11"),  (1201, "PC9"),  (1202, "PC8"),
              (1103, "PC12"),  (1104, "PD2"),   (1203, "PB8"),  (1204, "PC6"),
              (1105, "VDD"),   (1106, "E5V"),   (1205, "PB9"),  (1206, "PC5"),
              (1107, "BOOT0"), (1108, "GND"),   (1207, "AVDD"), (1208, "U5V"),
              (1109, "PF6"),   (1110, "NC1"),   (1209, "GND"),  (1210, "PD8"),
              (1111, "PF7"),   (1112, "IOREF"), (1211, "PA5"),  (1212, "PA12"),
              (1113, "PA13"),  (1114, "RESET"), (1213, "PA6"),  (1214, "PA11"),
              (1115, "PA14"),  (1116, "+3.3V"), (1215, "PA7"),  (1216, "PB12"),
              (1117, "PA15"),  (1118, "+5V"),   (1217, "PB6"),  (1218, "PB11"),
              (1119, "GND"),   (1120, "GND"),   (1219, "PC7"),  (1220, "GND"),
              (1121, "PB7"),   (1122, "GND"),   (1221, "PA9"),  (1222, "PB2"),
              (1123, "PC13"),  (1124, "VIN"),   (1223, "PA8"),  (1224, "PB1"),
              (1125, "PC14"),  (1126, "NC2"),   (1225, "PB10"), (1226, "PB15"),
              (1127, "PC15"),  (1128, "PA0"),   (1227, "PB4"),  (1228, "PB14"),
              (1129, "PH0"),   (1130, "PA1"),   (1229, "PB5"),  (1230, "PB13"),
              (1131, "PH1"),   (1132, "PA4"),   (1231, "PB3"),  (1232, "AGND"),
              (1133, "VBAT"),  (1134, "PB0"),   (1233, "PA10"), (1234, "PC4"),
              (1135, "PC2"),   (1136, "PC1"),   (1235, "PA2"),  (1236, "PF5"),
              (1137, "PC3"),   (1138, "PC0"),   (1237, "PA3"),  (1238, "PF4"),
              (1139, "PD4"),   (1140, "PD3"),   (1239, "GND"),  (1240, "PE8"),
              (1141, "PD5"),   (1142, "PG2"),   (1241, "PD13"), (1242, "PF10"),
              (1143, "PD6"),   (1144, "PG3"),   (1243, "PD12"), (1244, "PE7"),
              (1145, "PD7"),   (1146, "PE2"),   (1245, "PD11"), (1246, "PD14"),
              (1147, "PE3"),   (1148, "PE4"),   (1247, "PE10"), (1248, "PD15"),
              (1149, "GND"),   (1150, "PE5"),   (1249, "PE12"), (1250, "PF14"),
              (1151, "PF1"),   (1152, "PF2"),   (1251, "PE14"), (1252, "PE9"),
              (1153, "PF0"),   (1154, "PF8"),   (1253, "PE15"), (1254, "GND"),
              (1155, "PD1"),   (1156, "PF9"),   (1255, "PE13"), (1256, "PE11"),
              (1157, "PD0"),   (1158, "PG1"),   (1257, "PF13"), (1258, "PF3"),
              (1159, "PG0"),   (1160, "GND"),   (1259, "PF12"), (1260, "PF15"),
              (1161, "PE1"),   (1162, "PE6"),   (1261, "PG14"), (1262, "PF11"),
              (1163, "PG9"),   (1164, "PG15"),  (1263, "GND"),  (1264, "PE0"),
              (1165, "PG12"),  (1166, "PG10"),  (1265, "PD10"), (1266, "PG8"),
              (1167, "NC3"),   (1168, "PG13"),  (1267, "PG7"),  (1268, "PG5"),
              (1169, "PD9"),   (1170, "PG11"),  (1269, "PG4"),  (1270, "PG6")]

            # Sort the *nucleo144_bindings*:
            key: str
            nucleo144_bindings.sort(key=lambda binding: binding[0])

        return nucleo144_bindings

    # KiCube.nucleo64_bindings_generate():
    def nucleo64_bindings_generate(self, processor: str, pin_selects) -> List[Tuple[int, str]]:
        """Return the Nucleo64 pin bindings for a proceesor."""
        assert isinstance(processor, str)
        assert isinstance(pin_selects, list)
        # print("KiCube.nucleo64_bindings_generate(*, '{0}", "{1}')".format(processor, pin_selects))

        cpu_mapping = {
          "F030R8": "F030R8",
          "F070RB": "F070RB",
          "F334R8": "F334R8",
          "F303RE": "F334R8",
          "F091RC": "F334R8",
          "F072RB": "F334R8",
          "F103RB": "F103RB",
          "F302RB": "F302RB",
          "F401RE": "F446RE",
          "F411RE": "F446RE",
          "F446RE": "F446RE",
          "L053R8": "L152RE",
          "L073RZ": "L152RE",
          "L152RE": "L152RE",
          "L452RE": "L452RE",
          "L476RG": "L476RG",
          "F410RB": "L410RB"
        }

        nucleo64_bindings: List[Tuple[int, str]] = []
        pin_bindings: List[Tuple[int, str, List[Tuple[str, ...]]]]
        if processor in cpu_mapping:
            pin_bindings = [
                (701, "PC10", []),
                (703, "PC12", []),
                (705, "VDD", []),
                (707, "BOOT0", [("PH3:BT0", "L452RE")]),
                (709, "NC1", [("PF6", "F030R8")]),
                (711, "NC2", [("PF7", "F030R8")]),
                (713, "PA13", []),
                (715, "PA14", []),
                (717, "PA15", []),
                (719, "GND", []),
                (721, "PB7", []),
                (723, "PC13", []),
                (725, "PC14", []),
                (727, "PC15", []),
                (729, "PF0", [("PD0", "F103RB"),
                              ("PH0", "F446RE", "L152RE", "L452RE", "F476RG", "F410RB")]),
                (731, "PF1", [("PD1", "F103RB"),
                              ("PH1", "F446RE", "L152RE", "L452RE", "F476RG", "F410RB")]),
                (733, "VBAT", [("VDD", "F070RB"), ("VLCD", "L152RE")]),
                (735, "PC2", []),
                (737, "PC3", []),
                (702, "PC11", []),
                (704, "PD2", []),
                (706, "E5V", []),
                (708, "GND", []),
                (710, "NC3", []),
                (712, "IOREF", []),
                (714, "RESET", []),
                (716, "+3.3V", []),
                (718, "+5V", []),
                (720, "GND", []),
                (722, "GND", []),
                (724, "VIN", []),
                (726, "NC4", []),
                (728, "PA0", []),
                (730, "PA1", []),
                (732, "PA4", []),
                (734, "PB0", []),
                (736, "PC1:PB9", []),
                (738, "PC0:PB8", []),
                (1001, "PC9", []),
                (1003, "PB8", []),
                (1005, "PB9", []),
                (1007, "AVDD", []),
                (1009, "GND", []),
                (1011, "PA5", [("PB13", "F302R8")]),
                (1013, "PA6", [("PB14", "F302R8")]),
                (1015, "PA7", [("PB15", "F302R8")]),
                (1017, "PB6", []),
                (1019, "PC7", []),
                (1021, "PA9", []),
                (1023, "PA8", []),
                (1025, "PB10", []),
                (1027, "PB4", []),
                (1029, "PB5", []),
                (1031, "PB3", []),
                (1033, "PA10", []),
                (1035, "PA2", []),
                (1037, "PA3", []),
                (1002, "PC8", []),
                (1004, "PC6", []),
                (1006, "PC5", []),
                (1008, "U5V", []),
                (1010, "NC5", []),
                (1012, "PA12", []),
                (1014, "PA11", []),
                (1016, "PB12", []),
                (1018, "PB11", []),
                (1020, "GND", []),
                (1022, "PB2", []),
                (1024, "PB1", []),
                (1026, "PB15", [("PA7", "F302R8")]),
                (1028, "PB14", [("PA6", "F302R8")]),
                (1030, "PB13", [("PA5", "F302R8")]),
                (1032, "AGND", []),
                (1034, "PC4", []),
                (1036, "NC6", [("PF5", "F030R8")]),
                (1038, "NC7", [("PF4", "F030R8")]),
            ]

            # mapped_processor: Dict[str, str] = cpu_mapping[processor]
            pin_binding: Tuple[int, str, List[Tuple[str, ...]]]
            for pin_binding in pin_bindings:
                # print(pin_binding)
                pin_number: int = pin_binding[0]
                name: str = pin_binding[1]
                alternate_pin_bindings: List[Tuple[str, ...]] = pin_binding[2]
                alternate_pin_binding: Tuple[str, ...]
                for alternate_pin_binding in alternate_pin_bindings:
                    assert len(alternate_pin_binding) >= 2
                    alternate_name: str = alternate_pin_binding[0]
                    alternate_processors: Tuple[str, ...] = alternate_pin_binding[1:]
                    alternate_processor: str
                    for alternate_processor in alternate_processors:
                        # print(alternate_processor)
                        if processor == alternate_processor:
                            name = alternate_name

                # Force a name selection for pins that can be bridged to alternate pins:
                if ':' in name:
                    name1: str
                    name2: str
                    name1, name2 = name.split(':')
                    if name1 in pin_selects:
                        name = name1
                    elif name2 in pin_selects:
                        name = name2
                    else:
                        assert False, "You must pick between '{0}' and '{1}'".format(name1, name2)

                # Add the binding to *nucleo64_bindings*:
                nucleo64_bindings.append((pin_number, name))

            # Sort the result:
            nucleo64_bindings.sort(key=lambda binding: binding[0])

            debug = False
            # debug = True
            if debug:
                for index, binding in enumerate(nucleo64_bindings):
                    pin_number, name = binding
                    print("[{0}] {1} '{2}'".format(index, pin_number, name))

        # print("len(nucleo64_bindings)={0}".format(len(nucleo64_bindings)))
        return nucleo64_bindings


# SchematicLibaray:
class SchematicLibrary:
    """Represents a KiCad schematic symbol library."""

    # SchematicLibrary.__init__():
    def __init__(self, file_name: str) -> None:
        """Initialize SchematicLibary object.

        Args:
            *library_file_name* (*str*):
             The `.lib` file to open and read in.

        """
        # Verify argument types:
        assert file_name.endswith(".lib")
        # print("SchematicLibrary.__init__(*, '{0}')".format(file_name))

        # Start with an empty *symbols_table*:
        # schematic_library SchematicLibrary = self
        symbols_table: Dict[str, SchematicSymbol] = dict()
        self.symbols_table = symbols_table

        # Open *schematic_library_file_name* and break it into *lines*:
        library_file: IO[Any]
        with open(file_name, "r") as library_file:
            lines: List[str] = library_file.read().split('\n')

            # Sweep through *lines* looking for first/last lines a schematic symbol definition:
            def_line_index: int = -1
            line: str
            for line_index, line in enumerate(lines):
                # print("[{0}]: '{1}'".format(line_index, line))
                if line.startswith("DEF "):
                    # Found first line of schematic symbol definition:
                    def_line_index = line_index
                elif line.startswith("ENDDEF"):
                    # Found last line of schematic symbol defintion:
                    assert def_line_index >= 0
                    symbol: SchematicSymbol = SchematicSymbol(lines[def_line_index:line_index + 1])
                    symbol_name: str = symbol.name
                    assert symbol not in symbols_table
                    symbols_table[symbol_name] = symbol
                    def_line_index = -1

    # SchematicLibrary.insert():
    def insert(self, schematic_symbol: "SchematicSymbol") -> None:
        """Insert schematic symbol into a library."""
        assert isinstance(schematic_symbol, SchematicSymbol)
        schematic_library: SchematicLibrary = self
        symbols_table: Dict[str, SchematicSymbol] = schematic_library.symbols_table
        symbol_name: str = schematic_symbol.name
        symbols_table[symbol_name] = schematic_symbol

    # SchematicLibrary.fixup():
    def fixup(self) -> None:
        """Fixup a schematic library."""
        schematic_library: SchematicLibrary = self
        symbols_table: Dict[str, SchematicSymbol] = schematic_library.symbols_table
        symbol: SchematicSymbol
        for symbol in symbols_table.values():
            symbol.fixup()

    # SchematicLibrary.lookup():
    def lookup(self, part_name) -> "SchematicSymbol":
        """Lookup a schematic symbol by part name."""
        schematic_library: SchematicLibrary = self
        symbols_table: Dict[str, SchematicSymbol] = schematic_library.symbols_table
        assert part_name in symbols_table
        symbol: SchematicSymbol = symbols_table[part_name]
        return symbol

    # SchematicLibrary.write():
    def write(self, lib_file_name: str) -> None:
        """Write a schematic library out to a file."""
        # print("SchematicLibrary.write('{0}')".format(lib_file_name))

        # Create a sorted list of *symbols*:
        schematic_library: SchematicLibrary = self
        symbols_table: Dict[str, SchematicSymbol] = schematic_library.symbols_table
        symbols: List[SchematicSymbol] = list(symbols_table.values())
        symbol: SchematicSymbol
        symbols.sort(key=lambda symbol: symbol.name)

        # Open *lib_file_name*:
        lib_file: IO[Any]
        with open(lib_file_name, "w") as lib_file:
            # Write out the header:
            lib_file.write("EESchema-LIBRARY Version 2.3\n")
            lib_file.write("#encoding utf-8\n")

            # Output all of the *symbols* in sorted order:
            for symbol in symbols:
                symbol.write(lib_file)

            # Terminate the library:
            lib_file.write("#\n")
            lib_file.write("#End Library\n")


# SchematicSymbol:
class SchematicSymbol:
    """Represents a schematic symbol."""

    # SchematicSymbol.__init__():
    def __init__(self, lines: List[str]) -> None:
        """Initialize a SchematicSymbol."""
        first_line: str = lines[0]
        last_line: str = lines[-1]
        assert first_line.startswith("DEF"), "first_line='{0}'".format(first_line)
        assert last_line.startswith("ENDDEF"), "last_line='{0}'".format(last_line)
        first_line_trimmed: str = first_line[4:]
        space_index: int = first_line_trimmed.find(' ')
        assert space_index >= 0
        name: str = first_line_trimmed[:space_index]

        # schematic_symbol: SchematicSymbol = self
        self.lines: List[str] = lines
        self.name: str = name
        # print("second_space_index='{0}'".format(first_line))
        # print("first_line='{0}'".format(first_line))
        # print("Created Symbol '{0}'".format(name))

    # SchematicSymbol.fixup():
    def fixup(self) -> None:
        """Fix up a Sechemtaic symbol."""
        # Insert the "F2 ..." and "F3 ..." lines into *lines*
        symbol: SchematicSymbol = self
        lines: List[str] = symbol.lines
        line_index: int
        line: str
        for line_index, line in enumerate(lines):
            if line.startswith("F1"):
                lines.insert(line_index + 1, 'F2 "" 0 0 50 H I C CNN')
                lines.insert(line_index + 2, 'F3 "" 0 0 50 H I C CNN')
                break

        # Sweep through *lines* performing minor tweaks:
        for line_index, line in enumerate(lines):
            initial_line = line
            # Change reference label from U to N:
            if line.startswith('F0 "U"'):
                line = 'F0 "N"' + line[6:]

            # Turn on background highlighting for rectangles:
            if line.startswith("S ") and line.endswith(" N"):
                line = line[:-1] + "f N"

            # Force font sizes from 60 down to 50:
            if line.endswith("60 H V L CNN"):
                line = line[:-12] + "50 H V L CNN"

            # Update any *line* that changed:
            if initial_line != line:
                # print("'{0}' => '{1}'".format(initial_line, line))
                lines[line_index] = line

    # SchematicSymbol.write():
    def write(self, schematic_library_output_file: IO[Any]) -> None:
        """Write a SechematicySymbol out to an open file."""
        schematic_symbol: SchematicSymbol = self
        schematic_library_output_file.write("#\n")
        schematic_library_output_file.write("# {0}\n".format(schematic_symbol.name))
        schematic_library_output_file.write("#\n")
        schematic_library_output_file.write('\n'.join(schematic_symbol.lines))
        schematic_library_output_file.write('\n')


if __name__ == "__main__":
    main()
