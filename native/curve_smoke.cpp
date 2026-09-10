#include "curve_network.h"
#include <dxgi1_6.h>
#include <iostream>
int main(int argc, char **argv) try {
  if (argc != 4)
    throw std::runtime_error("Usage: enr_curve_smoke weights.bin input.f32 "
                             "output.f32 (320x180 NCHW)");
  using Microsoft::WRL::ComPtr;
  ComPtr<IDXGIFactory6> f;
  winrt::check_hresult(CreateDXGIFactory1(IID_PPV_ARGS(&f)));
  ComPtr<IDXGIAdapter1> a;
  winrt::check_hresult(f->EnumAdapterByGpuPreference(
      0, DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE, IID_PPV_ARGS(&a)));
  ComPtr<ID3D11Device> d;
  ComPtr<ID3D11DeviceContext> c;
  winrt::check_hresult(D3D11CreateDevice(a.Get(), D3D_DRIVER_TYPE_UNKNOWN,
                                         nullptr, 0, nullptr, 0,
                                         D3D11_SDK_VERSION, &d, nullptr, &c));
  std::vector<float> input(320 * 180 * 3);
  std::ifstream in(argv[2], std::ios::binary);
  in.read(reinterpret_cast<char *>(input.data()), input.size() * 4);
  if (!in || in.peek() != EOF)
    throw std::runtime_error("Invalid input bytes");
  CurveNetwork model(d.Get(), c.Get(), argv[1]);
  model.set_input(input);
  model.run_prepared();
  model.dump(argv[3]);
  std::cout << "Native FP32 curve written\n";
  return 0;
} catch (const winrt::hresult_error &e) {
  std::cerr << winrt::to_string(e.message());
  return 1;
} catch (const std::exception &e) {
  std::cerr << e.what();
  return 1;
}
