#pragma once
#include <d3d11.h>
#include <d3dcompiler.h>
#include <wrl/client.h>
#include <winrt/base.h>
#include <array>
#include <vector>
#include <fstream>
#include <filesystem>
#include <cmath>
#include <stdexcept>
#include <cstring>

// Zero-DCE++ inference topology. Model weights are separate, licensed research data.
// NCHW FP32, zero convolution padding, bilinear RGB downsampling, no CPU frame copy.
class CurveNetwork {
    template<class T> using Ptr=Microsoft::WRL::ComPtr<T>;
    static void ok(HRESULT result) { winrt::check_hresult(result); }
    struct Buffer { Ptr<ID3D11Buffer> data; Ptr<ID3D11ShaderResourceView> srv; Ptr<ID3D11UnorderedAccessView> uav; };
    struct Params { UINT width,height,in_channels,out_channels,split,weight_offset,bias_offset,activation; };
    ID3D11Device* device_;
    ID3D11DeviceContext* ctx_;
    UINT width_,height_;
    Buffer image_,depth_;
    std::array<Buffer,7> result_,weights_;
    Ptr<ID3D11ComputeShader> prepare_,depth_shader_,point_shader_,pack_;
    Ptr<ID3D11Buffer> params_;
    Ptr<ID3D11SamplerState> sampler_;
    Ptr<ID3D11Texture2D> curve_;
    Ptr<ID3D11ShaderResourceView> curve_srv_;
    Ptr<ID3D11UnorderedAccessView> curve_uav_;
    static constexpr UINT input_channels_[7]={3,32,32,32,64,64,64};
    static constexpr UINT output_channels_[7]={32,32,32,32,32,32,3};
    static constexpr const char* source_=R"HLSL(
cbuffer Params : register(b0) { uint W,H,IC,OC,SPLIT,WO,BO,ACT; };
StructuredBuffer<float> first : register(t0);
StructuredBuffer<float> second : register(t1);
StructuredBuffer<float> weights : register(t2);
Texture2D<float4> image : register(t3);
SamplerState linearSample : register(s0);
RWStructuredBuffer<float> result : register(u0);
RWTexture2D<float4> curve : register(u1);
float value(int x,int y,uint c) {
 if(x<0||y<0||x>=int(W)||y>=int(H))return 0;
 uint at=y*W+x;return c<SPLIT?first[c*W*H+at]:second[(c-SPLIT)*W*H+at];
}
[numthreads(8,8,1)] void prepare(uint3 p:SV_DispatchThreadID) {
 if(p.x>=W||p.y>=H)return;
 float3 rgb=image.SampleLevel(linearSample,(float2(p.xy)+.5)/float2(W,H),0).rgb;
 uint n=W*H,at=p.y*W+p.x;result[at]=rgb.r;result[n+at]=rgb.g;result[2*n+at]=rgb.b;
}
[numthreads(8,8,1)] void depthwise(uint3 p:SV_DispatchThreadID) {
 if(p.x>=W||p.y>=H||p.z>=IC)return;
 float sum=weights[BO+p.z];
 [unroll] for(int y=0;y<3;y++) [unroll] for(int x=0;x<3;x++)
  sum+=value(int(p.x)+x-1,int(p.y)+y-1,p.z)*weights[WO+p.z*9+y*3+x];
 result[p.z*W*H+p.y*W+p.x]=sum;
}
[numthreads(8,8,1)] void pointwise(uint3 p:SV_DispatchThreadID) {
 if(p.x>=W||p.y>=H||p.z>=OC)return;
 uint at=p.y*W+p.x;float sum=weights[BO+p.z];
 for(uint c=0;c<IC;c++)sum+=first[c*W*H+at]*weights[WO+p.z*IC+c];
 result[p.z*W*H+at]=ACT==2?tanh(sum):max(sum,0);
}
[numthreads(8,8,1)] void pack(uint3 p:SV_DispatchThreadID) {
 if(p.x>=W||p.y>=H)return;uint at=p.y*W+p.x,n=W*H;
 curve[p.xy]=float4(first[at],first[n+at],first[2*n+at],1);
}
)HLSL";
    Buffer buffer(UINT count,const float* initial=nullptr) {
        Buffer b;D3D11_BUFFER_DESC d{};d.ByteWidth=count*4;d.Usage=D3D11_USAGE_DEFAULT;
        d.BindFlags=D3D11_BIND_SHADER_RESOURCE|D3D11_BIND_UNORDERED_ACCESS;
        d.MiscFlags=D3D11_RESOURCE_MISC_BUFFER_STRUCTURED;d.StructureByteStride=4;
        D3D11_SUBRESOURCE_DATA s{};s.pSysMem=initial;
        ok(device_->CreateBuffer(&d,initial?&s:nullptr,&b.data));
        ok(device_->CreateShaderResourceView(b.data.Get(),nullptr,&b.srv));
        ok(device_->CreateUnorderedAccessView(b.data.Get(),nullptr,&b.uav));return b;
    }
    Ptr<ID3D11ComputeShader> shader(const char* entry) {
        Ptr<ID3DBlob> blob,error;auto hr=D3DCompile(source_,strlen(source_),"curve_network",nullptr,nullptr,entry,"cs_5_0",D3DCOMPILE_OPTIMIZATION_LEVEL3,0,&blob,&error);
        if(FAILED(hr)&&error)throw std::runtime_error(static_cast<char*>(error->GetBufferPointer()));ok(hr);
        Ptr<ID3D11ComputeShader> s;ok(device_->CreateComputeShader(blob->GetBufferPointer(),blob->GetBufferSize(),nullptr,&s));return s;
    }
    void dispatch(ID3D11ComputeShader* shader,Params p,ID3D11ShaderResourceView* a,ID3D11ShaderResourceView* b,ID3D11ShaderResourceView* weights,ID3D11ShaderResourceView* image,ID3D11UnorderedAccessView* out,ID3D11UnorderedAccessView* tex,UINT z) {
        ID3D11ShaderResourceView* srvs[]={a,b,weights,image};ID3D11UnorderedAccessView* uavs[]={out,tex};
        ctx_->UpdateSubresource(params_.Get(),0,nullptr,&p,0,0);ctx_->CSSetConstantBuffers(0,1,params_.GetAddressOf());
        ctx_->CSSetShaderResources(0,4,srvs);ctx_->CSSetUnorderedAccessViews(0,2,uavs,nullptr);
        ctx_->CSSetSamplers(0,1,sampler_.GetAddressOf());ctx_->CSSetShader(shader,nullptr,0);ctx_->Dispatch((width_+7)/8,(height_+7)/8,z);
        ID3D11ShaderResourceView* empty_srvs[4]={};ID3D11UnorderedAccessView* empty_uavs[2]={};
        ctx_->CSSetShaderResources(0,4,empty_srvs);ctx_->CSSetUnorderedAccessViews(0,2,empty_uavs,nullptr);
    }
public:
    CurveNetwork(ID3D11Device* device,ID3D11DeviceContext* ctx,const std::filesystem::path& path,UINT width=320,UINT height=180):device_(device),ctx_(ctx),width_(width),height_(height) {
        if(!width||!height||width>1280||height>720)throw std::runtime_error("Invalid network dimensions");
        std::ifstream f(path,std::ios::binary);char magic[4]{};f.read(magic,4);if(std::memcmp(magic,"ZDC1",4))throw std::runtime_error("Invalid curve weights header");
        for(int i=0;i<7;i++) {
            UINT ic=input_channels_[i],oc=output_channels_[i],count=10*ic+ic*oc+oc;
            std::vector<float> v(count);f.read(reinterpret_cast<char*>(v.data()),count*4);
            if(!f)throw std::runtime_error("Truncated curve weights");for(float value:v)if(!std::isfinite(value))throw std::runtime_error("Nonfinite curve weight");
            weights_[i]=buffer(count,v.data());result_[i]=buffer(width_*height_*oc);
        }
        if(f.peek()!=EOF)throw std::runtime_error("Unexpected trailing curve weights");
        image_=buffer(width_*height_*3);depth_=buffer(width_*height_*64);
        prepare_=shader("prepare");depth_shader_=shader("depthwise");point_shader_=shader("pointwise");pack_=shader("pack");
        D3D11_BUFFER_DESC d{};d.ByteWidth=sizeof(Params);d.Usage=D3D11_USAGE_DEFAULT;d.BindFlags=D3D11_BIND_CONSTANT_BUFFER;ok(device_->CreateBuffer(&d,nullptr,&params_));
        D3D11_SAMPLER_DESC sd{};sd.Filter=D3D11_FILTER_MIN_MAG_MIP_LINEAR;sd.AddressU=sd.AddressV=sd.AddressW=D3D11_TEXTURE_ADDRESS_CLAMP;sd.MaxLOD=D3D11_FLOAT32_MAX;ok(device_->CreateSamplerState(&sd,&sampler_));
        D3D11_TEXTURE2D_DESC td{};td.Width=width_;td.Height=height_;td.MipLevels=1;td.ArraySize=1;td.Format=DXGI_FORMAT_R32G32B32A32_FLOAT;td.SampleDesc.Count=1;td.BindFlags=D3D11_BIND_SHADER_RESOURCE|D3D11_BIND_UNORDERED_ACCESS;
        ok(device_->CreateTexture2D(&td,nullptr,&curve_));ok(device_->CreateShaderResourceView(curve_.Get(),nullptr,&curve_srv_));ok(device_->CreateUnorderedAccessView(curve_.Get(),nullptr,&curve_uav_));
    }
    void run(ID3D11ShaderResourceView* image) {
        dispatch(prepare_.Get(),{width_,height_,3,3,3,0,0,0},nullptr,nullptr,nullptr,image,image_.uav.Get(),nullptr,1);run_prepared();
    }
    void set_input(const std::vector<float>& input) {
        if(input.size()!=size_t(width_)*height_*3)throw std::runtime_error("Wrong curve input size");
        for(float value:input)if(!std::isfinite(value))throw std::runtime_error("Nonfinite curve input");
        ctx_->UpdateSubresource(image_.data.Get(),0,nullptr,input.data(),0,0);
    }
    void run_prepared() {
        for(int i=0;i<7;i++) {
            ID3D11ShaderResourceView* a=i?result_[i-1].srv.Get():image_.srv.Get();ID3D11ShaderResourceView* b=nullptr;UINT split=input_channels_[i];
            if(i>=4){a=result_[6-i].srv.Get();b=result_[i-1].srv.Get();split=32;}
            UINT ic=input_channels_[i],oc=output_channels_[i];
            dispatch(depth_shader_.Get(),{width_,height_,ic,ic,split,0,9*ic,0},a,b,weights_[i].srv.Get(),nullptr,depth_.uav.Get(),nullptr,ic);
            dispatch(point_shader_.Get(),{width_,height_,ic,oc,ic,10*ic,10*ic+ic*oc,i==6?2u:1u},depth_.srv.Get(),nullptr,weights_[i].srv.Get(),nullptr,result_[i].uav.Get(),nullptr,oc);
        }
        dispatch(pack_.Get(),{width_,height_,3,3,3,0,0,0},result_[6].srv.Get(),nullptr,nullptr,nullptr,nullptr,curve_uav_.Get(),1);ctx_->CSSetShader(nullptr,nullptr,0);
    }
    ID3D11ShaderResourceView* view()const{return curve_srv_.Get();}
    void dump(const std::filesystem::path& path) {
        D3D11_BUFFER_DESC d{};result_[6].data->GetDesc(&d);d.Usage=D3D11_USAGE_STAGING;d.BindFlags=0;d.CPUAccessFlags=D3D11_CPU_ACCESS_READ;d.MiscFlags=0;d.StructureByteStride=0;
        Ptr<ID3D11Buffer> staging;ok(device_->CreateBuffer(&d,nullptr,&staging));ctx_->CopyResource(staging.Get(),result_[6].data.Get());
        D3D11_MAPPED_SUBRESOURCE m{};ok(ctx_->Map(staging.Get(),0,D3D11_MAP_READ,0,&m));std::ofstream f(path,std::ios::binary);f.write(static_cast<char*>(m.pData),d.ByteWidth);ctx_->Unmap(staging.Get(),0);if(!f)throw std::runtime_error("Curve output write failed");
    }
};
