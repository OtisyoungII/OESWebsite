cmake_minimum_required(VERSION 3.24)
project(OesEyeballRenderer LANGUAGES CXX)

if(NOT WIN32)
    message(FATAL_ERROR "The OES Eyeball proof-of-concept renderer builds on Windows only.")
endif()

if(NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
    message(FATAL_ERROR "Configure an x64 generator; 32-bit renderer builds are unsupported.")
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(OES_CANONICAL_SVG "${CMAKE_CURRENT_SOURCE_DIR}/../static/images/oes-logo.svg")
set(OES_CANONICAL_RASTER
    "${CMAKE_CURRENT_SOURCE_DIR}/../oes_core_launcher/assets/source/oes-eyeball-source.png")

if(NOT EXISTS "${OES_CANONICAL_SVG}" OR NOT EXISTS "${OES_CANONICAL_RASTER}")
    message(FATAL_ERROR "Canonical Eyeball SVG or its verified lossless raster is missing.")
endif()

file(SHA256 "${OES_CANONICAL_SVG}" OES_CANONICAL_SVG_SHA256)
if(NOT OES_CANONICAL_SVG_SHA256 STREQUAL
   "1ce89e6864b8d5799d4806228a3f71172f5bd3c7adaba7d1c8772127d702032b")
    message(FATAL_ERROR "Canonical Eyeball SVG changed; verify the raster before building.")
endif()

add_executable(oes-eyeball-renderer WIN32
    src/main.cpp
)

target_compile_definitions(oes-eyeball-renderer PRIVATE
    UNICODE
    _UNICODE
    WIN32_LEAN_AND_MEAN
    NOMINMAX
)

target_compile_options(oes-eyeball-renderer PRIVATE /W4 /permissive- /EHsc)
target_link_libraries(oes-eyeball-renderer PRIVATE
    d3d11
    dxgi
    dcomp
    d3dcompiler
    windowscodecs
    shell32
    shlwapi
    psapi
)

add_custom_command(TARGET oes-eyeball-renderer POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:oes-eyeball-renderer>/assets"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${OES_CANONICAL_SVG}"
        "$<TARGET_FILE_DIR:oes-eyeball-renderer>/assets/oes-logo.svg"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${OES_CANONICAL_RASTER}"
        "$<TARGET_FILE_DIR:oes-eyeball-renderer>/assets/oes-logo.png"
)
