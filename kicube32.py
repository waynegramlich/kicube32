#!/usr/bin/env python

####################################################################################################
#-------------------------------------- 100 characters ------------------------------------------->|

# Usage:
#
#        kicube32.py -o libary_name.lib ioc_file1.ioc ioc_file2 ...
#
# The following `sed` command will turn on background highlighting:
#
#        sed -i -E 's/S (.*) N/S \1 f N/' cube.lib

import os
import subprocess
import sys

def main():
    output_library_file_name = ""

    # Parse the command line *arguments*:
    arguments = sys.argv[1:]
    arguments_size = len(arguments)
    argument_index = 0
    iocs = list()
    while argument_index < arguments_size:
	argument = arguments[argument_index]
	if argument.endswith(".ioc"):
	    # Collect file names that end in `.ioc` in *ioc_file_names* list:
	    ioc = IOC(argument)
	    iocs.append(ioc)
	elif argument == "-o":
	    # Make sure that on one `-o` option is specified:
	    if len(output_library_file_name) > 0:
		print("Duplicate -o command specified on command line")
                return 1

	    # Fetch the argument after the `-o`:
	    argument_index += 1
	    if argument_index >= arguments_size:
		print("No argument after -o on command line")
		return 1
	    output_library_file_name = arguments[argument_index]
	else:
	    print("Unrecognized command line argument '{0}'".format(argument))
	    return 1

	# Advance to next argument:
	argument_index += 1

    # Do some additonal command line checking:
    if len(iocs) ==  0:
        print("No .ioc files specified on command line")
        return 1
    if len(output_library_file_name) == 0:
        print("No -o command specified on command line.")
	return 1

    # Read in *output_schematic_library*:
    output_library = SchematicLibrary(output_library_file_name)

    # Process all of the *ioc_file_names*:
    #print("ioc_file_names=", ioc_file_names)
    for ioc in iocs:
	# Read in the `.csv` file associated with *ioc* into *kicube*:
	base_name = ioc.base_name
	board_name = ioc.board_name
	mcu_name = ioc.mcu_name
	package = ioc.package
	#print("base_name='{0}'".format(base_name))
	#print("mcu_name='{0}'".format(mcu_name))
	#print("board_name='{0}".format(board_name))
	#print("package='{0}".format(package))
	kicube = KiCube(base_name, mcu_name, board_name, package)

	# Verify timestamps:
	if ioc.timestamp >= kicube.timestamp:
	    print("File '{0}' has changed! Please update file '{1}'!!!".
	      format(ioc.file_name, kicbube.file_name))
	    return 1

	kicube.schematic_generate(output_library)
	    
    # Write out the updated *output_library*:
    output_library.write(output_library_file_name)

class ChipPin:
    """ *ChipPin*: Represents information about one physical microcontroller pin.
    """

    def __init__(self, line):
	""" *ChipPin*: Initialize *ChipPin* object (i.e. *self*).

	The arguments are:
	* *line* (str): One line from a `.csv` file of the form '"P","N","K","S","L"', where:
	  * "P" is name of the physical the chip pin (e.g 'B12', '3', '29', etc.)
	  * "N" is the vendor logical name for the chip pin (e.g. 'PB3', 'VSS', 'NRST', etc.)
	  * "K" is the electrical kind of the chip pin (e.g. "Power", "I/O", "Input", etc.)
	  * "S" is the internal signal name for chip pin (e.g. 'UART7_RX', etc.)
	  * "L" is some additional information about the pin, usually for GPI pins.
	These values are stuffed into driectly into attributes named *position*, *name*,
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
	#print("line={0}".format(line))

	# Split *line* into *fields* and break them out into *position*, *name*, *kind*, etc.:
	fields = tuple(line.replace('"', "").split(','))
	assert len(fields) == 5, "line='{0} fields={1}'".format(line, fields)
	position, name, kind, signal, label = fields

	# Compute *trimmed_name* which is *name* with everything after the '/' or '-' removed:
	slash_index = name.find('/')
	hypen_index = name.find('-')
	trim_index = max(slash_index, hypen_index)
	trimmed_name = name if trim_index < 0 else name[:trim_index]

	# Create *position_key* from *position* and stuff into *chip_pin*:
	if position[0].isalpha():
	    # We have a ball grid pin:
	    assert position[1:].isdigit()
	    position_key = (position[0], int(position[1:]))
	else:
	    # We have a more standard numerical pin:
	    assert position.isdigit()
	    position_key = tuple(position)

	# Figure out which ...
	asterisk_appended = False
	kicad_type = "no_connect"
	style = "non_logic"
	side = "right"
	if kind in ("I/O", "Input", "Output"): # or (name[0] == 'P' and name[2].isdigit() ):
	    # Parse out the Port name"
	    if ( len(trimmed_name) >= 3 and trimmed_name[0] == 'P' and
	     trimmed_name[1].isalpha() and trimmed_name[2:].isdigit() ):
		# We have a port name:
		unit = trimmed_name[:2]
		unit_sort = int(trimmed_name[2:])
	    else:
		unit = "?"
		unit_sort = "?"
		print("Unknown I/O name '{0}' (trimmed_name = '{1}')".format(name, trimmed_name))

	    style = "line"
	    if signal == "":
		# Unused:	
		kicad_type = "no_connect"
	    elif signal.startswith("ETH_"):
		kicad_type = "bidirectional"
		name += "({0})".format(signal)
	    elif signal.startswith("GPIO_"):
		if signal.endswith("_Input"):
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
		elif signal.endswith("_Output"):
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
			tag = label
		elif len(signal) >= 7 and signal[-7:-2] == "_EXTI":
		    # External interrupt:
		    kicad_type = "input"
		    tag = signal[-6:-1]
		    #print("tag='{0}".format(tag))
		else:
		    #print("signal[-7:-2]='{0}'".format(signal[-7:-2]))
		    print("Unrecognized GPIO signal: '{0}'".format(signal))
		    tag = "?"
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
		#print("name='{0}'".format(name))
	    elif signal.startswith("TIM"):
		kicad_type = "output"
		name += "({0})".format(signal)
	    elif signal.startswith("UART") or signal.startswith("USART"):
		#print("UART signal='{0}'".format(signal))
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
	    unit_sort = "?"
	    print("Unrecognized kind='{0}'".format(kind))
	if '[' in label and not asterisk_appended:
	    name += "*"

	# Stuff everything into *chip_pin* (i.e. *self*):
	chip_pin = self
	chip_pin.position = position
	chip_pin.name = name
	chip_pin.kind = kind
	chip_pin.trimmed_name = trimmed_name
	chip_pin.signal = signal
	chip_pin.label = label
	chip_pin.unit = unit
	chip_pin.unit_sort = unit_sort
	chip_pin.kicad_type = kicad_type
	chip_pin.style = style
	chip_pin.side = side
	chip_pin.position_key = position_key

    def __format__(self, format):
	""" *ChipPin*: Format the *ChipPin* object (i.e. *self*.)
	"""

	# Verify types:
	assert isinstance(format, str)

	chip_pin = self
	position = chip_pin.position
	name = chip_pin.name
	kind = chip_pin.kind
	signal = chip_pin.signal
	label = chip_pin.label
	return "{0:4} {1:6} {2:15} {3:20} {4}".format(
	  position, name, kind, signal, label)

class IOC:
    def __init__(self, ioc_file_name):
        assert isinstance(ioc_file_name, str)
	assert ioc_file_name.endswith(".ioc")
	base_name = ioc_file_name[:-4]
	timestamp = os.path.getmtime(ioc_file_name)
	mcu_name = ""
	board_name = ""
	package = ""
	with open(ioc_file_name, "r") as ioc_file:
	    lines = ioc_file.read().split('\n')
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
	ioc = self
	ioc.base_name = base_name
	ioc.board_name = board_name
	ioc.file_name = ioc_file_name
	ioc.mcu_name = mcu_name
	ioc.package = package
	ioc.timestamp = timestamp

class KiCube:
    """ *KiCube*: Represents data gleaned from an STM32Cube project.
    """

    def __init__(self, base_name, mcu_name, board_name, package):
	""" *KiCube*: Initialize the *Cube* object (i.e. *self*.)
	"""

	# Verify argument types*:
	assert isinstance(base_name, str)
	assert isinstance(mcu_name, str)
	assert isinstance(board_name, str)
	assert isinstance(package, str)

	#print("KiCube.__init__(*, '{0}', '{1}', '{2}', '{3}')".
	#  format(base_name, mcu_name, board_name, package))

	kicube = self
	csv_file_name = base_name + ".csv"
	cpu_name = ""
	footprint = ""
	nucleo_bindings = None
	if len(board_name) > 0:
	    # Nucleo board:
	    assert board_name.startswith("NUCLEO-")
	    cpu_name = board_name[7:]
	    nucleo144_bindings = kicube.nucleo144_bindings_generate(cpu_name)
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
	    assert mcu_name.startsiwth("STM32")
	    cpu_name = mcu_name[5:]
	    footprint = package
	#print("cpu_name='{0}'".format(cpu_name))
	#print("footprint='{0}'".format(footprint))

	kipart_part_name = cpu_name + ";" + footprint
	lib_file_name = cpu_name + "_" + footprint + ".lib"

	# Read in *ioc_txt_file_name*, break it into *lines* and extract the interesting
        # lines into *all__pins*:
	chip_pins = list()
	if not os.path.isfile(csv_file_name):
	    print("File '{0}' does not exist!!!".format(csv_file_name))
	    sys.exit(1)
	with open(csv_file_name, "r") as csv_file:
	    lines = csv_file.read().splitlines()
	    for line in lines[1:]:
		chip_pin = ChipPin(line)
		chip_pins.append(chip_pin)
		#print("{0}".format(chip_pin))

	kicube = self

	# Stuff *chip_pins* into *cube* (i.e. *self*):
	kicube.base_name = base_name
	kicube.csv_file_name = csv_file_name
	kicube.chip_pins = chip_pins
	kicube.cpu_name = cpu_name
	kicube.footprint = footprint
	kicube.nucleo_bindings = nucleo_bindings
	kicube.timestamp = os.path.getmtime(csv_file_name)	
	#print("len(kicube.nucleo_bindings)={0}".format(len(kicube.nucleo_bindings)))

    def schematic_generate(self, output_library):
	""" *KiCube*:
	"""

	#assert isinstance(part_name, str)
	#assert isinstance(output_csv_file_name, str)
	#print("=>KiCube.schematic_generate(*, '{0}', '{1}')".
	#  format(part_name, output_csv_file_name))

	kicube = self
	chip_pins = kicube.chip_pins
	nucleo_bindings = kicube.nucleo_bindings
	assert isinstance(nucleo_bindings, list)

	# Sweep through *chip_pins* and build up a table based on 
	chip_pins_table = dict()
	for chip_pin in chip_pins:
	    chip_pins_table[chip_pin.trimmed_name] = chip_pin

	nucleo_chip_pins = list()
	for position, name in nucleo_bindings:
	    if name in ("GND", "AGND", "E5V", "U5V", "+3.3V", "+5V", "AVDD", "VIN", "IOREF"):
		# Ground pin
		chip_pin = ChipPin('"{0}","{1}","Power","",""'.format(position, name))
	    elif name in ("RESET"):
		chip_pin = ChipPin('"{0}","{1}","Reset","",""'.format(position, name))
	    elif name.startswith("NC"):
		chip_pin = ChipPin('"{0}","{1}","NC","",""'.format(position, name))
	    elif name in chip_pins_table:
		chip_pin = chip_pins_table[name]
		chip_pin.position = position
    	    else:
		print("Need to deal with nucleo_pin: '{0}'".format(name))
	    nucleo_chip_pins.append(chip_pin)
	#print("len(nucleo_chip_pins)={0}".format(len(nucleo_chip_pins)))

	# Sort *nucleo_chip_pins* using the group key:
	nucleo_chip_pins.sort( key=lambda chip_pin: (chip_pin.unit, chip_pin.unit_sort) )

	kicad_part_name = (kicube.base_name + ';' + kicube.footprint).upper()
	print("kicad_part_name='{0}'".format(kicad_part_name))

	lines = list()
	lines.append("{0}\n".format(kicad_part_name))
	line_format = '"{0}", "{1}", "{2}", "{3}", "{4}", "{5}"\n'
	lines.append(line_format.format("Pin", "Unit", "Type", "Name", "Style", "Side"))

	for nucleo_chip_pin in nucleo_chip_pins:
	    position = nucleo_chip_pin.position
	    unit = nucleo_chip_pin.unit
	    kicad_type = nucleo_chip_pin.kicad_type
	    name = nucleo_chip_pin.name
	    style = nucleo_chip_pin.style
	    side = nucleo_chip_pin.side
	    line = line_format.format(position, unit, kicad_type, name, style, side)
	    lines.append(line)

	kipart_csv_file_name = kicube.base_name + "_kipart.csv"
	with open(kipart_csv_file_name, "w") as kipart_csv_file:
	    kipart_csv_file.writelines(lines)

	#print("calling kipart...")
	lib_file_name = "{0}_{1}.lib".format(kicube.base_name.upper(), kicube.footprint.upper())
	subprocess.call(
	  ("kipart", kipart_csv_file_name, "--overwrite", "-o", lib_file_name))
	#print("kipart called...")

	# Read *lib_file_name* in:
	schematic_library = SchematicLibrary(lib_file_name)
	cpu_symbol = schematic_library.lookup(kicad_part_name)
	print("before fixup")
	print('\n'.join(cpu_symbol.lines[0:25]))
	cpu_symbol.fixup()
	print("after fixup")
	print('\n'.join(cpu_symbol.lines[0:25]))
	output_library.insert(cpu_symbol)

    def nucleo144_bindings_generate(self, processor):
	# Verify argument types:
        assert isinstance(processor, str)
	#print("KiCube.nucleo144_bindings_generate(*, '{0}')".format(processor))

	nucleo144_mcus = [
	  "F207ZG",
	  "F303ZE",	#FIXME: This one may be slightly different!!!
	  "F412ZG",
	  "F413ZG",
	  "F429ZI",
	  "F746ZG",
	  "F767ZI",
	  "H743ZI",
        ]

	nucleo144_bindings = None
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
	      (1169, "PD9"),   (1170, "PG11"),  (1269, "PG4"),  (1270, "PG6") ]

	    # Sort the *nucleo144_bindings*:
	    nucleo144_bindings.sort(key = lambda binding: binding[0])

	return nucleo144_bindings

    def nucleo64_bindings_generate(self, processor, pin_selects):
	assert isinstance(processor, str)
	assert isinstance(pin_selects, list)
	#print("KiCube.nucleo64_bindings_generate(*, '{0}", "{1}')".format(processor, pin_selects))

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

	nucleo64_bindings = None
	if processor in cpu_mapping:
	    pin_bindings = [
	      (701, "PC10"),
	      (703, "PC12"),
	      (705, "VDD"),
	      (707, "BOOT0", ("PH3:BT0", "L452RE")),
	      (709, "NC1", ("PF6", "F030R8")),
	      (711, "NC2", ("PF7", "F030R8")),
	      (713, "PA13"),
	      (715, "PA14"),
	      (717, "PA14"),
	      (719, "GND"),
	      (721, "PB7"),
	      (723, "PC13"),
	      (725, "PC14"),
	      (727, "PC15"),
	      (729, "PF0",
	        ("PD0", "F103RB"), ("PH0", "F446RE", "L152RE", "L452RE", "F476RG", "F410RB")),
	      (731, "PF1",
	        ("PD1", "F103RB"), ("PH1", "F446RE", "L152RE", "L452RE", "F476RG", "F410RB")),
	      (733, "VBAT", ("VDD", "F070RB"), ("VLCD", "L152RE")),
	      (735, "PC2"),
	      (737, "PC3"),
	      (702, "PC11"),
	      (704, "PD2"),
	      (706, "E5V"),
	      (708, "GND"),
	      (710, "NC3"),
	      (712, "IOREF"),
	      (714, "RESET"),
	      (716, "+3.3V"),
	      (718, "+5V"),
	      (720, "GND"),
	      (722, "GND"),
	      (724, "VIN"),
	      (726, "NC4"),
	      (728, "PA0"),
	      (730, "PA1"),
	      (732, "PA4"),
	      (734, "PB0"),
	      (736, "PC1:PB9"),
	      (738, "PC0:PB8"),
	      (1001, "PC9"),
	      (1003, "PB8"),
	      (1005, "PB9"),
	      (1007, "AVDD"),
	      (1009, "GND"),
	      (1011, "PA5", ("PB13", "F302R8")),
	      (1013, "PA6", ("PB14", "F302R8")),
	      (1015, "PB6", ("PB15", "F302R8")),
	      (1017, "PB6"),
	      (1019, "PC7"),
	      (1021, "PA9"),
	      (1023, "PA8"),
	      (1025, "PB10"),
	      (1027, "PB4"),
	      (1029, "PB5"),
	      (1031, "PB3"),
	      (1033, "PA10"),
	      (1035, "PA2"),
	      (1037, "PA3"),

	      (1002, "PC8"),
	      (1004, "PC6"),
	      (1006, "PC5"),
	      (1008, "U5V"),
	      (1010, "NC5"),
	      (1012, "PA12"),
	      (1014, "PA11"),
	      (1016, "PB12"),
	      (1018, "PB11"),
	      (1020, "GND"),
	      (1022, "PB2"),
	      (1024, "PB1"),
	      (1026, "PB15", ("PA7", "F302R8")),
	      (1028, "PB14", ("PA6", "F302R8")),
	      (1030, "PB13", ("PA5", "F302R8")),
	      (1032, "AGND"),
	      (1034, "PC4"),
	      (1036, "NC6", ("PF5", "F030R8")),
	      (1038, "NC7", ("PF4", "F030R8")),
	    ]

	    mapped_processor = cpu_mapping[processor]

	    nucleo64_bindings = list()
	    for pin_binding in pin_bindings:
		#print(pin_binding)
		pin_number = pin_binding[0]
		name = pin_binding[1]
		alternate_pin_bindings = pin_binding[2:]
		for alternate_pin_binding in alternate_pin_bindings:
		    alternate_name = alternate_pin_binding[0]
		    alternate_processors = alternate_pin_binding[1:]
		    for alternate_processor in alternate_processors:
			#print(alternate_processor)
			if processor == alternate_processor:
			    name = alternate_name

		# Force a name selection for pins that can be bridged to alternate pins:
		if ':' in name:
		    name1, name2 = name.split(':')
		    if name1 in pin_selects:
			name = name1
		    elif name2 in pin_selects:
			name = name2
		    else:
			assert False, "You must pick between '{0}' and '{1}'".format(name1, name2)

		# Add the binding to *nucleo64_bindings*:
		nucleo64_bindings.append( (pin_number, name) )

	    # Sort the result:	
	    nucleo64_bindings.sort(key = lambda binding: binding[0])

	    debug = False
	    #debug = True
	    if debug:
		for index, binding in enumerate(nucleo64_bindings):
		    pin_number, name = binding
		    print("[{0}] {1} '{2}'".format(index, pin_number, name))

	#print("len(nucleo64_bindings)={0}".format(len(nucleo64_bindings)))
	return nucleo64_bindings

class SchematicLibrary:
    """ *SchematicLibrary*: represents a KiCad schematic symbol library
    """

    def __init__(self, file_name):
	""" *SchematicLibrary*: Initialize *SchematicLibary* object.

	The arguments are:
	* *library_file_name*: The `.lib` file to open and read in. 
	"""

	# Verify argument types:
	assert isinstance(file_name, str) and file_name.endswith(".lib")
	print("SchematicLibrary.__init__(*, '{0}')".format(file_name))

	# Start with an empty *symbols_table*:
	schematic_library = self
	schematic_library.symbols_table = symbols_table = dict()

	# Open *schematic_library_file_name* and break it into *lines*:
	with open(file_name, "r") as library_file:
	    lines = library_file.read().split('\n')

	    # Sweep through *lines* looking for first/last lines a schematic symbol definition:
	    def_line_index = -1
	    for line_index, line in enumerate(lines):
		#print("[{0}]: '{1}'".format(line_index, line))
		if line.startswith("DEF "):
		    # Found first line of schematic symbol definition:
		    def_line_index = line_index
		elif line.startswith("ENDDEF"):
		    # Found last line of schematic symbol defintion:
		    assert def_line_index >= 0
		    symbol = SchematicSymbol(lines[def_line_index:line_index + 1])
		    symbol_name = symbol.name
		    assert not symbol in symbols_table
		    symbols_table[symbol_name] = symbol
		    def_line_index = -1

    def insert(self, schematic_symbol):
	assert isinstance(schematic_symbol, SchematicSymbol)
	schematic_library = self
	symbols_table = schematic_library.symbols_table
	symbol_name = schematic_symbol.name
	symbols_table[symbol_name] = schematic_symbol

    def fixup(self):
	schematic_library = self
        symbols_table = schematic_library.symbols_table
	for symbol in symbols_table.values():
	    symbol.fixup()

    def lookup(self, part_name):
	schematic_library = self
	symbols_table = schematic_library.symbols_table
	assert part_name in symbols_table
	symbol = symbols_table[part_name]
	return symbol

    def write(self, lib_file_name):
	# Verify argument types:
	assert isinstance(lib_file_name, str)

	print("SchematicLibrary.write('{0}')".format(lib_file_name))

	# Create a sorted list of *symbols*:
	schematic_library = self
	symbols_table = schematic_library.symbols_table
	symbols = list(symbols_table.values())
	symbols.sort(key = lambda symbol: symbol.name)

	# Open *lib_file_name*:
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

class SchematicSymbol:
    def __init__(self, lines):
	first_line = lines[0]
	last_line = lines[-1]
	assert first_line.startswith("DEF"), "first_line='{0}'".format(first_line)
	assert last_line.startswith("ENDDEF"), "last_line='{0}'".format(last_line)
	first_line_trimmed = first_line[4:]
	space_index = first_line_trimmed.find(' ')
	assert space_index >= 0
	name = first_line_trimmed[:space_index]

	schematic_symbol = self	
	schematic_symbol.lines = lines
	schematic_symbol.name = name
	#print("second_space_index='{0}'".format(first_line))
	#print("first_line='{0}'".format(first_line))
	#print("Created Symbol '{0}'".format(name))

    def fixup(self):

	# Insert the "F2 ..." and "F3 ..." lines into *lines*
	symbol = self
	lines = symbol.lines
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
		print("'{0}' => '{1}'".format(initial_line, line))
		lines[line_index] = line

    def write(self, schematic_library_output_file):
	assert isinstance(schematic_library_output_file, file)
	schematic_symbol = self
	schematic_library_output_file.write("#\n")
	schematic_library_output_file.write("# {0}\n".format(schematic_symbol.name))
	schematic_library_output_file.write("#\n")
	schematic_library_output_file.write('\n'.join(schematic_symbol.lines))
	schematic_library_output_file.write('\n')


if __name__ == "__main__":
    main()

