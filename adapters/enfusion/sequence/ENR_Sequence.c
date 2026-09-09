#ifdef WORKBENCH
// The final protocol-1 still is a completion sentinel at the start camera.
// Sequence images have their own numbered telemetry and are validated by Python.
class ENR_Sequence
{
 static int Index;
 static int Hold;
 static float CompletedAt;

 static vector Position()
 {
  if (Index >= ENR_SequenceConfig.Samples) return ENR_SequenceConfig.Start;
  float t = 0;
  if (ENR_SequenceConfig.Samples > 1) t = Index / (ENR_SequenceConfig.Samples - 1.0);
  return ENR_SequenceConfig.Start + t * (ENR_SequenceConfig.End - ENR_SequenceConfig.Start);
 }

 static vector Direction()
 {
  float t = 0;
  if (ENR_SequenceConfig.Samples > 1 && Index < ENR_SequenceConfig.Samples)
   t = Index / (ENR_SequenceConfig.Samples - 1.0);
  float yaw = ENR_SequenceConfig.YawStart + t * (ENR_SequenceConfig.YawEnd - ENR_SequenceConfig.YawStart);
  return Vector(Math.Sin(yaw * Math.DEG2RAD), 0, Math.Cos(yaw * Math.DEG2RAD));
 }

 static void Camera(BaseWorld world)
 {
  int cam = world.GetCurrentCameraId();
  world.SetCamera(cam, Position(), Direction().VectorToAngles());
  world.SetCameraVerticalFOV(cam, ENR_SequenceConfig.FOV);
  world.SetCameraNearPlane(cam, ENR_SequenceConfig.Near);
  world.SetCameraFarPlane(cam, ENR_SequenceConfig.Far);
  world.SetCameraHDRBrightness(cam, ENR_SequenceConfig.Exposure);
 }

 static bool Tick(BaseWorld world, int width, int height)
 {
  if (Index >= ENR_SequenceConfig.Samples)
   return ELab_CaptureState.Elapsed - CompletedAt > 2;
  Hold++;
  if (Hold < ENR_SequenceConfig.HoldTicks) return false;
  Hold = 0;
  int cam = world.GetCurrentCameraId();
  vector matrix[4]; world.GetCurrentCamera(matrix);
  vector up = world.ProjectWorldToViewport(matrix[3] + 10 * matrix[2] + matrix[1], cam, width, height);
  vector right = world.ProjectWorldToViewport(matrix[3] + 10 * matrix[2] + matrix[0], cam, width, height);
  PrintFormat("ENR {\"protocol\":2,\"event\":\"sample\",\"index\":%1,\"world_frame\":%2,\"simulation_seconds\":%3,\"position\":[%4,%5,%6],\"direction\":[%7,%8,%9]}", Index, world.GetFrameNumber(), ELab_CaptureState.Elapsed, matrix[3][0], matrix[3][1], matrix[3][2], matrix[2][0], matrix[2][1], matrix[2][2]);
  PrintFormat("ENR {\"protocol\":2,\"event\":\"projection\",\"index\":%1,\"width\":%2,\"height\":%3,\"up_xy\":[%4,%5],\"right_xy\":[%6,%7],\"far_plane\":%8,\"hdr_brightness\":%9}", Index, width, height, up[0], up[1], right[0], right[1], world.GetCameraFarPlane(cam), world.GetCameraHDRBrightness(cam));
  if (!System.MakeScreenshot("$profile:sample-" + Index.ToString(5)))
   Print("ELAB {\"protocol\":1,\"event\":\"error\",\"message\":\"Sequence screenshot rejected\"}");
  Index++;
  if (Index == ENR_SequenceConfig.Samples) CompletedAt = ELab_CaptureState.Elapsed;
  return false;
 }
}
#endif
