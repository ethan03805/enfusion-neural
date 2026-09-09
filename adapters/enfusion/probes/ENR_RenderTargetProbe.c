#ifdef WORKBENCH
class ENR_RenderTargetProbe
{
 static RTTextureWidget Target;
 static RenderTargetWidget View;
 static ImageWidget Image;
 static bool Requested = false;
 static bool Completed = false;
 static int BindTicks = 0;

 static void Init(BaseWorld world)
 {
  if (Target) return;
  WorkspaceWidget root = GetGame().GetWorkspace();
  if (ELab_CaptureState.Elapsed < 2) return;
  Target = RTTextureWidget.Cast(root.CreateWidgetInWorkspace(WidgetType.RTTextureWidgetTypeID, 0, 0, 2560, 1440, WidgetFlags.VISIBLE, Color.FromInt(0xffffffff), 0));
  if (!Target) { Print("ENR_RT target creation failed"); return; }
  Target.SetResolutionScale(1.0);
  Target.ToggleFSR(false);
  FrameSlot.SetSize(Target, root.DPIUnscale(2560), root.DPIUnscale(1440));
  View = RenderTargetWidget.Cast(root.CreateWidget(WidgetType.RenderTargetWidgetTypeID, WidgetFlags.VISIBLE, Color.FromInt(0xffffffff), 0, Target));
  FrameSlot.SetSize(View, root.DPIUnscale(2560), root.DPIUnscale(1440));
  View.SetResolutionScale(1.0, 1.0);
  View.SetWorld(world, world.GetCurrentCameraId());
  Image = ImageWidget.Cast(root.CreateWidgetInWorkspace(WidgetType.ImageWidgetTypeID, 0, 0, 2560, 1440, WidgetFlags.VISIBLE, Color.FromInt(0xffffffff), 1));
  Image.SetImageTexture(0, Target);
  Image.SetImage(0);
  root.Update();
  float width, height;
  Target.GetScreenSize(width, height);
  PrintFormat("ENR_RT init root=%1x%2 target=%3x%4 scale=%5 fsr=%6", root.GetWidth(), root.GetHeight(), width, height, Target.GetResolutionScale(), Target.IsFSREnabled());
 }

 static void Export()
 {
  if (Requested || !Image) return;
  BindTicks++;
  Image.SetImageTexture(0, Target);
  Image.SetImage(0);
  if (BindTicks < 10) return;
  Requested = true;
  GetGame().GetWorkspace().Update();
  Target.Update();
  View.Update();
  Image.Update();
  int width, height;
  Image.GetImageSize(0, width, height);
  bool accepted = Image.GetTextureRawData(0, OnData);
  PrintFormat("ENR_RT export accepted=%1 size=%2x%3 completed=%4", accepted, width, height, Completed);
  float tw, th, vw, vh;
  Target.GetScreenSize(tw, th);
  View.GetScreenSize(vw, vh);
  PrintFormat("ENR_RT geometry target=%1x%2 view=%3x%4 visible=%5", tw, th, vw, vh, Target.IsVisibleInHierarchy());
  WorkspaceWidget root = GetGame().GetWorkspace();
  int nw, nh, rw, rh;
  System.GetNativeResolution(nw, nh);
  System.GetRenderingResolution(rw, rh);
  PrintFormat("ENR_RT final root=%1x%2 native=%3x%4 rendering=%5x%6", root.GetWidth(), root.GetHeight(), nw, nh, rw, rh);
  if (!accepted) { Completed = true; }
 }

 static void OnData(PixelRawData data, int width, int height, int stride)
 {
  string path;
  bool resolved = Workbench.GetAbsolutePath("$profile:render-target.png", path, false);
  bool saved;
  if (resolved) saved = Workbench.SavePixelRawData(path, data, width, height, stride);
  PrintFormat("ENR_RT exported width=%1 height=%2 stride=%3 resolved=%4 saved=%5 path=%6", width, height, stride, resolved, saved, path);
  Completed = true;
 }
}
#endif
