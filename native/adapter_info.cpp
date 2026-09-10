// Report the DXGI enumeration order used by the DirectML execution provider.
#include <windows.h>
#include <dxgi1_2.h>
#include <wrl/client.h>
#include <iostream>
using Microsoft::WRL::ComPtr;

int main() {
  ComPtr<IDXGIFactory1> factory;
  if (FAILED(CreateDXGIFactory1(IID_PPV_ARGS(&factory)))) return 1;
  for (UINT index = 0;; ++index) {
    ComPtr<IDXGIAdapter1> adapter;
    HRESULT result = factory->EnumAdapters1(index, &adapter);
    if (result == DXGI_ERROR_NOT_FOUND) break;
    if (FAILED(result)) return 2;
    DXGI_ADAPTER_DESC1 desc{};
    if (FAILED(adapter->GetDesc1(&desc))) return 3;
    char name[1024]{};
    if (!WideCharToMultiByte(CP_UTF8, 0, desc.Description, -1, name, sizeof(name), nullptr, nullptr)) return 4;
    std::cout << "{\"index\":" << index << ",\"description\":\"" << name
              << "\",\"vendor_id\":" << desc.VendorId << ",\"device_id\":" << desc.DeviceId
              << ",\"dedicated_video_bytes\":" << desc.DedicatedVideoMemory
              << ",\"software\":" << ((desc.Flags & DXGI_ADAPTER_FLAG_SOFTWARE) ? "true" : "false")
              << "}\n";
  }
}
