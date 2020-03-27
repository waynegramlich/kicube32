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

all: $(STM32CUBE_EXECUTABLE) $(KICUBE32_EXECUTABLE)

everything: all

clean:
	rm -f $(KICUBE32_EXECUTABLE)

debug:
	@echo KICUBE32_BIN_DIRECTORY=$(KICUBE32_BIN_DIRECTORY)
	@echo KICUBE32_EXECUTABLE=$(KICUBE32_EXECUTABLE)
	@echo KICUBE32_PY=$(KICUBE32_PY)
	@echo "================================================================"

$(KICUBE32_EXECUTABLE): $(KICUBE32_PY)
	mypy $(KICUBE32_PY)
	flake8 $(KICUBE32_PY) --max-line-length=100
	pydocstyle $(KICUBE32_PY)
	mkdir -p $(KICUBE32_BIN_DIRECTORY)
	if [ -n "$$VIRTUAL_ENV" ] ;				\
	   then pip install . ;					\
	   else rm -f $(KICUBE32_EXECUTABLE);			\
	        mkdir -p $(KICUBE32_BIN_DIRECTORY);	\
		cp $(KICUBE32_PY) $(KICUBE32_EXECUTABLE) ;	\
	   fi

$(STM32CUBE_EXECUTABLE):
	rm -f $(STM32CUBE_TAR_BZ2) $(STM32CUBE_TAR)
	cat $(STM32CUBE_DOWNLOAD_DIRECTORY)/* > $(STM32CUBE_TAR_BZ2)
	(cd /tmp ; bunzip2 $(STM32CUBE_TAR_BZ2) )
	rm -rf $(STMCUBE_DIRECTORY)
	tar -x -f $(STM32CUBE_TAR)
	rm $(STM32CUBE_TAR)
