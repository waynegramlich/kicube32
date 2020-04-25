.PHONY: all clean everything

STM32CUBE_DIRECTORY := stm32cube
STM32CUBE_DOWNLOAD_DIRECTORY := stm32cube_download
STM32CUBE_EXECUTABLE := $(STM32CUBE_DIRECTORY)/STM32CubeMX
STM32CUBE_TAR_BZ2 := /tmp/stm32cube.tar.bz2
STM32CUBE_TAR := /tmp/stm32cube.tar

KICUBE32_BIN_DIRECTORY :=			\
    $(shell if [ -n "$$VIRTUAL_ENV" ] ;		\
          then echo "$$VIRTUAL_ENV/bin" ;	\
          else echo "bin" ;			\
          fi )
KICUBE32_EXECUTABLE := $(KICUBE32_BIN_DIRECTORY)/kicube32
KICUBE32_PY := kicube32/kicube32.py

KIDOCGEN_BIN_DIRECTORY :=			\
    $(shell if [ -n "$$VIRTUAL_ENV" ] ;		\
          then echo "$$VIRTUAL_ENV/bin" ;	\
          else echo "bin" ;			\
          fi )
KIDOCGEN_EXECUTABLE := $(KIDOCGEN_BIN_DIRECTORY)/kidocgen
KIDOCGEN_PY := kidocgen/kidocgen.py

BOTH_PY :=		\
    $(KICUBE32_PY)	\
    $(KIDOCGEN_PY)

all: $(KICUBE32_EXECUTABLE) $(KIDOCGEN_EXECUTABLE)

everything: all

clean:
	rm -f $(KICUBE32_EXECUTABLE) $(KIDOCGEN_EXECUTABLE)

debug:
	@echo KICUBE32_BIN_DIRECTORY=$(KICUBE32_BIN_DIRECTORY)
	@echo KICUBE32_EXECUTABLE=$(KICUBE32_EXECUTABLE)
	@echo KICUBE32_PY=$(KICUBE32_PY)
	@echo KIDOCGEN_BIN_DIRECTORY=$(KIDOCGEN_BIN_DIRECTORY)
	@echo KIDOCGEN_EXECUTABLE=$(KIDOCGEN_EXECUTABLE)
	@echo KIDOCGEN_PY=$(KIDOCGEN_PY)
	@echo "================================================================"

$(KICUBE32_EXECUTABLE) $(KIDOCGEN_EXECUTABLE): ${BOTH_PY}
	mypy ${BOTH_PY}
	flake8 ${BOTH_PY} --max-line-length=100
	pydocstyle ${BOTH_PY}
	mkdir -p $(KICUBE32_BIN_DIRECTORY)
	mkdir -p $(KIDOCGEN_BIN_DIRECTORY)
	if [ -n "$$VIRTUAL_ENV" ] ;				\
	   then pip install . ;					\
		echo "No virtual environment set." ;		\
	   fi


