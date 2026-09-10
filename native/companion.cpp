// Standalone Windows Graphics Capture companion. No injection or game writes.
#include "curve_network.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <d3d11.h>
#include <d3dcompiler.h>
#include <dcomp.h>
#include <dwmapi.h>
#include <dxgi1_6.h>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <windows.graphics.capture.interop.h>
#include <windows.graphics.directx.direct3d11.interop.h>
#include <windows.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Graphics.Capture.h>
#include <winrt/Windows.Graphics.DirectX.Direct3D11.h>
#include <winrt/Windows.Graphics.DirectX.h>
#include <wrl/client.h>
using Microsoft::WRL::ComPtr;
using namespace winrt;
using namespace winrt::Windows::Graphics::Capture;
using namespace winrt::Windows::Graphics::DirectX;
using namespace winrt::Windows::Graphics::DirectX::Direct3D11;
namespace fs = std::filesystem;
void check(HRESULT hr) { winrt::check_hresult(hr); }
double now_ms() {
  static double f = [] {
    LARGE_INTEGER x;
    QueryPerformanceFrequency(&x);
    return double(x.QuadPart);
  }();
  LARGE_INTEGER n;
  QueryPerformanceCounter(&n);
  return n.QuadPart * 1000.0 / f;
}
struct Options {
  DWORD pid = 0;
  double seconds = 0, snapshot = 0;
  int mode = 0;
  bool overlay = false, layered = false, statistics = false, statistics_flush = false;
  float strength = .35f;
  fs::path model;
  fs::path out = "runs/companion";
};
Options args(int argc, char **argv) {
  Options o;
  for (int i = 1; i < argc; i++) {
    std::string a = argv[i];
    auto value = [&]() {
      if (++i >= argc)
        throw std::runtime_error("Missing value for " + a);
      return std::string(argv[i]);
    };
    if (a == "--layered-blt")
      o.layered = true;
    else if (a == "--frame-statistics")
      o.statistics = true;
    else if (a == "--frame-statistics-flush")
      o.statistics = o.statistics_flush = true;
    else if (a == "--pid")
      o.pid = std::stoul(value());
    else if (a == "--seconds")
      o.seconds = std::stod(value());
    else if (a == "--out")
      o.out = fs::u8path(value());
    else if (a == "--overlay")
      o.overlay = true;
    else if (a == "--model")
      o.model = fs::u8path(value());
    else if (a == "--strength")
      o.strength = std::stof(value());
    else if (a == "--snapshot-after")
      o.snapshot = std::stod(value());
    else if (a == "--mode") {
      auto v = value();
      if (v == "identity")
        o.mode = 0;
      else if (v == "invert")
        o.mode = 1;
      else if (v == "basic")
        o.mode = 2;
      else if (v == "neural")
        o.mode = 3;
      else if (v == "neural-raw")
        o.mode = 4;
      else
        throw std::runtime_error("Unknown mode");
    } else
      throw std::runtime_error(
          "Usage: enr_companion --pid GAME_PID --out NEW_DIRECTORY [--overlay] "
          "[--mode identity|invert|basic|neural|neural-raw] "
          "[--model weights.bin] [--strength .35] [--seconds 30] "
          "[--snapshot-after 5] [--frame-statistics | --frame-statistics-flush]");
  }
  if (!std::isfinite(o.strength) || o.strength < 0 || o.strength > 1)
    throw std::runtime_error("Strength must be 0..1");
  if (o.mode >= 3 && o.model.empty())
    throw std::runtime_error("Neural mode requires --model weights.bin");
  if (!o.pid)
    throw std::runtime_error("--pid is required");
  return o;
}
struct Find {
  DWORD pid;
  HWND hwnd = nullptr;
};
BOOL CALLBACK find_window(HWND w, LPARAM p) {
  auto &f = *reinterpret_cast<Find *>(p);
  DWORD pid = 0;
  GetWindowThreadProcessId(w, &pid);
  if (pid == f.pid && IsWindowVisible(w) && !GetWindow(w, GW_OWNER)) {
    RECT r;
    GetClientRect(w, &r);
    if (r.right > 320 && r.bottom > 200) {
      f.hwnd = w;
      return FALSE;
    }
  }
  return TRUE;
}
bool bypass = false, running = true;
int selected_mode = 0, enhancement_mode = 2;
HWND source_window = nullptr;
LRESULT CALLBACK proc(HWND w, UINT msg, WPARAM wp, LPARAM lp) {
  if (source_window && msg == WM_MOUSEACTIVATE)
    return MA_NOACTIVATE;
  if (msg == WM_NCHITTEST &&
      (GetWindowLongPtr(w, GWL_EXSTYLE) & WS_EX_NOACTIVATE))
    return HTTRANSPARENT;
  if (msg == WM_HOTKEY) {
    if (wp == 8)
      bypass = !bypass;
    if (wp == 9)
      selected_mode = selected_mode ? 0 : enhancement_mode;
    if (wp == 10)
      running = false;
    return 0;
  }
  if (msg == WM_CLOSE || msg == WM_DESTROY) {
    running = false;
    return 0;
  }
  return DefWindowProc(w, msg, wp, lp);
}
const char *shader = R"(
Texture2D<float4> source : register(t0);
Texture2D<float4> curve : register(t1);
SamplerState linearSampler : register(s0);
cbuffer Params : register(b0) { uint mode; float strength; float2 size; };
struct Vertex {float4 pos:SV_Position;float2 uv:TEXCOORD0;};
Vertex vs(uint id:SV_VertexID){Vertex o;o.uv=float2((id<<1)&2,id&2);o.pos=float4(o.uv*float2(2,-2)+float2(-1,1),0,1);return o;}
float4 ps(Vertex i):SV_Target {float4 c=source.SampleLevel(linearSampler,i.uv,0);if(mode==1)return float4(1-c.rgb,c.a);if(mode>=3){
 float3 r=curve.SampleLevel(linearSampler,i.uv,0).rgb;
 if(any(isnan(r))||any(isinf(r))||any(abs(r)>1))return c;
 float3 full=c.rgb;[unroll]for(uint k=0;k<8;k++)full+=r*(full*full-full);
 if(mode==4)return float4(saturate(full),c.a);
 float l=dot(c.rgb,float3(.2126,.7152,.0722));
 float target=dot(full,float3(.2126,.7152,.0722));
 float gain=clamp(target/max(l,.001),.85,1.4);
 float maxc=max(c.r,max(c.g,c.b));
 float deltaGain=clamp((gain-1)*strength,-.06/max(maxc,.001),.06/max(maxc,.001));
 // Keep positive common gain below a new RGB8 endpoint, including saturated colors.
 deltaGain=min(deltaGain,max(0,(254.0/255.0-maxc)/max(maxc,.001)));
 float protect=smoothstep(.03,.1,l)*(1-smoothstep(.70,.9,l));
 protect*=smoothstep(.045,.10,i.uv.y)*(1-smoothstep(.84,.91,i.uv.y));
 float crosshair=max(abs(i.uv.x-.5)/.018,abs(i.uv.y-.5)/.025);protect*=smoothstep(1,2,crosshair);
 return float4(saturate(c.rgb*(1+deltaGain*protect)),c.a);
 }if(mode==2){float l=dot(c.rgb,float3(.2126,.7152,.0722));float protect=smoothstep(.035,.12,l)*(1-smoothstep(.7,.95,l));float3 lifted=c.rgb+0.055*c.rgb*(1-c.rgb)*protect;return float4(saturate(lifted),c.a);}return c;}
)";
ComPtr<ID3DBlob> compile(const char *entry, const char *target) {
  ComPtr<ID3DBlob> b, e;
  auto hr =
      D3DCompile(shader, strlen(shader), "companion", nullptr, nullptr, entry,
                 target, D3DCOMPILE_OPTIMIZATION_LEVEL3, 0, &b, &e);
  if (FAILED(hr) && e)
    std::cerr << static_cast<char *>(e->GetBufferPointer());
  check(hr);
  return b;
}
struct Timing {
  ComPtr<ID3D11Query> disjoint, start, end;
  bool pending = false;
  uint64_t frame = 0;
  double captured = 0, received = 0, present = 0, returned = 0, interval = 0;
  int mode = 0, dropped = 0;
};
void bmp(ID3D11Device *device, ID3D11DeviceContext *ctx,
         ID3D11Texture2D *texture, const fs::path &path) {
  D3D11_TEXTURE2D_DESC d;
  texture->GetDesc(&d);
  d.Usage = D3D11_USAGE_STAGING;
  d.BindFlags = 0;
  d.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
  d.MiscFlags = 0;
  ComPtr<ID3D11Texture2D> s;
  check(device->CreateTexture2D(&d, nullptr, &s));
  ctx->CopyResource(s.Get(), texture);
  D3D11_MAPPED_SUBRESOURCE m;
  check(ctx->Map(s.Get(), 0, D3D11_MAP_READ, 0, &m));
  BITMAPFILEHEADER fh{};
  BITMAPINFOHEADER ih{};
  fh.bfType = 0x4d42;
  fh.bfOffBits = sizeof(fh) + sizeof(ih);
  fh.bfSize = fh.bfOffBits + d.Width * d.Height * 4;
  ih.biSize = sizeof(ih);
  ih.biWidth = d.Width;
  ih.biHeight = -LONG(d.Height);
  ih.biPlanes = 1;
  ih.biBitCount = 32;
  ih.biCompression = BI_RGB;
  std::ofstream f(path, std::ios::binary);
  f.write(reinterpret_cast<char *>(&fh), sizeof(fh));
  f.write(reinterpret_cast<char *>(&ih), sizeof(ih));
  for (UINT y = 0; y < d.Height; y++)
    f.write(static_cast<char *>(m.pData) + y * m.RowPitch, d.Width * 4);
  ctx->Unmap(s.Get(), 0);
  if (!f)
    throw std::runtime_error("Snapshot write failed");
}
int main(int argc, char **argv) try {
  auto o = args(argc, argv);
  selected_mode = o.mode;
  enhancement_mode = o.model.empty() ? 2 : 3;
  winrt::init_apartment(winrt::apartment_type::multi_threaded);
  SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
  if (fs::exists(o.out))
    throw std::runtime_error(
        "Choose a new output directory to retain earlier runs");
  fs::create_directories(o.out);
  std::ofstream log(o.out / "events.log"), csv(o.out / "frames.csv");
  std::ofstream stats;
  LARGE_INTEGER qpc_frequency;
  QueryPerformanceFrequency(&qpc_frequency);
  if (o.statistics) {
    stats.open(o.out / "display-statistics.csv");
    stats << "frame,capture_qpc_ms,present_call_qpc_ms,present_return_qpc_ms,"
             "last_present_hresult,last_present_count,query_start_qpc_ms,"
             "query_end_qpc_ms,flush_hresult,statistics_hresult,display_present_count,"
             "present_refresh_count,sync_refresh_count,sync_qpc_ticks,sync_qpc_ms\n"
          << std::fixed << std::setprecision(6);
    if (!stats)
      throw std::runtime_error("Cannot open frame statistics log");
  }
  log << std::unitbuf;
  csv << "frame,capture_qpc_ms,receive_qpc_ms,present_call_qpc_ms,present_"
         "return_qpc_ms,capture_to_present_call_ms,present_interval_ms,gpu_"
         "copy_draw_ms,mode,dropped_before\n"
      << std::fixed << std::setprecision(6);
  Find f{o.pid};
  EnumWindows(find_window, reinterpret_cast<LPARAM>(&f));
  if (!f.hwnd)
    throw std::runtime_error("No visible game window for PID");
  if (o.overlay)
    source_window = f.hwnd;
  ComPtr<IDXGIFactory6> factory;
  check(CreateDXGIFactory1(IID_PPV_ARGS(&factory)));
  ComPtr<IDXGIAdapter1> adapter;
  for (UINT i = 0; factory->EnumAdapterByGpuPreference(
                       i, DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE,
                       IID_PPV_ARGS(&adapter)) != DXGI_ERROR_NOT_FOUND;
       i++) {
    DXGI_ADAPTER_DESC1 d;
    adapter->GetDesc1(&d);
    if (!(d.Flags & DXGI_ADAPTER_FLAG_SOFTWARE))
      break;
    adapter.Reset();
  }
  if (!adapter)
    throw std::runtime_error("No hardware GPU");
  DXGI_ADAPTER_DESC1 ad;
  adapter->GetDesc1(&ad);
  ComPtr<ID3D11Device> device;
  ComPtr<ID3D11DeviceContext> ctx;
  D3D_FEATURE_LEVEL fl;
  check(D3D11CreateDevice(adapter.Get(), D3D_DRIVER_TYPE_UNKNOWN, nullptr,
                          D3D11_CREATE_DEVICE_BGRA_SUPPORT, nullptr, 0,
                          D3D11_SDK_VERSION, &device, &fl, &ctx));
  std::unique_ptr<CurveNetwork> network;
  if (!o.model.empty())
    network = std::make_unique<CurveNetwork>(device.Get(), ctx.Get(), o.model);
  auto interop = winrt::get_activation_factory<GraphicsCaptureItem,
                                               IGraphicsCaptureItemInterop>();
  GraphicsCaptureItem item{nullptr};
  check(interop->CreateForWindow(f.hwnd, winrt::guid_of<GraphicsCaptureItem>(),
                                 winrt::put_abi(item)));
  ComPtr<IDXGIDevice> dxgi;
  check(device.As(&dxgi));
  winrt::com_ptr<IInspectable> inspect;
  check(CreateDirect3D11DeviceFromDXGIDevice(dxgi.Get(), inspect.put()));
  auto capture_device = inspect.as<IDirect3DDevice>();
  auto size = item.Size();
  WNDCLASS wc{};
  wc.lpfnWndProc = proc;
  wc.hInstance = GetModuleHandle(nullptr);
  wc.lpszClassName = L"EnfusionNeuralCompanion";
  RegisterClass(&wc);
  DWORD ex = o.overlay ? (WS_EX_NOACTIVATE | WS_EX_TRANSPARENT |
                          WS_EX_TOOLWINDOW | (o.layered ? WS_EX_LAYERED : 0))
                       : 0;
  HWND window = CreateWindowEx(
      ex, wc.lpszClassName,
      L"Enfusion Neural Companion - F8 bypass / F9 mode / F10 exit",
      o.overlay ? WS_POPUP : WS_OVERLAPPEDWINDOW, 20, 20, size.Width,
      size.Height, nullptr, nullptr, wc.hInstance, nullptr);
  if (!window)
    check(HRESULT_FROM_WIN32(GetLastError()));
  if (o.overlay)
    EnableWindow(window, FALSE);
  if (o.layered) {
    check(SetLayeredWindowAttributes(window, 0, 255, LWA_ALPHA)
              ? S_OK
              : HRESULT_FROM_WIN32(GetLastError()));
    MARGINS margins{-1, -1, -1, -1};
    check(DwmExtendFrameIntoClientArea(window, &margins));
  }
  for (int k : {8, 9, 10})
    if (!RegisterHotKey(window, k, MOD_NOREPEAT, VK_F1 + k - 1))
      throw std::runtime_error("F8/F9/F10 hotkey registration failed");
  DXGI_SWAP_CHAIN_DESC1 sd{};
  sd.Width = size.Width;
  sd.Height = size.Height;
  sd.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
  sd.SampleDesc.Count = 1;
  sd.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
  sd.BufferCount = 2;
  sd.SwapEffect =
      o.layered ? DXGI_SWAP_EFFECT_DISCARD : DXGI_SWAP_EFFECT_FLIP_DISCARD;
  sd.AlphaMode = DXGI_ALPHA_MODE_IGNORE;
  sd.Flags = o.layered ? 0 : DXGI_SWAP_CHAIN_FLAG_FRAME_LATENCY_WAITABLE_OBJECT;
  ComPtr<IDXGISwapChain1> swap;
  check(factory->CreateSwapChainForHwnd(device.Get(), window, &sd, nullptr,
                                        nullptr, &swap));
  check(factory->MakeWindowAssociation(window, DXGI_MWA_NO_ALT_ENTER));
  ComPtr<IDXGISwapChain2> swap2;
  check(swap.As(&swap2));
  HANDLE latency = nullptr;
  if (!o.layered) {
    check(swap2->SetMaximumFrameLatency(1));
    latency = swap2->GetFrameLatencyWaitableObject();
  }
  ComPtr<ID3D11Texture2D> back, src;
  ComPtr<ID3D11RenderTargetView> rtv;
  ComPtr<ID3D11ShaderResourceView> srv;
  auto resources = [&]() {
    check(swap->GetBuffer(0, IID_PPV_ARGS(&back)));
    check(device->CreateRenderTargetView(back.Get(), nullptr, &rtv));
    D3D11_TEXTURE2D_DESC d{};
    d.Width = size.Width;
    d.Height = size.Height;
    d.MipLevels = 1;
    d.ArraySize = 1;
    d.Format = sd.Format;
    d.SampleDesc.Count = 1;
    d.Usage = D3D11_USAGE_DEFAULT;
    d.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    check(device->CreateTexture2D(&d, nullptr, &src));
    check(device->CreateShaderResourceView(src.Get(), nullptr, &srv));
  };
  resources();
  auto vb = compile("vs", "vs_5_0"), pb = compile("ps", "ps_5_0");
  ComPtr<ID3D11VertexShader> vs;
  ComPtr<ID3D11PixelShader> ps;
  check(device->CreateVertexShader(vb->GetBufferPointer(), vb->GetBufferSize(),
                                   nullptr, &vs));
  check(device->CreatePixelShader(pb->GetBufferPointer(), pb->GetBufferSize(),
                                  nullptr, &ps));
  D3D11_SAMPLER_DESC sm{};
  sm.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
  sm.AddressU = sm.AddressV = sm.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
  sm.MaxLOD = D3D11_FLOAT32_MAX;
  ComPtr<ID3D11SamplerState> sampler;
  check(device->CreateSamplerState(&sm, &sampler));
  D3D11_BUFFER_DESC bd{};
  bd.ByteWidth = 16;
  bd.Usage = D3D11_USAGE_DEFAULT;
  bd.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
  ComPtr<ID3D11Buffer> cb;
  check(device->CreateBuffer(&bd, nullptr, &cb));
  std::array<Timing, 16> samples;
  for (auto &t : samples) {
    D3D11_QUERY_DESC q{D3D11_QUERY_TIMESTAMP_DISJOINT, 0};
    check(device->CreateQuery(&q, &t.disjoint));
    q.Query = D3D11_QUERY_TIMESTAMP;
    check(device->CreateQuery(&q, &t.start));
    check(device->CreateQuery(&q, &t.end));
  }
  auto finish = [&](Timing &t, bool wait) {
    if (!t.pending)
      return;
    D3D11_QUERY_DATA_TIMESTAMP_DISJOINT d{};
    UINT64 a = 0, b = 0;
    HRESULT hr;
    double deadline = now_ms() + 2000;
    while ((hr = ctx->GetData(t.disjoint.Get(), &d, sizeof(d),
                              wait ? 0 : D3D11_ASYNC_GETDATA_DONOTFLUSH)) ==
               S_FALSE &&
           wait && now_ms() < deadline)
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
    double gpu = -1;
    if (hr == S_OK && !d.Disjoint &&
        ctx->GetData(t.start.Get(), &a, sizeof(a), 0) == S_OK &&
        ctx->GetData(t.end.Get(), &b, sizeof(b), 0) == S_OK)
      gpu = (b - a) * 1000.0 / d.Frequency;
    csv << t.frame << ',' << t.captured << ',' << t.received << ',' << t.present
        << ',' << t.returned << ',' << t.present - t.captured << ','
        << t.interval << ',' << gpu << ',' << t.mode << ',' << t.dropped
        << '\n';
    t.pending = false;
  };
  auto pool = Direct3D11CaptureFramePool::CreateFreeThreaded(
      capture_device, DirectXPixelFormat::B8G8R8A8UIntNormalized, 2, size);
  auto session = pool.CreateCaptureSession(item);
  session.IsCursorCaptureEnabled(false);
  session.StartCapture();
  std::ofstream manifest(o.out / "run.json");
  manifest
      << "{\n  \"schema_version\": 1,\n  \"source_pid\": " << o.pid
      << ",\n  \"adapter\": \"" << winrt::to_string(ad.Description)
      << "\",\n  \"width\": " << size.Width << ", \"height\": " << size.Height
      << ",\n  \"overlay\": " << (o.overlay ? "true" : "false")
      << ",\n  \"initial_mode\": " << o.mode
      << ",\n  \"frame_statistics\": " << (o.statistics ? "true" : "false")
      << ",\n  \"frame_statistics_dwm_flush\": " << (o.statistics_flush ? "true" : "false")
      << ",\n  \"qpc_frequency_hz\": " << qpc_frequency.QuadPart
      << ",\n  \"strength\": " << o.strength << ",\n  \"presentation\": \""
      << (o.layered ? "layered-bitblt-probe" : "hwnd-flip-discard") << "\""
      << ",\n  \"precision\": \"FP32\",\n  \"curve_dimensions\": [320, 180]"
      << ",\n  \"capture\": \"Windows Graphics Capture HWND BGRA8 SDR "
         "including HUD\",\n  \"latency_scope\": \"capture compositor QPC "
         "to companion Present call; excludes input and scanout\",\n  "
         "\"gpu_scope\": \"source GPU copy, optional neural inference and "
         "pixel draw; no CPU frame readback except requested "
         "snapshots\",\n  \"neural\": "
      << (network ? "true" : "false") << "\n}\n";
  manifest.close();
  log << "started " << std::setprecision(15) << now_ms() << "\n";
  std::cout << "Capture started on " << winrt::to_string(ad.Description)
            << " at " << size.Width << 'x' << size.Height
            << ". F8 bypass; F9 identity/enhancement; F10 quit.\n"
            << std::flush;
  double began = now_ms(), last_frame = began, last_present = 0,
         last_source = 0;
  uint64_t count = 0;
  bool shown = false, snapshot_done = false, old_bypass = false;
  while (running && IsWindow(f.hwnd) &&
         (o.seconds <= 0 || now_ms() - began < o.seconds * 1000)) {
    MSG msg;
    while (PeekMessage(&msg, nullptr, 0, 0, PM_REMOVE)) {
      TranslateMessage(&msg);
      DispatchMessage(&msg);
    }
    if (!running)
      break;
    if (bypass != old_bypass) {
      log << "bypass " << bypass << ' ' << now_ms() << '\n';
      log.flush();
      old_bypass = bypass;
    }
    DWORD foreground_pid = 0;
    GetWindowThreadProcessId(GetForegroundWindow(), &foreground_pid);
    bool inactive = o.overlay && foreground_pid != o.pid &&
                    foreground_pid != GetCurrentProcessId();
    if ((bypass || inactive || now_ms() - last_frame > 250 ||
         IsIconic(f.hwnd)) &&
        shown) {
      ShowWindow(window, SW_HIDE);
      shown = false;
      log << "hide " << now_ms() << '\n';
    }
    auto frame = pool.TryGetNextFrame();
    if (!frame) {
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
      continue;
    }
    int dropped = 0;
    while (auto newer = pool.TryGetNextFrame()) {
      frame.Close();
      frame = std::move(newer);
      dropped++;
    }
    double received = now_ms(),
           captured = frame.SystemRelativeTime().count() / 10000.0;
    last_frame = received;
    if (captured <= last_source) {
      frame.Close();
      continue;
    }
    last_source = captured;
    auto current = frame.ContentSize();
    if (current.Width <= 0 || current.Height <= 0) {
      frame.Close();
      continue;
    }
    if (current.Width != size.Width || current.Height != size.Height) {
      frame.Close();
      ctx->ClearState();
      back.Reset();
      rtv.Reset();
      src.Reset();
      srv.Reset();
      size = current;
      check(
          swap->ResizeBuffers(2, size.Width, size.Height, sd.Format, sd.Flags));
      resources();
      pool.Recreate(capture_device, DirectXPixelFormat::B8G8R8A8UIntNormalized,
                    2, size);
      log << "resize " << size.Width << ' ' << size.Height << '\n';
      continue;
    }
    if (bypass || inactive || received - captured > 250) {
      frame.Close();
      continue;
    }
    if (latency && WaitForSingleObject(latency, 100) != WAIT_OBJECT_0) {
      frame.Close();
      log << "presentation wait timeout " << now_ms() << '\n';
      if (shown) {
        ShowWindow(window, SW_HIDE);
        shown = false;
      }
      continue;
    }
    RECT rect;
    GetWindowRect(f.hwnd, &rect);
    if (o.overlay)
      SetWindowPos(window, HWND_TOPMOST, rect.left, rect.top,
                   rect.right - rect.left, rect.bottom - rect.top,
                   SWP_NOACTIVATE);
    if (!shown) {
      ShowWindow(window, SW_SHOWNOACTIVATE);
      shown = true;
    }
    auto access = frame.Surface()
                      .as<::Windows::Graphics::DirectX::Direct3D11::
                              IDirect3DDxgiInterfaceAccess>();
    ComPtr<ID3D11Texture2D> captured_texture;
    check(access->GetInterface(IID_PPV_ARGS(&captured_texture)));
    Timing &t = samples[count % samples.size()];
    finish(t, false);
    t.pending = true;
    t.frame = count++;
    t.captured = captured;
    t.received = received;
    t.mode = selected_mode;
    t.dropped = dropped;
    ctx->Begin(t.disjoint.Get());
    ctx->End(t.start.Get());
    ctx->CopyResource(src.Get(), captured_texture.Get());
    if (network && selected_mode >= 3)
      network->run(srv.Get());
    struct {
      UINT mode;
      float strength, w, h;
    } params{UINT(selected_mode), o.strength, float(size.Width),
             float(size.Height)};
    ctx->UpdateSubresource(cb.Get(), 0, nullptr, &params, 0, 0);
    D3D11_VIEWPORT vp{0, 0, float(size.Width), float(size.Height), 0, 1};
    ctx->RSSetViewports(1, &vp);
    ctx->OMSetRenderTargets(1, rtv.GetAddressOf(), nullptr);
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->VSSetShader(vs.Get(), nullptr, 0);
    ctx->PSSetShader(ps.Get(), nullptr, 0);
    ctx->PSSetSamplers(0, 1, sampler.GetAddressOf());
    ctx->PSSetConstantBuffers(0, 1, cb.GetAddressOf());
    ctx->PSSetShaderResources(0, 1, srv.GetAddressOf());
    ID3D11ShaderResourceView *curve_view = network ? network->view() : nullptr;
    ctx->PSSetShaderResources(1, 1, &curve_view);
    ctx->Draw(3, 0);
    ID3D11ShaderResourceView *nil = nullptr;
    ctx->PSSetShaderResources(0, 1, &nil);
    ctx->PSSetShaderResources(1, 1, &nil);
    ctx->End(t.end.Get());
    ctx->End(t.disjoint.Get());
    if (o.snapshot > 0 && !snapshot_done &&
        received - began >= o.snapshot * 1000) {
      if (network && selected_mode >= 3)
        network->dump(o.out / "curve.f32");
      bmp(device.Get(), ctx.Get(), src.Get(), o.out / "source.bmp");
      bmp(device.Get(), ctx.Get(), back.Get(), o.out / "output.bmp");
      snapshot_done = true;
      log << "snapshot_readback_frame " << t.frame << '\n';
    }
    t.present = now_ms();
    check(swap->Present(1, 0));
    t.returned = now_ms();
    if (o.statistics) {
      UINT last_count = 0;
      auto last_hr = swap->GetLastPresentCount(&last_count);
      DXGI_FRAME_STATISTICS s{};
      double query_start = now_ms();
      HRESULT flush_hr = o.statistics_flush ? DwmFlush() : S_FALSE;
      auto stat_hr = swap->GetFrameStatistics(&s);
      double query_end = now_ms();
      // Retain errors, duplicates and raw counters. Joining belongs in analysis;
      // SyncQPCTime alone is not the time this source frame reached the display.
      stats << t.frame << ',' << t.captured << ',' << t.present << ',' << t.returned
            << ',' << uint32_t(last_hr) << ',' << last_count << ',' << query_start
            << ',' << query_end << ',' << uint32_t(flush_hr) << ',' << uint32_t(stat_hr)
            << ',' << s.PresentCount << ',' << s.PresentRefreshCount << ','
            << s.SyncRefreshCount << ',' << s.SyncQPCTime.QuadPart << ','
            << s.SyncQPCTime.QuadPart * 1000.0 / qpc_frequency.QuadPart << '\n';
    }
    t.interval = last_present ? t.present - last_present : 0;
    last_present = t.present;
    frame.Close();
  }
  ShowWindow(window, SW_HIDE);
  session.Close();
  pool.Close();
  ctx->Flush();
  for (auto &t : samples)
    finish(t, true);
  csv.flush();
  log << "complete frames " << count << " elapsed_ms " << now_ms() - began
      << '\n';
  for (int k : {8, 9, 10})
    UnregisterHotKey(window, k);
  DestroyWindow(window);
  if (latency)
    CloseHandle(latency);
  std::cout << "Completed " << count << " frames.\n";
  return count ? 0 : 2;
} catch (winrt::hresult_error const &e) {
  std::cerr << "HRESULT 0x" << std::hex << uint32_t(e.code()) << ": "
            << winrt::to_string(e.message()) << '\n';
  return 1;
} catch (std::exception const &e) {
  std::cerr << e.what() << '\n';
  return 1;
}
