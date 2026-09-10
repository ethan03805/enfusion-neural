"""Shared rules for interpreting PresentMon evidence."""


def read_trace_log(path):
    data = path.read_bytes()
    return data.decode('utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig', errors='replace')


def application_present(row):
    # WGC also creates Runtime=Other records with a null swapchain. Counting them
    # together with the HWND swapchain falsely doubles companion throughput.
    return row.get('Runtime')=='DXGI' and int(row['SwapChainAddress'],16)!=0
