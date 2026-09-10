// Offline paired-frame diagnostic. No window, capture, Present or game hooks.
// The exact companion HLSL is supplied separately and hashed by the driver.
#include "curve_network.h"
#include <dxgi1_6.h>
#include <fcntl.h>
#include <io.h>
#include <iomanip>
#include <iostream>
#include <sstream>

int main(int argc, char **argv) try {
  if (argc != 4)
    throw std::runtime_error("Usage: enr_dce_replay weights.bin companion.hlsl NEW_CURVE_DIRECTORY; RGB24 2560x1440 frames on stdin/stdout");
  const auto folder = std::filesystem::u8path(argv[3]);
  if (std::filesystem::exists(folder) || !std::filesystem::create_directories(folder))
    throw std::runtime_error("Curve output directory must be new");
  _setmode(_fileno(stdin), _O_BINARY);
  _setmode(_fileno(stdout), _O_BINARY);
  using Microsoft::WRL::ComPtr;
  auto ok = [](HRESULT hr) { winrt::check_hresult(hr); };
  ComPtr<IDXGIFactory6> factory;
  ok(CreateDXGIFactory1(IID_PPV_ARGS(&factory)));
  ComPtr<IDXGIAdapter1> adapter;
  ok(factory->EnumAdapterByGpuPreference(0, DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE, IID_PPV_ARGS(&adapter)));
  DXGI_ADAPTER_DESC1 ad{}; ok(adapter->GetDesc1(&ad));
  if (ad.Flags & DXGI_ADAPTER_FLAG_SOFTWARE)
    throw std::runtime_error("Hardware adapter required");
  std::cerr << "adapter=" << winrt::to_string(ad.Description) << '\n';
  ComPtr<ID3D11Device> device;
  ComPtr<ID3D11DeviceContext> ctx;
  ok(D3D11CreateDevice(adapter.Get(), D3D_DRIVER_TYPE_UNKNOWN, nullptr,
      D3D11_CREATE_DEVICE_BGRA_SUPPORT, nullptr, 0, D3D11_SDK_VERSION, &device, nullptr, &ctx));
  CurveNetwork network(device.Get(), ctx.Get(), std::filesystem::u8path(argv[1]));
  std::ifstream source_file(std::filesystem::u8path(argv[2]), std::ios::binary);
  std::string shader((std::istreambuf_iterator<char>(source_file)), {});
  if (shader.empty()) throw std::runtime_error("Empty shader source");
  auto compile = [&](const char *entry, const char *target) {
    ComPtr<ID3DBlob> code, error;
    HRESULT hr = D3DCompile(shader.data(), shader.size(), "companion", nullptr, nullptr,
        entry, target, D3DCOMPILE_OPTIMIZATION_LEVEL3, 0, &code, &error);
    if (FAILED(hr) && error) std::cerr << static_cast<char *>(error->GetBufferPointer());
    ok(hr); return code;
  };
  auto vertex = compile("vs", "vs_5_0"), pixel = compile("ps", "ps_5_0");
  ComPtr<ID3D11VertexShader> vs;
  ComPtr<ID3D11PixelShader> ps;
  ok(device->CreateVertexShader(vertex->GetBufferPointer(), vertex->GetBufferSize(), nullptr, &vs));
  ok(device->CreatePixelShader(pixel->GetBufferPointer(), pixel->GetBufferSize(), nullptr, &ps));
  constexpr UINT width=2560, height=1440;
  D3D11_TEXTURE2D_DESC td{};
  td.Width=width; td.Height=height; td.MipLevels=1; td.ArraySize=1;
  td.Format=DXGI_FORMAT_B8G8R8A8_UNORM; td.SampleDesc.Count=1;
  td.Usage=D3D11_USAGE_DEFAULT; td.BindFlags=D3D11_BIND_SHADER_RESOURCE;
  ComPtr<ID3D11Texture2D> source, target, staging;
  ok(device->CreateTexture2D(&td,nullptr,&source));
  ComPtr<ID3D11ShaderResourceView> srv;
  ok(device->CreateShaderResourceView(source.Get(),nullptr,&srv));
  td.BindFlags=D3D11_BIND_RENDER_TARGET;
  ok(device->CreateTexture2D(&td,nullptr,&target));
  ComPtr<ID3D11RenderTargetView> rtv;
  ok(device->CreateRenderTargetView(target.Get(),nullptr,&rtv));
  td.BindFlags=0; td.Usage=D3D11_USAGE_STAGING; td.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
  ok(device->CreateTexture2D(&td,nullptr,&staging));
  D3D11_SAMPLER_DESC sd{};
  sd.Filter=D3D11_FILTER_MIN_MAG_MIP_LINEAR;
  sd.AddressU=sd.AddressV=sd.AddressW=D3D11_TEXTURE_ADDRESS_CLAMP;
  sd.MaxLOD=D3D11_FLOAT32_MAX;
  ComPtr<ID3D11SamplerState> sampler;
  ok(device->CreateSamplerState(&sd,&sampler));
  D3D11_BUFFER_DESC bd{}; bd.ByteWidth=16; bd.Usage=D3D11_USAGE_DEFAULT; bd.BindFlags=D3D11_BIND_CONSTANT_BUFFER;
  ComPtr<ID3D11Buffer> cb; ok(device->CreateBuffer(&bd,nullptr,&cb));
  struct Params { UINT mode; float strength,w,h; } params{3,.35f,float(width),float(height)};
  ctx->UpdateSubresource(cb.Get(),0,nullptr,&params,0,0);
  D3D11_VIEWPORT viewport{0,0,float(width),float(height),0,1};
  std::vector<unsigned char> rgb(size_t(width)*height*3), bgra(size_t(width)*height*4);
  size_t index=0;
  while (true) {
    std::cin.read(reinterpret_cast<char *>(rgb.data()),rgb.size());
    if (std::cin.gcount()==0 && std::cin.eof()) break;
    if (std::cin.gcount()!=std::streamsize(rgb.size())) throw std::runtime_error("Truncated RGB frame");
    for (size_t p=0;p<size_t(width)*height;p++) {
      bgra[4*p]=rgb[3*p+2]; bgra[4*p+1]=rgb[3*p+1]; bgra[4*p+2]=rgb[3*p]; bgra[4*p+3]=255;
    }
    ctx->UpdateSubresource(source.Get(),0,nullptr,bgra.data(),width*4,0);
    network.run(srv.Get());
    ctx->RSSetViewports(1,&viewport);
    ctx->OMSetRenderTargets(1,rtv.GetAddressOf(),nullptr);
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->VSSetShader(vs.Get(),nullptr,0); ctx->PSSetShader(ps.Get(),nullptr,0);
    ctx->PSSetSamplers(0,1,sampler.GetAddressOf()); ctx->PSSetConstantBuffers(0,1,cb.GetAddressOf());
    ctx->PSSetShaderResources(0,1,srv.GetAddressOf());
    ID3D11ShaderResourceView *curve=network.view(); ctx->PSSetShaderResources(1,1,&curve);
    ctx->Draw(3,0);
    ID3D11ShaderResourceView *null_views[2]{}; ctx->PSSetShaderResources(0,2,null_views);
    std::ostringstream name; name << "curve-" << std::setw(6) << std::setfill('0') << index << ".f32";
    network.dump(folder/name.str());
    ctx->CopyResource(staging.Get(),target.Get());
    D3D11_MAPPED_SUBRESOURCE mapped{}; ok(ctx->Map(staging.Get(),0,D3D11_MAP_READ,0,&mapped));
    for (size_t y=0;y<height;y++) {
      const auto *row=static_cast<const unsigned char *>(mapped.pData)+y*mapped.RowPitch;
      for (size_t x=0;x<width;x++) {
        size_t p=y*width+x; rgb[3*p]=row[4*x+2]; rgb[3*p+1]=row[4*x+1]; rgb[3*p+2]=row[4*x];
      }
    }
    ctx->Unmap(staging.Get(),0);
    std::cout.write(reinterpret_cast<char *>(rgb.data()),rgb.size()); std::cout.flush();
    if (!std::cout) throw std::runtime_error("Output stream closed");
    index++;
  }
  std::cerr << "completed_frames=" << index << '\n';
  return 0;
} catch (const winrt::hresult_error &e) {
  std::cerr << winrt::to_string(e.message()) << '\n'; return 1;
} catch (const std::exception &e) {
  std::cerr << e.what() << '\n'; return 1;
}
