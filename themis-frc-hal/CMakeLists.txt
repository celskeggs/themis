cmake_minimum_required(VERSION 3.5)
project(themis-frc)

set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

set(ARM_PREFIX arm-frc-linux-gnueabi)
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_CXX_COMPILER ${ARM_PREFIX}-g++)
set(CMAKE_C_COMPILER ${ARM_PREFIX}-gcc)
# note: these flags are duplicated in themis/cbuild.py
set(SHARED_FLAGS "-Wformat=2 -Wall -Wextra -Werror -pedantic -Wno-psabi -Wno-unused-parameter -Wno-error=deprecated-declarations -fPIC -Os -g0 -rdynamic")
set(CMAKE_CXX_FLAGS "-std=c++1y ${SHARED_FLAGS}")
set(CMAKE_C_FLAGS "-std=c11 -D_POSIX_C_SOURCE=199309L ${SHARED_FLAGS}")

set(SOURCE_FILES
    include/ctre/CtreCanNode.h
    include/ctre/ctre.h
    include/ctre/PDP.h
    include/ctre/ctre_frames.h
    include/ctre/PCM.h
    include/Log.hpp
    include/HAL/Errors.hpp
    include/HAL/Semaphore.hpp
    include/HAL/SerialPort.hpp
    include/HAL/cpp/Semaphore.hpp
    include/HAL/cpp/priority_mutex.h
    include/HAL/cpp/priority_condition_variable.h
    include/HAL/cpp/Resource.hpp
    include/HAL/HAL.hpp
    include/HAL/Power.hpp
    include/HAL/Notifier.hpp
    include/HAL/Solenoid.hpp
    include/HAL/Task.hpp
    include/HAL/Port.h
    include/HAL/Interrupts.hpp
    include/HAL/Compressor.hpp
    include/HAL/Utilities.hpp
    include/HAL/Analog.hpp
    include/HAL/CAN.hpp
    include/HAL/Digital.hpp
    include/HAL/PDP.hpp
    include/HAL/Accelerometer.hpp
    include/HAL/CanTalonSRX.h
    include/spilib/spi-lib.h
    lib/PDP.cpp
    lib/Analog.cpp
    lib/cpp/priority_mutex.cpp
    lib/cpp/Semaphore.cpp
    lib/cpp/Resource.cpp
    include/ChipObject.h
    lib/Interrupts.cpp
    lib/HAL.cpp
    lib/HALAthena.cpp
    include/FRC_FPGA_ChipObject/tSystemInterface.h
    include/FRC_FPGA_ChipObject/nInvariantFPGANamespace/tGlobal.h
    include/FRC_FPGA_ChipObject/nInvariantFPGANamespace/tAI.h
    include/FRC_FPGA_ChipObject/nInvariantFPGANamespace/tLoadOut.h
    include/FRC_FPGA_ChipObject/nInvariantFPGANamespace/nInterfaceGlobals.h
    include/FRC_FPGA_ChipObject/tDMAManager.h
    include/FRC_FPGA_ChipObject/printFpgaVersion.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tAnalogTrigger.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tAO.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tDMA.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tInterrupt.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tBIST.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tGlobal.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tPWM.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tSysWatchdog.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tCounter.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tAI.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tAccumulator.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tAlarm.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tSPI.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tAccel.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/nInterfaceGlobals.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tEncoder.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tDIO.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tPower.h
    include/FRC_FPGA_ChipObject/nRoboRIO_FPGANamespace/tRelay.h
    include/FRC_FPGA_ChipObject/fpgainterfacecapi/NiFpga.h
    include/FRC_FPGA_ChipObject/RoboRIO_FRC_ChipObject_Aliases.h
    include/FRC_FPGA_ChipObject/tSystem.h
    include/FRC_FPGA_ChipObject/FRC_FPGA_ChipObject_Aliases.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/tAnalogTrigger.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/tDMA.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/tInterrupt.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/tGlobal.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/tSysWatchdog.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/tWatchdog.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/tCounter.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/tAI.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/tAccumulator.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/tAlarm.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/tSPI.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/nInterfaceGlobals.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/tEncoder.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/tDIO.h
    include/FRC_FPGA_ChipObject/nRuntimeFPGANamespace/tSolenoid.h
    include/FRC_FPGA_ChipObject/tInterruptManager.h
    include/FRC_FPGA_ChipObject/tDMAChannelDescriptor.h
    lib/Accelerometer.cpp
    lib/Semaphore.cpp
    lib/Task.cpp
    lib/ctre/PDP.cpp
    lib/ctre/CtreCanNode.cpp
    lib/ctre/CanTalonSRX.cpp
    lib/ctre/PCM.cpp
    include/visa/visa.h
    include/visa/visatype.h
    include/FRC_NetworkCommunication/UsageReporting.h
    include/FRC_NetworkCommunication/FRCComm.h
    include/FRC_NetworkCommunication/AICalibration.h
    include/FRC_NetworkCommunication/CANInterfacePlugin.h
    include/FRC_NetworkCommunication/LoadOut.h
    include/FRC_NetworkCommunication/CANSessionMux.h
    lib/Notifier.cpp
    lib/Power.cpp
    lib/Compressor.cpp
    lib/SerialPort.cpp
    lib/Digital.cpp
    include/i2clib/i2c-lib.h
    lib/Solenoid.cpp
    lib/Utilities.cpp
    include/frccansae/CANDeviceInterface.h
    themis/themis.c themis/themis.h themis/runloop.c themis/timers.c themis/frc.cpp)

add_library(frc_netcomm SHARED IMPORTED)
SET_PROPERTY(TARGET frc_netcomm PROPERTY IMPORTED_LOCATION ${CMAKE_SOURCE_DIR}/ni-libraries/libFRC_NetworkCommunication.so.16.0.0)

add_library(frc_nifpga SHARED IMPORTED)
SET_PROPERTY(TARGET frc_nifpga PROPERTY IMPORTED_LOCATION ${CMAKE_SOURCE_DIR}/ni-libraries/libNiFpga.so.15.0.0)

add_library(frc_chipobject SHARED IMPORTED)
SET_PROPERTY(TARGET frc_chipobject PROPERTY IMPORTED_LOCATION ${CMAKE_SOURCE_DIR}/ni-libraries/libRoboRIO_FRC_ChipObject.so.16.0.0)

add_library(frc_visa SHARED IMPORTED)
SET_PROPERTY(TARGET frc_visa PROPERTY IMPORTED_LOCATION ${CMAKE_SOURCE_DIR}/ni-libraries/libvisa.so)

add_library(frc_spi SHARED IMPORTED)
SET_PROPERTY(TARGET frc_spi PROPERTY IMPORTED_LOCATION ${CMAKE_SOURCE_DIR}/ni-libraries/libspi.so.1.0.0)

add_library(frc_i2c SHARED IMPORTED)
SET_PROPERTY(TARGET frc_i2c PROPERTY IMPORTED_LOCATION ${CMAKE_SOURCE_DIR}/ni-libraries/libi2c.so.1.0.0)

add_library(themis-frc SHARED ${SOURCE_FILES})
target_include_directories(themis-frc PUBLIC include)
target_link_libraries(themis-frc Threads::Threads frc_netcomm frc_nifpga frc_chipobject frc_visa frc_spi frc_i2c)
