#include <windows.h>
#include <d3d11.h>
#include <d3dcompiler.h>
#include <dcomp.h>
#include <dxgi1_6.h>
#include <wincodec.h>
#include <psapi.h>
#include <shellapi.h>
#include <wrl/client.h>
#include <DirectXMath.h>

#include <array>
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
#include <utility>
#include <vector>

#include "scene_geometry.h"
#include "character_system.h"

using Microsoft::WRL::ComPtr;
using Clock = std::chrono::steady_clock;
using namespace DirectX;

namespace {
constexpr UINT kWidth = 512;
constexpr UINT kHeight = 512;
constexpr wchar_t kWindowClass[] = L"OesEyeballNativeRenderer";
constexpr float kPi = 3.14159265358979323846f;

struct RendererParameters {
    float scale=1, x=0, y=0, z=0;
    float rotation_x=0, rotation_y=0, rotation_z=0;
    float brightness=1, exposure=.92f, lighting_intensity=1;
    float camera_fov=50, camera_z=7.4f;
    float iris_scale=1, iris_depth=0, pupil_scale=1, pupil_depth=0;
    float glass_intensity=1, rim_intensity=1, orbit_intensity=1, particle_intensity=1;
    float logo_scale=1, logo_depth=0;
    UINT width=kWidth, height=kHeight;
};

struct Diagnostics {
    std::wstring adapter_name=L"unavailable";
    UINT vendor_id=0, device_id=0;
    D3D_FEATURE_LEVEL feature_level=D3D_FEATURE_LEVEL_9_1;
    bool hardware=false;
    double initialization_ms=0, first_frame_ms=0, fps=0;
    SIZE_T working_set_bytes=0;
    UINT width=kWidth, height=kHeight;
    RendererParameters parameters{};
};

struct alignas(16) FrameConstants {
    XMFLOAT4X4 view_projection{};
    XMFLOAT4 camera_exposure{}, ambient{}, directional{}, directional_color{};
    XMFLOAT4 point_position[4]{}, point_color[4]{};
};

struct alignas(16) ObjectConstants {
    XMFLOAT4X4 world{}, normal_world{};
    XMFLOAT4 base_color{}, emissive{}, surface{};
};

enum class BlendMode { opaque, alpha, additive };
struct Material {
    XMFLOAT4 base{}, emissive{};
    float roughness=.5f, metalness=0, mode=0;
    bool textured=false, depth_write=true;
    BlendMode blend=BlendMode::opaque;
};
struct Mesh {
    std::string name;
    ComPtr<ID3D11Buffer> vertices, indices;
    UINT index_count=0;
    D3D11_PRIMITIVE_TOPOLOGY topology=D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST;
};

void check(HRESULT result, const char* operation) {
    if (FAILED(result)) { std::ostringstream message; message << operation << " failed (0x"
        << std::hex << static_cast<unsigned long>(result) << ")"; throw std::runtime_error(message.str()); }
}
std::string json_escape(const std::wstring& value) {
    if (value.empty()) return {};
    int size=WideCharToMultiByte(CP_UTF8,0,value.c_str(),-1,nullptr,0,nullptr,nullptr);
    std::string text(static_cast<std::size_t>(size),'\0');
    WideCharToMultiByte(CP_UTF8,0,value.c_str(),-1,text.data(),size,nullptr,nullptr);
    text.resize(static_cast<std::size_t>(size-1)); std::string escaped;
    for(char character:text){if(character=='"'||character=='\\')escaped.push_back('\\');escaped.push_back(character);} return escaped;
}
std::string feature_level_name(D3D_FEATURE_LEVEL level) {
    switch(level){case D3D_FEATURE_LEVEL_12_1:return"12_1";case D3D_FEATURE_LEVEL_12_0:return"12_0";
    case D3D_FEATURE_LEVEL_11_1:return"11_1";case D3D_FEATURE_LEVEL_11_0:return"11_0";
    case D3D_FEATURE_LEVEL_10_1:return"10_1";case D3D_FEATURE_LEVEL_10_0:return"10_0";default:return"9_x";}
}
std::filesystem::path executable_directory(){std::vector<wchar_t> value(32768);DWORD length=GetModuleFileNameW(nullptr,value.data(),static_cast<DWORD>(value.size()));if(!length||length==value.size())throw std::runtime_error("Executable path is unavailable");return std::filesystem::path(std::wstring(value.data(),length)).parent_path();}
std::filesystem::path local_renderer_directory(){std::vector<wchar_t> value(32768);DWORD length=GetEnvironmentVariableW(L"LOCALAPPDATA",value.data(),static_cast<DWORD>(value.size()));if(!length||length>=value.size())return executable_directory();return std::filesystem::path(std::wstring(value.data(),length))/L"OES"/L"Core"/L"Renderer";}
std::filesystem::path argument_path(const wchar_t* name,const std::filesystem::path& fallback){int count=0;wchar_t** values=CommandLineToArgvW(GetCommandLineW(),&count);if(!values)return fallback;auto result=fallback;for(int i=1;i+1<count;++i)if(std::wstring(values[i])==name)result=values[i+1];LocalFree(values);return result;}
bool has_argument(const wchar_t* name){int count=0;wchar_t** values=CommandLineToArgvW(GetCommandLineW(),&count);if(!values)return false;bool found=false;for(int i=1;i<count;++i)found|=std::wstring(values[i])==name;LocalFree(values);return found;}
std::wstring argument_value(const wchar_t* name,const wchar_t* fallback){int count=0;wchar_t** values=CommandLineToArgvW(GetCommandLineW(),&count);if(!values)return fallback;std::wstring result=fallback;for(int i=1;i+1<count;++i)if(std::wstring(values[i])==name)result=values[i+1];LocalFree(values);return result;}
bool reduced_motion_enabled(){BOOL enabled=TRUE;SystemParametersInfoW(SPI_GETCLIENTAREAANIMATION,0,&enabled,0);return has_argument(L"--reduced-motion")||!enabled;}
bool read_json_number(const std::string& json,const char* name,double& result){const std::string needle=std::string("\"")+name+"\"";auto key=json.find(needle);if(key==std::string::npos)return false;auto colon=json.find(':',key+needle.size());if(colon==std::string::npos)return false;const char* start=json.c_str()+colon+1;char* end=nullptr;result=std::strtod(start,&end);return end!=start&&std::isfinite(result);}
template<typename T>bool assign_bounded(const std::string& json,const char* name,T& target,double low,double high){double value=0;if(!read_json_number(json,name,value)||value<low||value>high)return false;target=static_cast<T>(value);return true;}
bool read_parameters(const std::filesystem::path& path,RendererParameters& output){std::ifstream input(path,std::ios::binary);if(!input)return false;std::string json((std::istreambuf_iterator<char>(input)),{});double version=0;if(!read_json_number(json,"version",version)||version!=2)return false;RendererParameters v;bool ok=true;
    ok&=assign_bounded(json,"scale",v.scale,.25,1.5);ok&=assign_bounded(json,"x",v.x,-1,1);ok&=assign_bounded(json,"y",v.y,-1,1);ok&=assign_bounded(json,"z",v.z,-3,3);
    ok&=assign_bounded(json,"rotation_x",v.rotation_x,-180,180);ok&=assign_bounded(json,"rotation_y",v.rotation_y,-180,180);ok&=assign_bounded(json,"rotation_z",v.rotation_z,-180,180);
    ok&=assign_bounded(json,"brightness",v.brightness,.25,2.5);ok&=assign_bounded(json,"exposure",v.exposure,.25,2.5);ok&=assign_bounded(json,"lighting_intensity",v.lighting_intensity,.25,2.5);
    ok&=assign_bounded(json,"camera_fov",v.camera_fov,25,80);ok&=assign_bounded(json,"camera_z",v.camera_z,5,14);
    ok&=assign_bounded(json,"iris_scale",v.iris_scale,.6,1.4);ok&=assign_bounded(json,"iris_depth",v.iris_depth,-.35,.35);ok&=assign_bounded(json,"pupil_scale",v.pupil_scale,.6,1.4);ok&=assign_bounded(json,"pupil_depth",v.pupil_depth,-.35,.35);
    ok&=assign_bounded(json,"glass_intensity",v.glass_intensity,0,2);ok&=assign_bounded(json,"rim_intensity",v.rim_intensity,0,2);ok&=assign_bounded(json,"orbit_intensity",v.orbit_intensity,0,2);ok&=assign_bounded(json,"particle_intensity",v.particle_intensity,0,2);
    ok&=assign_bounded(json,"logo_scale",v.logo_scale,.5,1.5);ok&=assign_bounded(json,"logo_depth",v.logo_depth,-.3,.3);ok&=assign_bounded(json,"width",v.width,220,1600);ok&=assign_bounded(json,"height",v.height,220,1600);
    if(!ok)return false;output=v;return true;}
float radians(float degrees){return degrees*kPi/180.0f;}
XMFLOAT4 color(unsigned value,float alpha=1){return{float((value>>16)&255)/255,float((value>>8)&255)/255,float(value&255)/255,alpha};}

class Renderer {
public:
    Renderer(HWND window,bool force_warp)
        :Renderer(window,force_warp,
                  oes::character::animation_state(argument_value(L"--animation",L"idle")),
                  reduced_motion_enabled(),
                  oes::character::view(argument_value(L"--view",L"front"))){}
    Renderer(HWND window,bool force_warp,oes::character::AnimationState animation,
             bool reduced_motion,oes::character::View view)
        :window_(window),force_warp_(force_warp),animation_(animation,reduced_motion),view_(view){screenshot_path_=argument_path(L"--screenshot",{});}
    void initialize(const std::filesystem::path& texture){auto started=Clock::now();create_device();create_swap_chain();create_pipeline();create_states();create_texture(texture);create_geometry();diagnostics_.initialization_ms=elapsed(started);}
    void apply_parameters(const RendererParameters& value){parameters_=value;if(value.width!=diagnostics_.width||value.height!=diagnostics_.height)resize(value.width,value.height);diagnostics_.parameters=parameters_;}
    const Diagnostics& diagnostics()const{return diagnostics_;}void set_fps(double value){diagnostics_.fps=value;if(!screenshot_path_.empty()&&!screenshot_written_){capture_screenshot(screenshot_path_);screenshot_written_=true;}}
    void render(const Clock::time_point& process_started,bool first=false){const float clear[4]={0,0,0,0};context_->ClearRenderTargetView(target_.Get(),clear);context_->ClearDepthStencilView(depth_view_.Get(),D3D11_CLEAR_DEPTH,1,0);context_->OMSetRenderTargets(1,target_.GetAddressOf(),depth_view_.Get());D3D11_VIEWPORT viewport{0,0,float(diagnostics_.width),float(diagnostics_.height),0,1};context_->RSSetViewports(1,&viewport);context_->RSSetState(raster_.Get());context_->IASetInputLayout(input_layout_.Get());context_->VSSetShader(vertex_shader_.Get(),nullptr,0);context_->PSSetShader(pixel_shader_.Get(),nullptr,0);context_->PSSetSamplers(0,1,sampler_.GetAddressOf());context_->PSSetShaderResources(0,1,texture_view_.GetAddressOf());update_frame();context_->VSSetConstantBuffers(0,1,frame_buffer_.GetAddressOf());context_->PSSetConstantBuffers(0,1,frame_buffer_.GetAddressOf());context_->VSSetConstantBuffers(1,1,object_buffer_.GetAddressOf());context_->PSSetConstantBuffers(1,1,object_buffer_.GetAddressOf());const auto pose=animation_.sample(elapsed(process_started)/1000.0);XMMATRIX root=root_matrix(pose);draw_core(root,pose);draw_face(root,pose);draw_orbits(root);draw_particles(root);check(swap_chain_->Present(1,0),"Present renderer frame");if(first){diagnostics_.first_frame_ms=elapsed(process_started);PROCESS_MEMORY_COUNTERS memory{};memory.cb=sizeof(memory);if(GetProcessMemoryInfo(GetCurrentProcess(),&memory,sizeof(memory)))diagnostics_.working_set_bytes=memory.WorkingSetSize;}}
private:
    static double elapsed(const Clock::time_point& start){return std::chrono::duration<double,std::milli>(Clock::now()-start).count();}
    XMMATRIX root_matrix(const oes::character::Pose& pose)const{if(animation_.state()==oes::character::AnimationState::idle||animation_.reduced_motion())Sleep(15);float view_yaw=view_==oes::character::View::three_quarter?-.58f:(view_==oes::character::View::side?-1.18f:0);float interaction=(!animation_.reduced_motion()&&(GetAsyncKeyState(VK_LBUTTON)&0x8000))?.065f:0;return XMMatrixScaling(parameters_.scale,parameters_.scale,parameters_.scale)*XMMatrixRotationRollPitchYaw(radians(parameters_.rotation_x)+pose.pitch,radians(parameters_.rotation_y)+pose.yaw+view_yaw+interaction,radians(parameters_.rotation_z))*XMMatrixTranslation(parameters_.x,parameters_.y+pose.hover_y,parameters_.z);}
    Mesh create_mesh(std::string name,const oes::geometry::MeshData& data,D3D11_PRIMITIVE_TOPOLOGY topology=D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST){if(data.vertices.empty()||data.indices.empty())throw std::runtime_error("Empty scene mesh");Mesh mesh;mesh.name=std::move(name);mesh.index_count=static_cast<UINT>(data.indices.size());mesh.topology=topology;D3D11_BUFFER_DESC vd{};vd.ByteWidth=static_cast<UINT>(data.vertices.size()*sizeof(oes::geometry::Vertex));vd.Usage=D3D11_USAGE_IMMUTABLE;vd.BindFlags=D3D11_BIND_VERTEX_BUFFER;D3D11_SUBRESOURCE_DATA vi{data.vertices.data(),0,0};check(device_->CreateBuffer(&vd,&vi,&mesh.vertices),"Create scene vertex buffer");D3D11_BUFFER_DESC id{};id.ByteWidth=static_cast<UINT>(data.indices.size()*sizeof(std::uint32_t));id.Usage=D3D11_USAGE_IMMUTABLE;id.BindFlags=D3D11_BIND_INDEX_BUFFER;D3D11_SUBRESOURCE_DATA ii{data.indices.data(),0,0};check(device_->CreateBuffer(&id,&ii,&mesh.indices),"Create scene index buffer");return mesh;}
    void create_geometry(){using namespace oes::geometry;
        outer_=create_mesh("mechanical_body",sphere(1.18f,112,96));
        inner_=create_mesh("recessed_core",sphere(1.135f,96,80));
        energy_=create_mesh("energy_lattice",icosphere_lines(1.158f,5),D3D11_PRIMITIVE_TOPOLOGY_LINELIST);
        glass_=create_mesh("optical_glass",sphere(1.205f,96,80));
        rim_=create_mesh("housing_seam",torus(1.225f,.014f,16,180));
        housing_ring_=create_mesh("front_housing",torus(.79f,.075f,24,160));
        housing_rib_=create_mesh("body_rib",torus(1.19f,.032f,18,160));
        blade_=create_mesh("aperture_blade",aperture_blade(.29f,.72f,-.40f,.43f,.055f));
        iris_=create_mesh("layered_iris",spherical_annulus(1.203f,.225f,.565f,128,32));
        iris_ring_=create_mesh("iris_focusing_ring",spherical_annulus(1.211f,.205f,.285f,128,12));
        pupil_=create_mesh("recessed_pupil",spherical_cap(1.187f,.235f,112,24));
        pupil_glow_=create_mesh("pupil_light_ring",spherical_annulus(1.217f,.215f,.252f,112,6));
        logo_=create_mesh("oes_identity",outward_identity_plane(.45f,.45f));
        orbit_outer_=create_mesh("orbit_outer",torus(1.72f,.009f,14,180));orbit_middle_=create_mesh("orbit_middle",torus(1.51f,.011f,14,180));orbit_inner_=create_mesh("orbit_inner",torus(1.37f,.008f,14,180));std::array<float,5> sizes{.043f,.031f,.038f,.027f,.034f};for(std::size_t i=0;i<nodes_.size();++i)nodes_[i]=create_mesh("orbit_node",sphere(sizes[i],18,18));particles_=create_mesh("particles",particles(110,0x004f4553u,1.46f,2.71f),D3D11_PRIMITIVE_TOPOLOGY_POINTLIST);}
    Material surface(XMFLOAT4 base,XMFLOAT4 emissive,float roughness,float metalness,BlendMode blend=BlendMode::opaque,float mode=0)const{Material m;m.base=base;m.emissive=emissive;m.roughness=roughness;m.metalness=metalness;m.blend=blend;m.mode=mode;return m;}
    Material additive(XMFLOAT4 value)const{Material m;m.base=value;m.emissive={value.x,value.y,value.z,1};m.roughness=.2f;m.blend=BlendMode::additive;m.depth_write=false;m.mode=2;return m;}
    void draw_core(FXMMATRIX root,const oes::character::Pose& pose){
        draw(inner_,root,surface(color(0x01040a,1),color(0x0ea5e9,.008f),.5f,.72f),true);
        draw(outer_,root,surface(color(0x07111f,1),color(0x0c4a6e,.012f),.24f,.88f),true);
        draw(energy_,XMMatrixRotationRollPitchYaw(.28f+pose.pitch,-.24f+pose.yaw,.08f)*root,additive(color(0x38bdf8,.026f)),false);
        const Material rib=surface(color(0x111c2d,1),color(0x38bdf8,.018f),.2f,.94f);
        draw(housing_rib_,XMMatrixRotationX(kPi*.5f)*root,rib,true);
        draw(housing_rib_,XMMatrixRotationY(kPi*.5f)*root,rib,true);
        if(parameters_.glass_intensity>.001f)draw(glass_,root,surface(color(0xb9e9ff,.045f*parameters_.glass_intensity),color(0x7dd3fc,.012f*parameters_.glass_intensity),.04f,.08f,BlendMode::alpha,1),false);
        if(parameters_.rim_intensity>.001f)draw(rim_,root,additive(color(0x38bdf8,.12f*parameters_.rim_intensity)),false);
    }
    void draw_face(FXMMATRIX root,const oes::character::Pose& pose){
        const Material housing=surface(color(0x172235,1),color(0x0ea5e9,.018f),.19f,.96f);
        draw(housing_ring_,XMMatrixTranslation(0,0,.93f)*root,housing,true);
        const float blade_motion=(1.0f-pose.aperture)*.34f;
        for(int index=0;index<8;++index){const float angle=float(index)*kPi*.25f+blade_motion;XMMATRIX transform=XMMatrixRotationZ(angle)*XMMatrixTranslation(0,0,1.055f)*root;draw(blade_,transform,surface(color(index%2?0x1b2a40:0x253852,1),color(0x0891b2,.015f),.17f,.92f),true);}
        XMMATRIX gaze=XMMatrixTranslation(pose.gaze_x,pose.gaze_y,pose.lens_depth);
        XMMATRIX iris_transform=XMMatrixScaling(parameters_.iris_scale,parameters_.iris_scale,1)*gaze*XMMatrixTranslation(0,0,parameters_.iris_depth)*root;
        draw(iris_,iris_transform,surface(color(0x063f5b,1),color(0x22d3ee,.055f),.24f,.56f),true);
        draw(iris_ring_,iris_transform,surface(color(0x67e8f9,1),color(0x0ea5e9,.085f),.16f,.62f),true);
        const float pupil_scale=parameters_.pupil_scale*pose.pupil_scale*pose.aperture;
        XMMATRIX pupil_transform=XMMatrixScaling(pupil_scale,pupil_scale,1)*gaze*XMMatrixTranslation(0,0,parameters_.pupil_depth)*root;
        draw(pupil_,pupil_transform,surface(color(0x000105,1),color(0x020617,.004f),.38f,.46f),true);
        draw(pupil_glow_,pupil_transform,additive(color(0x22d3ee,.075f)),false);
        Material identity=additive(color(0xffffff));identity.textured=true;identity.blend=BlendMode::alpha;
        draw(logo_,XMMatrixScaling(parameters_.logo_scale,parameters_.logo_scale,1)*gaze*XMMatrixTranslation(0,0,1.201f+parameters_.logo_depth)*root,identity,false);
    }
    void draw_node(std::size_t index,float radius,float angle,FXMMATRIX orbit,FXMMATRIX root,unsigned tint){draw(nodes_[index],XMMatrixTranslation(std::cos(angle)*radius,std::sin(angle)*radius,0)*orbit*root,additive(color(tint,.42f*parameters_.orbit_intensity)),false);}
    void draw_orbits(FXMMATRIX root){if(parameters_.orbit_intensity<=.001f)return;XMMATRIX outer=XMMatrixRotationRollPitchYaw(1.12f,.1f,.16f),middle=XMMatrixRotationRollPitchYaw(.18f,1.12f,-.32f),inner=XMMatrixRotationRollPitchYaw(.74f,.82f,.42f);draw(orbit_outer_,outer*root,additive(color(0x38bdf8,.18f*parameters_.orbit_intensity)),false);draw(orbit_middle_,middle*root,additive(color(0x2563eb,.21f*parameters_.orbit_intensity)),false);draw(orbit_inner_,inner*root,additive(color(0xa855f7,.16f*parameters_.orbit_intensity)),false);draw_node(0,1.72f,0,outer,root,0x38bdf8);draw_node(1,1.72f,kPi,outer,root,0x2563eb);draw_node(2,1.51f,kPi*.5f,middle,root,0x2563eb);draw_node(3,1.51f,kPi*1.4f,middle,root,0x38bdf8);draw_node(4,1.37f,kPi*1.35f,inner,root,0xa855f7);}
    void draw_particles(FXMMATRIX root){if(parameters_.particle_intensity<=.001f)return;draw(particles_,root,additive(color(0x38bdf8,.16f*parameters_.particle_intensity)),false);}
    void draw(const Mesh& mesh,FXMMATRIX world,const Material& material,bool depth_write){ObjectConstants c{};XMStoreFloat4x4(&c.world,XMMatrixTranspose(world));XMVECTOR determinant{};XMStoreFloat4x4(&c.normal_world,XMMatrixInverse(&determinant,world));c.base_color=material.base;c.emissive=material.emissive;c.surface={material.roughness,material.metalness,material.mode,material.textured?1.0f:0.0f};context_->UpdateSubresource(object_buffer_.Get(),0,nullptr,&c,0,0);ID3D11BlendState* blend=material.blend==BlendMode::additive?additive_blend_.Get():(material.blend==BlendMode::alpha?alpha_blend_.Get():opaque_blend_.Get());float factor[4]={};context_->OMSetBlendState(blend,factor,0xffffffff);context_->OMSetDepthStencilState(depth_write&&material.depth_write?depth_write_state_.Get():depth_read_state_.Get(),0);UINT stride=sizeof(oes::geometry::Vertex),offset=0;context_->IASetVertexBuffers(0,1,mesh.vertices.GetAddressOf(),&stride,&offset);context_->IASetIndexBuffer(mesh.indices.Get(),DXGI_FORMAT_R32_UINT,0);context_->IASetPrimitiveTopology(mesh.topology);context_->DrawIndexed(mesh.index_count,0,0);}
    void capture_screenshot(const std::filesystem::path& path){ComPtr<ID3D11Texture2D> source;check(swap_chain_->GetBuffer(0,IID_PPV_ARGS(&source)),"Read screenshot buffer");D3D11_TEXTURE2D_DESC d{};source->GetDesc(&d);d.Usage=D3D11_USAGE_STAGING;d.BindFlags=0;d.CPUAccessFlags=D3D11_CPU_ACCESS_READ;d.MiscFlags=0;ComPtr<ID3D11Texture2D> staging;check(device_->CreateTexture2D(&d,nullptr,&staging),"Create screenshot staging texture");context_->CopyResource(staging.Get(),source.Get());D3D11_MAPPED_SUBRESOURCE mapped{};check(context_->Map(staging.Get(),0,D3D11_MAP_READ,0,&mapped),"Map screenshot texture");std::error_code ignored;std::filesystem::create_directories(path.parent_path(),ignored);ComPtr<IWICImagingFactory> factory;check(CoCreateInstance(CLSID_WICImagingFactory2,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&factory)),"Create screenshot factory");ComPtr<IWICStream> stream;check(factory->CreateStream(&stream),"Create screenshot stream");check(stream->InitializeFromFilename(path.c_str(),GENERIC_WRITE),"Open screenshot output");ComPtr<IWICBitmapEncoder> encoder;check(factory->CreateEncoder(GUID_ContainerFormatPng,nullptr,&encoder),"Create PNG encoder");check(encoder->Initialize(stream.Get(),WICBitmapEncoderNoCache),"Initialize PNG encoder");ComPtr<IWICBitmapFrameEncode> frame;check(encoder->CreateNewFrame(&frame,nullptr),"Create PNG frame");check(frame->Initialize(nullptr),"Initialize PNG frame");check(frame->SetSize(d.Width,d.Height),"Set PNG dimensions");WICPixelFormatGUID format=GUID_WICPixelFormat32bppBGRA;check(frame->SetPixelFormat(&format),"Set PNG pixel format");check(frame->WritePixels(d.Height,mapped.RowPitch,mapped.RowPitch*d.Height,static_cast<BYTE*>(mapped.pData)),"Write PNG pixels");check(frame->Commit(),"Commit PNG frame");check(encoder->Commit(),"Commit PNG image");context_->Unmap(staging.Get(),0);}
    void update_frame(){FrameConstants frame{};float aspect=float(diagnostics_.width)/float((std::max)(diagnostics_.height,1u));XMMATRIX view=XMMatrixLookAtLH(XMVectorSet(0,0,parameters_.camera_z,1),XMVectorZero(),XMVectorSet(0,1,0,0));XMMATRIX projection=XMMatrixPerspectiveFovLH(radians(parameters_.camera_fov),aspect,.1f,100);XMStoreFloat4x4(&frame.view_projection,XMMatrixTranspose(view*projection));frame.camera_exposure={0,0,parameters_.camera_z,parameters_.exposure*parameters_.brightness*parameters_.lighting_intensity};frame.ambient={.18f,.3f,.46f,.24f};XMVECTOR direction=XMVector3Normalize(XMVectorSet(-1.8f,2.5f,4.7f,0));XMStoreFloat4(&frame.directional,direction);frame.directional.w=.48f;frame.directional_color={1,.96f,.9f,1};std::array<XMFLOAT4,4> positions{{{-2.4f,1.65f,2.8f,1},{2.35f,-1.5f,2.25f,1},{0,.4f,-3.2f,1},{2.6f,1.8f,2.2f,1}}};std::array<XMFLOAT4,4> colors{{color(0x38bdf8),color(0x2563eb),color(0xa855f7),color(0x38bdf8)}};std::array<float,4> intensities{{.22f,.17f,.11f,.08f}};for(std::size_t i=0;i<4;++i){frame.point_position[i]=positions[i];frame.point_color[i]=colors[i];frame.point_color[i].w=intensities[i];}context_->UpdateSubresource(frame_buffer_.Get(),0,nullptr,&frame,0,0);}
    void resize(UINT width,UINT height){context_->OMSetRenderTargets(0,nullptr,nullptr);target_.Reset();depth_view_.Reset();depth_texture_.Reset();check(swap_chain_->ResizeBuffers(0,width,height,DXGI_FORMAT_UNKNOWN,0),"Resize renderer swap chain");create_targets(width,height);diagnostics_.width=width;diagnostics_.height=height;RECT bounds{0,0,int(width),int(height)};if(!GetParent(window_)){DWORD style=static_cast<DWORD>(GetWindowLongPtrW(window_,GWL_STYLE));DWORD extended=static_cast<DWORD>(GetWindowLongPtrW(window_,GWL_EXSTYLE));AdjustWindowRectEx(&bounds,style,FALSE,extended);}SetWindowPos(window_,nullptr,0,0,bounds.right-bounds.left,bounds.bottom-bounds.top,SWP_NOMOVE|SWP_NOZORDER|SWP_NOACTIVATE);}
    void create_device(){ComPtr<IDXGIFactory6> factory;check(CreateDXGIFactory2(0,IID_PPV_ARGS(&factory)),"Create DXGI factory");ComPtr<IDXGIAdapter1> selected;if(!force_warp_)for(UINT index=0;;++index){ComPtr<IDXGIAdapter1> candidate;HRESULT result=factory->EnumAdapterByGpuPreference(index,DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE,IID_PPV_ARGS(&candidate));if(result==DXGI_ERROR_NOT_FOUND)break;check(result,"Enumerate DXGI adapter");DXGI_ADAPTER_DESC1 d{};check(candidate->GetDesc1(&d),"Read DXGI adapter description");if(!(d.Flags&DXGI_ADAPTER_FLAG_SOFTWARE)){selected=candidate;diagnostics_.adapter_name=d.Description;diagnostics_.vendor_id=d.VendorId;diagnostics_.device_id=d.DeviceId;break;}}const D3D_FEATURE_LEVEL levels[]={D3D_FEATURE_LEVEL_11_1,D3D_FEATURE_LEVEL_11_0,D3D_FEATURE_LEVEL_10_1,D3D_FEATURE_LEVEL_10_0};auto create=[&](IDXGIAdapter* adapter,D3D_DRIVER_TYPE driver){HRESULT r=D3D11CreateDevice(adapter,driver,nullptr,D3D11_CREATE_DEVICE_BGRA_SUPPORT,levels,ARRAYSIZE(levels),D3D11_SDK_VERSION,&device_,&diagnostics_.feature_level,&context_);if(r==E_INVALIDARG)r=D3D11CreateDevice(adapter,driver,nullptr,D3D11_CREATE_DEVICE_BGRA_SUPPORT,levels+1,ARRAYSIZE(levels)-1,D3D11_SDK_VERSION,&device_,&diagnostics_.feature_level,&context_);return r;};HRESULT result=selected?create(selected.Get(),D3D_DRIVER_TYPE_UNKNOWN):create(nullptr,D3D_DRIVER_TYPE_WARP);if(FAILED(result)&&selected){selected.Reset();device_.Reset();context_.Reset();result=create(nullptr,D3D_DRIVER_TYPE_WARP);}check(result,"Create Direct3D 11 device");diagnostics_.hardware=selected!=nullptr;if(!selected){diagnostics_.adapter_name=L"Microsoft WARP";diagnostics_.vendor_id=0x1414;diagnostics_.device_id=0x008c;}}
    void create_swap_chain(){ComPtr<IDXGIDevice> dxgi;check(device_.As(&dxgi),"Query DXGI device");ComPtr<IDXGIAdapter> adapter;check(dxgi->GetAdapter(&adapter),"Get DXGI adapter");ComPtr<IDXGIFactory2> factory;check(adapter->GetParent(IID_PPV_ARGS(&factory)),"Get DXGI factory");DXGI_SWAP_CHAIN_DESC1 d{};d.Width=kWidth;d.Height=kHeight;d.Format=DXGI_FORMAT_B8G8R8A8_UNORM;d.SampleDesc.Count=1;d.BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT;d.BufferCount=2;d.Scaling=DXGI_SCALING_STRETCH;d.SwapEffect=DXGI_SWAP_EFFECT_FLIP_SEQUENTIAL;d.AlphaMode=DXGI_ALPHA_MODE_PREMULTIPLIED;check(factory->CreateSwapChainForComposition(device_.Get(),&d,nullptr,&swap_chain_),"Create composition swap chain");create_targets(kWidth,kHeight);ComPtr<IDCompositionDevice> composition;check(DCompositionCreateDevice(dxgi.Get(),IID_PPV_ARGS(&composition)),"Create DirectComposition device");ComPtr<IDCompositionTarget> target;check(composition->CreateTargetForHwnd(window_,TRUE,&target),"Create composition target");ComPtr<IDCompositionVisual> visual;check(composition->CreateVisual(&visual),"Create composition visual");check(visual->SetContent(swap_chain_.Get()),"Attach swap chain to visual");check(target->SetRoot(visual.Get()),"Attach visual to window");check(composition->Commit(),"Commit composition tree");composition_=composition;composition_target_=target;composition_visual_=visual;}
    void create_targets(UINT width,UINT height){ComPtr<ID3D11Texture2D> buffer;check(swap_chain_->GetBuffer(0,IID_PPV_ARGS(&buffer)),"Get swap-chain buffer");check(device_->CreateRenderTargetView(buffer.Get(),nullptr,&target_),"Create render target");D3D11_TEXTURE2D_DESC d{};d.Width=width;d.Height=height;d.MipLevels=1;d.ArraySize=1;d.Format=DXGI_FORMAT_D24_UNORM_S8_UINT;d.SampleDesc.Count=1;d.BindFlags=D3D11_BIND_DEPTH_STENCIL;check(device_->CreateTexture2D(&d,nullptr,&depth_texture_),"Create depth texture");check(device_->CreateDepthStencilView(depth_texture_.Get(),nullptr,&depth_view_),"Create depth view");}
    void create_pipeline(){static constexpr char shader[]=R"(
cbuffer Frame:register(b0){float4x4 view_projection;float4 camera_exposure;float4 ambient;float4 directional;float4 directional_color;float4 point_position[4];float4 point_color[4];};
cbuffer Object:register(b1){float4x4 world;float4x4 normal_world;float4 base_color;float4 emissive;float4 surface;};
Texture2D identity_texture:register(t0);SamplerState identity_sampler:register(s0);
struct Input{float3 position:POSITION;float3 normal:NORMAL;float2 uv:TEXCOORD0;};struct Output{float4 position:SV_POSITION;float3 world_position:TEXCOORD0;float3 normal:TEXCOORD1;float2 uv:TEXCOORD2;};
Output vs_main(Input v){Output o;float4 p=mul(float4(v.position,1),world);o.position=mul(p,view_projection);o.world_position=p.xyz;o.normal=normalize(mul(v.normal,(float3x3)normal_world));o.uv=v.uv;return o;}
float3 aces(float3 v){return saturate((v*(2.51*v+.03))/(v*(2.43*v+.59)+.14));}
float4 ps_main(Output v):SV_TARGET{if(surface.w>.5){float4 t=identity_texture.Sample(identity_sampler,v.uv);clip(t.a-.015);float3 r=pow(saturate(t.rgb*camera_exposure.w),1.0/2.2);return float4(r*t.a,t.a);}if(surface.z>1.5){float a=saturate(base_color.a);float3 r=pow(aces((base_color.rgb+emissive.rgb*emissive.a)*camera_exposure.w),1.0/2.2);return float4(r*a,a);}float3 n=normalize(v.normal),view=normalize(camera_exposure.xyz-v.world_position);float3 light=ambient.rgb*ambient.a;float3 ld=normalize(directional.xyz);float diff=saturate(dot(n,ld));float spec=pow(saturate(dot(n,normalize(ld+view))),lerp(96.0,8.0,surface.x));light+=directional_color.rgb*directional.w*(diff+spec*lerp(.15,.8,surface.y));[unroll]for(int i=0;i<4;++i){float3 delta=point_position[i].xyz-v.world_position;float ds=max(dot(delta,delta),.01);float3 d=normalize(delta);float pd=saturate(dot(n,d));float ps=pow(saturate(dot(n,normalize(d+view))),lerp(112.0,10.0,surface.x));light+=point_color[i].rgb*point_color[i].w/(1+ds*.18)*(pd+ps*lerp(.12,.72,surface.y));}float fresnel=pow(1-saturate(dot(n,view)),5);float3 lit=base_color.rgb*light+emissive.rgb*emissive.a;if(surface.z>.5)lit=lerp(lit*.28,base_color.rgb+light*.18,.35+fresnel*.65);float3 r=pow(aces(lit*camera_exposure.w),1.0/2.2);float a=saturate(base_color.a);return float4(r*a,a);})";ComPtr<ID3DBlob> vs,ps,errors;check(D3DCompile(shader,sizeof(shader),"oes_eyeball_3d.hlsl",nullptr,nullptr,"vs_main","vs_4_0",D3DCOMPILE_ENABLE_STRICTNESS,0,&vs,&errors),"Compile 3D vertex shader");check(D3DCompile(shader,sizeof(shader),"oes_eyeball_3d.hlsl",nullptr,nullptr,"ps_main","ps_4_0",D3DCOMPILE_ENABLE_STRICTNESS,0,&ps,&errors),"Compile 3D pixel shader");check(device_->CreateVertexShader(vs->GetBufferPointer(),vs->GetBufferSize(),nullptr,&vertex_shader_),"Create 3D vertex shader");check(device_->CreatePixelShader(ps->GetBufferPointer(),ps->GetBufferSize(),nullptr,&pixel_shader_),"Create 3D pixel shader");D3D11_INPUT_ELEMENT_DESC elements[]={{"POSITION",0,DXGI_FORMAT_R32G32B32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0},{"NORMAL",0,DXGI_FORMAT_R32G32B32_FLOAT,0,12,D3D11_INPUT_PER_VERTEX_DATA,0},{"TEXCOORD",0,DXGI_FORMAT_R32G32_FLOAT,0,24,D3D11_INPUT_PER_VERTEX_DATA,0}};check(device_->CreateInputLayout(elements,ARRAYSIZE(elements),vs->GetBufferPointer(),vs->GetBufferSize(),&input_layout_),"Create 3D input layout");D3D11_BUFFER_DESC fd{};fd.ByteWidth=sizeof(FrameConstants);fd.Usage=D3D11_USAGE_DEFAULT;fd.BindFlags=D3D11_BIND_CONSTANT_BUFFER;check(device_->CreateBuffer(&fd,nullptr,&frame_buffer_),"Create frame buffer");fd.ByteWidth=sizeof(ObjectConstants);check(device_->CreateBuffer(&fd,nullptr,&object_buffer_),"Create object buffer");}
    void create_states(){D3D11_RASTERIZER_DESC r{};r.FillMode=D3D11_FILL_SOLID;r.CullMode=D3D11_CULL_BACK;r.DepthClipEnable=TRUE;check(device_->CreateRasterizerState(&r,&raster_),"Create rasterizer state");D3D11_DEPTH_STENCIL_DESC d{};d.DepthEnable=TRUE;d.DepthFunc=D3D11_COMPARISON_LESS_EQUAL;d.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ALL;check(device_->CreateDepthStencilState(&d,&depth_write_state_),"Create depth-write state");d.DepthWriteMask=D3D11_DEPTH_WRITE_MASK_ZERO;check(device_->CreateDepthStencilState(&d,&depth_read_state_),"Create depth-read state");D3D11_BLEND_DESC b{};b.RenderTarget[0].RenderTargetWriteMask=D3D11_COLOR_WRITE_ENABLE_ALL;check(device_->CreateBlendState(&b,&opaque_blend_),"Create opaque blend state");b.RenderTarget[0].BlendEnable=TRUE;b.RenderTarget[0].SrcBlend=D3D11_BLEND_ONE;b.RenderTarget[0].DestBlend=D3D11_BLEND_INV_SRC_ALPHA;b.RenderTarget[0].BlendOp=D3D11_BLEND_OP_ADD;b.RenderTarget[0].SrcBlendAlpha=D3D11_BLEND_ONE;b.RenderTarget[0].DestBlendAlpha=D3D11_BLEND_INV_SRC_ALPHA;b.RenderTarget[0].BlendOpAlpha=D3D11_BLEND_OP_ADD;check(device_->CreateBlendState(&b,&alpha_blend_),"Create alpha blend state");b.RenderTarget[0].DestBlend=D3D11_BLEND_ONE;b.RenderTarget[0].DestBlendAlpha=D3D11_BLEND_ONE;check(device_->CreateBlendState(&b,&additive_blend_),"Create additive blend state");D3D11_SAMPLER_DESC s{};s.Filter=D3D11_FILTER_MIN_MAG_MIP_LINEAR;s.AddressU=s.AddressV=s.AddressW=D3D11_TEXTURE_ADDRESS_CLAMP;s.MaxLOD=D3D11_FLOAT32_MAX;check(device_->CreateSamplerState(&s,&sampler_),"Create identity sampler");}
    void create_texture(const std::filesystem::path& path){ComPtr<IWICImagingFactory> factory;check(CoCreateInstance(CLSID_WICImagingFactory2,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&factory)),"Create WIC factory");ComPtr<IWICBitmapDecoder> decoder;check(factory->CreateDecoderFromFilename(path.c_str(),nullptr,GENERIC_READ,WICDecodeMetadataCacheOnLoad,&decoder),"Open OES identity texture");ComPtr<IWICBitmapFrameDecode> frame;check(decoder->GetFrame(0,&frame),"Decode OES identity texture");UINT width=0,height=0;check(frame->GetSize(&width,&height),"Read identity dimensions");ComPtr<IWICFormatConverter> converter;check(factory->CreateFormatConverter(&converter),"Create WIC converter");check(converter->Initialize(frame.Get(),GUID_WICPixelFormat32bppRGBA,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeCustom),"Convert identity texture");std::vector<std::uint8_t> pixels(std::size_t(width)*height*4);check(converter->CopyPixels(nullptr,width*4,static_cast<UINT>(pixels.size()),pixels.data()),"Copy identity texture pixels");D3D11_TEXTURE2D_DESC d{};d.Width=width;d.Height=height;d.MipLevels=1;d.ArraySize=1;d.Format=DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;d.SampleDesc.Count=1;d.Usage=D3D11_USAGE_IMMUTABLE;d.BindFlags=D3D11_BIND_SHADER_RESOURCE;D3D11_SUBRESOURCE_DATA data{pixels.data(),width*4,0};ComPtr<ID3D11Texture2D> texture;check(device_->CreateTexture2D(&d,&data,&texture),"Create identity texture");check(device_->CreateShaderResourceView(texture.Get(),nullptr,&texture_view_),"Create identity view");}
    HWND window_{};bool force_warp_{};oes::character::AnimationController animation_;oes::character::View view_;std::filesystem::path screenshot_path_;bool screenshot_written_{};Diagnostics diagnostics_{};RendererParameters parameters_{};ComPtr<ID3D11Device> device_;ComPtr<ID3D11DeviceContext> context_;ComPtr<IDXGISwapChain1> swap_chain_;ComPtr<ID3D11RenderTargetView> target_;ComPtr<ID3D11Texture2D> depth_texture_;ComPtr<ID3D11DepthStencilView> depth_view_;ComPtr<ID3D11VertexShader> vertex_shader_;ComPtr<ID3D11PixelShader> pixel_shader_;ComPtr<ID3D11InputLayout> input_layout_;ComPtr<ID3D11Buffer> frame_buffer_,object_buffer_;ComPtr<ID3D11SamplerState> sampler_;ComPtr<ID3D11ShaderResourceView> texture_view_;ComPtr<ID3D11RasterizerState> raster_;ComPtr<ID3D11DepthStencilState> depth_write_state_,depth_read_state_;ComPtr<ID3D11BlendState> opaque_blend_,alpha_blend_,additive_blend_;ComPtr<IDCompositionDevice> composition_;ComPtr<IDCompositionTarget> composition_target_;ComPtr<IDCompositionVisual> composition_visual_;Mesh outer_,inner_,energy_,glass_,rim_,housing_ring_,housing_rib_,blade_,iris_,iris_ring_,pupil_,pupil_glow_,logo_,orbit_outer_,orbit_middle_,orbit_inner_,particles_;std::array<Mesh,5> nodes_{};
};

void write_diagnostics(const std::filesystem::path& path,const Diagnostics& value,const std::string& status,const std::string& error={}){if(path.empty())return;std::error_code ignored;std::filesystem::create_directories(path.parent_path(),ignored);std::ofstream out(path,std::ios::trunc);const auto&p=value.parameters;out<<"{\n  \"status\": \""<<status<<"\",\n  \"renderer_mode\": \"native_character_animated\",\n  \"component_count\": 26,\n  \"particle_count\": 110,\n  \"theme\": \"default\",\n  \"adapter_name\": \""<<json_escape(value.adapter_name)<<"\",\n  \"vendor_id\": \"0x"<<std::hex<<std::setw(4)<<std::setfill('0')<<value.vendor_id<<"\",\n  \"device_id\": \"0x"<<std::setw(4)<<value.device_id<<"\",\n"<<std::dec<<"  \"feature_level\": \""<<feature_level_name(value.feature_level)<<"\",\n  \"device_type\": \""<<(value.hardware?"hardware":"warp")<<"\",\n  \"initialization_ms\": "<<value.initialization_ms<<",\n  \"first_frame_ms\": "<<value.first_frame_ms<<",\n  \"working_set_bytes\": "<<value.working_set_bytes<<",\n  \"fps\": "<<value.fps<<",\n  \"width\": "<<value.width<<",\n  \"height\": "<<value.height<<",\n  \"parameters\": {\n";
    out<<"    \"scale\": "<<p.scale<<", \"x\": "<<p.x<<", \"y\": "<<p.y<<", \"z\": "<<p.z<<",\n    \"rotation_x\": "<<p.rotation_x<<", \"rotation_y\": "<<p.rotation_y<<", \"rotation_z\": "<<p.rotation_z<<",\n    \"brightness\": "<<p.brightness<<", \"exposure\": "<<p.exposure<<", \"lighting_intensity\": "<<p.lighting_intensity<<",\n    \"camera_fov\": "<<p.camera_fov<<", \"camera_z\": "<<p.camera_z<<",\n    \"iris_scale\": "<<p.iris_scale<<", \"iris_depth\": "<<p.iris_depth<<", \"pupil_scale\": "<<p.pupil_scale<<", \"pupil_depth\": "<<p.pupil_depth<<",\n    \"glass_intensity\": "<<p.glass_intensity<<", \"rim_intensity\": "<<p.rim_intensity<<", \"orbit_intensity\": "<<p.orbit_intensity<<", \"particle_intensity\": "<<p.particle_intensity<<",\n    \"logo_scale\": "<<p.logo_scale<<", \"logo_depth\": "<<p.logo_depth<<", \"width\": "<<p.width<<", \"height\": "<<p.height<<"\n  },\n  \"error\": \"";for(char c:error){if(c=='"'||c=='\\')out<<'\\';out<<c;}out<<"\"\n}\n";}
LRESULT CALLBACK window_procedure(HWND window,UINT message,WPARAM wparam,LPARAM lparam){if(message==WM_KEYDOWN&&wparam==VK_ESCAPE&&!GetParent(window)){DestroyWindow(window);return 0;}if(message==WM_CLOSE){DestroyWindow(window);return 0;}if(message==WM_DESTROY){PostQuitMessage(0);return 0;}return DefWindowProcW(window,message,wparam,lparam);}
} // namespace

int WINAPI wWinMain(HINSTANCE instance,HINSTANCE,PWSTR,int){auto process_started=Clock::now();auto directory=executable_directory();auto texture=argument_path(L"--asset",directory/L"assets"/L"oes-logo.png");auto local=local_renderer_directory();auto control=argument_path(L"--control",local/L"renderer-tuning.json");auto diagnostics_path=argument_path(L"--diagnostics",local/L"renderer-diagnostics.json");Diagnostics diagnostics;try{check(CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED),"Initialize COM");WNDCLASSEXW wc{sizeof(wc)};wc.hInstance=instance;wc.lpfnWndProc=window_procedure;wc.lpszClassName=kWindowClass;wc.hCursor=LoadCursor(nullptr,IDC_ARROW);check(RegisterClassExW(&wc)?S_OK:HRESULT_FROM_WIN32(GetLastError()),"Register renderer window");constexpr DWORD style=WS_OVERLAPPEDWINDOW;constexpr DWORD extended=WS_EX_APPWINDOW|WS_EX_NOREDIRECTIONBITMAP;RECT bounds{0,0,int(kWidth),int(kHeight)};check(AdjustWindowRectEx(&bounds,style,FALSE,extended)?S_OK:HRESULT_FROM_WIN32(GetLastError()),"Size renderer window");HWND window=CreateWindowExW(extended,kWindowClass,L"OES Eyeball Native 3D",style,CW_USEDEFAULT,CW_USEDEFAULT,bounds.right-bounds.left,bounds.bottom-bounds.top,nullptr,nullptr,instance,nullptr);if(!window)check(HRESULT_FROM_WIN32(GetLastError()),"Create renderer window");Renderer renderer(window,has_argument(L"--force-warp"));renderer.initialize(texture);RendererParameters parameters;renderer.apply_parameters(read_parameters(control,parameters)?parameters:RendererParameters{});ShowWindow(window,SW_SHOW);renderer.render(process_started,true);diagnostics=renderer.diagnostics();write_diagnostics(diagnostics_path,diagnostics,"ready");MSG message{};auto diagnostics_started=Clock::now(),control_checked=Clock::now();auto elapsed=[](const Clock::time_point&s){return std::chrono::duration<double,std::milli>(Clock::now()-s).count();};std::uint64_t frames=1;bool running=true;while(running){while(PeekMessageW(&message,nullptr,0,0,PM_REMOVE)){if(message.message==WM_QUIT){running=false;break;}TranslateMessage(&message);DispatchMessageW(&message);}if(!running)break;if(elapsed(control_checked)>=50){RendererParameters updated;if(read_parameters(control,updated))renderer.apply_parameters(updated);control_checked=Clock::now();}renderer.render(process_started);++frames;double interval=elapsed(diagnostics_started);if(interval>=1000){renderer.set_fps(double(frames)*1000/interval);diagnostics=renderer.diagnostics();write_diagnostics(diagnostics_path,diagnostics,"ready");frames=0;diagnostics_started=Clock::now();}}CoUninitialize();return 0;}catch(const std::exception& error){write_diagnostics(diagnostics_path,diagnostics,"failed",error.what());return 1;}}
