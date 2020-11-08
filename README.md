# PyPmx
Private Mode eXecution for Windows on Python

This project was made for https://habr.com/ru/post/527006/

Implements all kinds of kernel features using AsrDrv101 driver, including:
- Physical Memory Read / Write / Alloc / Free / Search
- PCI Config Space Read / Write
- IO, CR, MSR Read / Write
- TSC, PMC, CPUID Read

Intel BIOS read script is provided as an example
