#include <windows.h>
#include <d3d11.h>
#include <d3dcompiler.h>
#include <dcomp.h>
#include <dxgi1_6.h>
#include <wincodec.h>
#include <psapi.h>
#include <wrl/client.h>

#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
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

    void render_first_frame(const Clock::time_point& process_started) {
        const float transparent[] = {0.0f, 0.0f, 0.0f, 0.0f};
        context_->ClearRenderTargetView(target_.Get(), transparent);
        context_->OMSetRenderTargets(1, target_.GetAddressOf(), nullptr);
        const D3D11_VIEWPORT viewport{0.0f, 0.0f, static_cast<float>(kWidth),
                                      static_cast<float>(kHeight), 0.0f, 1.0f};
        context_->RSSetViewports(1, &viewport);
        context_->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLESTRIP);
        UINT stride = sizeof(Vertex), offset = 0;
        context_->IASetVertexBuffers(0, 1, vertex_buffer_.GetAddressOf(), &stride, &offset);
        context_->IASetInputLayout(input_layout_.Get());
        context_->VSSetShader(vertex_shader_.Get(), nullptr, 0);
        context_->PSSetShader(pixel_shader_.Get(), nullptr, 0);
        context_->PSSetShaderResources(0, 1, texture_view_.GetAddressOf());
        context_->PSSetSamplers(0, 1, sampler_.GetAddressOf());
        context_->Draw(4, 0);
        check(swap_chain_->Present(1, 0), "Present first frame");
        diagnostics_.first_frame_ms = elapsed_ms(process_started);
        PROCESS_MEMORY_COUNTERS memory{};
        memory.cb = sizeof(memory);
        if (GetProcessMemoryInfo(GetCurrentProcess(), &memory, sizeof(memory))) {
            diagnostics_.working_set_bytes = memory.WorkingSetSize;
        }
    }

    const Diagnostics& diagnostics() const { return diagnostics_; }

private:
    static double elapsed_ms(const Clock::time_point& start) {
        return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
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
            struct Input { float2 position : POSITION; float2 uv : TEXCOORD0; };
            struct Output { float4 position : SV_POSITION; float2 uv : TEXCOORD0; };
            Output vs_main(Input value) {
                Output result;
                result.position = float4(value.position, 0.0, 1.0);
                result.uv = value.uv;
                return result;
            }
            Texture2D identity_texture : register(t0);
            SamplerState identity_sampler : register(s0);
            float4 ps_main(Output value) : SV_TARGET {
                float4 color = identity_texture.Sample(identity_sampler, value.uv);
                color.rgb *= color.a;
                return color;
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
            {-0.86f,  0.86f, 0.0f, 0.0f}, { 0.86f,  0.86f, 1.0f, 0.0f},
            {-0.86f, -0.86f, 0.0f, 1.0f}, { 0.86f, -0.86f, 1.0f, 1.0f},
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
    ComPtr<ID3D11SamplerState> sampler_;
    ComPtr<ID3D11ShaderResourceView> texture_view_;
    ComPtr<IDCompositionDevice> composition_;
    ComPtr<IDCompositionTarget> composition_target_;
    ComPtr<IDCompositionVisual> composition_visual_;
};

void write_diagnostics(const std::filesystem::path& path, const Diagnostics& value,
                       const std::string& status, const std::string& error = {}) {
    if (path.empty()) return;
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
    const auto diagnostics_path = argument_path(
        L"--diagnostics", directory / L"oes-eyeball-renderer-diagnostics.json");
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
        ShowWindow(window, SW_SHOW);
        renderer.render_first_frame(process_started);
        diagnostics = renderer.diagnostics();
        write_diagnostics(diagnostics_path, diagnostics, "ready");

        MSG message{};
        while (GetMessageW(&message, nullptr, 0, 0) > 0) {
            TranslateMessage(&message);
            DispatchMessageW(&message);
        }
        CoUninitialize();
        return 0;
    } catch (const std::exception& error) {
        write_diagnostics(diagnostics_path, diagnostics, "failed", error.what());
        return 1;
    }
}
