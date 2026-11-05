#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <random>
#include <stdexcept>
#include <vector>

namespace oes::geometry {

constexpr float pi = 3.14159265358979323846f;

struct Vec3 {
    float x{};
    float y{};
    float z{};
};

struct Vertex {
    Vec3 position{};
    Vec3 normal{};
    float u{};
    float v{};
};

struct MeshData {
    std::vector<Vertex> vertices;
    std::vector<std::uint32_t> indices;
};

inline Vec3 normalized(Vec3 value, float radius = 1.0f) {
    const float length = std::sqrt(value.x * value.x + value.y * value.y + value.z * value.z);
    if (length <= 0.000001f) return {};
    const float scale = radius / length;
    return {value.x * scale, value.y * scale, value.z * scale};
}

inline Vec3 midpoint(Vec3 left, Vec3 right) {
    return {(left.x + right.x) * 0.5f, (left.y + right.y) * 0.5f,
            (left.z + right.z) * 0.5f};
}

inline MeshData sphere(float radius, std::uint32_t slices, std::uint32_t stacks,
                       float phi_start = 0.0f, float phi_length = pi) {
    MeshData result;
    result.vertices.reserve(static_cast<std::size_t>(slices + 1) * (stacks + 1));
    for (std::uint32_t stack = 0; stack <= stacks; ++stack) {
        const float v = static_cast<float>(stack) / static_cast<float>(stacks);
        const float phi = phi_start + phi_length * v;
        for (std::uint32_t slice = 0; slice <= slices; ++slice) {
            const float u = static_cast<float>(slice) / static_cast<float>(slices);
            const float theta = u * pi * 2.0f;
            const Vec3 normal{std::sin(phi) * std::cos(theta), std::cos(phi),
                              std::sin(phi) * std::sin(theta)};
            result.vertices.push_back({{normal.x * radius, normal.y * radius,
                                        normal.z * radius}, normal, u, v});
        }
    }
    for (std::uint32_t stack = 0; stack < stacks; ++stack) {
        for (std::uint32_t slice = 0; slice < slices; ++slice) {
            const std::uint32_t row = slices + 1;
            const std::uint32_t a = stack * row + slice;
            const std::uint32_t b = a + row;
            result.indices.insert(result.indices.end(), {a, a + 1, b, a + 1, b + 1, b});
        }
    }
    return result;
}

inline MeshData torus(float major_radius, float tube_radius, std::uint32_t radial_segments,
                      std::uint32_t tubular_segments) {
    MeshData result;
    result.vertices.reserve(static_cast<std::size_t>(radial_segments + 1) *
                            (tubular_segments + 1));
    for (std::uint32_t tube = 0; tube <= tubular_segments; ++tube) {
        const float u = static_cast<float>(tube) / static_cast<float>(tubular_segments);
        const float theta = u * pi * 2.0f;
        for (std::uint32_t radial = 0; radial <= radial_segments; ++radial) {
            const float v = static_cast<float>(radial) / static_cast<float>(radial_segments);
            const float phi = v * pi * 2.0f;
            const float ring = major_radius + tube_radius * std::cos(phi);
            const Vec3 normal{std::cos(theta) * std::cos(phi),
                              std::sin(theta) * std::cos(phi), std::sin(phi)};
            result.vertices.push_back({{ring * std::cos(theta), ring * std::sin(theta),
                                        tube_radius * std::sin(phi)}, normal, u, v});
        }
    }
    const std::uint32_t row = radial_segments + 1;
    for (std::uint32_t tube = 0; tube < tubular_segments; ++tube) {
        for (std::uint32_t radial = 0; radial < radial_segments; ++radial) {
            const std::uint32_t a = tube * row + radial;
            const std::uint32_t b = (tube + 1) * row + radial;
            result.indices.insert(result.indices.end(), {a, a + 1, b, a + 1, b + 1, b});
        }
    }
    return result;
}

inline MeshData annulus(float inner_radius, float outer_radius, std::uint32_t segments) {
    MeshData result;
    for (std::uint32_t index = 0; index <= segments; ++index) {
        const float u = static_cast<float>(index) / static_cast<float>(segments);
        const float angle = u * pi * 2.0f;
        const float x = std::cos(angle);
        const float y = std::sin(angle);
        result.vertices.push_back({{x * inner_radius, y * inner_radius, 0}, {0, 0, 1}, 0, u});
        result.vertices.push_back({{x * outer_radius, y * outer_radius, 0}, {0, 0, 1}, 1, u});
    }
    for (std::uint32_t index = 0; index < segments; ++index) {
        const std::uint32_t a = index * 2;
        result.indices.insert(result.indices.end(), {a, a + 2, a + 1, a + 1, a + 2, a + 3});
    }
    return result;
}

// Curved, outward-facing band on the +Z side of a sphere. Face features use
// this instead of flattened spheres and planes so their normals and depth
// remain readable from oblique viewpoints.
inline MeshData spherical_annulus(float radius, float inner_angle, float outer_angle,
                                  std::uint32_t segments, std::uint32_t rings) {
    MeshData result;
    result.vertices.reserve(static_cast<std::size_t>(segments + 1) * (rings + 1));
    for (std::uint32_t ring = 0; ring <= rings; ++ring) {
        const float v = static_cast<float>(ring) / static_cast<float>(rings);
        const float angle = inner_angle + (outer_angle - inner_angle) * v;
        const float radial = std::sin(angle);
        const float z = std::cos(angle);
        for (std::uint32_t segment = 0; segment <= segments; ++segment) {
            const float u = static_cast<float>(segment) / static_cast<float>(segments);
            const float theta = u * pi * 2.0f;
            const Vec3 normal{radial * std::cos(theta), radial * std::sin(theta), z};
            result.vertices.push_back({{normal.x * radius, normal.y * radius,
                                        normal.z * radius}, normal, u, v});
        }
    }
    const std::uint32_t row = segments + 1;
    for (std::uint32_t ring = 0; ring < rings; ++ring) {
        for (std::uint32_t segment = 0; segment < segments; ++segment) {
            const std::uint32_t a = ring * row + segment;
            const std::uint32_t b = a + row;
            // This +Z polar parameterization has the opposite tangent order
            // from sphere(); keep winding aligned with its outward normals.
            result.indices.insert(result.indices.end(), {a, b, a + 1, a + 1, b, b + 1});
        }
    }
    return result;
}

inline MeshData spherical_cap(float radius, float outer_angle,
                              std::uint32_t segments, std::uint32_t rings) {
    return spherical_annulus(radius, 0.0f, outer_angle, segments, rings);
}

inline MeshData plane(float width, float height) {
    const float x = width * 0.5f;
    const float y = height * 0.5f;
    MeshData result;
    result.vertices = {
        {{-x, -y, 0}, {0, 0, 1}, 0, 1}, {{-x, y, 0}, {0, 0, 1}, 0, 0},
        {{x, y, 0}, {0, 0, 1}, 1, 0}, {{x, -y, 0}, {0, 0, 1}, 1, 1},
    };
    result.indices = {0, 2, 1, 0, 3, 2};
    return result;
}

// Looking from +Z toward the origin reverses world X in the established
// left-handed view. Reverse U locally so the immutable OES identity reads
// outward correctly without mirroring the source asset.
inline MeshData outward_identity_plane(float width, float height) {
    MeshData result = plane(width, height);
    for (auto& vertex : result.vertices) vertex.u = 1.0f - vertex.u;
    return result;
}

inline MeshData aperture_blade(float inner_radius, float outer_radius,
                               float start_angle, float end_angle, float depth) {
    if (inner_radius <= 0 || outer_radius <= inner_radius || end_angle <= start_angle || depth <= 0)
        throw std::invalid_argument("Invalid aperture blade dimensions");
    MeshData result;
    const float middle = (start_angle + end_angle) * .5f;
    const float leading = start_angle + (end_angle - start_angle) * .18f;
    const std::array<Vec3, 4> face{{
        {std::cos(leading) * inner_radius, std::sin(leading) * inner_radius, depth * .5f},
        {std::cos(start_angle) * outer_radius, std::sin(start_angle) * outer_radius, depth * .5f},
        {std::cos(end_angle) * outer_radius, std::sin(end_angle) * outer_radius, depth * .5f},
        {std::cos(middle) * inner_radius, std::sin(middle) * inner_radius, depth * .5f},
    }};
    for (int side = 0; side < 2; ++side) {
        const float z = side ? -depth * .5f : depth * .5f;
        const Vec3 normal{0, 0, side ? -1.0f : 1.0f};
        for (const auto& point : face)
            result.vertices.push_back({point.x, point.y, z, normal.x, normal.y, normal.z,
                                       (point.x / outer_radius + 1) * .5f,
                                       (1 - point.y / outer_radius) * .5f});
    }
    result.indices.insert(result.indices.end(), {0, 1, 2, 0, 2, 3, 4, 6, 5, 4, 7, 6});
    for (std::uint32_t edge = 0; edge < 4; ++edge) {
        const std::uint32_t next = (edge + 1) % 4;
        result.indices.insert(result.indices.end(), {edge, edge + 4, next, next, edge + 4, next + 4});
    }
    return result;
}

inline void subdivide_icosphere_lines(Vec3 a, Vec3 b, Vec3 c, int detail, float radius,
                                      MeshData& result) {
    if (detail > 0) {
        const Vec3 ab = normalized(midpoint(a, b));
        const Vec3 bc = normalized(midpoint(b, c));
        const Vec3 ca = normalized(midpoint(c, a));
        subdivide_icosphere_lines(a, ab, ca, detail - 1, radius, result);
        subdivide_icosphere_lines(ab, b, bc, detail - 1, radius, result);
        subdivide_icosphere_lines(ca, bc, c, detail - 1, radius, result);
        subdivide_icosphere_lines(ab, bc, ca, detail - 1, radius, result);
        return;
    }
    for (const auto& point : std::array<Vec3, 6>{a, b, b, c, c, a}) {
        const Vec3 position = normalized(point, radius);
        result.vertices.push_back({position, normalized(point), 0, 0});
        result.indices.push_back(static_cast<std::uint32_t>(result.indices.size()));
    }
}

inline MeshData icosphere_lines(float radius, int detail) {
    const float t = (1.0f + std::sqrt(5.0f)) * 0.5f;
    std::array<Vec3, 12> points{{{-1, t, 0}, {1, t, 0}, {-1, -t, 0}, {1, -t, 0},
                                  {0, -1, t}, {0, 1, t}, {0, -1, -t}, {0, 1, -t},
                                  {t, 0, -1}, {t, 0, 1}, {-t, 0, -1}, {-t, 0, 1}}};
    for (auto& point : points) point = normalized(point);
    constexpr std::array<std::array<int, 3>, 20> faces{{
        {0, 11, 5}, {0, 5, 1}, {0, 1, 7}, {0, 7, 10}, {0, 10, 11},
        {1, 5, 9}, {5, 11, 4}, {11, 10, 2}, {10, 7, 6}, {7, 1, 8},
        {3, 9, 4}, {3, 4, 2}, {3, 2, 6}, {3, 6, 8}, {3, 8, 9},
        {4, 9, 5}, {2, 4, 11}, {6, 2, 10}, {8, 6, 7}, {9, 8, 1}}};
    MeshData result;
    const std::size_t triangle_count = static_cast<std::size_t>(20) << (detail * 2);
    result.vertices.reserve(triangle_count * 6);
    result.indices.reserve(triangle_count * 6);
    for (const auto& face : faces) {
        subdivide_icosphere_lines(points[face[0]], points[face[1]], points[face[2]],
                                  detail, radius, result);
    }
    return result;
}

inline MeshData particles(std::uint32_t count, std::uint32_t seed,
                          float minimum_radius, float maximum_radius) {
    std::mt19937 random(seed);
    std::uniform_real_distribution<float> unit(0.0f, 1.0f);
    MeshData result;
    result.vertices.reserve(count);
    result.indices.reserve(count);
    for (std::uint32_t index = 0; index < count; ++index) {
        const float radius = minimum_radius + unit(random) * (maximum_radius - minimum_radius);
        const float theta = unit(random) * pi * 2.0f;
        const float phi = std::acos(std::clamp(2.0f * unit(random) - 1.0f, -1.0f, 1.0f));
        result.vertices.push_back({{radius * std::sin(phi) * std::cos(theta),
                                    radius * std::sin(phi) * std::sin(theta),
                                    radius * std::cos(phi)}, {0, 0, 1}, 0, 0});
        result.indices.push_back(index);
    }
    return result;
}

}  // namespace oes::geometry
