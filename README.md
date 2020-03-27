# kicube32

*kicube32* is a program that takes output from the STM cube and generates an
a .csv (Comma Separated Value) for input the the `kipart` program.

## Installation:

For now, please clone this repository to get the code.

        cd SOMEWHERE
        git clone https://github.com/waynegramlich/kicube32.git
	make

The binary is `bin/kicube32`, unless you are using virtual enviroments
in which case you should be able to just run the program using `kicube32`.

In addition, this program currently useds a program called *kipart* to create
the KiCAD schematic symbols.  This is installed via:

        easy_install kipart
        pip install kipart


The `STM32CubeMX` program is typically downloaded from:

        https://www.st.com/en/development-tools/stm32cubemx.html

The web site is really annoying and will ask for an E-mail address before
it will letting you get the the software.  Prod the web site until it E-mails
you a URL for downloading the code.

To avoid the annoyance, there is a version of the code associated with repository.
To extract it, just type:

        make

There may be some issues with ensuring that Java is installed.  Seach the web to
figure out how to ensure that you have the correct version of Java installed.

Now you can run the program.:

        STM32CubeMX

The cube data file ends with a `.ioc` suffix.

## Usage

The first step is to start `STM32CubeMX` software:

        ./STM32CubeMX

This is some Java code with the usual Java annoyances.  It is kind of slow and sluggish
running on Linux.

* Select a chip or a development board.

* If you select a development board, a number of the pins will be orange to indicate
  that the development board is interested in thost pins.  Try to avoid them if you can.

* Bind pins to peripherals (e.g. UART's, Timers, etc.)

* It is recommended that GPIO pins be given a User Label [Right Mouse Button] to give
  them a label.  Label names that start with an underscore ('_') will show up in the
  schematic symbol with an overbar over the label name and an inversion circle on the
  schematic pin.

* When you are ready to generate the KiCAD symbol do the following:

  * Use the [File=>Save Project] or [File=>Save Project as ...] button to save
    the STM32CubeMX output into a `.ioc` file.

  * At the same time use the [v Pinout=>Export pinout without Alt. Functions]
    (or Control-U) to write out a `.csv` file that lists all the pins.

* It required that the generated `.ioc` and `.csv` files be located in the same
  directory and have the same file name (e.g. `f767zi.ioc` and `f767zi.csv`).

* Now run the `kicube32` program:

        kicube32 IOCFILE.ioc STM32CUBE.csv KIPART.csv

  where:

  * `IOCFILE.ioc` is the `.ioc` file output by STM32CubeMZ

  * `STMECUBE32.csv` is the `.csv` file that you manually generated using `STM32CubeMX`.

  * `KIPART.csv` is the 
    to use.

  * LIB.lib is the name of the KiCAD schematic symbol library file to store
    the generated KiCAD schematic symbol into.

  `kicube32.py` will insert/replace a new schematic symbol into KICADLIBDIR/LIB.lib
  with a name of BASENAME (converted to upper case.)

* Now restart KiCAD and bring up the schematic capture editor.

  * It will likely complain that it noticed that you changed the `.lib` file
    behind its back.  It will ask you if you want to "rescue" the symbol that
    changed.  Just click on [Cancel].

* Now you can use the schematic capture editor to insert the symbol into the
  schematic.  The generated symbol has multiple units from A to whatever.
  In general, the program attempts to asign port A to unit A, port B ot unit B,
  etc.  The last two units are miscellaneous pins (e.g. NC's, BOOT, RESET,)
  and power pins (VSS, VDD, AVDD, VBAT, etc.)

* Each time you update the symbol via `kicad.py`, you need to go into the
  schematic capture editor, and force the schematic capature to
  [Revert to Libary Defaults] using the 'E' key.

## Comments

1. This code is not properly commented internally yet.

2. There is a good chance that `kipart` will be removed over time.

3. There are plans to support Nucleo-64 board swapping whereby
   a single PCB can be designed to support multiple Nucleo-64's.
   The Nucleo-64 boards tend to have different pin bindings and peripheral
   pin mappings, and this will help alleviate that pain.

4. There are plans to support mulitple board that stack on top of
   a Nucleo board (call them daughter boards) and make sure that the
   pins do not conflict.

5. It may be possible to eliminate the `.csv` file output and directly read all
   the necessary information from the `.ioc` file.

