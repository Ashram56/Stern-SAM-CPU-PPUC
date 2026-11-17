# SAM CPU board replacement: RP2354B firmware.
#
#   cmake -B build -DPICO_SDK_PATH=/path/to/pico-sdk
#   cmake --build build
#
# SPDX-License-Identifier: GPL-3.0-or-later
cmake_minimum_required(VERSION 3.13)

set(PICO_BOARD sam_cpu_rp2354b CACHE STRING "Board")
set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR}/boards)
set(PICO_PLATFORM rp2350-arm-s CACHE STRING "Platform")

include(pico_sdk_import.cmake)

project(sam_cpu_firmware C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

add_executable(sam_cpu
  src/main.cpp
  src/core/coil_engine.cpp
  src/core/devices.cpp
  src/core/io_scheduler.cpp
  src/core/lamp_engine.cpp
  src/core/ppuc_session.cpp
  src/core/switch_scanner.cpp
  src/hw/link_uart.cpp
  src/hw/realtime.cpp
)

pico_generate_pio_header(sam_cpu ${CMAKE_CURRENT_LIST_DIR}/src/hw/sam_bus.pio)
pico_generate_pio_header(sam_cpu ${CMAKE_CURRENT_LIST_DIR}/src/hw/switch_chain.pio)

target_compile_options(sam_cpu PRIVATE -Wall -Wextra -Wno-unused-parameter)
target_compile_options(sam_cpu PRIVATE $<$<COMPILE_LANGUAGE:CXX>:-fno-exceptions -fno-rtti>)

target_link_libraries(sam_cpu
  pico_stdlib
  pico_multicore
  hardware_dma
  hardware_pio
  hardware_pwm
  hardware_uart
  hardware_watchdog
)

# Whole image runs from RAM: no flash stalls in the core1 loop or IRQs.
pico_set_binary_type(sam_cpu copy_to_ram)
# UART0 belongs to the PPUC link; debug output over USB.
pico_enable_stdio_uart(sam_cpu 0)
pico_enable_stdio_usb(sam_cpu 1)
pico_add_extra_outputs(sam_cpu)
