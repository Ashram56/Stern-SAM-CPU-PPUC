# Host tests for the hardware-independent part of the firmware (src/core).
#
#   cmake -B build-test test && cmake --build build-test && ./build-test/sam_core_tests
#
# SPDX-License-Identifier: GPL-3.0-or-later
cmake_minimum_required(VERSION 3.13)
project(sam_core_tests CXX)
set(CMAKE_CXX_STANDARD 17)

set(SRC ${CMAKE_CURRENT_LIST_DIR}/../src/core)
add_executable(sam_core_tests
  core_tests.cpp
  ${SRC}/coil_engine.cpp
  ${SRC}/devices.cpp
  ${SRC}/dmd_frames.cpp
  ${SRC}/io_scheduler.cpp
  ${SRC}/lamp_engine.cpp
  ${SRC}/ppuc_session.cpp
  ${SRC}/switch_scanner.cpp
)
target_compile_options(sam_core_tests PRIVATE -Wall -Wextra -Wno-unused-parameter)
target_link_libraries(sam_core_tests m)
