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
  PrintFormat("ENR_BRIDGE {\"event\":\"saved\",\"name\":\"%1\",\"width\":%2,\"height\":%3,\"stride\":%4,\"success\":%5,\"tick_ms\":%6}", name, width, height, stride, saved, System.GetTickCount());
  if (!saved) Fail("raw data save failed");
  return saved;
 }

 static void Fail(string reason)
 {
  PrintFormat("ENR_BRIDGE {\"event\":\"failure\",\"reason\":\"%1\",\"tick_ms\":%2}", reason, System.GetTickCount());
  Done = true;
  CompletedAt = ELab_CaptureState.Elapsed;
 }

 static void OnSource(PixelRawData data, int width, int height, int stride)
 {
  if (Save("bridge-input.png", data, width, height, stride)) Stage = 2;
 }

 static void OnTexture(PixelRawData data, int width, int height, int stride)
 {
  if (Save("bridge-texture.png", data, width, height, stride)) Stage = 6;
 }

 static void OnPresented(PixelRawData data, int width, int height, int stride)
 {
  if (Save("bridge-presented.png", data, width, height, stride))
  {
   PrintFormat("ENR_BRIDGE {\"event\":\"completed\",\"tick_ms\":%1}", System.GetTickCount());
   Done = true;
   CompletedAt = ELab_CaptureState.Elapsed;
  }
 }

 static void OnScreenshotTexture(ScreenshotTextureData data)
 {
  bool copied = Image.CopyImageTexture(0, data);
  PrintFormat("ENR_BRIDGE {\"event\":\"screenshot_texture\",\"copied\":%1,\"tick_ms\":%2}", copied, System.GetTickCount());
  if (!copied) { Fail("screenshot texture copy rejected"); return; }
  // Return from the screenshot callback before requesting UI readback.
  Stage = 5;
 }

 static void Step(string name)
 {
  PrintFormat("ENR_BRIDGE {\"event\":\"step\",\"name\":\"%1\",\"tick_ms\":%2}", name, System.GetTickCount());
 }

 static void Present()
 {
  Step("set_image");
  Image.SetImage(0);
  int width, height;
  Step("get_image_size");
  Image.GetImageSize(0, width, height);
  Step("set_visible");
  Image.SetVisible(true);
  Step("workspace_update");
  GetGame().GetWorkspace().Update();
  Step("waiting_for_visible_widget");
  Ticks = 0;
  Stage = 3;
 }

 static bool Tick(BaseWorld world, int width, int height)
 {
  if (Done) return ELab_CaptureState.Elapsed - CompletedAt > 2;
  if (Stage == 2 && FileIO.FileExists("$profile:bridge-worker.failed"))
  {
   Fail("external CPU worker failed; inspect retained worker error");
   return false;
  }
  if (Stage == 0)
  {
   ENR_BridgeEntities.Record();
   WorkspaceWidget root = GetGame().GetWorkspace();
   Image = ImageWidget.Cast(root.CreateWidgetInWorkspace(WidgetType.ImageWidgetTypeID, 0, 0, width, height, WidgetFlags.VISIBLE, Color.FromInt(0xffffffff), 1000));
   if (!Image) { Fail("image widget creation failed"); return false; }
   FrameSlot.SetSize(Image, root.DPIUnscale(width), root.DPIUnscale(height));
   Image.SetVisible(false);
   Stage = 1;
   PrintFormat("ENR_BRIDGE {\"event\":\"requested\",\"mode\":\"%1\",\"width\":%2,\"height\":%3,\"world_frame\":%4,\"tick_ms\":%5}", ENR_BridgeConfig.Mode, width, height, world.GetFrameNumber(), System.GetTickCount());
   if (ENR_BridgeConfig.Mode == "copy")
    System.MakeScreenshotTexture(OnScreenshotTexture, 0, 0, width, height, width, height);
   else if (ENR_BridgeConfig.SourceFile)
   {
    bool submitted = System.MakeScreenshot("$profile:bridge-input");
    PrintFormat("ENR_BRIDGE {\"event\":\"source_file\",\"submitted\":%1,\"tick_ms\":%2}", submitted, System.GetTickCount());
    if (!submitted) Fail("source file screenshot rejected");
    else Stage = 2;
   }
   else
    System.MakeScreenshotRawData(OnSource, 0, 0, width, height, width, height);
  }
  else if (Stage == 2 && FileIO.FileExists("$profile:bridge-worker.done"))
  {
   bool loaded = Image.LoadImageTexture(0, "$profile:bridge-output.png", true, true);
   PrintFormat("ENR_BRIDGE {\"event\":\"file_texture\",\"loaded\":%1,\"tick_ms\":%2}", loaded, System.GetTickCount());
   if (!loaded) { Fail("local PNG load rejected"); return false; }
   Present();
  }
  else if (Stage == 5)
  {
   Present();
  }
  else if (Stage == 3)
  {
   Ticks++;
   if (Ticks >= 12)
   {
    Stage = 4;
    Step("request_texture_raw_data");
    bool requested = Image.GetTextureRawData(0, OnTexture);
    int iw, ih;
    Image.GetImageSize(0, iw, ih);
    float sw, sh;
    Image.GetScreenSize(sw, sh);
    PrintFormat("ENR_BRIDGE {\"event\":\"presented\",\"texture_size\":[%1,%2],\"screen_size\":[%3,%4],\"visible\":%5,\"raw_requested\":%6,\"world_frame\":%7,\"tick_ms\":%8}", iw, ih, sw, sh, Image.IsVisibleInHierarchy(), requested, world.GetFrameNumber(), System.GetTickCount());
    if (!requested) Fail("widget raw-data request rejected");
   }
  }
  else if (Stage == 6)
  {
   Stage = 7;
   Step("request_presented_screenshot");
   System.MakeScreenshotRawData(OnPresented, 0, 0, width, height, width, height);
  }
  return false;
 }
}
#endif
