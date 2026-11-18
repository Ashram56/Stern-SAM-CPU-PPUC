# SAM universal test board: RP2354B firmware.
#
#   cmake -B build -DPICO_SDK_PATH=/path/to/pico-sdk && cmake --build build
#
# SPDX-License-Identifier: GPL-3.0-or-later
cmake_minimum_required(VERSION 3.13)
set(PICO_BOARD stb_rp2354b CACHE STRING "Board")
set(PICO_BOARD_HEADER_DIRS ${CMAKE_CURRENT_LIST_DIR}/boards)
set(PICO_PLATFORM rp2350-arm-s CACHE STRING "Platform")
include(pico_sdk_import.cmake)
project(stb_firmware C CXX ASM)
set(CMAKE_C_STANDARD 11)
pico_sdk_init()

add_executable(stb src/main.c src/capture.c src/switches.c src/proto.c src/rails.c src/sync.c)
pico_generate_pio_header(stb ${CMAKE_CURRENT_LIST_DIR}/src/stb.pio)
target_include_directories(stb PRIVATE src)
target_compile_options(stb PRIVATE -Wall -Wextra -O2)
target_link_libraries(stb pico_stdlib pico_multicore hardware_pio hardware_dma hardware_adc pico_unique_id)
pico_enable_stdio_usb(stb 1)
pico_enable_stdio_uart(stb 0)
pico_set_binary_type(stb copy_to_ram)
pico_add_extra_outputs(stb)
