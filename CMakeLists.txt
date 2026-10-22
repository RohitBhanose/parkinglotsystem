cmake_minimum_required(VERSION 3.16)
project(SmartParkingCore VERSION 2.0 LANGUAGES CXX)

# Build:   cmake -S . -B build        then   cmake --build build
# Test:    ctest --test-dir build --output-on-failure
# MySQL:   add -DPARKING_WITH_MYSQL=ON -DMYSQL_ROOT="<MySQL Server folder>"

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(PARKING_WITH_MYSQL "Build the optional MySQL repository (needs the MySQL C client library)" OFF)
option(PARKING_BUILD_TESTS "Build the unit tests" ON)

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_BINARY_DIR)
    message(FATAL_ERROR "Please build out of source, e.g.  cmake -S . -B build")
endif()

# Keep the executables directly in the build folder (also for Visual Studio),
# which is where the Python bridge (parking_core.py) looks for them.
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})
foreach(config_type Debug Release RelWithDebInfo MinSizeRel)
    string(TOUPPER ${config_type} config_upper)
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_${config_upper} ${CMAKE_BINARY_DIR})
endforeach()

add_library(parking_core STATIC
    src/app/CommandLineApp.cpp
    src/app/DemoRunner.cpp
    src/app/JsonWriter.cpp
    src/config/AppConfig.cpp
    src/config/KeyValueFile.cpp
    src/models/ParkingSlot.cpp
    src/models/ParkingTransaction.cpp
    src/models/Payment.cpp
    src/models/Vehicle.cpp
    src/services/ParkingFeeStrategy.cpp
    src/services/ParkingLot.cpp
    src/services/ParkingRecordManager.cpp
    src/storage/CsvParkingRepository.cpp
    src/storage/ParkingRepository.cpp
    src/util/TimeUtils.cpp
)
target_include_directories(parking_core PUBLIC src)

if(MSVC)
    target_compile_options(parking_core PUBLIC /W4 /permissive- /utf-8)
else()
    target_compile_options(parking_core PUBLIC -Wall -Wextra -Wpedantic -Wshadow)
endif()

if(PARKING_WITH_MYSQL)
    find_path(MYSQL_INCLUDE_DIR mysql.h
        HINTS ${MYSQL_ROOT} $ENV{MYSQL_ROOT}
        PATH_SUFFIXES include include/mysql)
    find_library(MYSQL_LIBRARY NAMES libmysql mysqlclient mysql
        HINTS ${MYSQL_ROOT} $ENV{MYSQL_ROOT}
        PATH_SUFFIXES lib lib/mysql)
    if(NOT MYSQL_INCLUDE_DIR OR NOT MYSQL_LIBRARY)
        message(FATAL_ERROR "MySQL client library not found. Pass -DMYSQL_ROOT=<folder containing include/ and lib/>")
    endif()
    message(STATUS "MySQL client: ${MYSQL_LIBRARY}")
    target_sources(parking_core PRIVATE src/storage/MySqlParkingRepository.cpp)
    target_compile_definitions(parking_core PUBLIC PARKING_WITH_MYSQL)
    target_include_directories(parking_core PRIVATE ${MYSQL_INCLUDE_DIR})
    target_link_libraries(parking_core PUBLIC ${MYSQL_LIBRARY})
endif()

add_executable(parkinglot src/main.cpp)
target_link_libraries(parkinglot PRIVATE parking_core)

# MinGW: link the C++ runtime statically so parkinglot.exe runs when Python
# starts it, even if the MSYS2 bin folder is not on that process's PATH.
if(MINGW)
    if(PARKING_WITH_MYSQL)
        target_link_options(parkinglot PRIVATE -static-libgcc -static-libstdc++)
    else()
        target_link_options(parkinglot PRIVATE -static)
    endif()
endif()

if(PARKING_BUILD_TESTS)
    enable_testing()
    add_executable(parking_tests
        tests/test_main.cpp
        tests/test_models.cpp
        tests/test_fees.cpp
        tests/test_storage.cpp
    )
    target_include_directories(parking_tests PRIVATE tests)
    target_link_libraries(parking_tests PRIVATE parking_core)
    if(MINGW AND NOT PARKING_WITH_MYSQL)
        target_link_options(parking_tests PRIVATE -static)
    endif()
    add_test(NAME parking_tests COMMAND parking_tests)
    add_test(NAME parkinglot_demo COMMAND parkinglot demo)
endif()
