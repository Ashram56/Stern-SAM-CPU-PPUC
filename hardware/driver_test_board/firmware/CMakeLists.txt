# SAM driver output test board: RP2354B firmware.
#
#   cmake -B build -DPICO_SDK_PATH=/path/to/pico-sdk && cmake --build build
#
# SPDX-License-Identifier: GPL-3.0-or-later
cmake_minimum_required(VERSION 3.13)
set(PICO_BOARD dtb_rp2354b CACHE STRING "Board")
set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR}/boards)
set(PICO_PLATFORM rp2350-arm-s CACHE STRING "Platform")
include(pico_sdk_import.cmake)
project(dtb_firmware C CXX ASM)
set(CMAKE_C_STANDARD 11)
pico_sdk_init()

add_executable(dtb src/main.c src/capture.c src/switches.c src/proto.c src/rails.c)
pico_generate_pio_header(dtb ${CMAKE_CURRENT_LIST_DIR}/src/dtb.pio)
target_include_directories(dtb PRIVATE src)
target_compile_options(dtb PRIVATE -Wall -Wextra -O2)
target_link_libraries(dtb pico_stdlib pico_multicore hardware_pio hardware_dma hardware_adc)
pico_enable_stdio_usb(dtb 1)
pico_enable_stdio_uart(dtb 0)
pico_set_binary_type(dtb copy_to_ram)
pico_add_extra_outputs(dtb)
