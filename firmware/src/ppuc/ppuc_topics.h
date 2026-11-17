// Configuration topics and device type values of the PPUC protocol.
//
// Copied from PPUC io-boards src/EventDispatcher/Event.h (commit 82511ef,
// GPLv3) so the firmware does not pull in the Arduino event framework. The
// values are on the wire: never renumber them.
//
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

// Section topics (ConfigPayload.topic).
#define CONFIG_TOPIC_PLATFORM 102
#define CONFIG_TOPIC_LED_STRING 103
#define CONFIG_TOPIC_LED_SEGMENT 104
#define CONFIG_TOPIC_LED_EFFECT 105
#define CONFIG_TOPIC_PWM_EFFECT 106
#define CONFIG_TOPIC_LAMPS 108
#define CONFIG_TOPIC_MECHS 109
#define CONFIG_TOPIC_PWM 112
#define CONFIG_TOPIC_COIN_DOOR_CLOSED_SWITCH 113
#define CONFIG_TOPIC_GAME_ON_SOLENOID 114
#define CONFIG_TOPIC_SWITCHES 115
#define CONFIG_TOPIC_TRIGGER 116
#define CONFIG_TOPIC_TILT_SWITCH 117
#define CONFIG_TOPIC_SWITCH_MATRIX 120
#define CONFIG_TOPIC_SWITCH_CHAIN 121

// New section for this board (proposal, not in upstream PPUC yet): board-wide
// SAM settings such as lamp PWM timing. See README.
#define CONFIG_TOPIC_SAM_BOARD 122

// Field topics (ConfigPayload.key). Several share a value; the section decides.
#define CONFIG_TOPIC_HOLD_POWER_ACTIVATION_TIME 65
#define CONFIG_TOPIC_DURATION 65
#define CONFIG_TOPIC_BRIGHTNESS 66
#define CONFIG_TOPIC_COLOR 67
#define CONFIG_TOPIC_STOP_SWITCH 68
#define CONFIG_TOPIC_STOP_SWITCH_2 69
#define CONFIG_TOPIC_FAST_SWITCH 70
#define CONFIG_TOPIC_FREQUENCY 70
#define CONFIG_TOPIC_AFTER_GLOW 71
#define CONFIG_TOPIC_HOLD_POWER 72
#define CONFIG_TOPIC_LED_NUMBER 76
#define CONFIG_TOPIC_MIN_PULSE_TIME 77
#define CONFIG_TOPIC_DEBOUNCE_TIME 77
#define CONFIG_TOPIC_MIN_INTENSITY 77
#define CONFIG_TOPIC_NUMBER 78
#define CONFIG_TOPIC_NUM_ROWS 79
#define CONFIG_TOPIC_PORT 80
#define CONFIG_TOPIC_MAX_PULSE_TIME 84
#define CONFIG_TOPIC_MAX_INTENSITY 84
#define CONFIG_TOPIC_LIGHT_UP 85
#define CONFIG_TOPIC_ACTIVE_LOW 86
#define CONFIG_TOPIC_POWER 87
#define CONFIG_TOPIC_NEXT_BOARD 88
#define CONFIG_TOPIC_TYPE 89
#define CONFIG_TOPIC_MODE 90
#define CONFIG_TOPIC_SWITCH_REPLY_DELAY_US 93
#define CONFIG_TOPIC_OPTIONS 94

// PWM output types (CONFIG_TOPIC_PWM / CONFIG_TOPIC_TYPE).
#define PWM_TYPE_SOLENOID 1
#define PWM_TYPE_FLASHER 2
#define PWM_TYPE_LAMP 3
#define PWM_TYPE_MOTOR 4
#define PWM_TYPE_SHAKER 5

// Switch debounce modes (CONFIG_TOPIC_SWITCHES / CONFIG_TOPIC_MODE).
#define SWITCH_DEBOUNCE_STANDARD 0
#define SWITCH_DEBOUNCE_FAST_FLIP 1
