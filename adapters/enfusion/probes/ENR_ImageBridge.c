#ifdef WORKBENCH
// A bounded screenshot / UI presentation probe. This is not a scene render pass.
class ENR_ImageBridge
{
 static ImageWidget Image;
 static int Stage;
 static int Ticks;
 static bool Done;
 static float CompletedAt;

 static bool Save(string name, PixelRawData data, int width, int height, int stride)
 {
  string absolute;
  bool saved;
  if (Workbench.GetAbsolutePath("$profile:" + name, absolute, false))
   saved = Workbench.SavePixelRawData(absolute, data, width, height, stride);
  PrintFormat("ENR_BRIDGE saved name=%1 width=%2 height=%3 stride=%4 success=%5", name, width, height, stride, saved);
  if (!saved) Fail("raw data save failed");
  return saved;
 }

 static void Fail(string reason)
 {
  PrintFormat("ENR_BRIDGE failure reason=%1", reason);
  Done = true;
  CompletedAt = ELab_CaptureState.Elapsed;
 }

 static void OnSource(PixelRawData data, int width, int height, int stride)
 {
  if (Save("bridge-input.png", data, width, height, stride)) Stage = 2;
 }

 static void OnTexture(PixelRawData data, int width, int height, int stride)
 {
  Save("bridge-texture.png", data, width, height, stride);
 }

 static void OnPresented(PixelRawData data, int width, int height, int stride)
 {
  if (Save("bridge-presented.png", data, width, height, stride))
  {
   Print("ENR_BRIDGE completed");
   Done = true;
   CompletedAt = ELab_CaptureState.Elapsed;
  }
 }

 static void OnScreenshotTexture(ScreenshotTextureData data)
 {
  bool copied = Image.CopyImageTexture(0, data);
  PrintFormat("ENR_BRIDGE screenshot_texture copied=%1", copied);
  if (!copied) { Fail("screenshot texture copy rejected"); return; }
  Present();
 }

 static void Present()
 {
  Image.SetImage(0);
  int width, height;
  Image.GetImageSize(0, width, height);
  bool requested = Image.GetTextureRawData(0, OnTexture);
  Image.SetVisible(true);
  GetGame().GetWorkspace().Update();
  float sw, sh;
  Image.GetScreenSize(sw, sh);
  PrintFormat("ENR_BRIDGE presented texture=%1x%2 screen=%3x%4 visible=%5 raw_requested=%6 world_frame=%7", width, height, sw, sh, Image.IsVisibleInHierarchy(), requested, GetGame().GetWorld().GetFrameNumber());
  Stage = 3;
 }

 static bool Tick(BaseWorld world, int width, int height)
 {
  if (Done) return ELab_CaptureState.Elapsed - CompletedAt > 2;
  if (Stage == 0)
  {
   WorkspaceWidget root = GetGame().GetWorkspace();
   Image = ImageWidget.Cast(root.CreateWidgetInWorkspace(WidgetType.ImageWidgetTypeID, 0, 0, width, height, WidgetFlags.VISIBLE, Color.FromInt(0xffffffff), 1000));
   if (!Image) { Fail("image widget creation failed"); return false; }
   FrameSlot.SetSize(Image, root.DPIUnscale(width), root.DPIUnscale(height));
   Image.SetVisible(false);
   Stage = 1;
   PrintFormat("ENR_BRIDGE requested mode=%1 width=%2 height=%3 world_frame=%4", ENR_BridgeConfig.Mode, width, height, world.GetFrameNumber());
   if (ENR_BridgeConfig.Mode == "copy")
    System.MakeScreenshotTexture(OnScreenshotTexture, 0, 0, width, height, width, height);
   else
    System.MakeScreenshotRawData(OnSource, 0, 0, width, height, width, height);
  }
  else if (Stage == 2 && FileIO.FileExists("$profile:bridge-worker.done"))
  {
   bool loaded = Image.LoadImageTexture(0, "$profile:bridge-output.png", true, true);
   PrintFormat("ENR_BRIDGE file_texture loaded=%1", loaded);
   if (!loaded) { Fail("local PNG load rejected"); return false; }
   Present();
  }
  else if (Stage == 3)
  {
   Ticks++;
   if (Ticks >= 12)
   {
    Stage = 4;
    System.MakeScreenshotRawData(OnPresented, 0, 0, width, height, width, height);
   }
  }
  return false;
 }
}
#endif
