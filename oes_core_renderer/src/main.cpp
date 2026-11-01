#include <windows.h>
#include <d3d11.h>
#include <d3dcompiler.h>
#include <dcomp.h>
#include <dxgi1_6.h>
#include <wincodec.h>
#include <psapi.h>
#include <shellapi.h>
#include <wrl/client.h>

#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iterator>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using Microsoft::WRL::ComPtr;
using Clock = std::chrono::steady_clock;

namespace {
constexpr UINT kWidth = 512;
constexpr UINT kHeight = 512;
constexpr wchar_t kWindowClass[] = L"OesEyeballNativeRenderer";

struct RendererParameters {
    float scale = 0.86f;
    float x = 0.0f;
    float y = 0.0f;
    float rotation = 0.0f;
    float opacity = 1.0f;
    float glow_intensity = 0.0f;
    float glow_radius = 0.0f;
    float brightness = 1.0f;
    float exposure = 0.0f;
    float lighting_intensity = 1.0f;
    float depth = 0.0f;
    float perspective_x = 0.0f;
    float perspective_y = 0.0f;
    UINT width = kWidth;
    UINT height = kHeight;
};

struct Vertex {
    float x, y;
    float u, v;
};

struct Diagnostics {
    std::wstring adapter_name = L"unavailable";
    UINT vendor_id = 0;
    UINT device_id = 0;
    D3D_FEATURE_LEVEL feature_level = D3D_FEATURE_LEVEL_9_1;
    bool hardware = false;
    double initialization_ms = 0.0;
    double first_frame_ms = 0.0;
    SIZE_T working_set_bytes = 0;
    double fps = 0.0;
    UINT width = kWidth;
    UINT height = kHeight;
    RendererParameters parameters{};
};

struct alignas(16) ShaderParameters {
    float transform[4]{};       // cosine, sine, scale, depth
    float translation[4]{};     // x, y, perspective x, perspective y
    float appearance[4]{};      // opacity, brightness multiplier, glow intensity, glow radius UV
    float texture[4]{};         // inverse width, inverse height, reserved, reserved
};

std::string json_escape(const std::wstring& value) {
    if (value.empty()) return {};
    int size = WideCharToMultiByte(CP_UTF8, 0, value.c_str(), -1, nullptr, 0, nullptr, nullptr);
    std::string result(static_cast<size_t>(size), '\0');
    WideCharToMultiByte(CP_UTF8, 0, value.c_str(), -1, result.data(), size, nullptr, nullptr);
    result.resize(static_cast<size_t>(size - 1));
    std::string escaped;
    for (char c : result) {
        if (c == '"' || c == '\\') escaped.push_back('\\');
        escaped.push_back(c);
    }
    return escaped;
}

std::string feature_level_name(D3D_FEATURE_LEVEL level) {
    switch (level) {
    case D3D_FEATURE_LEVEL_12_1: return "12_1";
    case D3D_FEATURE_LEVEL_12_0: return "12_0";
    case D3D_FEATURE_LEVEL_11_1: return "11_1";
    case D3D_FEATURE_LEVEL_11_0: return "11_0";
    case D3D_FEATURE_LEVEL_10_1: return "10_1";
    case D3D_FEATURE_LEVEL_10_0: return "10_0";
    default: return "9_x";
    }
}

void check(HRESULT result, const char* operation) {
    if (FAILED(result)) {
        std::ostringstream message;
        message << operation << " failed (0x" << std::hex << static_cast<unsigned long>(result) << ")";
        throw std::runtime_error(message.str());
    }
}

std::filesystem::path executable_directory() {
    std::vector<wchar_t> value(32768);
    DWORD length = GetModuleFileNameW(nullptr, value.data(), static_cast<DWORD>(value.size()));
    if (!length || length == value.size()) throw std::runtime_error("Executable path is unavailable");
    return std::filesystem::path(std::wstring(value.data(), length)).parent_path();
}

std::filesystem::path local_renderer_directory() {
    std::vector<wchar_t> value(32768);
    DWORD length = GetEnvironmentVariableW(L"LOCALAPPDATA", value.data(),
                                           static_cast<DWORD>(value.size()));
    if (!length || length >= value.size()) return executable_directory();
    return std::filesystem::path(std::wstring(value.data(), length)) /
           L"OES" / L"Core" / L"Renderer";
}

bool read_json_number(const std::string& json, const char* name, double& result) {
    const std::string needle = std::string("\"") + name + "\"";
    const auto key = json.find(needle);
    if (key == std::string::npos) return false;
    const auto colon = json.find(':', key + needle.size());
    if (colon == std::string::npos) return false;
    const char* start = json.c_str() + colon + 1;
    char* end = nullptr;
    result = std::strtod(start, &end);
    return end != start && std::isfinite(result);
}

template <typename T>
bool assign_bounded(const std::string& json, const char* name, T& target,
                    double low, double high) {
    double value = 0.0;
    if (!read_json_number(json, name, value) || value < low || value > high) return false;
    target = static_cast<T>(value);
    return true;
}

bool read_parameters(const std::filesystem::path& path, RendererParameters& output) {
    std::ifstream input(path, std::ios::binary);
    if (!input) return false;
    std::string json((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    double version = 0.0;
    if (!read_json_number(json, "version", version) || version != 1.0) return false;
    RendererParameters value;
    bool valid = true;
    valid &= assign_bounded(json, "scale", value.scale, .10, 1.50);
    valid &= assign_bounded(json, "x", value.x, -1.0, 1.0);
    valid &= assign_bounded(json, "y", value.y, -1.0, 1.0);
    valid &= assign_bounded(json, "rotation", value.rotation, -180.0, 180.0);
    valid &= assign_bounded(json, "opacity", value.opacity, 0.0, 1.0);
    valid &= assign_bounded(json, "glow_intensity", value.glow_intensity, 0.0, 2.0);
    valid &= assign_bounded(json, "glow_radius", value.glow_radius, 0.0, 32.0);
    valid &= assign_bounded(json, "brightness", value.brightness, .25, 2.50);
    valid &= assign_bounded(json, "exposure", value.exposure, -2.0, 2.0);
    valid &= assign_bounded(json, "lighting_intensity", value.lighting_intensity, .25, 2.50);
    valid &= assign_bounded(json, "depth", value.depth, -1.0, 1.0);
    valid &= assign_bounded(json, "perspective_x", value.perspective_x, -.50, .50);
    valid &= assign_bounded(json, "perspective_y", value.perspective_y, -.50, .50);
    valid &= assign_bounded(json, "width", value.width, 220.0, 1600.0);
    valid &= assign_bounded(json, "height", value.height, 220.0, 1600.0);
    if (!valid) return false;
    output = value;
    return true;
}

std::filesystem::path argument_path(const wchar_t* name, const std::filesystem::path& fallback) {
    int count = 0;
    wchar_t** values = CommandLineToArgvW(GetCommandLineW(), &count);
    if (!values) return fallback;
    std::filesystem::path result = fallback;
    for (int index = 1; index + 1 < count; ++index) {
        if (std::wstring(values[index]) == name) result = values[index + 1];
    }
    LocalFree(values);
    return result;
}

bool has_argument(const wchar_t* name) {
    int count = 0;
    wchar_t** values = CommandLineToArgvW(GetCommandLineW(), &count);
    if (!values) return false;
    bool found = false;
    for (int index = 1; index < count; ++index) found |= std::wstring(values[index]) == name;
    LocalFree(values);
    return found;
}

class Renderer {
public:
    Renderer(HWND window, bool force_warp) : window_(window), force_warp_(force_warp) {}

    void initialize(const std::filesystem::path& texture_path) {
        const auto started = Clock::now();
        create_device();
        create_composition_swap_chain();
        create_pipeline();
        create_texture(texture_path);
        diagnostics_.initialization_ms = elapsed_ms(started);
    }

    void apply_parameters(const RendererParameters& value) {
        parameters_ = value;
        if (value.width != diagnostics_.width || value.height != diagnostics_.height) {
            resize(value.width, value.height);
        }
        diagnostics_.parameters = parameters_;
    }

    void render(const Clock::time_point& process_started, bool first_frame = false) {
        const float transparent[] = {0.0f, 0.0f, 0.0f, 0.0f};
        context_->ClearRenderTargetView(target_.Get(), transparent);
        context_->OMSetRenderTargets(1, target_.GetAddressOf(), nullptr);
        const D3D11_VIEWPORT viewport{0.0f, 0.0f, static_cast<float>(diagnostics_.width),
                                      static_cast<float>(diagnostics_.height), 0.0f, 1.0f};
        context_->RSSetViewports(1, &viewport);
        context_->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP);
        UINT stride = sizeof(Vertex), offset = 0;
        context_->IASetVertexBuffers(0, 1, vertex_buffer_.GetAddressOf(), &stride, &offset);
        context_->IASetInputLayout(input_layout_.Get());
        context_->VSSetShader(vertex_shader_.Get(), nullptr, 0);
        update_shader_parameters();
        context_->VSSetConstantBuffers(0, 1, parameter_buffer_.GetAddressOf());
        context_->PSSetShader(pixel_shader_.Get(), nullptr, 0);
        context_->PSSetConstantBuffers(0, 1, parameter_buffer_.GetAddressOf());
        context_->PSSetShaderResources(0, 1, texture_view_.GetAddressOf());
        context_->PSSetSamplers(0, 1, sampler_.GetAddressOf());
        context_->Draw(4, 0);
        check(swap_chain_->Present(1, 0), "Present renderer frame");
        if (first_frame) {
            diagnostics_.first_frame_ms = elapsed_ms(process_started);
            PROCESS_MEMORY_COUNTERS memory{};
            memory.cb = sizeof(memory);
            if (GetProcessMemoryInfo(GetCurrentProcess(), &memory, sizeof(memory))) {
                diagnostics_.working_set_bytes = memory.WorkingSetSize;
            }
        }
    }

    const Diagnostics& diagnostics() const { return diagnostics_; }
    void set_fps(double value) { diagnostics_.fps = value; }

private:
    static double elapsed_ms(const Clock::time_point& start) {
        return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
    }

    void resize(UINT width, UINT height) {
        context_->OMSetRenderTargets(0, nullptr, nullptr);
        target_.Reset();
        check(swap_chain_->ResizeBuffers(0, width, height, DXGI_FORMAT_UNKNOWN, 0),
              "Resize renderer swap chain");
        ComPtr<ID3D11Texture2D> buffer;
        check(swap_chain_->GetBuffer(0, IID_PPV_ARGS(&buffer)), "Get resized swap-chain buffer");
        check(device_->CreateRenderTargetView(buffer.Get(), nullptr, &target_),
              "Create resized render target");
        diagnostics_.width = width;
        diagnostics_.height = height;
        SetWindowPos(window_, nullptr, 0, 0, static_cast<int>(width), static_cast<int>(height),
                     SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE);
    }

    void update_shader_parameters() {
        constexpr float pi = 3.14159265358979323846f;
        const float radians = parameters_.rotation * pi / 180.0f;
        ShaderParameters value{};
        value.transform[0] = std::cos(radians);
        value.transform[1] = std::sin(radians);
        value.transform[2] = parameters_.scale;
        value.transform[3] = parameters_.depth;
        value.translation[0] = parameters_.x;
        value.translation[1] = parameters_.y;
        value.translation[2] = parameters_.perspective_x;
        value.translation[3] = parameters_.perspective_y;
        value.appearance[0] = parameters_.opacity;
        value.appearance[1] = parameters_.brightness * parameters_.lighting_intensity *
                              std::pow(2.0f, parameters_.exposure);
        value.appearance[2] = parameters_.glow_intensity;
        value.appearance[3] = parameters_.glow_radius / 220.0f;
        value.texture[0] = texture_width_ ? 1.0f / texture_width_ : 0.0f;
        value.texture[1] = texture_height_ ? 1.0f / texture_height_ : 0.0f;
        context_->UpdateSubresource(parameter_buffer_.Get(), 0, nullptr, &value, 0, 0);
    }

    void create_device() {
        ComPtr<IDXGIFactory6> factory;
        check(CreateDXGIFactory2(0, IID_PPV_ARGS(&factory)), "Create DXGI factory");

        ComPtr<IDXGIAdapter1> selected;
        if (!force_warp_) {
            for (UINT index = 0;; ++index) {
                ComPtr<IDXGIAdapter1> candidate;
                HRESULT result = factory->EnumAdapterByGpuPreference(
                    index, DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE, IID_PPV_ARGS(&candidate));
                if (result == DXGI_ERROR_NOT_FOUND) break;
                check(result, "Enumerate DXGI adapter");
                DXGI_ADAPTER_DESC1 description{};
                check(candidate->GetDesc1(&description), "Read DXGI adapter description");
                if (!(description.Flags & DXGI_ADAPTER_FLAG_SOFTWARE)) {
                    selected = candidate;
                    diagnostics_.adapter_name = description.Description;
                    diagnostics_.vendor_id = description.VendorId;
                    diagnostics_.device_id = description.DeviceId;
                    break;
                }
            }
        }

        const D3D_FEATURE_LEVEL levels[] = {
            D3D_FEATURE_LEVEL_11_1, D3D_FEATURE_LEVEL_11_0,
            D3D_FEATURE_LEVEL_10_1, D3D_FEATURE_LEVEL_10_0
        };
        UINT flags = D3D11_CREATE_DEVICE_BGRA_SUPPORT;
#ifdef _DEBUG
        flags |= D3D11_CREATE_DEVICE_DEBUG;
#endif
        auto create = [&](IDXGIAdapter* adapter, D3D_DRIVER_TYPE driver) {
            HRESULT result = D3D11CreateDevice(
                adapter, driver, nullptr, flags, levels, ARRAYSIZE(levels), D3D11_SDK_VERSION,
                &device_, &diagnostics_.feature_level, &context_);
            if (result == E_INVALIDARG) {
                result = D3D11CreateDevice(
                    adapter, driver, nullptr, flags, levels + 1, ARRAYSIZE(levels) - 1,
                    D3D11_SDK_VERSION, &device_, &diagnostics_.feature_level, &context_);
            }
            return result;
        };
        HRESULT result = selected
            ? create(selected.Get(), D3D_DRIVER_TYPE_UNKNOWN)
            : create(nullptr, D3D_DRIVER_TYPE_WARP);
        if (FAILED(result) && selected) {
            selected.Reset();
            device_.Reset();
            context_.Reset();
            result = create(nullptr, D3D_DRIVER_TYPE_WARP);
        }
        check(result, "Create Direct3D 11 device");
        diagnostics_.hardware = selected != nullptr;
        if (!selected) {
            diagnostics_.adapter_name = L"Microsoft WARP";
            diagnostics_.vendor_id = 0x1414;
            diagnostics_.device_id = 0x008c;
        }
    }

    void create_composition_swap_chain() {
        ComPtr<IDXGIDevice> dxgi_device;
        check(device_.As(&dxgi_device), "Query DXGI device");
        ComPtr<IDXGIAdapter> adapter;
        check(dxgi_device->GetAdapter(&adapter), "Get DXGI adapter");
        ComPtr<IDXGIFactory2> factory;
        check(adapter->GetParent(IID_PPV_ARGS(&factory)), "Get DXGI factory");

        DXGI_SWAP_CHAIN_DESC1 description{};
        description.Width = kWidth;
        description.Height = kHeight;
        description.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
        description.SampleDesc.Count = 1;
        description.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
        description.BufferCount = 2;
        description.Scaling = DXGI_SCALING_STRETCH;
        description.SwapEffect = DXGI_SWAP_EFFECT_FLIP_SEQUENTIAL;
        description.AlphaMode = DXGI_ALPHA_MODE_PREMULTIPLIED;
        check(factory->CreateSwapChainForComposition(
            device_.Get(), &description, nullptr, &swap_chain_), "Create composition swap chain");

        ComPtr<ID3D11Texture2D> buffer;
        check(swap_chain_->GetBuffer(0, IID_PPV_ARGS(&buffer)), "Get swap-chain buffer");
        check(device_->CreateRenderTargetView(buffer.Get(), nullptr, &target_), "Create render target");

        ComPtr<IDCompositionDevice> composition;
        check(DCompositionCreateDevice(dxgi_device.Get(), IID_PPV_ARGS(&composition)),
              "Create DirectComposition device");
        ComPtr<IDCompositionTarget> target;
        check(composition->CreateTargetForHwnd(window_, TRUE, &target), "Create composition target");
        ComPtr<IDCompositionVisual> visual;
        check(composition->CreateVisual(&visual), "Create composition visual");
        check(visual->SetContent(swap_chain_.Get()), "Attach swap chain to visual");
        check(target->SetRoot(visual.Get()), "Attach visual to window");
        check(composition->Commit(), "Commit composition tree");
        composition_ = composition;
        composition_target_ = target;
        composition_visual_ = visual;
    }

    void create_pipeline() {
        static constexpr char shader[] = R"(
            cbuffer Parameters : register(b0) {
                float4 transform;
                float4 translation;
                float4 appearance;
                float4 texture_size;
            };
            struct Input { float2 position : POSITION; float2 uv : TEXCOORD0; };
            struct Output { float4 position : SV_POSITION; float2 uv : TEXCOORD0; };
            Output vs_main(Input value) {
                Output result;
                float2 rotated = float2(
                    value.position.x * transform.x - value.position.y * transform.y,
                    value.position.x * transform.y + value.position.y * transform.x);
                float depth_scale = 1.0 + transform.w * 0.15;
                float2 positioned = rotated * transform.z * depth_scale;
                positioned += float2(positioned.y * translation.z,
                                     positioned.x * translation.w);
                positioned += translation.xy;
                result.position = float4(positioned, 0.0, 1.0);
                result.uv = value.uv;
                return result;
            }
            Texture2D identity_texture : register(t0);
            SamplerState identity_sampler : register(s0);
            float4 ps_main(Output value) : SV_TARGET {
                float4 base = identity_texture.Sample(identity_sampler, value.uv);
                float2 offset = float2(appearance.w, appearance.w);
                float glow_alpha = 0.0;
                glow_alpha = max(glow_alpha, identity_texture.Sample(identity_sampler, value.uv + float2( offset.x, 0)).a);
                glow_alpha = max(glow_alpha, identity_texture.Sample(identity_sampler, value.uv + float2(-offset.x, 0)).a);
                glow_alpha = max(glow_alpha, identity_texture.Sample(identity_sampler, value.uv + float2(0,  offset.y)).a);
                glow_alpha = max(glow_alpha, identity_texture.Sample(identity_sampler, value.uv + float2(0, -offset.y)).a);
                glow_alpha = max(glow_alpha, identity_texture.Sample(identity_sampler, value.uv + offset).a);
                glow_alpha = max(glow_alpha, identity_texture.Sample(identity_sampler, value.uv - offset).a);
                glow_alpha = saturate((glow_alpha - base.a) * appearance.z);
                float alpha = saturate(max(base.a, glow_alpha) * appearance.x);
                float3 lit = base.rgb * appearance.y;
                float3 rgb = lerp(lit, float3(0.55, 0.82, 1.0), glow_alpha);
                return float4(rgb * alpha, alpha);
            }
        )";
        ComPtr<ID3DBlob> vertex_blob, pixel_blob, errors;
        check(D3DCompile(shader, sizeof(shader), "oes_identity.hlsl", nullptr, nullptr,
                         "vs_main", "vs_4_0", D3DCOMPILE_ENABLE_STRICTNESS, 0,
                         &vertex_blob, &errors), "Compile vertex shader");
        check(D3DCompile(shader, sizeof(shader), "oes_identity.hlsl", nullptr, nullptr,
                         "ps_main", "ps_4_0", D3DCOMPILE_ENABLE_STRICTNESS, 0,
                         &pixel_blob, &errors), "Compile pixel shader");
        check(device_->CreateVertexShader(vertex_blob->GetBufferPointer(), vertex_blob->GetBufferSize(),
                                           nullptr, &vertex_shader_), "Create vertex shader");
        check(device_->CreatePixelShader(pixel_blob->GetBufferPointer(), pixel_blob->GetBufferSize(),
                                          nullptr, &pixel_shader_), "Create pixel shader");
        D3D11_INPUT_ELEMENT_DESC elements[] = {
            {"POSITION", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 0, D3D11_INPUT_PER_VERTEX_DATA, 0},
            {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 8, D3D11_INPUT_PER_VERTEX_DATA, 0},
        };
        check(device_->CreateInputLayout(elements, ARRAYSIZE(elements), vertex_blob->GetBufferPointer(),
                                          vertex_blob->GetBufferSize(), &input_layout_),
              "Create input layout");
        const Vertex vertices[] = {
            {-1.0f,  1.0f, 0.0f, 0.0f}, { 1.0f,  1.0f, 1.0f, 0.0f},
            {-1.0f, -1.0f, 0.0f, 1.0f}, { 1.0f, -1.0f, 1.0f, 1.0f},
        };
        D3D11_BUFFER_DESC buffer_description{};
        buffer_description.ByteWidth = sizeof(vertices);
        buffer_description.Usage = D3D11_USAGE_IMMUTABLE;
        buffer_description.BindFlags = D3D11_BIND_VERTEX_BUFFER;
        D3D11_SUBRESOURCE_DATA buffer_data{vertices, 0, 0};
        check(device_->CreateBuffer(&buffer_description, &buffer_data, &vertex_buffer_),
              "Create vertex buffer");
        D3D11_SAMPLER_DESC sampler_description{};
        sampler_description.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
        sampler_description.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;
        sampler_description.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;
        sampler_description.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
        sampler_description.MaxLOD = D3D11_FLOAT32_MAX;
        check(device_->CreateSamplerState(&sampler_description, &sampler_), "Create sampler");
        D3D11_BUFFER_DESC parameter_description{};
        parameter_description.ByteWidth = sizeof(ShaderParameters);
        parameter_description.Usage = D3D11_USAGE_DEFAULT;
        parameter_description.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
        check(device_->CreateBuffer(&parameter_description, nullptr, &parameter_buffer_),
              "Create renderer parameter buffer");
    }

    void create_texture(const std::filesystem::path& path) {
        ComPtr<IWICImagingFactory> factory;
        check(CoCreateInstance(CLSID_WICImagingFactory2, nullptr, CLSCTX_INPROC_SERVER,
                               IID_PPV_ARGS(&factory)), "Create WIC factory");
        ComPtr<IWICBitmapDecoder> decoder;
        check(factory->CreateDecoderFromFilename(path.c_str(), nullptr, GENERIC_READ,
                                                 WICDecodeMetadataCacheOnLoad, &decoder),
              "Open canonical Eyeball texture");
        ComPtr<IWICBitmapFrameDecode> frame;
        check(decoder->GetFrame(0, &frame), "Decode canonical Eyeball texture");
        UINT width = 0, height = 0;
        check(frame->GetSize(&width, &height), "Read Eyeball texture dimensions");
        if (!width || !height) throw std::runtime_error("Canonical Eyeball texture is empty");
        texture_width_ = static_cast<float>(width);
        texture_height_ = static_cast<float>(height);
        ComPtr<IWICFormatConverter> converter;
        check(factory->CreateFormatConverter(&converter), "Create WIC converter");
        check(converter->Initialize(frame.Get(), GUID_WICPixelFormat32bppRGBA,
                                    WICBitmapDitherTypeNone, nullptr, 0.0,
                                    WICBitmapPaletteTypeCustom), "Convert Eyeball texture");
        std::vector<std::uint8_t> pixels(static_cast<size_t>(width) * height * 4);
        check(converter->CopyPixels(nullptr, width * 4, static_cast<UINT>(pixels.size()), pixels.data()),
              "Copy Eyeball texture pixels");
        D3D11_TEXTURE2D_DESC description{};
        description.Width = width;
        description.Height = height;
        description.MipLevels = 1;
        description.ArraySize = 1;
        description.Format = DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;
        description.SampleDesc.Count = 1;
        description.Usage = D3D11_USAGE_IMMUTABLE;
        description.BindFlags = D3D11_BIND_SHADER_RESOURCE;
        D3D11_SUBRESOURCE_DATA data{pixels.data(), width * 4, 0};
        ComPtr<ID3D11Texture2D> texture;
        check(device_->CreateTexture2D(&description, &data, &texture), "Create Eyeball texture");
        check(device_->CreateShaderResourceView(texture.Get(), nullptr, &texture_view_),
              "Create Eyeball texture view");
    }

    HWND window_{};
    bool force_warp_{};
    Diagnostics diagnostics_{};
    ComPtr<ID3D11Device> device_;
    ComPtr<ID3D11DeviceContext> context_;
    ComPtr<IDXGISwapChain1> swap_chain_;
    ComPtr<ID3D11RenderTargetView> target_;
    ComPtr<ID3D11VertexShader> vertex_shader_;
    ComPtr<ID3D11PixelShader> pixel_shader_;
    ComPtr<ID3D11InputLayout> input_layout_;
    ComPtr<ID3D11Buffer> vertex_buffer_;
    ComPtr<ID3D11Buffer> parameter_buffer_;
    ComPtr<ID3D11SamplerState> sampler_;
    ComPtr<ID3D11ShaderResourceView> texture_view_;
    ComPtr<IDCompositionDevice> composition_;
    ComPtr<IDCompositionTarget> composition_target_;
    ComPtr<IDCompositionVisual> composition_visual_;
    RendererParameters parameters_{};
    float texture_width_ = 0.0f;
    float texture_height_ = 0.0f;
};

void write_diagnostics(const std::filesystem::path& path, const Diagnostics& value,
                       const std::string& status, const std::string& error = {}) {
    if (path.empty()) return;
    std::error_code directory_error;
    std::filesystem::create_directories(path.parent_path(), directory_error);
    std::ofstream output(path, std::ios::trunc);
    output << "{\n"
           << "  \"status\": \"" << status << "\",\n"
           << "  \"adapter_name\": \"" << json_escape(value.adapter_name) << "\",\n"
           << "  \"vendor_id\": \"0x" << std::hex << std::setw(4) << std::setfill('0')
           << value.vendor_id << "\",\n"
           << "  \"device_id\": \"0x" << std::setw(4) << value.device_id << "\",\n"
           << std::dec << "  \"feature_level\": \"" << feature_level_name(value.feature_level) << "\",\n"
           << "  \"device_type\": \"" << (value.hardware ? "hardware" : "warp") << "\",\n"
           << "  \"initialization_ms\": " << value.initialization_ms << ",\n"
           << "  \"first_frame_ms\": " << value.first_frame_ms << ",\n"
           << "  \"working_set_bytes\": " << value.working_set_bytes << ",\n"
           << "  \"fps\": " << value.fps << ",\n"
           << "  \"width\": " << value.width << ",\n"
           << "  \"height\": " << value.height << ",\n"
           << "  \"parameters\": {\n"
           << "    \"scale\": " << value.parameters.scale << ",\n"
           << "    \"x\": " << value.parameters.x << ",\n"
           << "    \"y\": " << value.parameters.y << ",\n"
           << "    \"rotation\": " << value.parameters.rotation << ",\n"
           << "    \"opacity\": " << value.parameters.opacity << ",\n"
           << "    \"glow_intensity\": " << value.parameters.glow_intensity << ",\n"
           << "    \"glow_radius\": " << value.parameters.glow_radius << ",\n"
           << "    \"brightness\": " << value.parameters.brightness << ",\n"
           << "    \"exposure\": " << value.parameters.exposure << ",\n"
           << "    \"lighting_intensity\": " << value.parameters.lighting_intensity << ",\n"
           << "    \"depth\": " << value.parameters.depth << ",\n"
           << "    \"perspective_x\": " << value.parameters.perspective_x << ",\n"
           << "    \"perspective_y\": " << value.parameters.perspective_y << ",\n"
           << "    \"width\": " << value.parameters.width << ",\n"
           << "    \"height\": " << value.parameters.height << "\n"
           << "  },\n"
           << "  \"error\": \"";
    for (char c : error) {
        if (c == '"' || c == '\\') output << '\\';
        output << c;
    }
    output << "\"\n}\n";
}

LRESULT CALLBACK window_procedure(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
    if (message == WM_NCHITTEST) return HTCAPTION;
    if (message == WM_DESTROY) {
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(window, message, wparam, lparam);
}
} // namespace

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, PWSTR, int) {
    const auto process_started = Clock::now();
    const auto directory = executable_directory();
    const auto texture = argument_path(L"--asset", directory / L"assets" / L"oes-logo.png");
    const auto local_directory = local_renderer_directory();
    const auto control_path = argument_path(
        L"--control", local_directory / L"renderer-tuning.json");
    const auto diagnostics_path = argument_path(
        L"--diagnostics", local_directory / L"renderer-diagnostics.json");
    Diagnostics diagnostics;
    try {
        check(CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED), "Initialize COM");
        WNDCLASSEXW window_class{sizeof(window_class)};
        window_class.hInstance = instance;
        window_class.lpfnWndProc = window_procedure;
        window_class.lpszClassName = kWindowClass;
        window_class.hCursor = LoadCursor(nullptr, IDC_ARROW);
        check(RegisterClassExW(&window_class) ? S_OK : HRESULT_FROM_WIN32(GetLastError()),
              "Register renderer window");
        HWND window = CreateWindowExW(
            WS_EX_NOREDIRECTIONBITMAP | WS_EX_TOOLWINDOW, kWindowClass, L"OES Eyeball Native Proof",
            WS_POPUP, CW_USEDEFAULT, CW_USEDEFAULT, kWidth, kHeight,
            nullptr, nullptr, instance, nullptr);
        if (!window) check(HRESULT_FROM_WIN32(GetLastError()), "Create renderer window");
        Renderer renderer(window, has_argument(L"--force-warp"));
        renderer.initialize(texture);
        RendererParameters parameters;
        if (read_parameters(control_path, parameters)) renderer.apply_parameters(parameters);
        else renderer.apply_parameters(RendererParameters{});
        ShowWindow(window, SW_SHOW);
        renderer.render(process_started, true);
        diagnostics = renderer.diagnostics();
        write_diagnostics(diagnostics_path, diagnostics, "ready");

        MSG message{};
        auto diagnostics_started = Clock::now();
        auto control_checked = Clock::now();
        const auto milliseconds_since = [](const Clock::time_point& start) {
            return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
        };
        std::uint64_t frames = 1;
        bool running = true;
        while (running) {
            while (PeekMessageW(&message, nullptr, 0, 0, PM_REMOVE)) {
                if (message.message == WM_QUIT) {
                    running = false;
                    break;
                }
                TranslateMessage(&message);
                DispatchMessageW(&message);
            }
            if (!running) break;
            if (milliseconds_since(control_checked) >= 50.0) {
                RendererParameters updated;
                if (read_parameters(control_path, updated)) renderer.apply_parameters(updated);
                control_checked = Clock::now();
            }
            renderer.render(process_started);
            ++frames;
            const double interval = milliseconds_since(diagnostics_started);
            if (interval >= 1000.0) {
                renderer.set_fps(static_cast<double>(frames) * 1000.0 / interval);
                diagnostics = renderer.diagnostics();
                write_diagnostics(diagnostics_path, diagnostics, "ready");
                frames = 0;
                diagnostics_started = Clock::now();
            }
        }
        CoUninitialize();
        return 0;
    } catch (const std::exception& error) {
        write_diagnostics(diagnostics_path, diagnostics, "failed", error.what());
        return 1;
    }
}
